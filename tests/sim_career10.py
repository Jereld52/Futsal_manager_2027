# -*- coding: utf-8 -*-
r"""SIMULATION DE PARTIE REELLE - 10 ANS depuis la Ligue 6, comme un joueur humain.

Le manager-joueur :
- joue tous ses matchs (resultats bases sur la force de l'effectif, avance si meilleur) ;
- recrute a clôture et au fil de l'annee : PEPITES (potentiels 17-20 libres) d'abord,
  jeunes a fort potentiel ensuite, peres du club plafonnes par le budget ;
- re-mache les contrats clos, vend les surplus, garde ~un gardien minimum ;
- construit l'infrastructure : preparateur + recruteur + investissement centre (50k)
  + chantiers (centre niv.+, medical, arena, parking, services) en liste de priorites
  dependant de la division et du budget ;
- SAUVEGARDE REELLE a chaque cloture (fichier slot par saison + save_active_career).
Journal de carrierescre dans Temp\opencode\journal_career.txt
"""
import os, sys, shutil, random, json, statistics, time
os.environ["QT_QPA_PLATFORM"]="offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app

# ---- PROBE MEMOIRE (activable par MEMPROBE=1) : RSS du processus + comptage gc ----
import gc
if os.environ.get("MEMPROBE","0")=="1":
    import ctypes
    from ctypes import wintypes as _wt
    class _PMC(ctypes.Structure):
        _fields_=[("cb",_wt.DWORD),("PageFaultCount",_wt.DWORD),
                  ("PeakWorkingSetSize",ctypes.c_size_t),("WorkingSetSize",ctypes.c_size_t),
                  ("QuotaPeakPagedPoolUsage",ctypes.c_size_t),("QuotaPagedPoolUsage",ctypes.c_size_t),
                  ("QuotaPeakNonPagedPoolUsage",ctypes.c_size_t),("QuotaNonPagedPoolUsage",ctypes.c_size_t),
                  ("PagefileUsage",ctypes.c_size_t),("PeakPagefileUsage",ctypes.c_size_t)]
    def rss_mb():
        pmc=_PMC(); pmc.cb=ctypes.sizeof(_PMC)
        ctypes.windll.psapi.GetProcessMemoryInfo.argtypes=[_wt.HANDLE,ctypes.POINTER(_PMC),_wt.DWORD]
        ctypes.windll.psapi.GetProcessMemoryInfo.restype=_wt.BOOL
        h=ctypes.windll.kernel32.GetCurrentProcess()
        ok=ctypes.windll.psapi.GetProcessMemoryInfo(_wt.HANDLE(h),ctypes.byref(pmc),ctypes.sizeof(_PMC))
        if not ok: return -1
        return pmc.WorkingSetSize//1048576
    MEM_LAST=[0]
    def gcm():
        return getattr(w,"_manager_messages",[])
    def qt_counts():
        from PySide6.QtWidgets import QWidget, QLabel, QPushButton
        from PySide6.QtGui import QPixmap
        from collections import Counter
        widgets=pixmaps=0
        types=Counter()
        for o in gc.get_objects():
            t=type(o).__name__
            if t in ("QWidget","QLabel","QPushButton","QPixmap","QListWidgetItem","QTableWidgetItem","QFrame","QTimer","QPolygonF","QIcon"):
                types[t]+=1
        return types
    def mem_probe(tag):
        # TRAITEMENT DES DEFFERED DELETE DU Qt (pause d'evenements) + collecte
        # Python : sinon deleteLater telephonés du purgeur s'entassent dans la
        # file — la sonde offrirait une image faussement gonflée.
        try:
            from PySide6.QtCore import QCoreApplication, QEvent
            inst=QCoreApplication.instance()
            if inst is not None:
                while inst.hasPendingEvents(): inst.processEvents()
                # pousse specifiquement les	deferred delete en attente
                QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)
        except Exception: pass
        gc.collect()
        mb=rss_mb()
        counts=gc.get_count()
        objs=len(gc.get_objects())
        msgs=len(gcm())
        tc=qt_counts()
        # VUE C++ REELLE : allWidgets compte les widgets vivants cote Qt
        # (les compteurs gc n'entassent pas toujours des wrappers morts).
        _all,_top=-2,-2; _tlt={}
        try:
            from PySide6.QtWidgets import QApplication as _QA
            _w=_QA.allWidgets(); _all=len(_w)
            for x in _w:
                if x.parent() is None:
                    _k=type(x).__name__; _tlt[_k]=_tlt.get(_k,0)+1
            _top=sum(_tlt.values())
        except Exception: pass
        detail=" ".join(f"{k}={v:,}" for k,v in tc.most_common(8))
        # CENSUS PAR PARENT : ou s'entassent les widgets vivants ?
        _cen=""
        try:
            _cc={}
            for x in _w:
                p=x.parent()
                k=(type(p).__name__+"#"+str(p.objectName() or p.metaObject().className())) if p is not None else "ROOT"
                _cc[k]=_cc.get(k,0)+1
            _cen=" ; ".join(f"{k}={v}" for k,v in sorted(_cc.items(),key=lambda t:-t[1])[:7])
        except Exception: pass
        j(f"MEMPROBE {tag}: RSS={mb:,} Mo (+{max(0,mb-MEM_LAST[0]):,} depuis precedent) ; gc={counts} msgs_cache={msgs:,} objets_py={objs:,} ALLW={_all} TOP={_top} PARENTS[{_cen}] | {detail}".replace(","," "))
        MEM_LAST[0]=mb
else:
    def mem_probe(tag): pass

TMP=r"C:\Users\jauvray\AppData\Local\Temp\opencode"
SCENARIO=os.environ.get("SCENARIO","base")
SLOTS=os.path.join(TMP,f"slots_carriere_{SCENARIO}"); os.makedirs(SLOTS,exist_ok=True)
app.DB_PATH=os.path.join(TMP,f"carriere10_{SCENARIO}.db")
for ext in ("","-wal","-shm","-journal"):
    try: os.remove(app.DB_PATH+ext)
    except OSError: pass
JOURNAL=os.path.join(TMP,f"journal_career_{SCENARIO}.txt")
try: os.remove(JOURNAL)
except OSError: pass
def jline(s):
    with open(JOURNAL,"a",encoding="utf-8") as f: f.write(s+"\n")
