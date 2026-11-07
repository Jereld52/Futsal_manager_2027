# -*- coding: utf-8 -*-
"""Délégations étendues : entraînement, billetterie, veille du marché."""
import os, sys, tempfile
from datetime import timedelta
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication

TMP = tempfile.mkdtemp(prefix="fm_delegext_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP; app.BASE_DIR = TMP
app.OPTIONS_FILE = os.path.join(TMP, "options.json")
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=3,
            identity={"name": "Deleg FC", "arena_name": "A", "color1": "#c47220",
                      "color2": "#14171f", "division": 3})

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
w = app.MainWindow(); w.show(); w.show_game_message = lambda *a, **k: True

assert len(app.MainWindow.DELEGATION_TASKS) == 7
c = app.db()
for key in ("adjoint_hired", "preparateur_physique_hired", "comptable_hired", "scout_staff_hired"):
    c.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?, '1')", (key,))
c.execute("UPDATE club SET budget=2000000 WHERE id=1")
c.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('delegate_ticketing','1')")
c.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('delegate_scouting','1')")
c.commit()
current = c.execute('SELECT "current_date" FROM career WHERE id=1').fetchone()["current_date"]
# Prépare un match à domicile dans 3 jours et une cible sur le marché.
today = app.parse_iso(current)
home_date = (today + timedelta(days=3)).isoformat()
season = int(c.execute("SELECT season FROM club WHERE id=1").fetchone()["season"] or 1)
opp = c.execute("SELECT id FROM club WHERE id<>1 LIMIT 1").fetchone()["id"]
c.execute("INSERT INTO fixture(season,matchday,fixture_date,home_club_id,away_club_id,fixture_type,played) "
          "VALUES(?,?,?,?,?,'championship',0)", (season, 2, home_date, 1, int(opp)))
target = c.execute("SELECT id FROM player WHERE club_id<>1 AND COALESCE(retired,0)=0 LIMIT 1").fetchone()
c.execute("UPDATE player SET transfer_listed=1, market_value=50000 WHERE id=?", (int(target["id"]),))
c.execute("DELETE FROM shortlist")
c.commit()

# Entraînement : délégué au préparateur par défaut.
c.execute("DELETE FROM training_session WHERE completed=0")
c.execute("DELETE FROM meta WHERE key='delegate_training'")
c.commit()
assert w._delegation_active("training", c)
planned = w.auto_delegate_training(c, current)
c.commit()
count = c.execute("SELECT COUNT(*) n FROM training_session WHERE completed=0").fetchone()["n"]
assert planned >= 7 and count >= 7, (planned, count)
print("OK entraînement délégué par défaut :", count, "séances")

# Reprise en main : plus de planification automatique.
w._set_delegation("training", False, c); c.commit()
c.execute("DELETE FROM training_session WHERE completed=0"); c.commit()
assert w.auto_delegate_training(c, current) == 0
w._set_delegation("training", True, c); c.commit()

# Billetterie : le comptable applique le tarif conseillé.
c.execute("UPDATE facility SET ticket_price=7 WHERE id=1"); c.commit()
club = c.execute("SELECT reputation FROM club WHERE id=1").fetchone()
fac = c.execute("SELECT marketing_level FROM facility WHERE id=1").fetchone()
expected = max(5, min(35, 10 + int(club["reputation"] or 20) // 16 + int(fac["marketing_level"] or 1) // 2))
assert w.auto_delegate_ticket_price(c, current)
assert int(c.execute("SELECT ticket_price FROM facility WHERE id=1").fetchone()["ticket_price"]) == expected
print("OK billetterie déléguée :", expected, "€")

# Veille du marché : une cible ajoutée par semaine.
monday = today + timedelta(days=(7 - today.weekday()) % 7)
assert w.auto_delegate_scouting(c, monday.isoformat())
c.commit()
rows = c.execute("SELECT COUNT(*) n FROM shortlist").fetchone()["n"]
assert rows >= 1, rows
assert w.auto_delegate_scouting(c, monday.isoformat()) is False
print("OK veille du marché :", rows, "cible(s) épinglée(s)")
c.close()

# Tous les rôles présents : toutes les tâches sont débloquées.
w.show_page(10); w._staff_refresh(); q.processEvents()
assert all(btn.isEnabled() for btn in w.delegation_buttons.values())
print("RESULT: ALL OK")
