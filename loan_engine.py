# -*- coding: utf-8 -*-
"""Prêts sortants : un jeune du club est prêté à un club IA pour la saison.

Le prêt dure jusqu'à la fin de la saison en cours :
- le joueur quitte l'effectif (club_id = club emprunteur, loan_from_club = 1) ;
- il joue chaque semaine selon la promesse faite (titulaire / rotation),
  progresse et son moral dépend de son temps de jeu ;
- il peut être rappelé à tout moment par le manager ;
- il revient automatiquement au club à la clôture de la saison.
"""
import random

MAX_OUTGOING = 3
MIN_SQUAD_AFTER = 11   # le garde-fou hebdomadaire reconstruit ensuite un effectif de 12
MAX_AGE_LOAN = 23


def _levels(conn, club_id):
    """Niveaux (sur 20) des joueurs valides d'un club."""
    from app import player_level_from_row
    rows = conn.execute(
        "SELECT * FROM player WHERE club_id=? AND COALESCE(is_free_agent,0)=0 AND COALESCE(retired,0)=0",
        (int(club_id),)).fetchall()
    return [player_level_from_row(p) for p in rows]


def outgoing_loans(conn):
    """Joueurs du manager actuellement prêtés ailleurs."""
    return conn.execute(
        """SELECT p.*, c.name club_name, c.division club_division
           FROM player p JOIN club c ON c.id=p.club_id
           WHERE COALESCE(p.loan_from_club,0)=1 AND p.club_id<>1 AND COALESCE(p.retired,0)=0
           ORDER BY p.last_name, p.first_name""").fetchall()


def outgoing_count(conn):
    try:
        return len(outgoing_loans(conn))
    except Exception:
        return 0


def loan_out_block_reason(conn, player):
    """Raison pour laquelle ce joueur ne peut pas être prêté (None = éligible)."""
    if not player:
        return "Joueur introuvable."
    if int(player["club_id"] or 0) != 1 or int(player["is_free_agent"] or 0):
        return "Seul un joueur de ton effectif peut être prêté."
    if int(player["loan_from_club"] or 0) if "loan_from_club" in player.keys() else 0:
        return "Ce joueur appartient déjà à un autre club (prêt entrant)."
    if int(player["age"] or 24) > MAX_AGE_LOAN:
        return f"Les prêts sortants sont réservés aux moins de {MAX_AGE_LOAN + 1} ans."
    if outgoing_count(conn) >= MAX_OUTGOING:
        return f"Trois prêts sortants maximum ({MAX_OUTGOING}) : rappelle un joueur avant d'en prêter un autre."
    squad = int(conn.execute(
        "SELECT COUNT(*) n FROM player WHERE club_id=1 AND COALESCE(is_free_agent,0)=0").fetchone()["n"] or 0)
    if squad - 1 < MIN_SQUAD_AFTER:
        return f"Ton effectif ne peut pas descendre sous {MIN_SQUAD_AFTER} joueurs : recrute d'abord."
    if int(player["injury_days"] or 0) > 0 or int(player["injury_matches"] or 0) > 0:
        return "Un joueur blessé ne part pas en prêt."
    return None


