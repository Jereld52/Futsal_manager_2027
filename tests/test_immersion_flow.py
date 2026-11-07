# -*- coding: utf-8 -*-
"""Parcours immersion complet : avant-match -> direct -> fin de match."""
import os
import shutil
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["FM2027_NO_AUDIO"] = "1"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

SRC = r"C:\FM2027V2\data\saves\arbot_futsal_saison_saison_6_20261028_025341.db"
TMP = tempfile.mkdtemp(prefix="fm_immflow_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
DB = os.path.join(TMP, "saves", "flow.db")
shutil.copy(SRC, DB)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = DB
app.DB_PATH = DB
app.DATA_DIR = TMP
app.BASE_DIR = TMP
app.active_save_path = lambda: DB
app.set_active_save_path = lambda p: None
app.init_db()

c = app.db()
next_fx = c.execute(
    "SELECT fixture_date FROM fixture WHERE (home_club_id=1 OR away_club_id=1) "
    "AND played=0 AND COALESCE(fixture_type,'championship')='championship' "
    "ORDER BY fixture_date LIMIT 1").fetchone()
assert next_fx is not None
c.execute("UPDATE career SET current_date=? WHERE id=1", (next_fx["fixture_date"],))
c.commit(); c.close()

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
old_exec = app.QDialog.exec
def auto_dialog(dlg, *args, **kwargs):
    return 1 if "Avant-match" in dlg.windowTitle() else 0
app.QDialog.exec = auto_dialog
try:
    w = app.MainWindow()
    w.setAttribute(Qt.WA_DontShowOnScreen, True)
    w.show_game_message = lambda *a, **k: True
    w.resize(1600, 1000); w.show(); q.processEvents()
    w.activate_career(DB); q.processEvents()
    assert w.app_stack.currentWidget() is w.game_shell
    w.start_match(); q.processEvents()
    assert w.match_state and not w.match_state.get("finished", True), w.match_state
    assert w.timer.isActive()
    w.timer.stop()
    assert "La salle explose" not in w.commentary_label.text()  # pas encore de but
    assert w.commentary_log.toPlainText().strip(), "commentaire de coup d'envoi absent"
    w.advance_minute(); q.processEvents()
    w.finish_match_now(); q.processEvents()
    assert w.match_state.get("finished") is True
    assert w.last_match_report is not None, "rapport non créé"
    assert w.match_phase.text().startswith("COUP DE SIFFLET"), w.match_phase.text()
    assert w.arena_sound.enabled is False
    c = app.db()
    rec = c.execute("SELECT COUNT(*) n FROM match_record WHERE season>0").fetchone()["n"]
    c.close()
    assert rec >= 1, rec
    w.close(); q.processEvents()
finally:
    app.QDialog.exec = old_exec
assert os.path.getsize(r"C:\FM2027V2\data\error.log") == 0
print("1) avant-match accepté, match lancé, commentaire de coup d'envoi présent")
print("2) fin de match : vestiaire/presse ignorés proprement, rapport enregistré")
print("RESULT: ALL OK")
