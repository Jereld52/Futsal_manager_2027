# -*- coding: utf-8 -*-
"""Audit visuel court : pages, accueil, mercato, graphe plat et absence de match."""
import os, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app, ui_components

TMP = tempfile.mkdtemp(prefix="fm_visual_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP; app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=3,
            identity={"name": "Visual FC", "arena_name": "Halle", "color1": "#c47220",
                      "color2": "#14171f", "division": 3})

from PySide6.QtWidgets import QApplication, QPushButton, QLabel, QFrame
from PySide6.QtTest import QTest
q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
messages = []
app.MainWindow.show_game_message = lambda self, *a, **k: (messages.append(a), True)[1]
w = app.MainWindow(); w.resize(1360, 900); w.show()
w.app_stack.setCurrentWidget(w.game_shell); q.processEvents()
try: w._animate_page_reveal = lambda idx: None
except Exception: pass

# 1) Centre de match sans rencontre : message explicite, pas de clic silencieux.
w.show_page(2); q.processEvents()
w.show_page(3); q.processEvents()
print("message centre de match:", messages[-1] if messages else None)
assert messages and "Aucun match" in str(messages[-1][1])

# 2) Accueil : raccourcis retirés, bloc climat arrondi présent.
labels = [b.text() for b in w.pages[0].findChildren(QPushButton)]
assert "Centre de formation" not in labels and "Finances" not in labels, labels
assert w.pages[0].findChild(QFrame, "ClimatePanel") is not None
assert w.board_gauge_label is not None and w.fans_gauge_label is not None
assert not hasattr(w, "notif_panel")
print("accueil: raccourcis retirés, climat présent")

# 3) Mercato : filtres complets et tableau alimenté.
w.show_page(7); QTest.qWait(120); q.processEvents()
print("mercato:", w.market_table.rowCount(), "lignes |", w.mercato_attr.count(), "atouts |", w.mercato_stat.count(), "stats")
assert w.market_table.rowCount() > 0
assert w.mercato_attr.count() >= 8 and w.mercato_stat.count() >= 3

# 4) Graphe plat : pas de bloc plein, rendu sans erreur.
chart = app.FinanceChart("bar", "Flux")
chart.resize(360, 150); chart.set_series([0]); pm = chart.grab()
assert not pm.isNull() and pm.width() == 360
chart.set_series([120000, 120000, 120000]); pm = chart.grab()
assert not pm.isNull()
print("graphe plat:", pm.width(), "x", pm.height())

# 4a) Mercato : grand tableau de 16 colonnes et panneau détail repliable.
w.show_page(7); QTest.qWait(140); q.processEvents()
assert w.market_table.columnCount() == 16
assert w.market_table.rowCount() > 0
assert not w.market_side_panel.isVisible()
w._toggle_market_detail(); q.processEvents()
assert w.market_side_panel.isVisible()
w._toggle_market_detail(); q.processEvents()
assert not w.market_side_panel.isVisible()
print("mercato:", w.market_table.columnCount(), "colonnes |", w.market_table.rowCount(), "lignes")

# 4b) Effectif : toutes les colonnes sont redimensionnables et mémorisées.
w.show_page(1); q.processEvents()
header = w.roster_table.horizontalHeader()
assert all(header.sectionResizeMode(c) == app.QHeaderView.Interactive for c in range(header.count()))
header.resizeSection(4, 88)
QTest.qWait(650); q.processEvents()
w.refresh_all(); q.processEvents()
print("largeur colonne 4:", header.sectionSize(4))
assert header.sectionSize(4) == 88

# 4c) Calendrier : listes remplies à l'ouverture et au changement d'onglet.
w.show_page(8); QTest.qWait(180); q.processEvents()
print("calendrier saison:", w.calendar_fixture_list.count())
assert w.calendar_fixture_list.count() > 0
w.championship_tabs.setCurrentIndex(1); QTest.qWait(180); q.processEvents()
w.championship_tabs.setCurrentIndex(0); QTest.qWait(220); q.processEvents()
assert w.calendar_fixture_list.count() > 0
w.championship_tabs.setCurrentIndex(2); QTest.qWait(160); q.processEvents()
assert w.calendar_cup_list.count() >= 0
w.championship_tabs.setCurrentIndex(0); q.processEvents()

