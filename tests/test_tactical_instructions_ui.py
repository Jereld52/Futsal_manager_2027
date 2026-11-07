# -*- coding: utf-8 -*-
"""Consignes tactiques : dialogue lisible, aperçu de schéma et sauvegarde."""
import os, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication, QTabWidget, QComboBox

TMP = tempfile.mkdtemp(prefix="fm_tactical_ui_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP; app.BASE_DIR = TMP
app.OPTIONS_FILE = os.path.join(TMP, "options.json")
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=3,
            identity={"name": "Tactique FC", "arena_name": "Halle", "color1": "#c47220",
                      "color2": "#14171f", "division": 3})

conn = app.db()
conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('tactics_familiarity','72')")
conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('setpiece_corner','Poteau')")
conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('setpiece_freekick','Direct')")
conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('setpiece_exit','Court')")
conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('powerplay','Automatique')")
conn.commit(); conn.close()

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
app.MainWindow.show_game_message = lambda self, *a, **k: True
w = app.MainWindow(); w.resize(1360, 900); w.show()
w.app_stack.setCurrentWidget(w.game_shell); q.processEvents()
w.show_page(2); q.processEvents()

dlg = w._build_tactical_instructions_dialog()
assert dlg is not None
tabs = dlg.findChild(QTabWidget)
assert tabs is not None and tabs.count() == 2, tabs.count() if tabs else None
assert [tabs.tabText(i) for i in range(tabs.count())] == ["LE CINQ", "COUPS DE PIED"]

board = dlg.findChild(app.SetPieceBoard)
assert board is not None
assert board.kind == "corner" and board.variant == "Poteau", (board.kind, board.variant)

combos = dlg.findChildren(QComboBox)
role_combos = [cb for cb in combos if cb.findData("Fixo") >= 0 and cb.findData("Universel") >= 0]
assert role_combos, "combo de rôle absent"
target = next((cb for cb in role_combos if cb.currentData() != "Fixo"), role_combos[0])
target.setCurrentIndex(target.findData("Fixo")); q.processEvents()
c = app.db(); row = c.execute("SELECT COUNT(*) n FROM tactical_instruction WHERE role='Fixo'").fetchone(); c.close()
assert int(row["n"] or 0) >= 1

kick = next((cb for cb in combos if cb.findData("Combiné") >= 0), None)
assert kick is not None
kick.setCurrentIndex(kick.findData("Combiné")); q.processEvents()
assert board.kind == "freekick" and board.variant == "Combiné", (board.kind, board.variant)
c = app.db(); row = c.execute("SELECT value FROM meta WHERE key='setpiece_freekick'").fetchone(); c.close()
assert row and row["value"] == "Combiné", row["value"] if row else None

assert any("FAMILIARITÉ DU PLAN" == lbl.text() for lbl in dlg.findChildren(app.QLabel))
print("OK consignes :", tabs.count(), "onglets •", len(role_combos), "cartes de rôle • aperçu", board.kind, board.variant)
print("RESULT: ALL OK")
