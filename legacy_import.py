import os
import re
from typing import List, Dict, Any, Tuple


def _extract_insert_blocks(sql_text: str, table: str) -> List[str]:
    pattern = re.compile(rf"INSERT INTO `{re.escape(table)}`\s*\([^)]*\)\s*VALUES\s*(.*?);", re.S)
    return [m.group(1) for m in pattern.finditer(sql_text)]


def _extract_tuples(values_blob: str) -> List[str]:
    tuples = []
    in_quote = False
    escape = False
    depth = 0
    current = []
    for ch in values_blob:
        if escape:
            current.append(ch)
            escape = False
            continue
        if ch == "\\":
            current.append(ch)
            escape = True
            continue
        if ch == "'":
            in_quote = not in_quote
            current.append(ch)
            continue
        if not in_quote:
            if ch == "(":
                depth += 1
                if depth == 1:
                    current = []
                    continue
            elif ch == ")":
                if depth == 1:
                    tuples.append("".join(current))
                    current = []
                    depth = 0
                    continue
                depth = max(0, depth - 1)
        if depth >= 1:
            current.append(ch)
    return tuples


def _split_fields(tuple_content: str) -> List[str]:
    fields = []
    in_quote = False
    escape = False
    current = []
    for ch in tuple_content:
        if escape:
            current.append(ch)
            escape = False
            continue
        if ch == "\\":
            current.append(ch)
            escape = True
            continue
        if ch == "'":
            in_quote = not in_quote
            current.append(ch)
            continue
        if ch == "," and not in_quote:
            fields.append("".join(current).strip())
            current = []
            continue
        current.append(ch)
    if current:
        fields.append("".join(current).strip())
    return fields


def _decode_sql_value(raw: str):
    raw = raw.strip()
    if raw.upper() == "NULL":
        return None
    if raw.startswith("'") and raw.endswith("'"):
        txt = raw[1:-1]
        txt = txt.replace("\\n", " ").replace("\\r", " ").replace("\\t", " ")
        txt = txt.replace("\\'", "'").replace("\\\\", "\\")
        return " ".join(txt.split()).strip()
    try:
        return int(raw)
    except Exception:
        return raw


def _scale_20_to_100(v: int) -> int:
    v = max(0, min(20, int(v)))
    return max(1, min(100, v * 5))


def _position_from_stats(p: Dict[str, int]) -> str:
    gk = (p["prise_balle"] + p["reflexe"] + p["sorti_pied"] + p["relance"] + p["diriger_def"]) / 5
    de = (p["marquage"] + p["anticipation"] + p["placement"] + p["decision"]) / 4
    at = (p["dribble"] + p["passe"] + p["technique"] + p["finition"] + p["appel_balle"]) / 5
    if gk >= de + 2 and gk >= at + 2:
        return "Gardien"
    if de >= at + 1.5:
        return "Défenseur"
    if at >= de + 2 and p["finition"] >= p["passe"]:
        return "Pivot"
    if at >= de:
        return "Ailier"
    return "Universel"


def _parse_legacy_clubs(sql_text: str, max_clubs: int = 40) -> List[Dict[str, Any]]:
    clubs = []
    seen = set()
    for block in _extract_insert_blocks(sql_text, "fk_equipe"):
        for tup in _extract_tuples(block):
            fields = [_decode_sql_value(x) for x in _split_fields(tup)]
            if len(fields) < 29:
                continue
            legacy_id = int(fields[0]) if isinstance(fields[0], int) else None
            name = str(fields[1] or "").strip()
            rep = int(fields[27] or 0) if str(fields[27]).isdigit() else 0
            if not name:
                continue
            k = name.lower()
            if k in seen:
                continue
            seen.add(k)
            clubs.append({"legacy_id": legacy_id, "name": name, "reputation": max(1, min(8, rep + 1))})
            if len(clubs) >= max_clubs:
                return clubs
    return clubs


