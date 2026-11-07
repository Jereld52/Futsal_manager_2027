# -*- coding: utf-8 -*-
"""Scénarios extrêmes : forfaits, effectif décimé, club change mi-saison."""
import os, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication

TMP = tempfile.mkdtemp(prefix="fm_scen_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP; app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=3,
            identity={"name": "Scen FC", "arena_name": "A", "color1": "#2f6fed",
                      "color2": "#101a2e", "division": 3})

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
w = app.MainWindow()
w.setAttribute(app.Qt.WA_DontShowOnScreen, True)
w.show_game_message = lambda *a, **k: True
app.QDialog.exec = lambda self, *a, **k: 1
w.resize(1400, 900); w.show(); q.processEvents()
w.app_stack.setCurrentWidget(w.game_shell); q.processEvents()

c = app.db()
# Match IA à venir, hors club du joueur.
fx = c.execute("""SELECT * FROM fixture WHERE played=0 AND COALESCE(fixture_type,'championship')='championship'
                  AND home_club_id<>1 AND away_club_id<>1 ORDER BY fixture_date, id LIMIT 1""").fetchone()
assert fx is not None, "aucun match IA à venir"
home_id, away_id = int(fx["home_club_id"]), int(fx["away_club_id"])
md, date = int(fx["matchday"]), str(fx["fixture_date"])
print("match test :", home_id, "vs", away_id, "| J", md, date)

# 1) Effectif décimé : tous blessés + aucun libre recrutable -> forfait.
c.execute("UPDATE player SET injury_days=60 WHERE club_id=?", (home_id,))
c.execute("UPDATE player SET is_free_agent=0 WHERE is_free_agent=1")
c.commit()
w._simulate_other_fixtures(c, md, today=date)
c.commit()
row = c.execute("SELECT played,home_goals,away_goals FROM fixture WHERE id=?", (int(fx["id"]),)).fetchone()
assert int(row["played"]) == 1, dict(row)
assert (int(row["home_goals"]), int(row["away_goals"])) == (0, 3), dict(row)
rep = c.execute("SELECT scorers FROM ai_match_report WHERE fixture_id=?", (int(fx["id"]),)).fetchone()
assert rep and "forfait" in str(rep["scorers"]).lower(), rep["scorers"] if rep else None
st = c.execute("SELECT * FROM league_standing WHERE club_id=?", (away_id,)).fetchone()
assert int(st["wins"]) == 1 and int(st["pts"]) == 3, dict(st)
left = c.execute("SELECT COUNT(*) n FROM player WHERE club_id=? AND COALESCE(retired,0)=0", (home_id,)).fetchone()["n"]
assert left >= 5, left
print("OK forfait domicile 0-3, classement adverse +3, effectif conservé :", left)

# 2) Le même club refait forfait à la journée suivante sans planter.
nxt = c.execute("""SELECT * FROM fixture WHERE played=0 AND COALESCE(fixture_type,'championship')='championship'
                   AND (home_club_id=? OR away_club_id=?) ORDER BY fixture_date, id LIMIT 1""",
                (home_id, home_id)).fetchone()
if nxt is not None:
    w._simulate_other_fixtures(c, int(nxt["matchday"]), today=str(nxt["fixture_date"]))
    c.commit()
    r2 = c.execute("SELECT played FROM fixture WHERE id=?", (int(nxt["id"]),)).fetchone()
    assert int(r2["played"]) == 1
    print("OK second forfait joué sans erreur")

# 3) Changement de club en cours de saison : le monde reste cohérent.
target = c.execute("SELECT id,name,division FROM club WHERE id<>1 ORDER BY id LIMIT 1").fetchone()
ok = w.change_manager_club(int(target["id"]))
assert ok is True, "bascule refusée"
c.close()
c = app.db()
dup = c.execute("SELECT COUNT(*) n, COUNT(DISTINCT id) d FROM club").fetchone()
assert int(dup["n"]) == int(dup["d"]), dict(dup)
one = c.execute("SELECT COUNT(*) n FROM club WHERE id=1").fetchone()["n"]
assert int(one) == 1
squad = c.execute("SELECT COUNT(*) n FROM player WHERE club_id=1 AND COALESCE(is_free_agent,0)=0").fetchone()["n"]
assert 5 <= int(squad) <= 30, squad
dups = c.execute("""SELECT club_id, COUNT(*) n FROM league_standing GROUP BY club_id HAVING n>1""").fetchall()
assert not dups, [dict(r) for r in dups]
# Un match du nouveau club se joue sans erreur : on avance jusqu'à sa date.
today_fx = None
for _ in range(100):
    c2 = app.db()
    today_fx = w._today_fixture_for_user(c2)
    c2.close()
    if today_fx is not None:
        break
    w.advance_calendar_days(1)
    q.processEvents()
if today_fx is None:
    c2 = app.db()
    today_fx = w._today_fixture_for_user(c2)
    c2.close()
if today_fx is not None:
    w.start_match(); w.finish_match_now(); q.processEvents()
    r3 = c.execute("SELECT played,home_goals,away_goals FROM fixture WHERE id=?", (int(today_fx["id"]),)).fetchone()
    assert int(r3["played"]) == 1, dict(r3)
    print("OK match après changement de club :", dict(r3))
else:
    print("(pas de match à venir pour le nouveau club)")
c.close()
w.close(); q.processEvents()
size = os.path.getsize(os.path.join(r"C:\FM2027V2\data", "error.log"))
assert size == 0, f"error.log {size} octets"
print("error.log : 0 octet")
print("RESULT: ALL OK")
