# -*- coding: utf-8 -*-
"""Changement de club : messagerie videe, elements du nouveau club, accueil."""
import os, sys, tempfile, json
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication

TMP = tempfile.mkdtemp(prefix="fm_clubchange_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP
app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=1,
            identity={"name": "Ancien FC", "arena_name": "Vieille salle",
                      "color1": "#2f6fed", "color2": "#101a2e",
                      "division": 1, "difficulty": "Normal"})
try:
    open(r"C:\FM2027V2\data\error.log", "r+b").truncate(0)
except FileNotFoundError:
    open(r"C:\FM2027V2\data\error.log", "wb").close()

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
w = app.MainWindow()
w.show_game_message = lambda *a, **k: True
w.resize(1400, 900)
w.show()
w.app_stack.setCurrentWidget(w.game_shell)
q.processEvents()

# --- Etat « ancien club » a nettoyer ---
conn = app.db()
target = conn.execute("SELECT * FROM club WHERE id<>1 AND division>=4 ORDER BY id LIMIT 1").fetchone()
assert target is not None, "aucun club de division basse pour le test"
est, _ = w.club_facility_profile(target)
conn.execute("INSERT INTO manager_message(kind,title,body,created_date,due_date,status,action_data,is_read) "
             "VALUES('club_news','Ancien message','vieux','2026-07-01','2026-07-01','waiting','{}',0)")
conn.execute("INSERT INTO manager_message(kind,title,body,created_date,due_date,status,action_data,is_read) "
             "VALUES('match_report','Ancien rapport','vieux','2026-07-02','2026-07-02','handled','{}',1)")
conn.execute("INSERT INTO manager_message_archive(kind,title,body,created_date,due_date,status,action_data,is_read,archived_date) "
             "VALUES('club_news','Archive','vieux','2026-06-01','2026-06-01','handled','{}',1,'2026-06-02')")
conn.execute("INSERT INTO news(title,body,created_at) VALUES('Ancienne actu','vieux','2026-07-01T10:00')")
conn.execute("INSERT INTO facility_project(facility_key,label,target_level,cost,duration_days,start_date,due_date,status) "
             "VALUES('arena_level','Tribunes',9,100000,30,'2026-07-01','2026-07-31','in_progress')")
conn.execute("INSERT INTO loan(principal,rate_bps,weekly_due,term_weeks,weeks_paid,start_date,next_due_date,status,label) "
             "VALUES(500000,250,5000,52,10,'2026-07-01','2026-07-08','active','Pret bancaire')")
for key, value in (("sponsor_deal", '{"name":"Vieux Sponsor"}'), ("sponsor_used_season", "7"),
                   ("academy_unlocked", "1"), ("academy_invest_season", "7"),
                   ("academy_last_detection", "2026-09-01"), ("rival_club_id", "4")):
    conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)", (key, value))
conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('job_offers',?)",
             (json.dumps([{"club_id": int(target["id"]), "name": target["name"],
                           "division": int(target["division"]), "reason": "nouveau projet"}]),))
conn.commit()
conn.close()

w._accept_job_offer(int(target["id"]), str(target["name"]))
q.processEvents()

conn = app.db()
club = conn.execute("SELECT * FROM club WHERE id=1").fetchone()
msgs = conn.execute("SELECT * FROM manager_message").fetchall()
arch = conn.execute("SELECT COUNT(*) n FROM manager_message_archive").fetchone()["n"]
news = conn.execute("SELECT * FROM news").fetchall()
works = conn.execute("SELECT COUNT(*) n FROM facility_project").fetchone()["n"]
loans = conn.execute("SELECT COUNT(*) n FROM loan").fetchone()["n"]
meta = {k: (conn.execute("SELECT value FROM meta WHERE key=?", (k,)).fetchone() or [None])[0]
        for k in ("sponsor_deal", "sponsor_used_season", "academy_invest_season",
                  "academy_last_detection", "academy_unlocked", "rival_club_id",
                  "board_objective_label", "job_offers",
                  "facility_max_arena_level", "facility_max_medical_level")}
facility = conn.execute("SELECT * FROM facility WHERE id=1").fetchone()
conn.close()

assert club["name"] == target["name"], (club["name"], target["name"])
print("OK: club bascule ->", club["name"])
assert len(msgs) == 1 and msgs[0]["kind"] == "club_news", [(m["kind"], m["title"]) for m in msgs]
assert "Bienvenue" in msgs[0]["title"] and club["name"] in msgs[0]["body"]
assert "messagerie" in msgs[0]["body"].lower()
assert int(msgs[0]["is_read"]) == 0
print("OK: messagerie videe + message de bienvenue :", msgs[0]["title"])
assert arch == 0, arch
assert len(news) == 1 and news[0]["title"] == "Nouveau club", [(n["title"]) for n in news]
print("OK: archives et actualites de l'ancien club effacees")
assert works == 0 and loans == 0, (works, loans)
assert meta["sponsor_deal"] is None and meta["sponsor_used_season"] is None
assert meta["academy_invest_season"] is None and meta["academy_last_detection"] is None
assert meta["rival_club_id"] is None or int(meta["rival_club_id"]) != 1
print("OK: sponsors et centre de formation remis a zero | rival recalcule :", meta["rival_club_id"])
assert meta["job_offers"] is None
print("OK: prets, chantiers et offres remis a zero")
for _col in ("arena_level", "medical_level", "youth_level", "marketing_level",
             "lighting_level", "parking_level", "has_bar", "has_vip", "has_shop",
             "has_rental_courts", "has_events_hall", "has_fan_zone",
             "video_level", "volunteer_level", "restaurant_level"):
    assert int(facility[_col]) == int(est[_col]), (_col, dict(facility), est)
assert int(meta["facility_max_arena_level"]) == int(est["arena_level"]), (meta, est)
assert int(meta["facility_max_medical_level"]) == int(est["medical_level"]), (meta, est)
print("OK: installations du nouveau club :", dict(facility))
assert meta["board_objective_label"], meta
print("OK: objectif du board :", meta["board_objective_label"])

w.show_page(6)
q.processEvents()
w._refresh_messages_ui()
q.processEvents()
assert getattr(w, "mail_club_name", None) == club["name"], (getattr(w, "mail_club_name", None), club["name"])
assert w._mail_slug(club["name"]) in w.mail_club_address, (w.mail_club_address, club["name"])
print("OK: messagerie re-identifiee :", w.mail_club_name, "|", w.mail_club_address)

w.close()
q.processEvents()
size = os.path.getsize(r"C:\FM2027V2\data\error.log")
print("error.log =", size, "octet(s)")
assert size == 0
print("RESULT: ALL OK")
