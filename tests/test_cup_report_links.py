# -*- coding: utf-8 -*-
"""Coupe : étiquettes de rapport, lien message/calendrier et réparation des anciens libellés."""
import json
import os
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

TMP = tempfile.mkdtemp(prefix="fm_cuplink_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP
app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=2,
            identity={"name": "Cup FC", "arena_name": "Halle", "color1": "#2f6fed",
                      "color2": "#14171f", "division": 2})

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
app.QDialog.exec = lambda self, *a, **k: 1
w = app.MainWindow()
w.setAttribute(app.Qt.WA_DontShowOnScreen, True)
w.show_game_message = lambda *a, **k: True
w.resize(1600, 1000); w.show(); q.processEvents()
w.app_stack.setCurrentWidget(w.game_shell)
w.show_page(2); q.processEvents()
w.auto_pick_lineup(); q.processEvents()

# ---------- 1) Match de coupe réellement joué ----------
c = app.db()
season = int(c.execute("SELECT season FROM club WHERE id=1").fetchone()["season"])
away = int(c.execute("SELECT id FROM club WHERE id<>1 ORDER BY id LIMIT 1").fetchone()["id"])
c.execute("UPDATE career SET current_date='2026-07-08' WHERE id=1")
c.execute("INSERT INTO fixture(season,matchday,fixture_date,home_club_id,away_club_id,fixture_type) VALUES(?,101,'2026-07-08',1,?,'cup')", (season, away))
c.commit()
cup_id = int(c.execute("SELECT id FROM fixture WHERE season=? AND matchday=101 AND home_club_id=1", (season,)).fetchone()["id"])
c.close()
w.refresh_all(ui_only=True); q.processEvents()
w.start_match(); q.processEvents()
assert w.match_state and not w.match_state.get("finished", True)
w.finish_match_now(); q.processEvents()

c = app.db()
msg = c.execute("SELECT title,body,action_data FROM manager_message WHERE kind='match_report' ORDER BY id DESC LIMIT 1").fetchone()
record = c.execute("SELECT id,matchday,fixture_type,home,away FROM match_record ORDER BY id DESC LIMIT 1").fetchone()
c.close()
assert msg is not None and "COUPE" in msg["title"], msg["title"]
assert "J1" not in msg["title"].replace("COUPE", ""), msg["title"]
data = json.loads(msg["action_data"])
assert data.get("fixture_type") == "cup" and int(data.get("matchday")) == 101, data
assert "journée" not in msg["body"].lower(), msg["body"][-120:]
assert record and str(record["fixture_type"]) == "cup" and int(record["matchday"]) == 0
print("1) rapport de coupe :", msg["title"], "| action_data", data)

# ---------- 2) Calendrier : filtre TOUT par défaut, carte coupe avec rapport ----------
w.show_page(8); q.processEvents()
assert w.calendar_filter_combo.currentText() == "TOUT", w.calendar_filter_combo.currentText()
cup_row = None
for i in range(w.calendar_fixture_list.count()):
    it = w.calendar_fixture_list.item(i); d = it.data(Qt.UserRole)
    if isinstance(d, dict) and int(d.get("fixture_id", 0)) == cup_id:
        cup_row = i; break
assert cup_row is not None, cup_id
card = w.calendar_fixture_list.itemWidget(w.calendar_fixture_list.item(cup_row))
texts = [lbl.text() for lbl in card.findChildren(app.QLabel) if lbl.text().strip()]
assert "RAPPORT →" in texts, texts
assert "COUPE" in " ".join(texts) and "C1" in texts, texts
assert not any("🏆" in t for t in texts), texts
print("2) carte coupe :", [t for t in texts if t in ("C1", "RAPPORT →")], "|", texts[-1])

# ---------- 3) Détail : rapport complet, pas le rapport simplifié ----------
w.calendar_fixture_list.setCurrentRow(cup_row); q.processEvents()
assert "32es DE FINALE" in w.calendar_report_title.text(), w.calendar_report_title.text()
assert "simplifié" not in w.calendar_report_browser.toHtml()

print("3) détail coupe :", w.calendar_report_title.text(), "| rapport complet")

# ---------- 4) Bouton « dernier rapport » : coupe incluse, pas J0 ----------
seen = {}
w.show_saved_match_report = lambda **kw: seen.update(kw)
w.show_latest_saved_match_report()
assert int(seen.get("record_id", 0)) == int(record["id"]), seen
assert "COUPE" in w.calendar_latest_report_btn.text(), w.calendar_latest_report_btn.text()
print("4) dernier rapport :", w.calendar_latest_report_btn.text(), "-> record", seen.get("record_id"))

# ---------- 5) Réparation des anciens messages « J<n> » de coupe ----------
c = app.db()
c.execute("""INSERT INTO manager_message(kind,title,body,created_date,due_date,status,action_data,is_read)
             VALUES('match_report','Rapport de match • J5','Fin de match. Rapport détaillé archivé dans le Calendrier, journée 5.','2026-07-08','2026-07-08','handled','{}',1)""")
c.execute("""INSERT INTO fixture(season,matchday,fixture_date,home_club_id,away_club_id,played,home_goals,away_goals,fixture_type)
             VALUES(?,6,'2026-07-09',1,?,1,3,1,'championship')""", (season, away))
c.execute("""INSERT INTO manager_message(kind,title,body,created_date,due_date,status,action_data,is_read)
             VALUES('match_report','Rapport de match • J6','Fin de match. Rapport détaillé archivé dans le Calendrier, journée 6.','2026-07-09','2026-07-09','handled','{}',1)""")
c.commit()
fixed = app.repair_match_report_labels(c)
c.commit()
legacy_cup = c.execute("SELECT title,body FROM manager_message WHERE title LIKE 'Rapport de match • COUPE%' ORDER BY id DESC LIMIT 1").fetchone()
legacy_league = c.execute("SELECT title FROM manager_message WHERE title LIKE '%J6' ORDER BY id DESC LIMIT 1").fetchone()
c.close()
assert fixed >= 1, fixed
assert legacy_cup and "COUPE R1" in legacy_cup["title"], dict(legacy_cup) if legacy_cup else None
assert "journée 5" not in legacy_cup["body"], legacy_cup["body"]
assert legacy_league and legacy_league["title"].endswith("J6"), legacy_league["title"]
print("5) réparation :", legacy_cup["title"], "| J6 de championnat intact")

w.close(); q.processEvents()
assert os.path.getsize(r"C:\FM2027V2\data\error.log") == 0
print("RESULT: ALL OK")
