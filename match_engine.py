# -*- coding: utf-8 -*-
"""Moteur de resultat v2 : simulation des matchs entre clubs.

Le moteur prend en compte :
- le niveau et l'etat des cinq alignes (attaque, defense, passe, finition,
  gardien, dribble, vitesse, placement, moral, condition, endurance) ;
- l'identite tactique complete (style, formation, pressing, tempo, mentalite,
  hauteur de bloc, largeur, axe de jeu, discipline) ;
- la dynamique du match : momentum, fatigue qui monte, score et temps restant,
  inferiorite numerique (rouge = 2 minutes a 4), 6e faute et suivantes -> 10 m ;
- l'aleatoire maitrise : forme du jour, arbitre, erreur de gardien, but contre
  son camp, frappe deviee, occasion nette ou speculative.

Le resultat reste deterministe pour un meme fixture (RNG seme).
"""
import hashlib
import json
import random

TICKS = 120
SECONDS_PER_TICK = 20
MATCH_SECONDS = 2400

# --- calibrage global (buts/match ~4.5-5.5) ---
HOME_ATTACK = 0.095          # avantage du terrain sur l'attaque
HOME_DEFENSE = 0.045
EDGE_COEF = 0.0017           # 1 point d'ecart attaque/defense
SHOT_BASE = 0.440
SHOT_BUILD = 0.090
SHOT_EDGE = 0.85

MENTALITY = {
    "Offensive":  {"atk": 1.085, "def": 0.945, "conv": 1.00, "risk": 1.18, "push": 12},
    "Prudente":   {"atk": 0.945, "def": 1.075, "conv": 1.00, "risk": 0.88, "push": 6},
    "Équilibrée": {"atk": 1.000, "def": 1.000, "conv": 1.00, "risk": 1.00, "push": 8},
}

BLOCK = {
    "Haut":   {"def": 0.970, "press": 1.10, "atk": 1.020},
    "Médian": {"def": 1.000, "press": 1.00, "atk": 1.000},
    "Bas":    {"def": 1.050, "press": 0.92, "atk": 0.985},
}

STYLE = {
    "possession": {"poss": 1.28, "pass": 1.020, "atk": 1.000, "def": 1.000},
    "contre":     {"poss": 0.88, "pass": 0.990, "atk": 1.015, "def": 1.010},
    "pressing":   {"poss": 1.04, "pass": 0.995, "atk": 1.020, "def": 0.990},
    "equilibre":  {"poss": 1.00, "pass": 1.000, "atk": 1.000, "def": 1.000},
}


def _num(obj, key, default=45.0):
    try:
        value = obj.get(key, default) if hasattr(obj, "get") else obj[key]
        return float(value) if value is not None else float(default)
    except Exception:
        return float(default)


def _clamp(value, low, high):
    return max(low, min(high, value))


