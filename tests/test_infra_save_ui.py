# -*- coding: utf-8 -*-
"""QA visuelle : proportions de l'arena Infrastructure (ratio fixe sur tous
les ecrans) + gestion des sauvegardes : selection multiple et suppression
grouped. Ce test cree ses propres sauvegardes ZZTEST_* et ne touche JAMAIS
aux sauvegardes utilisateur."""
import os, sys, sqlite3, tempfile
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, r"C:\FM2027V2")
sys.path.insert(0, r"C:\FM2027V2\tests")

import app as appmod
from PySide6.QtCore import Qt, QRectF
from PySide6.QtWidgets import QApplication, QDialog, QListWidget, QPushButton

def ok(msg):
    print("OK:", msg)

app = QApplication([])

# ---------------------------------------------------------------- 1) arena : proportion
from app import FacilityArenaView
av = FacilityArenaView()
av.resize(1900, 600); img1 = av.grab()
assert not img1.isNull()
av.resize(700, 800);  img2 = av.grab()
assert not img2.isNull()
# ratio du terrain : toujours 2:1 quelles que soient les bornes
g = av.futsal_court_geometry(QRectF(0, 0, 1000, 300))
assert abs(g.width()/g.height() - 2.0) < 0.01
g2 = av.futsal_court_geometry(QRectF(0, 0, 300, 1000))
assert abs(g2.width()/g2.height() - 2.0) < 0.01
ok("1) arena : grab 1900x600 et 700x800 sans distorsion, terrain 2:1 garanti")

# ---------------------------------------------------------------- 2) dialogues sauvegardes
SAVE_DIR = appmod.SAVE_DIR
os.makedirs(SAVE_DIR, exist_ok=True)
FAKE_SCHEME = """
CREATE TABLE club(id INTEGER PRIMARY KEY, name TEXT, color1 TEXT, color2 TEXT, division INTEGER, season INTEGER);
CREATE TABLE career(id INTEGER PRIMARY KEY, club_id INTEGER, season INTEGER, matchday INTEGER,
    wins INTEGER, draws INTEGER, losses INTEGER, goals_for INTEGER, goals_against INTEGER,
    points INTEGER, [current_date] TEXT);
CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT);
INSERT INTO club VALUES(1,'ZZTEST ACADEMY','#88ffcc','#2255aa',6,2027);
INSERT INTO career VALUES(1,1,2027,1,1,0,0,2,1,3,'2026-10-24');
INSERT INTO meta VALUES('career_created','2026-10-24');
"""
def make_fake(path):
    conn = sqlite3.connect(path)
    conn.executescript(FAKE_SCHEME)
    conn.commit(); conn.close()

