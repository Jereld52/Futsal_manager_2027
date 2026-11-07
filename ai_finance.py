# -*- coding: utf-8 -*-
"""Finances reelles des clubs IA et marche secondaire.

Chaque club IA encaisse des revenus mensuels (droits TV, billetterie,
sponsors) et paie la masse salariale de son effectif ainsi que l'entretien de
ses installations. Un club dans le rouge place ses gros salaires sur le
marche ; les clubs riches ou ambitieux peuvent les acheter.
"""
import random

from club_profiles import profile_for


def division_base(division):
    from app import LEAGUE_DEFINITIONS
    division = max(1, min(6, int(division or 3)))
    return int(LEAGUE_DEFINITIONS[division - 1][3])


def monthly_income(conn, club):
    """Revenus mensuels estimes : base division x reputation x profil."""
    p = profile_for(conn, club)
    division = max(1, min(6, int(club["division"] or 3)))
    base = max(28_000.0, division_base(division) / 36.0)
    reputation = max(0, min(100, int(club["reputation"] or 0)))
    rep_factor = 0.55 + 0.45 * (reputation / 100.0)
    return int(base * rep_factor * float(p.get("income", 1.0)))


def wage_bill(conn, club_id):
    try:
        row = conn.execute("""SELECT COALESCE(SUM(salary),0) s FROM player
                              WHERE club_id=? AND COALESCE(is_free_agent,0)=0
                                AND COALESCE(retired,0)=0""", (int(club_id),)).fetchone()
        return int(row["s"] or 0)
    except Exception:
        return 0


def upkeep(conn, club):
    p = profile_for(conn, club)
    base = max(28_000.0, division_base(int(club["division"] or 3)) / 36.0)
    return int(base * float(p.get("upkeep", 0.10)))


def monthly_net(conn, club):
    return int(monthly_income(conn, club) - wage_bill(conn, int(club["id"])) - upkeep(conn, club))


def can_afford(conn, club, salary, signing_cost=0, emergency=False):
    """Le club peut-il assumer ce salaire et ce cout de signature ?"""
    p = profile_for(conn, club)
    budget = int(club["budget"] or 0)
    salary = int(salary or 0)
    signing_cost = int(signing_cost or 0)
    if budget <= 0:
        return False
    if budget < signing_cost + salary * 3:
        return False
    ratio = float(p.get("wage_ratio", 0.62))
    if emergency:
        ratio = max(ratio, 0.85)
    room = monthly_income(conn, club) * ratio - wage_bill(conn, int(club["id"]))
    return salary <= max(600.0, room)


def _market_news(conn, body, current_iso_date=None, limit=2):
    """News marché filtrée : seuls les mouvements notables, 2 par jour maximum.

    Sans ce garde-fou, chaque transfert/liste/signature IA inondait le fil
    d'actualité (« Marché des transferts » en boucle) et masquait les news
    importantes (trésorerie, coupe, saison)."""
    try:
        from app import add_news
        key = "market_news_%s" % (str(current_iso_date or "x")[:10])
        row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        count = int(row["value"] or 0) if row else 0
        if count >= int(limit):
            return False
        conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)", (key, str(count + 1)))
        add_news(conn, "Marché des transferts", body)
        return True
    except Exception:
        return False


def list_player(host, conn, club, player, reason):
    pid = int(player["id"])
    if int(player["transfer_listed"] or 0):
        return False
    # Ne jamais descendre sous 11 joueurs sous contrat pour une simple vente.
    size = int(conn.execute("""SELECT COUNT(*) n FROM player WHERE club_id=?
                               AND COALESCE(is_free_agent,0)=0 AND COALESCE(retired,0)=0""",
                            (int(club["id"]),)).fetchone()["n"] or 0)
    if size <= 11:
        return False
    conn.execute("UPDATE player SET transfer_listed=1 WHERE id=?", (pid,))
    try:
        if int(player["market_value"] or 0) >= 60000:
            date = None
            try:
                date = host._current_date(conn)
            except Exception:
                date = None
            _market_news(conn,
                         f"{club['name']} place {player['first_name']} {player['last_name']} sur le marché "
                         f"({reason}).", date, limit=2)
    except Exception:
        pass
    return True


