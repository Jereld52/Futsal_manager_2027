# -*- coding: utf-8 -*-
"""Affichages : aucun nom interne ni underscore dans les libellés visibles."""
import os, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import (QApplication, QLabel, QPushButton, QCheckBox,
                               QGroupBox, QTabWidget, QTableWidget, QComboBox)

TMP = tempfile.mkdtemp(prefix="fm_labels_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP; app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=3,
            identity={"name": "Label FC", "arena_name": "A", "color1": "#c47220",
                      "color2": "#14171f", "division": 3})

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
w = app.MainWindow(); w.show()
w.show_game_message = lambda *a, **k: True
w.app_stack.setCurrentWidget(w.game_shell); q.processEvents()
w.refresh_all(); q.processEvents()

texts = set()
for cls in (QLabel, QPushButton, QCheckBox, QGroupBox):
    for obj in w.findChildren(cls):
        try: text = obj.text()
        except Exception: continue
        if text: texts.add(str(text).strip())
for obj in w.findChildren(QTabWidget):
    for i in range(obj.count()):
        texts.add(obj.tabText(i).strip())
for obj in w.findChildren(QTableWidget):
    for c in range(obj.columnCount()):
        item = obj.horizontalHeaderItem(c)
        if item and item.text(): texts.add(item.text().strip())
for obj in w.findChildren(QComboBox):
    for i in range(obj.count()): texts.add(obj.itemText(i).strip())

bad_tokens = ("player_history", "finance_tx", "manager_message", "action_data",
              "ENTRANTS_SORTANTS", "club_id", "player_id")
bad = sorted(t for t in texts if "_" in t or any(tok in t for tok in bad_tokens))
assert not bad, bad[:10]
assert "PRÊTS" in {w.mercato_tabs.tabText(i) for i in range(w.mercato_tabs.count())}
assert "ENTRANTS & SORTANTS" not in " ".join(texts)
print("OK libellés :", len(texts), "textes contrôlés, aucun nom interne")
print("RESULT: ALL OK")
