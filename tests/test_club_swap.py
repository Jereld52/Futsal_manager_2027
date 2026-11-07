# -*- coding: utf-8 -*-
"""Test : changement de club (offres de fin de saison + bascule complète)."""
import os, sys, tempfile, json
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app

TMP = tempfile.mkdtemp(prefix="fm_swap_test_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP; app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=2,
            identity={"name": "Arbot Futsal", "arena_name": "A", "color1": "#c47220",
                      "color2": "#14171f", "division": 2})

from PySide6.QtWidgets import QApplication
q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
w = app.MainWindow(); w.resize(1400, 900); w.show()
w.app_stack.setCurrentWidget(w.game_shell); q.processEvents()
w.show_game_message = lambda *a, **k: True

c = app.db()
old = c.execute("SELECT id,name,division FROM club WHERE id=1").fetchone()
target = c.execute("SELECT id,name,division FROM club WHERE id<>1 ORDER BY id LIMIT 1").fetchone()
players_old = c.execute("SELECT COUNT(*) n FROM player WHERE club_id=1 AND COALESCE(is_free_agent,0)=0").fetchone()["n"]
players_target = c.execute("SELECT COUNT(*) n FROM player WHERE club_id=? AND COALESCE(is_free_agent,0)=0", (int(target["id"]),)).fetchone()["n"]
# archive de saison pour déclencher une offre
c.execute("INSERT OR REPLACE INTO season_archive(season,division,rank,club_id,club_name,played,pts,gf,ga,kind) VALUES(1,?,1,1,?,22,60,70,20,'champion')",
          (int(old["division"]), old["name"]))
c.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('board_confidence','75')")
c.commit()
offers = w.generate_job_offers(c)
c.commit()
assert offers, "aucune offre de club générée"
oid = int(offers[0]["club_id"])
c.close()
assert w.change_manager_club(oid) is True, "bascule refusée"
c = app.db()
new1 = c.execute("SELECT id,name,division FROM club WHERE id=1").fetchone()
oldt = c.execute("SELECT id,name,division FROM club WHERE id=?", (oid,)).fetchone()
new_players = c.execute("SELECT COUNT(*) n FROM player WHERE club_id=1 AND COALESCE(is_free_agent,0)=0").fetchone()["n"]
old_players = c.execute("SELECT COUNT(*) n FROM player WHERE club_id=? AND COALESCE(is_free_agent,0)=0", (oid,)).fetchone()["n"]
dup = c.execute("SELECT COUNT(*) n, COUNT(DISTINCT id) d FROM club").fetchone()
arch_old = c.execute("SELECT COUNT(*) n FROM season_archive WHERE club_id=? AND kind='champion'", (oid,)).fetchone()["n"]
meta_jobs = c.execute("SELECT value FROM meta WHERE key='job_offers'").fetchone()
c.close()
assert new1["name"] == offers[0]["name"], (new1["name"], offers[0]["name"])
assert oldt["name"] == old["name"], (oldt["name"], old["name"])
assert new_players == players_target and old_players == players_old, (new_players, players_target, old_players, players_old)
assert dup["n"] == dup["d"], "identifiants de club dupliqués"
assert arch_old == 1, "palmarès du club quitté perdu"
assert meta_jobs is None or meta_jobs["value"] in ("", "[]"), "offres non purgées"
print("RESULT: ALL OK")