def process_ai_monthly_finances(host, conn, current_iso_date):
    """Le 1er du mois : revenus, salaires, entretien, cap et pression financiere."""
    from app import parse_iso
    try:
        if parse_iso(current_iso_date).day != 1:
            return 0
        month_key = str(current_iso_date)[:7]
        guard = conn.execute("SELECT value FROM meta WHERE key='ai_finance_month'").fetchone()
        if guard and str(guard["value"] or "") == month_key:
            return 0
        clubs = conn.execute("SELECT * FROM club WHERE id<>1").fetchall()
        processed = 0
        for club in clubs:
            cid = int(club["id"])
            income = monthly_income(conn, club)
            wages = wage_bill(conn, cid)
            costs = upkeep(conn, club)
            net = income - wages - costs
            budget = int(club["budget"] or 0) + net
            conn.execute("UPDATE club SET budget=? WHERE id=?", (budget, cid))
            processed += 1

            # Pression financiere : le club met un gros salaire sur le marche.
            if budget < 0 or (income and wages > income * 0.95):
                top = conn.execute("""SELECT * FROM player WHERE club_id=? AND COALESCE(is_free_agent,0)=0
                                      AND COALESCE(retired,0)=0 AND COALESCE(loan_from_club,0)=0
                                      ORDER BY salary DESC, market_value ASC LIMIT 8""", (cid,)).fetchall()
                for candidate in top:
                    if list_player(host, conn, club, candidate,
                                   "budget dans le rouge" if budget < 0 else "masse salariale trop lourde"):
                        break

            # Degraissage : un effectif de plus de 13 joueurs place un element.
            size = int(conn.execute("""SELECT COUNT(*) n FROM player WHERE club_id=?
                                       AND COALESCE(is_free_agent,0)=0 AND COALESCE(retired,0)=0""",
                                    (cid,)).fetchone()["n"] or 0)
            if size > 13 and random.random() < 0.35:
                spare = conn.execute("""SELECT * FROM player WHERE club_id=? AND COALESCE(is_free_agent,0)=0
                                        AND COALESCE(retired,0)=0 AND COALESCE(transfer_listed,0)=0
                                        ORDER BY market_value ASC, age DESC LIMIT 1""", (cid,)).fetchone()
                if spare:
                    list_player(host, conn, club, spare, "effectif trop large")
        conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('ai_finance_month',?)", (month_key,))
        return processed
    except Exception as exc:
        try:
            host.log_error("ai_finances", exc)
        except Exception:
            pass
        return 0


