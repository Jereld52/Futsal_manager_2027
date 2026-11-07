# -*- coding: utf-8 -*-
"""Prêts : fiches complètes (sans scouting) et mention du club prêteur/emprunteur."""
import os
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication, QLabel
from PySide6.QtCore import Qt

TMP = tempfile.mkdtemp(prefix="fm_loanprof_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP
app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=2,
            identity={"name": "Loan FC", "arena_name": "Halle", "color1": "#2f6fed",
                      "color2": "#14171f", "division": 2})

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
CAPTURED = []
app.QDialog.exec = lambda self, *a, **k: (CAPTURED.append(self), 1)[1]
w = app.MainWindow()
w.setAttribute(app.Qt.WA_DontShowOnScreen, True)
w.show_game_message = lambda *a, **k: True
w.resize(1600, 1000); w.show(); q.processEvents()
w.app_stack.setCurrentWidget(w.game_shell)

c = app.db()
season = int(c.execute("SELECT season FROM club WHERE id=1").fetchone()["season"] or 1)
borrower = c.execute("SELECT id,name FROM club WHERE id<>1 ORDER BY id LIMIT 1").fetchone()
parent = c.execute("SELECT id,name FROM club WHERE id<>1 AND id<>? ORDER BY id LIMIT 1", (borrower["id"],)).fetchone()
out_pid = int(c.execute("SELECT id FROM player WHERE club_id=1 ORDER BY id LIMIT 1").fetchone()["id"])
in_pid = int(c.execute("SELECT id FROM player WHERE club_id=? ORDER BY id LIMIT 1", (parent["id"],)).fetchone()["id"])
# Notre joueur prêté au club borrower (parent = 1).
c.execute("""UPDATE player SET club_id=?,loan_from_club=1,loan_until_season=?,loan_promise='rotation',
             loan_start_date='2026-07-01',loan_start_matches=0 WHERE id=?""", (int(borrower["id"]), season, out_pid))
# Joueur du club parent prêté CHEZ NOUS.
c.execute("""UPDATE player SET club_id=1,loan_from_club=?,loan_until_season=?,loan_promise='rotation',
             loan_start_date='2026-07-01',loan_start_matches=0 WHERE id=?""", (int(parent["id"]), season, in_pid))
c.commit(); c.close()

w.refresh_all(); q.processEvents()

w.refresh_loans_tab(); q.processEvents()
assert w.loans_out_table.rowCount() >= 1, w.loans_out_table.rowCount()
assert w.loans_in_table.rowCount() >= 1, w.loans_in_table.rowCount()
print("1) prêts listés :", w.loans_out_table.rowCount(), "sortant(s),", w.loans_in_table.rowCount(), "entrant(s)")

# ---------- Fiche d'un joueur prêté PAR NOUS : complète + PRÊTÉ À ----------
CAPTURED.clear()
w.open_club_player_profile(out_pid); q.processEvents()
assert CAPTURED, "fiche du prêt sortant non ouverte"
texts = [lbl.text() for lbl in CAPTURED[-1].findChildren(QLabel)]
joined = "\n".join(texts)
assert f"PRÊTÉ À {borrower['name']}" in joined, [t for t in texts if "PRÊT" in t][:4]
assert "NIVEAU" in joined and "≈" not in joined, [t for t in texts if "NIVEAU" in t][:3]
assert "TECHNIQUE" in joined and "DÉFENSIF" in joined, [t for t in texts if "TECHNIQUE" in t][:2]
print("2) prêt sortant :", [t for t in texts if "PRÊTÉ" in t][0])

# ---------- Fiche d'un joueur prêté CHEZ NOUS : PRÊTÉ PAR ----------
CAPTURED.clear()
w.open_club_player_profile(in_pid); q.processEvents()
assert CAPTURED, "fiche du prêt entrant non ouverte"
texts = [lbl.text() for lbl in CAPTURED[-1].findChildren(QLabel)]
joined = "\n".join(texts)
assert f"PRÊTÉ PAR {parent['name']}" in joined, [t for t in texts if "PRÊT" in t][:4]
assert "NIVEAU" in joined and "≈" not in joined, [t for t in texts if "NIVEAU" in t][:3]
print("3) prêt entrant :", [t for t in texts if "PRÊTÉ" in t][0])

# ---------- Fiche express (Effectif) : mention PRÊTÉ PAR ----------
w.show_page(1); q.processEvents()
found = False
for row in range(w.roster_table.rowCount()):
    it = w.roster_table.item(row, 2)
    if it and int(it.data(Qt.UserRole) or 0) == in_pid:
        w.roster_table.setCurrentCell(row, 2); w.update_player_panel(row); q.processEvents()
        found = True; break
assert found, "joueur prêté absent de l'effectif"
assert f"PRÊTÉ PAR {parent['name']}" in w.player_meta.text(), w.player_meta.text()
print("4) fiche express :", "PRÊTÉ PAR" in w.player_meta.text())

w.close(); q.processEvents()
assert os.path.getsize(r"C:\FM2027V2\data\error.log") == 0
print("RESULT: ALL OK")
