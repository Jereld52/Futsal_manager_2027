# -*- coding: utf-8 -*-
"""Tactiques : terrain large horizontal, tuiles lisibles et banc enrichi."""
import os, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

TMP = tempfile.mkdtemp(prefix="fm_tactics_layout_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP; app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=3,
            identity={"name": "Tactics FC", "arena_name": "A", "color1": "#1f8a4d",
                      "color2": "#0f3d27", "division": 3})

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
w = app.MainWindow(); w.resize(1920, 900); w.show()
w.show_game_message = lambda *a, **k: True
w.app_stack.setCurrentWidget(w.game_shell); q.processEvents()
w.show_page(2); q.processEvents()
w.auto_pick_lineup(); q.processEvents()
w.refresh_tactical_bench(); w.update_formation_layout(); q.processEvents()

# 1) Le splitter occupe toute la largeur de la page (plus de vide a droite).
page = w.stack.currentWidget()
assert w.tactics_splitter.width() >= page.width() - 6, (w.tactics_splitter.width(), page.width())
assert w.tactics_splitter.orientation() == Qt.Horizontal

# 2) Terrain horizontal large et tuiles lisibles.
court = w.pitch.court_rect()
assert not w.pitch.vertical
assert court.width() > court.height() * 1.5, (court.width(), court.height())
assert w.pitch.width() >= 900, w.pitch.width()
widths = [z.width() for z in w.pitch_zones.values()]
assert min(widths) >= 130, widths
# Tuiles raccourcies : assez basses pour ne jamais se superposer, assez hautes pour le contenu.
assert all(44 <= z.height() <= 78 for z in w.pitch_zones.values()), [z.height() for z in w.pitch_zones.values()]
zones = list(w.pitch_zones.values())
for i in range(len(zones)):
    for j in range(i + 1, len(zones)):
        assert not zones[i].geometry().intersects(zones[j].geometry()), \
            (zones[i].position_label, zones[j].position_label)
filled = [z for z in w.pitch_zones.values() if z.player_stats]
assert filled and "TEC" in filled[0].player_stats and "FIN" in filled[0].player_stats
print("OK terrain", w.pitch.width(), "x", w.pitch.height(), "| tuiles", widths[0])

# 3) Banc large et fiches enrichies.
assert w.tactic_bench.width() >= 440, w.tactic_bench.width()
item = next((w.tactic_bench.item(i) for i in range(w.tactic_bench.count())
             if w.tactic_bench.item(i).data(Qt.UserRole+2)), None)
assert item is not None
data = item.data(Qt.UserRole+2)
for key in ("TEC", "PAS", "FIN", "DÉF", "END", "MOR"):
    assert key in data.get("stats", ""), (key, data.get("stats"))
assert item.sizeHint().height() >= 70, item.sizeHint().height()
print("OK banc", w.tactic_bench.width(), "px |", data["stats"])

# 4) Responsive : passage en colonne sur fenetre etroite, terrain toujours horizontal.
w.resize(1000, 700); q.processEvents(); w.fit_tactics_layout(); q.processEvents()
assert w.tactics_splitter.orientation() == Qt.Vertical
assert not w.pitch.vertical
court = w.pitch.court_rect()
assert court.width() > court.height() * 1.5
zones = list(w.pitch_zones.values())
for i in range(len(zones)):
    for j in range(i + 1, len(zones)):
        assert not zones[i].geometry().intersects(zones[j].geometry()), \
            ("etroit", zones[i].position_label, zones[j].position_label)
print("OK responsive : colonne etroite, terrain horizontal, aucune tuile superposee")
print("RESULT: ALL OK")
