# -*- coding: utf-8 -*-
"""Fiche club : grande, effectif degage, onglet DERNIERS MATCHS separe."""
import os, re, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication, QDialog, QTabWidget, QTableWidget, QListWidget, QLabel

TMP = tempfile.mkdtemp(prefix="fm_clubsheet_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP
app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=1,
            identity={"name": "Fiche FC", "arena_name": "A", "color1": "#2f6fed",
                      "color2": "#101a2e", "division": 1, "difficulty": "Normal"})
try:
    open(r"C:\FM2027V2\data\error.log", "r+b").truncate(0)
except FileNotFoundError:
    open(r"C:\FM2027V2\data\error.log", "wb").close()

# Quelques matchs joues pour le club 1 (club du joueur : fiche complète).
c = app.db()
rows = c.execute("SELECT id FROM fixture WHERE (home_club_id=1 OR away_club_id=1) "
                 "AND played=0 ORDER BY fixture_date LIMIT 8").fetchall()
for i, r in enumerate(rows):
    c.execute("UPDATE fixture SET played=1, home_goals=?, away_goals=? WHERE id=?",
              (1 + (i % 3), (i + 1) % 3, int(r["id"])))
c.commit()
c.close()

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
w = app.MainWindow()
w.show_game_message = lambda *a, **k: True
w.resize(1400, 900)
w.show()
q.processEvents()

captured = {}
_orig = app.QDialog.exec


def _exec_capture(self, *a, **k):
    captured["dlg"] = self
    return 0


app.QDialog.exec = _exec_capture
try:
    w.show_club_profile(1)
finally:
    app.QDialog.exec = _orig
    q.processEvents()

dlg = captured.get("dlg")
assert dlg is not None, "la fiche club ne s'est pas ouverte"
assert dlg.minimumWidth() >= 1000, dlg.minimumWidth()
assert dlg.minimumHeight() >= 700, dlg.minimumHeight()
print("OK: fiche club agrandie :", dlg.width(), "x", dlg.height(),
      "| minimum", dlg.minimumWidth(), "x", dlg.minimumHeight())

tabs = [t for t in dlg.findChildren(QTabWidget) if t.count() >= 4]
assert tabs, "onglets de la fiche introuvables"
club_tabs = tabs[0]
labels = [club_tabs.tabText(i) for i in range(club_tabs.count())]
assert "EFFECTIF" in labels and "DERNIERS MATCHS" in labels, labels
assert "SALLE" in labels and "PALMARÈS" in labels, labels
print("OK: onglets :", labels)

eff_page = club_tabs.widget(labels.index("EFFECTIF"))
assert not eff_page.findChildren(QTableWidget), "l'effectif contient encore le tableau des matchs"
roster = eff_page.findChild(QListWidget)
assert roster is not None and roster.count() > 0, "effectif vide"
print("OK: effectif seul dans son onglet :", roster.count(), "joueurs")

recent_page = club_tabs.widget(labels.index("DERNIERS MATCHS"))
rtbl = recent_page.findChild(QTableWidget)
assert rtbl is not None, "tableau des derniers matchs absent"
assert rtbl.rowCount() == len(rows), (rtbl.rowCount(), len(rows))
assert rtbl.horizontalHeaderItem(2).text() == "DOMICILE"
assert rtbl.horizontalHeaderItem(4).text() == "EXTÉRIEUR"
print("OK: onglet DERNIERS MATCHS :", rtbl.rowCount(), "matchs")

# ---------- Forme : même sens partout (plus ancien à gauche) ----------
c = app.db()
games = c.execute("""SELECT * FROM fixture WHERE season=1 AND played=1
                     AND COALESCE(fixture_type,'championship')='championship'
                     AND (home_club_id=1 OR away_club_id=1)
                     ORDER BY fixture_date,id""").fetchall()
c.close()
expected = ""
for g in games:
    home = int(g["home_club_id"]) == 1
    ours = int((g["home_goals"] if home else g["away_goals"]) or 0)
    theirs = int((g["away_goals"] if home else g["home_goals"]) or 0)
    expected += "V" if ours > theirs else ("N" if ours == theirs else "D")
expected = expected[-5:]
caps = [lbl for lbl in dlg.findChildren(QLabel)
        if lbl.text().strip() == "FORME  •  5 DERNIERS"]
assert caps, "tuile FORME absente"
tile = caps[0].parentWidget()
values = [lbl for lbl in tile.findChildren(QLabel)
          if lbl is not caps[0] and lbl.text().strip()]
assert values, "valeur FORME absente"
kpi_order = "".join(re.findall(r">([VND])<", values[0].text()))
assert kpi_order == expected, (kpi_order, expected)
pills = [lbl for lbl in dlg.findChildren(QLabel)
         if lbl.minimumWidth() == 22 and lbl.minimumHeight() == 22
         and lbl.text().strip() in ("V", "N", "D")]
assert len(pills) >= len(expected), (len(pills), expected)
pill_order = "".join(p.text().strip() for p in pills[:len(expected)])
assert pill_order == expected, (pill_order, expected)
print("OK: forme fiche club (tuile + pastilles) :", expected, "du plus ancien au plus récent")

dlg.close()
q.processEvents()
size = os.path.getsize(r"C:\FM2027V2\data\error.log")
print("error.log =", size, "octet(s)")
assert size == 0
print("RESULT: ALL OK")
