# -*- coding: utf-8 -*-
"""Réalisme tactique : tactiques et attributs doivent changer le jeu."""
import os
import random
import statistics
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["FM2027_NO_AUDIO"] = "1"
sys.path.insert(0, r"C:\FM2027V2")
import match_engine as me

BASE = {"style": "equilibre", "formation": "3-1", "pressing": "Médian",
        "tempo": "Normal", "mentality": "Équilibrée", "block": "Médian",
        "width": "Normale", "focus": "Axe", "discipline": 0.7}


def ident(**kw):
    row = dict(BASE); row.update(kw); return row


def player(pid, pos="Ailier", level=60, **kw):
    row = {"id": pid, "first_name": f"J{pid}", "last_name": "X", "position": pos,
           "age": 25, "technique": level, "passing": level, "finishing": level,
           "defense": level, "goalkeeper": level if pos == "Gardien" else 20,
           "stamina": level, "dribble": level, "speed": level,
           "positioning": level, "morale": 65, "condition": 90}
    row.update(kw); return row


def five(prefix=10, level=60, **kw):
    return [player(prefix, "Gardien", level, **kw),
            player(prefix + 1, "Défenseur", level, **kw),
            player(prefix + 2, "Ailier", level, **kw),
            player(prefix + 3, "Pivot", level, **kw),
            player(prefix + 4, "Universel", level, **kw)]


def prof(level=60, attack=None, defense=None, passing=None, finishing=None,
         keeper=None, dribble=None, speed=None, positioning=None):
    return {"attack": attack if attack is not None else level,
            "defense": defense if defense is not None else level,
            "passing": passing if passing is not None else level,
            "finishing": finishing if finishing is not None else level,
            "keeper": keeper if keeper is not None else level,
            "dribble": dribble if dribble is not None else level,
            "speed": speed if speed is not None else level,
            "positioning": positioning if positioning is not None else level,
            "stamina": level}


def run(hi, ai, hp=None, ap=None, hline=None, aline=None, n=900, seed=8080):
    rng = random.Random(seed)
    hw = dr = aw = 0; gf = ga = 0
    for _ in range(n):
        h = me._team_state("h", hp or prof(), hline or five(10), hi, 60, True, rng)
        a = me._team_state("a", ap or prof(), aline or five(20), ai, 60, False, rng)
        h["team_name"] = "H"; a["team_name"] = "A"
        me._simulate_match(h, a, rng)
        gf += h["goals"]; ga += a["goals"]
        if h["goals"] > a["goals"]: hw += 1
        elif h["goals"] < a["goals"]: aw += 1
        else: dr += 1
    return {"gf": gf / n, "ga": ga / n, "hw": 100 * hw / n,
            "dr": 100 * dr / n, "aw": 100 * aw / n}


base = run(ident(), ident())
poss = run(ident(style="possession", tempo="Patient", width="Large", focus="Ailes"), ident())
off = run(ident(mentality="Offensive"), ident(mentality="Prudente"))
press = run(ident(pressing="Haut", block="Haut", style="pressing"),
            ident(pressing="Bas", block="Bas", style="contre"))
counter = run(ident(style="contre", tempo="Rapide"), ident(style="possession", tempo="Patient"))

assert poss["gf"] > poss["ga"] + 0.12, poss
assert 40.0 <= poss["hw"] <= 62.0, poss
assert off["gf"] > off["ga"] + 0.12, off
assert press["gf"] > press["ga"] + 0.08, press
assert counter["hw"] >= 30.0 and counter["aw"] <= 70.0, counter
print("1) tactiques : possession %.2f-%.2f | offensive %.2f-%.2f | pressing %.2f-%.2f | contre %.1f%%"
      % (poss["gf"], poss["ga"], off["gf"], off["ga"], press["gf"], press["ga"], counter["hw"]))

# Effets déterministes des réglages sur la qualité offensive/defensive.
rng = random.Random(1)
team = me._team_state("h", prof(), five(10), ident(), 60, True, rng)
opp = me._team_state("a", prof(), five(20), ident(), 60, False, rng)
team["width"] = "Large"; team["focus"] = "Ailes"; team["tempo"] = "Rapide"
large_score = me._attack_score(team, opp, 10)
team["width"] = "Étroite"; team["focus"] = "Axe"; team["tempo"] = "Patient"
narrow_score = me._attack_score(team, opp, 10)
assert large_score > narrow_score, (large_score, narrow_score)
team["mentality"] = "Offensive"; offensive_score = me._attack_score(team, opp, 10)
team["mentality"] = "Prudente"; prudent_score = me._attack_score(team, opp, 10)
assert offensive_score > prudent_score, (offensive_score, prudent_score)
print("2) réglages déterministes : large/ailes/rapide > étroit/axe/patient, offensive > prudente")

# Attributs : chaque famille doit peser sur le résultat ou les buts encaissés.
fin_hi = run(ident(), ident(), prof(attack=64), prof(), five(10, finishing=72), five(20))
fin_lo = run(ident(), ident(), prof(attack=56), prof(), five(10, finishing=48), five(20))
assert fin_hi["gf"] > fin_lo["gf"] + 0.25, (fin_hi, fin_lo)

def_hi = run(ident(), ident(), prof(defense=65), prof(), five(10, defense=72), five(20))
def_lo = run(ident(), ident(), prof(defense=55), prof(), five(10, defense=48), five(20))
assert def_hi["ga"] < def_lo["ga"] - 0.08, (def_hi, def_lo)

gk_hi = run(ident(), ident(), prof(keeper=70), prof(), five(10, goalkeeper=72), five(20))
gk_lo = run(ident(), ident(), prof(keeper=50), prof(), five(10, goalkeeper=48), five(20))
assert gk_hi["ga"] < gk_lo["ga"] - 0.08, (gk_hi, gk_lo)

pass_hi = run(ident(), ident(), prof(attack=62, passing=70), prof(), five(10, passing=72), five(20))
pass_lo = run(ident(), ident(), prof(attack=58, passing=50), prof(), five(10, passing=48), five(20))
assert pass_hi["gf"] > pass_lo["gf"] + 0.08, (pass_hi, pass_lo)

speed_hi = run(ident(), ident(), prof(attack=62), prof(), five(10, speed=72, dribble=72), five(20))
speed_lo = run(ident(), ident(), prof(attack=58), prof(), five(10, speed=48, dribble=48), five(20))
assert speed_hi["gf"] > speed_lo["gf"] + 0.03, (speed_hi, speed_lo)

pos_hi = run(ident(), ident(), prof(defense=66), prof(), five(10, positioning=75), five(20))
pos_lo = run(ident(), ident(), prof(defense=54), prof(), five(10, positioning=45), five(20))
assert pos_hi["ga"] < pos_lo["ga"] - 0.08, (pos_hi, pos_lo)
print("3) attributs : finition, défense, gardien, passe, vitesse et placement pèsent sur le jeu")

print("4) base de référence : %.2f-%.2f, 1X2 %.1f/%.1f/%.1f"
      % (base["gf"], base["ga"], base["hw"], base["dr"], base["aw"]))
print("RESULT: ALL OK")




