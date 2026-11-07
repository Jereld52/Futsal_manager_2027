# -*- coding: utf-8 -*-
"""Helpers purs partagés par tout le jeu : dates, notes /20, montants.

Aucun accès à la base ni à l'UI : importables partout, testables seuls.
"""
from datetime import date


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
