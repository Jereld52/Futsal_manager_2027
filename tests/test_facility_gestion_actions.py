# -*- coding: utf-8 -*-
"""Infrastructure > Gestion : les cartes réagissent et lancent vraiment les chantiers."""
import os, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication, QPushButton, QLabel

TMP = tempfile.mkdtemp(prefix="fm_facact_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP; app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=3,
            identity={"name": "Actions FC", "arena_name": "A", "color1": "#c47220",
                      "color2": "#14171f", "division": 3})

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
w = app.MainWindow(); w.resize(1560, 900); w.show()
msgs = []
w.show_game_message = lambda *a, **k: msgs.append(a)
w.app_stack.setCurrentWidget(w.game_shell); q.processEvents()
w.show_page(5); q.processEvents()
w.facility_tabs.setCurrentIndex(1); q.processEvents()
c = app.db(); c.execute("UPDATE club SET budget=2000000 WHERE id=1"); c.commit(); c.close()


def refresh():
    c = app.db()
    club = c.execute("SELECT * FROM club WHERE id=1").fetchone()
    fac = c.execute("SELECT * FROM facility WHERE id=1").fetchone()
    c.close()
    w.refresh_facility_panel(fac, club); q.processEvents()


refresh()


def find_card(grid, needle):
    for i in range(grid.count()):
        card = grid.itemAt(i).widget()
        if card is None:
            continue
        labels = [l.text() for l in card.findChildren(QLabel)]
        if any(needle.lower() in str(t).lower() for t in labels):
            return card
    return None


restaurant = find_card(w.facility_services_grid, "Restaurant")
assert restaurant is not None
button = restaurant.findChild(QPushButton)
assert button is not None and button.isEnabled(), (button.text() if button else None)
button.click(); q.processEvents()
c = app.db()
row = c.execute("SELECT status,target_level FROM facility_project WHERE facility_key='restaurant_level' "
                "ORDER BY id DESC LIMIT 1").fetchone()
bar = c.execute("SELECT restaurant_level FROM facility WHERE id=1").fetchone()
c.close()
assert row and row["status"] == "in_progress" and int(row["target_level"]) == 1, row and dict(row)
assert int(bar["restaurant_level"] or 0) == 0
print("OK restaurant lancé par le bouton :", dict(row))

# Places saturées : le bouton reste réactif et explique le blocage.
refresh()
arena = find_card(w.facility_buildings_grid, "Tribunes")
assert arena is not None
arena_btn = arena.findChild(QPushButton)
assert arena_btn is not None and arena_btn.isEnabled(), arena_btn.text() if arena_btn else None
msgs.clear()
arena_btn.click(); q.processEvents()
assert any("satur" in str(m[0]).lower() or "satur" in str(m[1]).lower() for m in msgs), msgs
print("OK refus expliqué :", msgs[-1][0])

# Budget insuffisant : clic -> message clair, pas de chantier fantôme.
w.facility_invest_tabs.setCurrentIndex(1); q.processEvents()
c = app.db(); c.execute("UPDATE club SET budget=0 WHERE id=1")
c.execute("UPDATE facility_project SET status='completed' WHERE status='in_progress'")
c.commit(); c.close()
refresh()
vol = find_card(w.facility_divers_grid, "bénévoles")
assert vol is not None
vol_btn = vol.findChild(QPushButton)
assert vol_btn is not None and vol_btn.isEnabled(), vol_btn.text() if vol_btn else None
msgs.clear()
vol_btn.click(); q.processEvents()
assert any("budget" in str(m[0]).lower() for m in msgs), msgs
c = app.db(); bad = c.execute("SELECT COUNT(*) n FROM facility_project WHERE facility_key='volunteer_level' AND status='in_progress'").fetchone()["n"]; c.close()
assert bad == 0
print("OK budget insuffisant :", msgs[-1][0])
print("RESULT: ALL OK")