def loan_candidates(conn, player_id):
    """Trois clubs IA intéressés par le joueur (même division ou en dessous)."""
    player = conn.execute(
        "SELECT p.*, c.division club_division FROM player p JOIN club c ON c.id=p.club_id WHERE p.id=?",
        (int(player_id),)).fetchone()
    if not player or loan_out_block_reason(conn, player):
        return []
    my_div = int(player["club_division"] or 6)
    level = None
    rows = conn.execute(
        """SELECT c.id,c.name,c.division,c.reputation,
                  (SELECT COUNT(*) FROM player x
                    WHERE x.club_id=c.id AND COALESCE(x.is_free_agent,0)=0 AND COALESCE(x.retired,0)=0) n
           FROM club c WHERE c.id<>1 AND c.division>=?""", (my_div,)).fetchall()
    pool = []
    for row in rows:
        count = int(row["n"] or 0)
        if count >= 16 or count < 8:
            continue
        levels = _levels(conn, int(row["id"]))
        avg = (sum(levels) / len(levels)) if levels else 0.0
        if level is None:
            from app import player_level_from_row
            level = player_level_from_row(player)
        gap = level - avg
        if gap < -4.0:
            continue
        need = max(0, 13 - count)
        score = need * 3 + min(3.0, max(-3.0, gap)) + (1.0 if int(row["division"]) == my_div else 0.0)
        pool.append({"id": int(row["id"]), "name": row["name"], "division": int(row["division"]),
                     "count": count, "avg": round(avg, 1), "gap": round(gap, 1),
                     "score": score, "need": need})
    if not pool:
        # Vivier très maigre : on accepte les clubs à effectif réduit.
        for row in rows:
            count = int(row["n"] or 0)
            if count >= 16 or count < 5:
                continue
            levels = _levels(conn, int(row["id"]))
            avg = (sum(levels) / len(levels)) if levels else 0.0
            if level is None:
                from app import player_level_from_row
                level = player_level_from_row(player)
            gap = level - avg
            if gap < -4.0:
                continue
            pool.append({"id": int(row["id"]), "name": row["name"], "division": int(row["division"]),
                         "count": count, "avg": round(avg, 1), "gap": round(gap, 1),
                         "score": max(0, 13 - count) * 3, "need": max(0, 13 - count)})
    pool.sort(key=lambda c: (-c["score"], -c["need"], c["name"]))
    top = pool[:6]
    random.shuffle(top)
    top.sort(key=lambda c: (-c["score"], c["name"]))
    return top[:3]


def request_loan_out(host, player_id, destination_id, promise):
    """Envoie la demande de prêt ; la réponse arrive sous 1 à 3 jours."""
    from app import (db, parse_iso, timedelta, queue_manager_message, add_news, fmt_date_fr)
    conn = db()
    try:
        window = host.transfer_window_state(conn)
        if not window["open"]:
            from app import fmt_date_fr as _fmt
            host.show_game_message(
                "Mercato fermé",
                f"Les prêts se règlent pendant une fenêtre (réouverture le {_fmt(window['reopens'].isoformat())}).",
                "warning")
            return False
        player = conn.execute(
            "SELECT p.*, c.name club_name FROM player p JOIN club c ON c.id=p.club_id WHERE p.id=?",
            (int(player_id),)).fetchone()
        reason = loan_out_block_reason(conn, player)
        if reason:
            host.show_game_message("Prêt impossible", reason, "warning")
            return False
        dest = conn.execute("SELECT id,name,division FROM club WHERE id=?", (int(destination_id),)).fetchone()
        if not dest or int(dest["id"]) == 1:
            host.show_game_message("Prêt impossible", "Ce club ne peut pas accueillir le joueur.", "warning")
            return False
        active = conn.execute(
            "SELECT action_data FROM manager_message WHERE kind='loan_out_request' AND status IN ('waiting','ready')").fetchall()
        import json
        if any(json.loads(row["action_data"] or "{}").get("player_id") == int(player_id) for row in active):
            host.show_game_message("Demande en cours", "Une demande de prêt est déjà partie pour ce joueur.", "info")
            return False
        current = host._current_date(conn)
        due = (parse_iso(current) + timedelta(days=random.randint(1, 3))).isoformat()
        data = {"player_id": int(player_id), "player_name": f"{player['first_name']} {player['last_name']}",
                "to_club": int(dest["id"]), "club_name": dest["name"], "promise": promise}
        queue_manager_message(
            conn, "loan_out_request", "Demande de prêt sortant envoyée",
            f"{dest['name']} (Ligue {dest['division']}) étudie l'accueil de "
            f"{player['first_name']} {player['last_name']} avec une promesse de {promise.lower()}. "
            f"Réponse attendue le {fmt_date_fr(due)}.",
            current, due, data, is_read=True)
        add_news(conn, "Prêt", f"Demande de prêt envoyée : {player['first_name']} {player['last_name']} "
                               f"pourrait rejoindre {dest['name']} jusqu'à la fin de la saison.")
        conn.commit()
    except Exception as exc:
        host.log_error("request_loan_out", exc)
        return False
    finally:
        conn.close()
    host.refresh_all()
    host.show_game_message(
        "Demande envoyée",
        f"{dest['name']} analyse le dossier. Réponse sous 1 à 3 jours dans la messagerie.",
        "success")
    return True


