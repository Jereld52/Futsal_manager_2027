# -*- coding: utf-8 -*-
"""Sponsors : logos fictifs, mur de partenaires, bouton masqué après signature."""
import os, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication

TMP = tempfile.mkdtemp(prefix="fm_sponsorui_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP; app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=3,
            identity={"name": "Sponsor FC", "arena_name": "A", "color1": "#c47220",
                      "color2": "#14171f", "division": 3})

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
app.MainWindow.show_game_message = lambda self, *a, **k: True
w = app.MainWindow(); w.resize(1360, 900); w.show()
w.app_stack.setCurrentWidget(w.game_shell); q.processEvents()
w.show_page(9); q.processEvents()
w.finance_tabs.setCurrentIndex(3); q.processEvents()
w._sponsor_refresh(); q.processEvents()

assert len(w.sponsor_wall_tiles) == len(w.SPONSOR_NAMES) == 10
assert all(tile.height() > 0 for tile in w.sponsor_wall_tiles.values())
logo = w.sponsor_logo_pixmap("GreenPulse", "#9fb6cc", 52)
assert logo is not None and not logo.isNull()
assert w.sponsor_btn.isVisible()

assert w.negotiate_sponsor(); q.processEvents()
w._sponsor_refresh(); q.processEvents()
assert len(w.sponsor_offer_cards) == 3
pixmaps = [lbl.pixmap() for card in w.sponsor_offer_cards for lbl in card["card"].findChildren(app.QLabel)
           if lbl.pixmap() is not None and not lbl.pixmap().isNull()]
assert len(pixmaps) >= 3, len(pixmaps)

name = w.sponsor_offer_cards[0]["offer"]["name"]
assert w.sign_sponsor(0); q.processEvents()
w._sponsor_refresh(); q.processEvents()
assert not w.sponsor_btn.isVisible(), "le bouton TROUVER DES SPONSORS doit disparaître après signature"
assert not w.sponsor_status.isVisible()
assert name.upper() in w.sponsor_deal_status.text()
assert w.sponsor_wall_tags[name].text() == "OFFICIEL"
assert w.sponsor_hero_icon.pixmap() is not None and not w.sponsor_hero_icon.pixmap().isNull()
print("OK sponsors :", name, "| logo officiel |", len(w.sponsor_wall_tiles), "partenaires")
print("RESULT: ALL OK")