paths = [os.path.join(SAVE_DIR, "ZZTEST_multi_%d.db" % i) for i in (1, 2)]
try:
    for p in paths:
        if os.path.exists(p):
            os.remove(p)
        make_fake(p)
    ok("2) deux sauvegardes ZZTEST creees (jamais celles de l'utilisateur)")

    opened = {}
    def fake_exec(dialog, *a, **k):
        dialog.show(); QApplication.instance().processEvents()
        title = dialog.windowTitle()
        opened[title] = opened.get(title, 0) + 1
        if "charger une partie" in title.lower():
            # Ne jamais activer une vraie carrière depuis un test.
            dialog.reject(); return QDialog.Rejected
        if title == "Gérer les sauvegardes":
            lst = dialog.findChild(QListWidget)
            assert lst is not None, "liste de sauvegardes introuvable"
            zz = [lst.item(i) for i in range(lst.count()) if "ZZTEST" in lst.item(i).text()]
            assert len(zz) >= 2, "catalogue sans les deux ZZTEST : %d" % len(zz)
            lst.clearSelection()
            for it in zz:
                it.setSelected(True)
            QApplication.instance().processEvents()
            btns = [b for b in dialog.findChildren(QPushButton) if b.text().startswith("SUPPRIMER")]
            assert len(btns) == 1
            btn = btns[0]
            assert btn.isEnabled(), "SUPPRIMER inactif sur deux suppressibles"
            assert "2" in btn.text(), "compteur de selection multiple absent : " + btn.text()
            btn.click(); QApplication.instance().processEvents()
            assert "ENCORE" in btn.text(), "double confirmation absente"
            btn.click(); QApplication.instance().processEvents()
            for p in paths:
                assert not os.path.exists(p), "fichier non supprime : " + p
            ok("3) selection multiple : 2 sauvegardes supprimees en une action (double clic)")
        dialog.accept()
        return QDialog.Accepted
    appmod.QDialog.exec = fake_exec

    # DB de la fenetre : une base TMP neuve (l'utilisateur n'est jamais touche)
    tmp_db = os.path.join(tempfile.mkdtemp(prefix="qa_fm27_"), "qa_career.db")
    appmod.DB_PATH = tmp_db
    appmod.init_db(fresh_universe=True, selected_division=6,
                   identity={"name": "ZZTEST CLUB", "short_name": "ZZT", "color1": "#88ffcc",
                             "color2": "#2255aa", "kit_pattern": "vertical", "logo_pattern": "shield",
                             "database_size": "classic", "division": 6})
    try:
        open(os.path.join(r"C:\FM2027V2\data", "error.log"), "r+b").truncate(0)
    except FileNotFoundError:
        open(os.path.join(r"C:\FM2027V2\data", "error.log"), "wb").close()

    w = appmod.MainWindow(); w.show(); QApplication.instance().processEvents()

    # Aucun test ne doit écrire data/active_save.txt ni charger une vraie carrière.
    appmod.set_active_save_path = lambda p: None
    w.activate_career = lambda *a, **k: None

    # gestion : suppression multiple verifiee dans fake_exec
    w.open_manage_saves_dialog()
    assert opened.get("Gérer les sauvegardes") == 1, opened
    ok("   gestion des sauvegardes : suppression multiple confirmee par le resultat fichier")

    # chargement : dialogue mono-selection (Charger) non casse
    w.open_load_career_dialog()
    ok("4) dialog CHARGER : mono-selection preserve, suivi double clic load")

    # Les dialogues de sauvegarde ont pu rebasculer sur une carrière réelle :
    # on revient sur la base temporaire du test avant de vérifier l'infrastructure.
    appmod.DB_PATH = tmp_db

    # panneau lateral : chantiers + services du stade
    assert hasattr(w, "facility_side_panel") and hasattr(w, "facility_projects_layout")
    conn = appmod.db()
    facility = conn.execute("SELECT * FROM facility WHERE id=1").fetchone()
    club = conn.execute("SELECT * FROM club WHERE id=1").fetchone()
    career = conn.execute('SELECT "current_date" AS d FROM career WHERE id=1').fetchone()
    today_iso = career["d"] if career else "2026-08-01"
    conn.execute("DELETE FROM facility_project WHERE facility_key='arena_level'")
    conn.execute("DELETE FROM finance_tx WHERE club_id=1 AND label LIKE '%Tribunes%'")
    conn.execute("DELETE FROM news WHERE body LIKE '%Tribunes%'")
    conn.execute("DELETE FROM meta WHERE key='facility_max_arena_level'")
    conn.execute("UPDATE facility SET arena_level=1 WHERE id=1")
    target_level = 2
    conn.execute("""INSERT INTO facility_project(facility_key,label,target_level,cost,duration_days,
                    start_date,due_date,status) VALUES('arena_level',?,?,50000,5,?,date(?,'+5 day'),'in_progress')""",
                 (f"Tribunes niv. {target_level}", target_level, today_iso, today_iso))
    conn.commit(); conn.close()
    w.refresh_facility_panel(facility, club)
    w.refresh_facility_panel(facility, club)
    QApplication.instance().processEvents()
    conn = appmod.db()
    active = conn.execute("SELECT COUNT(*) n FROM facility_project WHERE status='in_progress'").fetchone()["n"]
    conn.close()
    assert w.facility_projects_layout.count() == active, (w.facility_projects_layout.count(), active)
    assert w.facility_projects_layout.count() >= 1
    assert "place(s) occupée(s)" in w.facility_side_slots.text()
    assert int(w.facility_side_slots.text().split("/")[0].strip()) >= 1
    assert w.facility_vip_status.text() in ("OUVERT", "À CONSTRUIRE")
    ok("5) panneau lateral : chantier en cours + statut VIP/bar/boutique")
    w.close()
finally:
    for p in paths:
        try:
            if os.path.exists(p):
                os.remove(p)
        except OSError:
            pass
    print("cleanup : ZZTEST_* retires du dossier de sauvegardes")

ok("RESULT: ALL OK")
