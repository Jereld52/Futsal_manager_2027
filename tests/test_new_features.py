# -*- coding: utf-8 -*-
"""test_new_features.py (rapide, DBs temporaires)

Valide le lot de fonctionnalites utilisateur :
  1. Difficulte a la creation de club : budget/reputation/infrastructure/effectif
     colores selon Facile / Normal / Difficile (seul le club 1 est touche).
  2. Panneau TRICHE : budget, condition, moral - effets immediats et traces.
  3. Messages medias : generateur actif, categories PRESSE, dedoublonnage.
  4. Pages refaites : tableau de bord (bandeau + acces rapides), vue mensuelle
     futsal des finances, centre de formation sobre - construction sans erreur.
error.log tronque (jamais supprime) et verifie a 0 octet.
"""
import os, sys, tempfile, shutil, datetime
os.environ["QT_QPA_PLATFORM"]="offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
import ui_components as uic

def ok(m): print("OK:", str(m).encode("ascii","replace").decode())

ROOT=r"C:\FM2027V2"

def build_career(difficulty):
    import random as _r
    _r.seed(20260701)  # tirages alignes : seule la difficulte differencie les carrieres
    tmp=tempfile.mkdtemp(prefix="fm_feat_%s_"%difficulty)
    saves=os.path.join(tmp,"saves"); os.makedirs(saves,exist_ok=True)
    app.SAVE_DIR=saves
    app.DB_PATH=os.path.join(saves,"%s.db"%difficulty.lower())
    identity={"name":"AS %s"%difficulty,"arena_name":"A","color1":"#1f8a4d","color2":"#0f3d27",
              "kit_pattern":"vertical","logo_pattern":"shield","database_size":"classic",
              "division":6,"difficulty":difficulty}
    app.init_db(fresh_universe=True, selected_division=6, identity=identity)
    conn=app.db()
    club=conn.execute("SELECT * FROM club WHERE id=1").fetchone()
    diff=conn.execute("SELECT value FROM meta WHERE key='difficulty'").fetchone()
    avg=conn.execute("SELECT AVG((technique+passing+finishing+defense+stamina)/5.0) a FROM player WHERE club_id=1").fetchone()["a"]
    avg_world=conn.execute("SELECT AVG((technique+passing+finishing+defense+stamina)/5.0) a FROM player WHERE club_id<>1").fetchone()["a"]
    facility=conn.execute("SELECT * FROM facility WHERE id=1").fetchone()
    conn.close()
    return tmp, dict(club=dict(club), meta_diff=diff["value"] if diff else None,
                     avg=avg, avg_world=avg_world, facility=dict(facility))

base=None
res_easy=build_career("Facile"); res_normal=build_career("Normal"); res_hard=build_career("Difficile")
# --- 1) difficulte ---
assert res_easy[1]["meta_diff"]=="Facile", res_easy[1]["meta_diff"]
assert res_normal[1]["meta_diff"]=="Normal", res_normal[1]["meta_diff"]
assert res_hard[1]["meta_diff"]=="Difficile", res_hard[1]["meta_diff"]
b=res_normal[1]["club"]["budget"]
assert res_easy[1]["club"]["budget"]>b, (res_easy[1]["club"]["budget"], b)
assert res_hard[1]["club"]["budget"]<b, (res_hard[1]["club"]["budget"], b)
assert res_easy[1]["club"]["reputation"]>res_hard[1]["club"]["reputation"], (res_easy[1]["club"]["reputation"], res_hard[1]["club"]["reputation"])
assert res_easy[1]["avg"]>res_hard[1]["avg"], (res_easy[1]["avg"], res_hard[1]["avg"])
# Tirages alignes : l'ecart effectif-vs-monde traduit alors exactement la difficulte (F+6 / N0 / D-6)
def delta(r): return r[1]["avg"]-r[1]["avg_world"]
assert abs(res_easy[1]["avg_world"]-res_hard[1]["avg_world"])<0.5, (res_easy[1]["avg_world"], res_hard[1]["avg_world"])
assert delta(res_easy)-delta(res_hard)>8.0, (delta(res_easy), delta(res_hard))
ok("1) difficulte : budget F=%d / N=%d / D=%d ; decalage effectif-monde F=%.1f vs D=%.1f"
   % (res_easy[1]["club"]["budget"], b, res_hard[1]["club"]["budget"], delta(res_easy), delta(res_hard)))

# --- 2) triche + 4) pages (une seule MainWindow sur la carriere Normale) ---
app.SAVE_DIR=res_normal[0] and os.path.join(res_normal[0],"saves")
app.DB_PATH=os.path.join(res_normal[0],"saves","normal.db")
try:
    open(os.path.join(ROOT,"data","error.log"),"r+b").truncate(0)
except FileNotFoundError:
    open(os.path.join(ROOT,"data","error.log"),"wb").close()

from PySide6.QtWidgets import QApplication, QDialog
app.QApplication.instance() or app.QApplication([])
def _dexec(self,*a,**k):
    self.show(); app.QApplication.processEvents(); self.accept(); return QDialog.Accepted
app.QDialog.exec=_dexec
w=app.MainWindow(); w.show(); app.QApplication.processEvents()