def resolve_outgoing_loan(host, conn, data):
    """Décision du club IA. Retourne (outcome, titre, corps du message)."""
    from app import (player_level_from_row, next_shirt_number, record_player_history, add_news)
    player = conn.execute(
        "SELECT p.*, c.name club_name FROM player p JOIN club c ON c.id=p.club_id WHERE p.id=?",
        (data.get("player_id"),)).fetchone()
    name = data.get("player_name") or "Le joueur"
    if (not player or int(player["club_id"] or 0) != 1 or int(player["is_free_agent"] or 0)
            or int(player["loan_from_club"] or 0) or int(player["retired"] or 0)):
        return "unavailable", "Prêt annulé", f"{name} n'est plus disponible pour un prêt."
    dest = conn.execute("SELECT * FROM club WHERE id=?", (data.get("to_club"),)).fetchone()
    if not dest:
        return "unavailable", "Prêt annulé", "Le club destinataire n'existe plus."
    if outgoing_count(conn) >= MAX_OUTGOING:
        return "refused", "Prêt refusé", f"Le club a déjà {MAX_OUTGOING} joueurs prêtés : rappelle-en un avant."
    promise = str(data.get("promise") or "ROTATION").upper()
    if promise not in ("TITULAIRE", "ROTATION"):
        promise = "ROTATION"

    squad = conn.execute(
        "SELECT COUNT(*) n FROM player WHERE club_id=? AND COALESCE(is_free_agent,0)=0 AND COALESCE(retired,0)=0",
        (int(dest["id"]),)).fetchone()
    count = int(squad["n"] or 0)
    if count >= 16:
        return "refused", "Prêt refusé", f"{dest['name']} a déjà {count} joueurs : pas de place pour un prêt."
    levels = _levels(conn, int(dest["id"]))
    avg = (sum(levels) / len(levels)) if levels else 0.0
    gap = player_level_from_row(player) - avg
    if gap < -4.0:
        return "refused", "Prêt refusé", f"{dest['name']} juge le niveau trop juste pour son groupe ({gap:+.1f})."
    if promise == "TITULAIRE" and gap < -0.8:
        return "refused", "Prêt refusé", f"{dest['name']} ne garantit pas une place de titulaire à {name}."
    if random.random() < 0.12:
        return "refused", "Prêt refusé", f"{dest['name']} a finalement choisi une autre piste pour ce poste."

    season = int(conn.execute("SELECT season FROM club WHERE id=1").fetchone()["season"] or 1)
    number = next_shirt_number(conn, int(dest["id"]))
    today = conn.execute('SELECT "current_date" FROM career WHERE id=1').fetchone()["current_date"]
    conn.execute(
        """UPDATE player SET club_id=?,is_free_agent=0,transfer_listed=0,shirt_number=?,
                            loan_from_club=1,loan_until_season=?,loan_promise=?,
                            loan_start_matches=?,loan_start_date=? WHERE id=?""",
        (int(dest["id"]), number, season, promise,
         int(player["season_matches"] or 0), today, int(player["id"])))
    record_player_history(conn, int(player["id"]), int(dest["id"]), "transfer",
                          f"Prêt sortant vers {dest['name']}")
    add_news(conn, "Prêt", f"{name} est prêté à {dest['name']} (Ligue {dest['division']}) "
                           f"jusqu'à la fin de la saison — promesse : {promise.lower()}.")
    try:
        host.close_player_dossiers(conn, int(player["id"]), reason="Prêt sortant")
    except Exception:
        pass
    try:
        for zone in getattr(host, "pitch_zones", {}).values():
            if zone.player_id == int(player["id"]):
                zone.reset_zone()
    except Exception:
        pass
    body = (f"{dest['name']} accueille {name} en prêt jusqu'à la fin de la saison. "
            f"Rôle promis : {promise.lower()}. Il reste rappelable depuis l'onglet PRÊTS.")
    if gap >= 0:
        body += " Son niveau s'intègre bien au groupe."
    else:
        body += " Il devra gagner sa place."
    return "accepted", "Prêt accepté", body


