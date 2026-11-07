# -*- coding: utf-8 -*-
"""Marché : tableau pleine largeur, colonnes masquables et redimensionnables."""
import os, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication, QHeaderView

TMP = tempfile.mkdtemp(prefix="fm_marketcols_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP; app.BASE_DIR = TMP
app.OPTIONS_FILE = os.path.join(TMP, "options.json")
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=3,
            identity={"name": "Cols FC", "arena_name": "A", "color1": "#c47220",
                      "color2": "#14171f", "division": 3})

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
w = app.MainWindow(); w.resize(1560, 900); w.show()
w.show_game_message = lambda *a, **k: True
w.app_stack.setCurrentWidget(w.game_shell); q.processEvents()
w.show_page(7); q.processEvents()

table = w.market_table
header = table.horizontalHeader()
assert table.columnCount() == len(app.MARKET_COLUMN_SPECS) == 16
assert header.sectionsMovable()
assert header.sectionResizeMode(2) == QHeaderView.Stretch


def visible_width():
    return sum(table.columnWidth(i) for i in range(table.columnCount()) if not table.isColumnHidden(i))


assert visible_width() >= table.viewport().width() - 2, (visible_width(), table.viewport().width())
print("OK pleine largeur :", visible_width(), "/", table.viewport().width())

# Le nom est la colonne extensible, toutes les autres restent réglables.
header.resizeSection(4, 92); q.processEvents()
assert table.columnWidth(4) == 92
assert visible_width() >= table.viewport().width() - 2
print("OK largeur personnalisée :", table.columnWidth(4), "px")

# La fenêtre de colonnes propose les 16 colonnes, le nom reste verrouillé.
dlg = app.MarketColumnsDialog(w)
assert len(dlg.boxes) == 16 and len(dlg.spins) == 16
assert dlg.boxes["name"].isChecked() and not dlg.boxes["name"].isEnabled()
assert not dlg.spins["name"].isEnabled()
dlg.deleteLater()

# Masquer des colonnes puis tout réafficher, sans casser la largeur.
w.apply_market_columns({"nationality", "moral"}, None, save=False); q.processEvents()
assert table.isColumnHidden(6) and table.isColumnHidden(15)
assert visible_width() >= table.viewport().width() - 2, (visible_width(), table.viewport().width())
w.apply_market_columns(set(), None, save=False); q.processEvents()
assert not table.isColumnHidden(6) and not table.isColumnHidden(15)
print("OK colonnes masquables et réaffichables")

# L'état des en-têtes est mémorisé dans les options du joueur.
w._market_header_ready = True
w._save_market_header_state()
assert w.game_options.get("market_header_state")
assert os.path.exists(app.OPTIONS_FILE)
print("OK en-têtes mémorisés")
print("RESULT: ALL OK")
