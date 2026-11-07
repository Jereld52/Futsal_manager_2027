# -*- coding: utf-8 -*-
"""Projets des clubs IA : ambition, objectif, entraîneur, besoins et dynamique.

Chaque club IA possède une identité stable (profil de club_profiles.py) qui
oriente son projet sportif. Le projet est recalculé à chaque nouvelle saison :

- ambition et objectif de classement cohérents avec la division, la réputation
  et le profil du club ;
- entraîneur stable, remplacé quand les résultats trahissent le projet ;
- dynamique de recrutement « animée » ou « prudente » selon l'identité, les
  moyens et l'ambition — le monde reste vivant sans inflation ;
- besoins par poste, âge et niveau, utilisés par le marché IA.

Le club du manager (id=1) est ignoré : ses choix restent libres.
"""
import json
import random

from club_profiles import profile_for, profile_name

ACTIVITY_LABELS = ("Animé", "Équilibré", "Prudent")

# Base de dynamique par identité : le Riche tente, l'Économe attend.
BASE_ACTIVITY = {
    "Riche": 0.86,
    "Spectacle": 0.76,
    "Opportuniste": 0.70,
    "Bâtisseur": 0.52,
    "Guerrier": 0.46,
    "Formateur": 0.40,
    "Économe": 0.30,
}

BASE_PATIENCE = {
    "Riche": 38,
    "Spectacle": 48,
    "Opportuniste": 55,
    "Bâtisseur": 68,
    "Guerrier": 64,
    "Formateur": 74,
    "Économe": 70,
}

STYLE_LABELS = {
    "possession": "Possession",
    "pressing": "Pressing",
    "contre": "Contre",
    "equilibre": "Équilibré",
}

FIRST_NAMES = (
    "Lucas", "Marc", "Julien", "Sofiane", "Diego", "Andrei", "Tomas", "Nuno",
    "Rafael", "Yann", "Karim", "Erik", "Paulo", "Mateo", "Hugo", "Ivan",
    "Sergio", "Damien", "Nicolas", "Bruno", "Omar", "Viktor", "Adrien", "Leo",
)
LAST_NAMES = (
    "Moreau", "Silva", "Kovac", "Bianchi", "Novak", "Costa", "Weber", "Petrov",
    "Lopez", "Dumas", "Rossi", "Fischer", "Almeida", "Keller", "Santos",
    "Lefevre", "Marques", "Horvat", "Reyes", "Vidal", "Bauer", "Pereira",
)

IDEAL_SQUAD = {"Gardien": 2, "Défenseur": 4, "Ailier": 4, "Pivot": 3, "Universel": 1}
MIN_SQUAD = {"Gardien": 1, "Défenseur": 3, "Ailier": 3, "Pivot": 2}