def process_outgoing_loans(host, conn, current_iso_date):
    """Chaque lundi : temps de jeu, note, moral et progression des prêtés."""
    from app import parse_iso, player_level_from_row, player_potential_from_row, add_news
    try:
        if parse_iso(current_iso_date).weekday() != 0:
            return 0
        rows = outgoing_loans(conn)
        if not rows:
            return 0
        played_notes = []
        for p in rows:
            pid = int(p["id"])
            name = f"{p['first_name']} {p['last_name']}"
            promise = "TITULAIRE" if str(p["loan_promise"] or "").upper() == "TITULAIRE" else "ROTATION"
            levels = _levels(conn, int(p["club_id"]))
            avg = (sum(levels) / len(levels)) if levels else 0.0
            level = player_level_from_row(p)
            chance = 0.88 if promise == "TITULAIRE" else 0.55
            # Un joueur nettement au-dessus du groupe joue quasi toujours.
            if level - avg >= 2.0:
                chance = min(0.96, chance + 0.08)
            if random.random() <= chance:
                # Notes sur 20, comme les matchs du manager et les matchs IA.
                rating = 11.3 + max(-2.4, min(2.8, (level - avg) * 0.44)) + random.gauss(0, 1.1)
                rating = round(max(4.0, min(20.0, rating)), 1)
                condition_loss = random.randint(4, 9)
                conn.execute(
                    """UPDATE player SET season_matches=season_matches+1,
                                         season_rating_sum=season_rating_sum+?,season_rating_count=season_rating_count+1,
                                         condition=MAX(25,condition-?),morale=MIN(100,morale+?) WHERE id=?""",
                    (rating, condition_loss, 1 if rating >= 11.5 else -1, pid))
                position = str(p["position"] or "")
                goal_chance = {"Pivot": 0.55, "Ailier": 0.40, "Universel": 0.25,
                               "Défenseur": 0.12, "Gardien": 0.01}.get(position, 0.2)
                goals = 1 if random.random() < goal_chance else 0
                assists = 1 if random.random() < goal_chance * 0.7 else 0
                if goals:
                    conn.execute("UPDATE player SET season_goals=season_goals+? WHERE id=?", (goals, pid))
                if assists:
                    conn.execute("UPDATE player SET season_assists=season_assists+? WHERE id=?", (assists, pid))
                played_notes.append((name, rating))
            else:
                conn.execute("UPDATE player SET morale=MAX(30,morale-1) WHERE id=?", (pid,))
            # Progression : le temps de jeu accélère la marge de potentiel.
            if random.random() < (0.55 if promise == "TITULAIRE" else 0.38):
                potential = int(round(player_potential_from_row(p) * 5))
                attrs = [a for a in ("technique", "passing", "finishing", "defense", "dribble", "speed", "positioning")
                         if int(p[a] or 0) < potential]
                if attrs:
                    attr = random.choice(attrs)
                    conn.execute(f"UPDATE player SET {attr}=MIN(?,{attr}+1) WHERE id=?", (potential, pid))
        if played_notes:
            best = max(played_notes, key=lambda n: n[1])
            add_news(conn, "Prêt",
                     f"Prêts : {len(played_notes)} joueur(s) ont joué cette semaine. "
                     f"Meilleure note : {best[0]} ({best[1]}/20).")
        return len(played_notes)
    except Exception as exc:
        host.log_error("process_outgoing_loans", exc)
        return 0


