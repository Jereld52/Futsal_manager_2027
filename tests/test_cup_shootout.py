# -*- coding: utf-8 -*-
"""Coupe : une égalité passe par une vraie séance de 10 m visible (pas de but surprise)."""
import os
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

TMP = tempfile.mkdtemp(prefix="fm_shootaudit_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP
app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=2,
            identity={"name": "Shoot FC", "arena_name": "Halle", "color1": "#2f6fed",
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

# ---------- 1) Match de coupe à égalité (2-2) ----------
c = app.db()
season = int(c.execute("SELECT season FROM club WHERE id=1").fetchone()["season"])
away = int(c.execute("SELECT id FROM club WHERE id<>1 ORDER BY id LIMIT 1").fetchone()["id"])
cup = c.execute("""SELECT id FROM fixture WHERE COALESCE(fixture_type,'')='cup'
                   AND (home_club_id=1 OR away_club_id=1) ORDER BY matchday,id LIMIT 1""").fetchone()
if cup:
    fid = int(cup["id"]); c.execute("UPDATE fixture SET fixture_date='2026-07-08' WHERE id=?", (fid,))
else:
    c.execute("INSERT INTO fixture(season,matchday,fixture_date,home_club_id,away_club_id,fixture_type) VALUES(?,101,'2026-07-08',1,?,'cup')", (season, away))
    fid = int(c.execute("SELECT id FROM fixture WHERE fixture_date='2026-07-08' AND home_club_id=1 AND fixture_type='cup'").fetchone()["id"])
c.execute("UPDATE career SET current_date='2026-07-08' WHERE id=1")
c.commit(); c.close()

w.refresh_all(ui_only=True); q.processEvents()
w.start_match(); q.processEvents()
assert w.match_state and not w.match_state["finished"]
w.match_state["hg"] = 2; w.match_state["ag"] = 2; w.match_state["half_time_score"] = (1, 2)
w.finish_match(); q.processEvents()

c = app.db()
fx = c.execute("SELECT * FROM fixture WHERE id=?", (fid,)).fetchone()
rec = c.execute("SELECT * FROM match_record ORDER BY id DESC LIMIT 1").fetchone()
msg = c.execute("SELECT title,body FROM manager_message WHERE kind='match_report' ORDER BY id DESC LIMIT 1").fetchone()
c.close()
assert int(fx["home_goals"]) == 2 and int(fx["away_goals"]) == 2, (fx["home_goals"], fx["away_goals"])
assert fx["pen_home"] is not None and fx["pen_away"] is not None, dict(fx)
ph, pa = int(fx["pen_home"]), int(fx["pen_away"])
assert ph != pa, (ph, pa)
assert int(rec["home_goals"]) == 2 and int(rec["away_goals"]) == 2
assert int(rec["pen_home"]) == ph and int(rec["pen_away"]) == pa
assert "SÉANCE DE 10 M" in (rec["report"] or "")
assert "10 m" in (rec["report"] or "")
assert "COUPE" in msg["title"] and "journée" not in msg["body"].lower(), (msg["title"], msg["body"][-80:])
print(f"1) 2-2 conservé · 10 m {ph}-{pa} ·", msg["title"])

# ---------- 2) Le qualifié est celui des 10 m ----------
winner = app._cup_winner_of(fx)
expected = int(fx["home_club_id"]) if ph > pa else int(fx["away_club_id"])
assert winner == expected, (winner, expected, ph, pa)
report = w.last_match_report
assert report and report.get("shootout"), report
assert int(report["shootout"]["h"]) == ph and int(report["shootout"]["a"]) == pa
manager_side = "h" if report["manager_home"] else "a"
assert report["outcome"] == ("VICTOIRE" if report["shootout"]["winner"] == manager_side else "DÉFAITE"), report["outcome"]
assert report["outcome"] != "MATCH NUL"
print("2) qualifié = vainqueur des 10 m ·", report["outcome"])

# ---------- 3) Direct : les tentatives sont visibles ----------
log = w.event_log.toPlainText()
assert log.count("10 m —") >= 5, log[-400:]
assert "qualifié" in log.lower() or "qualifie" in log.lower(), log[-200:]
print("3) direct :", log.count("10 m —"), "lignes de 10 m")

# ---------- 4) Calendrier : score 2-2 + mention des 10 m ----------
w.show_page(8); q.processEvents()
row = None
for i in range(w.calendar_fixture_list.count()):
    it = w.calendar_fixture_list.item(i); data = it.data(Qt.UserRole)
    if isinstance(data, dict) and int(data.get("fixture_id", 0)) == fid:
        row = i; break
assert row is not None
card = w.calendar_fixture_list.itemWidget(w.calendar_fixture_list.item(row))
texts = [lbl.text() for lbl in card.findChildren(app.QLabel) if lbl.text().strip()]
assert any(t == f"10 m {ph}-{pa}" for t in texts), texts
w.calendar_fixture_list.setCurrentRow(row); q.processEvents()
assert "2  :  2" in w.calendar_report_score.text(), w.calendar_report_score.text()
assert "aux 10 m" in w.calendar_report_score.text(), w.calendar_report_score.text()
assert "SÉANCE DE 10 M" in w.calendar_report_browser.toHtml()
print("4) calendrier :", w.calendar_report_score.text(), "| rapport complet")

# ---------- 5) Bilan de coupe : un succès aux 10 m n'est pas une élimination ----------
c = app.db()
c.execute("DELETE FROM meta WHERE key LIKE 'cup_recap_%'")
c.execute("UPDATE fixture SET matchday=106, home_club_id=1, away_club_id=?, home_goals=2, away_goals=2, pen_home=4, pen_away=3, played=1 WHERE id=?", (away, fid))
c.commit()
w.send_cup_recap(c, season)
c.commit()
recap = c.execute("SELECT title,body FROM manager_message WHERE title LIKE 'Coupe Inter-Ligue%' ORDER BY id DESC LIMIT 1").fetchone()
c.close()
assert recap and "VAINQUEUR" in recap["title"], dict(recap) if recap else None
assert "ÉLIMINÉ" not in recap["title"], recap["title"]
print("5) bilan coupe :", recap["title"])

w.close(); q.processEvents()
assert os.path.getsize(r"C:\FM2027V2\data\error.log") == 0
print("RESULT: ALL OK")