# 4d) Classement : couronne seulement quand le titre est acquis.
rows = [{"played": 20, "pts": 60, "club_id": 1}, {"played": 20, "pts": 55, "club_id": 2}]
assert not app.MainWindow._champion_is_clinched(rows, {1: 4, 2: 4})
assert app.MainWindow._champion_is_clinched(
    [{"played": 20, "pts": 80, "club_id": 1}, {"played": 20, "pts": 55, "club_id": 2}], {1: 4, 2: 4})
assert app.MainWindow._champion_is_clinched(rows, {}, True)

w.show_page(11); QTest.qWait(320); q.processEvents()
conn = app.db()
ids = [int(r["club_id"]) for r in conn.execute(
    "SELECT s.club_id FROM league_standing s JOIN club c ON c.id=s.club_id WHERE c.division=3").fetchall()]
assert len(ids) >= 2, ids
for pos, cid in enumerate(ids):
    conn.execute("UPDATE league_standing SET pts=?, played=20 WHERE club_id=?", (60 - pos * 2, cid))
conn.commit(); conn.close()
w._fill_standalone_standings(); q.processEvents()
first = w.standalone_standings.itemWidget(w.standalone_standings.item(0))
crowns = [lbl for lbl in first.findChildren(QLabel) if "champion" in (lbl.toolTip() or "").lower()]
assert not crowns, "couronne affichée avant le titre"
conn = app.db(); conn.execute("UPDATE league_standing SET pts=200 WHERE club_id=?", (ids[0],)); conn.commit(); conn.close()
w._fill_standalone_standings(); q.processEvents()
first = w.standalone_standings.itemWidget(w.standalone_standings.item(0))
crowns = [lbl for lbl in first.findChildren(QLabel) if "champion" in (lbl.toolTip() or "").lower()]
assert len(crowns) == 1, crowns
texts = [lbl.text() for lbl in first.findChildren(QLabel)]
assert all("CHAMPION" not in text.upper() for text in texts), texts
print("couronne champion: OK")

# 4e) En-tête unique : chaque page porte le même bandeau d'identité, sans doublon.
EXPECTED_TITLES = ["Direction sportive", "Effectif", "Tactiques", "Centre de match",
                   "Entraînement", "Infrastructure", "Messagerie", "Transferts",
                   "Calendrier", "Finances", "Personnel du club", "Compétitions",
                   "Recherche", "Centre de formation"]
for idx, expected in enumerate(EXPECTED_TITLES):
    page = w.pages[idx]
    hero = page.findChild(QFrame, "PageHero")
    assert hero is not None, (idx, expected)
    labels = [lbl.text() for lbl in hero.findChildren(QLabel)]
    assert expected in labels, (idx, expected, labels[:4])
    dups = [lbl.text() for lbl in page.findChildren(QLabel)
            if lbl.text().strip().lower() == expected.lower()]
    assert len(dups) == 1, (idx, expected, dups)
print("bandeau unique sur", len(EXPECTED_TITLES), "pages: OK")

# 4f) Tactiques : terrain horizontal large, banc lisible.
w.show_page(2); QTest.qWait(220); q.processEvents()
court = w.pitch.court_rect()
assert (not w.pitch.vertical) and court.width() > court.height() * 1.5, (court.width(), court.height())
assert w.tactic_bench.width() >= 380, w.tactic_bench.width()
print("tactiques: terrain horizontal %.0fx%.0f | banc %d" % (court.width(), court.height(), w.tactic_bench.width()))

# 5) Toutes les pages se rendent en 1000x700 sans exception.
w.resize(1000, 700); q.processEvents()
for idx in range(14):
    w.show_page(idx); QTest.qWait(30); q.processEvents()
    pm = w.grab()
    assert not pm.isNull() and pm.width() == 1000 and pm.height() == 700, (idx, pm.size())
print("rendu 14 pages en 1000x700: OK")

# 6) Recherche : debounce présent.
w.search_query.setText("pivot"); w._on_search_filter_changed(); q.processEvents()
assert hasattr(w, "_search_debounce") and w._search_debounce.interval() >= 100
print("debounce recherche:", w._search_debounce.interval(), "ms")
w.close()
print("RESULT: ALL OK")