def _parse_legacy_players(sql_text: str, max_players: int = 600) -> List[Dict[str, Any]]:
    players = []
    for block in _extract_insert_blocks(sql_text, "fk_joueurs"):
        for tup in _extract_tuples(block):
            fields = [_decode_sql_value(x) for x in _split_fields(tup)]
            if len(fields) < 42:
                continue
            stat = {
                "prise_balle": int(fields[8] or 0),
                "reflexe": int(fields[9] or 0),
                "sorti_pied": int(fields[10] or 0),
                "relance": int(fields[11] or 0),
                "diriger_def": int(fields[12] or 0),
                "marquage": int(fields[13] or 0),
                "anticipation": int(fields[14] or 0),
                "decision": int(fields[15] or 0),
                "placement": int(fields[17] or 0),
                "dribble": int(fields[18] or 0),
                "passe": int(fields[19] or 0),
                "technique": int(fields[22] or 0),
                "finition": int(fields[23] or 0),
                "appel_balle": int(fields[26] or 0),
                "endurance": int(fields[29] or 0),
            }
            first_name = str(fields[3] or "").strip().title() or "Joueur"
            last_name = str(fields[2] or "").strip().title() or "Legacy"
            age = int(fields[4] or 22)
            condition = int(fields[40] or 100)
            moral = int(fields[41] or 7)
            position = _position_from_stats(stat)
            players.append({
                "legacy_id": int(fields[0]) if isinstance(fields[0], int) else None,
                "first_name": first_name,
                "last_name": last_name,
                "age": max(16, min(40, age)),
                "position": position,
                "technique": _scale_20_to_100(stat["technique"]),
                "passing": _scale_20_to_100(stat["passe"]),
                "finishing": _scale_20_to_100(stat["finition"]),
                "defense": _scale_20_to_100(int((stat["marquage"] + stat["anticipation"] + stat["placement"]) / 3)),
                "goalkeeper": _scale_20_to_100(int((stat["prise_balle"] + stat["reflexe"] + stat["sorti_pied"] + stat["relance"]) / 4)),
                "stamina": _scale_20_to_100(stat["endurance"]),
                "condition": max(30, min(100, condition)),
                "morale": max(20, min(100, moral * 10 if moral <= 20 else moral)),
                "nationality": str(fields[5] or "Inconnue").strip() or "Inconnue",
            })
            if len(players) >= max_players:
                return players
    return players


def import_legacy_dump(conn, sql_path: str) -> Dict[str, int]:
    if not os.path.exists(sql_path):
        return {"clubs": 0, "players": 0}

    sql_text = open(sql_path, "r", encoding="latin-1", errors="ignore").read()
    clubs = _parse_legacy_clubs(sql_text, max_clubs=40)
    players = _parse_legacy_players(sql_text, max_players=640)
    if not clubs or not players:
        return {"clubs": 0, "players": 0}

    conn.execute("DELETE FROM match_record")
    conn.execute("DELETE FROM player")
    conn.execute("DELETE FROM career")
    conn.execute("DELETE FROM club")

    managed_name = "Paris Futsal"
    managed = None
    for c in clubs:
        if c["name"].lower() == managed_name.lower():
            managed = c
            break
    if managed is None:
        managed = clubs[0]

    ordered = [managed] + [c for c in clubs if c is not managed]
    old_to_new = {}
    for idx, c in enumerate(ordered, start=1):
        old_to_new[c["legacy_id"]] = idx
        budget = 180000 + c["reputation"] * 45000
        conn.execute(
            "INSERT INTO club(id,name,reputation,budget,season,legacy_id) VALUES(?,?,?,?,1,?)",
            (idx, c["name"], c["reputation"], budget, c["legacy_id"]),
        )

    conn.execute("INSERT INTO career(id,club_id,matchday,wins,draws,losses,goals_for,goals_against,points) VALUES(1,1,1,0,0,0,0,0,0)")

    club_count = len(ordered)
    # Répartition simple des joueurs: priorité au club géré puis rotation.
    assigned = 0
    for p in players:
        club_id = 1 if assigned < 14 else ((assigned - 14) % max(1, club_count - 1)) + 2
        assigned += 1
        conn.execute(
            """INSERT INTO player(club_id,first_name,last_name,age,position,technique,passing,finishing,defense,goalkeeper,stamina,condition,morale,nationality,injury_matches,legacy_id)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,0,?)""",
            (
                club_id,
                p["first_name"],
                p["last_name"],
                p["age"],
                p["position"],
                p["technique"],
                p["passing"],
                p["finishing"],
                p["defense"],
                p["goalkeeper"],
                p["stamina"],
                p["condition"],
                p["morale"],
                p["nationality"],
                p["legacy_id"],
            ),
        )

    return {"clubs": len(ordered), "players": len(players)}
