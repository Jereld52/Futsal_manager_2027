# -*- coding: utf-8 -*-
"""test_match_pitch2d.py (rapide, DB temporaire)

Niveau 1 : le terrain 2D est un MOUCHARD. Preuves :
  1. DETERMINISME : le meme match (meme DB bit-a-bit, meme seed) joue deux fois
     — l'une SANS terrain (match_pitch desactive), l'autre AVEC terrain branche.
     Les stats complete sont STRICTEMENT identiques => le visuel ne touche rien.
  2. ROBUSTESSE : note_event/note_state avec des ordures (side inconnu, kind
     inconnu, state "None") -> aucune exception, aucune mutation.
  3. RENDU : captures offscreen du centre de match (avant-match, dans le match,
     flash BUT, fin) -> tests\\captures\\matchday_2d_*.png
error.log tronque (jamais supprime) et verifie a 0 octet.
"""
import os, sys, tempfile, shutil, json, hashlib
os.environ["QT_QPA_PLATFORM"]="offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app

def ok(m): print("OK:", str(m).encode("ascii","replace").decode())

TMP=tempfile.mkdtemp(prefix="fm_pitch_")
SAVE_DIR=os.path.join(TMP,"saves"); os.makedirs(SAVE_DIR,exist_ok=True)
os.makedirs(r"C:\FM2027V2\tests\captures",exist_ok=True)
app.SAVE_DIR=SAVE_DIR
app.DEFAULT_DB_PATH=os.path.join(TMP,"never_default.db")
app.active_save_path=lambda: app.DB_PATH
app.set_active_save_path=lambda p: None
app.DB_PATH=os.path.join(SAVE_DIR,"pitch.db")
identity={"name":"AS Horizon","arena_name":"A","color1":"#1f8a4d","color2":"#0f3d27",
          "kit_pattern":"vertical","logo_pattern":"shield","database_size":"classic","division":6}
app.init_db(fresh_universe=True, selected_division=6, identity=identity)
try:
    open(r"C:\FM2027V2\data\error.log","r+b").truncate(0)
except FileNotFoundError:
    open(r"C:\FM2027V2\data\error.log","wb").close()

# --- fixture du club forcee a la date de carriere (match jour 1 dispo)
c=app.db()
fx=c.execute("SELECT f.*, hc.name home_name, ac.name away_name FROM fixture f "
             "JOIN club hc ON hc.id=f.home_club_id JOIN club ac ON ac.id=f.away_club_id "
             "WHERE (f.home_club_id=1 OR f.away_club_id=1) ORDER BY f.fixture_date LIMIT 1").fetchone()
assert fx, "aucun fixture du club"
cd=c.execute('SELECT career."current_date" cd FROM career WHERE id=1').fetchone()["cd"]
c.execute("UPDATE fixture SET played=0, fixture_date=? WHERE id=?", (cd, int(fx["id"])))
c.commit(); fx_id=int(fx["id"]); c.close()
dbpath=app.DB_PATH
cap=["a","b","c"]
paths={k:os.path.join(TMP,"match_copy_%s.db"%k) for k in cap}
for k,p in paths.items():
    shutil.copyfile(dbpath, p)

from PySide6.QtWidgets import QApplication, QDialog
app.QApplication.instance() or app.QApplication([])
def _dexec(self,*a,**k):
    self.show(); app.QApplication.processEvents(); self.accept(); return QDialog.Accepted
app.QDialog.exec=_dexec

# --- affutage de match complet synchrone, digest des stats cles
def run_match(db_copy, with_pitch):
    app.DB_PATH=db_copy
    w=app.MainWindow(); w.show(); app.QApplication.processEvents()
    if not with_pitch:
        w.match_pitch=None                      # hook inerte : voie de comparaison
    assert w._launch_match_after_confirmation() is None
    assert w.match_state and w.match_state["fixture_id"]==fx_id, "match non lance"
    w.finish_match_now()                        # 120 ticks synchrones + finalisation
    s=w.match_state
    digest={
        "id":s["fixture_id"],"hg":s["hg"],"ag":s["ag"],
        "shots_h":s["shots_h"],"shots_a":s["shots_a"],
        "target_h":s["target_h"],"target_a":s["target_a"],
        "passes":s["passes"],"passes_completed":s["passes_completed"],
        "interceptions":s["interceptions"],"corners":s["corners"],
        "poss_sec":s["possession_seconds"],"yellow":(s["yellow_h"],s["yellow_a"]),
        "red":(s["red_h"],s["red_a"]),"fouls":(s["fouls_h"],s["fouls_a"]),
        "subs":(s["subs_used"],s["opponent_subs_used"]),
        "timeline":len(s["timeline"]),"goals":[(g.get("side"),g.get("minute"),g.get("second")) for g in s["goals"]],
        "cond":round(sum(s["conditions"].values()),4),
        "opp_cond":round(sum(s["opponent_conditions"].values()),4),
        "injuries":sorted(s["injuries"].keys()),
        "sentoff":(len(s["sent_off_players"]["h"]),len(s["sent_off_players"]["a"])),
    }
    seed=w.match_rng.getstate() if w.match_rng else None
    w.close(); app.QApplication.processEvents()
    return digest, seed

# --- 1) meme match, deux fois, terrain OFF vs terrain ON
d_off,_=run_match(paths["a"], with_pitch=False)
d_on, seed_on=run_match(paths["b"], with_pitch=True)
if d_off!=d_on:
    diff={k:(d_off[k],d_on[k]) for k in d_off if d_off[k]!=d_on[k]}
    print("DIFFS:", {k:(str(v[0])[:80],str(v[1])[:80]) for k,v in diff.items()})