def ok(m):
    line="OK: "+str(m)
    print(line.encode("ascii","replace").decode())
    jline(line)
def j(s):
    print("JOURNAL:", str(s).encode("ascii","replace").decode()); jline(s)

from PySide6.QtWidgets import QApplication, QDialog
def fast_exec(self,*a,**k):
    self.show(); app.QApplication.processEvents(); self.accept(); return QDialog.Accepted
QDialog.exec=fast_exec
app.QApplication.instance() or app.QApplication([])
identity={"name":"AS Horizon","arena_name":"Horizon Arena","color1":"#1f8a4d","color2":"#0f3d27",
          "kit_pattern":"vertical","logo_pattern":"shield","database_size":"classic","division":6}
app.init_db(fresh_universe=True, selected_division=6, identity=identity)
try: open(r"C:\FM2027V2\data\error.log","w").close()
except OSError: pass
w=app.MainWindow(); w.show(); w.resize(1600,900); app.QApplication.processEvents()

rng=random.Random(20261022)
PROMO_GRACE=0  # nombre de sessions mercato restantes sans chantiers apres une promotion
CASH_ANNOUNCED=set()  # pids deja annonces en vente (evite les annonces repetees tant que non vendu)
DIAG=(os.environ.get("DIAG","0")=="1")  # journaliser les refus du mercato (raison exacte)
# Plafond de masse salariale par palier (les salaires sont preleves chaque mois)
# : garde-fou du pilotage pour rester sous les recettes (TV + sponsor + matchday).
WAGE_CAP={6:20000,5:26000,4:34000,3:45000,2:60000,1:95000}

# MODE RICH ("je me crois riche") : aucun garde-fou du pilotage — pas de plafond
# de paie, pas de reserve, tous les chantiers et l'academie des la saison 2,
# achats au max des exigences. Sert a verifier la chaine de banqueroute du
# moteur (alerte, embargo, plan de redressement).
RICH=(os.environ.get("RICH","0")=="1")
RICH_X=int(os.environ.get("RICH_X","0"))

def diag():
    return DIAG

def wage_bill():
    return int(one("SELECT COALESCE(SUM(salary),0) s FROM player WHERE club_id=1")["s"])
TARGET_SEASONS=int(os.environ.get("SIM_SEASONS","10"))

def _norm(params): return tuple(params[0]) if len(params)==1 and isinstance(params[0],(tuple,list)) else params
def q(sql,*p):
    c=app.db(); rows=c.execute(sql,_norm(p)).fetchall(); c.close(); return rows
def one(sql,*p):
    c=app.db(); r=c.execute(sql,_norm(p)).fetchone(); c.close(); return r
def run(sql,*p):
    c=app.db(); c.execute(sql,_norm(p)); c.commit(); c.close()

def squad_dicts(cid):
    return [dict(r) for r in q("SELECT id,first_name,last_name,position,condition FROM player WHERE club_id=? ORDER BY id",(cid,))]

def full_rows(cid_or_fa=None):
    if cid_or_fa is None:
        return [dict(r) for r in q("SELECT p.* FROM player p WHERE p.club_id=1")]
    return [dict(r) for r in q("SELECT p.* FROM player p WHERE p.club_id=?", (cid_or_fa,))]

SPECS={"Gardien":90,"Défenseur":65,"Ailier":70,"Pivot":68,"Universel":62,"Milieu":70,"Attaquant":75}
def level(r): return app.player_level_from_row(r)
def pot(r): return app.player_potential_from_row(r)

def my_stats():
    rows=full_rows()
    if not rows: return {"n":0,"mean":0,"top":0,"gk":0}
    return {"n":len(rows),
            "mean":statistics.mean(level(r) for r in rows),
            "top":max(level(r) for r in rows),
            "gk":sum(1 for r in rows if r["position"]=="Gardien"),
            "def":sum(1 for r in rows if r["position"]=="Défenseur"),
            "mil":sum(1 for r in rows if r["position"] in ("Ailier","Pivot")),
            "att":sum(1 for r in rows if r["position"] in ("Universel",)),
            "fa":sum(1 for r in rows if int(r["is_free_agent"] or 0))}

def opp_mean_level(opp_id):
    rows=[dict(r) for r in q("SELECT * FROM player WHERE club_id=?",(opp_id,))]
    return statistics.mean(level(r) for r in rows) if rows else 8

def play_user_match():
    c=app.db(); fx=w._today_fixture_for_user(c); c.close()
    if fx is None: return None
    is_home=int(fx["home_club_id"])==1
    opp_id=int(fx["away_club_id"] if is_home else fx["home_club_id"])
    ms=my_stats(); om=opp_mean_level(opp_id)
    diff=(ms["mean"] if ms["mean"] else 6)-om
    p_win=0.52+0.055*diff
    if is_home: p_win+=0.04
    p_win=max(0.30,min(0.82,p_win))
    r=rng.random()
    if r<p_win: hg=max(0,round(rng.gauss(1.9+0.35*max(0,diff),1.1))); ag=max(0,round(rng.gauss(1.25-0.30*max(0,diff),1.0)))
    else: hg=max(0,round(rng.gauss(1.2-0.25*max(0,diff),1.0))); ag=max(0,round(rng.gauss(1.6+0.30*abs(min(0,diff)),1.1)))
    hg=min(hg,6); ag=min(ag,6)
    hg=0 if hg<0 else hg
    state={"finished":False,"is_home":is_home,"home":fx["home_name"],"away":fx["away_name"],
           "hg":hg,"ag":ag,"shots_h":9,"shots_a":6,"target_h":4,"target_a":3,
           "fouls_h":3,"fouls_a":5,"fixture_id":int(fx["id"]),"opponent_club_id":opp_id,
           "simulation_seed":rng.randint(1,10**9),"conditions":{},"opponent_conditions":{},
           "injuries":{},"card_events":[],"goals":[],"timeline":[],"player_goals":{},
           "all_players":squad_dicts(1)+squad_dicts(opp_id),
           "lineup":squad_dicts(1)[:5],"bench":squad_dicts(1)[5:],
           "opponent_lineup":squad_dicts(opp_id)[:5],"opponent_bench":squad_dicts(opp_id)[5:]}
    w.match_state=state
    assert w.finish_match() is True
    return {"hg":hg,"ag":ag,"win":hg>ag,"opp":fx["away_name"] if is_home else fx["home_name"]}

