# -*- coding: utf-8 -*-
"""test_ui_start_render.py : capture offscreen de l'ecran de demarrage et du
dialogue de creation de club apres le relooking (logo au-dessus du menu,
apercu a proportions fixes). DB temporaire, error.log tronque."""
import os, sys, tempfile
os.environ["QT_QPA_PLATFORM"]="offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
import ui_components

TMP=tempfile.mkdtemp(prefix="fm_ui_")
SAVE_DIR=os.path.join(TMP,"saves"); os.makedirs(SAVE_DIR,exist_ok=True)
app.SAVE_DIR=SAVE_DIR
app.DEFAULT_DB_PATH=os.path.join(TMP,"never_default.db")
app.active_save_path=lambda: app.DB_PATH
app.set_active_save_path=lambda p: None
app.DB_PATH=os.path.join(SAVE_DIR,"ui.db")
try:
    open(r"C:\FM2027V2\data\error.log","r+b").truncate(0)
except FileNotFoundError:
    open(r"C:\FM2027V2\data\error.log","wb").close()

from PySide6.QtWidgets import QApplication, QDialog
qapp=app.QApplication.instance() or app.QApplication([])
identity={"name":"AS Horizon","arena_name":"A","color1":"#1f8a4d","color2":"#0f3d27",
          "kit_pattern":"vertical","logo_pattern":"shield","database_size":"classic","division":6}
app.init_db(fresh_universe=True, selected_division=6, identity=identity)

# 1) Ecran de demarrage (sans carriere : la page vit sans DB complete)
w=app.MainWindow(); w.resize(1280,800); w.show(); qapp.processEvents()
w.app_stack.setCurrentWidget(w.start_screen); qapp.processEvents()
pm1=w.start_screen.grab()
OUT=r"C:\FM2027V2\tests"
pm1.save(os.path.join(OUT,"ui_start.png"))
print("capture ecran de demarrage -> ui_start.png")

# 2) Dialogue de creation de club
dlg=ui_components.ClubSetupDialog(w, app.LEAGUE_DEFINITIONS, app.facility_capacity)
dlg.resize(1040,720); dlg.show(); qapp.processEvents()
dlg.grab().save(os.path.join(OUT,"ui_setup.png"))
print("capture creation de club -> ui_setup.png")
pv=dlg.preview
print("preview geometry:", pv.geometry(), "| parent visible:", pv.isVisible(),
      "| sizeHint:", pv.sizeHint(), "| minH:", pv.minimumHeight())

# Le logo charge est bien logo2.png ?
p=app.start_logo_pixmap(520)
print("pixmap logo:", "OK" if (p is not None and not p.isNull()) else "ECHEC",
      "| source attendue data/logo1.png")
w.close(); qapp.processEvents()
sz=os.path.getsize(r"C:\FM2027V2\data\error.log")
print("error.log =", sz, "octet(s)")
