# -*- coding: utf-8 -*-
"""Ecran de demarrage : fiche carriere, recentes, ticker et fond anime."""
import os, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app

TMP = tempfile.mkdtemp(prefix="fm_starttest_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP; app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=2,
            identity={"name": "Start FC", "arena_name": "Arena", "color1": "#c47220",
                      "color2": "#14171f", "division": 2})
from PySide6.QtWidgets import QApplication
q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
w = app.MainWindow(); w.resize(1280, 780); w.show(); q.processEvents()
w.app_stack.setCurrentWidget(w.start_screen); w.refresh_save_catalog(); q.processEvents()

for attr in ("start_hero_club", "start_hero_budget", "start_hero_record",
             "start_save_count", "start_recent_list", "start_tip_label", "start_status_label"):
    assert hasattr(w, attr), attr
print("hero:", w.start_hero_club.text(), "|", w.start_hero_meta.text())
print("budget:", w.start_hero_budget.text(), "| recentes:", w.start_recent_list.count())
assert "START FC" in w.start_hero_club.text().upper()
assert w.start_hero_budget.text() not in ("", "—")
assert w.start_recent_list.count() >= 1
assert "REPRENDRE" in w.resume_career_btn.text()
# Animation et ticker.
for _ in range(95):
    w._start_screen_tick()
assert w.start_tip_label.text().startswith("CONSEIL")
print("RESULT: ALL OK")
