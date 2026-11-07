# -*- coding: utf-8 -*-
"""Probe onglet HISTORIQUE transferts : filtre VOIR TOUT / par saison,
construction LAZY (dirty flag), et vitesse de reconstruction."""
import os, sys, tempfile, datetime, time
os.environ["QT_QPA_PLATFORM"]="offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app

def ok(m): print("OK:", str(m).encode("ascii","replace").decode())

ROOT=r"C:\FM2027V2"
import random as _r
_r.seed(20260701)
tmp=tempfile.mkdtemp(prefix="fm_hist_")
saves=os.path.join(tmp,"saves"); os.makedirs(saves,exist_ok=True)
app.SAVE_DIR=saves; app.DB_PATH=os.path.join(saves,"hist.db")
identity={"name":"AS HISTO","arena_name":"A","color1":"#1f8a4d","color2":"#0f3d27",
          "kit_pattern":"vertical","logo_pattern":"shield","database_size":"classic",
          "division":6,"difficulty":"Normal"}
app.init_db(fresh_universe=True, selected_division=6, identity=identity)
try:
    open(os.path.join(ROOT,"data","error.log"),"r+b").truncate(0)
except FileNotFoundError:
    open(os.path.join(ROOT,"data","error.log"),"wb").close()

# Donnees d'historique synthetiques : 2 saisons, arrivees + departs + indemnites
conn=app.db()
players=[r["id"] for r in conn.execute("SELECT id FROM player WHERE club_id=1 LIMIT 6")]
now=datetime.date(2027,3,10)
for i,pid in enumerate(players):
    season=1 if i<3 else 2
    kind, detail = ("transfer","Recrute par AS HISTO") if i%2==0 else ("free","Libre")
    conn.execute("INSERT INTO player_history(player_id,season,club_id,kind,detail,created_at) VALUES(?,?,?,?,?,?)",
                 (pid,season,1,kind,detail,now.isoformat()))
    if kind=="transfer":
        conn.execute("INSERT INTO finance_tx(club_id,category,label,amount,created_at) VALUES(1,'Transfert',?,?,?)",
                     ("Transfert entrant Test %d"%pid,-45000,now.isoformat()))
players_out=[r["id"] for r in conn.execute("SELECT id FROM player WHERE club_id<>1 LIMIT 2")]
for pid in players_out:
    conn.execute("INSERT INTO player_history(player_id,season,club_id,kind,detail,created_at) VALUES(?,?,?,?,?,?)",
                 (pid,2,9,"transfer","Départ vers AS HISTO",now.isoformat()))
conn.commit(); conn.close()

from PySide6.QtWidgets import QApplication, QDialog
app.QApplication.instance() or app.QApplication([])
def _dexec(self,*a,**k):
    self.show(); app.QApplication.processEvents(); self.accept(); return QDialog.Accepted
app.QDialog.exec=_dexec
w=app.MainWindow(); w.show(); app.QApplication.processEvents()

assert hasattr(w,"transfer_history_table"), "table historique absente"
assert hasattr(w,"history_season_filter"), "filtre saison absent"
assert w.mercato_tabs.count()==6 and w.mercato_tabs.tabText(4)=="HISTORIQUE", w.mercato_tabs.tabText(4)

# 1) Construction forcee (onglet non courant) -> rempli
w.refresh_transfer_history(force=True)
n_all=w.transfer_history_table.rowCount()
assert n_all==8, n_all  # 6 interne + 2 departs externes (a nous)
ok("1) VOIR TOUT : %d lignes affichees"%n_all)

# 2) Filtre par saison -> conserve la liste des saisons et filtre
combo=w.history_season_filter
seasons=[combo.itemData(i) for i in range(combo.count())]
assert seasons[0] is None and set(seasons[1:])=={1,2}, seasons
pos=combo.findData(1); combo.setCurrentIndex(pos); app.QApplication.processEvents()
n_s1=w.transfer_history_table.rowCount()
dates=set(w.transfer_history_table.item(r,1).text() for r in range(n_s1))
assert n_s1==3 and all(s=="Saison 1" for s in dates), (n_s1,dates)
ok("2) filtre SAISON 1 : %d lignes, colonne saison coherente"%n_s1)
combo.setCurrentIndex(0); app.QApplication.processEvents()
assert w.transfer_history_table.rowCount()==n_all

# 3) LAZY : refresh sans force hors onglet -> simple marquage dirty, pas de rebuild
before=w.transfer_history_table.rowCount()
w._history_built=True; w._transfer_history_dirty=False
t0=time.perf_counter(); w.refresh_transfer_history(); dt=time.perf_counter()-t0
assert w._transfer_history_dirty is True and w.transfer_history_table.rowCount()==before, "lazy inoperant"
ok("3) lazy hors onglet : marquage dirty en %.1f ms, table intacte"%(dt*1000))

# 4) Retour sur l'onglet HISTORIQUE -> rebuild declenche par currentChanged
w.mercato_tabs.setCurrentIndex(4); app.QApplication.processEvents()
assert w._transfer_history_dirty is False and w.transfer_history_table.rowCount()==n_all
ok("4) bascule sur l'onglet : reconstruction via currentChanged")

# 5) Vitesse d'une reconstruction complete
t0=time.perf_counter(); w.refresh_transfer_history(force=True); dt=time.perf_counter()-t0
assert dt<0.8, dt
ok("5) reconstruction complete 250 max lignes : %.0f ms"%(dt*1000))

conn=app.db()
hist=conn.execute("SELECT COUNT(*) n FROM player_history WHERE kind IN ('transfer','free')").fetchone()["n"]
conn.close()
assert hist>=8, hist
try:
    open(os.path.join(ROOT,"data","error.log"),"r+b").truncate(0)
except FileNotFoundError:
    pass
print("RESULT: ALL OK")
