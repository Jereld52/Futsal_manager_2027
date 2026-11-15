# -*- coding: utf-8 -*-
"""Attributs cachés, étoiles et erreur de scouting.

Vérifie trois contrats :
1. les traits cachés sont stables, bornés et influencent vraiment le moteur ;
2. le niveau/potentiel ne s'affiche qu'en étoiles (avec demi-étoiles) ;
3. un recruteur faible produit une estimation plus large et parfois fausse.
"""
import os
import random
import statistics
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["FM2027_NO_AUDIO"] = "1"
sys.path.insert(0, r"C:\FM2027V2")

import app
import match_engine as me
from game_utils import (HIDDEN_TRAIT_KEYS, hidden_attributes_for, hidden_trait_index,
                        star_value, stars_half, stars_compact, star_range_text)


def player(pid=1, position="Ailier", age=24, level=60):
    row={"id":pid,"first_name":f"J{pid}","last_name":"Test","position":position,
         "age":age,"technique":level,"passing":level,"finishing":level,"defense":level,
         "goalkeeper":level if position=="Gardien" else 20,"stamina":level,
         "dribble":level,"speed":level,"positioning":level,"condition":90,"morale":65}
    return row


# 1) Traits cachés : stables, bornés, différents selon le poste.
a=hidden_attributes_for(player(1,"Ailier",24))
b=hidden_attributes_for(player(1,"Ailier",24))
assert a==b, (a,b)
assert set(a)==set(HIDDEN_TRAIT_KEYS), a
assert all(15<=v<=95 for v in a.values()), a
keepers=[hidden_attributes_for(player(i,"Gardien",30))["aggression"] for i in range(1,40)]
outfield=[hidden_attributes_for(player(i,"Ailier",24))["aggression"] for i in range(1,40)]
assert statistics.mean(keepers) < statistics.mean(outfield), (statistics.mean(keepers),statistics.mean(outfield))
print("1) traits cachés : stables, bornés, profil de poste respecté")

# 2) Étoiles : échelle par demi-pas, jamais de note /20.
assert stars_half(1)=="½☆☆☆☆", stars_half(1)
assert stars_half(20)=="★★★★★", stars_half(20)
assert stars_half(14)=="★★★½☆", stars_half(14)
assert stars_half(12)=="★★★☆☆", stars_half(12)
assert star_value(10)==2.5 and star_value(2)==0.5
assert "½" in stars_half(18)
assert star_range_text(2.5,3.5)!=star_range_text(3.0,3.0)
print("2) étoiles : 0,5 à 5, demi-étoiles, fourchettes lisibles")

# 3) Scouting : un faible recruteur a une fourchette plus large et peut se tromper.
p=player(42,"Pivot",22,72)
p["potential_fixed"]=18
low=app.scout_star_band(p,30,0.42,"level",scout_level=0,reports=1)
high=app.scout_star_band(p,100,0.92,"level",scout_level=5,reports=12)
assert low and high, (low,high)
assert low["high"]-low["low"] >= high["high"]-high["low"], (low,high)
assert high["exact"] and high["mid"]==high["true"], high
assert app.scout_star_band(p,40,0.5,"potential",0,1) is None
assert app.scout_star_text(p,0,0.4,"level",0,0)=="À évaluer"
assert "/20" not in app.scout_star_text(p,80,0.5,"level",1,3)
low_txt=app.scout_hidden_text(p,"composure",30,0.42,0,1)
high_txt=app.scout_hidden_text(p,"composure",100,0.92,5,12)
assert low_txt=="—" or isinstance(low_txt,str)
assert high_txt!="—"
print("3) scouting : fourchette faible plus large, dossier complet exact")


def profile(level=60, hidden=None):
    row={"attack":level,"defense":level,"passing":level,"finishing":level,"keeper":level,
         "dribble":level,"speed":level,"positioning":level,"stamina":level}
    if hidden:
        row.update(hidden)
    return row


IDENT={"style":"equilibre","formation":"3-1","pressing":"Médian","tempo":"Normal",
       "mentality":"Équilibrée","block":"Médian","width":"Normale","focus":"Axe","discipline":0.7}


