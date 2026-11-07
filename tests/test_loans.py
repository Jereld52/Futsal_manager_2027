# -*- coding: utf-8 -*-
"""Prêts sortants : demande, acceptation, temps de jeu, rappel, retour de saison, UI."""
import os, sys, tempfile, random
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from loan_engine import (loan_candidates, request_loan_out, process_outgoing_loans,
                         recall_loaned_player, return_outgoing_loans, loan_out_block_reason)

random.seed(20261028)

TMP = tempfile.mkdtemp(prefix="fm_loans_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP; app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=2,
            identity={"name": "Loan FC", "arena_name": "A", "color1": "#c47220",
                      "color2": "#14171f", "division": 2})

from PySide6.QtWidgets import QApplication, QDialog
q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
w = app.MainWindow(); w.resize(1400, 900); w.show()
w.app_stack.setCurrentWidget(w.game_shell); q.processEvents()
w.show_game_message = lambda *a, **k: True
app.QDialog.exec = lambda self, *a, **k: QDialog.Rejected

c = app.db()
squad = [int(r["id"]) for r in c.execute("SELECT id FROM player WHERE club_id=1 ORDER BY id").fetchall()]
assert len(squad) >= 12, f"effectif de test trop court ({len(squad)})"
young = int(c.execute("SELECT id FROM player WHERE club_id=1 ORDER BY age ASC, id ASC LIMIT 1").fetchone()["id"])
c.execute("UPDATE player SET age=19,loan_from_club=0,loan_until_season=0,loan_promise='',injury_days=0,injury_matches=0 WHERE id=?", (young,))
c.commit()
season = int(c.execute("SELECT season FROM club WHERE id=1").fetchone()["season"])
today = c.execute('SELECT "current_date" d FROM career WHERE id=1').fetchone()["d"]

# Garde-fous : âge et effectif.
older = int(c.execute("SELECT id FROM player WHERE club_id=1 AND id<>? ORDER BY id LIMIT 1", (young,)).fetchone()["id"])
c.execute("UPDATE player SET age=29 WHERE id=?", (older,)); c.commit()
assert loan_out_block_reason(c, c.execute("SELECT * FROM player WHERE id=?", (older,)).fetchone())
c.execute("UPDATE player SET age=22 WHERE id=?", (older,)); c.commit()

cands = loan_candidates(c, young)
assert cands, "aucun club candidat"
assert all(8 <= x["count"] < 16 for x in cands)
dest = None
for cand in cands:
    ok = request_loan_out(w, young, cand["id"], "ROTATION")
    if not ok:
        continue
    c = app.db()
    msg = c.execute("SELECT * FROM manager_message WHERE kind='loan_out_request' ORDER BY id DESC LIMIT 1").fetchone()
    assert msg and msg["status"] == "waiting"
    c.execute("UPDATE manager_message SET due_date=? WHERE id=?", (today, int(msg["id"]))); c.commit()
    w.process_due_manager_messages(c, today); c.commit()
    msg = c.execute("SELECT * FROM manager_message WHERE id=?", (int(msg["id"]),)).fetchone()
    import json
    data = json.loads(msg["action_data"] or "{}")
    c.close()
    if data.get("outcome") == "accepted":
        dest = cand
        break
assert dest, f"aucun club n'a accepté ({[x['name'] for x in cands]})"
print(f"candidats={len(cands)} destination={dest['name']} (Ligue {dest['division']})")

c = app.db()
p = c.execute("SELECT * FROM player WHERE id=?", (young,)).fetchone()
assert int(p["club_id"]) == int(dest["id"]) and int(p["loan_from_club"]) == 1
assert int(p["loan_until_season"]) == season and p["loan_promise"] == "ROTATION"
c.close()

# Onglet PRÊTS : le joueur apparaît dans les sortants.
w.refresh_loans_tab()
assert w.loans_out_table.rowCount() == 1, w.loans_out_table.rowCount()
assert w.loans_in_table.rowCount() == 0
assert w.mercato_tabs.count() == 6
print("onglet prets : 1 sortant affiche")

# Trois lundis de temps de jeu.
played = 0
for week in range(3):
    c = app.db()
    played += process_outgoing_loans(w, c, "2026-07-%02d" % (6 + 7 * week))
    c.commit(); c.close()
c = app.db()
p = c.execute("SELECT season_matches,season_rating_count FROM player WHERE id=?", (young,)).fetchone()
assert int(p["season_rating_count"]) == int(p["season_matches"])
c.close()
print(f"apparitions={played} matchs={int(p['season_matches'])}")

# Rappel immédiat.
assert recall_loaned_player(w, young)
c = app.db()
p = c.execute("SELECT club_id,loan_from_club,loan_until_season,loan_promise FROM player WHERE id=?", (young,)).fetchone()
assert int(p["club_id"]) == 1 and int(p["loan_from_club"]) == 0 and p["loan_promise"] == ""
c.close()
w.refresh_loans_tab()
assert w.loans_out_table.rowCount() == 0, w.loans_out_table.rowCount()

# Retour automatique en fin de saison, avec bilan gravé.
c = app.db()
other = c.execute("SELECT id FROM club WHERE id<>1 AND division>=2 ORDER BY id LIMIT 1").fetchone()
c.execute("""UPDATE player SET club_id=?,loan_from_club=1,loan_until_season=?,loan_promise='TITULAIRE',
                            shirt_number=0,season_matches=4,season_goals=2,season_assists=1,
                            season_rating_sum=28,season_rating_count=4 WHERE id=?""",
          (int(other["id"]), season, young))
c.commit()
assert return_outgoing_loans(w, c, season) == 1
c.commit()
p = c.execute("SELECT club_id,loan_from_club,loan_until_season,loan_promise FROM player WHERE id=?", (young,)).fetchone()
assert int(p["club_id"]) == 1 and int(p["loan_from_club"]) == 0 and p["loan_promise"] == ""
hist = c.execute("SELECT detail FROM player_history WHERE player_id=? ORDER BY id DESC LIMIT 1", (young,)).fetchone()
assert hist and "Retour de prêt" in hist["detail"] and "2 but" in hist["detail"], hist
c.close()
w.refresh_loans_tab()
assert w.loans_out_table.rowCount() == 0

# Dialogue construit sans erreur (rejeté par le patch de test).
assert w.open_loan_out_dialog(young) is False
print("RESULT: ALL OK")
