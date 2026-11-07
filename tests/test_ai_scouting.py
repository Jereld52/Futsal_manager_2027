# -*- coding: utf-8 -*-
"""Perception IA et retraite des libres que personne ne signe."""
import os, sys, tempfile, random
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
import ai_scouting

random.seed(20261028)

TMP = tempfile.mkdtemp(prefix="fm_aiscout_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP; app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=2,
            identity={"name": "Scout FC", "arena_name": "A", "color1": "#c47220",
                      "color2": "#14171f", "division": 2})
from PySide6.QtWidgets import QApplication, QDialog
q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
w = app.MainWindow(); w.show(); w.app_stack.setCurrentWidget(w.game_shell); q.processEvents()
w.show_game_message = lambda *a, **k: True
app.QDialog.exec = lambda self, *a, **k: QDialog.Accepted

c = app.db()
clubs = [int(r["id"]) for r in c.execute("SELECT id FROM club WHERE id<>1 ORDER BY id LIMIT 3").fetchall()]
for cid in clubs[:2]:
    for row in c.execute("SELECT id FROM player WHERE club_id=? ORDER BY id DESC LIMIT 2", (cid,)).fetchall():
        c.execute("""UPDATE player SET is_free_agent=1,contract_years=0,free_agent_since='2026-07-01',
                                     club_id=? WHERE id=?""", (cid, int(row["id"])))
c.commit()

# 1) La perception est imparfaite puis converge avec les observations.
club = c.execute("SELECT * FROM club WHERE id=?", (clubs[0],)).fetchone()
free = c.execute("SELECT * FROM player WHERE is_free_agent=1 LIMIT 1").fetchone()
true_level = app.player_level_from_row(free)
perceived, knowledge = ai_scouting.scout_player(c, club, free, "2026-07-04")
print(f"perception initiale={perceived:.1f} vrai={true_level} connaissance={knowledge}")
assert knowledge < 40
for _ in range(8):
    perceived, knowledge = ai_scouting.scout_player(c, club, free, "2026-07-11")
print(f"apres 9 observations: perception={perceived:.1f} connaissance={knowledge}")
assert knowledge == 100
assert abs(perceived - true_level) <= 2.0, (perceived, true_level)
assert c.execute("SELECT COUNT(*) n FROM ai_scout_knowledge").fetchone()["n"] > 0
c.commit()

# 2) Les clubs IA recrutent selon leur perception et purgent la date de libre.
before = sum(c.execute("SELECT COUNT(*) n FROM player WHERE club_id=? AND is_free_agent=0", (cid,)).fetchone()["n"] for cid in clubs)
for weekend in ("2026-07-04", "2026-07-11", "2026-07-18", "2026-07-25", "2026-08-01", "2026-08-08"):
    w.process_ai_recruitment(c, weekend)
    c.commit()
after = sum(c.execute("SELECT COUNT(*) n FROM player WHERE club_id=? AND is_free_agent=0", (cid,)).fetchone()["n"] for cid in clubs)
stale = c.execute("SELECT COUNT(*) n FROM player WHERE is_free_agent=0 AND COALESCE(free_agent_since,'')<>''").fetchone()["n"]
print(f"recrutements IA: {before} -> {after} | dates non purgees={stale}")
assert after > before
assert stale == 0
assert c.execute("SELECT COUNT(*) n FROM ai_scout_knowledge").fetchone()["n"] >= 1

# 3) Un libre que personne ne signe raccroche, meme jeune.
young = c.execute("SELECT * FROM player WHERE is_free_agent=1 ORDER BY age ASC LIMIT 1").fetchone()
c.execute("UPDATE player SET age=19,free_agent_since='2024-01-01' WHERE id=?", (int(young["id"]),))
c.execute("UPDATE fixture SET played=1,home_goals=1,away_goals=0 WHERE played=0")
c.commit(); c.close()
assert w.start_new_season() is True
c = app.db()
row = c.execute("SELECT retired,is_free_agent,free_agent_since FROM player WHERE id=?", (int(young["id"]),)).fetchone()
no_date = c.execute("""SELECT COUNT(*) n FROM player WHERE COALESCE(is_free_agent,0)=1
                       AND COALESCE(free_agent_since,'')=''""").fetchone()["n"]
free_club1 = c.execute("SELECT COUNT(*) n FROM player WHERE is_free_agent=1 AND club_id=1").fetchone()["n"]
# Le reapprovisionnement ne doit jamais remettre un retraite sur le marche.
app.ensure_free_agents(c); c.commit()
row_again = c.execute("SELECT is_free_agent FROM player WHERE id=?", (int(young["id"]),)).fetchone()
c.close()
print(f"libre jeune: retire={row['retired']} libre={row['is_free_agent']} date='{row['free_agent_since']}' | sans date={no_date}")
assert int(row["retired"]) == 1 and int(row["is_free_agent"]) == 0 and row["free_agent_since"] == ""
assert int(row_again["is_free_agent"]) == 0, "un retraite est revenu sur le marche"
assert no_date == 0 and free_club1 == 0
print("RESULT: ALL OK")