def need_positions():
    ms=my_stats()
    need=[]
    if ms["gk"]<1: need.append("Gardien")
    if ms["def"]<2: need.append("Défenseur")
    if ms["mil"]<3: need.extend(["Ailier","Pivot"])
    if ms["att"]<2: need.append("Universel")
    return need

def squad_full(): return my_stats()["n"]>=14

# ----------------------------- INFRA/STAFF -----------------------------
def affordable(key):
    c=app.db(); f=c.execute("SELECT * FROM facility WHERE id=1").fetchone(); c.close()
    lvl=int((f[key] if f else 1) or 1)
    if lvl>=8: return None
    cost,dur=w.facility_upgrade_terms(key,lvl)
    return {"key":key,"cost":cost,"dur":dur,"target":lvl+1,"current":lvl}

FACILITY_WISH=("youth_level","medical_level","arena_level","parking_level","marketing_level","lighting_level")
def try_facility(wish_keys):
    c=app.db(); _academy_locked=not app.academy_unlocked(c); c.close()
    # DOCTRINE "EFFECTIF D'ABORD" (lecon de la carriere de reference : 2,5 M€
    # d'infrastructures en L6 pendant que l'effectif restait sous le standard,
    # donc JAMAIS de promotion) : tant qu'on n'est pas au-dessus de la norme
    # de la division et en concurrence pour la montee, pas de chantier lourd.
    div=int(one("SELECT division FROM club WHERE id=1")["division"] or 6)
    ms=my_stats(); norm=app.DIVISION_LEVEL_NORM.get(div,9.5)
    promotion_ready=True if RICH else (ms["mean"]>=norm+0.6)
    for key in wish_keys:
        if key=="youth_level" and _academy_locked: continue  # campus ferme : ouverture via try_academy_invest d'abord
        info=affordable(key)
        if info is None: continue
        if div>=4 and not promotion_ready:
            if info["cost"]>=100000: continue  # chantier lourd suspendu jusqu'a la conquete
        c=app.db(); budget=int(c.execute("SELECT budget FROM club WHERE id=1").fetchone()["budget"]); c.close()
        if budget<info["cost"]+60000: continue
        label="Centre de formation" if key=="youth_level" else ("Pôle médical" if key=="medical_level" else ("Stade" if key=="arena_level" else ("Parking" if key=="parking_level" else ("Marketing" if key=="marketing_level" else "Eclairage"))))
        started=w.start_facility_project(key,info["cost"],f"{label} niv. {info['target']}",info["target"],info["dur"])
        if started:
            j(f"Infrastructure : chantier {label} niv {info['current']} -> {info['target']} lance ({info['cost']:,} €, {info['dur']} j).".replace(","," "))
            return True
    return False

def try_staff():
    prep=one("SELECT value FROM meta WHERE key='preparateur_physique_hired'")
    b=int(one("SELECT budget FROM club WHERE id=1")["budget"])
    if not (prep and prep["value"]=="1") and b>=90000:
        if w.hire_physical_trainer() is True:
            j("Staff : preparateur physique engage (30 000 €).")
            return True
    sl=int((one("SELECT value FROM meta WHERE key='scout_level'") or {"value":"0"})["value"] or 0)
    costs=(18000,30000,45000,65000,90000)
    if sl<2 and b>=costs[sl]+80000:
        before=b
        if w.hire_scout_staff() is True:
            j(f"Staff : scouting au niveau {sl+1} ({costs[sl]:,} €).".replace(","," "))
            return True
    phys=one("SELECT value FROM meta WHERE key='physio_hired'")
    physv=phys["value"]=="1" if phys else False
    if not physv and b>=130000:
        if w.hire_physiotherapist():
            j("Staff : kine engage (Service medical individuel, 30 000 €).")
            return True
    surete=126000
    compt=one("SELECT value FROM meta WHERE key='comptable_hired'")
    if b>=surete and not (compt and compt["value"]=="1"):
        if w.hire_generic_staff("comptable_hired","Comptable",2200):
            j("Staff : comptable engage (gestion fine du budget).")
            return True
    arch=one("SELECT value FROM meta WHERE key='architecte_hired'")
    if b>=200000 and not (arch and arch["value"]=="1"):
        if w.hire_generic_staff("architecte_hired","Architecte",3200):
            j("Staff : architecte engage (chantiers -couts/-delais).")
            return True
    return False

def try_sponsors():
    """Negocie et signe le sponsor de la saison (profil stable pour securiser
    la tresorerie des petits paliers, performance quand le club est solide).
    Sans ce coup de pouce la masse salariale mensuelle epuise le club en L6/L5."""
    row=one("SELECT value FROM meta WHERE key='sponsor_deal'")
    if row: return False
    used=one("SELECT value FROM meta WHERE key='sponsor_used_season'")
    season=int(one("SELECT season FROM club WHERE id=1")["season"] or 1)
    if used and int(used["value"] or 0)==season: return False
    w.negotiate_sponsor()
    offers=one("SELECT value FROM meta WHERE key='sponsor_offers'")
    if not offers: return False
    try: offs=json.loads(offers["value"] or "[]")
    except ValueError: return False
    if not offs: return False
    div=int(one("SELECT division FROM club WHERE id=1")["division"] or 6)
    want="performance" if div<=3 else "stable"
    pick=0
    for i,o in enumerate(offs):
        if o.get("profile")==want: pick=i; break
    w.sign_sponsor(pick)
    o=offs[pick]
    j(f"Sponsors : {o.get('name','sponsor')} ({want}) signe — {int(o.get('weekly',0)):,} €/semaine + {int(o.get('win_bonus',0)):,} € par victoire.".replace(","," "))
    return True