def ensure_table(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS ai_club_plan(
        club_id INTEGER PRIMARY KEY,
        season INTEGER NOT NULL DEFAULT 1,
        ambition TEXT NOT NULL DEFAULT '',
        objective_rank INTEGER NOT NULL DEFAULT 1,
        patience INTEGER NOT NULL DEFAULT 60,
        activity TEXT NOT NULL DEFAULT 'Équilibré',
        activity_score REAL NOT NULL DEFAULT 0.5,
        manager_name TEXT NOT NULL DEFAULT '',
        manager_style TEXT NOT NULL DEFAULT '',
        needs TEXT NOT NULL DEFAULT '[]',
        updated_date TEXT NOT NULL DEFAULT ''
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS ai_manager_history(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        club_id INTEGER NOT NULL,
        season INTEGER NOT NULL,
        manager_name TEXT NOT NULL,
        manager_style TEXT NOT NULL DEFAULT '',
        reason TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL DEFAULT ''
    )""")


def _club_season(conn):
    try:
        row = conn.execute('SELECT season FROM club WHERE id=1').fetchone()
        return int(row["season"] or 1) if row else 1
    except Exception:
        return 1


def _current_date(conn, fallback=""):
    if fallback:
        return str(fallback)
    try:
        row = conn.execute('SELECT "current_date" d FROM career WHERE id=1').fetchone()
        return str(row["d"] or "") if row else ""
    except Exception:
        return ""


def _division_rank(conn, club):
    """Rang de réputation du club dans sa division (1 = le plus prestigieux)."""
    try:
        rows = conn.execute("""SELECT id,reputation FROM club WHERE division=?
                               ORDER BY reputation DESC,id""",
                            (int(club["division"] or 3),)).fetchall()
    except Exception:
        rows = []
    for index, row in enumerate(rows, 1):
        if int(row["id"]) == int(club["id"]):
            return index, len(rows)
    return max(1, (len(rows) + 1) // 2), max(1, len(rows))


def _target_level(division, reputation):
    return max(5.0, 22.0 - int(division or 3) * 2.0) + max(0, int(reputation or 20)) // 12.0


def manager_identity(club_id, season, profile):
    rng = random.Random("ai-manager|%s|%s|%s" % (int(club_id), int(season), str(profile)))
    name = "%s %s" % (rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES))
    style = STYLE_LABELS.get(str(profile.get("style", {}).get("style", "equilibre")), "Équilibré")
    return name, style


def _objective_for(rank, size, division):
    """(ambition, objectif de rang) selon la hiérarchie de réputation."""
    size = max(1, int(size))
    if rank <= 2:
        if int(division) > 2:
            return "Montée", 1
        return "Titre", 1
    if rank <= max(3, int(round(size * 0.30))):
        return "Haut de tableau", min(3, size)
    if rank <= max(5, int(round(size * 0.62))):
        return "Milieu de tableau", max(5, min(size, int(round(size * 0.55))))
    return "Maintien", max(1, size - 2)


def _activity_for(conn, club, profile, ambition, rank, size):
    score = float(BASE_ACTIVITY.get(profile_name(conn, club), 0.5))
    if ambition in ("Titre", "Montée", "Haut de tableau"):
        score += 0.12
    elif ambition == "Maintien":
        score -= 0.06
    try:
        from ai_finance import division_base, monthly_income, wage_bill
        income = max(1, int(monthly_income(conn, club)))
        wages = int(wage_bill(conn, int(club["id"])))
        ratio = float(profile.get("wage_ratio", 0.80))
        room = (income * ratio - wages) / float(income)
        score += max(-0.20, min(0.20, room * 0.55))
        budget = int(club["budget"] or 0)
        base = max(1, int(division_base(int(club["division"] or 3))))
        if budget < 0:
            score -= 0.25
        elif budget > base * 0.60:
            score += 0.04
    except Exception:
        pass
    return max(0.12, min(0.92, score))


def _activity_label(score):
    if score >= 0.72:
        return "Animé"
    if score >= 0.48:
        return "Équilibré"
    return "Prudent"


def _patience_for(profile_name_, ambition):
    value = int(BASE_PATIENCE.get(profile_name_, 62))
    if ambition == "Maintien":
        value += 9
    elif ambition == "Titre":
        value -= 6
    elif ambition == "Montée":
        value -= 2
    return max(24, min(92, value))


def needs_for(conn, club, profile=None):
    """Besoins lisibles : poste, priorité, raison."""
    profile = profile or profile_for(conn, club)
    rows = conn.execute("""SELECT position,age,contract_years FROM player
                           WHERE club_id=? AND COALESCE(is_free_agent,0)=0
                             AND COALESCE(retired,0)=0""",
                        (int(club["id"]),)).fetchall()
    counts = {}
    ages = []
    expiring = 0
    for row in rows:
        position = str(row["position"] or "Universel")
        counts[position] = counts.get(position, 0) + 1
        ages.append(int(row["age"] or 25))
        if int(row["contract_years"] or 0) <= 1:
            expiring += 1
    total = len(rows)
    avg_age = (sum(ages) / float(total)) if total else 24.0
    needs = []

    def add(position, priority, reason):
        needs.append({"position": position, "priority": priority, "reason": reason})

    for position, minimum in MIN_SQUAD.items():
        if counts.get(position, 0) < minimum:
            add(position, "Haute", "poste découvert")
    if total < 12:
        add("Universel", "Haute", "effectif court (%d joueurs)" % total)
    for position, ideal in IDEAL_SQUAD.items():
        if counts.get(position, 0) < ideal:
            add(position, "Moyenne", "effectif à compléter")
            continue
    if total and avg_age > float(profile.get("max_age", 30)) + 1.5:
        add("Universel", "Moyenne", "effectif vieillissant")
    if total and expiring >= max(4, total // 3):
        add("Universel", "Moyenne", "%d fins de contrat" % expiring)
    try:
        from app import player_level_from_row
        levels = [player_level_from_row(row) for row in rows]
        avg_level = sum(levels) / float(total) if total else 0.0
        target = _target_level(club["division"], club["reputation"])
        if total and avg_level < target - 1.2:
            add("Universel", "Moyenne", "niveau moyen %.1f/20" % avg_level)
    except Exception:
        pass
    if float(profile.get("youth_bonus", 0.0)) > 0.25:
        young = sum(1 for age in ages if age <= 23)
        if young < 3:
            add("Universel", "Basse", "projection jeunes")
    order = {"Haute": 0, "Moyenne": 1, "Basse": 2}
    needs.sort(key=lambda item: (order.get(item["priority"], 3), item["position"]))
    # Doublons de poste : on ne garde que le besoin le plus fort.
    seen = set()
    unique = []
    for item in needs:
        if item["position"] in seen:
            continue
        seen.add(item["position"])
        unique.append(item)
    return unique[:4]


def _json_needs(needs):
    try:
        return json.dumps(needs, ensure_ascii=False)
    except Exception:
        return "[]"


def _load_needs(raw):
    try:
        value = json.loads(raw or "[]")
        return value if isinstance(value, list) else []
    except Exception:
        return []


def _row_to_plan(row):
    if not row:
        return None
    plan = dict(row)
    plan["needs"] = _load_needs(plan.get("needs"))
    plan["needs_positions"] = [item.get("position") for item in plan["needs"]]
    plan["high_needs"] = [item.get("position") for item in plan["needs"]
                          if item.get("priority") == "Haute"]
    return plan


def plan_for(conn, club_id):
    try:
        row = conn.execute("SELECT * FROM ai_club_plan WHERE club_id=?", (int(club_id),)).fetchone()
    except Exception:
        return None
    return _row_to_plan(row)


def _build_plan(conn, club, season, current_iso_date):
    profile = profile_for(conn, club)
    ident = profile_name(conn, club)
    rank, size = _division_rank(conn, club)
    ambition, objective = _objective_for(rank, size, club["division"])
    # L'identité nuance l'objectif : un Riche/Spectacle vise un cran plus haut,
    # un Économe/Formateur sécurise sa saison.
    if ident in ("Riche", "Spectacle"):
        objective = max(1, objective - 1)
        if ambition == "Milieu de tableau":
            ambition = "Haut de tableau"
    elif ident in ("Économe", "Formateur", "Guerrier"):
        objective = min(size, objective + 1)
    activity_score = _activity_for(conn, club, profile, ambition, rank, size)
    activity = _activity_label(activity_score)
    patience = _patience_for(ident, ambition)
    manager, style = "", ""
    try:
        previous = conn.execute("SELECT manager_name,manager_style FROM ai_club_plan WHERE club_id=?",
                                (int(club["id"]),)).fetchone()
        if previous and str(previous["manager_name"] or "").strip():
            manager = str(previous["manager_name"]).strip()
            style = str(previous["manager_style"] or "").strip()
    except Exception:
        previous = None
    if not manager:
        manager, style = manager_identity(int(club["id"]), season, profile)
    needs = needs_for(conn, club, profile)
    return {
        "club_id": int(club["id"]),
        "season": int(season),
        "ambition": ambition,
        "objective_rank": int(objective),
        "patience": int(patience),
        "activity": activity,
        "activity_score": float(activity_score),
        "manager_name": manager,
        "manager_style": style,
        "needs": needs,
        "updated_date": _current_date(conn, current_iso_date),
    }


def _save_plan(conn, plan):
    conn.execute("""INSERT INTO ai_club_plan(club_id,season,ambition,objective_rank,patience,activity,
                                             activity_score,manager_name,manager_style,needs,updated_date)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(club_id) DO UPDATE SET
                        season=excluded.season,
                        ambition=excluded.ambition,
                        objective_rank=excluded.objective_rank,
                        patience=excluded.patience,
                        activity=excluded.activity,
                        activity_score=excluded.activity_score,
                        manager_name=excluded.manager_name,
                        manager_style=excluded.manager_style,
                        needs=excluded.needs,
                        updated_date=excluded.updated_date""",
                 (plan["club_id"], plan["season"], plan["ambition"], plan["objective_rank"],
                  plan["patience"], plan["activity"], plan["activity_score"],
                  plan["manager_name"], plan["manager_style"], _json_needs(plan["needs"]),
                  plan["updated_date"]))


def ensure_plans(conn, current_iso_date="", force=False, announce=True):
    """Crée les projets manquants (ou tous si force=True) pour la saison en cours."""
    try:
        ensure_table(conn)
        season = _club_season(conn)
        season_key = str(season)
        guard = conn.execute("SELECT value FROM meta WHERE key='ai_plans_season'").fetchone()
        same_season = bool(guard and str(guard["value"] or "") == season_key)
        created = 0
        for club in conn.execute("SELECT * FROM club WHERE id<>1 ORDER BY id").fetchall():
            if not force:
                row = conn.execute("SELECT season FROM ai_club_plan WHERE club_id=?",
                                   (int(club["id"]),)).fetchone()
                if row and int(row["season"] or 0) == season:
                    continue
            plan = _build_plan(conn, club, season, current_iso_date)
            _save_plan(conn, plan)
            created += 1
        conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('ai_plans_season',?)",
                     (season_key,))
        if created and announce and not same_season:
            try:
                from app import add_news
                _announce_ambitions(conn, season)
            except Exception:
                pass
        return created
    except Exception:
        return 0


def _announce_ambitions(conn, season):
    """Un seul entrefilet par saison : les favoris et les outsiders."""
    try:
        from app import add_news
        lines = []
        for division in range(1, 7):
            rows = conn.execute("""SELECT p.ambition,p.objective_rank,c.name
                                   FROM ai_club_plan p JOIN club c ON c.id=p.club_id
                                   WHERE c.division=? AND p.season=?
                                   ORDER BY p.objective_rank,c.reputation DESC LIMIT 3""",
                                (division, season)).fetchall()
            if not rows:
                continue
            favourites = " ; ".join("%s (%s)" % (r["name"], r["ambition"]) for r in rows)
            lines.append("Ligue %d : %s" % (division, favourites))
        if lines:
            add_news(conn, "Ambitions de la saison",
                     "Les projets des clubs IA sont fixés. " + " • ".join(lines[:6]))
    except Exception:
        pass


def refresh_needs(conn, current_iso_date=""):
    """Met à jour les besoins de tous les clubs (hebdomadaire)."""
    updated = 0
    try:
        ensure_table(conn)
        season = _club_season(conn)
        for club in conn.execute("SELECT * FROM club WHERE id<>1").fetchall():
            plan = plan_for(conn, int(club["id"]))
            if not plan or int(plan.get("season") or 0) != season:
                continue
            needs = needs_for(conn, club)
            conn.execute("UPDATE ai_club_plan SET needs=?,updated_date=? WHERE club_id=?",
                         (_json_needs(needs), _current_date(conn, current_iso_date),
                          int(club["id"])))
            updated += 1
        return updated
    except Exception:
        return updated


def _current_rank(conn, club_id, division):
    try:
        rows = conn.execute("""SELECT s.club_id FROM league_standing s JOIN club c ON c.id=s.club_id
                               WHERE c.division=? ORDER BY s.pts DESC,(s.gf-s.ga) DESC,s.gf DESC,c.name""",
                            (int(division),)).fetchall()
    except Exception:
        return None
    for index, row in enumerate(rows, 1):
        if int(row["club_id"]) == int(club_id):
            return index
    return None


def process_weekly(host, conn, current_iso_date):
    """Chaque lundi : besoins à jour ; chaque début de mois : pression du board."""
    try:
        from app import add_news, parse_iso
        today = parse_iso(current_iso_date)
    except Exception:
        return 0
    changed = 0
    if today.weekday() != 0:
        return 0
    try:
        ensure_plans(conn, current_iso_date)
        changed += refresh_needs(conn, current_iso_date)
        # Pression : uniquement quand le championnat a réellement commencé.
        if today.day <= 7:
            season = _club_season(conn)
            for club in conn.execute("SELECT * FROM club WHERE id<>1").fetchall():
                plan = plan_for(conn, int(club["id"]))
                if not plan or int(plan.get("season") or 0) != season:
                    continue
                played = conn.execute("SELECT played FROM league_standing WHERE club_id=?",
                                      (int(club["id"]),)).fetchone()
                if not played or int(played["played"] or 0) <= 0:
                    continue
                rank = _current_rank(conn, int(club["id"]), club["division"])
                if not rank:
                    continue
                target = int(plan.get("objective_rank") or 1)
                patience = int(plan.get("patience") or 60)
                if rank <= target:
                    patience = min(95, patience + 2)
                elif rank > target + 3:
                    patience = max(5, patience - 4)
                conn.execute("UPDATE ai_club_plan SET patience=? WHERE club_id=?",
                             (patience, int(club["id"])))
                if patience <= 18:
                    key = "ai_pressure_%d_%d" % (int(club["id"]), season)
                    seen = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
                    if not seen:
                        conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)", (key, "1"))
                        try:
                            add_news(conn, "Pression",
                                     "%s : le board perd patience, l'entraîneur %s est sous pression."
                                     % (club["name"], plan.get("manager_name") or "en poste"))
                        except Exception:
                            pass
        return changed
    except Exception as exc:
        try:
            host.log_error("ai_club_plans", exc)
        except Exception:
            pass
        return changed


def finalize_season(host, conn, tables, moved, season):
    """Bilan des projets : patience, changements d'entraîneur, historique."""
    sacked = []
    try:
        ensure_table(conn)
        from app import add_news, career_timestamp
        ranks = {}
        for division, rows in (tables or {}).items():
            for index, row in enumerate(rows, 1):
                ranks[int(row["id"])] = index
        for club in conn.execute("SELECT * FROM club WHERE id<>1").fetchall():
            cid = int(club["id"])
            plan = plan_for(conn, cid)
            if not plan or int(plan.get("season") or 0) != int(season):
                continue
            final_rank = ranks.get(cid)
            if not final_rank:
                continue
            target = int(plan.get("objective_rank") or 1)
            patience = int(plan.get("patience") or 60)
            if final_rank <= target:
                patience = min(95, patience + 8)
            elif final_rank <= target + 2:
                patience = max(5, patience - 5)
            else:
                patience = max(5, patience - 15)
            moved_info = (moved or {}).get(cid)
            relegated = bool(moved_info and moved_info[1] == "relegation")
            sack_chance = (100 - patience) / 100.0 * 0.55
            if final_rank > target + 3:
                sack_chance += 0.20
            if relegated:
                sack_chance += 0.25
            if patience <= 15:
                sack_chance = max(sack_chance, 0.65)
            underperforming = (final_rank > target + 3) or relegated or patience <= 15
            if underperforming and random.random() < min(0.85, sack_chance):
                old_name = plan.get("manager_name") or "l'entraîneur"
                conn.execute("""INSERT INTO ai_manager_history(club_id,season,manager_name,manager_style,reason,created_at)
                                VALUES(?,?,?,?,?,?)""",
                             (cid, int(season), old_name, plan.get("manager_style") or "",
                              "objectif manqué (%de pour une cible de %de)" % (final_rank, target),
                              career_timestamp(conn)))
                profile = profile_for(conn, club)
                new_name, new_style = manager_identity(cid, int(season) + 1, profile)
                conn.execute("""UPDATE ai_club_plan SET manager_name=?,manager_style=?,patience=?
                                WHERE club_id=?""",
                             (new_name, new_style, min(95, max(45, patience + 25)), cid))
                sacked.append((club["name"], old_name, final_rank, target))
            else:
                conn.execute("UPDATE ai_club_plan SET patience=? WHERE club_id=?", (patience, cid))
        if sacked:
            lines = ["%s se sépare de %s (objectif manqué)." % (name, manager)
                     for name, manager, _rank, _target in sacked[:6]]
            add_news(conn, "Entraîneurs", " ".join(lines))
        return len(sacked)
    except Exception as exc:
        try:
            host.log_error("ai_club_plans_finalize", exc)
        except Exception:
            pass
        return len(sacked)


def need_priority_for(conn, club_id, position):
    """Priorité du besoin d'un club pour un poste (Haute/Moyenne/Basse/'')."""
    try:
        plan = plan_for(conn, int(club_id))
    except Exception:
        plan = None
    if not plan:
        return ""
    position = str(position or "")
    for item in plan.get("needs") or []:
        if str(item.get("position") or "") == position:
            return str(item.get("priority") or "")
    return ""


def interest_weight(conn, club, player):
    """Poids d'intérêt d'un club pour un joueur du manager.

    Le projet du club compte : un besoin haute priorité pèse beaucoup plus
    qu'une simple envie, et un club animé se penche plus vite sur le dossier.
    """
    try:
        plan = plan_for(conn, int(club["id"]))
    except Exception:
        plan = None
    weight = 1.0 + float((plan or {}).get("activity_score") or 0.4)
    priority = need_priority_for(conn, int(club["id"]), player["position"])
    if priority == "Haute":
        weight += 2.2
    elif priority == "Moyenne":
        weight += 0.9
    elif priority == "Basse":
        weight += 0.3
    ambition = str((plan or {}).get("ambition") or "")
    if ambition in ("Titre", "Montée"):
        weight += 0.35
    return max(0.25, weight)


def buyer_story(conn, club):
    """Phrase courte expliquant pourquoi le club veut recruter."""
    plan = plan_for(conn, int(club["id"])) or {}
    ambition = str(plan.get("ambition") or "Projet sportif")
    target = int(plan.get("objective_rank") or 0)
    manager = str(plan.get("manager_name") or "")
    bits = [ambition]
    if target:
        bits.append("objectif top %d" % target)
    if manager:
        bits.append("entraîneur %s" % manager)
    return " • ".join(bits)


def board_objective_for(conn, club):
    """Objectif du board du club du joueur, avec le même barème que les IA."""
    rank, size = _division_rank(conn, club)
    ambition, target = _objective_for(rank, size, club["division"])
    return ambition, int(target)


def transfer_behavior(conn, club, plan=None):
    """Réglages de marché dérivés du projet : animation, prudence, besoins."""
    plan = plan or plan_for(conn, int(club["id"])) or {}
    score = float(plan.get("activity_score") or 0.5)
    activity = str(plan.get("activity") or "Équilibré")
    high = set(plan.get("high_needs") or [])
    wanted = set(plan.get("needs_positions") or [])
    if activity == "Animé":
        return {"activity": activity, "activity_score": score, "max_deals": 2,
                "buyer_slots": 10, "market_chance": 0.85, "fee_multiplier": 1.15,
                "size_limit": 14, "recruitment_chance": 0.46, "high_needs": high,
                "need_positions": wanted}
    if activity == "Prudent":
        return {"activity": activity, "activity_score": score, "max_deals": 1,
                "buyer_slots": 6, "market_chance": 0.32, "fee_multiplier": 0.78,
                "size_limit": 12, "recruitment_chance": 0.16, "high_needs": high,
                "need_positions": wanted}
    return {"activity": activity, "activity_score": score, "max_deals": 1,
            "buyer_slots": 8, "market_chance": 0.58, "fee_multiplier": 1.0,
            "size_limit": 13, "recruitment_chance": 0.28, "high_needs": high,
            "need_positions": wanted}


def renewal_chance(conn, club_id):
    """Les clubs bâtisseurs gardent leurs joueurs ; les riches font tourner."""
    try:
        plan = plan_for(conn, int(club_id))
        activity = str((plan or {}).get("activity") or "Équilibré")
    except Exception:
        activity = "Équilibré"
    # La dynamique suffit : un club animé renouvelle moins, un prudent sécurise.
    return {"Animé": 0.58, "Équilibré": 0.72, "Prudent": 0.82}.get(activity, 0.72)


def objective_state(conn, club_id):
    """État lisible du projet pour la fiche club."""
    try:
        plan = plan_for(conn, int(club_id))
        if not plan:
            return None
        row = conn.execute("""SELECT c.division,s.played FROM club c
                              LEFT JOIN league_standing s ON s.club_id=c.id
                              WHERE c.id=?""", (int(club_id),)).fetchone()
        rank = None
        if row and int(row["played"] or 0) > 0:
            rank = _current_rank(conn, int(club_id), int(row["division"] or 3))
        target = int(plan.get("objective_rank") or 1)
        state = "en attente" if not rank else ("en avance" if rank <= target else (
            "dans les temps" if rank <= target + 2 else "en difficulté"))
        return {"rank": rank, "target": target, "state": state}
    except Exception:
        return None
