# -*- coding: utf-8 -*-
"""Ventes différées : aucune offre sur un joueur déjà vendu."""
import os, sys, tempfile, json
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication

TMP = tempfile.mkdtemp(prefix="fm_soldoffers_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP
app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=3,
            identity={"name": "Vente FC", "arena_name": "A", "color1": "#2f6fed",
                      "color2": "#101a2e", "division": 3, "difficulty": "Normal"})
try:
    open(r"C:\FM2027V2\data\error.log", "r+b").truncate(0)
except FileNotFoundError:
    open(r"C:\FM2027V2\data\error.log", "wb").close()

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
w = app.MainWindow()
w.show_game_message = lambda *a, **k: True
w.resize(1300, 800)
w.show()
w.app_stack.setCurrentWidget(w.game_shell)
q.processEvents()

c = app.db()
season = int(c.execute("SELECT season FROM club WHERE id=1").fetchone()["season"])
player = c.execute("SELECT * FROM player WHERE club_id=1 ORDER BY id LIMIT 1").fetchone()
buyer = c.execute("SELECT id,name FROM club WHERE id<>1 ORDER BY id LIMIT 1").fetchone()
pid = int(player["id"]); bid = int(buyer["id"])
name = f"{player['first_name']} {player['last_name']}"
c.execute("UPDATE player SET transfer_listed=1 WHERE id=?", (pid,))
dep = {"player_id": pid, "player_name": name, "buyer_id": bid, "buyer_name": buyer["name"],
       "fee": 1000, "deferred": True, "effective_date": "2033-07-01"}
c.execute("INSERT INTO manager_message(kind,title,body,created_date,due_date,status,action_data,is_read) "
          "VALUES('transfer_departure','Vente • départ à l''ouverture','test','2026-07-01','2033-07-01','waiting',?,0)",
          (json.dumps(dep),))
for i in range(2):
    offer = dict(dep); offer.update({"fee": 1200 + i, "buyer_limit": 1500})
    c.execute("INSERT INTO manager_message(kind,title,body,created_date,due_date,status,action_data,is_read) "
              "VALUES('transfer_sale','Offre reçue','test','2026-07-01','2026-07-02','ready',?,0)",
              (json.dumps(offer),))
# doublon de départ
c.execute("INSERT INTO manager_message(kind,title,body,created_date,due_date,status,action_data,is_read) "
          "VALUES('transfer_departure','Vente • départ à l''ouverture','doublon','2026-07-01','2033-07-01','waiting',?,0)",
          (json.dumps(dep),))
c.commit(); c.close()

changed = w.repair_pending_departures()
assert changed >= 3, changed
c = app.db()
deps = c.execute("SELECT id,action_data FROM manager_message WHERE kind='transfer_departure' "
                 "AND status IN ('waiting','ready') AND action_data LIKE ?", (f'%"player_id": {pid}%',)).fetchall()
offers = c.execute("SELECT id,status,action_data FROM manager_message WHERE kind='transfer_sale'").fetchall()
listed = int(c.execute("SELECT transfer_listed FROM player WHERE id=?", (pid,)).fetchone()["transfer_listed"])
c.close()
assert len(deps) == 1, len(deps)
assert all(o["status"] == "handled" and json.loads(o["action_data"]).get("outcome") == "already_sold" for o in offers), offers
assert listed == 0, listed
print("OK: 1 seul depart, offres classees, joueur retire de la liste")

# Une nouvelle offre acceptée sur ce joueur est classée elle aussi.
c = app.db()
offer = dict(dep); offer.update({"fee": 2000})
c.execute("INSERT INTO manager_message(kind,title,body,created_date,due_date,status,action_data,is_read) "
          "VALUES('transfer_sale','Offre tardive','test','2026-07-01','2026-07-02','ready',?,0)",
          (json.dumps(offer),))
mid = int(c.execute("SELECT MAX(id) FROM manager_message").fetchone()[0])
c.commit(); c.close()
c = app.db()
rows = c.execute("SELECT * FROM manager_message ORDER BY id DESC LIMIT 200").fetchall()
c.close()
w.refresh_manager_message_queue(rows)
w.resolve_manager_message("accept", mid)
q.processEvents()
c = app.db()
row = c.execute("SELECT status,action_data FROM manager_message WHERE id=?", (mid,)).fetchone()
deps = c.execute("SELECT COUNT(*) n FROM manager_message WHERE kind='transfer_departure' "
                 "AND status IN ('waiting','ready') AND action_data LIKE ?", (f'%"player_id": {pid}%',)).fetchone()["n"]
c.close()
assert row["status"] == "handled", row["status"]
assert json.loads(row["action_data"]).get("outcome") == "already_sold", row["action_data"]
assert deps == 1, deps
print("OK: offre tardive refusee et classee")

w.close(); q.processEvents()
size = os.path.getsize(r"C:\FM2027V2\data\error.log")
print("error.log =", size, "octet(s)")
assert size == 0
print("RESULT: ALL OK")
