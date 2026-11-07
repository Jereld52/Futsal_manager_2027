# -*- coding: utf-8 -*-
"""Identites de club : profils, philosophie de jeu et politique de recrutement.

Chaque club IA recoit un profil stable (determine par son identifiant) qui
oriente ses transferts, ses finances, sa formation et son style tactique.
Le club du manager (id=1) garde le profil "Manager" : ses choix restent libres.
"""
import random

PROFILES = {
    "Formateur": {
        "label": "Formateur",
        "motto": "Faire grandir les jeunes et valoriser le centre de formation.",
        "style": {"style": "possession", "formation": "4-0", "pressing": "Médian", "tempo": "Patient"},
        "income": 0.95, "upkeep": 0.13, "wage_ratio": 0.82, "transfer_ratio": 0.10,
        "max_age": 25, "youth_bonus": 1.6, "star_bonus": 0.4,
        "attack_bonus": 0.0, "defense_bonus": 0.1, "frugal": 0.3,
        "youth_mult": 1.30,
    },
    "Riche": {
        "label": "Riche",
        "motto": "Un mécène : des stars, des résultats tout de suite.",
        "style": {"style": "possession", "formation": "3-1", "pressing": "Haut", "tempo": "Normal"},
        "income": 1.22, "upkeep": 0.12, "wage_ratio": 0.95, "transfer_ratio": 0.35,
        "max_age": 34, "youth_bonus": -0.5, "star_bonus": 1.5,
        "attack_bonus": 0.3, "defense_bonus": 0.0, "frugal": -0.1,
        "youth_mult": 0.95,
    },
    "Spectacle": {
        "label": "Spectacle",
        "motto": "Offrir du jeu, des buts et du spectacle au public.",
        "style": {"style": "pressing", "formation": "3-1", "pressing": "Haut", "tempo": "Rapide"},
        "income": 1.10, "upkeep": 0.12, "wage_ratio": 0.88, "transfer_ratio": 0.20,
        "max_age": 30, "youth_bonus": 0.3, "star_bonus": 0.8,
        "attack_bonus": 1.0, "defense_bonus": -0.2, "frugal": 0.1,
        "youth_mult": 1.05,
    },
    "Économe": {
        "label": "Économe",
        "motto": "Chaque euro compte : effectif restreint, paris malins.",
        "style": {"style": "contre", "formation": "2-2", "pressing": "Bas", "tempo": "Rapide"},
        "income": 0.90, "upkeep": 0.07, "wage_ratio": 0.75, "transfer_ratio": 0.06,
        "max_age": 32, "youth_bonus": 0.1, "star_bonus": -0.4,
        "attack_bonus": -0.3, "defense_bonus": 0.4, "frugal": 0.8,
        "youth_mult": 0.92,
    },
    "Bâtisseur": {
        "label": "Bâtisseur",
        "motto": "Construire patiemment, équilibrer le sport et les finances.",
        "style": {"style": "equilibre", "formation": "3-1", "pressing": "Médian", "tempo": "Normal"},
        "income": 1.00, "upkeep": 0.11, "wage_ratio": 0.85, "transfer_ratio": 0.16,
        "max_age": 30, "youth_bonus": 0.4, "star_bonus": 0.2,
        "attack_bonus": 0.0, "defense_bonus": 0.1, "frugal": 0.2,
        "youth_mult": 1.10,
    },
    "Opportuniste": {
        "label": "Opportuniste",
        "motto": "Acheter bas, revendre haut, saisir les coups du marché.",
        "style": {"style": "contre", "formation": "2-2", "pressing": "Médian", "tempo": "Rapide"},
        "income": 0.95, "upkeep": 0.08, "wage_ratio": 0.80, "transfer_ratio": 0.20,
        "max_age": 29, "youth_bonus": 0.4, "star_bonus": 0.3,
        "attack_bonus": 0.2, "defense_bonus": 0.0, "frugal": 0.4,
        "youth_mult": 1.05,
    },
    "Guerrier": {
        "label": "Guerrier",
        "motto": "Bloc compact, intensité, mental : gagner le duel avant le match.",
        "style": {"style": "pressing", "formation": "3-1", "pressing": "Haut", "tempo": "Rapide"},
        "income": 0.90, "upkeep": 0.09, "wage_ratio": 0.78, "transfer_ratio": 0.08,
        "max_age": 31, "youth_bonus": 0.0, "star_bonus": -0.2,
        "attack_bonus": -0.2, "defense_bonus": 1.0, "frugal": 0.4,
        "youth_mult": 1.0,
    },
}
DEFAULT_PROFILE = "Bâtisseur"
PROFILE_WEIGHTS = {
    "Formateur": 18, "Riche": 10, "Spectacle": 15, "Économe": 17,
    "Bâtisseur": 15, "Opportuniste": 15, "Guerrier": 10,
}