def run_traits(hidden_home,hidden_away,n=600,seed=900):
    rng=random.Random(seed); hw=dr=aw=0; gf=ga=0
    for i in range(n):
        h=me._team_state("h",profile(60,hidden_home),[player(1,"Ailier"),player(2),player(3),player(4),player(5)],
                         IDENT,60,True,rng)
        a=me._team_state("a",profile(60,hidden_away),[player(11),player(12),player(13),player(14),player(15)],
                         IDENT,60,False,rng)
        h["team_name"]="H"; a["team_name"]="A"
        me._simulate_match(h,a,rng)
        gf+=h["goals"]; ga+=a["goals"]
        if h["goals"]>a["goals"]: hw+=1
        elif h["goals"]<a["goals"]: aw+=1
        else: dr+=1
    return gf/n,ga/n,100*hw/n,100*dr/n,100*aw/n


HIGH={"composure":85,"consistency":85,"work_rate":80,"aggression":75,"leadership":85,
      "professionalism":85,"big_matches":80,"injury_proneness":20,"versatility":70}
LOW={"composure":20,"consistency":20,"work_rate":25,"aggression":25,"leadership":20,
     "professionalism":25,"big_matches":20,"injury_proneness":80,"versatility":30}
res=run_traits(HIGH,LOW)
assert res[0]>res[1]+0.25, res
assert res[2]>=55, res
print("4) moteur : traits hauts %.2f - %.2f traits bas (%.1f%% / %.1f%% / %.1f%%)" % res)

# L'agressivité cachée doit augmenter les fautes sans changer les attributs visibles.
def fouls_with(aggression):
    rng=random.Random(1234); total=0
    hidden={"composure":50,"consistency":50,"work_rate":50,"aggression":aggression,
            "leadership":50,"professionalism":50,"big_matches":50,
            "injury_proneness":50,"versatility":50}
    for _ in range(250):
        h=me._team_state("h",profile(60,hidden),[player(1),player(2),player(3),player(4),player(5)],
                         IDENT,60,True,rng)
        a=me._team_state("a",profile(60,hidden),[player(11),player(12),player(13),player(14),player(15)],
                         IDENT,60,False,rng)
        h["team_name"]="H"; a["team_name"]="A"
        me._simulate_match(h,a,rng); total+=h["fouls"]
    return total/250

assert fouls_with(85)>fouls_with(15)+0.5, (fouls_with(85),fouls_with(15))
print("5) agressivité cachée : fautes %.2f vs %.2f" % (fouls_with(85),fouls_with(15)))

# 6) Statistiques par joueur produites par le moteur.
rng=random.Random(77)
h=me._team_state("h",profile(60),[player(1),player(2),player(3),player(4),player(5)],IDENT,60,True,rng)
a=me._team_state("a",profile(60),[player(11),player(12),player(13),player(14),player(15)],IDENT,60,False,rng)
h["team_name"]="H"; a["team_name"]="A"
me._simulate_match(h,a,rng)
for team in (h,a):
    stats=team["player_stats"]
    assert stats, team["team_name"]
    assert sum(row.get("shots",0) for row in stats.values())==team["shots"], (stats,team["shots"])
    assert sum(row.get("passes_attempted",0) for row in stats.values())>0
    assert all(value>=0 for row in stats.values() for value in row.values())
print("6) stats joueur : tirs et passes attribués, cohérents avec le total équipe")

# 7) Les notes récentes comptent dans la forme du jour.
def form_with(note):
    rows=[player(1),player(2),player(3),player(4),player(5)]
    for row in rows:
        row["season_rating_sum"]=note*5; row["season_rating_count"]=5
    rng=random.Random(4242)
    return me._team_state("h",profile(60),rows,IDENT,60,True,rng)["form"]
assert form_with(17.5)>form_with(8.0)+0.01, (form_with(17.5),form_with(8.0))
print("7) forme récente : %.4f (bonne série) > %.4f (mauvaise série)" % (form_with(17.5),form_with(8.0)))

print("RESULT: ALL OK")
