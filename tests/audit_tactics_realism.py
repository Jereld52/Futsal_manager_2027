# -*- coding: utf-8 -*-
"""Réalisme des tactiques : presets, formations, mentalités, rythme, pressing.

Deux niveaux de vérification :
  A. Facteurs déterministes du moteur (attaque/défense) : chaque plan a un
     effet réel, ordonné et borné (pas de tactique cassée ni surpuissante).
  B. Matchs simulés (400 par preset) : buts, résultats, possession, tirs,
     cartons et viabilité de chaque tactique.
"""
import os
import random
import statistics
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import match_engine as me

BASE = {"style": "equilibre", "formation": "3-1", "pressing": "Médian", "tempo": "Normal",
        "mentality": "Équilibrée", "block": "Médian", "width": "Normale", "focus": "Axe",
        "discipline": 0.7}

PRESETS = {
    "Équilibré": dict(BASE),
    "Possession": dict(BASE, style="possession", formation="4-0", tempo="Patient",
                       width="Large", focus="Ailes"),
    "Contre": dict(BASE, style="contre", formation="2-2", pressing="Bas", tempo="Rapide",
                   mentality="Prudente", block="Bas", width="Étroite"),
    "Pressing": dict(BASE, style="pressing", pressing="Haut", tempo="Rapide",
                     mentality="Offensive", block="Haut", width="Large", focus="Ailes"),
    "Powerplay": dict(BASE, style="pressing", formation="Gardien volant", pressing="Haut",
                      tempo="Rapide", mentality="Offensive", block="Haut", width="Large",
                      focus="Axe"),
}


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
    return {k: level for k in ("attack", "defense", "passing", "finishing", "keeper",
                              "dribble", "speed", "positioning", "stamina")}


def factors(ident, opponent=None, level=60):
    """Facteurs d'attaque/défense du plan à la 10e minute (équipe à domicile)."""
    rng = random.Random(1)
    h = me._team_state("h", profile(level), lineup(level), ident, 50, True, rng)
    a = me._team_state("a", profile(level), lineup(level), opponent or BASE, 50, False, rng)
    return me._attack_score(h, a, 10), me._defense_score(h, a, 10)


def run(ident, opponent, n, level=60):
    """Statistiques de `ident` contre `opponent`, domicile/extérieur alternés."""
    totals = dict(hg=0, ag=0, w=0, d=0, l=0, poss=0.0, shots=0, target=0, goals=0,
                  cards=0, reds=0, bad=0)
    for i in range(n):
        rng = random.Random(91000 + i)
        home_id = ident if i % 2 == 0 else opponent
        away_id = opponent if i % 2 == 0 else ident
        h = me._team_state("h", profile(level), lineup(level), home_id, 50, True, rng)
        a = me._team_state("a", profile(level), lineup(level), away_id, 50, False, rng)
        h["team_name"] = "H"; a["team_name"] = "A"
        me._simulate_match(h, a, rng)
        mine, other = (h, a) if i % 2 == 0 else (a, h)
        totals["hg"] += mine["goals"]; totals["ag"] += other["goals"]
        if mine["goals"] > other["goals"]: totals["w"] += 1
        elif mine["goals"] < other["goals"]: totals["l"] += 1
        else: totals["d"] += 1
        total_pos = mine["possession"] + other["possession"]
        if total_pos:
            totals["poss"] += mine["possession"] / total_pos
        totals["shots"] += mine["shots"]; totals["target"] += mine["on_target"]
        totals["goals"] += mine["goals"]
        cards = mine["cards"] + other["cards"]
        totals["cards"] += len(cards)
        totals["reds"] += sum(1 for c in cards if c["type"] == "red")
        if not (mine["on_target"] <= mine["shots"] and mine["goals"] <= mine["on_target"]):
            totals["bad"] += 1
        if not (other["on_target"] <= other["shots"] and other["goals"] <= other["on_target"]):
            totals["bad"] += 1
    return {k: v / n for k, v in totals.items()}


def pct(stats, key):
    return stats[key] * 100.0


issues = []


def check(cond, msg):
    if not cond:
        issues.append(msg)
        print("  !!", msg)


