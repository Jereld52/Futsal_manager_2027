# -*- coding: utf-8 -*-
"""Immersion : commentaire live, sons de salle, vestiaire et avant-match."""
import os
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["FM2027_NO_AUDIO"] = "1"
sys.path.insert(0, r"C:\FM2027V2")
import app
from immersion import ArenaSound, commentary_line
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

TMP = tempfile.mkdtemp(prefix="fm_immersion_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "default.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP
app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=2,
            identity={"name": "Immersion FC", "arena_name": "Halle",
                      "color1": "#2f6fed", "color2": "#14171f", "division": 2})

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
app.QDialog.exec = lambda self, *a, **k: 1
w = app.MainWindow()
w.setAttribute(Qt.WA_DontShowOnScreen, True)
w.show_game_message = lambda *a, **k: True
w.resize(1600, 1000)
w.show(); q.processEvents()
w.app_stack.setCurrentWidget(w.game_shell); q.processEvents()

# 1) Commentaire : nettoyage HTML et préfixe vivant.
line = commentary_line("goal", "<b>00:12 — BUT !</b> Roux conclut l'action.")
assert line.startswith("La salle explose"), line
assert "<" not in line and "00:12" not in line, line
print("1) commentaire :", line)

# 2) Son : désactivé en mode test, aucun WAV créé.
sound = ArenaSound(TMP, enabled=True)
assert not sound.enabled
assert not os.path.isdir(os.path.join(TMP, "audio"))
print("2) sons : silencieux hors écran, aucun asset généré")

# 3) Ticker + journal de commentaire branchés sur les événements.
w.match_state = {"elapsed_seconds": 12, "timeline": []}
w.log_match_event("<b>00:12 — BUT !</b> Roux conclut l'action.", "goal")
assert "La salle explose" in w.commentary_label.text(), w.commentary_label.text()
assert "BUT" in w.commentary_log.toPlainText()
print("3) ticker :", w.commentary_label.text())

# 4) Avant-match : salle, vestiaire, adversaire et enjeu.
c = app.db()
fx = c.execute("""SELECT * FROM fixture WHERE fixture_type='championship'
                  AND (home_club_id=1 OR away_club_id=1) LIMIT 1""").fetchone()
assert fx is not None
is_home = int(fx["home_club_id"]) == 1
opp_id = int(fx["away_club_id"] if is_home else fx["home_club_id"])
opp_row = c.execute("SELECT name FROM club WHERE id=?", (opp_id,)).fetchone()
c.close()
opp = opp_row["name"] if opp_row else "Adversaire"
atmo = w._prematch_atmosphere(fx, is_home, opp or "Adversaire")
html = atmo["html"]
for token in ("ARRIVÉE AU GYMNASE", "VESTIAIRE", "ADVERSAIRE", "ENJEU"):
    assert token in html, (token, html)
assert atmo["attendance"] > 0, atmo
print("4) avant-match :", atmo["attendance"], "spectateurs,", atmo["rank"], "e / top", atmo["target"])

# 5) Vestiaire d'après-match : acceptation -> conférence.
c = app.db()
players = [dict(row) for row in c.execute(
    "SELECT * FROM player WHERE club_id=1 ORDER BY id LIMIT 3").fetchall()]
c.close()
state = {"hg": 3, "ag": 1, "is_home": True, "lineup": players,
         "player_goals": {int(players[0]["id"]): 2},
         "player_saves": {int(players[1]["id"]): 4}}
old_exec = app.QDialog.exec
app.QDialog.exec = lambda self, *a, **k: 1
try:
    assert w._show_postmatch_dressing_room({"outcome": "VICTOIRE"}, state) is True
finally:
    app.QDialog.exec = old_exec
print("5) vestiaire : scène acceptée, passage en conférence")

w.close(); q.processEvents()
assert os.path.getsize(os.path.join(TMP, "error.log")) == 0 if os.path.exists(os.path.join(TMP, "error.log")) else True
assert os.path.getsize(r"C:\FM2027V2\data\error.log") == 0
print("RESULT: ALL OK")