def try_academy_invest():
    c=app.db(); b=int(c.execute("SELECT budget FROM club WHERE id=1").fetchone()["budget"]); season=int(c.execute("SELECT season FROM club WHERE id=1").fetchone()["season"]); locked=not app.academy_unlocked(c); c.close()
    # A. Centre FERME au demarrage : on ne l'ouvre qu'apres s'etre installe (saison 3+,
    #    tresorerie confortable). Un gros investissement, pas un reflexe de jour 1.
    if locked:
        if RICH:
            if season>=2 and b>=250000:
                w.invest_academy()
                c=app.db(); opened=app.academy_unlocked(c); c.close()
                if opened:
                    j("Centre de formation : OUVERTURE immediate (mode riche, 250 000 €).")
                    return True
            return False
        if season>=3 and b>=450000:
            w.invest_academy()
            c=app.db(); opened=app.academy_unlocked(c); c.close()
            if opened:
                j("Centre de formation : OUVERTURE du campus engagee (250 000 €) — premiere promotion de jeunes en fin de saison.")
                return True
        return False
    row=one("SELECT value FROM meta WHERE key='academy_invest_season'")
    if row and int(row["value"] or 0)==season: return False
    if b>=90000:
        w.invest_academy()
        j("Centre de formation : investissement 50 000 € engage (+8 de note cette generation).")
        return True
    return False

# ----------------------------- MERCATO -----------------------------
def pending_player_ids():
    rows=q("SELECT action_data FROM manager_message WHERE kind IN ('market_offer','free_agent_contract') AND status IN ('waiting','ready')")
    ids=set()
    for r in rows:
        try: ids.add(int(json.loads(r["action_data"] or "{}").get("player_id",0)))
        except ValueError: pass
    return ids

def candidates():
    ids=pending_player_ids()
    mine={int(r["id"]) for r in q("SELECT id FROM player WHERE club_id=1")}
    my_pot_top=sorted((pot(r) for r in full_rows()),reverse=True)[:4]
    bench_pot=max(my_pot_top[3:]) if len(my_pot_top)>=4 else 0
    div=int(one("SELECT division FROM club WHERE id=1")["division"])
    out=[]
    # 0) PROJETS DE CROISSANCE (top priorite) : 15-17 ans a pot 16+, listés —
    #    ils arrivent a niveau modeste (demande de base), grandissent avec le
    #    préparateur et deviennent les cadres de la montee. La doctrine
    #    "du rien a l'elite" : construire, ne pas acheter des prima donnas.
    proj=q("""SELECT p.*, c.name cname, c.division cdiv FROM player p JOIN club c ON c.id=p.club_id
              WHERE p.club_id<>1 AND p.is_free_agent=0 AND p.transfer_listed=1
              AND p.age<=17 AND COALESCE(p.potential_fixed,0)>=16
              ORDER BY p.potential_fixed DESC, p.age ASC LIMIT 10""")
    for r in proj: r["_why"]="projet"
    # 1) PEPITES : potentiels 17-20, jeunes, sur le MARCHE uniquement (listés),
    #    clubs FAIBLES d'abord (moins cheres) — une offre sur un joueur non listé
    #    serait systématiquement refusée par son club.
    gems=q("""SELECT p.*, c.name cname, c.division cdiv FROM player p JOIN club c ON c.id=p.club_id
              WHERE p.club_id<>1 AND COALESCE(p.potential_fixed,0)>=17 AND p.age<=19 AND p.is_free_agent=0
              AND p.transfer_listed=1
              ORDER BY c.division DESC, p.potential_fixed DESC, p.age ASC LIMIT 12""")
    for r in gems: r["_why"]="pepite_club"
    gems_fa=[dict(r) for r in q("SELECT p.* FROM player p WHERE p.is_free_agent=1 AND COALESCE(p.potential_fixed,0)>=17 AND p.age<=19 LIMIT 8")]
    for r in gems_fa: r["_why"]="pepite_libre"
    # 2) jeunes a fort potentiel progressifs, listes
    youngs=q("""SELECT p.*, c.name cname, c.division cdiv FROM player p JOIN club c ON c.id=p.club_id
                WHERE p.club_id<>1 AND p.is_free_agent=0 AND p.transfer_listed=1 AND p.age<=21
                AND COALESCE(p.potential_fixed,0)>=15
                ORDER BY p.potential_fixed DESC LIMIT 14""")
    for r in youngs: r["_why"]="jeune"
    # 3) remplissage : uniquement si un poste manque, jeunes prometteurs
    fill=q("SELECT * FROM player WHERE is_free_agent=1 AND age<=20 AND COALESCE(potential_fixed,0)>=14 ORDER BY potential_fixed DESC LIMIT 10")
    for r in fill: r["_why"]="remplissage"
    # 4) coup de boost : cadre LISTE pour viser la montee — jeunes puis cadres a 26 ans max
    boosts=q("""SELECT p.*, c.name cname, c.division cdiv FROM player p JOIN club c ON c.id=p.club_id
                WHERE p.club_id<>1 AND p.is_free_agent=0 AND p.transfer_listed=1 AND p.age<=26
                AND COALESCE(p.potential_fixed,0)>=15 ORDER BY p.potential_fixed DESC, p.age ASC LIMIT 12""")
    for r in boosts: r["_why"]="cadre_liste"
    seen=set()
    for r in proj+gems_fa+gems+youngs+fill+boosts:
        pid=int(r["id"])
        if pid in ids or pid in seen or pid in mine or pid in ABANDON: continue
        seen.add(pid); out.append(r)
    return out

def demand_salary_for(r):
    signing=one("SELECT division,reputation FROM club WHERE id=1")
    d,_gap=app.player_salary_demand(r,signing)
    return int(d)

def make_room(reject_row=None):
    """Amicissement : quand le plafond de paie sature et qu'une cible vaut la
    peine, mettre en vente le moins prometteur des seniors (pot le plus bas,
    age le plus eleve) pour laisser respirer la masse salariale a la prochaine
    session (vente rcuperee plus tard par un acheteur IA)."""
    ms=my_stats()
    if ms["n"]<=11: return False
    rows=full_rows()
    listed={int(r["id"]) for r in q("SELECT id FROM player WHERE club_id=1 AND transfer_listed=1")}
    pool=[r for r in rows if int(r["id"]) not in listed and int(r["age"] or 0)>=22]
    if not pool: return False
    top={int(r["id"]) for r in sorted(rows,key=pot,reverse=True)[:4]}
    pool=[r for r in pool if int(r["id"]) not in top]
    if not pool: return False
    victim=min(pool,key=lambda r:(pot(r),-int(r["age"] or 0)))
    run("UPDATE player SET transfer_listed=1 WHERE id=?",(int(victim["id"]),))
    j(f"Amicissement : {victim['first_name']} {victim['last_name']} (pot {int(victim['potential_fixed'] or 0)}, {int(victim['age'])} ans) place sur la liste pour liberer de la masse salariale.")
    return True

