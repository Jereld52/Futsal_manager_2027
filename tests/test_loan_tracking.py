# -*- coding: utf-8 -*-
"""Prêts : suivi, évolution, fiche au clic et fin de prêt si le joueur ne joue pas."""
import os, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication, QDialog

TMP = tempfile.mkdtemp(prefix="fm_loantrack_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP
app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=2,
            identity={"name": "Suivi FC", "arena_name": "A", "color1": "#2f6fed",
                      "color2": "#101a2e", "division": 2})
try:
    open(r"C:\FM2027V2\data\error.log", "r+b").truncate(0)
except FileNotFoundError:
    open(r"C:\FM2027V2\data\error.log", "wb").close()

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
w = app.MainWindow()
w.show_game_message = lambda *a, **k: True
w.resize(1400, 900)
w.show()
w.app_stack.setCurrentWidget(w.game_shell)
q.processEvents()

c = app.db()
season = int(c.execute("SELECT season FROM club WHERE id=1").fetchone()["season"])
today = c.execute('SELECT "current_date" FROM career WHERE id=1').fetchone()["current_date"]
young = c.execute("SELECT * FROM player WHERE club_id=1 ORDER BY age ASC, id ASC LIMIT 1").fetchone()
dest = c.execute("SELECT id,name,division FROM club WHERE id<>1 AND division>=2 ORDER BY id LIMIT 1").fetchone()
pid = int(young["id"]); did = int(dest["id"])
attrs = ("technique","passing","finishing","defense","goalkeeper","stamina","speed","dribble","positioning")
base_vals = [max(1, int(young[k] or 0) - 3) for k in attrs]
c.execute("INSERT OR REPLACE INTO player_attr_baseline(player_id,season,technique,passing,finishing,defense,"
          "stamina,speed,dribble,positioning,goalkeeper) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
          (pid, season, base_vals[0], base_vals[1], base_vals[2], base_vals[3],
           base_vals[5], base_vals[6], base_vals[7], base_vals[8], base_vals[4]))
c.execute("UPDATE player SET club_id=?,loan_from_club=1,loan_until_season=?,loan_promise='ROTATION',"
          "loan_start_matches=0,loan_start_date=?,"
          "season_matches=0,season_rating_count=0,season_rating_sum=0,shirt_number=0 WHERE id=?",
          (did, season, today, pid))
row = c.execute("SELECT 1 FROM league_standing WHERE club_id=?", (did,)).fetchone()
if row:
    c.execute("UPDATE league_standing SET played=10 WHERE club_id=?", (did,))
else:
    c.execute("INSERT INTO league_standing(club_id,played,wins,draws,losses,gf,ga,pts) VALUES(?,10,0,0,0,0,0,0)", (did,))
c.commit(); c.close()

w.refresh_loans_tab(); q.processEvents()
assert w.loans_out_table.rowCount() == 1, w.loans_out_table.rowCount()
assert w.loans_out_table.columnCount() == 11, w.loans_out_table.columnCount()
headers = [w.loans_out_table.horizontalHeaderItem(i).text() for i in range(11)]
assert "NIVEAU" in headers and "ÉVOLUTION" in headers and "TEMPS DE JEU" in headers, headers
evo = w.loans_out_table.item(0, 7).text()
play = w.loans_out_table.item(0, 8).text()
assert evo and evo != "—", evo
assert play.startswith("0/10"), play
assert "⚠" in play, play
assert not w.loans_out_watch.isHidden() and "sans temps de jeu" in w.loans_out_watch.text(), w.loans_out_watch.text()
print("OK: suivi affiche |", headers[6:9], "| evo", evo, "| temps", play)

# Double-clic -> fiche du joueur.
captured = []
_orig = QDialog.exec


def _exec(self, *a, **k):
    captured.append(self.windowTitle())
    return 0


QDialog.exec = _exec
w._open_loan_player(w.loans_out_table, 0)
QDialog.exec = _orig
q.processEvents()
assert captured, "la fiche du joueur ne s'est pas ouverte"
print("OK: fiche ouverte :", captured[-1])

# Fin de prêt possible car il ne joue pas.
w._last_loan_side = "out"
w.loans_out_table.selectRow(0); q.processEvents()
w._end_selected_loan(); q.processEvents()
c = app.db()
p = c.execute("SELECT club_id,loan_from_club FROM player WHERE id=?", (pid,)).fetchone()
c.close()
assert int(p["club_id"]) == 1 and int(p["loan_from_club"]) == 0, dict(p)
w.refresh_loans_tab()
assert w.loans_out_table.rowCount() == 0
print("OK: prêt terminé (joueur sans temps de jeu)")

# S'il joue assez, la fin de prêt est bloquée : il faut passer par RAPPELER.
c = app.db()
c.execute("UPDATE player SET club_id=?,loan_from_club=1,loan_until_season=?,loan_promise='ROTATION',"
          "loan_start_matches=0,loan_start_date=?,season_matches=8 WHERE id=?", (did, season, today, pid))
c.commit(); c.close()
w.refresh_loans_tab(); q.processEvents()
assert w.loans_out_table.rowCount() == 1
w._last_loan_side = "out"
w.loans_out_table.selectRow(0); q.processEvents()
w._end_selected_loan(); q.processEvents()
c = app.db()
p = c.execute("SELECT club_id,loan_from_club FROM player WHERE id=?", (pid,)).fetchone()
c.close()
assert int(p["club_id"]) == did and int(p["loan_from_club"]) == 1, dict(p)
print("OK: prêt conservé quand le joueur joue")

# Prêt entrant : fin de prêt depuis la table des entrants.
c = app.db()
other = c.execute("SELECT id FROM player WHERE club_id=? AND id<>? ORDER BY id LIMIT 1", (did, pid)).fetchone()
inpid = int(other["id"])
c.execute("UPDATE player SET club_id=1,loan_from_club=?,loan_until_season=?,loan_promise='ROTATION',"
          "loan_start_matches=0,loan_start_date=?,shirt_number=0 WHERE id=?", (did, season, today, inpid))
c.commit(); c.close()
w.refresh_loans_tab(); q.processEvents()
assert w.loans_in_table.rowCount() >= 1
w._last_loan_side = "in"
w.loans_in_table.selectRow(0); q.processEvents()
w._end_selected_loan(); q.processEvents()
c = app.db()
p = c.execute("SELECT club_id,loan_from_club FROM player WHERE id=?", (inpid,)).fetchone()
c.close()
assert int(p["club_id"]) == did and int(p["loan_from_club"]) == 0, dict(p)
print("OK: fin de prêt entrant")

w.close(); q.processEvents()
size = os.path.getsize(r"C:\FM2027V2\data\error.log")
print("error.log =", size, "octet(s)")
assert size == 0
print("RESULT: ALL OK")