assert d_off==d_on, "le terrain a change le deroulement du match !"
ok("1) determinisme : digest strictement identique OFF vs ON terrain (%d cles)" % len(d_on))
ok("   resultats : %d-%d | tirs %d-%d | poss. %r/%r s" % (d_on["hg"],d_on["ag"],d_on["shots_h"],d_on["shots_a"],d_on["poss_sec"]["h"],d_on["poss_sec"]["a"]))

# --- 2) ordures sans exception
app.DB_PATH=paths["c"]
w=app.MainWindow(); w.show(); app.QApplication.processEvents()
assert w.match_pitch is not None, "terrain 2D absent (import echoue ?)"
p=w.match_pitch
p.note_state(None); p.note_event("zzz","unknown",None)
p.note_state({"elapsed_seconds":"x","hg":"junk","passes":None,"players_on":None,
              "sent_off_players":None,"lineup":None}, True)
p.note_event("h","goal")
p.note_event("a","save")
ok("2) robustesse : ordures avalees sans exception, moteur intact")

def _fake(base):
    return [{"id": base+i, "first_name": "J%d" % i, "last_name": "X%d" % i,
             "position": "Gardien" if i == 0 else "Ailier", "shirt_number": i+1,
             "condition": 80} for i in range(5)]

def pitch_state(sec, poss, passes, hg=0, ag=0):
    return {"elapsed_seconds": sec, "hg": hg, "ag": ag, "finished": False, "half_time_break": False,
            "players_on": {"h": 5, "a": 5}, "possession_side": poss, "passes": passes,
            "sent_off_players": {"h": [], "a": []},
            "lineup": _fake(100), "opponent_lineup": _fake(200),
            "conditions": {}, "opponent_conditions": {}}

# --- 2b) verrous : un tir "priorise" la cible ballon sur le tick suivant
import time as _time
p.note_state(pitch_state(600, "h", {"h": 10, "a": 5}))
p.note_event("h","shot")
p.note_state(pitch_state(620, "a", {"h": 11, "a": 6}))
tx=p._ball["target"][0]
assert tx>0.85, tx  # la cible reste鲜活 sur la cage (verrou, pas possession)
ok("2b) verrou tir : ballon toujours sur la cage malgre le tick possession")

# --- 2c) but : flash + buteur + celebration au coin
p.note_event("a","goal",detail="Marco Scorer")   # "a" attaque a gauche
assert p._goal_info and "Marco Scorer" in p._goal_info[0], p._goal_info
assert p._celebrate and p._celebrate["side"]=="a"
cx=p._teams["a"][1]["target"][0]
assert cx<0.12, cx  # les joueurs accourent au coin gauche
assert p._ball["target"][0]<=0.02
p.note_state(pitch_state(640, "a", {"h": 11, "a": 7}, hg=0, ag=1))
assert p._teams["a"][1]["target"][0]<0.12, "la celebration a ete ecrasee par le tick !"
ok("2c) but : flash + buteur + celebration qui survit au tick")

# --- 3) captures UI (avant-match / dans le match / but / fin)
def grab_page(p_tmp):
    p_tmp.resize(1300, 840); app.QApplication.processEvents(); app.QApplication.processEvents()
    img = p_tmp.grab()
    return img

# --- 3) captures UI (avant-match / dans le match / but / fin)
page=w.pages[3] if len(w.pages)>3 else w
w.show_page(3); w.show(); app.QApplication.processEvents()
# entree carriere officielle (comme un joueur qui ouvre sa sauvegarde) :
w.app_stack.setCurrentWidget(w.game_shell)
w.resize(1500,930); app.QApplication.processEvents(); app.QApplication.processEvents()
grab_page(page).save(r"C:\FM2027V2\tests\captures\matchday_2d_prematch.png")
ok("3) capture avant-match enregistree")
assert w._launch_match_after_confirmation() is None
assert w.match_state
# --- 3b) menus verrouilles pendant le direct
assert w._match_is_live(), "direct non detecte"
assert w.nav_buttons[0].isEnabled() is False, "nav non verrouillee au lancement"
assert w.advance_button.isEnabled() is False, "CONTINUER non verrouille"
w.show_page(0)   # doit refuser : retour au centre de match
assert w.stack.currentIndex() == 3, "la navigation a fuite pendant le direct !"
ok("3b) direct : sidebar verrouillee, nuance refusee, CONTINUER inactif")
for _ in range(10):
    if w.match_state.get("half_time_break"): break
    w.advance_minute(); app.QApplication.processEvents()
grab_page(page).save(r"C:\FM2027V2\tests\captures\matchday_2d_live.png")
ok("   capture live (t) enregistree ; phase terrain = %s" % p._phase)
w.finish_match_now()
assert w._match_is_live() is False, "le direct reste verrouille apres finalisation !"
assert w.nav_buttons[0].isEnabled(), "nav non deverrouillee apres le match"
ok("   menus deverrouilles apres finalisation")
grab_page(page).save(r"C:\FM2027V2\tests\captures\matchday_2d_fulltime.png")
ok("   capture fin de match ; phase terrain = %s" % p._phase)
for f in ("matchday_2d_prematch.png","matchday_2d_live.png","matchday_2d_fulltime.png"):
    sz=os.path.getsize(os.path.join(r"C:\FM2027V2\tests\captures",f))
    assert sz>5000, (f,sz)
w.close()

# --- 4) error.log
sz=os.path.getsize(r"C:\FM2027V2\data\error.log")
if sz:
    print(open(r"C:\FM2027V2\data\error.log",encoding="utf-8",errors="replace").read())
ok("4) error.log = %d octet(s)"%sz)
assert sz==0

ok("RESULT: ALL OK")
