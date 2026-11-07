# -*- coding: utf-8 -*-
"""Audit Effectif / fiche joueur / fiche club : largeurs, fiche express, contrats, libellés."""
import json
import os
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication, QLabel
from PySide6.QtCore import Qt, QPoint

TMP = tempfile.mkdtemp(prefix="fm_squadaudit_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP
app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=2,
            identity={"name": "Squad FC", "arena_name": "Halle", "color1": "#2f6fed",
                      "color2": "#14171f", "division": 2})

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
CAPTURED = []
app.QDialog.exec = lambda self, *a, **k: (CAPTURED.append(self), 1)[1]
w = app.MainWindow()
w.setAttribute(app.Qt.WA_DontShowOnScreen, True)
w.show_game_message = lambda *a, **k: True
w.resize(1600, 1000); w.show(); q.processEvents()
w.app_stack.setCurrentWidget(w.game_shell)

# ---------- Préparation : 1 match nul, 1 buteur, contrats courts, vieilles largeurs ----------
c = app.db()
own = c.execute("SELECT id FROM player WHERE club_id=1 ORDER BY id LIMIT 1").fetchone()["id"]
c.execute("UPDATE player SET contract_years=1, season_goals=1, yellow_cards=2, suspension_matches=1 WHERE id=?", (own,))
c.execute("UPDATE league_standing SET played=1,wins=0,draws=1,losses=0,gf=2,ga=2,pts=1 WHERE club_id=1")
bad_widths = {"0":92,"1":174,"2":246,"3":124,"4":42,"5":40,"6":40,"7":40,"8":40,"9":40,"10":40,
              "11":46,"12":64,"13":64,"14":70,"15":56,"16":87,"17":141,"18":40,"19":44,"20":188,"21":104}
c.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('roster_column_widths',?)", (json.dumps(bad_widths),))
ai_player = c.execute("SELECT id FROM player WHERE club_id=2 ORDER BY id LIMIT 1").fetchone()["id"]
c.execute("UPDATE player SET season_goals=1, contract_years=1 WHERE id=?", (ai_player,))
c.commit(); c.close()

w.show_page(1); q.processEvents(); w.refresh_all(); q.processEvents()

# ---------- 1) Tableau : tient dans la page, colonnes lisibles ----------
table = w.roster_table
assert table.horizontalScrollBar().maximum() == 0, table.horizontalScrollBar().maximum()
headers = [table.horizontalHeaderItem(c).text() for c in range(table.columnCount())]
for expected in ("ÉTAT", "JOUEUR", "POSTE", "CONTRAT", "SALAIRE", "VALEUR", "J/S", "BUTS"):
    assert expected in headers, (expected, headers)
row = next(i for i in range(table.rowCount())
           if table.item(i, 2) and int(table.item(i, 2).data(Qt.UserRole) or 0) == int(own))
assert table.item(row, 15).text() == "1 an", table.item(row, 15).text()
assert table.item(row, 16).text().endswith("€") and "/mois" not in table.item(row, 16).text(), table.item(row, 16).text()
assert "VALEUR" not in table.item(row, 17).text(), table.item(row, 17).text()
assert "/20" not in table.item(row, 14).text(), table.item(row, 14).text()
assert table.item(row, 21).text() == "2J/1S", table.item(row, 21).text()
print("1) tableau :", table.horizontalScrollBar().maximum(), "dépassement ·", table.item(row, 15).text(), "·", table.item(row, 17).text())

# ---------- 2) Fiche express : visible, au-dessus du tableau, lisible ----------
table.setCurrentCell(row, 2); w.update_player_panel(row); q.processEvents()
assert w.player_panel.isVisible(), "fiche express cachée"
assert w.player_name.text() and "SÉLECTIONNE" not in w.player_name.text(), w.player_name.text()
page = w.stack.currentWidget()
assert w.player_panel.mapTo(page, QPoint(0, 0)).y() < w.roster_table.mapTo(page, QPoint(0, 0)).y()
assert "CONTRAT 1 an" in w.player_meta.text(), w.player_meta.text()
assert "FORME" in w.player_meta.text() and "MORAL" in w.player_meta.text()
print("2) fiche express :", w.player_name.text(), "|", w.player_meta.text().splitlines()[-1][:60])

# ---------- 3) Fiche joueur : contrat exact pour un joueur du club ----------
CAPTURED.clear()
w.open_player_profile(int(own)); q.processEvents()
assert CAPTURED, "fiche joueur non ouverte"
dlg = CAPTURED[-1]
texts = [lbl.text() for lbl in dlg.findChildren(QLabel)]
assert "CONTRAT" in texts, texts[:10]
assert "1 an" in texts, [t for t in texts if "an" in t][:8]
assert not any("an(s)" in t or t.startswith("≈") for t in texts), [t for t in texts if "an(s)" in t][:5]
print("3) fiche joueur : contrat", "1 an", "· pas de fourchette")

# ---------- 4) Fiche club : BP/BC, singuliers ----------
CAPTURED.clear()
w.show_club_profile(1); q.processEvents()
assert CAPTURED, "fiche club non ouverte"
texts = [lbl.text() for lbl in CAPTURED[-1].findChildren(QLabel)]
joined = " | ".join(texts)
assert "BP 2 · BC 2" in joined, [t for t in texts if "BP " in t][:3]
assert "1 PT" in joined and "1 MATCH" in joined, [t for t in texts if "PT" in t][:4]
assert "1 but" in joined and "1 buts" not in joined, [t for t in texts if "but" in t][:4]
print("4) fiche club : BP/BC, 1 PT, 1 MATCH, 1 but")

# ---------- 5) Fiche club IA : libellés singuliers ----------
CAPTURED.clear()
w.show_club_profile(2); q.processEvents()
texts = [lbl.text() for lbl in CAPTURED[-1].findChildren(QLabel)]
joined = " | ".join(texts)
assert "an(s)" not in joined, [t for t in texts if "an(s)" in t][:3]
assert "buts" not in joined or "1 but" in joined, [t for t in texts if "but" in t][:4]
print("5) fiche club IA : pas de an(s)/1 buts")

w.close(); q.processEvents()
assert os.path.getsize(r"C:\FM2027V2\data\error.log") == 0
print("RESULT: ALL OK")
