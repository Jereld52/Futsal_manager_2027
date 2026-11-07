# -*- coding: utf-8 -*-
"""Infrastructure : les chantiers ne doivent jamais faire redescendre un niveau."""
import os, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication

TMP = tempfile.mkdtemp(prefix="fm_facrepair_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP; app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=3,
            identity={"name": "Repair FC", "arena_name": "A", "color1": "#c47220",
                      "color2": "#14171f", "division": 3})

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
w = app.MainWindow(); w.show()
w.show_game_message = lambda *a, **k: True
w.app_stack.setCurrentWidget(w.game_shell); q.processEvents()

c = app.db()
c.execute("UPDATE facility SET arena_level=8 WHERE id=1")
c.execute("INSERT INTO facility_project(facility_key,label,target_level,cost,duration_days,start_date,due_date,status,completed_date) "
          "VALUES('arena_level','Tribunes niv. 9',9,1,1,'2032-09-01','2032-09-01','completed','2032-09-02')")
c.execute("INSERT INTO facility_project(facility_key,label,target_level,cost,duration_days,start_date,due_date,status) "
          "VALUES('arena_level','Tribunes niv. 2',2,1,1,'2032-09-03','2032-09-03','in_progress')")
c.commit(); c.close()

# Historique : on ne redescend pas de 8 à 2.
w._repair_facility_levels(app.db(), "2032-09-03")
c = app.db(); level = int(c.execute("SELECT arena_level FROM facility WHERE id=1").fetchone()["arena_level"]); c.close()
assert level == 8, level
print("OK réparation : niveau 8 conservé")

# Un chantier inférieur arrivé à échéance ne doit pas écraser le niveau.
c = app.db()
c.execute("INSERT INTO facility_project(facility_key,label,target_level,cost,duration_days,start_date,due_date,status) "
          "VALUES('arena_level','Tribunes niv. 2',2,1,1,'2032-09-03','2032-09-03','in_progress')")
c.commit()
w.process_facility_projects(c, "2032-09-03")
level = int(c.execute("SELECT arena_level FROM facility WHERE id=1").fetchone()["arena_level"]); c.close()
assert level == 8, level
print("OK process : aucun downgrade")

# Un niveau max refuse une nouvelle amélioration.
assert w.upgrade_facility("arena_level", 1, "Tribunes & capacité") is False
print("OK : amélioration refusée au niveau maximum")
print("RESULT: ALL OK")
