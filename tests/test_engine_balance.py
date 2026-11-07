# -*- coding: utf-8 -*-
"""Équilibrage du moteur : buts, 1X2, discipline, 10 m et favoris.

Échantillons déterministes (graines fixes) sur un harnais synthétique :
aucune base de données, exécution en quelques secondes. Les bornes sont
volontairement larges : elles attrapent une dérive, pas le bruit.
"""
import os
import random
import statistics
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["FM2027_NO_AUDIO"] = "1"
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
    "agressif": {"style": "pressing", "formation": "3-1", "pressing": "Haut",
                 "tempo": "Rapide", "mentality": "Offensive", "block": "Haut",
                 "width": "Large", "focus": "Ailes", "discipline": 0.2},
}


def match(level_h, level_a, ident_h="equilibre", ident_a="equilibre", seed=0):
    rng = random.Random(seed)
    home = me._team_state("h", profile(level_h), lineup(level_h), IDENT[ident_h], 50, True, rng)
    away = me._team_state("a", profile(level_a), lineup(level_a), IDENT[ident_a], 50, False, rng)
    home["team_name"] = "Domicile"
    away["team_name"] = "Extérieur"
    return me._simulate_match(home, away, rng), home, away


def run(level_h, level_a, n=600, ident_h="equilibre", ident_a="equilibre"):
    totals = {"goals": [], "shots": 0, "on_target": 0, "fouls": 0, "cards": 0,
              "yellows": 0, "reds": 0, "ten": 0, "ten_goals": 0, "saves": 0,
              "clean_sheets": 0, "nil_nil": 0, "max_ten": 0}
    hw = dr = aw = 0
    for i in range(n):
        report, home, away = match(level_h, level_a, ident_h, ident_a, seed=3000 + i)
        hg, ag = home["goals"], away["goals"]
        totals["goals"].append(hg + ag)
        totals["shots"] += home["shots"] + away["shots"]
        totals["on_target"] += home["on_target"] + away["on_target"]
        totals["saves"] += home["saves"] + away["saves"]
        totals["fouls"] += home["fouls"] + away["fouls"]
        totals["ten"] += home["ten_meter"] + away["ten_meter"]
        totals["ten_goals"] += sum(1 for e in report["events"] if e.get("type") == "10 m")
        totals["max_ten"] = max(totals["max_ten"],
                                home["ten_meter"] + away["ten_meter"])
        if hg == 0 or ag == 0:
            totals["clean_sheets"] += 1
        if hg == 0 and ag == 0:
            totals["nil_nil"] += 1
        for team in (home, away):
            # Une équipe ne peut pas tirer plus de 10 m qu'elle ne commet de fautes.
            assert team["ten_meter"] <= team["fouls"], (team["ten_meter"], team["fouls"])
        for card in home["cards"] + away["cards"]:
            totals["cards"] += 1
            if card["type"] == "red":
                totals["reds"] += 1
            else:
                totals["yellows"] += 1
        if hg > ag:
            hw += 1
        elif hg < ag:
            aw += 1
        else:
            dr += 1
    return {
        "n": n, "goals": statistics.mean(totals["goals"]),
        "hw": 100.0 * hw / n, "dr": 100.0 * dr / n, "aw": 100.0 * aw / n,
        "shots": totals["shots"] / n, "on_target": totals["on_target"] / n,
        "saves": totals["saves"] / n, "fouls": totals["fouls"] / n,
        "cards": totals["cards"] / n, "yellows": totals["yellows"] / n,
        "reds": totals["reds"] / n, "ten": totals["ten"] / n,
        "ten_goals": totals["ten_goals"] / n, "max_ten": totals["max_ten"],
        "ten_conv": 100.0 * totals["ten_goals"] / max(1, totals["ten"]),
        "clean_sheets": 100.0 * totals["clean_sheets"] / n,
        "nil_nil": 100.0 * totals["nil_nil"] / n,
        "pct_8plus": 100.0 * sum(1 for g in totals["goals"] if g >= 8) / n,
    }