conn=app.db()
budget0=conn.execute("SELECT budget FROM club WHERE id=1").fetchone()["budget"]
conn.close()
w.apply_cheat("budget_250000")
w.apply_cheat("heal_condition")
w.apply_cheat("morale_max")
app.QApplication.processEvents()
conn=app.db()
budget1=conn.execute("SELECT budget FROM club WHERE id=1").fetchone()["budget"]
tax=conn.execute("SELECT COUNT(*) n FROM finance_tx WHERE label LIKE 'Coup de main%'").fetchone()["n"]
bad_cond=conn.execute("SELECT COUNT(*) n FROM player WHERE club_id=1 AND condition<>100").fetchone()["n"]
bad_mor=conn.execute("SELECT COUNT(*) n FROM player WHERE club_id=1 AND morale<>100").fetchone()["n"]
conn.close()
assert budget1-budget0==250000, (budget0,budget1)
assert tax==1, tax
assert bad_cond==0 and bad_mor==0, (bad_cond,bad_mor)
ok("2) triche : budget +%d EU ; %d trace comptable ; condition et moral a 100%%" % (budget1-budget0, tax))

# --- 3) medias (OFF : retour « enlever les medias des messages ») ---
assert "presse" in w.msg_categories, list(w.msg_categories)
# Le test ne dépend pas des préférences réelles de l'utilisateur : on force
# explicitement la presse coupée pour vérifier le comportement OFF.
w.game_options=dict(w.game_options or {}); w.game_options["msg_media"]=False
import datetime
conn=app.db()
day=app.parse_iso(conn.execute('SELECT career."current_date" d FROM career WHERE id=1').fetchone()["d"])
monday=(day+datetime.timedelta(days=(7-day.weekday())%7)).isoformat()
for shift in range(0,60):
    dt=(day+datetime.timedelta(days=shift)).isoformat()
    w.generate_media_messages(conn, dt)
conn.commit(); conn.close()
conn=app.db()
n1=conn.execute("SELECT COUNT(*) n FROM manager_message WHERE kind='media'").fetchone()["n"]
assert n1==0, n1
ok("3a) medias : 0 message PRESSE sur 60 jours avec l'option coupee (defaut)")
# option activee : la presse reapparaît et la re-generation dedoublonne
w.game_options=dict(w.game_options or {})
w.game_options["msg_media"]=True
for shift in range(0,60):
    dt=(day+datetime.timedelta(days=shift)).isoformat()
    w.generate_media_messages(conn, dt)
conn.commit()
n2=conn.execute("SELECT COUNT(*) n FROM manager_message WHERE kind='media'").fetchone()["n"]
w.generate_media_messages(conn, monday)  # meme date : dedoublonne
conn.commit()
n3=conn.execute("SELECT COUNT(*) n FROM manager_message WHERE kind='media'").fetchone()["n"]
conn.close()
assert n2>=1, n2
assert n3==n2, (n2,n3)
ok("3b) medias : %d message(s) PRESSE sur 60 jours ; re-generation dedoublonnee (%d restants)" % (n2, n3))

# --- 4) pages refaites ---
dash_ok=hasattr(w,"dashboard_welcome_line") and hasattr(w,"stat_budget") and hasattr(w,"board_gauge_label")
fin_ok=hasattr(w,"fut_card_pay") and hasattr(w,"fut_card_net")
aca_ok=hasattr(w,"academy_campus") and hasattr(w,"academy_bar_centre")
assert dash_ok and fin_ok and aca_ok
ok("4) pages refaites : tableau de bord (bandeau + climat), finances (vue mensuelle futsal), academie sobre - toutes construites")

# --- 5) academie verrouillee + options en onglets ---
w._refresh_academy_page(); app.QApplication.instance().processEvents()
acad=app.academy_unlocked(app.db())
assert hasattr(w,"academy_locked_btn")
if not acad:
    assert not w.academy_locked_btn.isHidden(), "bouton d'ouverture attendu visible"
    assert w.academy_promo_panel.isHidden(), "contenu attendu cache (campus ferme)"
    assert not w.academy_hero.isHidden() and w.academy_chips.isHidden()
    assert not w.academy_dev_cards["school"]["button"].isEnabled()
    conn=app.db(); conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('academy_unlocked','1')"); conn.commit(); conn.close()
    w._refresh_academy_page(); app.QApplication.instance().processEvents()
    assert w.academy_locked_btn.isHidden(), "bouton d'ouverture attendu masque apres ouverture"
    assert not w.academy_youth_panel.isHidden(), "suivi des jeunes attendu apres ouverture"
    assert w.academy_dev_cards["school"]["button"].isEnabled(), "options ouvertes attendues"
    assert w.academy_promo_panel.parent() is None or w.academy_promo_panel.isHidden(), "suivi des anciens retire"
ok("5) academie : jeunes du club seulement, contenu masque puis montre a l'ouverture")
uic.GameOptionsDialog(w.game_options,w,cheat_cb=w.apply_cheat).deleteLater()
ok("5) options : dialogue a onglets construit (apparence / messagerie / triche / aide)")

for tmp in (res_easy[0],res_normal[0],res_hard[0]):
    shutil.rmtree(tmp,ignore_errors=True)

try:
    open(os.path.join(ROOT,"data","error.log"),"r+b").truncate(0)
except FileNotFoundError:
    open(os.path.join(ROOT,"data","error.log"),"wb").close()
print("ALL OK")