# Identite tactique complete (lue par le moteur de match).
# discipline : 1 = tres discipline (peu de fautes), 0 = agressif.
IDENTITIES = {
    "Formateur":    {"style": "possession", "formation": "4-0", "pressing": "Médian",
                     "tempo": "Patient", "mentality": "Équilibrée", "block": "Médian",
                     "width": "Normale", "focus": "Ailes", "discipline": 0.85},
    "Riche":        {"style": "possession", "formation": "3-1", "pressing": "Haut",
                     "tempo": "Normal", "mentality": "Offensive", "block": "Haut",
                     "width": "Large", "focus": "Axe", "discipline": 0.60},
    "Spectacle":    {"style": "pressing", "formation": "3-1", "pressing": "Haut",
                     "tempo": "Rapide", "mentality": "Offensive", "block": "Haut",
                     "width": "Large", "focus": "Ailes", "discipline": 0.50},
    "Économe":      {"style": "contre", "formation": "2-2", "pressing": "Bas",
                     "tempo": "Rapide", "mentality": "Prudente", "block": "Bas",
                     "width": "Étroite", "focus": "Axe", "discipline": 0.85},
    "Bâtisseur":    {"style": "equilibre", "formation": "3-1", "pressing": "Médian",
                     "tempo": "Normal", "mentality": "Équilibrée", "block": "Médian",
                     "width": "Normale", "focus": "Axe", "discipline": 0.70},
    "Opportuniste": {"style": "contre", "formation": "2-2", "pressing": "Médian",
                     "tempo": "Rapide", "mentality": "Prudente", "block": "Médian",
                     "width": "Étroite", "focus": "Ailes", "discipline": 0.65},
    "Guerrier":     {"style": "pressing", "formation": "3-1", "pressing": "Haut",
                     "tempo": "Rapide", "mentality": "Offensive", "block": "Haut",
                     "width": "Normale", "focus": "Axe", "discipline": 0.35},
}


def profile_name_for(club_id):
    """Profil stable d'un club (meme identite a chaque sauvegarde)."""
    rng = random.Random(f"club-profile|{int(club_id)}")
    names = list(PROFILES.keys())
    weights = [PROFILE_WEIGHTS[name] for name in names]
    return rng.choices(names, weights=weights, k=1)[0]


def ensure_profiles(conn):
    """Assigne un profil aux clubs IA qui n'en ont pas encore."""
    try:
        conn.execute("UPDATE club SET profile='Manager' WHERE id=1 AND COALESCE(profile,'')=''")
        rows = conn.execute("SELECT id FROM club WHERE id<>1 AND COALESCE(profile,'')=''").fetchall()
        for row in rows:
            conn.execute("UPDATE club SET profile=? WHERE id=?", (profile_name_for(int(row["id"])), int(row["id"])))
        return len(rows)
    except Exception:
        return 0


def profile_for(conn, club):
    """Dictionnaire de profil pour une ligne club (ou un dict)."""
    try:
        name = club["profile"]
    except Exception:
        name = club.get("profile") if isinstance(club, dict) else ""
    return PROFILES.get(str(name or ""), PROFILES[DEFAULT_PROFILE])


def profile_name(conn, club):
    try:
        name = str(club["profile"] or "")
    except Exception:
        name = ""
    return name or DEFAULT_PROFILE


def style_for_club(conn, club_id):
    """Style tactique lisible par le moteur de match."""
    try:
        row = conn.execute("SELECT profile FROM club WHERE id=?", (int(club_id),)).fetchone()
        name = str(row["profile"] or "") if row else ""
    except Exception:
        name = ""
    if int(club_id) == 1:
        return dict(PROFILES[DEFAULT_PROFILE]["style"])
    return dict(PROFILES.get(name or profile_name_for(club_id), PROFILES[DEFAULT_PROFILE])["style"])


def identity_for_club(conn, club_id):
    """Identite tactique complete : style, formation, pressing, tempo, mentalite,
    hauteur de bloc, largeur, axe de jeu et discipline (0 = agressif)."""
    try:
        row = conn.execute("SELECT profile FROM club WHERE id=?", (int(club_id),)).fetchone()
        name = str(row["profile"] or "") if row else ""
    except Exception:
        name = ""
    if int(club_id) == 1:
        name = DEFAULT_PROFILE
    return dict(IDENTITIES.get(name or profile_name_for(club_id), IDENTITIES[DEFAULT_PROFILE]))


def youth_multiplier(conn, club_id):
    try:
        row = conn.execute("SELECT profile FROM club WHERE id=?", (int(club_id),)).fetchone()
        name = str(row["profile"] or "") if row else ""
    except Exception:
        name = ""
    return float(PROFILES.get(name or profile_name_for(club_id), PROFILES[DEFAULT_PROFILE])["youth_mult"])


def signing_score(profile, player, perceived_level, salary):
    """Note de recrutement selon la marque de fabrique du club.

    N'utilise QUE le niveau perçu (scouting), l'age, le poste et le salaire :
    le club ne voit jamais les vraies caracteristiques.
    """
    age = int(player["age"] or 25) if "age" in player.keys() else 25
    position = str(player["position"] or "")
    score = float(perceived_level)
    max_age = int(profile.get("max_age", 30))
    if age > max_age:
        score -= (age - max_age) * 0.8
    if age <= 23:
        score += float(profile.get("youth_bonus", 0.0))
    if perceived_level >= 15:
        score += float(profile.get("star_bonus", 0.0))
    if position in ("Ailier", "Pivot"):
        score += float(profile.get("attack_bonus", 0.0))
    if position in ("Défenseur", "Gardien"):
        score += float(profile.get("defense_bonus", 0.0))
    score -= (max(0, int(salary or 0)) / 1000.0) * float(profile.get("frugal", 0.0))
    return score
