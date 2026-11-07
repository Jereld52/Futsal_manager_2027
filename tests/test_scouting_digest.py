# -*- coding: utf-8 -*-
"""Messagerie : pas de spam scouting, un rapport mensuel unique."""
import os, sys, tempfile, json
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest

TMP = tempfile.mkdtemp(prefix="fm_scoutdigest_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP; app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=3,
            identity={"name": "Digest FC", "arena_name": "A", "color1": "#c47220",
                      "color2": "#14171f", "division": 3})

c = app.db()
players = c.execute("SELECT id,first_name,last_name FROM player WHERE club_id<>1 LIMIT 2").fetchall()
for p in players:
    c.execute("INSERT OR REPLACE INTO scout_report(player_id,knowledge,reports,accuracy,updated_date) VALUES(?,?,?,0.8,'2026-09-15')",
              (int(p["id"]), 88, 2))
    c.execute("INSERT INTO manager_message(kind,title,body,created_date,due_date,status,action_data,is_read) "
              "VALUES('scout_report','Rapport','Observation','2026-09-15','2026-09-15','ready',?,0)",
              (json.dumps({"player_id": int(p["id"])}),))
c.commit(); c.close()

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
w = app.MainWindow(); w.show()
w.show_game_message = lambda *a, **k: True
w.app_stack.setCurrentWidget(w.game_shell); q.processEvents()
w.refresh_all(); q.processEvents()

rows = []
c = app.db(); rows = c.execute("SELECT * FROM manager_message ORDER BY id DESC").fetchall(); c.close()
w.refresh_manager_message_queue(rows); q.processEvents()
assert all(str(m["kind"]) != "scout_report" for m in w._manager_messages), [m["kind"] for m in w._manager_messages]
print("OK inbox : rapports individuels masqués")

c = app.db(); w.process_monthly_scouting_digest(c, "2026-10-01")
digest = c.execute("SELECT * FROM manager_message WHERE kind='scout_digest'").fetchone()
c.close()
assert digest is not None
info = json.loads(digest["action_data"]).get("players_info") or []
assert len(info) == 2, info
assert players[0]["last_name"] in info[0]["name"]
w.process_monthly_scouting_digest(app.db(), "2026-10-02")
c = app.db(); count = c.execute("SELECT COUNT(*) n FROM manager_message WHERE kind='scout_digest'").fetchone()["n"]; c.close()
assert count == 1, count
print("OK digest mensuel :", digest["title"])

# Rendu : le détail du digest affiche un tableau de fiches, pas une liste brute.
w.show_page(6); q.processEvents()
w._refresh_messages_ui(); q.processEvents()
row = next(i for i in range(w.action_message_list.count())
           if w.action_message_list.item(i).data(app.Qt.UserRole) == int(digest["id"]))
w.action_message_list.setCurrentRow(row); q.processEvents()
detail = w.action_message_detail.toPlainText()
assert "FICHES OUVERTES CE MOIS-CI" in detail, detail[:300]
assert players[0]["last_name"] in detail and players[1]["last_name"] in detail
print("OK détail : fiches du mois en cartes")
print("RESULT: ALL OK")
