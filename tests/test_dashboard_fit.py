# -*- coding: utf-8 -*-
"""Direction sportive : le bandeau compact tient dans la page sans defilement."""
import os, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication

TMP = tempfile.mkdtemp(prefix="fm_dashfit_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP; app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=3,
            identity={"name": "Dash FC", "arena_name": "A", "color1": "#c47220",
                      "color2": "#14171f", "division": 3})

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
w = app.MainWindow(); w.resize(1360, 900); w.show()
w.show_game_message = lambda *a, **k: True
w.app_stack.setCurrentWidget(w.game_shell); q.processEvents()
w.show_page(0); q.processEvents()
w.refresh_all(); q.processEvents()

page = w.stack.currentWidget()
assert page.height() <= w.stack.height() + 2, (page.height(), w.stack.height())
assert page.width() <= w.stack.width() + 2, (page.width(), w.stack.width())
assert page.sizeHint().width() <= page.width() + 2, (page.sizeHint().width(), page.width())

# Bandeau d'accueil : climat + 4 KPI compacts.
assert w.stat_budget.maximumHeight() <= 60
assert w.stat_points.maximumHeight() <= 60
assert w.stat_budget.findChild(app.QLabel, "Muted") is not None
# Prochain match : carte ramenee a 160 px maximum.
nextf = w.dashboard_open_match_btn.parentWidget()
assert nextf.maximumHeight() <= 160, nextf.maximumHeight()
assert nextf.height() <= 170, nextf.height()
print("OK page", page.width(), "x", page.height(), "dans", w.stack.width(), "x", w.stack.height())
print("OK prochain match", nextf.height(), "px | KPI", w.stat_budget.height(), "px")
print("RESULT: ALL OK")
w.close()