def _team_state(side, profile, lineup, identity, reputation, is_home, rng):
    """Etat d'une equipe pour le match : niveau, forme du jour, fatigue, mentalite."""
    players = [p for p in (lineup or []) if p]
    field = [p for p in players if str(p.get("position")) != "Gardien"] or players
    identity = dict(identity or {})
    style = str(identity.get("style") or "equilibre")
    pressing = str(identity.get("pressing") or "Médian")
    tempo = str(identity.get("tempo") or "Normal")
    mentality = str(identity.get("mentality") or "Équilibrée")

    morale = sum(_num(p, "morale", 60) for p in field) / max(1, len(field))
    condition = sum(_num(p, "condition", 70) for p in field) / max(1, len(field))
    stamina = sum(min(_num(p, "stamina", 45), _num(p, "condition", 70)) for p in field) / max(1, len(field))

    state = {
        "side": side,
        "players": players,
        "identity": identity,
        "style": style,
        "pressing": pressing,
        "tempo": tempo,
        "mentality": mentality,
        "block": str(identity.get("block") or "Médian"),
        "width": str(identity.get("width") or "Normale"),
        "focus": str(identity.get("focus") or "Axe"),
        "discipline": _clamp(float(identity.get("discipline", 0.65) or 0.65), 0.2, 1.0),
        "reputation": _num({"r": reputation}, "r", 30),
        "is_home": bool(is_home),
        "attack": _num(profile, "attack", 50),
        "defense": _num(profile, "defense", 50),
        "passing": _num(profile, "passing", 50),
        "finishing": _num(profile, "finishing", 50),
        "keeper": _num(profile, "keeper", 50),
        "dribble": _num(profile, "dribble", 50),
        "speed": _num(profile, "speed", 50),
        "positioning": _num(profile, "positioning", 50),
        "morale": morale,
        "condition": condition,
        "stamina": stamina,
        "fatigue": 0.0,
        "momentum": 0.0,
        "players_on": 5,
        "red_ticks": 0,
        "fouls_half": 0,
        "fouls": 0,
        "ten_meter": 0,
        "goals": 0,
        "shots": 0,
        "on_target": 0,
        "corners": 0,
        "saves": 0,
        "possession": 0,
        "build": 0,
        "cards": [],
        "injuries": [],
        "scorers": {},
    }
    # Forme du jour : moral + fraicheur + hasard (une grande equipe peut rater son match).
    state["form"] = (1.0 + (morale - 60.0) / 100.0 * 0.045
                     + (condition - 70.0) / 100.0 * 0.045
                     + rng.uniform(-0.028, 0.028))
    press_fatigue = 1.25 if pressing == "Haut" else 1.0
    tempo_fatigue = 1.18 if tempo == "Rapide" else 0.92 if tempo == "Patient" else 1.0
    state["fatigue_rate"] = (0.0015 * press_fatigue * tempo_fatigue
                             * (1.0 + max(0.0, 62.0 - stamina) / 120.0))
    return state


def _attack_score(team, opponent, minute):
    """Qualite offensive du moment (mentalite, bloc, forme, fatigue, score)."""
    mental = MENTALITY.get(team["mentality"], MENTALITY["Équilibrée"])
    block = BLOCK.get(team["block"], BLOCK["Médian"])
    style = STYLE.get(team["style"], STYLE["equilibre"])
    score = team["attack"] * mental["atk"] * block["atk"] * style["atk"]
    formation = str(team["identity"].get("formation") or "")
    if formation.startswith("4-0"):
        score *= 1.025
    elif formation.startswith("2-2"):
        score *= 1.015
    elif formation.startswith("1-1-2"):
        score *= 1.025
    elif formation.startswith("1-2-1"):
        score *= 1.012
    elif formation.lower().startswith("gardien"):
        score *= 1.030
    # Gardien volant : la cage est vide, l'adversaire en profite.
    if str(opponent.get("identity", {}).get("formation") or "").lower().startswith("gardien"):
        score *= 1.085
    if team["width"] == "Large":
        score *= 1.015
    elif team["width"] == "Étroite":
        score *= 1.008
    if team["focus"] == "Ailes" and team["width"] == "Large":
        score *= 1.010
    elif team["focus"] == "Axe":
        score *= 1.006
    score *= (1.0 - 0.20 * team["fatigue"])
    score *= team["form"]
    score *= (1.0 - 0.02 * min(2, len(team["injuries"])))
    score *= (1.0 + 0.05 * team["momentum"])
    score *= (1.0 + HOME_ATTACK) if team["is_home"] else 1.0
    if team["players_on"] < 5:
        score *= 0.86
    # Effet du score dans le money-time, module par la mentalite.
    remaining = MATCH_SECONDS - minute * 60
    diff = team["goals"] - opponent["goals"]
    push = mental["push"] * 60
    if diff < 0 and remaining <= push:
        score *= 1.10
    elif diff > 0 and remaining <= push:
        score *= 0.96
    return score


