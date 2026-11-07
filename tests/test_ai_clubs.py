# -*- coding: utf-8 -*-
"""Socles des clubs IA : projets, besoins, marche et changement d'entraîneur."""
import os, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app, ai_clubs

TMP = tempfile.mkdtemp(prefix="fm_aiclubs_test_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP; app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=3,
            identity={"name": "Plan FC", "arena_name": "Halle", "color1": "#c47220",
                      "color2": "#14171f", "division": 3})

conn = app.db()

# 1) Tous les clubs IA ont un projet complet et une identité stable.
plans = conn.execute("""SELECT p.*,c.name,c.division,c.profile
                        FROM ai_club_plan p JOIN club c ON c.id=p.club_id
                        ORDER BY c.division,c.id""").fetchall()
ai_count = int(conn.execute("SELECT COUNT(*) n FROM club WHERE id<>1").fetchone()["n"])
print("projets:", len(plans), "/", ai_count)
assert len(plans) == ai_count
labels = set(r["activity"] for r in plans)
print("dynamiques:", {label: sum(1 for r in plans if r["activity"] == label) for label in labels})
assert labels <= {"Animé", "Équilibré", "Prudent"}
assert "Animé" in labels and "Prudent" in labels, "le monde doit rester mixte"
assert all(str(r["manager_name"] or "").strip() for r in plans)
assert all(1 <= int(r["objective_rank"] or 0) <= 12 for r in plans)
assert all(20 <= int(r["patience"] or 0) <= 95 for r in plans)

sample = plans[0]
cid = int(sample["club_id"])
plan = ai_clubs.plan_for(conn, cid)
assert plan and plan["needs"], "besoins absents"
print("exemple:", sample["name"], "|", plan["ambition"], plan["objective_rank"],
      "|", plan["activity"], "|", plan["manager_name"], plan["manager_style"])
print("besoins:", plan["needs"])
assert all(item.get("position") and item.get("priority") in ("Haute", "Moyenne", "Basse")
           for item in plan["needs"])
assert ai_clubs.plan_for(conn, cid)["manager_name"] == plan["manager_name"]

# 2) Le comportement de marché suit la dynamique du club.
for row in plans:
    club = conn.execute("SELECT * FROM club WHERE id=?", (int(row["club_id"]),)).fetchone()
    behavior = ai_clubs.transfer_behavior(conn, club)
    if row["activity"] == "Animé":
        assert behavior["market_chance"] >= 0.80 and behavior["fee_multiplier"] > 1.0
    elif row["activity"] == "Prudent":
        assert behavior["market_chance"] <= 0.40 and behavior["fee_multiplier"] < 1.0
    else:
        assert 0.5 <= behavior["market_chance"] <= 0.7
print("comportements de marché : OK")

# 3) Fin de saison : un club très en dessous de son objectif peut changer d'entraîneur.
target = conn.execute("""SELECT p.*,c.name FROM ai_club_plan p JOIN club c ON c.id=p.club_id
                         WHERE p.club_id<>1 ORDER BY p.objective_rank DESC LIMIT 1""").fetchone()
tcid = int(target["club_id"])
conn.execute("UPDATE ai_club_plan SET objective_rank=1,patience=5 WHERE club_id=?", (tcid,))
old_manager = ai_clubs.plan_for(conn, tcid)["manager_name"]
tables = {1: [{"id": 1}] + [{"id": int(r["club_id"])} for r in plans if int(r["club_id"]) != tcid] + [{"id": tcid}]}
_orig_random = ai_clubs.random.random
ai_clubs.random.random = lambda: 0.0
class _Host:
    def log_error(self, *args, **kwargs):
        pass
try:
    sacked = ai_clubs.finalize_season(_Host(), conn, tables, {}, 1)
finally:
    ai_clubs.random.random = _orig_random
new_manager = ai_clubs.plan_for(conn, tcid)["manager_name"]
print("entraîneur:", old_manager, "->", new_manager, "| changements:", sacked)
assert sacked >= 1
assert new_manager and new_manager != old_manager
hist = conn.execute("SELECT COUNT(*) n FROM ai_manager_history WHERE club_id=?", (tcid,)).fetchone()["n"]
assert hist >= 1

# 4) Nouvelle saison : les projets sont reconstruits sans changer un entraîneur conservé.
keep = plans[1]
kcid = int(keep["club_id"])
keep_manager = ai_clubs.plan_for(conn, kcid)["manager_name"]
conn.execute("UPDATE club SET season=2")
conn.execute("UPDATE club SET division=? WHERE id=?",
             (5 if int(keep["division"]) != 5 else 4, kcid))
created = ai_clubs.ensure_plans(conn, "2027-07-01", force=True, announce=False)
assert created >= 1
rebuilt = ai_clubs.plan_for(conn, kcid)
print("projet reconstruit:", rebuilt["season"], rebuilt["ambition"], rebuilt["manager_name"])
assert rebuilt["season"] == 2
assert rebuilt["manager_name"] == keep_manager
conn.execute("UPDATE club SET season=1")

# 5) Fiche club : le bloc PROJET est visible pour un club IA.
conn.commit(); conn.close()
from PySide6.QtWidgets import QApplication, QDialog, QLabel
q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
w = app.MainWindow(); w.resize(1280, 800); w.show()
w.app_stack.setCurrentWidget(w.game_shell); q.processEvents()

# 4b) Board du club du joueur : même langage que les projets IA.
conn = app.db()
club0 = conn.execute("SELECT * FROM club WHERE id=1").fetchone()
w.ensure_board_objectives(conn, club0)
label_row = conn.execute("SELECT value FROM meta WHERE key='board_objective_label'").fetchone()
target_row = conn.execute("SELECT value FROM meta WHERE key='board_objective_rank'").fetchone()
print("objectif board:", label_row["value"] if label_row else None,
      "top", target_row["value"] if target_row else None)
assert label_row and str(label_row["value"] or "") in ("Titre", "Montée", "Haut de tableau", "Milieu de tableau", "Maintien")
assert target_row and 1 <= int(target_row["value"] or 0) <= 12

# 4c) Les offres vers le manager expliquent le projet de l'acheteur.
import random, json
from datetime import date, timedelta
random.seed(11)
listed = conn.execute("SELECT id FROM player WHERE club_id=1 AND COALESCE(is_free_agent,0)=0 LIMIT 1").fetchone()
conn.execute("UPDATE player SET transfer_listed=1 WHERE id=?", (int(listed["id"]),))
conn.commit()
for day in range(1, 50):
    w.generate_transfer_interest(conn, (date(2026, 9, 1) + timedelta(days=day)).isoformat())
rows = conn.execute("SELECT action_data FROM manager_message WHERE kind='transfer_sale'").fetchall()
stories = []
for row in rows:
    try:
        data = json.loads(row["action_data"] or "{}")
    except Exception:
        continue
    if data.get("interest_reason"):
        stories.append(data["interest_reason"])
print("offres motivées:", len(stories), "|", stories[:2])
assert stories, "les offres doivent être reliées au projet du club acheteur"
conn.close()
captured = []
def _exec(self, *a, **k):
    self.resize(1020, 820); self.show(); QApplication.processEvents()
    captured.append(self); return QDialog.Rejected
app.QDialog.exec = _exec
w.show_club_profile(cid); q.processEvents()
dlg = captured[-1]
texts = [l.text() for l in dlg.findChildren(QLabel)]
assert {"PROJET", "ENTRAÎNEUR", "DYNAMIQUE", "BESOINS"} <= set(texts), texts[:20]
print("fiche club : bloc projet OK")
dlg.close()
print("RESULT: ALL OK")
