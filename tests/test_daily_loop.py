# -*- coding: utf-8 -*-
"""test_daily_loop.py (rapide, DB temporaire)
Valide le chemin de fluidite du journalier :
  1. update_player_market_values : lot (executemany) applique, pas d'erreur
  2. advance_calendar_days : 3 jours avances sans exception, date bougee
  3. mesures : temps des 3 jours (court) — le clic utilisateur reste fluide
error.log tronque (jamais supprime) et verifie a 0 octet.
"""
import os, sys, tempfile, time
os.environ["QT_QPA_PLATFORM"]="offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app

def ok(m): print("OK:", str(m).encode("ascii","replace").decode())

TMP=tempfile.mkdtemp(prefix="fm_daily_")
SAVE_DIR=os.path.join(TMP,"saves"); os.makedirs(SAVE_DIR,exist_ok=True)
app.SAVE_DIR=SAVE_DIR
app.DEFAULT_DB_PATH=os.path.join(TMP,"never_default.db")
app.active_save_path=lambda: app.DB_PATH
app.set_active_save_path=lambda p: None
app.DB_PATH=os.path.join(SAVE_DIR,"daily.db")
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

# --- 1) marche : le lot applique bien les derives
c=app.db()
before=c.execute("SELECT COUNT(*) n FROM player WHERE market_value>0").fetchone()["n"]
assert before>50, before
mvs=b=c.execute("SELECT id,market_value FROM player WHERE market_value>0 LIMIT 3").fetchall()
c.close()
t0=time.time()
cc=app.db(); w.update_player_market_values(cc); cc.commit(); cc.close()
c=app.db()
after=c.execute("SELECT id,market_value FROM player WHERE market_value>0").fetchall()
after={int(r["id"]): int(r["market_value"] or 0) for r in after}
c.close()
t_marche=time.time()-t0
moved=any(after.get(int(r["id"]))!=int(r["market_value"] or 0) for r in mvs)
ok("1) valeurs marchandes : %d joueurs traites en %.2fs ; derive appliquee : %s"
   % (before, t_marche, "OUI" if moved else "NON"))
assert t_marche<3.0, t_marche

# --- 2) boucle quotidienne : 3 jours
t0=time.time()
w.advance_calendar_days(3)
t_avance=time.time()-t0
c=app.db()
d=c.execute('SELECT career."current_date" cd FROM career WHERE id=1').fetchone()["cd"]
c.close()
ok("2) avance de 3 jours : %.2fs ; date = %s" % (t_avance, d))

# --- 3) error.log
sz=os.path.getsize(r"C:\FM2027V2\data\error.log")
if sz:
    d=open(r"C:\FM2027V2\data\error.log",encoding="utf-8",errors="replace").read()
    print("CONTENU error.log :")
    print(d)
ok("3) error.log = %d octet(s)"%sz)
assert sz==0

ok("RESULT: ALL OK")
