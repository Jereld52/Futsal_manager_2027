# -*- coding: utf-8 -*-
"""Audit de la Direction sportive : forme, prochain match, board, actualités."""
import os
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication, QLabel

TMP = tempfile.mkdtemp(prefix="fm_dashaudit_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP
app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=2,
            identity={"name": "Dash FC", "arena_name": "A", "color1": "#2f6fed",
                      "color2": "#101a2e", "division": 2})

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
app.QDialog.exec = lambda self, *a, **k: 1
w = app.MainWindow()
w.setAttribute(app.Qt.WA_DontShowOnScreen, True)
w.show_game_message = lambda *a, **k: True
w.resize(1600, 1000)
w.show(); q.processEvents()
w.app_stack.setCurrentWidget(w.game_shell)
w.show_page(0); q.processEvents()

# ---------- 1) Aucun match : forme vide ----------
chips = getattr(w, "dashboard_form_chips", [])
assert len(chips) == 5, len(chips)
assert all(c.text() == "—" for c in chips), [c.text() for c in chips]
assert w.dashboard_form_summary.text() == "aucun match", w.dashboard_form_summary.text()
# Début de saison : objectif provisoire, pas de sanction sur 0 match.
assert w.board_obj_rank.text().startswith("…"), w.board_obj_rank.text()
assert "début de saison" in w.board_obj_sub.text(), w.board_obj_sub.text()
conf0 = int(w.board_obj_conf.text().rstrip("%"))
assert conf0 >= 55, conf0
print("1) forme vide: 5 cases —, « aucun match » | board lancement, confiance", conf0, "%")

# ---------- 1b) Deux matchs, deux défaites : toujours en lancement ----------
c = app.db()
early = c.execute("""SELECT * FROM fixture WHERE fixture_type='championship'
                     AND (home_club_id=1 OR away_club_id=1)
                     ORDER BY fixture_date LIMIT 2""").fetchall()
for g in early:
    if int(g["home_club_id"]) == 1:
        c.execute("UPDATE fixture SET played=1,home_goals=0,away_goals=2 WHERE id=?", (int(g["id"]),))
    else:
        c.execute("UPDATE fixture SET played=1,home_goals=2,away_goals=0 WHERE id=?", (int(g["id"]),))
c.commit(); c.close()
w.refresh_all(); q.processEvents()
assert w.board_obj_rank.text().startswith("…"), w.board_obj_rank.text()
assert "début de saison" in w.board_obj_sub.text(), w.board_obj_sub.text()
conf2 = int(w.board_obj_conf.text().rstrip("%"))
assert conf2 >= 55, conf2
c = app.db()
freeze = c.execute("SELECT value FROM meta WHERE key='board_transfer_freeze'").fetchone()
warn = c.execute("SELECT value FROM meta WHERE key='board_warning_season'").fetchone()
c.close()
assert (freeze["value"] if freeze else "0") == "0", freeze
assert not (warn and str(warn["value"] or "")), warn
print("1b) 2 défaites: objectif en lancement, pas de gel ni d'avertissement, confiance", conf2, "%")

# ---------- 2) Trois matchs : V, N, D dans l'ordre ----------
c = app.db()
games = c.execute("""SELECT * FROM fixture WHERE fixture_type='championship'
                     AND (home_club_id=1 OR away_club_id=1) ORDER BY fixture_date LIMIT 3""").fetchall()
assert len(games) == 3
plans = [(2, 0), (1, 1), (0, 2)]  # pour l'équipe du manager : V, N, D
for g, (gf, ga) in zip(games, plans):
    if int(g["home_club_id"]) == 1:
        c.execute("UPDATE fixture SET played=1,home_goals=?,away_goals=? WHERE id=?", (gf, ga, int(g["id"])))
    else:
        c.execute("UPDATE fixture SET played=1,home_goals=?,away_goals=? WHERE id=?", (ga, gf, int(g["id"])))
c.commit(); c.close()
w.refresh_all(); q.processEvents()
labels = [c.text() for c in chips]
assert labels[:3] == ["V", "N", "D"], labels
assert labels[3:] == ["—", "—"], labels
assert w.dashboard_form_summary.text() == "1V 1N 1D", w.dashboard_form_summary.text()
assert not w.board_obj_rank.text().startswith("…"), w.board_obj_rank.text()
print("2) forme: V N D (plus ancien → plus récent), total 1V 1N 1D | board évalué")

# ---------- 3) Prochain match : pastille lieu + compte à rebours ----------
assert "J−" in w.dashboard_match_pill.text() or "AUJOURD" in w.dashboard_match_pill.text(), w.dashboard_match_pill.text()
assert ("DOMICILE" in w.dashboard_match_pill.text() or "EXTÉRIEUR" in w.dashboard_match_pill.text())
assert "J04" in w.dashboard_matchday_tag.text(), w.dashboard_matchday_tag.text()
print("3) prochain match:", w.dashboard_match_pill.text(), "|", w.dashboard_matchday_tag.text())

# ---------- 4) Board : légende CONFIANCE + valeur ----------
panel = w.board_obj_conf.parentWidget()
texts = [lbl.text() for lbl in panel.findChildren(QLabel)]
assert "CONFIANCE" in texts, texts
assert w.board_obj_conf.text().endswith("%"), w.board_obj_conf.text()
print("4) board: légende CONFIANCE, valeur", w.board_obj_conf.text())

# ---------- 5) Actualités : titre présent, mise en page compacte ----------
c = app.db()
c.execute("""INSERT INTO news(title,body,created_at) VALUES(?,?,?)""",
          ("Titre test dashboard", "Corps de test pour l'audit de la Direction sportive.", "2026-10-04 12:00:00"))
c.commit(); c.close()
w.refresh_all(); q.processEvents()
plain = w.news_feed.toPlainText()
assert "Titre test dashboard" in plain, plain[:200]
assert plain.count("Titre test dashboard") == 1
assert "Bienvenue Manager" not in plain or "Titre test dashboard" in plain
print("5) actualités: titre affiché une fois")

w.close(); q.processEvents()
size = os.path.getsize(r"C:\FM2027V2\data\error.log")
assert size == 0, size
print("RESULT: ALL OK")
