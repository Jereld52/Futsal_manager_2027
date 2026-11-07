# -*- coding: utf-8 -*-
"""Plafond de masse salariale du club du manager (joueurs + staff).

Le plafond est mensuel et derive de trois facteurs concrets :
- les revenus mensuels estimés du club (billetterie, TV, sponsors, installations),
- le budget disponible (matelas de trésorerie),
- la réputation et la division (ambition du club).

Il sert de garde-fou aux signatures, aux prolongations et aux evolutions du
staff. Pour une prolongation, on remplace l'ancien salaire : on ne l'ajoute
jamais au nouveau.
"""


def _club(conn):
    return conn.execute("SELECT budget,division,reputation FROM club WHERE id=1").fetchone()


def _monthly_income(host, conn, club, division):
    """Revenus mensuels estimés ; repli sur la TV si le calcul complet échoue."""
    tv = 4000 + 6500 * max(1, 7 - division)
    income = tv
    if host is not None and hasattr(host, "estimate_monthly_finance"):
        try:
            facility = conn.execute("SELECT * FROM facility WHERE id=1").fetchone()
            if facility is not None:
                estimate = host.estimate_monthly_finance(conn, club, facility)
                income = max(income, int(estimate.get("income", 0) or 0))
        except Exception:
            pass
    return int(income)


def wage_cap_details(host, conn):
    """Détail du plafond : cap final + facteurs utilisés (pour l'UI/tooltip)."""
    from app import LEAGUE_DEFINITIONS
    club = _club(conn)
    if not club:
        return {"cap": 0, "income": 0, "budget": 0, "reputation": 0,
                "division": 0, "base": 0, "revenue_part": 0,
                "budget_part": 0, "ambition_part": 0, "reputation_factor": 1.0}
    division = max(1, min(6, int(club["division"] or 3)))
    base = int(LEAGUE_DEFINITIONS[division - 1][3])
    reputation = max(0, min(100, int(club["reputation"] or 0)))
    budget = int(club["budget"] or 0)
    income = _monthly_income(host, conn, club, division)

    # 90 % des revenus récurrents + 2,5 % du budget par mois + ambition du club.
    revenue_part = income * 0.90
    budget_part = max(0, budget) * 0.025
    ambition_part = base * 0.020
    reputation_factor = 0.95 + 0.25 * (reputation / 100.0)
    cap = (revenue_part + budget_part + ambition_part) * reputation_factor

    # Plancher historique : aucune division ne doit perdre son minimum.
    floor = (base / 55.0 + 18_000.0) * (0.90 + 0.20 * (reputation / 100.0))
    cap = max(cap, floor)
    if budget < 0:
        cap *= 0.88
    cap = int(round(cap / 50.0)) * 50
    return {"cap": cap, "income": income, "budget": budget,
            "reputation": reputation, "division": division, "base": base,
            "revenue_part": int(revenue_part), "budget_part": int(budget_part),
            "ambition_part": int(ambition_part),
            "reputation_factor": round(reputation_factor, 3)}


def wage_cap(conn, host=None):
    """Plafond mensuel joueurs + staff, arrondi a 50 €."""
    return wage_cap_details(host, conn)["cap"]


def player_bill(conn):
    row = conn.execute("""SELECT COALESCE(SUM(salary),0) s FROM player
                          WHERE club_id=1 AND COALESCE(is_free_agent,0)=0
                            AND COALESCE(retired,0)=0""").fetchone()
    return int(row["s"] or 0)


def _staff_salary(host, level, base):
    return int(round(float(base) * (1 + 0.15 * (max(1, min(5, int(level))) - 1)) / 50.0)) * 50


def staff_bill(host, conn, hire_key=None, level_key=None, level=None):
    """Masse salariale staff reelle, remise du comptable incluse.

    `hire_key` simule l'embauche d'un membre ; `level_key`/`level` simule une
    evolution de niveau sans modifier la base.
    """
    total = 0
    comptable_level = None
    for key, base in host.STAFF_BASE_SALARY.items():
        row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        hired = bool(row and str(row["value"]) == "1")
        if key == hire_key:
            hired = True
        if not hired:
            continue
        lv = int(level) if (level_key == key and level is not None) else host.staff_level(conn, key)
        lv = max(1, min(5, lv))
        total += _staff_salary(host, lv, base)
        if key == "comptable_hired":
            comptable_level = lv
    if comptable_level is None and hire_key == "comptable_hired":
        comptable_level = 1
    discount = 1.0
    if comptable_level:
        discount = 1.0 - min(0.12, 0.04 + 0.02 * (comptable_level - 1))
    return int(round(total * discount / 50.0)) * 50


def status(host, conn):
    details = wage_cap_details(host, conn)
    cap = details["cap"]
    players = player_bill(conn)
    staff = staff_bill(host, conn)
    total = players + staff
    return {"cap": cap, "players": players, "staff": staff, "total": total,
            "room": cap - total, "over": max(0, total - cap),
            "cap_details": details}


def can_add_player(host, conn, new_salary, old_salary=0):
    """Nouveau salaire a la place de l'ancien (0 pour une recrue)."""
    st = status(host, conn)
    old_salary = max(0, int(old_salary or 0))
    new_salary = max(0, int(new_salary or 0))
    projected = st["total"] - old_salary + new_salary
    # Une prolongation a la baisse reste possible meme si le club est au-dessus
    # du plafond : c'est le seul moyen de revenir dans les clous sans vendre.
    improving = bool(old_salary and new_salary < old_salary)
    return (projected <= st["cap"]) or improving, st, projected


def can_set_staff_level(host, conn, key, level, hire=False):
    st = status(host, conn)
    projected_staff = staff_bill(host, conn, hire_key=key if hire else None,
                                 level_key=key, level=level)
    projected = st["players"] + projected_staff
    return projected <= st["cap"], st, projected


def summary_text(host, conn):
    st = status(host, conn)
    if st["cap"] <= 0:
        return "Plafond de masse salariale indisponible."
    state = "MARGE" if st["room"] >= 0 else "DÉPASSEMENT"
    return (f"Masse salariale {st['total']:,} € / plafond {st['cap']:,} € par mois "
            f"({state} {abs(st['room']):,} €) • joueurs {st['players']:,} € • staff {st['staff']:,} €"
            ).replace(",", " ")
