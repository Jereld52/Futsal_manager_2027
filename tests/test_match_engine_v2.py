# -*- coding: utf-8 -*-
"""Moteur de match v2 : déterminisme, avantage du terrain, mentalités, réalisme."""
import os, random, statistics, sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import match_engine as me


def lineup(level, morale=65, condition=85):
    players = [{"id": 1, "first_name": "G", "last_name": "Keeper", "position": "Gardien",
                "goalkeeper": level + 2, "condition": condition, "stamina": level,
                "positioning": level, "morale": morale, "finishing": 30, "technique": 50,
                "dribble": 45, "speed": 50}]
    for i in range(4):
        players.append({"id": 10 + i, "first_name": "J", "last_name": str(i + 1),
                        "position": ["Défenseur", "Ailier", "Pivot", "Universel"][i],
                        "defense": level, "finishing": level, "technique": level,
                        "passing": level, "dribble": level, "speed": level,
                        "positioning": level, "stamina": level, "condition": condition,
                        "morale": morale, "goalkeeper": 20})
    return players


def profile(level):
    return {"attack": level, "defense": level, "passing": level, "finishing": level,
            "keeper": level, "dribble": level, "speed": level, "positioning": level,
            "stamina": level}


IDENT = {
    "equilibre": {"style": "equilibre", "formation": "3-1", "pressing": "Médian",
                  "tempo": "Normal", "mentality": "Équilibrée", "block": "Médian",
                  "width": "Normale", "focus": "Axe", "discipline": 0.7},
    "offensive": {"style": "pressing", "formation": "3-1", "pressing": "Haut",
                  "tempo": "Rapide", "mentality": "Offensive", "block": "Haut",
                  "width": "Large", "focus": "Ailes", "discipline": 0.5},
    "prudent": {"style": "contre", "formation": "2-2", "pressing": "Bas",
                "tempo": "Patient", "mentality": "Prudente", "block": "Bas",
                "width": "Étroite", "focus": "Axe", "discipline": 0.85},
}


def match(level_h, level_a, ident_h="equilibre", ident_a="equilibre", seed=0):
    rng = random.Random(seed)
    h = me._team_state("h", profile(level_h), lineup(level_h), IDENT[ident_h], 50, True, rng)
    a = me._team_state("a", profile(level_a), lineup(level_a), IDENT[ident_a], 50, False, rng)
    h["team_name"] = "H"; a["team_name"] = "A"
    return me._simulate_match(h, a, rng), h, a


def run(level_h, level_a, n=400, ident_h="equilibre", ident_a="equilibre"):
    goals = []
    hw = aw = dr = 0
    hg = ag = 0
    reds = cards = 0
    for i in range(n):
        _, h, a = match(level_h, level_a, ident_h, ident_a, seed=500 + i)
        hg += h["goals"]; ag += a["goals"]
        goals.append(h["goals"] + a["goals"])
        if h["goals"] > a["goals"]: hw += 1
        elif h["goals"] < a["goals"]: aw += 1
        else: dr += 1
        allcards = h["cards"] + a["cards"]
        cards += len(allcards)
        reds += sum(1 for c in allcards if c["type"] == "red")
    return {"hg": hg / n, "ag": ag / n, "goals": statistics.mean(goals),
            "hw": 100.0 * hw / n, "aw": 100.0 * aw / n, "dr": 100.0 * dr / n,
            "cards": cards / n, "reds": reds / n}


# 1) Déterminisme : même graine -> même score et mêmes buteurs.
r1, h1, a1 = match(60, 60, seed=42)
r2, h2, a2 = match(60, 60, seed=42)
assert (h1["goals"], a1["goals"]) == (h2["goals"], a2["goals"]), (h1["goals"], a1["goals"], h2["goals"], a2["goals"])
assert [e["scorer"] for e in r1["events"]] == [e["scorer"] for e in r2["events"]]
print("OK déterminisme :", h1["goals"], "-", a1["goals"])

# 2) Avantage du terrain sur équipes égales.
eq = run(60, 60)
assert eq["hw"] > eq["aw"] + 5, eq
points_home = 3 * eq["hw"] + eq["dr"]
points_away = 3 * eq["aw"] + eq["dr"]
assert points_home > points_away * 1.10, (points_home, points_away)
print("OK domicile :", round(eq["hw"], 1), "% /", round(eq["dr"], 1), "% /", round(eq["aw"], 1), "%")

# 3) Une équipe très supérieure gagne nettement, sans écraser toute surprise.
strong = run(72, 52)
assert strong["hw"] > 60, strong
assert strong["aw"] >= 5, strong
print("OK hiérarchie :", round(strong["hg"], 2), "-", round(strong["ag"], 2),
      "| victoires", round(strong["hw"], 1), "% | exploits", round(strong["aw"], 1), "%")

# 4) Buts/match réalistes (futsal) et bornés.
assert 3.2 <= eq["goals"] <= 6.5, eq
print("OK buts/match :", round(eq["goals"], 2))

# 5) Mentalités : à niveau égal, l'offensive marque plus et encaisse plus.
off = run(60, 60, ident_h="offensive", ident_a="equilibre")
pru = run(60, 60, ident_h="prudent", ident_a="equilibre")
assert off["hg"] > pru["hg"], (off["hg"], pru["hg"])
assert off["ag"] > pru["ag"], (off["ag"], pru["ag"])
print("OK mentalités : offensive", round(off["hg"], 2), "+", round(off["ag"], 2),
      "| prudente", round(pru["hg"], 2), "+", round(pru["ag"], 2))
# Aucune mentalité ne domine outrageusement l'autre.
assert abs(off["hw"] - pru["hw"]) < 25, (off["hw"], pru["hw"])

# 6) Discipline bornée.
assert 0.5 <= eq["cards"] <= 7.0, eq
assert eq["reds"] <= 0.35, eq
print("OK discipline :", round(eq["cards"], 2), "cartons/match,", round(eq["reds"], 3), "rouge/match")

# 7) Événements exploitables par le rapport (buteurs, côté, minute).
assert all(e.get("scorer") and e.get("side") in ("h", "a") for e in r1["events"])
print("OK rapport :", len(r1["events"]), "but(s) détaillé(s)")

print("RESULT: ALL OK")
