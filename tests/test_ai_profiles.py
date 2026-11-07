# -*- coding: utf-8 -*-
"""Profils de club : distribution, finances, style, preferences de recrutement."""
import os, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
import ai_finance
from club_profiles import PROFILES, profile_for, signing_score

TMP = tempfile.mkdtemp(prefix="fm_aiprofiles_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP; app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=3,
            identity={"name": "Profiles FC", "arena_name": "A", "color1": "#c47220",
                      "color2": "#14171f", "division": 3})
from PySide6.QtWidgets import QApplication, QDialog
q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
w = app.MainWindow(); w.show(); w.app_stack.setCurrentWidget(w.game_shell); q.processEvents()
w.show_game_message = lambda *a, **k: True
app.QDialog.exec = lambda self, *a, **k: QDialog.Accepted

c = app.db()
profiles = c.execute("SELECT profile,COUNT(*) n FROM club WHERE id<>1 GROUP BY profile").fetchall()
distinct = c.execute("SELECT COUNT(DISTINCT profile) n FROM club WHERE id<>1").fetchone()["n"]
empty = c.execute("SELECT COUNT(*) n FROM club WHERE id<>1 AND COALESCE(profile,'')=''").fetchone()["n"]
manager = c.execute("SELECT profile FROM club WHERE id=1").fetchone()["profile"]
print("profils:", [(r["profile"], r["n"]) for r in profiles], "| distincts", distinct, "| club1", manager)
assert distinct >= 5 and empty == 0 and manager == "Manager"

# Finances : coherence et impact mensuel reel.
club = c.execute("SELECT * FROM club WHERE id<>1 AND division=3 ORDER BY id LIMIT 1").fetchone()
income = ai_finance.monthly_income(c, club)
wages = ai_finance.wage_bill(c, int(club["id"]))
upkeep = ai_finance.upkeep(c, club)
net = ai_finance.monthly_net(c, club)
print(f"{club['name']} [{club['profile']}] revenus={income} salaires={wages} entretien={upkeep} net={net}")
assert income > 0 and wages > 0 and upkeep > 0 and net == income - wages - upkeep
b0 = int(c.execute("SELECT budget FROM club WHERE id=?", (int(club["id"]),)).fetchone()["budget"])
w.process_ai_finances(c, "2026-08-01"); c.commit()
b1 = int(c.execute("SELECT budget FROM club WHERE id=?", (int(club["id"]),)).fetchone()["budget"])
assert b1 == b0 + net, (b0, b1, net)
# Le meme mois ne doit jamais etre paye deux fois (saut de date de cloture).
w.process_ai_finances(c, "2026-08-01"); c.commit()
b2 = int(c.execute("SELECT budget FROM club WHERE id=?", (int(club["id"]),)).fetchone()["budget"])
assert b2 == b1, (b1, b2)

# Pression : budget negatif -> au moins un joueur liste.
c.execute("UPDATE club SET budget=-400000 WHERE id=?", (int(club["id"]),)); c.commit()
w.process_ai_finances(c, "2026-09-01"); c.commit()
listed = c.execute("SELECT COUNT(*) n FROM player WHERE club_id=? AND transfer_listed=1",
                   (int(club["id"]),)).fetchone()["n"]
print("joueurs listes apres decouvert:", listed)
assert listed >= 1

# Style tactique propre au profil (identite complete : les 4 cles historiques
# restent celles du profil, la v2 ajoute mentalite/bloc/largeur/axe/discipline).
style = w.opponent_tactical_identity(int(club["id"]), 3, 50)
print("style:", style)
base_style = PROFILES[club["profile"]]["style"]
for key in ("style", "formation", "pressing", "tempo"):
    assert style[key] == base_style[key], (key, style.get(key), base_style[key])
assert style.get("mentality") in ("Offensive", "Prudente", "Équilibrée")
assert 0.0 < float(style.get("discipline", 0)) <= 1.0

# Preferences : memes joueurs, notes perçues egales -> choix differents.
def fake(age, position, salary=2000):
    return {"age": age, "position": position, "salary": salary}
young = fake(19, "Ailier")
veteran = fake(33, "Défenseur")
star = fake(27, "Pivot", 6000)
formateur = PROFILES["Formateur"]; riche = PROFILES["Riche"]; guerrier = PROFILES["Guerrier"]
score_form_young = signing_score(formateur, young, 13, 2000)
score_rich_young = signing_score(riche, young, 13, 2000)
assert score_form_young > score_rich_young, (score_form_young, score_rich_young)
score_form_old = signing_score(formateur, veteran, 13, 2000)
score_rich_old = signing_score(riche, veteran, 13, 2000)
assert score_form_old < score_rich_old, (score_form_old, score_rich_old)
assert signing_score(riche, star, 17, 6000) > signing_score(formateur, star, 17, 6000)
assert signing_score(guerrier, veteran, 13, 2000) > signing_score(formateur, veteran, 13, 2000)
print("preferences profils: OK")
c.close()
print("RESULT: ALL OK")
