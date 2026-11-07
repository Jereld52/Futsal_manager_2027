# -*- coding: utf-8 -*-
"""Réparation : un match de coupe réellement joué ne doit pas redevenir « à jouer »."""
import os, sys, tempfile, json
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app

TMP = tempfile.mkdtemp(prefix="fm_phantom_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP; app.BASE_DIR = TMP
app.OPTIONS_FILE = os.path.join(TMP, "options.json")
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=3,
            identity={"name": "Phantom FC", "arena_name": "A", "color1": "#c47220",
                      "color2": "#14171f", "division": 3})

c = app.db()
season = int(c.execute("SELECT season FROM club WHERE id=1").fetchone()["season"] or 1)
me = c.execute("SELECT name FROM club WHERE id=1").fetchone()["name"]
opp = c.execute("SELECT id,name FROM club WHERE id<>1 ORDER BY id LIMIT 1").fetchone()
opp_id, opp_name = int(opp["id"]), opp["name"]

# 1) Match de coupe réellement joué : fixture + rapport calendrier + match_record.
c.execute("INSERT INTO fixture(season,matchday,fixture_date,home_club_id,away_club_id,fixture_type,played,home_goals,away_goals) "
          "VALUES(?,?,?,?,?,'cup',1,3,1)", (season, 101, "2026-09-15", 1, opp_id))
fx_id = int(c.execute("SELECT id FROM fixture WHERE fixture_type='cup' ORDER BY id DESC LIMIT 1").fetchone()["id"])
c.execute("INSERT INTO ai_match_report(fixture_id,scorers,created_at) VALUES(?,?,?)",
          (fx_id, json.dumps([{"minute": 8, "side": "h", "team": me, "scorer": "Test", "assist": None}]), "2026-09-15"))
c.execute("INSERT INTO match_record(season,matchday,home,away,home_goals,away_goals,report,simulation_seed,created_at) "
          "VALUES(?,?,?,?,?,?,?,?,?)", (season, 0, me, opp_name, 3, 1, "rapport", 0, "2026-09-15"))
c.commit()
app.repair_phantom_user_fixtures(c)
c.commit()
row = c.execute("SELECT played,home_goals,away_goals FROM fixture WHERE id=?", (fx_id,)).fetchone()
assert int(row["played"]) == 1 and int(row["home_goals"]) == 3, dict(row)
assert c.execute("SELECT 1 FROM ai_match_report WHERE fixture_id=?", (fx_id,)).fetchone()
print("OK match de coupe réel conservé :", dict(row))

# 2) Vrai fantôme de coupe : remis à jouer, sans toucher aux classements.
before = c.execute("SELECT COALESCE(SUM(played),0) p,COALESCE(SUM(pts),0) pts FROM league_standing").fetchone()
c.execute("INSERT INTO fixture(season,matchday,fixture_date,home_club_id,away_club_id,fixture_type,played,home_goals,away_goals) "
          "VALUES(?,?,?,?,?,'cup',1,2,0)", (season, 102, "2026-10-15", 1, opp_id))
ghost = int(c.execute("SELECT id FROM fixture WHERE fixture_type='cup' ORDER BY id DESC LIMIT 1").fetchone()["id"])
c.commit()
app.repair_phantom_user_fixtures(c)
c.commit()
ghost_row = c.execute("SELECT played FROM fixture WHERE id=?", (ghost,)).fetchone()
after = c.execute("SELECT COALESCE(SUM(played),0) p,COALESCE(SUM(pts),0) pts FROM league_standing").fetchone()
assert int(ghost_row["played"]) == 0
assert int(before["p"]) == int(after["p"]) and int(before["pts"]) == int(after["pts"])
c.close()
print("OK fantôme de coupe remis à jouer sans toucher au classement")

# 3) Sauvegarde déjà touchée par l'ancien bug : un match de coupe remis à jouer
#    mais dont le match_record existe doit être restauré avec son score.
c = app.db()
c.execute("INSERT INTO fixture(season,matchday,fixture_date,home_club_id,away_club_id,fixture_type,played,home_goals,away_goals) "
          "VALUES(?,?,?,?,?,'cup',0,NULL,NULL)", (season, 103, "2026-11-20", opp_id, 1))
lost = int(c.execute("SELECT id FROM fixture WHERE fixture_type='cup' AND fixture_date='2026-11-20' ORDER BY id DESC LIMIT 1").fetchone()["id"])
c.execute("INSERT INTO match_record(season,matchday,home,away,home_goals,away_goals,report,simulation_seed,created_at) "
          "VALUES(?,?,?,?,?,?,?,?,?)", (season, 0, opp_name, me, 1, 4, "rapport coupe", 0, "2026-11-20 20:00"))
# Un amical du même adversaire à une autre date ne doit pas être confondu.
c.execute("INSERT INTO fixture(season,matchday,fixture_date,home_club_id,away_club_id,fixture_type,played) "
          "VALUES(?,?,?,?,?,'cup',0)", (season, 104, "2026-12-20", opp_id, 1))
other = int(c.execute("SELECT id FROM fixture WHERE fixture_type='cup' AND fixture_date='2026-12-20' ORDER BY id DESC LIMIT 1").fetchone()["id"])
c.commit()
app.restore_cup_results_from_records(c); c.commit()
row = c.execute("SELECT played,home_goals,away_goals FROM fixture WHERE id=?", (lost,)).fetchone()
assert int(row["played"]) == 1 and int(row["home_goals"]) == 1 and int(row["away_goals"]) == 4, dict(row)
assert int(c.execute("SELECT played FROM fixture WHERE id=?", (other,)).fetchone()["played"]) == 0
c.close()
print("OK résultat de coupe restauré depuis le match_record")
print("RESULT: ALL OK")