# ---------------- A. Facteurs déterministes ----------------
base_atk, base_def = factors(BASE)
print("A) facteurs (base atk %.2f / def %.2f)" % (base_atk, base_def))
atk_f = {}
def_f = {}
for name, ident in PRESETS.items():
    atk, dfn = factors(ident)
    atk_f[name] = atk / base_atk
    def_f[name] = dfn / base_def
    print(f"  {name:10s} attaque {atk_f[name]:.3f}  défense {def_f[name]:.3f}")
    check(0.80 <= atk_f[name] <= 1.25, f"{name}: facteur attaque hors bornes ({atk_f[name]:.3f})")
    check(0.80 <= def_f[name] <= 1.25, f"{name}: facteur défense hors bornes ({def_f[name]:.3f})")

check(atk_f["Possession"] > 1.02, "Possession doit apporter de la présence offensive")
check(def_f["Contre"] > 1.08 and atk_f["Contre"] < 1.0,
      "Contre doit défendre plus et attaquer moins")
check(atk_f["Pressing"] > 1.08 and def_f["Pressing"] < 0.95,
      "Pressing doit être plus offensif et plus exposé")
check(atk_f["Powerplay"] > atk_f["Pressing"], "Powerplay doit être plus offensif que Pressing")

# Gardien volant : l'adversaire doit voir sa note d'attaque monter.
adv_vs_pp, _ = factors(BASE, PRESETS["Powerplay"])
adv_vs_base, _ = factors(BASE, BASE)
check(adv_vs_pp / adv_vs_base > 1.04,
      f"Gardien volant : aucun bonus pour l'adversaire ({adv_vs_pp/adv_vs_base:.3f})")
print(f"  gardien volant : attaque adverse x{adv_vs_pp/adv_vs_base:.3f}")

# Formations : chacune a un effet réel et ordonné.
f_atk = {}
for formation in ("3-1", "4-0", "2-2", "Gardien volant", "1-2-1", "1-1-2"):
    a, _d = factors(dict(BASE, formation=formation))
    f_atk[formation] = a / base_atk
    print(f"  formation {formation:15s} attaque x{f_atk[formation]:.3f}")
check(f_atk["4-0"] > 1.0, "4-0 doit apporter un plus offensif")
check(f_atk["1-1-2"] > f_atk["1-2-1"] > 1.0, "1-1-2 doit être plus offensif que 1-2-1")
check(f_atk["Gardien volant"] > 1.0, "Gardien volant doit apporter un plus offensif")

# ---------------- B. Matchs simulés ----------------
print("\nB) matchs simulés")
N = 400
mirror = run(BASE, BASE, N)
mirror_total = mirror["hg"] + mirror["ag"]
print(f"  miroir : {mirror['hg']:.2f}-{mirror['ag']:.2f} "
      f"(total {mirror_total:.2f}) | V {pct(mirror,'w'):.1f}% N {pct(mirror,'d'):.1f}% D {pct(mirror,'l'):.1f}%")
check(3.8 <= mirror_total <= 5.5, f"buts/match du miroir hors plage ({mirror_total:.2f})")
check(0.5 <= mirror["cards"] <= 6.0, f"cartons hors plage ({mirror['cards']:.2f})")
check(mirror["reds"] <= 0.4, f"rouges hors plage ({mirror['reds']:.3f})")

results = {}
for name, ident in PRESETS.items():
    if name == "Équilibré":
        continue
    s = run(ident, PRESETS["Équilibré"], N)
    results[name] = s
    total = s["hg"] + s["ag"]
    print(f"  {name:10s} {s['hg']:.2f}-{s['ag']:.2f} total {total:.2f} | "
          f"V {pct(s,'w'):.1f}% N {pct(s,'d'):.1f}% D {pct(s,'l'):.1f}% | "
          f"poss {pct(s,'poss'):.1f}% | cartons {s['cards']:.2f}")
    check(4.0 <= total <= 6.2, f"{name}: buts/match hors plage ({total:.2f})")
    check(30.0 <= pct(s, "w") <= 60.0, f"{name}: taux de victoire hors plage ({pct(s,'w'):.1f}%)")
    check(pct(s, "l") >= 25.0, f"{name}: adversaire trop battu ({pct(s,'l'):.1f}%)")
    check(10.0 <= pct(s, "d") <= 30.0, f"{name}: part de nuls hors plage ({pct(s,'d'):.1f}%)")
    check(s["bad"] == 0, f"{name}: incohérence tirs/buts")
    check(s["reds"] <= 0.4, f"{name}: trop de rouges ({s['reds']:.3f})")

