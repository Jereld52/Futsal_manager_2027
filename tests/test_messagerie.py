# -*- coding: utf-8 -*-
"""test_messagerie.py (rapide, DB temporaire)
Options de messagerie :
  1. brief Hebdomadaire (defaut) : lundi -> news+club_news ; autres jours -> rien
  2. brief Quotidien : genere aussi un autre jour (nouveau declencheur)
  3. categories filtrees : club silencieux quand tout est off
  4. anniversaires ecores (defaut OFF) : age applique, zero message ; ON -> messages
error.log tronque (jamais supprime) et verifie a 0 octet.
"""
import os, sys, tempfile
os.environ["QT_QPA_PLATFORM"]="offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app

def ok(m): print("OK:", str(m).encode("ascii","replace").decode())

TMP=tempfile.mkdtemp(prefix="fm_msg_")
SAVE_DIR=os.path.join(TMP,"saves"); os.makedirs(SAVE_DIR,exist_ok=True)
app.SAVE_DIR=SAVE_DIR
app.DEFAULT_DB_PATH=os.path.join(TMP,"never_default.db")
app.active_save_path=lambda: app.DB_PATH
app.set_active_save_path=lambda p: None
app.DB_PATH=os.path.join(SAVE_DIR,"msg.db")
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

w.game_options={"brief_cadence":"Hebdomadaire","msg_anniversaire":False,"msg_perf":True,
                "msg_blessure":True,"msg_staff":False,"msg_transfert":True,"msg_contrat":True}

# Contrats uniformes : evite qu'un joueur deja en fin de contrat (aleatoire a
# la generation) monopolise les trois places du brief et masque le declencheur.
_c=app.db(); _c.execute("UPDATE player SET contract_years=2 WHERE club_id=1 AND COALESCE(is_free_agent,0)=0"); _c.commit(); _c.close()

def counts():
    c=app.db()
    n=c.execute("SELECT COUNT(*) n FROM manager_message WHERE kind='club_news'").fetchone()["n"]
    news=[r["title"] for r in c.execute("SELECT title FROM news WHERE title LIKE 'Brief % du club'").fetchall()]
    c.close(); return n, news
def prefix():  # nombre de club_news generes par le test (hors init)
    c=app.db()
    n=c.execute("SELECT COUNT(*) n FROM manager_message WHERE kind='club_news' AND created_date>='2026-07-06'").fetchone()["n"]
    c.close(); return n
def player(nth, unique_name=None):
    c=app.db()
    # Choisit un joueur encore sous contrat long : un joueur deja en fin de
    # contrat aurait pu etre cite dans le brief precedent (dedup par nom).
    r=c.execute("SELECT id FROM player WHERE club_id=1 AND contract_years>1 ORDER BY id LIMIT ? OFFSET ?",(1,nth)).fetchone()
    if not r:
        r=c.execute("SELECT id FROM player WHERE club_id=1 ORDER BY id LIMIT ? OFFSET ?",(1,nth)).fetchone()
    pid=int(r["id"])
    if unique_name:
        # noms d'univers aleatoires : deux joueurs peuvent porter le meme nom -> le
        # dedoublonnage du brief (LIKE sur le nom) rendrait le test fluctuant.
        c.execute("UPDATE player SET first_name=? WHERE id=?",(unique_name,pid))
    c.execute("UPDATE player SET contract_years=1, injury_days=0 WHERE id=?",(pid,))
    c.commit(); c.close()
    return pid

# --- declencheur : joueur 1 en fin de contrat ; lundi 2026-07-06
pid1=player(0)
cc=app.db(); w.generate_live_club_messages(cc,"2026-07-06"); cc.commit(); cc.close()
n_hebdo,news_hebdo=counts()
assert prefix()>=1, "aucun brief cree le lundi"
assert any("hebdomadaire" in t for t in news_hebdo), news_hebdo
ok("1) hebdo lundi : brief %s publie (news+messagerie)" % ("hebdomadaire du club" if news_hebdo else "?"))

# --- mercredi (hebdo) : rien de nouveau, dedup + cadence
base=prefix()
cc=app.db(); w.generate_live_club_messages(cc,"2026-07-08"); cc.commit(); cc.close()
assert prefix()==base
ok("1b) hebdo : aucun brief hors lundi")

# --- 2) quotidien : jeudi avec un NOUVEAU declencheur (joueur 2)
pid2=player(1, unique_name="Bruno")
w.game_options["brief_cadence"]="Quotidien"
cc=app.db(); w.generate_live_club_messages(cc,"2026-07-09"); cc.commit(); cc.close()
assert prefix()>base, "le mode quotidien n'a rien produit un jeudi"
c=app.db()
t=c.execute("SELECT title FROM news ORDER BY id DESC LIMIT 1").fetchone()["title"]; c.close()
assert "quotidien" in t, t
ok("2) quotidien : brief aussi ailleurs que lundi ; titre : %s" % t)

# --- 3) tout off : aucun contenu
base=prefix()
w.game_options.update({"msg_perf":False,"msg_blessure":False,"msg_staff":False,
                       "msg_transfert":False,"msg_contrat":False,
                       "brief_cadence":"Quotidien"})
pid3=player(2, unique_name="Calixte")
cc=app.db(); w.generate_live_club_messages(cc,"2026-07-10"); cc.commit(); cc.close()
assert prefix()==base, "des topics sont passes alors que tout est desactive"
ok("3) tout OFF : le club reste silencieux")

# --- 4) anniversaires : vieillissement sans message (OFF), messages si ON
w.game_options.update({"msg_anniversaire":False,"msg_contrat":True})
c=app.db()
row=c.execute("SELECT id,age FROM player WHERE club_id=1 LIMIT 1").fetchone()
c.execute("UPDATE player SET birth_date=? WHERE id=?",("2026-07-30",int(row["id"])))
c.commit(); c.close()
cc=app.db(); w.process_player_birthdays(cc,"2026-07-30"); cc.commit(); cc.close()
c=app.db()
age_after=int(c.execute("SELECT age FROM player WHERE id=?",(int(row["id"]),)).fetchone()["age"])
nb=c.execute("SELECT COUNT(*) n FROM manager_message WHERE title='Anniversaire joueur'").fetchone()["n"]
c.close()
assert age_after==int(row["age"])+1, (row["age"],age_after)
assert nb==0, nb
w.game_options["msg_anniversaire"]=True
cc=app.db(); w.process_player_birthdays(cc,"2026-07-30"); cc.commit(); cc.close()
c=app.db(); nb2=c.execute("SELECT COUNT(*) n FROM manager_message WHERE title='Anniversaire joueur'").fetchone()["n"]; c.close()
assert nb2>=1, nb2
ok("4) anniversaires : age +1 sans message (OFF) ; messages (ON) quand active")

# --- 5) error.log
sz=os.path.getsize(r"C:\FM2027V2\data\error.log")
ok("5) error.log = %d octet(s)"%sz)
assert sz==0

ok("RESULT: ALL OK")
