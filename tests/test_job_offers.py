# -*- coding: utf-8 -*-
"""Offres de club : lateral possible en Ligue 1, aucune offre apres relegation."""
import os, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import json
import app
from PySide6.QtWidgets import QApplication

TMP = tempfile.mkdtemp(prefix="fm_joboffers_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP
app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=1,
            identity={"name": "Job FC", "arena_name": "A", "color1": "#2f6fed",
                      "color2": "#101a2e", "division": 1, "difficulty": "Normal"})
try:
    open(r"C:\FM2027V2\data\error.log", "r+b").truncate(0)
except FileNotFoundError:
    open(r"C:\FM2027V2\data\error.log", "wb").close()

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
w = app.MainWindow()
w.show_game_message = lambda *a, **k: True
w.resize(1200, 800)
w.show()
q.processEvents()


def archive(conn, rank, kind):
    conn.execute("DELETE FROM season_archive WHERE club_id=1")
    conn.execute("INSERT INTO season_archive(season,division,rank,club_id,club_name,"
                 "played,pts,gf,ga,kind) VALUES(1,1,?,1,'Job FC',18,40,50,20,?)",
                 (int(rank), kind))
    conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('board_confidence','80')")
    conn.commit()


c = app.db()
archive(c, 1, "champion")
offers = w.generate_job_offers(c)
assert len(offers) == 2, ("deux offres attendues en Ligue 1", offers)
assert all(int(o["division"]) == 1 for o in offers), offers
assert all(int(o["club_id"]) != 1 for o in offers), offers
print("OK: champion Ligue 1 ->", [(o["name"], o["division"]) for o in offers])

# Message SECRET/privé pour chaque club qui veut recruter le manager.
msgs = c.execute("SELECT * FROM manager_message WHERE kind='job_offer' ORDER BY id").fetchall()
assert len(msgs) == len(offers), [dict(m) for m in msgs]
offer_ids = {int(o["club_id"]) for o in offers}
for m in msgs:
    data = json.loads(m["action_data"])
    assert int(data["club_id"]) in offer_ids, data
    assert "SECRET" in m["title"], m["title"]
    assert "CONFIDENTIEL" in m["body"], m["body"]
    assert m["status"] == "ready" and not int(m["is_read"])
print("OK: messages SECRET créés ->", [m["title"] for m in msgs])

# Une seule vague de messages par saison (pas de doublon).
w.generate_job_offers(c)
count = c.execute("SELECT COUNT(*) n FROM manager_message WHERE kind='job_offer'").fetchone()["n"]
assert count == len(offers), count
print("OK: pas de doublon de message SECRET")

# Famille de messagerie dédiée + badge.
assert w._message_category("job_offer") == "carriere"
badge, color, label = w._message_kind_meta("job_offer")
assert badge == "SE" and "SECRET" in label, (badge, label)
assert "carriere" in w.msg_categories
print("OK: famille carriere et badge SECRET")

# Refuser une offre clôt son message SECRET.
first_club = int(offers[0]["club_id"])
c.commit()
w._decline_job_offer(first_club)
closed = [m for m in c.execute("SELECT * FROM manager_message WHERE kind='job_offer'").fetchall()
          if int(json.loads(m["action_data"]).get("club_id") or 0) == first_club]
assert closed and all(m["status"] == "handled" and int(m["is_read"]) == 1 for m in closed), [dict(m) for m in closed]
print("OK: refus -> message SECRET clos")

archive(c, 10, "relegation")
offers = w.generate_job_offers(c)
assert offers == [], ("aucune offre apres relegation", offers)
row = c.execute("SELECT value FROM meta WHERE key='job_offers'").fetchone()
assert row and row["value"] == "[]", row
print("OK: relegation -> aucune offre")

archive(c, 8, "")
c.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('board_confidence','50')")
c.commit()
offers = w.generate_job_offers(c)
assert offers == [], ("saison moyenne sans confiance -> aucune offre", offers)
print("OK: saison moyenne -> aucune offre")
c.close()

w.close()
q.processEvents()
size = os.path.getsize(r"C:\FM2027V2\data\error.log")
print("error.log =", size, "octet(s)")
assert size == 0
print("RESULT: ALL OK")