def _defense_score(team, opponent, minute):
    mental = MENTALITY.get(team["mentality"], MENTALITY["Équilibrée"])
    block = BLOCK.get(team["block"], BLOCK["Médian"])
    style = STYLE.get(team["style"], STYLE["equilibre"])
    score = team["defense"] * mental["def"] * block["def"] * style["def"]
    score *= (1.0 - 0.18 * team["fatigue"])
    score *= team["form"]
    score *= (1.0 - 0.025 * min(2, len(team["injuries"])))
    score *= (1.0 - 0.04 * team["momentum"])
    score *= (1.0 + HOME_DEFENSE) if team["is_home"] else 1.0
    if team["players_on"] < 5:
        score *= 0.82
    remaining = MATCH_SECONDS - minute * 60
    diff = team["goals"] - opponent["goals"]
    push = mental["push"] * 60
    if diff > 0 and remaining <= push:
        score *= 1.05
    elif diff < 0 and remaining <= push:
        score *= 0.94
    return score


def _possession_weight(team):
    style = STYLE.get(team["style"], STYLE["equilibre"])
    weight = 0.55 + (team["passing"] - 55.0) * 0.006
    weight *= style["poss"]
    weight *= 1.04 if team["pressing"] == "Haut" else 0.97 if team["pressing"] == "Bas" else 1.0
    weight *= 1.03 if team["tempo"] == "Rapide" else 0.98 if team["tempo"] == "Patient" else 1.0
    weight *= (1.0 - 0.20 * team["fatigue"])
    weight *= (1.0 + 0.06 * team["momentum"])
    weight *= team["form"]
    weight *= (1.05 if team["is_home"] else 1.0)
    weight *= (0.90 if team["players_on"] < 5 else 1.0)
    return max(0.20, weight)


def _pick(players, weights, rng):
    total = sum(weights)
    if total <= 0:
        return players[0] if players else None
    roll = rng.random() * total
    upto = 0.0
    for player, weight in zip(players, weights):
        upto += weight
        if roll <= upto:
            return player
    return players[-1]


def _shooter(team, rng):
    field = [p for p in team["players"] if str(p.get("position")) != "Gardien"]
    if not field:
        field = team["players"]
    weights = [max(1.0, _num(p, "finishing", 45) * 0.50 + _num(p, "technique", 45) * 0.20
                   + _num(p, "dribble", 50) * 0.14 + _num(p, "speed", 50) * 0.08
                   + _num(p, "condition", 70) * 0.08) for p in field]
    return _pick(field, weights, rng)


def _keeper_of(team):
    return next((p for p in team["players"] if str(p.get("position")) == "Gardien"),
                team["players"][0] if team["players"] else None)