def ask_budget_allowance():
    c=app.db(); b=int(c.execute("SELECT budget FROM club WHERE id=1").fetchone()["budget"]); div=int(c.execute("SELECT division FROM club WHERE id=1").fetchone()["division"] or 6); c.close()
    if RICH: return b  # mode riche : tout le budget est depensable
    # reserve infra : n'a de sens qu'en haut de pyramide ou quand la montee
    # est en cours — en L4-L6 sans effectif au standard, le thesaurus reste
    # au mercato (lecon de la carriere de reference).
    reserve=60000
    ms=my_stats(); norm=app.DIVISION_LEVEL_NORM.get(div,9.5)
    if div<=3 or ms["mean"]>=norm+0.6:
        for key in FACILITY_WISH:
            info=affordable(key)
            if info:
                reserve=max(reserve,min(info["cost"],250000)); break
        reserve=min(reserve,int(b*0.45))
    return b-reserve

def submit_for(r, why):
    budget=ask_budget_allowance()
    pref_salary=demand_salary_for(r)
    div=int(one("SELECT division FROM club WHERE id=1")["division"] or 6)
    cap=10**9 if RICH else WAGE_CAP.get(div,22000)
    if r["is_free_agent"]:
        bid=int(round(pref_salary*1.06/50.))*50+50
        cost=bid*12
        if not RICH and cost>budget:
            return False
        if wage_bill()+bid>cap:
            make_room()
            if wage_bill()+bid>cap:
                if diag():
                    j(f"DBG refus {r['first_name']} {r['last_name']} ({r.get('_why')}, {r['age']} ans, pot {int(r['potential_fixed'] or 0)}) : masse salariale saturee ({wage_bill():,} + {bid:,} > plafond {cap:,}).".replace(","," "))
                return False
        bid=max(700, bid)
        w.submit_market_offer(int(r["id"]), bid, years=3)
        j(f"Mercato entrant : offre envoyee a {r['first_name']} {r['last_name']} ({r.get('_why')}, {int(r['age'])} ans, pot {int(r['potential_fixed'] or 0)}) — salaire propose {bid:,} €/mois.".replace(","," "))
        return True
    # joueur en club : ouverture marchee, cap selon la raison du recrutement
    val=int(r["market_value"] or 5000)
    opening=int(round(val*(1.15 if r.get("_why")=="pepite_club" else 0.95)/500.))*500
    sal=int(round(pref_salary*1.04/50.))*50
    fee_cap=int(max(10000,market_val_target(r)))
    fee=min(opening,fee_cap)
    wage_cap=10**9 if RICH else WAGE_CAP.get(div,22000)
    # Le moteur debite l'indemnite a la signature ; les salaires passent dans la
    # masse salariale MENSUELLE : garder une couverture d'une annee de salaires
    # ET respecter le PLAFOND DE PAIE (et non le plafond d'indemnite).
    if wage_bill()+sal>wage_cap:
        make_room()
        if wage_bill()+sal>wage_cap:
            if diag():
                j(f"DBG refus {r['first_name']} {r['last_name']} ({r.get('_why')}, {r['age']} ans, pot {int(r['potential_fixed'] or 0)}, list\u00e9={int(r['transfer_listed'] or 0)}) : masse salariale saturee ({wage_bill():,} + {sal:,} > plafond de paie {wage_cap:,}).".replace(","," "))
            return False
    if not RICH and fee+sal*12>budget*0.90:
        if diag():
            j(f"DBG refus {r['first_name']} {r['last_name']} ({r.get('_why')}, {r['age']} ans, pot {int(r['potential_fixed'] or 0)}, list\u00e9={int(r['transfer_listed'] or 0)}) : indemnité {fee:,} + sal 1an {sal*12:,} = {(fee+sal*12):,} > 0.90×budget {budget:,}.".replace(","," "))
        return False
    w.submit_market_offer(int(r["id"]), max(250,fee), years=3, player_salary=max(600,sal))
    j(f"Mercato entrant : offre envoyee a {r['first_name']} {r['last_name']} ({r.get('_why')}, {int(r['age'])} ans, pot {int(r['potential_fixed'] or 0)}) — indemnité {fee:,} € + salaire {sal:,} €/mois.".replace(","," "))
    return True

def market_val_target(r):
    v=int(r["market_value"] or 4000)
    if r.get("_why")=="pepite_club": return min(v*2, ask_budget_allowance()*0.5)
    return v*2

def mercato_session(limit=3):
    targets=candidates()
    need=need_positions()
    done=0
    for r in targets:
        if done>=limit: break
        if r.get("_why")=="remplissage" and not need: continue
        if r.get("_why")=="remplissage" and r["position"] not in need: continue
        if submit_for(r,r.get("_why")): done+=1
    if done==0:
        if diag():
            nlist=int(one("SELECT COUNT(*) n FROM player WHERE club_id<>1 AND is_free_agent=0 AND transfer_listed=1")["n"])
            j(f"DBG session vide : {len(targets)} cibles candidates ({done} conclues), listés au monde={nlist}, budget_dispo={ask_budget_allowance():,} €.".replace(","," "))
        j("Mercato : aucune cible abordable cette session (budget reserve infra).")
    return done

ROUNDS={}
ABANDON=set()
RENEWED_SEASON=set()
PROBE={}  # pid -> valeur de base observee (pour mesurer la plus-value avant revente)

def sync_msg_cache():
    w._manager_messages=q("SELECT * FROM manager_message ORDER BY id DESC")

