# -*- coding: utf-8 -*-
"""Infrastructure > Gestion : cartes compactes, pas de défilement en grand écran."""
import os, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication, QScrollArea

TMP = tempfile.mkdtemp(prefix="fm_facfit_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP; app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=3,
            identity={"name": "Infra FC", "arena_name": "H", "color1": "#c47220",
                      "color2": "#14171f", "division": 3})

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
w = app.MainWindow(); w.resize(1560, 900); w.show()
w.show_game_message = lambda *a, **k: True
w.app_stack.setCurrentWidget(w.game_shell); q.processEvents()
w.show_page(5); q.processEvents()
w.facility_tabs.setCurrentIndex(1); q.processEvents()

page = w.facility_tabs.currentWidget()
scroll = page.findChild(QScrollArea)
assert scroll is not None
assert scroll.verticalScrollBar().maximum() == 0, scroll.verticalScrollBar().maximum()
assert w._fac_grid_cols == 3, w._fac_grid_cols

# Les cartes ont une hauteur compacte et trois colonnes distinctes.
cards = [w.facility_buildings_grid.itemAt(i).widget()
         for i in range(w.facility_buildings_grid.count())]
assert cards and all(100 <= c.height() <= 132 for c in cards), [c.height() for c in cards]
cols = {(w.facility_buildings_grid.getItemPosition(i)[1])
        for i in range(w.facility_buildings_grid.count())}
assert len(cols) == 3, cols
print("OK gestion 1560 : aucune barre de défilement,", len(cards), "cartes, 3 colonnes")

# En fenêtre plus étroite on repasse à 2 colonnes lisibles.
w.resize(1360, 900); q.processEvents(); w._fit_facility_layout(); q.processEvents()
assert w._fac_grid_cols == 2, w._fac_grid_cols
print("OK gestion 1360 : bascule en 2 colonnes")
print("RESULT: ALL OK")
