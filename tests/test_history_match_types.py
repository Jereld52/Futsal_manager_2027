# -*- coding: utf-8 -*-
"""Historique : les matchs de coupe ne doivent plus être étiquetés AMICAL."""
import os, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication

TMP = tempfile.mkdtemp(prefix="fm_history_types_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP; app.BASE_DIR = TMP
app.OPTIONS_FILE = os.path.join(TMP, "options.json")
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=3,
            identity={"name": "History FC", "arena_name": "Arena", "color1": "#c47220",
                      "color2": "#14171f", "division": 3})

c = app.db()
season = int(c.execute("SELECT season FROM club WHERE id=1").fetchone()["season"] or 1)
club1 = c.execute("SELECT name FROM club WHERE id=1").fetchone()["name"]
club2 = c.execute("SELECT id,name FROM club WHERE id<>1 ORDER BY id LIMIT 1").fetchone()
opp_id, opp = int(club2["id"]), club2["name"]

def fixture(md, date_iso, ftype):
    c.execute("INSERT INTO fixture(season,matchday,fixture_date,home_club_id,away_club_id,fixture_type,played) "
              "VALUES(?,?,?,?,?,?,1)", (season, md, date_iso, 1, opp_id, ftype))

def record(md, date_iso):
    c.execute("INSERT INTO match_record(season,matchday,home,away,home_goals,away_goals,report,created_at) "
              "VALUES(?,?,?,?,?,?,?,?)", (season, md, club1, opp, 3, 1, "", date_iso + "T12:00"))

fixture(2, "2026-09-05", "championship"); record(2, "2026-09-05")
fixture(101, "2026-10-10", "cup"); record(0, "2026-10-10")
fixture(0, "2026-08-20", "friendly"); record(0, "2026-08-20")
c.commit()
app.ensure_management_tables(c)  # reprise des anciens enregistrements
c.commit()

rows = c.execute("SELECT id,matchday,fixture_type FROM match_record ORDER BY id").fetchall()
vals = [r["fixture_type"] for r in rows]
assert vals.count("championship") == 1 and vals.count("cup") == 1 and vals.count("friendly") == 1, vals
c.close()

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
app.MainWindow.show_game_message = lambda self, *a, **k: True
w = app.MainWindow(); w.resize(1360, 900); w.show()
w.app_stack.setCurrentWidget(w.game_shell); q.processEvents()
w.show_page(11); q.processEvents()
w.classement_tabs.setCurrentIndex(3); q.processEvents()
w._refresh_history_page(); q.processEvents()
idx = next((i for i in range(w.history_season_combo.count())
            if w.history_season_combo.itemData(i) == season), 0)
w.history_season_combo.setCurrentIndex(idx); q.processEvents()
w.history_tabs.setCurrentIndex(1); w._refresh_history_results(); q.processEvents()
days = [w.history_results_table.item(r, 0).text() for r in range(w.history_results_table.rowCount())]
assert "COUPE" in days, days
assert "AMICAL" in days, days
assert "J2" in days, days
print("OK historique :", days)
print("RESULT: ALL OK")