def react_messages():
    """Reagit comme un joueur : ACCEPTER ce qui est acceptable, afranchir/relancer sinon."""
    acted=0
    sync_msg_cache()
    msgs=q("SELECT * FROM manager_message WHERE kind IN ('contract_offer','free_agent_contract','market_offer','transfer_sale','transfer_sale_counter') AND status='ready'")
    for msg in msgs:
        try: data=json.loads(msg["action_data"] or "{}")
        except ValueError: data={}
        kind=msg["kind"]; out=data.get("outcome")
        if out in ("accepted","seller_accepted"):
            if kind in ("market_offer","transfer_sale","transfer_sale_counter") and my_stats()["n"]>=16:
                sync_msg_cache(); w.resolve_manager_message("reject",int(msg["id"])); acted+=1
            else:
                pname=one("SELECT first_name,last_name FROM player WHERE id=?",(int(data.get("player_id",0) or 0),))
                nm=f"{pname['first_name']} {pname['last_name']}" if pname else "cible"
                if kind in ("contract_offer","free_agent_contract"):
                    j(f"Signature reussie : {nm} (salaire {int(data.get('final_salary',data.get('counter_salary',data.get('offer_salary',0))) or 0):,} €/mois, {int(data.get('final_years',data.get('counter_years',data.get('offer_years',2))) or 2)} ans).".replace(","," "))
                else:
                    j(f"Transfert conclu : {nm} pour {int(data.get('final_fee',data.get('counter_fee',data.get('bid',0))) or 0):,} €.".replace(","," "))
                sync_msg_cache(); w.resolve_manager_message("accept",int(msg["id"]))
                brec=one("SELECT market_value FROM player WHERE id=?",(int(data.get("player_id",0) or 0),))
                if brec: PROBE[int(data["player_id"])]=int(brec["market_value"] or 0)
                acted+=1
        elif out=="counter" or out=="player_counter":
            pid=int(data.get("player_id",0) or 0)
            pname=one("SELECT first_name,last_name FROM player WHERE id=?",(pid,))
            nm=f"{pname['first_name']} {pname['last_name']}" if pname else "cible"
            ROUNDS[pid]=ROUNDS.get(pid,0)+1
            if ROUNDS[pid]>=3:
                ABANDON.add(pid)
                j(f"Negociation abandonnee : {nm} (trop cher ou resistant).")
                sync_msg_cache(); w.resolve_manager_message("reject",int(msg["id"])); acted+=1
            elif kind=="market_offer":
                asked=int(data.get("counter_fee",0) or data.get("final_fee",0) or 0)
                sal=int(data.get("counter_salary",0) or data.get("offer_salary",0) or 0)
                bid=int(round(asked*1.03/500.))*500 if asked else max(250,int((data.get("bid",0) or 250)*1.1))
                sms=sal+200 if sal else None
                j(f"Negociation : {nm} demande {asked:,} € + {sal:,} €/mois — relance {ROUNDS[pid]} a {bid:,} €.".replace(","," "))
                sync_msg_cache(); w.resolve_manager_message("reject",int(msg["id"]))
                w.submit_market_offer(pid,bid,years=int(data.get("counter_years",data.get("offer_years",3)) or 3),player_salary=sms if sms and sms>=600 else None)
                acted+=1
            else:
                cs=int(data.get("counter_salary",0) or data.get("offer_salary",0) or 0)
                sync_msg_cache()
                if cs:
                    w.resolve_manager_message("reject",int(msg["id"]))
                    queue_contract_offer(pid,int(round(cs*1.04)),int(data.get("counter_years",data.get("offer_years",2)) or 3))
                else:
                    w.resolve_manager_message("reject",int(msg["id"]))
                acted+=1
        elif out=="offer" and kind in ("transfer_sale","transfer_sale_counter"):
            pid=int(data.get("player_id",0) or 0)
            prow=one("SELECT market_value,first_name,last_name,age,position FROM player WHERE id=?",(pid,)) if pid else None
            fee=int(data.get("fee",data.get("final_fee",0)) or 0)
            val=int((prow["market_value"] if prow else 0) or 0)
            same_pos=sum(1 for x in full_rows() if x["position"]==(prow["position"] if prow else "")) if prow else 0
            if prow and fee>=int(val*1.15) and same_pos>=2 and my_stats()["n"]>12:
                base=PROBE.get(pid,val)
                delta=int((fee-max(base,1))*100/max(base,1)) if base>0 else 0
                gain=f"+{delta}%" if delta>=0 else f"-{abs(delta)}%"
                j(f"Vente {gain} : {prow['first_name']} {prow['last_name']} ({prow['age']} ans) cede {fee:,} € (achete ~{base:,}, valeur {val:,}).".replace(","," "))
                sync_msg_cache(); w.resolve_manager_message("accept",int(msg["id"])); acted+=1
            else:
                sync_msg_cache(); w.resolve_manager_message("reject",int(msg["id"])); acted+=1
        elif out=="unavailable":
            sync_msg_cache(); w.resolve_manager_message("reject",int(msg["id"])); acted+=1
    return acted

def queue_contract_offer(pid, salary, years=None):
    conn_arg=None
    c=app.db(); cd=w._current_date(c); c.close()
    import datetime as dt
    due=(app.parse_iso(cd)+dt.timedelta(days=2)).isoformat()
    c=app.db()
    app.queue_manager_message(c,"contract_offer","Proposition de contrat envoyée",f"Proposition sentilisée.",cd,due,{"player_id":pid,"offer_salary":int(salary),"offer_years":int(years or 2)},is_read=True)
    c.commit(); c.close()

def renew_contracts():
    acted=0
    c=app.db(); season=int(c.execute("SELECT season FROM club WHERE id=1").fetchone()["season"]); c.close()
    if season in RENEWED_SEASON: return 0
    ms=my_stats()
    div=int(one("SELECT division FROM club WHERE id=1")["division"] or 6)
    cap=10**9 if RICH else WAGE_CAP.get(div,22000)
    bill=wage_bill()
    for r in full_rows():
        if bill>=cap: break
        cy=int(r["contract_years"] or 0)
        if cy<=1 and int(r["age"] or 30)<=33:
            salary=int(r["salary"] or 800)
            idle=min(3, int(r["contract_years"] or 1)+2)
            # demande moteur-conforme (morale, niveau) mais hausse plafonnee a +20%
            dem=int(max(salary+250, salary*1.06+max(0,70-int(r["morale"] or 70))*.002*1000+max(0,level(r)-14)*.012*1000))
            dem=min(int(round(dem/50.))*50+50, int(salary*1.2)+250)
            budget=ask_budget_allowance()
            if bill+(dem-salary)>cap: continue
            if dem*12*2<=budget:
                queue_contract_offer(int(r["id"]), dem, idle); bill+=dem-salary; acted+=1
    RENEWED_SEASON.add(season)
    return acted

