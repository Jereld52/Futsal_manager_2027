# -*- coding: utf-8 -*-
"""Captures des 14 pages (offscreen 1500x880) pour audit visuel d'homogeneite."""
import os, sys, tempfile
os.environ["QT_QPA_PLATFORM"]="offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app

ROOT=r"C:\FM2027V2"
import random as _r
_r.seed(20260701)
tmp=tempfile.mkdtemp(prefix="fm_audit_"); saves=os.path.join(tmp,"saves"); os.makedirs(saves,exist_ok=True)
app.SAVE_DIR=saves; app.DB_PATH=os.path.join(saves,"audit.db")
identity={"name":"AS AUDIT","arena_name":"Halle Jacques Viot","color1":"#9e2b33","color2":"#123c66",
          "kit_pattern":"vertical","logo_pattern":"shield","database_size":"classic","division":6,"difficulty":"Normal"}
app.init_db(fresh_universe=True, selected_division=6, identity=identity)
try:
    open(os.path.join(ROOT,"data","error.log"),"r+b").truncate(0)
except FileNotFoundError:
    open(os.path.join(ROOT,"data","error.log"),"wb").close()

from PySide6.QtWidgets import QApplication, QDialog
app.QApplication.instance() or app.QApplication([])
# Fidélité : appliquer le THÈME global comme le fait le vrai main() (sinon
# les captures sont décolorées : composants natifs blancs, faux positifs).
app.QApplication.instance().setStyleSheet(app.style_for_theme("Nuit violette"))
def _dexec(self,*a,**k):
    self.show(); app.QApplication.processEvents(); self.accept(); return QDialog.Accepted
app.QDialog.exec=_dexec
w=app.MainWindow(); w.show(); w.resize(1500,880); app.QApplication.processEvents()
w.app_stack.setCurrentWidget(w.game_shell)  # montrer le shell (sinon pages jamais "shown", onglets stale au grab)
# debox le centre de formation pour les deux etats fideles
conn=app.db()
conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('academy_unlocked','1')")
conn.execute("UPDATE facility SET youth_level=3, medical_level=4 WHERE id=1")
conn.commit(); conn.close()

OUT=os.path.join(ROOT,"tests","captures","audit")
os.makedirs(OUT, exist_ok=True)
names=["dashboard","roster","tactics","match","training","facility","messages","mercato","calendar","finances","staff","standings","search","academy"]
for idx,name in enumerate(names):
    try:
        w.show_page(idx); app.QApplication.processEvents()
        if getattr(w,"_ui_ready",False):
            w.refresh_all()
        app.QApplication.processEvents()
        page=w.pages[idx]; page.setFixedSize(1500,880)
        app.QApplication.processEvents()
        page.grab().save(os.path.join(OUT,"page_%02d_%s.png"%(idx,name)))
        print("saved", name)
    except Exception as exc:
        print("FAIL", name, repr(exc)[:120])
try: open(os.path.join(ROOT,"data","error.log"),"r+b").truncate(0)
except FileNotFoundError: pass
print("RESULT: ALL OK")
