# -*- coding: utf-8 -*-
"""Helpers purs partagés par tout le jeu : dates, notes /20, montants.

Aucun accès à la base ni à l'UI : importables partout, testables seuls.
"""
from datetime import date
import random


def parse_iso(d):

    try:

        return date.fromisoformat(d)

    except Exception:

        return date.today()

def fmt_date_fr(d_iso):

    d = parse_iso(d_iso)

    return d.strftime("%d/%m/%Y")

def fmt_datetime_fr(value):
    """Date ISO (avec ou sans heure) -> JJ/MM/AAAA HH:MM."""
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        day = fmt_date_fr(text[:10])
    except Exception:
        return text
    clock = ""
    if len(text) >= 16 and text[10] in "T ":
        clock = text[11:16]
    return f"{day} {clock}".strip()

def fmt_match_time(minute,second=0):

    return f"{int(minute):02d}:{int(second):02d}"

def iso_today():

    return date.today().isoformat()

def rating20(value):

    """Convert legacy 0-100 attributes/condition into a consistent 1-20 rating."""

    return max(1,min(20,int(round(float(value)/5))))

def stars5(value20):

    count=max(1,min(5,(int(value20)+3)//4))

    return "★"*count + "☆"*(5-count)

def star_value(value20):
    """Note /20 -> étoiles par demi-pas (0,5 à 5). 20 = 5 ★, 1 = 0,5 ★."""
    try:
        value=max(1.0,min(20.0,float(value20)))
    except (TypeError,ValueError):
        value=1.0
    return max(0.5,min(5.0,round(value/4.0*2.0)/2.0))

def stars_half(value20):
    """Version étoilée d'une note /20, avec demi-étoile : ★★★½☆."""
    stars=star_value(value20)
    full=int(stars)
    half=1 if (stars-full)>=0.5 else 0
    return "★"*full + ("½" if half else "") + "☆"*(5-full-half)

def stars_compact(value_stars):
    """Étoiles compactes pour une valeur déjà exprimée en étoiles."""
    try: stars=max(0.5,min(5.0,float(value_stars)))
    except (TypeError,ValueError): stars=0.5
    full=int(stars)
    half=1 if (stars-full)>=0.5 else 0
    return "★"*full + ("½" if half else "") + "☆"*(5-full-half)

def star_range_text(low_stars, high_stars):
    """Fourchette lisible ; identique -> une seule série d'étoiles."""
    if low_stars is None or high_stars is None:
        return "—"
    low=stars_compact(low_stars); high=stars_compact(high_stars)
    return low if low==high else f"{low}–{high}"

def round_half(value):
    """Arrondi au demi-point le plus proche."""
    try: value=float(value)
    except (TypeError,ValueError): return 0.0
    return round(value*2.0)/2.0


# --- Attributs cachés -------------------------------------------------------
# Ces traits ne sont jamais affichés en chiffres. Ils sont dérivés de façon
# stable à partir de l'identité du joueur (id/nom/poste) : deux sauvegardes
# du même joueur donnent les mêmes traits, sans colonne à migrer.
HIDDEN_TRAIT_KEYS = (
    "composure", "consistency", "big_matches", "work_rate", "aggression",
    "leadership", "professionalism", "injury_proneness", "versatility",
)

HIDDEN_TRAIT_LABELS = {
    "composure": "Sang-froid",
    "consistency": "Régularité",
    "big_matches": "Matchs à enjeu",
    "work_rate": "Activité",
    "aggression": "Agressivité",
    "leadership": "Leadership",
    "professionalism": "Professionnalisme",
    "injury_proneness": "Fragilité",
    "versatility": "Polyvalence",
}

_TRAIT_TIERS = {
    "composure": ("fragile", "hésitant", "correct", "solide", "glacial"),
    "consistency": ("très irrégulier", "irrégulier", "correct", "régulier", "métronome"),
    "big_matches": ("s'efface", "discret", "normal", "aime ça", "homme des grands soirs"),
    "work_rate": ("économe", "modéré", "normal", "généreux", "infatigable"),
    "aggression": ("très propre", "prudent", "normal", "engagé", "bouillant"),
    "leadership": ("effacé", "discret", "normal", "écouté", "patron"),
    "professionalism": ("fantasque", "perfectible", "normal", "sérieux", "exemplaire"),
    "injury_proneness": ("solide", "rarement blessé", "normal", "sujet aux pépins", "fragile"),
    "versatility": ("spécialiste", "assez fixe", "normal", "adaptable", "couteau suisse"),
}

_POSITION_TRAIT_MODS = {
    "Gardien": {"composure": 9, "consistency": 3, "leadership": 6, "aggression": -10,
                "work_rate": -2, "big_matches": 3, "injury_proneness": -2},
    "Défenseur": {"aggression": 9, "work_rate": 5, "composure": 2, "leadership": 2,
                  "versatility": -2, "consistency": 2},
    "Ailier": {"work_rate": 9, "versatility": 7, "aggression": -4, "consistency": -2,
               "composure": -1, "injury_proneness": 2},
    "Pivot": {"composure": 5, "big_matches": 5, "aggression": 3, "work_rate": -2,
              "consistency": 2, "versatility": -4},
    "Universel": {"versatility": 13, "leadership": 3, "work_rate": 3, "composure": 1},
}


def hidden_attributes_for(player):
    """Traits mentaux stables d'un joueur (0-100), jamais montrés en chiffres.

    Le tirage est semé par l'identité du joueur, donc identique après un
    rechargement de sauvegarde. Les valeurs restent dans 15-95 pour éviter
    les personnalités caricaturales.
    """
    try:
        get=lambda key,default=None: player.get(key,default) if hasattr(player,"get") else player[key]
    except Exception:
        get=lambda key,default=None: default
    pid=get("id","")
    name=f"{get('first_name','')}|{get('last_name','')}|{get('position','')}"
    rng=random.Random(f"fm27-hidden|{pid}|{name}")
    position=str(get("position","") or "")
    mods=_POSITION_TRAIT_MODS.get(position,{})
    age=int(get("age",24) or 24)
    traits={}
    for key in HIDDEN_TRAIT_KEYS:
        base=52+mods.get(key,0)
        if key=="professionalism":
            base+=(age-24)*0.9
        elif key=="composure":
            base+=(age-24)*0.55
        elif key=="leadership":
            base+=(age-24)*0.45
        elif key=="injury_proneness":
            base+=(age-24)*0.55
        elif key=="consistency":
            base+=(age-24)*0.30
        value=int(round(rng.gauss(base,11)))
        traits[key]=max(15,min(95,value))
    return traits


def hidden_trait_tier(key,value):
    """Libellé qualitatif d'un trait caché (jamais de chiffre)."""
    tiers=_TRAIT_TIERS.get(key,("faible","moyen","correct","bon","excellent"))
    try: value=float(value)
    except (TypeError,ValueError): value=50.0
    index=0 if value<30 else 1 if value<45 else 2 if value<60 else 3 if value<75 else 4
    return tiers[index]


def hidden_trait_index(key,value):
    tiers=_TRAIT_TIERS.get(key,("faible","moyen","correct","bon","excellent"))
    try: value=float(value)
    except (TypeError,ValueError): value=50.0
    return min(len(tiers)-1,0 if value<30 else 1 if value<45 else 2 if value<60 else 3 if value<75 else 4)


def hidden_trait_text(key,index):
    tiers=_TRAIT_TIERS.get(key,("faible","moyen","correct","bon","excellent"))
    return tiers[max(0,min(len(tiers)-1,int(index)))]


def hidden_attributes_profile(player):
    """Version agrégée pour le moteur : traits + libellés, sans accès DB."""
    traits=hidden_attributes_for(player)
    traits["tiers"]={key:hidden_trait_tier(key,value) for key,value in traits.items()}
    return traits

def round_money(value):

    """Arrondit une somme a un palier lisible en fonction de son ordre de grandeur.



    Exemples : 47 138 -> 47 000 • 87 250 -> 85 000 • 523 400 -> 520 000 • 3 116 890 -> 3 100 000.

    """

    try: v=int(float(value))

    except (TypeError,ValueError): return 0

    sign=1 if v>=0 else -1; v=abs(v)

    if v<2000: step=100

    elif v<20000: step=500

    elif v<100000: step=2500

    elif v<500000: step=10000

    elif v<2000000: step=50000

    elif v<10000000: step=250000

    else: step=1000000

    return sign*((v+step//2)//step*step)

def format_euros(value, suffix=""):

    """Format monétaire unique pour éviter les écarts entre les vues (montant entier en euros)."""

    try:

        amount=int(float(value or 0))

    except (TypeError, ValueError):

        amount=0

    return f"{amount:,}".replace(",", " ") + " €" + suffix