def list_for_sale():
    rows=full_rows()
    for r in rows:
        PROBE.setdefault(int(r["id"]),int(r["market_value"] or 0))
    placed=0
    # 1) surcharge d'effectif : le moins prometteur part (plafond pratique ~19 joueurs)
    if my_stats()["n"]>16:
        cand=min((r for r in rows if int(r["injury_days"] or 0)==0),key=pot,default=None)
        if cand is not None:
            run("UPDATE player SET transfer_listed=1 WHERE id=?",(int(cand["id"]),))
            if int(cand["id"]) not in CASH_ANNOUNCED:
                CASH_ANNOUNCED.add(int(cand["id"]))
                j(f"Mercato sortant : {cand['first_name']} {cand['last_name']} ({cand['position']}, {int(cand['age'])} ans) place sur la liste des transferts.")
            placed+=1
    # 2) CASH-OUT : le meilleur ratio de plus-value, si le poste reste couvert en doublon
    #    Politique "hold" : on garde la pepite jusqu'a maturite (niveau 12+, 21 ans+)
    #    pour encaisser des montants L2/L1 (absolute value), plutot qu'une vente rapide.
    hold=(os.environ.get("GEM_POLICY","quick")=="hold")
    cands=[]
    div=int(one("SELECT division FROM club WHERE id=1")["division"])
    # Plancher de vente echelonne : une pepite niveau 11-12 vaut deux fois plus en L3 qu'en L6.
    value_floor=int(20000*(1.0+(6-max(1,div))*0.30))
    for r in rows:
        pid=int(r["id"]); base=PROBE.get(pid,0)
        cur=int(r["market_value"] or 0)
        age=int(r["age"] or 0); lvl=int(level(r))
        if hold:
            if base>0 and cur>=base*1.9 and cur>=value_floor and lvl>=11 and age>=20 and int(r["injury_days"] or 0)==0:
                cands.append((cur/base,cur,r))
        else:
            if base>0 and cur>=base*1.9 and cur>=15000 and age>=19 and int(r["injury_days"] or 0)==0:
                cands.append((cur/base,cur,r))
    for ratio,cur,r in sorted(cands,reverse=True):
        pos=r["position"]
        if my_stats()["n"]<13: break
        if sum(1 for x in rows if x["position"]==pos)<2: continue
        run("UPDATE player SET transfer_listed=1 WHERE id=?",(int(r["id"]),))
        if int(r["id"]) not in CASH_ANNOUNCED:
            CASH_ANNOUNCED.add(int(r["id"]))
            j(f"CASH-OUT : {r['first_name']} {r['last_name']} ({pos}, {int(r['age'])} ans, pot {int(r['potential_fixed'] or 0)}) en vente pour encaisser la plus-value (x{ratio:.1f} -> {cur:,} €).".replace(","," "))
        placed+=1
        break
    return placed

# ----------------------------- STRUCTURE DE SAISON -----------------------------
cur=int(one("SELECT season FROM club WHERE id=1")["season"])
START_SEASON=cur
season_seen=cur
day=0; session_day=-999
results_log=[]
t0=time.time()
j(f"Debut de partie : {identity['name']}, depart en Ligue 6 (saison {season_seen}).")
ms=my_stats(); c=app.db(); budget0=int(c.execute("SELECT budget FROM club WHERE id=1").fetchone()["budget"]); c.close()
# MODE RICH_X : le club SE CROIT riche — capital fantaisiste injecte (le signal
# d'un president irresponeux) ; les recettes reelles restent celles de la L6,
# c'est exactement le terrain d'essai de la chaine de banqueroute du moteur.
if RICH_X>0:
    injection=budget0*(RICH_X-1)
    run("UPDATE club SET budget=budget+?",(injection,))
    budget0+=injection
    j(f"MODE RICH X{RICH_X} : capital fantaisiste injecte (+{injection:,} €.)".replace(","," "))
    # Paie mensuelle COMPLETE des le depart (pas d'exemption prepaye) :
    # c'est le vrai terrain de la banqueroute — la paie depasse les recettes.
    run("INSERT OR REPLACE INTO meta(key,value) VALUES('payroll_reform_season','1')")
    run("INSERT OR REPLACE INTO meta(key,value) VALUES('prepaid_wage_ids','[]')")
    j("MODE RICH : rien n'est pre-payé — la paie mensuelle complete frappe des le mois 1.")
j(f"Effectif de depart : {ms['n']} joueurs, niveau moyen {ms['mean']:.1f}, gardien: {ms['gk']}, budget {budget0:,} €.".replace(","," "))