check(pct(results["Possession"], "poss") >= 52.0,
      f"Possession ne contrôle pas assez le ballon ({pct(results['Possession'],'poss'):.1f}%)")
check(pct(results["Contre"], "poss") <= 50.5,
      f"Contre devrait laisser le ballon ({pct(results['Contre'],'poss'):.1f}%)")
check(results["Pressing"]["cards"] >= mirror["cards"] + 0.25,
      "Pressing haut doit provoquer plus de cartons")
check(max(pct(s, "w") for s in results.values()) <= 60.0, "une tactique domine trop")

# Formations : toutes viables et réalistes.
print("\n  formations (300 matchs chacune)")
for formation in ("3-1", "4-0", "2-2", "Gardien volant", "1-2-1", "1-1-2"):
    s = run(dict(BASE, formation=formation), BASE, 300)
    total = s["hg"] + s["ag"]
    print(f"  {formation:15s} {s['hg']:.2f}-{s['ag']:.2f} total {total:.2f} | V {pct(s,'w'):.1f}%")
    check(4.0 <= total <= 5.5, f"formation {formation}: buts/match hors plage ({total:.2f})")
    check(30.0 <= pct(s, "w") <= 55.0, f"formation {formation}: victoires hors plage")

# Mentalités : l'offensive pousse plus et se découvre plus que la prudente.
print("\n  mentalités (400 matchs chacune)")
off_atk, off_def = factors(dict(BASE, mentality="Offensive"))
pru_atk, pru_def = factors(dict(BASE, mentality="Prudente"))
check(off_atk > pru_atk, "mentalité offensive : attaque non supérieure à la prudente")
check(off_def < pru_def, "mentalité offensive : défense non inférieure à la prudente")
print(f"  facteurs : offensive atk {off_atk/base_atk:.3f} def {off_def/base_def:.3f} | "
      f"prudente atk {pru_atk/base_atk:.3f} def {pru_def/base_def:.3f}")
off = run(dict(BASE, mentality="Offensive"), BASE, N)
pru = run(dict(BASE, mentality="Prudente"), BASE, N)
print(f"  offensive {off['hg']:.2f}-{off['ag']:.2f} | prudente {pru['hg']:.2f}-{pru['ag']:.2f}")
# Contrôle statistique large : l'offensive doit rester dans la même enveloppe,
# sans devenir une tactique perdante.
check(4.0 <= off["hg"] + off["ag"] <= 5.5, "offensive : buts hors plage")
check(4.0 <= pru["hg"] + pru["ag"] <= 5.5, "prudente : buts hors plage")
check(30.0 <= pct(off, "w") <= 60.0 and 30.0 <= pct(pru, "w") <= 60.0,
      "mentalités : taux de victoire hors plage")

# Rythme et pressing restent dans des bornes réalistes.
print("\n  rythme / pressing")
for tempo in ("Patient", "Normal", "Rapide"):
    s = run(dict(BASE, tempo=tempo), BASE, 300)
    total = s["hg"] + s["ag"]
    print(f"  tempo {tempo:8s} total {total:.2f}")
    check(4.0 <= total <= 5.5, f"tempo {tempo}: buts hors plage ({total:.2f})")
for press in ("Bas", "Médian", "Haut"):
    s = run(dict(BASE, pressing=press), BASE, 300)
    total = s["hg"] + s["ag"]
    print(f"  press {press:8s} total {total:.2f} | cartons {s['cards']:.2f}")
    check(4.0 <= total <= 5.5, f"pressing {press}: buts hors plage ({total:.2f})")

if issues:
    print("\nPROBLEMES:", len(issues))
    for msg in issues:
        print(" -", msg)
    raise SystemExit(1)

print("\nRESULT: ALL OK")
