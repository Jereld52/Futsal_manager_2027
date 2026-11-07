# -*- coding: utf-8 -*-
"""Audit de la page Compétitions : classement, forme, coupe, archives."""
import os
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication, QLabel

TMP = tempfile.mkdtemp(prefix="fm_compaudit_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP
app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=2,
            identity={"name": "Comp FC", "arena_name": "A", "color1": "#2f6fed",
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

# 5 journées pour un classement vivant.
for _ in range(5):
    for _day in range(40):
        c = app.db(); fx = w._today_fixture_for_user(c); ready = c.execute("SELECT value FROM meta WHERE key='season_ready'").fetchone(); c.close()
        if fx:
            w.start_match(); w.finish_match_now(); q.processEvents(); break
        if ready and str(ready["value"]) == "1":
            break
        w.advance_calendar_days(1); q.processEvents()

w.show_page(11); q.processEvents()
w.classement_tabs.setCurrentIndex(0); q.processEvents()

# ---------- 1) Cohérence des données de classement ----------
c = app.db()
rows = c.execute("""SELECT s.*,c.division,c.name FROM league_standing s JOIN club c ON c.id=s.club_id
                    WHERE c.division=2 ORDER BY s.pts DESC,(s.gf-s.ga) DESC,s.gf DESC,c.name""").fetchall()
gf = sum(int(r["gf"] or 0) for r in rows); ga = sum(int(r["ga"] or 0) for r in rows)
assert len(rows) == 10
assert gf == ga, (gf, ga)
for r in rows:
    assert int(r["played"]) == int(r["wins"]) + int(r["draws"]) + int(r["losses"])
    assert int(r["pts"]) == 3 * int(r["wins"]) + int(r["draws"])
c.close()
print("1) classement: 10 clubs, points/MJ cohérents, GF = GA")

# ---------- 2) Liste : 10 lignes, zones, propre club, noms alignés ----------
assert w.standalone_standings.count() == 10, w.standalone_standings.count()
row_widgets = [w.standalone_standings.itemWidget(w.standalone_standings.item(i)) for i in range(10)]
assert "101f1a" in row_widgets[0].styleSheet() and "101f1a" in row_widgets[1].styleSheet(), "zone promotion"
assert "231619" in row_widgets[-1].styleSheet() and "231619" in row_widgets[-2].styleSheet(), "zone relégation"
_own_names = [lbl for rw in row_widgets for lbl in rw.findChildren(QLabel) if lbl.text().strip() == "Comp FC"]
assert _own_names and "2f6fed" in _own_names[0].styleSheet().lower(), "propre club non surligné"
xs = []
for rw in row_widgets:
    lab = next((lbl for lbl in rw.findChildren(QLabel) if lbl.text().lstrip("★ ").strip() in [r["name"] for r in rows]), None)
    assert lab is not None
    xs.append(lab.geometry().x())
assert max(xs) - min(xs) <= 1, xs
print("2) liste: zones OK, propre club surligné, noms alignés (x =", xs[0], ")")

# ---------- 3) Forme : championnat uniquement ----------
c = app.db()
games = c.execute("""SELECT * FROM fixture WHERE season=1 AND played=1
                     AND COALESCE(fixture_type,'championship')='championship'
                     AND (home_club_id=1 OR away_club_id=1)
                     ORDER BY fixture_date DESC LIMIT 5""").fetchall()
c.close()
expected = ""
for g in reversed(games):
    home = int(g["home_club_id"]) == 1
    ours = int((g["home_goals"] if home else g["away_goals"]) or 0)
    theirs = int((g["away_goals"] if home else g["home_goals"]) or 0)
    expected += "V" if ours > theirs else ("N" if ours == theirs else "D")
kpi = w.standings_kpi_form.text().replace(" ", "")
assert kpi == expected, (kpi, expected)
own_card = next((rw for rw in row_widgets
                 if any(lbl.text().strip() == "Comp FC" for lbl in rw.findChildren(QLabel))), None)
assert own_card is not None, "carte du club absent"
chips = [lbl for lbl in own_card.findChildren(QLabel)
         if lbl.width() == 15 and lbl.height() == 15
         and lbl.text().strip() in ("V", "N", "D")]
assert "".join(c.text().strip() for c in chips) == expected, \
    ("".join(c.text().strip() for c in chips), expected)
print("3) forme:", kpi, "= résultats de championnat, cartes dans le même sens")

# La coupe ne doit pas polluer la forme du classement.
c = app.db()
cup = c.execute("""SELECT id FROM fixture WHERE season=1 AND fixture_type='cup'
                   AND (home_club_id=1 OR away_club_id=1) LIMIT 1""").fetchone()
if cup:
    g = c.execute("SELECT * FROM fixture WHERE id=?", (int(cup["id"]),)).fetchone()
    if int(g["home_club_id"]) == 1:
        c.execute("UPDATE fixture SET played=1,home_goals=9,away_goals=0 WHERE id=?", (int(cup["id"]),))
    else:
        c.execute("UPDATE fixture SET played=1,home_goals=0,away_goals=9 WHERE id=?", (int(cup["id"]),))
    c.commit()
c.close()
w.refresh_all(); q.processEvents()
assert w.standings_kpi_form.text().replace(" ", "") == expected, "la coupe modifie la forme du championnat"
print("   coupe exclue de la forme")

# ---------- 4) Sélecteurs de division synchronisés ----------
w.standings_division_combo.setCurrentIndex(1); q.processEvents()  # Ligue 1
assert w.standalone_standings.count() == 10
assert w.history_division_combo.currentIndex() == 0, w.history_division_combo.currentIndex()
assert w.history_palmares_combo.currentIndex() == 0
assert w.palmares_league.currentIndex() == 0
w.standings_division_combo.setCurrentIndex(0); q.processEvents()  # mon club (L2)
assert w.history_division_combo.currentIndex() == 1, w.history_division_combo.currentIndex()
assert w.palmares_league.currentIndex() == 1
print("4) divisions synchronisées (historique/palmarès suivent)")

# ---------- 5) Historique : statuts live ----------
w.classement_tabs.setCurrentIndex(3); q.processEvents()
t = w.history_standings_table
statuses = [t.item(r, 6).text() for r in range(t.rowCount())]
assert "EN TÊTE" in statuses[0], statuses
assert "PROMOTION" in statuses[:2], statuses[:2]
assert "RELÉGATION" in statuses[-2:], statuses[-2:]
_captions = [lbl.text() for lbl in w.history_kpi_seasons.parentWidget().findChildren(QLabel)]
assert "SAISONS ARCHIVÉES" in _captions, _captions
print("5) historique: statuts", statuses[0], "/", statuses[1], "/", statuses[-1])

# ---------- 6) Palmarès : division par défaut + état vide ----------
w.classement_tabs.setCurrentIndex(4); q.processEvents()
assert w.palmares_league.currentIndex() == 1, w.palmares_league.currentIndex()
assert w.palmares_empty.isVisible(), "état vide du palmarès"
assert "Aucune saison archivée" in w.palmares_empty.text(), w.palmares_empty.text()
print("6) palmarès: Ligue 2 par défaut, état vide lisible")

# ---------- 7) Coupe : tableau et repères non tronqués ----------
w.classement_tabs.setCurrentIndex(1); q.processEvents()
assert w.cup_kpi_matches.text() == "28", w.cup_kpi_matches.text()
assert w.cup_minnow_label.height() >= 40, w.cup_minnow_label.height()
assert w.cup_minnow_sub.height() >= 30, w.cup_minnow_sub.height()
assert w.cup_minnow_label.text().strip(), "petit poucet vide"
assert "du 1er tour" in w.cup_byes_label.text().lower() or "exempt" in w.cup_byes_label.text().lower()
print("7) coupe: 28 matchs, repères", w.cup_minnow_label.height(), "px, non tronqués")

w.close(); q.processEvents()
size = os.path.getsize(r"C:\FM2027V2\data\error.log")
assert size == 0, size
print("RESULT: ALL OK")
