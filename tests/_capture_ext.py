# -*- coding: utf-8 -*-
"""Captures offscreen : la vue exterieure EVOLUE PAR ETAPES DE CONSTRUCTION."""
import os, sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
from PySide6.QtWidgets import QApplication
app = QApplication([])
from app import FacilityCampusView

OUT = r"C:\FM2027V2\tests\captures"
os.makedirs(OUT, exist_ok=True)

club = {"name":"Arbot Futsal","arena_name":"Halle Jacques Viot","color1":"#9e2b33",
        "color2":"#123c66","reputation":34,"division":6}

def fac(arena=1,med=1,youth=1,mkt=1,light=1,park=1,bar=0,vip=0,shop=0):
    return {"arena_level":arena,"medical_level":med,"youth_level":youth,"marketing_level":mkt,
            "lighting_level":light,"parking_level":park,"has_bar":bar,"has_vip":vip,"has_shop":shop,"ticket_price":12}

cases = [
    # Etape 0 : DEPART — halls petit, PLOTS VIDES (a batir), pas de drapeaux,
    # parking minimal : exactement la composition de modelext.png
    ("ext_etape0_depart", fac(), None, None, 320),
    # Etape 1 : PÔLE MÉDICAL bâti (niveau 3) + parking agrandi
    ("ext_etape1_medical", fac(med=3,park=3), None, 620, 950),
    # Etape 2 : FORMATION bâtie (youth 4) -> terrain tracé + bâtiment ;
    # marketing 3 -> drapeaux ; bar + boutique ; eclairage 2
    ("ext_etape2_formation", fac(arena=4,med=4,youth=4,mkt=3,light=2,park=4,bar=1,shop=1), None, 1650, 1900),
    # Etape 3 : COMPLET — arène 8, tout max, VIP, chantier en cours sur l'arène,
    # affluence forte
    ("ext_etape3_complet", fac(arena=8,med=8,youth=7,mkt=5,light=4,park=6,bar=1,vip=1,shop=1),
     {"facility_key":"arena_level","label":"Extension de l'arène","remaining_days":5}, 4200, 7800),
]
v = FacilityCampusView(); v.resize(1200, 700)
for name, facade, project, att, cap in cases:
    v.set_arena_state(facade, club, project, capacity=cap, attendance=att)
    v.grab().save(os.path.join(OUT, name + ".png"))
    print("saved", name)
print("CAPTURES OK")
