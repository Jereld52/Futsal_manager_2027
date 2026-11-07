# -*- coding: utf-8 -*-
"""Centre de match : le signal des consignes n'est connecté qu'une fois et
ne déclenche aucun avertissement de déconnexion."""
import os, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication

TMP = tempfile.mkdtemp(prefix="fm_livesig_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP; app.BASE_DIR = TMP
app.OPTIONS_FILE = os.path.join(TMP, "options.json")
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=3,
            identity={"name": "Signal FC", "arena_name": "A", "color1": "#c47220",
                      "color2": "#14171f", "division": 3})

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
w = app.MainWindow(); w.show(); w.show_game_message = lambda *a, **k: True
player = {"id": 1, "first_name": "Test", "last_name": "Joueur", "position": "Pivot",
          "shirt_number": 7, "condition": 80}
w.match_state = {"home": "Signal FC", "away": "Adversaire", "is_home": True,
                 "lineup": [player], "bench": [], "opponent_lineup": [], "opponent_bench": [],
                 "conditions": {1: 80}, "opponent_conditions": {}, "individual_instructions": {}}
for _ in range(4):
    w._update_live_match_widgets()
lw = w.live_team_lists["own"]
assert getattr(lw, "_instruction_handler_connected", False)
assert hasattr(w, "_on_live_team_item_clicked")
print("RESULT: ALL OK")
