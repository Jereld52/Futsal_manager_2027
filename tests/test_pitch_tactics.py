# -*- coding: utf-8 -*-
"""Terrain 2D : lecture réelle des tactiques, phases de construction et attributs."""
import copy
import os
import sys
import time

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
from PySide6.QtWidgets import QApplication
from match_pitch2d import Pitch2DWidget, FORMATION_SLOTS

q = QApplication.instance() or QApplication([])


def people(prefix, speed=70, passing=70, dribble=70, positioning=70):
    out = [{"id": 100 + (0 if prefix == "h" else 50), "first_name": "G", "last_name": "K",
            "position": "Gardien", "shirt_number": 1, "condition": 88,
            "speed": speed, "passing": passing, "dribble": dribble,
            "positioning": positioning, "technique": 70, "finishing": 55,
            "defense": 65, "stamina": 75}]
    for i in range(4):
        out.append({"id": 101 + i + (0 if prefix == "h" else 50), "first_name": "J",
                    "last_name": f"{prefix}{i}",
                    "position": ["Défenseur", "Ailier", "Pivot", "Universel"][i],
                    "shirt_number": 2 + i, "condition": 88,
                    "speed": speed, "passing": passing, "dribble": dribble,
                    "positioning": positioning, "technique": 70, "finishing": 55,
                    "defense": 65, "stamina": 75})
    return out


def state(tactics=None, h_people=None, a_people=None):
    return {"elapsed_seconds": 300, "hg": 0, "ag": 0, "is_home": True,
            "lineup": h_people or people("h"), "opponent_lineup": a_people or people("a"),
            "possession_side": "h", "passes": {"h": 1, "a": 0},
            "players_on": {"h": 5, "a": 5}, "conditions": {}, "opponent_conditions": {},
            "finished": False, "half_time_break": False,
            "tactics_2d": tactics or {
                "h": {"pressing": 1, "mentality": 0, "preset": "equilibre",
                      "formation": "2-2", "style": "equilibre", "block": "Médian",
                      "width": "Normale", "focus": "Axe", "tempo": "Normal"},
                "a": {"pressing": 1, "mentality": 0, "preset": "equilibre",
                      "formation": "2-2", "style": "equilibre", "block": "Médian",
                      "width": "Normale", "focus": "Axe", "tempo": "Normal"}}}


w = Pitch2DWidget(); w.resize(880, 460); w.show(); q.processEvents()
w.reset_teams("Tactique FC", "Bloc FC", "#2f6fed", "#c47220")

# 1) Formation réellement lue et appliquée aux slots.
st = state()
w.note_state(st, animate=True)
slot_2_2 = tuple(w._teams["h"][1]["slot"])
st4 = state(tactics={"h": {"formation": "4-0", "preset": "possession", "pressing": 2,
                            "mentality": 2, "block": "Haut", "width": "Large",
                            "focus": "Ailes", "tempo": "Rapide"},
                     "a": {"formation": "1-2-1", "preset": "contre", "pressing": 0,
                            "mentality": 1, "block": "Bas", "width": "Étroite",
                            "focus": "Axe", "tempo": "Patient"}})
w.note_state(st4, animate=True)
assert tuple(w._teams["h"][1]["slot"]) == FORMATION_SLOTS["4-0"][1], w._teams["h"][1]["slot"]
assert tuple(w._teams["h"][1]["slot"]) != slot_2_2
assert tuple(w._teams["a"][1]["slot"]) == (1.0 - FORMATION_SLOTS["1-2-1"][1][0], 1.0 - FORMATION_SLOTS["1-2-1"][1][1])
print("1) formations lues : 2-2 ->", slot_2_2, "| 4-0 ->", w._teams["h"][1]["slot"])

# 2) Largeur / axe : les cibles latérales changent réellement.
w._possession = "h"
w._tactics["h"]["width"] = "Large"; w._tactics["h"]["focus"] = "Ailes"
w._aim_slot("h", 1, w._teams["h"][1]); wide_y = w._teams["h"][1]["target"][1]
w._tactics["h"]["width"] = "Étroite"; w._tactics["h"]["focus"] = "Axe"
w._aim_slot("h", 1, w._teams["h"][1]); narrow_y = w._teams["h"][1]["target"][1]
assert abs(wide_y - 0.5) > abs(narrow_y - 0.5), (wide_y, narrow_y)
print("2) largeur lue : large =", round(wide_y, 3), "| étroite =", round(narrow_y, 3))

