# -*- coding: utf-8 -*-
"""Filière de formation : promotion annuelle, détection, progression, plafonds.

Couvre :
  1. Promotion annuelle du centre (1-3 jeunes, 15-17 ans, profils et plafonds).
  2. Campus fermé : aucune promotion.
  3. Investissement de saison : +8 de note, consommé une seule fois.
  4. Entraînement quotidien : un U18 du centre progresse plus vite qu'un senior,
     et plus vite quand le campus est ouvert.
  5. Développement hebdomadaire : les jeunes montent, les 34 ans régressent
     physiquement, jamais au-delà du potentiel.
"""
import os
import random
import sys
import tempfile
from datetime import timedelta

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication

TMP = tempfile.mkdtemp(prefix="fm_acadpipe_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP
app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=3,
            identity={"name": "Pipeline FC", "arena_name": "A", "color1": "#c47220",
                      "color2": "#14171f", "division": 3})

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
app.QDialog.exec = lambda self, *a, **k: 1
w = app.MainWindow()
w.setAttribute(app.Qt.WA_DontShowOnScreen, True)
w.show_game_message = lambda *a, **k: True
w.resize(1400, 900)
w.show(); q.processEvents()
w.app_stack.setCurrentWidget(w.game_shell)

c = app.db()
c.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('academy_unlocked','1')")
c.execute("UPDATE facility SET youth_level=6 WHERE id=1")
c.execute("UPDATE club SET budget=8000000 WHERE id=1")
c.commit(); c.close()

POSITIONS = {"Gardien", "Défenseur", "Ailier", "Pivot", "Universel"}


def max_player_id():
    c = app.db(); n = int(c.execute("SELECT COALESCE(MAX(id),0) m FROM player").fetchone()["m"]); c.close()
    return n


def new_players(after_id):
    c = app.db()
    rows = c.execute("SELECT * FROM player WHERE id>?", (after_id,)).fetchall()
    c.close()
    return rows


# ---------------- 1) Promotion annuelle ----------------
before = max_player_id()
c = app.db(); w.process_academy_intake(c, 2); c.commit(); c.close()
promo = new_players(before)
assert 1 <= len(promo) <= 3, len(promo)
c = app.db()
for p in promo:
    pot = int(p["potential_fixed"] or 0)
    assert int(p["club_id"]) == 1
    assert 15 <= int(p["age"]) <= 17, (p["first_name"], p["age"])
    assert str(p["position"]) in POSITIONS, p["position"]
    assert 1 <= pot <= 20, pot
    assert int(p["contract_years"]) == 3, p["contract_years"]
    assert int(p["salary"] or 0) > 0
    assert 85 <= int(p["condition"]) <= 100 and 62 <= int(p["morale"]) <= 84
    for key in app.TRAINING_ATTRIBUTE_LABELS:
        assert int(p[key] or 0) <= pot * 5, (p["first_name"], key, p[key], pot)
    hist = c.execute("SELECT COUNT(*) n FROM player_history WHERE player_id=? AND kind='formation'",
                     (int(p["id"]),)).fetchone()["n"]
    assert hist >= 1, "historique de formation manquant"
shirts = c.execute("""SELECT shirt_number, COUNT(*) n FROM player WHERE club_id=1 AND shirt_number>0
                      GROUP BY shirt_number HAVING n>1""").fetchall()
news = c.execute("SELECT title,body FROM news WHERE title='Centre de formation' ORDER BY id DESC LIMIT 1").fetchone()
c.close()
assert not shirts, [dict(r) for r in shirts]
assert news and "Promotion 2" in news["body"], news["body"] if news else None
print("1) promotion:", len(promo), "jeunes |", ", ".join(
    f"{p['first_name']} {p['last_name']} {p['age']}a {p['position']} pot {p['potential_fixed']}/20" for p in promo))

# ---------------- 2) Campus fermé : aucune promotion ----------------
c = app.db(); c.execute("UPDATE meta SET value='0' WHERE key='academy_unlocked'"); c.commit(); c.close()
before = max_player_id()
c = app.db(); w.process_academy_intake(c, 3); c.commit(); c.close()
assert not new_players(before), "promotion générée avec le campus fermé"
print("2) campus fermé: aucune promotion")

# ---------------- 3) Investissement de saison : +8 et consommation ----------------
c = app.db()
c.execute("UPDATE meta SET value='1' WHERE key='academy_unlocked'")
season = int(c.execute("SELECT season FROM club WHERE id=1").fetchone()["season"] or 1)
c.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('academy_invest_season',?)", (str(season),))
c.commit(); c.close()
before = max_player_id()
c = app.db(); w.process_academy_intake(c, 4); c.commit(); c.close()
promo_boost = new_players(before)
c = app.db()
invest = c.execute("SELECT value FROM meta WHERE key='academy_invest_season'").fetchone()
news = c.execute("SELECT body FROM news WHERE title='Centre de formation' ORDER BY id DESC LIMIT 1").fetchone()
c.close()
assert promo_boost, "aucune promotion avec investissement"
assert invest is None, "investissement non consommé"
assert news and "investissement +8" in news["body"], news["body"] if news else None
print("3) investissement: +8 appliqué et consommé")


