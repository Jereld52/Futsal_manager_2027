# -*- coding: utf-8 -*-
"""Transferts : scouting lisible, états vides et shortlist propre."""
import os, sys, tempfile, json
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest

TMP = tempfile.mkdtemp(prefix="fm_scoutui_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP; app.BASE_DIR = TMP
app.OPTIONS_FILE = os.path.join(TMP, "options.json")
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=3,
            identity={"name": "Scout UI FC", "arena_name": "A", "color1": "#c47220",
                      "color2": "#14171f", "division": 3})

c = app.db()
c.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('scout_staff_hired','1')")
c.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('scout_level','2')")
players = c.execute("SELECT id FROM player WHERE club_id<>1 ORDER BY id LIMIT 2").fetchall()
for p in players:
    c.execute("INSERT OR REPLACE INTO scout_report(player_id,knowledge,reports,accuracy,updated_date) VALUES(?,?,?,?, '2026-07-01')",
              (int(p["id"]), 70, 2, 0.75))
    c.execute("INSERT INTO manager_message(kind,title,body,created_date,due_date,status,action_data,is_read) "
              "VALUES('scout_report','Rapport','Observation','2026-07-01','2026-07-05','ready',?,0)",
              (json.dumps({"player_id": int(p["id"]), "effort":"standard", "accuracy":0.75}),))
c.commit(); c.close()

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
w = app.MainWindow(); w.resize(1560, 900); w.show()
w.show_game_message = lambda *a, **k: True
w.app_stack.setCurrentWidget(w.game_shell); q.processEvents()
w.show_page(7); QTest.qWait(300); q.processEvents()
scout_idx = [w.mercato_tabs.tabText(i) for i in range(w.mercato_tabs.count())].index("SCOUTING")
w.mercato_tabs.setCurrentIndex(scout_idx); QTest.qWait(250); q.processEvents()

assert not w.scouting_table.wordWrap()
assert w.scouting_table.columnCount() == 7
assert w.scouting_table.horizontalHeaderItem(2).text() == "STATUT"
assert w.scouting_table.isVisible() and w.scouting_table.rowCount() == 2
bars = [w.scouting_table.cellWidget(r, 3) for r in range(w.scouting_table.rowCount())]
assert bars and all(b is not None and "RAPPORT" not in b.format() and "%" in b.format() for b in bars), [b.format() if b else None for b in bars]
print("OK scouting :", w.scouting_table.rowCount(), "missions lisibles")

# Les joueurs libres restent visibles dans le scouting.
c = app.db()
free = c.execute("SELECT id FROM player WHERE COALESCE(is_free_agent,0)=1 LIMIT 1").fetchone()
if free:
    fid = int(free["id"])
    c.execute("INSERT OR REPLACE INTO scout_report(player_id,knowledge,reports,accuracy,updated_date) VALUES(?,?,?,?, '2026-07-01')",
              (fid, 55, 1, 0.65))
    c.execute("INSERT INTO manager_message(kind,title,body,created_date,due_date,status,action_data,is_read) "
              "VALUES('scout_report','Rapport','Observation','2026-07-01','2026-07-05','ready',?,0)",
              (json.dumps({"player_id": fid, "effort":"standard", "accuracy":0.65}),))
    c.commit()
c.close()
w.refresh_scouting_tracker(); q.processEvents()
clubs = [w.scouting_table.item(r, 1).text() for r in range(w.scouting_table.rowCount()) if w.scouting_table.item(r, 1)]
if free:
    assert any("Joueur libre" in name for name in clubs), clubs
print("OK scouting : joueurs libres visibles")

# État vide du scouting.
c = app.db(); c.execute("DELETE FROM manager_message WHERE kind='scout_report'"); c.commit(); c.close()
w.refresh_scouting_tracker(); q.processEvents()
assert w.scouting_empty.isVisible() and not w.scouting_table.isVisible()
assert w.scouting_empty.findChildren(app.QPushButton)
print("OK scouting vide : état vide + accès marché")

# Shortlist vide puis remplie.
c = app.db(); c.execute("DELETE FROM shortlist"); c.commit(); c.close()
short_idx = [w.mercato_tabs.tabText(i) for i in range(w.mercato_tabs.count())].index("SHORTLIST")
w.mercato_tabs.setCurrentIndex(short_idx); q.processEvents()
w.refresh_shortlist_tab(); q.processEvents()
assert w.shortlist_empty.isVisible() and not w.shortlist_table.isVisible()
c = app.db()
pid = int(c.execute("SELECT id FROM player WHERE club_id<>1 LIMIT 1").fetchone()["id"])
c.execute("INSERT INTO shortlist(player_id,added_date,added_value,added_knowledge) VALUES(?,?,?,?)", (pid, "2026-07-01", 120000, 40))
c.commit(); c.close()
w.refresh_shortlist_tab(); q.processEvents()
assert w.shortlist_table.isVisible() and w.shortlist_table.rowCount() == 1
assert not w.shortlist_table.wordWrap()
print("OK shortlist :", w.shortlist_table.rowCount(), "cible(s), lignes propres")
print("RESULT: ALL OK")