# 1) Deux équipes égales : volume de jeu, scores et issue crédibles.
eq = run(60, 60, n=600)
assert 4.2 <= eq["goals"] <= 5.2, eq
assert 40.0 <= eq["hw"] <= 52.0, eq
assert 14.0 <= eq["dr"] <= 24.0, eq
assert 30.0 <= eq["aw"] <= 43.0, eq
assert 29.0 <= eq["shots"] <= 36.0, eq
assert 14.0 <= eq["on_target"] <= 19.0, eq
assert 9.0 <= eq["saves"] <= 15.0, eq
assert eq["nil_nil"] <= 4.0, eq
assert 10.0 <= eq["clean_sheets"] <= 28.0, eq
assert 3.0 <= eq["pct_8plus"] <= 14.0, eq
print("1) égalité : %.2f buts/match | 1X2 %.1f/%.1f/%.1f | tirs %.1f (%.1f cadrés)"
      % (eq["goals"], eq["hw"], eq["dr"], eq["aw"], eq["shots"], eq["on_target"]))

# 2) Discipline : fautes, cartons, rouges dans les clous du futsal.
assert 7.5 <= eq["fouls"] <= 12.5, eq
assert 2.0 <= eq["cards"] <= 3.8, eq
assert 1.8 <= eq["yellows"] <= 3.5, eq
assert eq["reds"] <= 0.30, eq
print("2) discipline : %.1f fautes, %.2f cartons (%.2f jaunes, %.3f rouge)/match"
      % (eq["fouls"], eq["cards"], eq["yellows"], eq["reds"]))

# 3) 10 m : rares mais présents avec un profil discipliné, conversion réaliste.
assert 0.0 <= eq["ten"] <= 0.60, eq
assert eq["ten_goals"] <= eq["ten"], eq
print("3) 10 m profil discipliné : %.2f tentative(s)/match" % eq["ten"])

# 4) Un profil agressif cumule les fautes et les 10 m, et plusieurs 10 m
#    peuvent tomber dans la même mi-temps (règle de la 6e faute accumulée).
agr = run(60, 60, n=300, ident_h="agressif")
assert agr["fouls"] > eq["fouls"] + 3.0, (agr["fouls"], eq["fouls"])
assert agr["cards"] > eq["cards"] + 1.0, (agr["cards"], eq["cards"])
assert agr["ten"] >= 1.2, agr
assert agr["max_ten"] >= 3, agr
assert 15.0 <= agr["ten_conv"] <= 45.0, agr
assert agr["ten_goals"] <= agr["ten"], agr
print("4) 10 m : %.2f tentative(s)/match (max %d), %.1f%% de conversion, "
      "profil agressif : %.1f fautes"
      % (agr["ten"], agr["max_ten"], agr["ten_conv"], agr["fouls"]))

# 5) Hiérarchie : une équipe nettement supérieure gagne, sans écraser
#    toute possibilité d'exploit.
fort = run(72, 52, n=400)
assert fort["hw"] >= 70.0, fort
assert fort["aw"] >= 3.0, fort
assert 4.5 <= fort["goals"] <= 6.0, fort
print("5) favori : %.1f%% de victoires (%.1f%% d'exploits), %.2f buts/match"
      % (fort["hw"], fort["aw"], fort["goals"]))

# 6) Déterminisme : les mêmes graines doivent rejouer le même match.
a1, h1, _ = match(60, 60, seed=77777)
a2, h2, _ = match(60, 60, seed=77777)
assert (h1["goals"], h1["shots"], h1["fouls"], h1["ten_meter"]) == \
       (h2["goals"], h2["shots"], h2["fouls"], h2["ten_meter"])
assert [e["scorer"] for e in a1["events"]] == [e["scorer"] for e in a2["events"]]
print("6) déterminisme : score, tirs, fautes et buteurs identiques")

print("RESULT: ALL OK")