# ---------------- helpers joueurs ----------------
def make_player(first, last, age, potential=20, base=40, position="Universel"):
    c = app.db()
    shirt = int(c.execute("SELECT COALESCE(MAX(shirt_number),0) v FROM player WHERE club_id=1").fetchone()["v"]) + 1
    c.execute("""INSERT INTO player(club_id,first_name,last_name,age,position,technique,passing,finishing,
                                     defense,goalkeeper,stamina,condition,morale,nationality,salary,contract_years,
                                     market_value,is_free_agent,shirt_number,dribble,speed,positioning,potential_fixed)
                 VALUES(1,?,?,?,?,?,?,?,?,?,?,?,?,'Française',1500,3,20000,0,?,?,?,?,?)""",
              (first, last, age, position, base, base, base, base, 20, 60, 100, 70, shirt,
               base, base, base, potential))
    c.commit()
    pid = int(c.execute("SELECT id FROM player ORDER BY id DESC LIMIT 1").fetchone()["id"])
    c.close()
    return pid


def reset_conditions(pids):
    c = app.db()
    for pid in pids:
        c.execute("UPDATE player SET condition=100, injury_days=0, injury_matches=0 WHERE id=?", (pid,))
    c.commit(); c.close()


def train(days, pids=(), activity="Technique", intensity="Faible"):
    start = app.parse_iso(w._career_day())
    for d in range(days):
        day = (start + timedelta(days=d)).isoformat()
        c = app.db()
        c.execute("INSERT INTO training_session(focus,planned_date,activity_key,intensity,quality,created_at,completed) "
                  "VALUES(?,?,?,?,100,?,0)", (activity, day, activity, intensity, day))
        c.commit(); c.close()
        c = app.db(); w.apply_training_schedule(c, day); c.commit(); c.close()
        if pids:
            reset_conditions(pids)


def gains(pid, since):
    c = app.db()
    n = int(c.execute("""SELECT COALESCE(SUM(CASE WHEN delta>0 THEN delta ELSE 0 END),0) g
                         FROM player_training_log WHERE player_id=? AND created_at>=?""",
                      (pid, since)).fetchone()["g"] or 0)
    c.close()
    return n


# ---------------- 4) Entraînement quotidien : centre vs senior ----------------
young = make_player("Jeune", "Centre", 17)
senior = make_player("Vieux", "Briscard", 27)
ids = (young, senior)
season_start = w._season_start_for(w._career_day()).isoformat()
c = app.db()
c.execute("UPDATE meta SET value='1' WHERE key='academy_unlocked'")
c.execute("UPDATE facility SET youth_level=8 WHERE id=1")
c.commit(); c.close()
random.seed(4242)
train(200, ids)
y_gain = gains(young, season_start)
s_gain = gains(senior, season_start)
print(f"4) quotidien (centre ouvert): U18 +{y_gain} | senior +{s_gain}")
assert y_gain > s_gain, ("le U18 doit progresser plus que le senior", y_gain, s_gain)
# Facteur académie déterministe : le U18 du centre progresse ~2x plus vite.
p_closed = app.training_growth_probability(100, "Faible", 0.62, 17, 1.0, 0.85)
p_open = app.training_growth_probability(100, "Faible", 0.62, 17, 1.0, 1.70)
assert p_open > p_closed * 1.5, (p_closed, p_open)
print(f"   facteur académie: {p_closed:.4f} -> {p_open:.4f} par séance")

# ---------------- 5) Développement hebdomadaire ----------------
young2 = make_player("Pousse", "Rapide", 17, potential=20, base=30)
veteran = make_player("Ancien", "Cadre", 34, potential=14, base=70)
c = app.db()
lvl0 = app.player_level_from_row(c.execute("SELECT * FROM player WHERE id=?", (young2,)).fetchone())
v_sta0 = int(c.execute("SELECT stamina FROM player WHERE id=?", (veteran,)).fetchone()["stamina"])
c.close()
random.seed(7)
day = app.parse_iso(w._career_day())
for wk in range(30):
    c = app.db(); w.process_player_development(c, (day + timedelta(days=7 * wk)).isoformat()); c.commit(); c.close()
c = app.db()
yrow = c.execute("SELECT * FROM player WHERE id=?", (young2,)).fetchone()
vrow = c.execute("SELECT * FROM player WHERE id=?", (veteran,)).fetchone()
lvl1 = app.player_level_from_row(yrow)
v_sta1 = int(vrow["stamina"])
y_gain = int(c.execute("""SELECT COALESCE(SUM(CASE WHEN delta>0 THEN delta ELSE 0 END),0) g
                          FROM player_training_log WHERE player_id=? AND activity_key='Développement'""",
                       (young2,)).fetchone()["g"] or 0)
v_loss = int(c.execute("""SELECT COALESCE(SUM(CASE WHEN delta<0 THEN -delta ELSE 0 END),0) g
                          FROM player_training_log WHERE player_id=? AND activity_key='Vieillissement'""",
                       (veteran,)).fetchone()["g"] or 0)
cap = int(yrow["potential_fixed"] or 0) * 5
over = [k for k in app.TRAINING_ATTRIBUTE_LABELS if int(yrow[k] or 0) > cap]
prog = c.execute("SELECT * FROM player_dev_progress WHERE player_id=?", (young2,)).fetchone()
c.close()
assert lvl1 > lvl0, (lvl0, lvl1)
assert y_gain > 10, y_gain
assert v_loss >= 5, v_loss
assert v_sta1 < v_sta0, (v_sta0, v_sta1)
assert not over, over
assert prog is not None
print(f"5) hebdo: U18 {lvl0:.1f}->{lvl1:.1f}/20 (+{y_gain} pts) | vétéran {v_loss} régressions "
      f"(endurance {v_sta0}->{v_sta1})")

w.close(); q.processEvents()
size = os.path.getsize(r"C:\FM2027V2\data\error.log")
assert size == 0, size
print("RESULT: ALL OK")
