# -*- coding: utf-8 -*-
"""Infrastructure : labo vidéo, centre des bénévoles et restaurant."""
import os, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication

TMP = tempfile.mkdtemp(prefix="fm_newbuild_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP; app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=3,
            identity={"name": "NewBuild FC", "arena_name": "A", "color1": "#c47220",
                      "color2": "#14171f", "division": 3})

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
w = app.MainWindow(); w.resize(1560, 900); w.show()
w.show_game_message = lambda *a, **k: True
w.app_stack.setCurrentWidget(w.game_shell); q.processEvents()
w.show_page(5); q.processEvents()
w.facility_tabs.setCurrentIndex(1); q.processEvents()

assert [w.facility_invest_tabs.tabText(i) for i in range(w.facility_invest_tabs.count())] == ["BÂTIMENTS", "SERVICES", "REVENUS"]
assert w.facility_buildings_grid.count() == 7
assert w.facility_services_grid.count() == 4
assert w.facility_divers_grid.count() == 4
print("OK onglets investissement et cartes :", 7, 4, 4)

c = app.db()
c.execute("UPDATE facility SET video_level=2,volunteer_level=2,restaurant_level=2 WHERE id=1")
c.commit()
club = c.execute("SELECT * FROM club WHERE id=1").fetchone()
fac = c.execute("SELECT * FROM facility WHERE id=1").fetchone()
opp = c.execute("SELECT id FROM club WHERE id<>1 LIMIT 1").fetchone()["id"]
c.close()

parts = w.facility_matchday_revenue(club, fac, 1000, 10)
assert parts["restaurant"] == 2400, parts["restaurant"]
assert parts["total"] >= parts["restaurant"]
report = w.video_analysis_for_opponent(opp, 2)
assert "LABO VIDÉO niv. 2" in report and "forme" in report, report
print("OK restaurant :", parts["restaurant"], "€ |", report[:80])

assert w.facility_upgrade_terms("video_level", 0)[0] > 0

# Régression : les nouveaux chantiers doivent vraiment démarrer.
c = app.db()
c.execute("UPDATE club SET budget=5000000 WHERE id=1")
c.execute("UPDATE facility SET video_level=0,volunteer_level=0,restaurant_level=0 WHERE id=1")
c.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('architecte_hired','1')")
c.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('architecte_level','3')")
c.commit(); c.close()
for key, label in (("video_level", "Laboratoire vidéo"),
                   ("volunteer_level", "Centre des bénévoles"),
                   ("restaurant_level", "Restaurant & food truck")):
    cost = w.facility_upgrade_terms(key, 0)[0]
    assert w.start_facility_project(key, cost, label, 1, 10), key
c = app.db()
rows = {r["facility_key"]: r for r in c.execute(
    "SELECT facility_key,status,target_level FROM facility_project WHERE status='in_progress'").fetchall()}
c.close()
for key in ("video_level", "volunteer_level", "restaurant_level"):
    assert rows.get(key) and rows[key]["status"] == "in_progress", (key, rows.get(key))
print("OK lancement des nouveaux chantiers :", sorted(rows))
print("RESULT: ALL OK")
