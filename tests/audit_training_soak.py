# -*- coding: utf-8 -*-
"""Soak entraînement : 60 jours de séances, progression et plafonds.

Vérifie que la progression reste bornée au potentiel, que les journaux ne
contiennent que des gains +1 (hors inactivité -1), que l'UI affiche des totaux
cohérents et que la fatigue/forme restent dans les bornes.
"""
import os, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication

DAYS = int(os.environ.get("SOAK_DAYS", "60"))

TMP = tempfile.mkdtemp(prefix="fm_trainsoak_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP
app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=2,
            identity={"name": "Soak FC", "arena_name": "A", "color1": "#2f6fed",
                      "color2": "#101a2e", "division": 2})

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
app.QDialog.exec = lambda self, *a, **k: 1
w = app.MainWindow()
w.setAttribute(app.Qt.WA_DontShowOnScreen, True)
w.show_game_message = lambda *a, **k: True
w.resize(1400, 900)
w.show(); q.processEvents()
w.app_stack.setCurrentWidget(w.game_shell)

# Deux groupes : focus manuel « défense » / auto.
c = app.db()
squad = c.execute("SELECT id FROM player WHERE club_id=1 ORDER BY id").fetchall()
for i, row in enumerate(squad):
    if i % 2 == 0:
        c.execute("UPDATE player SET training_focus='defense' WHERE id=?", (int(row["id"]),))
# 60 jours de séances « Défense », normales.
start = app.parse_iso(w._career_day())
for d in range(DAYS):
    day = (start + app.timedelta(days=d)).isoformat()
    c.execute("INSERT INTO training_session(focus,planned_date,activity_key,intensity,quality,created_at,completed) "
              "VALUES(?,?,?,?,?,?,0)",
              ("Défense", day, "Défense", "Normale", 100, day))
c.commit(); c.close()

before = app.db()
caps = {int(r["id"]): int(round(app.player_potential_from_row(r))) * 5
        for r in before.execute("SELECT * FROM player WHERE club_id=1").fetchall()}
initial = {int(r["id"]): {k: int(r[k] or 0) for k in app.TRAINING_ATTRIBUTE_LABELS}
           for r in before.execute("SELECT * FROM player WHERE club_id=1").fetchall()}
before.close()

w.advance_calendar_days(DAYS)
q.processEvents()

c = app.db()
players = c.execute("SELECT * FROM player WHERE club_id=1").fetchall()
issues = []
for p in players:
    pid = int(p["id"]); cap = caps[pid]; ini = initial[pid]
    for key in app.TRAINING_ATTRIBUTE_LABELS:
        value = int(p[key] or 0)
        # Un attribut déjà au-dessus du plafond à la création ne doit pas bouger ;
        # sous le plafond, il ne doit jamais le dépasser.
        if ini[key] < cap and value > cap:
            issues.append(f"{p['first_name']} {p['last_name']} : {key} {value} > plafond {cap}")
        if ini[key] >= cap and value > ini[key]:
            issues.append(f"{p['first_name']} {p['last_name']} : {key} progresse au-delà du plafond")
    if not (0 <= int(p["condition"] or 0) <= 100):
        issues.append(f"condition hors bornes pour {pid}: {p['condition']}")
    if not (0 <= int(p["morale"] or 0) <= 100):
        issues.append(f"moral hors bornes pour {pid}: {p['morale']}")
    if int(p["injury_days"] or 0) < 0 or int(p["injury_matches"] or 0) < 0:
        issues.append(f"blessure négative pour {pid}")

bad_delta = c.execute("""SELECT COUNT(*) n FROM player_training_log t
                         JOIN player p ON p.id=t.player_id
                         WHERE p.club_id=1 AND t.delta NOT IN (-1,1)""").fetchone()["n"]
if int(bad_delta):
    issues.append(f"{bad_delta} delta(s) de journal hors -1/+1 pour le club")

season_start = w._season_start_for(w._career_day()).isoformat()
gains = c.execute("""SELECT SUM(CASE WHEN t.delta>0 THEN t.delta ELSE 0 END) g,
                            SUM(CASE WHEN t.delta<0 THEN -t.delta ELSE 0 END) p
                     FROM player_training_log t JOIN player p ON p.id=t.player_id
                     WHERE p.club_id=1 AND t.created_at>=?""", (season_start,)).fetchone()
total_gain = int(gains["g"] or 0); total_loss = int(gains["p"] or 0)
if total_gain <= 0:
    issues.append("aucun gain sur la période")
user_rows = c.execute("""SELECT SUM(CASE WHEN delta>0 THEN delta ELSE 0 END) g
                         FROM player_training_log WHERE player_id=?""", (int(squad[0]["id"]),)).fetchone()["g"]
c.close()

# UI : le KPI doit refléter exactement les gains positifs.
w.show_page(4); q.processEvents()
w.training_tabs.setCurrentIndex(2); q.processEvents()
kpi = w.training_evo_kpi_total[1].text()
if kpi != f"{total_gain} PTS":
    issues.append(f"KPI {kpi} != gains {total_gain}")
neg = [lbl.text() for card in w.training_evo_cards for lbl in card.findChildren(app.QLabel)
       if lbl.text().startswith("-")]
if neg:
    issues.append(f"valeurs négatives affichées : {neg[:3]}")

# Effet du focus : la probabilité par séance est ~2,2x supérieure.
p_auto = app.training_growth_probability(70, "Normale", 0.62, 22, 0.8, 1.0)
p_focus = app.training_growth_probability(70, "Normale", 0.62 * 2.2, 22, 0.8, 1.0)
ratio = p_focus / p_auto if p_auto else 0
if abs(ratio - 2.2) > 0.01:
    issues.append(f"ratio focus {ratio:.2f} != 2.2")

print(f"jours simulés : {DAYS} | gains {total_gain} | pertes {total_loss} | KPI {kpi}")
print(f"ratio focus/auto : {ratio:.2f} | ex. joueur suivi : +{int(user_rows or 0)}")
if issues:
    print("PROBLEMES:")
    for i in issues:
        print(" -", i)
    raise SystemExit(1)

w.close(); q.processEvents()
size = os.path.getsize(r"C:\FM2027V2\data\error.log")
assert size == 0, size
print("RESULT: ALL OK")
