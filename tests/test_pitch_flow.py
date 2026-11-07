# -*- coding: utf-8 -*-
"""Rendu 2D : mouvement continu (vitesse bornée), ballon physique, cadence."""
import os, sys, math
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
from PySide6.QtWidgets import QApplication
from match_pitch2d import Pitch2DWidget

q = QApplication.instance() or QApplication([])
w = Pitch2DWidget()
w.resize(860, 430)
w.show()
q.processEvents()
w.reset_teams("DOM", "EXT", "#2f6fed", "#c47220")


def people(prefix):
    out = [{"id": 100 + (0 if prefix == "h" else 50), "first_name": "G", "last_name": "K",
            "position": "Gardien", "shirt_number": 1, "condition": 85,
            "first_name": "G", "last_name": "K"}]
    for i in range(4):
        out.append({"id": 101 + i + (0 if prefix == "h" else 50), "first_name": "J",
                    "last_name": f"{prefix}{i}", "position": ["Défenseur", "Ailier", "Pivot", "Universel"][i],
                    "shirt_number": 2 + i, "condition": 85})
    return out


state = {"elapsed_seconds": 300, "hg": 0, "ag": 0, "is_home": True,
         "lineup": people("h"), "opponent_lineup": people("a"),
         "possession_side": "h", "passes": {"h": 1, "a": 0},
         "players_on": {"h": 5, "a": 5}, "conditions": {}, "opponent_conditions": {},
         "finished": False, "half_time_break": False}
w.note_state(state, animate=True)
for _ in range(24):
    w._step()

positions = [list(e["pos"]) for e in w._teams["h"]]
assert all(0.0 <= x <= 1.0 and 0.0 <= y <= 1.0 for x, y in positions), positions
print("OK placements :", [(round(x, 2), round(y, 2)) for x, y in positions[:3]])

# Le ballon part vers le but adverse, sans saut brutal.
w.note_event("h", "shot", "Test frappe")
prev = list(w._ball["pos"])
steps = []
for _ in range(40):
    w._step()
    cur = w._ball["pos"]
    steps.append(math.hypot(cur[0] - prev[0], cur[1] - prev[1]))
    prev = list(cur)
assert steps and max(steps) < 0.07, max(steps)
assert w._ball["pos"][0] > 0.55, w._ball["pos"]
print("OK ballon :", [round(v, 2) for v in w._ball["pos"]],
      "| pas max", round(max(steps), 4))

# Aucun joueur ne se téléporte d'une frame à l'autre.
for _ in range(30):
    before = [list(e["pos"]) for e in w._teams["h"]]
    w._step()
    after = [list(e["pos"]) for e in w._teams["h"]]
    for (x1, y1), (x2, y2) in zip(before, after):
        assert abs(x2 - x1) + abs(y2 - y1) < 0.05, (x1, y1, x2, y2)
print("OK joueurs : pas de saut > 0,05 par frame")

# Cadence : les verrous d'action suivent la vitesse de simulation.
w.set_pace(140)
fast = w._pace_k
w.set_pace(900)
slow = w._pace_k
assert fast < 0.4 < 1.0 < slow, (fast, slow)
print("OK cadence : 5x =", round(fast, 2), "| 1x =", round(slow, 2))

# Passe nommée : le ballon vise le joueur cité.
w.set_pace(600)
w.note_event("h", "pass", "J h0 → J h2")
target = w._ball["target"]
receiver = w._entity_by_name("h", "J h2")
assert receiver is not None
assert abs(target[0] - (receiver["pos"][0] + 0.045)) < 0.08
print("OK passe nommée : cible vers", receiver["name"])

# Rendu complet sans exception.
img = w.grab().toImage()
assert not img.isNull()
print("RESULT: ALL OK")
