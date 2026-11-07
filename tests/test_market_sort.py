# -*- coding: utf-8 -*-
"""Marché : le tri porte sur tout le marché, pas seulement sur la page affichée.

Régression : en cliquant sur POTENTIEL (ou toute colonne), les meilleurs
profils pouvaient rester en page 2/3 car le tri Qt ne s'appliquait qu'aux
20 lignes visibles. Le tri est maintenant fait avant la pagination.
"""
import os, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

TMP = tempfile.mkdtemp(prefix="fm_marketsort_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP; app.BASE_DIR = TMP
app.OPTIONS_FILE = os.path.join(TMP, "options.json")
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=3,
            identity={"name": "Tri FC", "arena_name": "A", "color1": "#2b6cb0",
                      "color2": "#14171f", "division": 3})

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
w = app.MainWindow(); w.resize(1560, 900); w.show()
w.show_game_message = lambda *a, **k: True
w.app_stack.setCurrentWidget(w.game_shell); q.processEvents()
w.show_page(7); q.processEvents()

table = w.market_table
header = table.horizontalHeader()
rows = w._market_rows
assert len(rows) > w.market_page_size, len(rows)
print("OK marché chargé :", len(rows), "joueurs,", table.rowCount(), "lignes affichées")

# Le tri Qt est désactivé : c'est le tri maison qui pilote l'ordre.
assert not table.isSortingEnabled()
assert w._market_sort_column == -1
first_default = table.item(0, 2).text()
print("OK tri Qt désactivé, ordre par défaut conservé :", first_default)

# Un clic sur ÂGE (colonne 5) revient page 1 et trie tout le marché.
w.market_page_change(1); q.processEvents()
assert w.market_page == 1
w._market_header_clicked(5); q.processEvents()
assert w.market_page == 0, w.market_page
assert w._market_sort_column == 5 and w._market_sort_order == Qt.AscendingOrder
ages = [int(p["age"]) for p in w._market_rows]
assert ages == sorted(ages), ages[:10]
assert int(table.item(0, 5).text()) == min(ages)
print("OK tri ÂGE croissant sur tout le marché, page 1 :", ages[:5])

# Deuxième clic : ordre décroissant, le plus âgé en page 1.
w._market_header_clicked(5); q.processEvents()
assert w._market_sort_order == Qt.DescendingOrder
ages = [int(p["age"]) for p in w._market_rows]
assert ages == sorted(ages, reverse=True), ages[:10]
assert int(table.item(0, 5).text()) == max(ages)
print("OK tri ÂGE décroissant, plus âgé en page 1 :", ages[:5])

# La page 2 continue l'ordre global (pas de tri par page).
last_page1 = int(w._market_rows[w.market_page_size - 1]["age"])
w.market_page_change(1); q.processEvents()
assert w.market_page == 1
first_page2 = int(table.item(0, 5).text())
assert last_page1 >= first_page2, (last_page1, first_page2)
print("OK pagination cohérente :", last_page1, ">=", first_page2)

# Tri SCOUT (colonne 14) décroissant : le mieux connu du marché en page 1.
w._market_header_clicked(14); q.processEvents()
assert w.market_page == 0
w._market_header_clicked(14); q.processEvents()
known = [int(p["scout_knowledge"] or 0) for p in w._market_rows]
assert known == sorted(known, reverse=True), known[:10]
assert int(table.item(0, 14).text().replace(" %", "")) == max(known)
print("OK tri SCOUT décroissant, page 1 :", known[:5])

# Le tri survit à un changement de page et à un filtre.
w.market_page_change(1); q.processEvents()
w.refresh_market_only(reset_page=False); q.processEvents()
assert w._market_sort_column == 14
known2 = [int(p["scout_knowledge"] or 0) for p in w._market_rows]
assert known2 == sorted(known2, reverse=True)
print("OK tri conservé après rafraîchissement")

# Retour à l'ordre par défaut du marché.
w._market_sort_column = -1
w.refresh_market_only(reset_page=True); q.processEvents()
assert table.item(0, 2).text() == first_default, (table.item(0, 2).text(), first_default)
print("OK retour à l'ordre par défaut :", first_default)

# Le signal de clic d'en-tête est bien branché sur le tri global.
header.sectionClicked.emit(5)
q.processEvents()
assert w._market_sort_column == 5, w._market_sort_column
assert w.market_page == 0
print("OK clic d'en-tête branché : colonne", w._market_sort_column, "-> page", w.market_page + 1)

print("RESULT: ALL OK")
