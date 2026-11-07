# -*- coding: utf-8 -*-
"""Staff : cartes compactes, bandeau de synthèse non dupliqué."""
import os, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest

TMP = tempfile.mkdtemp(prefix="fm_staffui_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP; app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=3,
            identity={"name": "Staff FC", "arena_name": "A", "color1": "#c47220",
                      "color2": "#14171f", "division": 3})

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
w = app.MainWindow(); w.resize(1560, 900); w.show()
w.show_game_message = lambda *a, **k: True
w.app_stack.setCurrentWidget(w.game_shell); q.processEvents()
w.show_page(10); QTest.qWait(300); q.processEvents()

assert len(w.staff_cards) == 8
assert w.staff_summary.isHidden()
assert all(info["card"].maximumHeight() <= 120 for info in w.staff_cards.values())
assert all(len(info["card"].findChildren(app.QPushButton)) >= 2 for info in w.staff_cards.values())
print("OK staff :", len(w.staff_cards), "cartes compactes, synthèse non dupliquée")

# Un poste pourvu doit rester lisible et sobre.
c = app.db()
c.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('comptable_hired','1')")
c.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('comptable_hired_level','2')")
c.commit(); c.close()
w._staff_refresh(); q.processEvents()
info = w.staff_cards["comptable_hired"]
assert info["status"].text() == "EN POSTE"
assert info["btn"].text() == "LICENCIER"
assert "€/mois" in info["cost_lbl"].full_text()
print("OK poste pourvu :", info["status"].text(), "|", info["btn"].text())
print("RESULT: ALL OK")
