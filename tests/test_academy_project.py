# -*- coding: utf-8 -*-
"""Centre de formation : un chantier a la fois, livraison apres un delai."""
import os, sys, tempfile, json
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication

TMP = tempfile.mkdtemp(prefix="fm_acadproj_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP
app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=3,
            identity={"name": "Academy FC", "arena_name": "A", "color1": "#2f6fed",
                      "color2": "#101a2e", "division": 3, "difficulty": "Normal"})
try:
    open(r"C:\FM2027V2\data\error.log", "r+b").truncate(0)
except FileNotFoundError:
    open(r"C:\FM2027V2\data\error.log", "wb").close()

c = app.db()
c.execute("UPDATE club SET budget=2000000 WHERE id=1")
c.commit(); c.close()

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
w = app.MainWindow()
w.show_game_message = lambda *a, **k: True
w.resize(1400, 900)
w.show()
q.processEvents()
w.app_stack.setCurrentWidget(w.game_shell)
q.processEvents()

c = app.db()
if not app.academy_unlocked(c):
    c.close()
    w.invest_academy()
    q.processEvents()
    c = app.db()
assert app.academy_unlocked(c)
today = c.execute('SELECT "current_date" FROM career WHERE id=1').fetchone()["current_date"]
budget0 = int(c.execute("SELECT budget FROM club WHERE id=1").fetchone()["budget"])
c.close()

ok = w.buy_academy_dev("school")
q.processEvents()
assert ok, "le chantier n'a pas demarre"
c = app.db()
levels = app.academy_dev_levels(c)
project = app.academy_dev_project(c)
budget1 = int(c.execute("SELECT budget FROM club WHERE id=1").fetchone()["budget"])
c.close()
assert levels["school"] == 0, levels
assert project and project["key"] == "school" and project["target"] == 1, project
assert project["due"] > today, (today, project["due"])
assert budget1 == budget0 - 45000, (budget0, budget1)
from game_utils import parse_iso
assert (parse_iso(project["due"]) - parse_iso(today)).days == app.ACADEMY_DEV_DURATIONS[1]
print("OK: chantier lance, niveau pas encore applique |", project["due"])

# Deuxieme action refusee tant que le chantier tourne.
assert not w.buy_academy_dev("local"), "deux chantiers simultanes acceptes"
w._refresh_academy_dev_widgets()
q.processEvents()
school = w.academy_dev_cards["school"]
local = w.academy_dev_cards["local"]
school_status = school["status"].full_text() if hasattr(school["status"], "full_text") else school["status"].text()
assert "Chantier" in school_status, school_status
assert school["button"].text() == "EN COURS" and not school["button"].isEnabled()
assert local["button"].text() == "BLOQUÉ" and not local["button"].isEnabled()
print("OK: cartes bloquees |", school_status, "|", local["button"].text())

# Le dialogue secondaire doit refleter le meme chantier.
try:
    dlg = app.AcademyDevDialog(w)
    dlg.refresh()
    assert dlg.rows.count() > 8, dlg.rows.count()
    dlg.close()
    print("OK: dialogue de developpement synchronise")
except AttributeError:
    pass

# A l'echeance, le niveau s'applique tout seul.
c = app.db()
c.execute('UPDATE career SET current_date=? WHERE id=1', (project["due"],))
c.commit(); c.close()
w._refresh_academy_dev_widgets()
q.processEvents()
c = app.db()
assert app.academy_dev_levels(c)["school"] == 1
assert app.academy_dev_project(c) is None
msg = c.execute("SELECT title FROM manager_message WHERE title LIKE 'Chantier terminé%'").fetchone()
news = c.execute("SELECT title FROM news WHERE title='Centre de formation'").fetchone()
c.close()
assert msg and "École de football" in msg["title"], msg
assert news, "actualite de fin de chantier absente"
print("OK: livraison appliquee |", msg["title"])

# Niveau suivant : 21 jours.
c = app.db()
today2 = c.execute('SELECT "current_date" FROM career WHERE id=1').fetchone()["current_date"]
c.close()
assert w.buy_academy_dev("school")
c = app.db()
p2 = app.academy_dev_project(c)
c.close()
assert p2 and p2["target"] == 2, p2
assert (parse_iso(p2["due"]) - parse_iso(today2)).days == app.ACADEMY_DEV_DURATIONS[2]
print("OK: niveau 2 en chantier pour", app.ACADEMY_DEV_DURATIONS[2], "jours")

w.close()
q.processEvents()
size = os.path.getsize(r"C:\FM2027V2\data\error.log")
print("error.log =", size, "octet(s)")
assert size == 0
print("RESULT: ALL OK")
