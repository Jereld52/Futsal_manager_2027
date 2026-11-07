# -*- coding: utf-8 -*-
"""Arène : récupération du niveau perdu et blocage des chantiers niv. 2 fantômes."""
import os, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication

TMP = tempfile.mkdtemp(prefix="fm_arenarepair_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP; app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=3,
            identity={"name": "Arena Repair FC", "arena_name": "A", "color1": "#c47220",
                      "color2": "#14171f", "division": 3})
q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
w = app.MainWindow(); w.show()
w.show_game_message = lambda *a, **k: True
w.app_stack.setCurrentWidget(w.game_shell); q.processEvents()

c = app.db()
c.execute("UPDATE club SET budget=5000000 WHERE id=1")
c.execute("UPDATE facility SET arena_level=2 WHERE id=1")
c.execute("DELETE FROM facility_project")
c.execute("INSERT INTO facility_project(facility_key,label,target_level,cost,duration_days,start_date,due_date,status,completed_date) "
          "VALUES('arena_level','Tribunes niv. 2',2,1,1,'2032-09-03','2032-09-03','completed','2032-09-04')")
c.execute("INSERT INTO finance_tx(club_id,label,amount,created_at,category) "
          "VALUES(1,'Début chantier • Tribunes & capacité',-2442000,'2031-07-03T23:10','Infrastructure')")
c.commit()
w._repair_facility_levels(c, "2032-11-25"); c.commit()
level = int(c.execute("SELECT arena_level FROM facility WHERE id=1").fetchone()["arena_level"])
assert level == 8, level
print("OK récupération arène : 2 -> 8 depuis les paiements de chantier")

before = c.execute("SELECT COUNT(*) n FROM facility_project").fetchone()["n"]
assert w.start_facility_project("arena_level", 1, "Tribunes niv. 2", 2, 1) is False
after = c.execute("SELECT COUNT(*) n FROM facility_project").fetchone()["n"]
assert before == after, (before, after)
print("OK garde-fou : aucun chantier niv. 2 relancé")

# Un ancien chantier actif niv. 2 ne doit plus produire d'actualité ni baisser l'arène.
c.execute("INSERT INTO facility_project(facility_key,label,target_level,cost,duration_days,start_date,due_date,status) "
          "VALUES('arena_level','Tribunes niv. 2',2,1,1,'2032-09-03','2032-09-03','in_progress')")
c.commit()
news_before = c.execute("SELECT COUNT(*) n FROM news WHERE body LIKE '%Tribunes niv. 2%'").fetchone()["n"]
w.process_facility_projects(c, "2032-11-25"); c.commit()
level = int(c.execute("SELECT arena_level FROM facility WHERE id=1").fetchone()["arena_level"])
active = c.execute("SELECT COUNT(*) n FROM facility_project WHERE facility_key='arena_level' AND status='in_progress'").fetchone()["n"]
news_after = c.execute("SELECT COUNT(*) n FROM news WHERE body LIKE '%Tribunes niv. 2%'").fetchone()["n"]
c.close()
assert level == 8 and active == 0, (level, active)
assert news_after == news_before, (news_before, news_after)
print("OK process : niveau 8 conservé, doublon neutralisé sans actualité")

# Sauvegarde où l'historique financier a été purgé : les actualités suffisent.
c = app.db()
c.execute("DELETE FROM facility_project")
c.execute("DELETE FROM finance_tx WHERE label LIKE '%Tribunes%'")
c.execute("UPDATE facility SET arena_level=1 WHERE id=1")
c.execute("INSERT INTO news(title,body,created_at) VALUES('Nouveau chantier',?, '2031-07-03T23:10')",
          ("Tribunes & capacité démarre pour 2 442 000 € • durée prévue : 261 jours • livraison le 20/03/2032.",))
c.execute("INSERT INTO facility_project(facility_key,label,target_level,cost,duration_days,start_date,due_date,status) "
          "VALUES('arena_level','Tribunes niv. 2',2,1,1,'2032-11-25','2032-11-30','in_progress')")
c.commit()
w._repair_facility_levels(c, "2032-11-25"); c.commit()
level = int(c.execute("SELECT arena_level FROM facility WHERE id=1").fetchone()["arena_level"])
active = c.execute("SELECT COUNT(*) n FROM facility_project WHERE facility_key='arena_level' AND status='in_progress'").fetchone()["n"]
assert level == 8 and active == 0, (level, active)
print("OK actualités seules : arène 8 récupérée, chantier niv. 2 neutralisé")

# Motif de corruption : plusieurs « Tribunes niv. 2 » sans trace financière.
c = app.db()
c.execute("DELETE FROM facility_project")
c.execute("DELETE FROM finance_tx WHERE label LIKE '%Tribunes%'")
c.execute("DELETE FROM news WHERE body LIKE '%Tribunes%'")
c.execute("DELETE FROM meta WHERE key='facility_max_arena_level'")
c.execute("UPDATE facility SET arena_level=1, medical_level=8, youth_level=8, marketing_level=8, "
          "lighting_level=8, parking_level=8 WHERE id=1")
for _i in range(2):
    c.execute("INSERT INTO manager_message(kind,title,body,created_date,due_date,status,action_data,is_read) "
              "VALUES('club_news','Chantier terminé','Tribunes niv. 2 est terminé et opérationnel.','2032-11-25','2032-11-25','ready','{}',0)")
c.execute("INSERT INTO facility_project(facility_key,label,target_level,cost,duration_days,start_date,due_date,status) "
          "VALUES('arena_level','Tribunes niv. 2',2,1,1,'2032-11-25','2032-11-30','in_progress')")
c.commit()
w._repair_facility_levels(c, "2032-11-25"); c.commit()
level = int(c.execute("SELECT arena_level FROM facility WHERE id=1").fetchone()["arena_level"])
active = c.execute("SELECT COUNT(*) n FROM facility_project WHERE facility_key='arena_level' AND status='in_progress'").fetchone()["n"]
assert level == 8 and active == 0, (level, active)
print("OK motif corruption : arène 8 restaurée, chantier niv. 2 neutralisé")

# Un chantier supérieur encore en cours ne doit pas être appliqué par anticipation.
c = app.db()
c.execute("DELETE FROM facility_project")
c.execute("DELETE FROM meta WHERE key='facility_max_arena_level'")
c.execute("UPDATE facility SET arena_level=5 WHERE id=1")
c.execute("INSERT INTO facility_project(facility_key,label,target_level,cost,duration_days,start_date,due_date,status) "
          "VALUES('arena_level','Tribunes & capacité niv. 8',8,2442000,1,'2032-11-25','2032-11-25','in_progress')")
c.commit()
w._repair_facility_levels(c, "2032-11-25"); c.commit()
level = int(c.execute("SELECT arena_level FROM facility WHERE id=1").fetchone()["arena_level"])
assert level == 5, level
w.process_facility_projects(c, "2032-11-25"); c.commit()
level = int(c.execute("SELECT arena_level FROM facility WHERE id=1").fetchone()["arena_level"])
c.close()
assert level == 8, level
print("OK chantier en cours : niveau appliqué seulement à la livraison")
print("RESULT: ALL OK")
