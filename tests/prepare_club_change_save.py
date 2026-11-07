# -*- coding: utf-8 -*-
"""prepare_club_change_save.py - fabrique une sauvegarde de test avec offres de club.

Usage :
    python tests\\prepare_club_change_save.py

Copie la sauvegarde active dans TEMP, joue la fin de saison, declenche la
transition (qui genere les offres de clubs), puis ecrit une NOUVELLE sauvegarde
de test dans data/saves/ (la sauvegarde active et les autres ne sont pas
modifiees ; data/active_save.txt n'est jamais touche).

La sauvegarde produite s'ouvre sur le debut de la saison suivante, avec les
offres de changement de club deja proposees sur la Direction sportive.
"""
import os, sys, tempfile, shutil, time, json, sqlite3
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication

ROOT = r"C:\FM2027V2"


def read_active_save():
    """Lit data/active_save.txt en LECTURE SEULE pour trouver la sauvegarde."""
    marker = os.path.join(ROOT, "data", "active_save.txt")
    try:
        with open(marker, "r", encoding="utf-8") as fh:
            path = fh.read().strip()
        if path and os.path.exists(path):
            return path
    except OSError:
        pass
    return os.path.join(ROOT, "data", "saves",
                        "arbot_futsal_saison_saison_6_20261028_025341.db")


ACTIVE = read_active_save()
TARGET = os.path.join(ROOT, "data", "saves",
                      "test_changement_club_%s.db" % time.strftime("%Y%m%d_%H%M%S"))
DAYS = 280


def simulate_to_new_season(db_path):
    app.SAVE_DIR = os.path.dirname(db_path)
    app.DEFAULT_DB_PATH = os.path.join(os.path.dirname(db_path), "default.db")
    app.DB_PATH = db_path
    app.DATA_DIR = os.path.dirname(os.path.dirname(db_path))
    app.BASE_DIR = app.DATA_DIR
    app.OPTIONS_FILE = os.path.join(app.DATA_DIR, "options.json")
    app.active_save_path = lambda: db_path
    app.set_active_save_path = lambda p: None
    app.init_db()

    q = QApplication.instance() or QApplication([])
    w = app.MainWindow()
    w.show_game_message = lambda *a, **k: True
    w.resize(1400, 900)
    w.show()
    app.QDialog.exec = lambda self, *a, **k: 1

    matches = 0
    for step in range(DAYS):
        c = app.db()
        fx = w._today_fixture_for_user(c)
        ready = c.execute("SELECT value FROM meta WHERE key='season_ready'").fetchone()
        c.close()
        if ready and str(ready["value"]) == "1":
            ok = w.start_new_season()
            q.processEvents()
            print("transition de saison :", "OK" if ok else "ECHEC", "| matchs joues :", matches)
            break
        if fx:
            w.start_match()
            q.processEvents()
            w.finish_match_now()
            q.processEvents()
            matches += 1
        else:
            w.advance_calendar_days(1)
            q.processEvents()
    else:
        raise SystemExit("saison non terminee apres %d jours" % DAYS)

    c = app.db()
    season = c.execute("SELECT season,division,budget FROM club WHERE id=1").fetchone()
    date = c.execute('SELECT "current_date" d FROM career WHERE id=1').fetchone()["d"]
    offers_row = c.execute("SELECT value FROM meta WHERE key='job_offers'").fetchone()
    archive = c.execute("SELECT * FROM season_archive WHERE club_id=1 ORDER BY season DESC LIMIT 1").fetchone()
    c.close()
    offers = json.loads(offers_row["value"] or "[]") if offers_row else []
    try:
        w.close()
        QApplication.processEvents()
    except Exception:
        pass
    return season, date, offers, archive


def main():
    if not os.path.exists(ACTIVE):
        raise SystemExit("sauvegarde active introuvable : " + ACTIVE)
    tmp = tempfile.mkdtemp(prefix="fm_club_change_")
    work = os.path.join(tmp, "saves")
    os.makedirs(work, exist_ok=True)
    work_db = os.path.join(work, "work.db")
    src = sqlite3.connect(ACTIVE, timeout=30)
    dst = sqlite3.connect(work_db)
    src.backup(dst)
    dst.close(); src.close()

    print("sauvegarde source :", os.path.basename(ACTIVE))
    season, date, offers, archive = simulate_to_new_season(work_db)
    print("nouvelle saison :", dict(season), "| date :", date)
    if archive:
        print("bilan saison precedente : rang %s | %s pts | %s-%s | %s" % (
            archive["rank"], archive["pts"], archive["gf"], archive["ga"], archive["kind"]))
    print("offres :", [(o.get("name"), o.get("division"), o.get("reason")) for o in offers])
    if not offers:
        raise SystemExit("aucune offre generee : sauvegarde non produite")

    shutil.copy2(work_db, TARGET)
    conn = sqlite3.connect(TARGET)
    conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('save_slot_name',?)",
                 ("Test - Changement de club (v2)",))
    conn.commit()
    conn.close()
    print("sauvegarde creee :", TARGET)

    # Verification : on recharge la sauvegarde comme le ferait le joueur.
    app.DB_PATH = TARGET
    app.active_save_path = lambda: TARGET
    app.set_active_save_path = lambda p: None
    app.init_db()
    w = app.MainWindow()
    w.show_game_message = lambda *a, **k: True
    w.resize(1400, 900)
    w.show()
    QApplication.processEvents()
    w.app_stack.setCurrentWidget(w.game_shell)
    w.show_page(0)
    QApplication.processEvents()
    w.refresh_job_offers()
    QApplication.processEvents()
    c = app.db()
    row = c.execute("SELECT value FROM meta WHERE key='job_offers'").fetchone()
    name = c.execute("SELECT value FROM meta WHERE key='save_slot_name'").fetchone()
    c.close()
    reloaded = json.loads(row["value"] or "[]") if row else []
    panel = getattr(w, "job_offers_panel", None)
    print("relecture :", name["value"] if name else "?", "| offres", len(reloaded),
          "| panneau visible :", bool(panel and panel.isVisible()))
    for off in reloaded:
        print("  -", off.get("name"), "Ligue", off.get("division"), "|", off.get("reason"))
    w.close()
    QApplication.processEvents()
    assert loaded_ok(reloaded), "relecture des offres vide"
    print("RESULT: ALL OK")


def loaded_ok(offers):
    return bool(offers)


if __name__ == "__main__":
    main()
