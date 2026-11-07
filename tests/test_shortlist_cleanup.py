# -*- coding: utf-8 -*-
"""Shortlist : les joueurs recrutes par le club en sortent automatiquement."""
import os, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication

TMP = tempfile.mkdtemp(prefix="fm_shortclean_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP; app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=3,
            identity={"name": "Short FC", "arena_name": "A", "color1": "#c47220",
                      "color2": "#14171f", "division": 3})

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
w = app.MainWindow(); w.show()
w.show_game_message = lambda *a, **k: True
w.app_stack.setCurrentWidget(w.game_shell); q.processEvents()

c = app.db()
own = c.execute("SELECT id FROM player WHERE club_id=1 LIMIT 1").fetchone()["id"]
other = c.execute("SELECT id FROM player WHERE club_id<>1 LIMIT 1").fetchone()["id"]
for pid in (own, other):
    c.execute("INSERT OR REPLACE INTO shortlist(player_id,added_date,added_value,added_knowledge) VALUES(?,?,?,0)",
              (int(pid), "2026-08-01", 100000))
c.commit(); c.close()

removed = w.purge_shortlist_owned()
assert removed >= 1, removed
c = app.db()
ids = {int(r["player_id"]) for r in c.execute("SELECT player_id FROM shortlist").fetchall()}
c.close()
assert int(own) not in ids and int(other) in ids, ids
print("OK purge :", removed, "cible(s) du club retirée(s),", len(ids), "externe(s) conservée(s)")

# La lecture de la shortlist purge aussi les arrivals.
c = app.db(); c.execute("INSERT OR REPLACE INTO shortlist(player_id,added_date,added_value,added_knowledge) VALUES(?,?,?,0)", (int(own), "2026-08-01", 100000)); c.commit(); c.close()
rows = w.shortlist_rows()
assert all(int(r["id"]) != int(own) for r in rows)
print("OK shortlist_rows : aucune cible déjà recrutée")
print("RESULT: ALL OK")