try_sponsors()  # sponsor de la saison 1 avant d'entrer dans la boucle
IT=0; MAXIT=12500
while season_seen<TARGET_SEASONS and IT<MAXIT:
    IT+=1
    if IT%150==0: mem_probe(f"IT {IT}")
    c=app.db(); fx=w._today_fixture_for_user(c); c.close()
    # messages : agir sur les reponses pretes avant d'avancer le temps
    acted=react_messages()
    if fx is not None:
        res=play_user_match()
        if res: results_log.append(res)
    else:
        w.advance_calendar_days(1)
        # session mercato chaque mois +5 jours, apres cloture immediate
        day+=1
        if day-session_day>=25:
            session_day=day
            if PROMO_GRACE>0:
                PROMO_GRACE-=1
                j("Post-promotion : chantiers suspendus, la tresorerie va d'abord aux renforts.")
                try_staff()
            else:
                try_staff(); try_academy_invest(); try_facility(FACILITY_WISH)
            renew_contracts(); react_messages()
            if not squad_full():
                mercato_session(limit=2)
            list_for_sale()
    cur=int(one("SELECT season FROM club WHERE id=1")["season"])
    if cur>season_seen:
        season_seen=cur
        prev=cur-1
        # bilan de l'an passe
        me=one("SELECT division,budget FROM club WHERE id=1")
        hon=q("SELECT kind FROM club_honours WHERE season=? AND club_id=1",(prev,))
        kinds=[r["kind"] for r in hon]
        rank=q("SELECT rank FROM season_archive WHERE season=? AND club_id=1",(prev,))
        ranktxt=rank[0]["rank"] if rank else "?"
        chs=q("""SELECT c.name n,s.division d FROM season_archive s JOIN club c ON c.id=s.club_id
                 WHERE s.season=? AND s.rank=1 ORDER BY s.division""",(prev,))
        ch_txt=" | ".join(f"L{r['d']}: {r['n']}" for r in chs)
        ms=my_stats()
        wins=sum(1 for r in results_log if r["win"]); draws=sum(1 for r in results_log if not r["win"] and r["hg"]==r["ag"]); losses=len(results_log)-wins-draws
        gf=sum(r["hg"] for r in results_log); ga=sum(r["ag"] for r in results_log)
        fac=app.db(); f=fac.execute("SELECT * FROM facility WHERE id=1").fetchone(); fac.close()
        c=app.db(); prof=app.academy_profile(c); c.close()
        top=sorted(full_rows(),key=lambda r:pot(r),reverse=True)[:3]
        top_txt=", ".join(f"{r['first_name'][0]}. {r['last_name']} ({int(r['age'])} ans, pot {int(r['potential_fixed'] or 0)}/20)" for r in top)
        j("")
        j(f"### SAISON {prev} TERMINEE -> saison {cur} en L{me['division']}")
        # CHECK MEMOIRE PAR SAISON (retour « des checks entre les saisons si ca
        # monte trop ») : RSS + objet Qt a chaque clôture pour suivre la pente réelle.
        if os.environ.get("MEMPROBE","0")=="1":
            try: mem_probe(f"FIN SAISON {prev}")
            except Exception: pass
        j(f"Classement: {ranktxt}. Bilan sportif: {wins}V-{draws}N-{losses}D, {gf} buts pour / {ga} contre sur {len(results_log)} matchs.")
        j(f"Trophees: {', '.join(kinds) if kinds else 'aucun'}.")
        j(f"Monde: {ch_txt}")
        j(f"Effectif: {ms['n']} joueurs, niveau moyen {ms['mean']:.1f}, gardien {ms['gk']}, budget {int(me['budget']):,} €.".replace(","," "))
        j(f"Infra: centre niv {int(f['youth_level'])}, medical niv {int(f['medical_level'])}, arena niv {int(f['arena_level'])}, academie note {int(prof['total'])}/100.")
        j(f"Top 3 potentiels: {top_txt}")
        # Renfort d'abord, chantiers ensuite : apres une promotion, les 2 sessions
        # suivantes gardent la tresorerie pour signer des cadres au niveau du palier.
        if any(k=="promotion" for k in kinds) and PROMO_GRACE<=0:
            PROMO_GRACE=2
        # session d'actions post-cloture
        try_sponsors()
        if PROMO_GRACE>0:
            PROMO_GRACE-=1
            j("Post-promotion : chantiers suspendus 1 session, la tresorerie va d'abord aux renforts.")
            try_staff()
        else:
            while try_facility(FACILITY_WISH): pass
            try_staff()
            try_academy_invest()
        renew_contracts(); react_messages()
        if not squad_full(): mercato_session(limit=4)
        list_for_sale()
        results_log=[]
        ROUNDS.clear(); ABANDON.clear()
        ours={int(r["id"]) for r in full_rows()}
        for pid in [p for p in PROBE if p not in ours]: PROBE.pop(pid,None)
        # SAUVEGARDE REELLE (slot + checkpoint)
        assert w.save_active_career(show_notice=False) is True
        shutil.copy2(app.DB_PATH,os.path.join(SLOTS,f"fin_saison{prev:02d}_L{int(me['division'])}.db"))
        j(f"SAUVEGARDE ok : slots/fin_saison{prev:02d}_L{int(me['division'])}.db")

# FIN DE PARTIE
me=one("SELECT division,budget FROM club WHERE id=1")
ms=my_stats()
c=app.db(); f=c.execute("SELECT * FROM facility WHERE id=1").fetchone(); c.close()
c=app.db(); prof=app.academy_profile(c); c.close()
hon=q("SELECT season,kind FROM club_honours WHERE club_id=1 ORDER BY season")
titles=[f"s{r['season']} {r['kind']}" for r in hon]
j("")
_season_now=int(one("SELECT season FROM club WHERE id=1")["season"])
_played=max(0,_season_now-START_SEASON)
j(f"==== FIN DE CARRIERE ({_played} saison(s) jouees) ====")
j(f"Division finale : L{int(me['division'])} | Budget {int(me['budget']):,} €.".replace(","," "))
j(f"Effectif final : {ms['n']} joueurs, niveau moyen {ms['mean']:.1f}, meilleur niveau {ms['top']}, gardien {ms['gk']}.")
j(f"Infrastructure : arena {int(f['arena_level'])}/8, centre {int(f['youth_level'])}/8, medical {int(f['medical_level'])}/8.")
j(f"Academie : note {int(prof['total'])}/100.")
j(f"Palmares complet : {', '.join(titles) if titles else 'aucun trophée'}")
DIVNORM=app.DIVISION_LEVEL_NORM
expected=DIVNORM.get(int(me['division']),10)
if ms['mean']>=expected-1: ok(f"effectif au standard de la division (moyen {ms['mean']:.1f} vs attendu ~{expected})")
assert os.path.getsize(r"C:\FM2027V2\data\error.log")==0, "error.log non vide"
ok("zero erreur engine (error.log 0 octet)")
# export demonstratif : COPIE de sauvegarde offerte au joueur pour tester dans l'UI (sauvegardes existantes intactes)
# opt-in : DEMO_EXPORT=1 uniquement (les runs de verification par defaut n'ecrivent RIEN dans data/saves).
import datetime as _dt
if os.environ.get("DEMO_EXPORT")=="1" or SCENARIO in ("hold","hold2"):
    _demo_name=("Demo_carriere_AS_Horizon_%s.db"%_dt.date.today().strftime("%Y%m%d")) if SCENARIO in ("hold","hold2") else ("Demo_carriere_%s_%s.db"%(SCENARIO,_dt.date.today().strftime("%Y%m%d")))
    demo=os.path.join(r"C:\FM2027V2\data\saves",_demo_name)
    shutil.copy2(app.DB_PATH,demo)
    ok(f"sauvegarde de test proposee : {demo}")
w.save_active_career=lambda show_notice=False: True
print(f"RESULT: RUN TERMINE — {_played} saison(s) jouees")