# 3) Phases de construction : basses, médianes, dernier tiers, transition, arrêt.
w._second_half = False; w._burst = None; w._set_piece_until = 0.0; w._possession = "h"
w._ball["pos"] = [0.12, 0.5]; assert w._read_build_phase("h") == "build_low"
w._ball["pos"] = [0.42, 0.5]; assert w._read_build_phase("h") == "build_mid"
w._ball["pos"] = [0.86, 0.5]; assert w._read_build_phase("h") == "final_third"
w._burst = ("h", time.monotonic() + 2.0); assert w._read_build_phase("h") == "transition"
w._burst = None; w._set_piece_until = time.monotonic() + 2.0
assert w._read_build_phase("h") == "set_piece"
w._set_piece_until = 0.0
print("3) phases : build_low / build_mid / final_third / transition / set_piece")

# 4) Les attributs de vitesse changent vraiment le déplacement.
def displacement(speed_value):
    p = Pitch2DWidget(); p.resize(880, 460); p.show(); q.processEvents()
    p.reset_teams("Rapide", "Lent", "#2f6fed", "#c47220")
    p.note_state(state(h_people=people("h", speed=speed_value),
                       a_people=people("a", speed=speed_value)), animate=True)
    start = [list(e["pos"]) for e in p._teams["h"]]
    for _ in range(35): p._step()
    return sum(abs(e["pos"][0]-start[i][0]) + abs(e["pos"][1]-start[i][1])
               for i, e in enumerate(p._teams["h"]))

slow = displacement(20); fast = displacement(95)
assert fast > slow + 0.03, (slow, fast)
print("4) attributs vitesse : lent", round(slow, 3), "| rapide", round(fast, 3))

# 5) La circulation visuelle choisit un receveur selon la phase/le style.
w.reset_teams("Tactique FC", "Bloc FC", "#2f6fed", "#c47220")
w.note_state(st, animate=True)
w._tactics["h"].update({"preset": "possession", "tempo": "Patient", "width": "Large",
                        "focus": "Ailes", "formation": "2-2"})
w._phase = "live"; w._possession = "h"; w._ball["pos"] = [0.82, 0.5]
w._build_phase = "final_third"; w._visual_next = 0
w._visual_circulate("h", time.monotonic())
assert w._follow_ent is not None and w._follow_side == "h"
assert w._follow_ent.get("role") in ("Ailier", "Pivot", "Universel", "Défenseur")
print("5) circulation : receveur", w._follow_ent.get("name"), "en phase", w._build_phase)

# 6) note_state reste strictement en lecture seule.
snapshot = copy.deepcopy(st)
w2 = Pitch2DWidget(); w2.resize(880, 460); w2.show(); q.processEvents()
w2.note_state(st, animate=True)
assert st == snapshot, "le terrain a muté l'état du moteur"
print("6) lecture seule : état du moteur inchangé")

# 7) Stress de fluidité : 600 frames, changements de possession et de tactique.
w3 = Pitch2DWidget(); w3.resize(880, 460); w3.show(); q.processEvents()
w3.reset_teams("Stress FC", "Rideau FC", "#2f6fed", "#c47220")
allowed_phases = {"build_low","build_mid","progress","final_third","transition","set_piece","defend"}
for block in range(10):
    poss = "h" if block % 3 else "a"
    form = ["2-2","3-1","4-0","1-2-1","1-1-2"][block % 5]
    st2 = state(tactics={"h": {"formation": form, "preset": "possession" if block % 2 else "contre",
                                "pressing": 2 if block % 2 else 0, "mentality": 2 if block % 2 else 1,
                                "block": "Haut" if block % 2 else "Bas", "width": "Large" if block % 2 else "Étroite",
                                "focus": "Ailes" if block % 2 else "Axe", "tempo": "Rapide" if block % 2 else "Patient"},
                         "a": {"formation": "3-1", "preset": "equilibre", "pressing": 1,
                                "mentality": 0, "block": "Médian", "width": "Normale",
                                "focus": "Axe", "tempo": "Normal"}})
    st2["possession_side"] = poss
    w3.note_state(st2, animate=True)
    w3._ball["pos"] = [0.20 + 0.06 * block, 0.50]
    for frame in range(60):
        before = [list(e["pos"]) for e in w3._teams["h"] + w3._teams["a"]]
        w3._step()
        after = [list(e["pos"]) for e in w3._teams["h"] + w3._teams["a"]]
        for (x1,y1),(x2,y2) in zip(before, after):
            assert abs(x2-x1)+abs(y2-y1) < 0.06, (block, frame, x1,y1,x2,y2)
    for e in w3._teams["h"] + w3._teams["a"]:
        assert e["shown"] is False or (0.0 <= e["pos"][0] <= 1.0 and 0.0 <= e["pos"][1] <= 1.0)
    assert w3._build_phase in allowed_phases, w3._build_phase
    if not (w3._goal_flash and w3._goal_flash[1] > time.monotonic()):
        assert 0.0 <= w3._ball["pos"][0] <= 0.995, w3._ball["pos"]
print("7) stress fluidité : 600 frames, 5 systèmes, aucun saut ni ballon dans le but")

print("RESULT: ALL OK")
