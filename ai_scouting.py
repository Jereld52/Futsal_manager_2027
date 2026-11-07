# -*- coding: utf-8 -*-
"""Perception des clubs IA et fin de carrière des libres non désirés.

Les clubs IA ne lisent plus la vraie valeur d'un joueur : ils le supervisent
comme le ferait un recruteur. Chaque observation fait progresser une
connaissance propre au club (`ai_scout_knowledge`) ; l'erreur d'estimation
diminue avec cette connaissance, si bien qu'un club peut se tromper sur un
joueur, le surestimer ou passer à côté d'une pépite.

Un joueur libre que PERSONNE n'a signé pendant une saison met fin à sa
carrière, même s'il est jeune : le marché se nettoie naturellement.
"""
import random
from datetime import timedelta

from club_profiles import profile_for, signing_score

FREE_AGENT_RETIRE_DAYS = 330


def ensure_table(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS ai_scout_knowledge(
        club_id INTEGER NOT NULL,
        player_id INTEGER NOT NULL,
        knowledge INTEGER NOT NULL DEFAULT 0,
        updated_date TEXT NOT NULL DEFAULT '',
        PRIMARY KEY(club_id,player_id))""")


def knowledge_of(conn, club_id, player_id):
    try:
        row = conn.execute("SELECT knowledge FROM ai_scout_knowledge WHERE club_id=? AND player_id=?",
                           (int(club_id), int(player_id))).fetchone()
        return int(row["knowledge"] or 0) if row else 0
    except Exception:
        return 0


def scout_player(conn, club, player, current_iso_date, persist=True):
    """Retourne (niveau perçu sur 20, connaissance 0-100).

    Plus le club connaît le joueur, plus l'estimation se rapproche du vrai
    niveau. À connaissance nulle, l'écart type est proche de 5 niveaux.
    """
    from app import player_level_from_row
    cid = int(club["id"])
    pid = int(player["id"])
    reputation = int(club["reputation"] or 20)
    division = int(club["division"] or 6)
    gain = 9 + reputation // 10 + (2 if division <= 2 else 1 if division <= 4 else 0)
    knowledge = min(100, knowledge_of(conn, cid, pid) + gain)
    if persist:
        try:
            conn.execute("""INSERT INTO ai_scout_knowledge(club_id,player_id,knowledge,updated_date)
                            VALUES(?,?,?,?)
                            ON CONFLICT(club_id,player_id) DO UPDATE SET
                                knowledge=excluded.knowledge,updated_date=excluded.updated_date""",
                         (cid, pid, knowledge, current_iso_date))
        except Exception:
            pass
    true_level = float(player_level_from_row(player))
    spread = max(0.35, 4.9 * (1.0 - knowledge / 100.0))
    perceived = true_level + random.gauss(0, spread)
    return max(1.0, min(20.0, perceived)), knowledge


def rank_free_agents(conn, club, current_iso_date, pool=14, known=5):
    """Classe un échantillon de libres selon la perception du club.

    Le club ne voit pas tout le marché : il supervise un petit lot au hasard
    et les joueurs qu'il connaît déjà. Retourne [{player, level, knowledge}] trié.
    """
    cid = int(club["id"])
    profile = profile_for(None, club)
    if not current_iso_date:
        try:
            current_iso_date = str(conn.execute('SELECT "current_date" d FROM career WHERE id=1').fetchone()["d"])
        except Exception:
            current_iso_date = ""
    rows = conn.execute("""SELECT * FROM player WHERE is_free_agent=1 AND COALESCE(retired,0)=0
                           AND injury_days<=0 AND injury_matches<=0
                           ORDER BY RANDOM() LIMIT ?""", (max(4, int(pool)),)).fetchall()
    try:
        known_rows = conn.execute("""SELECT p.* FROM player p
                                     JOIN ai_scout_knowledge k ON k.player_id=p.id
                                     WHERE p.is_free_agent=1 AND COALESCE(p.retired,0)=0
                                       AND k.club_id=? AND k.knowledge>=30
                                     ORDER BY k.knowledge DESC, RANDOM() LIMIT ?""",
                                  (cid, max(0, int(known)))).fetchall()
    except Exception:
        known_rows = []
    seen = set()
    scored = []
    for player in list(known_rows) + list(rows):
        pid = int(player["id"])
        if pid in seen:
            continue
        seen.add(pid)
        perceived, knowledge = scout_player(conn, club, player, current_iso_date)
        score = signing_score(profile, player, perceived, int(player["salary"] or 0))
        scored.append({"player": player, "level": perceived, "knowledge": knowledge,
                       "score": score, "profile": profile["label"]})
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored


def retire_unwanted_free_agents(host, conn, current_iso_date, days=FREE_AGENT_RETIRE_DAYS):
    """Retraite les libres sans club depuis plus de `days` jours, sans limite d'âge."""
    from app import parse_iso, record_player_history, add_news, queue_manager_message
    try:
        cut = parse_iso(current_iso_date) - timedelta(days=int(days))
        rows = conn.execute("""SELECT * FROM player WHERE COALESCE(is_free_agent,0)=1
                               AND COALESCE(retired,0)=0 AND COALESCE(free_agent_since,'')<>''""").fetchall()
        retired = []
        retired_ids = []
        for p in rows:
            try:
                since = parse_iso(str(p["free_agent_since"]))
            except Exception:
                continue
            if since > cut:
                continue
            pid = int(p["id"])
            conn.execute("""UPDATE player SET retired=1,retired_date=?,club_id=0,is_free_agent=0,
                                                 transfer_listed=0,contract_years=0,salary=0,
                                                 shirt_number=0,free_agent_since='' WHERE id=?""",
                         (str(current_iso_date), pid))
            record_player_history(conn, pid, 0, "retraite",
                                  "Libre sans club pendant une saison — fin de carrière")
            retired.append(f"{p['first_name']} {p['last_name']} ({int(p['age'] or 0)} ans)")
            retired_ids.append(pid)
        if retired:
            body = ("Aucun club n'a proposé de contrat : " + " ; ".join(retired[:8]) +
                    (" ..." if len(retired) > 8 else "") + " mettent fin à leur carrière.")
            add_news(conn, "Marché des libres", body)
            try:
                queue_manager_message(conn, "club_news", "Libres non signés : fins de carrière",
                                      body, str(current_iso_date), str(current_iso_date),
                                      {"player_ids": retired_ids},
                                      is_read=False, ready=True)
            except Exception:
                pass
        return len(retired)
    except Exception as exc:
        try:
            host.log_error("free_agent_retirements", exc)
        except Exception:
            pass
        return 0
