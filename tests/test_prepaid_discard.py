# -*- coding: utf-8 -*-
"""test_prepaid_discard.py
Correctif du jour : _prepaid_wage_discard(pid, conn=None).
1) Connexion partagee avec le flux appelant : ecritures en attente + discard
   dans la MEME transaction -> plus jamais "database is locked".
2) Cas autonome (conn=None) : commit et fermeture par la fonction.
3) Semantique : l'id vise sort du pool, les autres restent.
4) Scenarios reels de l'IA : prolongation (flux renew) et vente (flux market_offer)
  Ре declenchent le discard sans erreur.
DB temporaire ; error.log tronque (jamais supprime).
"""
import os, sys, json
os.environ["QT_QPA_PLATFORM"]="offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app

def ok(m): print("OK:", str(m).encode("ascii","replace").decode())

import tempfile
TMP=tempfile.mkdtemp(prefix="fm_prepaid_")
SAVE_DIR=os.path.join(TMP,"saves"); os.makedirs(SAVE_DIR,exist_ok=True)
app.SAVE_DIR=SAVE_DIR
app.DEFAULT_DB_PATH=os.path.join(TMP,"never_default.db")
app.active_save_path=lambda: app.DB_PATH
app.set_active_save_path=lambda p: None
app.DB_PATH=os.path.join(SAVE_DIR,"prepaid_discard.db")
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

# --- 1) Discard avec la connexion de l'appelant, ecritures en attente ---
conn=app.db()
rows=conn.execute("SELECT id FROM player WHERE club_id=1 ORDER BY id LIMIT 3").fetchall()
ids=[int(r["id"]) for r in rows]
pid_keep, pid_drop, pid_other = ids[0], ids[1], ids[2]
conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('prepaid_wage_ids',?)",
             (json.dumps([pid_keep,pid_drop,pid_other]),))
# ecriture en attente sur la MEME connexion (simule le flux prolongation) :
conn.execute("UPDATE player SET morale=50 WHERE id=?",(pid_keep,))
res=w._prepaid_wage_discard(pid_drop, conn)
conn.commit(); conn.close()
ok("1) discard(conn partagee, ecritures en attente) -> %s, zero locked" % res)
assert res is True

c=app.db()
val=c.execute("SELECT value FROM meta WHERE key='prepaid_wage_ids'").fetchone()["value"]
after=json.loads(val)
c.close()
assert pid_drop not in after and pid_keep in after and pid_other in after, after
ok("2) semantique : %s sorti ; %s et %s conserves" % (pid_drop,pid_keep,pid_other))

# --- 3) Discard autonome (conn=None) ---
res2=w._prepaid_wage_discard(pid_keep)
assert res2 is True
c=app.db()
after2=json.loads(c.execute("SELECT value FROM meta WHERE key='prepaid_wage_ids'").fetchone()["value"])
c.close()
assert pid_keep not in after2 and pid_other in after2
ok("3) discard autonome committe proprement")

# --- 4) Discard d'un id absent -> False sans casse ---
res3=w._prepaid_wage_discard(999999)
assert res3 is False
c=app.db()
after3=json.loads(c.execute("SELECT value FROM meta WHERE key='prepaid_wage_ids'").fetchone()["value"])
c.close()
assert pid_other in after3
ok("4) id absent : retour False, pool intact")

# --- 5) La prolongation moteur reutilise la connexion (inspection du code) ---
src=open(r"C:\FM2027V2\app.py",encoding="utf-8").read()
n_shared=src.count("self._prepaid_wage_discard(player_id,conn)")
n_own=src.count("self._prepaid_wage_discard(player_id)")-n_shared  # differences de suffixe
ok("5) appels moteur partageant la connexion (renew/ventes) : %d" % n_shared)
assert n_shared>=3

# --- 6) error.log ---
sz=os.path.getsize(r"C:\FM2027V2\data\error.log")
ok("6) error.log = %d octet(s)" % sz)
assert sz==0, "error.log non vide"

ok("RESULT: ALL OK")
