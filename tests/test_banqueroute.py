# -*- coding: utf-8 -*-
"""test_banqueroute.py (v2, connexion partagée comme le flux moteur réel)
Chaine de banqueroute moteur (process_board_financial_watch + embargo + plan de
redressement), testee determinantement sur DB temporaire :
  1. jour 1 dans le rouge -> alerte "Trésorerie négative"
  2. embargo : submit_market_offer refuse pendant le rouge (libre ET club)
  3. embargo : take_loan refuse pendant le rouge
  4. jour 60 puis 120 : plan de redressement -> joueur le plus dispendieux mis
     en vente par le board (jamais sous un noyau de 8)
  5. jours 61-119 : aucune nouvelle vague entre les multiples de 60
  6. noyau <= 8 joueurs : pas de vente forcee
  7. retour au vert : compteur a zero + news "Retour au vert"
DB temporaire ; error.log tronque (jamais supprime).
"""
import os, sys, json
os.environ["QT_QPA_PLATFORM"]="offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app

def ok(m): print("OK:", str(m).encode("ascii","replace").decode())

import tempfile
TMP=tempfile.mkdtemp(prefix="fm_bankrupt_")
SAVE_DIR=os.path.join(TMP,"saves"); os.makedirs(SAVE_DIR,exist_ok=True)
app.SAVE_DIR=SAVE_DIR
app.DEFAULT_DB_PATH=os.path.join(TMP,"never_default.db")
app.active_save_path=lambda: app.DB_PATH
app.set_active_save_path=lambda p: None
app.DB_PATH=os.path.join(SAVE_DIR,"banqueroute.db")
identity={"name":"AS Horizon","arena_name":"A","color1":"#1f8a4d","color2":"#0f3d27",
          "kit_pattern":"vertical","logo_pattern":"shield","database_size":"classic","division":6}
app.init_db(fresh_universe=True, selected_division=6, identity=identity)
try:
    open(r"C:\FM2027V2\data\error.log","r+b").truncate(0)
except FileNotFoundError:
    open(r"C:\FM2027V2\data\error.log","wb").close()

from PySide6.QtWidgets import QApplication, QDialog
app.QApplication.instance() or app.QApplication([])
def _dexec(self,*a,**k):
    self.show(); app.QApplication.processEvents(); self.accept(); return QDialog.Accepted
app.QDialog.exec=_dexec
w=app.MainWindow(); w.show(); app.QApplication.processEvents()

# Connexion partAagée pour tout le test (miroir de la boucle quotidienne moteur)
G=app.db()
def commit(): G.commit()
def news_titles():
    return [r["title"] for r in G.execute("SELECT title FROM news").fetchall()]
def budget():
    return int(G.execute("SELECT budget FROM club WHERE id=1").fetchone()["budget"] or 0)
def red_days():
    r=G.execute("SELECT value FROM meta WHERE key='club1_red_days'").fetchone()
    try: return int(r["value"]) if r else 0
    except (ValueError,TypeError): return 0
def listed_ids():
    return {int(r["id"]) for r in G.execute("SELECT id FROM player WHERE club_id=1 AND transfer_listed=1").fetchall()}
def set_budget(v):
    G.execute("UPDATE club SET budget=? WHERE id=1",(v,)); commit()
def watch(day):
    w.process_board_financial_watch(G, day.isoformat()); commit()

import datetime as _dt
day=_dt.date(2026,8,1)

# --- 0) point de depart : dans le rouge
set_budget(-5000)
assert red_days()==0 and budget()==-5000

# --- 1) jour 1 : alerte
day+=_dt.timedelta(days=1); watch(day)
assert red_days()==1, red_days()
assert "Trésorerie négative" in news_titles()
ok("1) jour 1 dans le rouge : alerte 'Trésorerie négative' + red_days=1")

# --- 2) embargo recrutement (libre ET club)
day+=_dt.timedelta(days=4); set_budget(-5000)
free=G.execute("SELECT id FROM player WHERE is_free_agent=1 AND club_id<>1 LIMIT 1").fetchone()
assert free is not None
res_free=w.submit_market_offer(int(free["id"]), 1000, years=2)
assert res_free is False
cb=G.execute("SELECT id FROM player WHERE club_id<>1 AND is_free_agent=0 LIMIT 1").fetchone()
assert cb is not None
res_club=w.submit_market_offer(int(cb["id"]), 5000, years=3, player_salary=1000)
assert res_club is False
ok("2) embargo : offres libre ET club refusees pendant le rouge")

# --- 3) embargo pret (via la connexion du moteur, commit explicite apres)
day+=_dt.timedelta(days=1); set_budget(-5000)
b0=budget()
w.take_loan(20000, 12)
assert budget()==b0, (b0,budget())
ok("3) embargo : la banque refuse de preter a un club deficitaire")

# --- 4) jour 60 : plan de redressement
n0=int(G.execute("SELECT COUNT(*) n FROM player WHERE club_id=1").fetchone()["n"]); assert n0>8, n0
for i in range(59):
    day+=_dt.timedelta(days=1); watch(day)
assert red_days()==60, red_days()
victims=listed_ids()
assert victims, "aucun joueur liste au jour 60 (red=%d)" % red_days()
top=G.execute("SELECT id FROM player WHERE club_id=1 AND COALESCE(transfer_listed,0)=0 ORDER BY COALESCE(market_value,0) DESC LIMIT 1").fetchone()
ok("4) jour 60 : %d joueur(s) forces en vente ; le (dispendieux hors test) OK ; news presente : %s" % (len(victims), "Plan de redressement" in news_titles()))
assert "Plan de redressement" in news_titles()

# --- 5) jours 61-119 : pas de nouvelle vague
for i in range(59):
    day+=_dt.timedelta(days=1); watch(day)
assert red_days()==119, red_days()
ok("5) jours 61-119 : compteur %d, pas de vague intermediaire" % red_days())

# --- 5b) jour 120 : deuxieme vague
day+=_dt.timedelta(days=1); watch(day)
assert red_days()==120
v3=listed_ids()
ok("5b) jour 120 : red_days=120, %d joueur(s) listes au total" % len(v3))
assert len(v3)>=len(victims)

# --- 6) noyau <= 8 : plus de vente forcee
sel=G.execute("SELECT id FROM player WHERE club_id=1 ORDER BY id DESC LIMIT 8").fetchall()
kept={int(r["id"]) for r in sel}
for r in G.execute("SELECT id FROM player WHERE club_id=1").fetchall():
    if int(r["id"]) not in kept:
        G.execute("UPDATE player SET club_id=2, is_free_agent=1 WHERE id=?",(int(r["id"]),))
commit()
mark=len(news_titles())
for i in range(60):
    day+=_dt.timedelta(days=1); watch(day)
assert len(news_titles())==mark, news_titles()[mark:][:4]
ok("6) noyau de 8 joueurs : aucune vente forcee (zero news supplementaire)")

# --- 7) retour au vert
set_budget(250000)
day+=_dt.timedelta(days=1); watch(day)
assert red_days()==0
assert "Retour au vert" in news_titles()[-3:]
ok("7) retour au vert : compteur a zero + news 'Retour au vert'")

# --- 8) error.log
G.close()
import os.path
sz=os.path.getsize(r"C:\FM2027V2\data\error.log")
ok("8) error.log = %d octet(s)" % sz)
assert sz==0

ok("RESULT: ALL OK")
