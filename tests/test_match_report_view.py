# -*- coding: utf-8 -*-
"""Rapport de match : ecusson et maillot sur fond transparent (pas de carre noir)."""
import os, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication, QDialog, QWidget, QLabel

TMP = tempfile.mkdtemp(prefix="fm_reports_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP
app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=3,
            identity={"name": "Report FC", "arena_name": "A", "color1": "#2f6fed",
                      "color2": "#101a2e", "division": 3, "difficulty": "Normal"})
try:
    open(r"C:\FM2027V2\data\error.log", "r+b").truncate(0)
except FileNotFoundError:
    open(r"C:\FM2027V2\data\error.log", "wb").close()

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
w = app.MainWindow()
w.show_game_message = lambda *a, **k: True
w.resize(1400, 900)
w.show()
q.processEvents()
w.app_stack.setCurrentWidget(w.game_shell)
q.processEvents()

c = app.db()
fx = c.execute("SELECT id FROM fixture WHERE (home_club_id=1 OR away_club_id=1) "
               "AND played=0 ORDER BY fixture_date LIMIT 1").fetchone()
career = c.execute('SELECT "current_date" FROM career WHERE id=1').fetchone()["current_date"]
assert fx, "aucune rencontre pour le club"
c.execute("UPDATE fixture SET fixture_date=? WHERE id=?", (career, int(fx["id"])))
c.commit(); c.close()
w.refresh_all(); q.processEvents()
w.show_page(3); q.processEvents()

captured = {"groups": []}


def _exec(self, *a, **k):
    if self.windowTitle() == "Rapport de match":
        for group in self.findChildren(QWidget, "ReportVisualGroup"):
            captured["groups"].append({
                "group": group.styleSheet(),
                "labels": [lab.styleSheet() for lab in group.findChildren(QLabel)],
            })
    return QDialog.Accepted


app.QDialog.exec = _exec
assert w._launch_match_after_confirmation() is None
assert w.match_state
w.finish_match_now(); q.processEvents()

groups = captured["groups"]
assert len(groups) == 2, groups
for entry in groups:
    assert "transparent" in entry["group"], entry["group"]
    assert len(entry["labels"]) == 2, entry["labels"]
    for style in entry["labels"]:
        assert "transparent" in style, style
        assert "rgba(10,16,29" not in style, style
print("OK: 2 groupes ecusson+maillot transparents")

w.close()
q.processEvents()
size = os.path.getsize(r"C:\FM2027V2\data\error.log")
print("error.log =", size, "octet(s)")
assert size == 0
print("RESULT: ALL OK")