def return_outgoing_loans(host, conn, current_season):
    """Fin de saison : les prêtés reviennent au club avec leur bilan."""
    from app import record_player_history, add_news, repair_shirt_numbers
    try:
        rows = conn.execute(
            """SELECT * FROM player WHERE COALESCE(loan_from_club,0)=1 AND club_id<>1
               AND COALESCE(loan_until_season,0)<=? AND COALESCE(retired,0)=0""",
            (int(current_season),)).fetchall()
        returned = []
        for p in rows:
            pid = int(p["id"])
            matches = int(p["season_matches"] or 0)
            goals = int(p["season_goals"] or 0)
            assists = int(p["season_assists"] or 0)
            rcount = int(p["season_rating_count"] or 0)
            avg = (float(p["season_rating_sum"] or 0) / rcount) if rcount else 0.0
            detail = f"Retour de prêt ({matches} match(s), {goals} but(s), {assists} passe(s) décisive(s)"
            detail += f", note {avg:.2f})" if rcount else ")"
            conn.execute(
                """UPDATE player SET club_id=1,loan_from_club=0,loan_until_season=0,loan_promise='',
                                     transfer_listed=0,shirt_number=0 WHERE id=?""", (pid,))
            record_player_history(conn, pid, 1, "transfer", detail)
            returned.append(f"{p['first_name']} {p['last_name']} ({matches} matchs)")
        if returned:
            try:
                repair_shirt_numbers(conn)
            except Exception:
                pass
            add_news(conn, "Prêt", "Fin de saison : retour de prêt de " + ", ".join(returned) + ".")
        return len(returned)
    except Exception as exc:
        host.log_error("return_outgoing_loans", exc)
        return 0


def recall_loaned_player(host, player_id):
    """Rappelle immédiatement un joueur prêté ailleurs."""
    from app import db, record_player_history, add_news, repair_shirt_numbers
    conn = db()
    try:
        player = conn.execute(
            "SELECT * FROM player WHERE id=? AND COALESCE(loan_from_club,0)=1 AND club_id<>1",
            (int(player_id),)).fetchone()
        if not player:
            host.show_game_message("Rappel impossible", "Ce joueur n'est pas prêté par ton club.", "info")
            return False
        club = conn.execute("SELECT name FROM club WHERE id=?", (int(player["club_id"]),)).fetchone()
        where = club["name"] if club else "son club"
        answer = host.show_game_message(
            "Rappeler le joueur",
            f"Rappeler {player['first_name']} {player['last_name']} ?\n"
            f"Il quittera {where} immédiatement et réintégrera ton effectif.",
            "warning", confirm=True, confirm_text="RAPPELER")
        if not answer:
            return False
        conn.execute(
            """UPDATE player SET club_id=1,loan_from_club=0,loan_until_season=0,loan_promise='',
                                 transfer_listed=0,shirt_number=0 WHERE id=?""", (int(player_id),))
        record_player_history(conn, int(player_id), 1, "transfer", f"Rappel de prêt ({where})")
        add_news(conn, "Prêt", f"{player['first_name']} {player['last_name']} est rappelé de son prêt à {where}.")
        try:
            repair_shirt_numbers(conn)
        except Exception:
            pass
        conn.commit()
    except Exception as exc:
        host.log_error("recall_loaned_player", exc)
        return False
    finally:
        conn.close()
    for zone in getattr(host, "pitch_zones", {}).values():
        if zone.player_id == int(player_id):
            zone.reset_zone()
    host.refresh_all()
    try:
        host.persist_tactics_settings()
    except Exception:
        pass
    host.show_game_message("Joueur rappelé",
                           f"{player['first_name']} {player['last_name']} réintègre l'effectif.", "success")
    return True
