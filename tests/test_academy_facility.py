# -*- coding: utf-8 -*-
"""Centre de formation : jeunes <=18 du club uniquement ; gestion infrastructure lisible."""
import os, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication, QScrollArea

TMP = tempfile.mkdtemp(prefix="fm_acadfac_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP; app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=3,
            identity={"name": "AcadFac FC", "arena_name": "A", "color1": "#c47220",
                      "color2": "#14171f", "division": 3})
q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
w = app.MainWindow(); w.resize(900, 650); w.show()
w.app_stack.setCurrentWidget(w.game_shell); q.processEvents()
w.show_game_message = lambda *a, **k: True

c = app.db()
c.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('academy_unlocked','1')")
c.execute("UPDATE facility SET youth_level=3 WHERE id=1")
ids = [int(r["id"]) for r in c.execute("SELECT id FROM player WHERE club_id=1 ORDER BY id LIMIT 3").fetchall()]
for pid, age, first in zip(ids, (17, 18, 19), ("Jeune17", "Jeune18", "Ancien19")):
    c.execute("UPDATE player SET age=?,first_name=? WHERE id=?", (age, first, pid))
    c.execute("INSERT INTO player_history(player_id,season,club_id,kind,detail,created_at) VALUES(?,1,1,'formation','Formation — test','2026-07-01T00:00')", (pid,))
c.commit()
facility = c.execute("SELECT * FROM facility WHERE id=1").fetchone()
club = c.execute("SELECT * FROM club WHERE id=1").fetchone()

w.refresh_academy_youth()
rows = w.academy_youth_table.rowCount()
names = [w.academy_youth_table.item(i, 0).text() for i in range(rows)]
print("jeunes:", rows, names)
assert rows >= 2 and not any("Ancien19" in x for x in names)
assert any("Jeune17" in x for x in names) and any("Jeune18" in x for x in names)
w._refresh_academy_page(facility, club)
assert w.academy_youth_table.rowCount() >= 2
assert w.academy_kpi_formed.text() == "2"
assert w.academy_promo_panel.isHidden(), "le panneau des promotions reste masque sans promotion"

w.show_page(6); q.processEvents()
w.refresh_facility_panel(facility, club); q.processEvents()
gestion = w.facility_tabs.widget(1)
assert isinstance(gestion.layout().itemAt(0).widget(), QScrollArea), "GESTION doit etre defilante"
# En petite fenetre : une seule colonne de cartes.
if w.facility_buildings_grid.count() > 2:
    assert w.facility_buildings_grid.itemAtPosition(1, 1) is None
print("colonnes batiments:", [w.facility_buildings_grid.getItemPosition(i) for i in range(w.facility_buildings_grid.count())][:6])
c.close()
print("RESULT: ALL OK")