def _simulate_match(home, away, rng):
    """Coeur du moteur : 120 sequences de 20 secondes."""
    events = []
    goals_by_player = {}
    assists_by_player = {}
    referee = _clamp(rng.gauss(1.0, 0.13), 0.70, 1.30)
    wh = _possession_weight(home); wa = _possession_weight(away)
    side = "h" if rng.random() < wh / (wh + wa) else "a"

    def team_of(code):
        return home if code == "h" else away

    def other(code):
        return "a" if code == "h" else "h"

    def add_goal(code, minute, kind="jeu", scorer=None, assist=None):
        team = team_of(code)
        team["goals"] += 1
        player = scorer or _shooter(team, rng)
        label = f"{player['first_name']} {player['last_name']}" if player else "Buteur"
        pid = player.get("id") if player else None
        if pid:
            goals_by_player[pid] = goals_by_player.get(pid, 0) + 1
        assist_label = None
        if assist is not None:
            assist_label = f"{assist['first_name']} {assist['last_name']}"
            if assist.get("id"):
                assists_by_player[assist["id"]] = assists_by_player.get(assist["id"], 0) + 1
        events.append({"minute": minute, "side": code, "team": team["team_name"],
                       "scorer": label, "assist": assist_label, "type": kind})
        team["momentum"] = _clamp(team["momentum"] + 0.55, -1.2, 1.2)
        rival = team_of(other(code))
        rival["momentum"] = _clamp(rival["momentum"] - 0.45, -1.2, 1.2)

    def attempt_pass(attacker, defender):
        pass_edge = ((attacker["passing"] - defender["defense"]) * 0.0022
                     + (0.030 if attacker["style"] == "possession" else 0.0)
                     + (0.020 if attacker["tempo"] == "Patient" else -0.012 if attacker["tempo"] == "Rapide" else 0.0)
                     + (0.025 if attacker["players_on"] > defender["players_on"] else 0.0)
                     - 0.06 * attacker["fatigue"])
        completion = _clamp(0.73 + pass_edge, 0.50, 0.93)
        if rng.random() < completion:
            attacker["build"] = min(6, attacker["build"] + 2)
            return True
        defender["possessions_won"] = defender.get("possessions_won", 0) + 1
        attacker["build"] = 0
        return False

    for tick in range(TICKS):
        elapsed = (tick + 1) * SECONDS_PER_TICK
        minute = max(1, (elapsed + 59) // 60)
        if elapsed == MATCH_SECONDS // 2:
            home["fouls_half"] = 0
            away["fouls_half"] = 0
        for code in ("h", "a"):
            team = team_of(code)
            if team["red_ticks"] > 0:
                team["red_ticks"] -= 1
                if team["red_ticks"] == 0:
                    team["players_on"] = 5
            team["fatigue"] = _clamp(team["fatigue"] + team["fatigue_rate"], 0.0, 1.0)
            team["momentum"] *= 0.975
            # Blessure en match : rare, aggravee par la fatigue.
            if team["players"] and rng.random() < 0.0007 * (1.0 + 1.5 * team["fatigue"]):
                victim = rng.choice(team["players"])
                team["injuries"].append({"player": victim, "days": rng.randint(2, 10)})

        if rng.random() >= 0.62:
            wh = _possession_weight(home); wa = _possession_weight(away)
            side = "h" if rng.random() < wh / (wh + wa) else "a"

        attack_side, defend_side = side, other(side)
        attacker = team_of(attack_side)
        defender = team_of(defend_side)
        attacker["possession"] += 1

        # --- fautes : discipline, pressing, mentalite ---
        foul_p = 0.130 * (1.30 - defender["discipline"]) * (1.28 if defender["pressing"] == "Haut" else 1.0)
        foul_p *= MENTALITY.get(defender["mentality"], MENTALITY["Équilibrée"])["risk"]
        # A partir de la 5e faute de la mi-temps, on defend plus prudemment :
        # les equipes evitent la 6e faute et le 10 m.
        if defender["fouls_half"] >= 5:
            foul_p *= 0.65
        if rng.random() < foul_p:
            defender["fouls_half"] += 1
            defender["fouls"] += 1
            pool = [p for p in defender["players"] if str(p.get("position")) != "Gardien"] or defender["players"]
            roll = rng.random()
            yellow_p = 0.28 * referee * (1.20 - defender["discipline"] * 0.40)
            red_p = 0.020 * referee * (1.40 - defender["discipline"])
            if pool and roll < red_p and defender["players_on"] == 5:
                player = _pick(pool, [max(1.0, 62.0 - _num(p, "defense", 45)) for p in pool], rng)
                defender["players_on"] = 4
                defender["red_ticks"] = 6
                defender["cards"].append({"player": player, "type": "red", "minute": minute, "side": defend_side})
            elif pool and roll < red_p + yellow_p:
                player = _pick(pool, [max(1.0, _num(p, "defense", 45)) for p in pool], rng)
                defender["cards"].append({"player": player, "type": "yellow", "minute": minute, "side": defend_side})
            if defender["fouls_half"] >= 6:
                # Regle futsal : a partir de la 6e faute accumulee dans la
                # mi-temps, chaque faute supplementaire donne un 10 m.
                defender["ten_meter"] += 1
                atk = _attack_score(attacker, defender, minute)
                dfn = _defense_score(defender, attacker, minute)
                kicker = _shooter(attacker, rng)
                conv = _clamp(0.27 + (_num(kicker, "finishing", 45) - defender["keeper"]) * 0.0022
                              + (atk - dfn) * 0.0010, 0.12, 0.46)
                attacker["shots"] += 1
                if rng.random() < conv:
                    attacker["on_target"] += 1
                    add_goal(attack_side, minute, "10 m", scorer=kicker)
                else:
                    if rng.random() < 0.55 and _keeper_of(defender) is not None:
                        attacker["on_target"] += 1
                        defender["saves"] += 1
                attacker["build"] = 0
                side = defend_side
                continue
            attacker["build"] = max(1, attacker["build"])
            continue

        # --- perte de balle sous pression ---
        press = 1.10 if defender["pressing"] == "Haut" else 1.0 if defender["pressing"] == "Médian" else 0.92
        turnover = (0.016 + 0.020 * press
                    + (0.030 if defender["momentum"] > 0.4 else 0.0)
                    + 0.004 * max(0, attacker["build"] - 2)
                    + 0.020 * attacker["fatigue"])
        if rng.random() < turnover:
            defender["possessions_won"] = defender.get("possessions_won", 0) + 1
            attacker["build"] = 0
            side = defend_side
            continue

        # --- construction ---
        min_build = 1 if press > 1.05 else 2
        if attacker["build"] < min_build:
            if not attempt_pass(attacker, defender):
                side = defend_side
            continue

        atk = _attack_score(attacker, defender, minute)
        dfn = _defense_score(defender, attacker, minute)
        edge = (atk - dfn) * EDGE_COEF
        shot_p = SHOT_BASE + edge * SHOT_EDGE + min(4, attacker["build"]) * SHOT_BUILD
        shot_p *= MENTALITY.get(attacker["mentality"], MENTALITY["Équilibrée"])["risk"]
        if attacker["is_home"]:
            shot_p += 0.015
        shot_p = _clamp(shot_p, 0.04, 0.72)
        if rng.random() >= shot_p:
            if not attempt_pass(attacker, defender):
                side = defend_side
            continue

        # --- frappe ---
        attacker["shots"] += 1
        attacker["build"] = 0
        kind_roll = rng.random()
        big_bonus = 0.04 if attacker["pressing"] == "Haut" else 0.0
        big_bonus += 0.05 if attacker["mentality"] == "Prudente" else (-0.03 if attacker["mentality"] == "Offensive" else 0.0)
        if kind_roll < 0.14 + big_bonus:
            quality = "nette"
        elif kind_roll < 0.80:
            quality = "normale"
        else:
            quality = "speculative"
        shooter = _shooter(attacker, rng)
        assist = None
        if rng.random() < 0.60:
            others = [p for p in attacker["players"] if p is not shooter]
            if others:
                assist = _pick(others, [max(1.0, _num(p, "passing", 45)) for p in others], rng)

        base_target = {"nette": 0.68, "normale": 0.53, "speculative": 0.32}[quality]
        target = _clamp(base_target + (_num(shooter, "finishing", 45) - defender["positioning"]) * 0.0022, 0.20, 0.86)
        goal_kind = None
        if rng.random() < target:
            attacker["on_target"] += 1
            base_conv = {"nette": 0.44, "normale": 0.225, "speculative": 0.075}[quality]
            conv = (base_conv
                    + (_num(shooter, "finishing", 45) - defender["keeper"]) * 0.0018
                    + (atk - dfn) * 0.0012)
            conv *= MENTALITY.get(attacker["mentality"], MENTALITY["Équilibrée"])["conv"]
            if attacker["is_home"]:
                conv += 0.020
            conv = _clamp(conv, 0.03, 0.55)
            if rng.random() < conv:
                goal_kind = "jeu"
            else:
                keeper = _keeper_of(defender)
                if keeper is not None and rng.random() < 0.018 * (1.15 - defender["form"]):
                    goal_kind = "erreur"
                else:
                    defender["saves"] += 1
        else:
            if rng.random() < 0.28:
                attacker["corners"] += 1
                if rng.random() < 0.055 + (atk - dfn) * 0.0006:
                    goal_kind = "corner"

        if goal_kind:
            add_goal(attack_side, minute, goal_kind, scorer=shooter, assist=assist)
            side = defend_side
            defender["build"] = 0
            continue

        side = defend_side
        attacker["build"] = 0

    return {
        "home": home, "away": away, "events": events,
        "goals_by_player": goals_by_player, "assists_by_player": assists_by_player,
        "referee": referee,
    }


def simulate_other_fixtures(host, conn, matchday, human_opponent_name=None, today=None):
    """Simule les matchs IA de la journee (championnat + coupe arrivee a echeance)."""
    from app import career_timestamp

    if today is None:
        today = str(conn.execute('SELECT career."current_date" AS current_date FROM career WHERE id=1').fetchone()["current_date"])

    fixtures = conn.execute("""SELECT f.*,hc.reputation home_rep,hc.division home_div,
                                   ac.reputation away_rep,ac.division away_div
                            FROM fixture f JOIN club hc ON hc.id=f.home_club_id
                            JOIN club ac ON ac.id=f.away_club_id
                            WHERE f.played=0 AND f.home_club_id<>1 AND f.away_club_id<>1
                              AND ((COALESCE(f.fixture_type,'championship')='championship' AND f.matchday=?)
                                OR (f.fixture_type='cup' AND f.fixture_date<=?))
                            ORDER BY f.id""", (matchday, today)).fetchall()

    rosters = {}
    club_names = {row["id"]: row["name"] for row in conn.execute("SELECT id,name FROM club").fetchall()}

    def club_match_data(club_id):
        if club_id in rosters:
            return rosters[club_id]
        eligible = conn.execute("SELECT * FROM player WHERE club_id=? AND is_free_agent=0 AND injury_matches<=0 AND injury_days<=0 AND suspension_matches<=0 ORDER BY id", (club_id,)).fetchall()
        all_players = conn.execute("SELECT * FROM player WHERE club_id=? AND is_free_agent=0 ORDER BY id", (club_id,)).fetchall()
        if len(eligible) < 5:
            for _ in range(3):
                signed = host.emergency_sign_free_agent(conn, club_id)
                if not signed:
                    break
                eligible.append(signed)
        if len(eligible) < 5:
            rosters[club_id] = {"all": all_players, "lineup": [], "profile": None, "tactics": {},
                                "forfeit": True,
                                "reason": f"{int(5-len(eligible))} joueur(s) valide(s) manquant(s)"}
            return rosters[club_id]
        lineup = host.select_club_match_five(eligible)
        profile = host.match_team_profile(lineup)
        club = conn.execute("SELECT division,reputation FROM club WHERE id=?", (club_id,)).fetchone()
        tactics = host.opponent_tactical_identity(club_id, club["division"] if club else 3, club["reputation"] if club else 30)
        rosters[club_id] = {"all": all_players, "lineup": lineup, "profile": profile,
                            "tactics": tactics, "forfeit": False}
        return rosters[club_id]

    for fixture in fixtures:
        seed_text = (f"league-fixture-v2|{int(fixture['season'])}|{int(fixture['id'])}|"
                     f"{int(fixture['home_club_id'])}|{int(fixture['away_club_id'])}")
        fixture_seed = int.from_bytes(hashlib.sha256(seed_text.encode("utf-8")).digest()[:8], "big") & ((1 << 63) - 1)
        rng = random.Random(fixture_seed)

        home_id = int(fixture["home_club_id"]); away_id = int(fixture["away_club_id"])
        home_data = club_match_data(home_id); away_data = club_match_data(away_id)

        if home_data.get("forfeit") or away_data.get("forfeit"):
            home_short = bool(home_data.get("forfeit")); away_short = bool(away_data.get("forfeit"))
            hg = 0 if home_short else 3; ag = 0 if away_short else 3
            if home_short and away_short:
                hg = 0; ag = 0
            conn.execute("UPDATE fixture SET played=1,home_goals=?,away_goals=? WHERE id=?", (hg, ag, fixture["id"]))
            ftype = int(str(fixture["fixture_type"] if "fixture_type" in fixture.keys() else "championship") == "championship")
            if ftype:
                host._update_standing(conn, home_id, hg, ag)
                host._update_standing(conn, away_id, ag, hg)
            for _cid in (home_id, away_id):
                conn.execute("UPDATE player SET injury_days=MAX(0,injury_days-1) WHERE club_id=? AND injury_days>0", (_cid,))
                conn.execute("UPDATE player SET suspension_matches=MAX(0,suspension_matches-1) WHERE club_id=? AND suspension_matches>0", (_cid,))
            forfeit_note = f"{club_names.get(home_id,'?')} {hg} - {ag} {club_names.get(away_id,'?')} (forfait)"
            conn.execute("INSERT OR REPLACE INTO ai_match_report(fixture_id,scorers,created_at) VALUES(?,?,?)",
                         (fixture["id"], json.dumps([{"forfeit": True, "minute": 0, "side": "h",
                                                      "team": club_names.get(home_id, "—"),
                                                      "scorer": forfeit_note, "assist": None}], ensure_ascii=False),
                          career_timestamp(conn)))
            continue

        home = _team_state("h", home_data["profile"], home_data["lineup"], home_data["tactics"],
                           fixture["home_rep"], True, rng)
        away = _team_state("a", away_data["profile"], away_data["lineup"], away_data["tactics"],
                           fixture["away_rep"], False, rng)
        home["team_name"] = club_names.get(home_id, "—")
        away["team_name"] = club_names.get(away_id, "—")

        result = _simulate_match(home, away, rng)
        goals = {"h": home["goals"], "a": away["goals"]}
        events = result["events"]

        conn.execute("UPDATE fixture SET played=1,home_goals=?,away_goals=? WHERE id=?",
                     (goals["h"], goals["a"], fixture["id"]))

        _ftype = str(fixture["fixture_type"] if "fixture_type" in fixture.keys() else "championship")
        if _ftype == "championship":
            host._update_standing(conn, home_id, goals["h"], goals["a"])
            host._update_standing(conn, away_id, goals["a"], goals["h"])
        elif goals["h"] == goals["a"]:
            rngc = random.Random(f"cup-shootout|{int(fixture['id'])}")
            hr = int(fixture["home_rep"] or 30); ar = int(fixture["away_rep"] or 30)
            winner = "h" if rngc.random() < (hr + 35.0) / max(1, hr + ar + 70) else "a"
            pens = (4, 3) if winner == "h" else (3, 4)
            events.append({"minute": 40, "side": winner, "team": "10 m",
                           "scorer": f"Séance de 10 m ({pens[0]}-{pens[1]})", "assist": None, "shootout": True})
            # Le score du temps réglementaire reste 2-2 : les 10 m désignent le qualifié.
            conn.execute("UPDATE fixture SET pen_home=?,pen_away=? WHERE id=?",
                         (pens[0], pens[1], fixture["id"]))

        for pid, count in result["goals_by_player"].items():
            conn.execute("UPDATE player SET season_goals=season_goals+? WHERE id=?", (int(count), int(pid)))
        for pid, count in result["assists_by_player"].items():
            conn.execute("UPDATE player SET season_assists=season_assists+? WHERE id=?", (int(count), int(pid)))

        home_gk = _keeper_of(home); away_gk = _keeper_of(away)
        if home_gk and int(goals["a"]) > 0:
            conn.execute("UPDATE player SET season_conceded=season_conceded+? WHERE id=?", (int(goals["a"]), int(home_gk["id"])))
        if away_gk and int(goals["h"]) > 0:
            conn.execute("UPDATE player SET season_conceded=season_conceded+? WHERE id=?", (int(goals["h"]), int(away_gk["id"])))
        if home_gk and int(home["saves"]):
            conn.execute("UPDATE player SET season_saves=season_saves+? WHERE id=?", (int(home["saves"]), int(home_gk["id"])))
        if away_gk and int(away["saves"]):
            conn.execute("UPDATE player SET season_saves=season_saves+? WHERE id=?", (int(away["saves"]), int(away_gk["id"])))

        for team_data in (home, away):
            for player in team_data["players"]:
                conn.execute("UPDATE player SET season_matches=season_matches+1 WHERE id=?", (int(player["id"]),))

        # Notes et cartons coherents avec le deroule.
        for code, team_data in (("h", home), ("a", away)):
            conceded = goals["a" if code == "h" else "h"]
            scored = goals[code]
            for player in team_data["players"]:
                pid = int(player["id"])
                plays = int(result["goals_by_player"].get(pid, 0))
                passes = int(result["assists_by_player"].get(pid, 0))
                note = 11.4 + rng.uniform(-1.1, 1.1) + plays * 2.1 + passes * 0.45
                if str(player.get("position")) == "Gardien":
                    note += int(team_data["saves"]) * 0.30
                    note += 0.5 if conceded == 0 else -0.30 * min(3, conceded)
                elif scored == 0:
                    note -= 0.5
                if scored > conceded:
                    note += 0.5
                elif scored < conceded:
                    note -= 0.4
                note = max(4.0, min(20.0, note))
                conn.execute("UPDATE player SET season_rating_sum=season_rating_sum+?, season_rating_count=season_rating_count+1 WHERE id=?",
                             (note, pid))
            for card in team_data["cards"]:
                player = card.get("player") or {}
                if not player.get("id"):
                    continue
                if card["type"] == "red":
                    conn.execute("UPDATE player SET suspension_matches=MAX(suspension_matches,1),season_red=season_red+1 WHERE id=?",
                                 (int(player["id"]),))
                else:
                    conn.execute("UPDATE player SET season_yellow=season_yellow+1 WHERE id=?", (int(player["id"]),))

        conn.execute("INSERT OR REPLACE INTO ai_match_report(fixture_id,scorers,created_at) VALUES(?,?,?)",
                     (fixture["id"], json.dumps(events, ensure_ascii=False), career_timestamp(conn)))

        for club_id, team_data in ((home_id, home), (away_id, away)):
            for injury in team_data["injuries"]:
                victim = injury.get("player") or {}
                if victim.get("id"):
                    conn.execute("UPDATE player SET injury_days=MAX(injury_days,?) WHERE id=?",
                                 (int(injury["days"]), int(victim["id"])))
            conn.execute("UPDATE player SET injury_days=MAX(0,injury_days-1) WHERE club_id=? AND injury_days>0", (club_id,))
            conn.execute("UPDATE player SET suspension_matches=MAX(0,suspension_matches-1) WHERE club_id=? AND suspension_matches>0", (club_id,))
            on_field = {int(p["id"]) for p in team_data["players"]}
            fatigue_points = max(2, int(round(2 + 6 * team_data["fatigue"])))
            for player in team_data["players"]:
                conn.execute("UPDATE player SET condition=MAX(10,condition-?) WHERE id=? AND club_id=?",
                             (fatigue_points, player["id"], club_id))
            if on_field:
                ph = ",".join("?" * len(on_field))
                conn.execute("UPDATE player SET condition=MIN(100,condition+3) WHERE club_id=? AND injury_days<=0 AND id NOT IN (%s)" % ph,
                             (club_id, *on_field))