def process_ai_transfer_market(host, conn, current_iso_date):
    """Marché secondaire IA-IA : les clubs achètent les joueurs listés.

    Le club du manager n'est jamais acheteur ni vendeur ici : ses propres
    transferts passent par la messagerie et ses décisions.
    """
    from app import parse_iso, next_shirt_number, record_player_history, add_news
    from ai_scouting import scout_player
    from club_profiles import signing_score
    from ai_clubs import transfer_behavior
    try:
        if parse_iso(current_iso_date).weekday() != 2:  # mercredi
            return 0
        listed = conn.execute("""SELECT * FROM player WHERE COALESCE(transfer_listed,0)=1
                                 AND club_id NOT IN (0,1) AND COALESCE(is_free_agent,0)=0
                                 AND COALESCE(retired,0)=0 AND COALESCE(loan_from_club,0)=0""").fetchall()
        if not listed:
            return 0
        # Chaque club candidat est filtré par son projet : un club animé se
        # penche sur le marché, un club prudent attend une vraie opportunité.
        candidates = conn.execute("SELECT * FROM club WHERE id<>1 AND budget>0 ORDER BY RANDOM()").fetchall()
        buyers = []
        for candidate in candidates:
            behavior = transfer_behavior(conn, candidate)
            if random.random() > behavior["market_chance"]:
                continue
            buyers.append((behavior, candidate))
        buyers.sort(key=lambda item: item[0]["activity_score"], reverse=True)
        deals = 0
        for behavior, buyer in buyers[:10]:
            if deals >= 4:
                break
            profile = profile_for(conn, buyer)
            size = int(conn.execute("""SELECT COUNT(*) n FROM player WHERE club_id=?
                                       AND COALESCE(is_free_agent,0)=0 AND COALESCE(retired,0)=0""",
                                    (int(buyer["id"]),)).fetchone()["n"] or 0)
            if size >= int(behavior.get("size_limit", 13)):
                continue
            sample = random.sample(listed, min(10, len(listed)))
            best = None
            for player in sample:
                seller_id = int(player["club_id"])
                if seller_id == int(buyer["id"]):
                    continue
                seller_count = int(conn.execute("""SELECT COUNT(*) n FROM player WHERE club_id=?
                                                   AND COALESCE(is_free_agent,0)=0 AND COALESCE(retired,0)=0""",
                                                (seller_id,)).fetchone()["n"] or 0)
                if seller_count <= 11:
                    continue
                fee = int(player["market_value"] or 0)
                if fee <= 0:
                    continue
                if int(buyer["budget"] or 0) < fee + int(player["salary"] or 0) * 3:
                    continue
                fee_cap = max(40_000, int(buyer["budget"] or 0)
                              * float(profile.get("transfer_ratio", 0.16))
                              * float(behavior.get("fee_multiplier", 1.0)))
                if fee > fee_cap:
                    continue
                if not can_afford(conn, buyer, int(player["salary"] or 0), fee):
                    continue
                perceived, _k = scout_player(conn, buyer, player, current_iso_date)
                score = signing_score(profile, player, perceived, int(player["salary"] or 0))
                position = str(player["position"] or "")
                if position in behavior.get("high_needs", set()):
                    score += 1.6
                elif position in behavior.get("need_positions", set()):
                    score += 0.7
                if best is None or score > best[0]:
                    best = (score, player, seller_id, fee)
            if not best:
                continue
            _score, player, seller_id, fee = best
            # Le joueur a pu etre vendu entre-temps : on relit son etat reel.
            fresh = conn.execute("""SELECT * FROM player WHERE id=?""", (int(player["id"]),)).fetchone()
            if (not fresh or int(fresh["club_id"] or 0)!=seller_id
                    or not int(fresh["transfer_listed"] or 0)
                    or int(fresh["is_free_agent"] or 0) or int(fresh["retired"] or 0)
                    or int(fresh["loan_from_club"] or 0)):
                continue
            seller = conn.execute("SELECT * FROM club WHERE id=?", (seller_id,)).fetchone()
            if not seller:
                continue
            conn.execute("UPDATE club SET budget=budget+? WHERE id=?", (fee, seller_id))
            conn.execute("UPDATE club SET budget=budget-? WHERE id=?", (fee, int(buyer["id"])))
            number = next_shirt_number(conn, int(buyer["id"]))
            conn.execute("""UPDATE player SET club_id=?,transfer_listed=0,free_agent_since='',shirt_number=?,
                                                 contract_years=MAX(2,contract_years) WHERE id=?""",
                         (int(buyer["id"]), number, int(player["id"])))
            record_player_history(conn, int(player["id"]), int(buyer["id"]), "transfer",
                                  f"Transfert de {seller['name']} vers {buyer['name']} ({fee:,} €)".replace(",", " "))
            if fee >= 50000 or int(buyer["reputation"] or 0) >= 60:
                _market_news(conn,
                             f"{buyer['name']} achète {player['first_name']} {player['last_name']} à "
                             f"{seller['name']} pour {fee:,} €.".replace(",", " "),
                             current_iso_date, limit=2)
            deals += 1
        return deals
    except Exception as exc:
        try:
            host.log_error("ai_transfer_market", exc)
        except Exception:
            pass
        return 0
