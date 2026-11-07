# -*- coding: utf-8 -*-
"""Centre de formation : projets, détection, recrutement de jeunes."""
import os, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtTest import QTest

TMP = tempfile.mkdtemp(prefix="fm_acaddev_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP; app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=3,
            identity={"name": "Acad Dev FC", "arena_name": "A", "color1": "#c47220",
                      "color2": "#14171f", "division": 3})

c = app.db()
c.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('academy_unlocked','1')")
c.execute("UPDATE club SET budget=5000000 WHERE id=1")
c.commit(); c.close()

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
w = app.MainWindow(); w.resize(1560, 900); w.show()
w.show_game_message = lambda *a, **k: True
app.QDialog.exec = lambda self, *a, **k: QDialog.Accepted
w.app_stack.setCurrentWidget(w.game_shell); q.processEvents()
w.show_page(13); QTest.qWait(300); q.processEvents()

assert w.academy_dev_cards["school"]["pill"].text() == "NIV. 0/3"
assert w.academy_detection_btn.isEnabled()

# 1) Projets : école puis partenariat étranger, avec un chantier à la fois.
c = app.db(); total0 = app.academy_profile(c)["total"]; c.close()

def finish_project(key):
    c = app.db()
    p = app.academy_dev_project(c)
    assert p and p["key"] == key, (key, p)
    c.execute('UPDATE career SET current_date=? WHERE id=1', (p["due"],))
    c.commit()
    app.complete_academy_dev_project(c, p["due"])
    c.commit(); c.close()

assert w.buy_academy_dev("school")
assert not w.buy_academy_dev("foreign"), "deux chantiers simultanés acceptés"
finish_project("school")
assert w.buy_academy_dev("foreign")
finish_project("foreign")
c = app.db()
levels = app.academy_dev_levels(c)
bonus = app.academy_dev_bonus(c)
total1 = app.academy_profile(c)["total"]
c.close()
assert levels["school"] == 1 and levels["foreign"] == 1
assert bonus["growth"] > 0 and bonus["foreign_level"] == 1
assert total1 > total0, (total0, total1)
print("OK projets : école 1, étranger 1 (2 chantiers successifs), note", total0, "->", total1)

# 2) Prospect étranger : nationalité non française et potentiel boosté.
c = app.db()
p = w._generate_academy_prospect(c, 70, foreign=True, foreign_level=1)
c.close()
assert p["foreign"] and p["nationality"] != "Française", (p["foreign"], p["nationality"])
assert p["age"] <= 17 and p["potential"] >= 1
print("OK prospect étranger :", p["first_name"], p["last_name"], p["nationality"], p["potential"], "/20")

# 3) Signature : le jeune entre au club et apparaît dans le centre.
assert w.sign_academy_prospect(p)
c = app.db()
row = c.execute("SELECT age,potential_fixed FROM player WHERE club_id=1 AND first_name=? AND last_name=?",
                (p["first_name"], p["last_name"])).fetchone()
youth = c.execute("SELECT COUNT(*) n FROM player WHERE club_id=1 AND age<=18").fetchone()["n"]
c.close()
assert row is not None and int(row["age"]) <= 18
assert youth >= 1
print("OK signature :", youth, "jeune(s) au club")

# 4) Journée de détection : coût, cooldown et bouton désactivé.
c = app.db(); before = int(c.execute("SELECT budget FROM club WHERE id=1").fetchone()["budget"]); c.close()
w.launch_academy_detection(); q.processEvents()
c = app.db()
after = int(c.execute("SELECT budget FROM club WHERE id=1").fetchone()["budget"])
last = c.execute("SELECT value FROM meta WHERE key='academy_last_detection'").fetchone()
c.close()
assert before - after == app.ACADEMY_DETECTION_COST, (before, after)
assert last and last["value"]
w._refresh_academy_dev_widgets()
assert not w.academy_detection_btn.isEnabled()
assert "DANS" in w.academy_detection_btn.text().upper()
print("OK détection :", before - after, "€ |", w.academy_detection_btn.text())

# 5) Plafond : deux journées de détection par saison, pas plus.
from datetime import timedelta
def _skip_detection_cooldown():
    c = app.db()
    old = (app.parse_iso(w._career_day()) - timedelta(days=30)).isoformat()
    c.execute("UPDATE meta SET value=? WHERE key='academy_last_detection'", (old,))
    c.commit(); c.close()

_skip_detection_cooldown()
w.launch_academy_detection(); q.processEvents()
c = app.db()
used = int((c.execute("SELECT value FROM meta WHERE key='academy_detection_count'").fetchone() or {"value": 0})["value"] or 0)
c.close()
assert used == 2, used
_skip_detection_cooldown()
c = app.db(); before3 = int(c.execute("SELECT budget FROM club WHERE id=1").fetchone()["budget"]); c.close()
w.launch_academy_detection(); q.processEvents()
c = app.db(); after3 = int(c.execute("SELECT budget FROM club WHERE id=1").fetchone()["budget"]); c.close()
assert before3 == after3, (before3, after3)
w._refresh_academy_dev_widgets()
assert "2/2" in w.academy_detection_btn.text(), w.academy_detection_btn.text()
print("OK plafond détection : 2 journées par saison")
print("RESULT: ALL OK")
