# -*- coding: utf-8 -*-
"""Onboarding : guide des 3 premiers jours et progression persistante."""
import os
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

TMP = tempfile.mkdtemp(prefix="fm_onboarding_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "default.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP
app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=2,
            identity={"name": "Guide FC", "arena_name": "Halle",
                      "color1": "#2f6fed", "color2": "#14171f", "division": 2})

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
old_exec = app.QDialog.exec
app.QDialog.exec = lambda self, *a, **k: 1
try:
    w = app.MainWindow()
    w.setAttribute(Qt.WA_DontShowOnScreen, True)
    w.show_game_message = lambda *a, **k: True
    w.resize(1600, 1000); w.show(); q.processEvents()
    w.app_stack.setCurrentWidget(w.game_shell); q.processEvents()

    steps, played = w._onboarding_steps()
    assert len(steps) == 4, steps
    assert played == 0
    assert not steps[1][2], steps[1]
    w._apply_prematch_talk("confiance")
    steps, _ = w._onboarding_steps()
    assert steps[1][2], steps[1]
    c = app.db()
    c.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('onboarding_transfer_seen','1')")
    c.commit(); c.close()
    steps, _ = w._onboarding_steps()
    assert steps[3][2], steps[3]
    w.open_onboarding(); q.processEvents()
    # Hors écran, l'auto-affichage est volontairement désactivé.
    w.maybe_show_onboarding(); q.processEvents()
    c = app.db()
    auto = c.execute("SELECT value FROM meta WHERE key='onboarding_auto_shown'").fetchone()
    c.close()
    assert auto is None
    w.close(); q.processEvents()
finally:
    app.QDialog.exec = old_exec
assert os.path.getsize(r"C:\FM2027V2\data\error.log") == 0
print("1) guide : 4 étapes, causerie et mercato marqués")
print("2) hors écran : pas d'auto-affichage")
print("RESULT: ALL OK")
