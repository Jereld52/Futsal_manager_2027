# -*- coding: utf-8 -*-
"""Centre de formation : options visibles, sans doublons et sans équipe première."""
import os, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication, QPushButton

TMP = tempfile.mkdtemp(prefix="fm_acadopt_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP; app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=3,
            identity={"name": "Options FC", "arena_name": "A", "color1": "#c47220",
                      "color2": "#14171f", "division": 3})

c = app.db()
c.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('academy_unlocked','1')")
c.execute("UPDATE club SET budget=1000000 WHERE id=1")
ids = [int(r["id"]) for r in c.execute("SELECT id FROM player WHERE club_id=1 ORDER BY id LIMIT 4").fetchall()]
for pid, age, first in zip(ids[:2], (16, 17), ("Centre16", "Centre17")):
    c.execute("UPDATE player SET age=?,first_name=? WHERE id=?", (age, first, pid))
    c.execute("INSERT INTO player_history(player_id,season,club_id,kind,detail,created_at) "
              "VALUES(?,1,1,'formation','Formation — test','2026-07-01T00:00')", (pid,))
c.execute("UPDATE player SET age=17,first_name='Premiere17' WHERE id=?", (ids[2],))
c.commit(); c.close()

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
w = app.MainWindow(); w.resize(1560, 900); w.show()
msgs = []
w.show_game_message = lambda *a, **k: msgs.append(a)
w.app_stack.setCurrentWidget(w.game_shell); q.processEvents()
w.show_page(13); q.processEvents()

assert len(w.academy_option_cards) == 8, len(w.academy_option_cards)
assert len(w.academy_dev_cards) == len(app.ACADEMY_DEV_PROJECTS) == 6
assert all(card.isVisible() for card in w.academy_option_cards)
assert not hasattr(w, "academy_dev_btn"), "l'ancien bouton caché ne doit plus exister"
print("OK options visibles :", len(w.academy_option_cards), "cartes")

# Les jeunes listés sont ceux formés au centre, pas les U18 de l'équipe première.
names = [w.academy_youth_table.item(i, 0).text() for i in range(w.academy_youth_table.rowCount())]
assert any("Centre16" in n for n in names) and any("Centre17" in n for n in names), names
assert not any("Premiere17" in n for n in names), names
print("OK jeunes du centre uniquement :", names)

# Aucune passerelle vers le staff de l'équipe première.
btns = [b.text().upper() for b in w.academy_options_panel.findChildren(QPushButton)]
page_btns = [b.text().upper() for b in w.stack.widget(13).findChildren(QPushButton)]
assert not any("STAFF" in t for t in page_btns), page_btns
assert hasattr(w, "academy_support_label") and "Soutien du club" in w.academy_support_label.text()
print("OK pas de mélange avec l'équipe première")

# Clic direct sur une option : l'école passe au niveau 1.
school = w.academy_dev_cards["school"]
assert school["button"].isEnabled()
assert "45 000" in school["button"].text(), school["button"].text()
school["button"].click(); q.processEvents()
c = app.db()
project = app.academy_dev_project(c)
lvl = app.academy_dev_levels(c).get("school", 0)
c.close()
assert project and project["key"] == "school" and project["target"] == 1, project
assert lvl == 0, lvl
assert school["pill"].text() == "NIV. 0→1", school["pill"].text()
print("OK chantier école lancé")
c = app.db()
c.execute('UPDATE career SET current_date=? WHERE id=1', (project["due"],))
c.commit(); c.close()
w._refresh_academy_dev_widgets(); q.processEvents()
c = app.db()
level = c.execute("SELECT value FROM meta WHERE key='academy_dev_school'").fetchone()
c.close()
assert level and int(level["value"]) == 1, level and level["value"]
assert school["pill"].text() == "NIV. 1/3", school["pill"].text()
print("OK école niveau 1 après livraison")

# Détection et moyens renforcés sont eux aussi sur la page.
assert hasattr(w, "academy_detection_btn") and w.academy_detection_btn.isVisible()
assert hasattr(w, "academy_boost_btn") and w.academy_boost_btn.isVisible()
print("OK détection et moyens renforcés visibles")
print("RESULT: ALL OK")
