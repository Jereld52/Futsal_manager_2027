# -*- coding: utf-8 -*-
"""Compétitions : structure coupe, historique et palmarès."""
import os, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest

TMP = tempfile.mkdtemp(prefix="fm_compui_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP; app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=3,
            identity={"name": "Comp FC", "arena_name": "A", "color1": "#c47220",
                      "color2": "#14171f", "division": 3})

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
w = app.MainWindow(); w.resize(1560, 900); w.show()
w.show_game_message = lambda *a, **k: True
w.app_stack.setCurrentWidget(w.game_shell); q.processEvents()
w.show_page(11); QTest.qWait(400); q.processEvents()

# Championnat : les zones sont indiquées par la couleur et une flèche,
# jamais par un préfixe texte redondant.
w.classement_tabs.setCurrentIndex(0); q.processEvents()
labels = [lab.text().strip() for lab in w.standalone_standings.findChildren(app.QLabel)]
assert not any(t.startswith(("DESCENTE", "MONTÉE")) for t in labels), [t for t in labels if t.startswith(("DESCENTE", "MONTÉE"))]
rows = [w.standalone_standings.itemWidget(w.standalone_standings.item(i)) for i in range(w.standalone_standings.count())]
assert any("relégation" in (row.toolTip() or "").lower() for row in rows if row is not None)
print("OK classement : zones colorées, aucun préfixe DESCENTE/MONTÉE")

# Coupe : tableau + repères + état vide.
w.classement_tabs.setCurrentIndex(1); q.processEvents()
w.refresh_cup_page(); q.processEvents()
assert hasattr(w, "cup_bracket_empty") and hasattr(w, "cup_path") and hasattr(w, "cup_palmares")
if w.cup_matches.count() == 0:
    assert w.cup_bracket_empty.isVisible()
else:
    assert not w.cup_bracket_empty.isVisible()
print("OK coupe :", w.cup_matches.count(), "match(s) au tableau")

# Historique : tableaux stylés et noms de clubs neutres.
w.classement_tabs.setCurrentIndex(3); q.processEvents()
assert "QHeaderView" in w.history_standings_table.styleSheet()
assert w.history_standings_table.alternatingRowColors()
print("OK historique : tableau stylé,", w.history_standings_table.rowCount(), "ligne(s)")

# Palmarès : en-tête, KPI et tableau.
w.classement_tabs.setCurrentIndex(4); q.processEvents()
w._refresh_palmares_page(); q.processEvents()
for key in ("palmares_kpi_titles", "palmares_kpi_seasons", "palmares_kpi_last"):
    assert hasattr(w, key), key
assert "QHeaderView" in w.palmares_tab_table.styleSheet()
print("OK palmarès : KPI et tableau")
print("RESULT: ALL OK")
