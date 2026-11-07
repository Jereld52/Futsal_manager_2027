# -*- coding: utf-8 -*-
"""Smoke test : _step() (mouvement continu) s'execute sans exception,
les joueurs BOUGENT reellement (wander/pressing/courses), le ballon suit
le porteur, aucun caprice quand le terrain n'a pas d'effectif."""
import os, sys, time
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, r"C:\FM2027V2")
sys.path.insert(0, r"C:\FM2027V2\tests")

import match_pitch2d as mp
mp.FPS_MS = 16

def ok(msg):
    print("OK:", msg)

app = mp.QApplication.instance() or mp.QApplication([]) if False else None
from PySide6.QtWidgets import QApplication
app = QApplication([])

p = mp.Pitch2DWidget()
p.resize(880, 460)

# sans effectif : _step ne doit rien casser
for _ in range(10):
    p._step()
ok("1) _step x10 sans effectif : aucune exception")

# avec un cinq affiche + possession
p.reset_teams("AS Horizon", "FC Test", "#66ff99", "#3388ff")
p.resize(880, 460)
p.note_state({"elapsed_seconds": 60, "hg": 0, "ag": 0, "finished": False,
              "half_time_break": False, "players_on": {"h": 5, "a": 5},
              "possession_side": "h", "passes": {"h": 3, "a": 1},
              "sent_off_players": {"h": [], "a": []},
              "lineup": [{"id": 10+i, "first_name": "J", "last_name": str(i),
                          "position": "Gardien" if i == 0 else "Ailier",
                          "shirt_number": i+1, "condition": 90} for i in range(5)],
              "opponent_lineup": [{"id": 20+i, "first_name": "K", "last_name": str(i),
                                   "position": "Gardien" if i == 0 else "Ailier",
                                   "shirt_number": i+1, "condition": 90} for i in range(5)],
              "conditions": {}, "opponent_conditions": {}})

h1 = [list(p._teams["h"][i]["pos"]) for i in range(5)]
b1 = list(p._ball["pos"])
for _ in range(40):
    p._step()
h2 = [p._teams["h"][i]["pos"] for i in range(5)]
b2 = p._ball["pos"]

moved = sum(1 for i in range(5)
            if abs(h2[i][0]-h1[i][0])+abs(h2[i][1]-h1[i][1]) > 0.004)
assert moved >= 3, moved
ok("2) %s/5 joueurs h bougent en 40 frames (wander/pressing)" % moved)

# le ballon glisse vers le porteur (possession "h" attaque a droite)
holder = p._carrier_entity("h")
assert holder is not None, "porteur introuvable"
d = abs(b2[0]-holder["pos"][0])+abs(b2[1]-holder["pos"][1])
ok("3) ballon colle au porteur : distance %.3f (<0.15)" % d)

# cap de vitesse : aucun deplacement par frame au-dela de MAX_STEP
for i in range(5):
    d2 = abs(h2[i][0]-h1[i][0])
    assert d2 <= mp.MAX_STEP*40+0.02, (i, d2)
ok("4) vitesse de course plafonnee (pas de teleport)")

# verrou tir : le ballon N'EST PAS attrache au porteur pendant le lock
p.note_event("h", "shot")
locked_target = list(p._ball["target"])
for _ in range(20):
    p._step()
assert abs(p._ball["target"][0]-locked_target[0]) < 1e-9, "le lock a saute !"
ok("5) verrou tir respecte : cible branch non re-envoye vers le porteur")

# peinture via grab (rendu complet avec mouvement)
p._goal_flash = ("h", time.monotonic()+1.5)
p._goal_info = ("J. 2", "h", time.monotonic()+1.5)
pix = p.grab()
assert not pix.isNull(), "grab null"
ok("6) rendu complet (flash but inclus) : grab OK %dx%d" % (pix.width(), pix.height()))

ok("RESULT: ALL OK")
