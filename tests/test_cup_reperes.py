# -*- coding: utf-8 -*-
"""Coupe : le bloc reperes suit les tours (KPI, exemptes, petit poucet)."""
import os, sys, tempfile, re
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication

TMP = tempfile.mkdtemp(prefix="fm_cuprep_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP
app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=3,
            identity={"name": "Coupe FC", "arena_name": "A", "color1": "#2f6fed",
                      "color2": "#101a2e", "division": 3, "difficulty": "Normal"})
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
q.processEvents()
w.app_stack.setCurrentWidget(w.game_shell)
q.processEvents()

c = app.db()
season = int(c.execute("SELECT season FROM club WHERE id=1").fetchone()["season"])
today = c.execute('SELECT "current_date" FROM career WHERE id=1').fetchone()["current_date"]
app.ensure_cup_fixtures(c, season, today)
c.commit()


def round_fixtures(conn, md):
    return conn.execute("SELECT * FROM fixture WHERE season=? AND fixture_type='cup' AND matchday=?",
                        (season, md)).fetchall()


def play_round(conn, md):
    rows = round_fixtures(conn, md)
    assert rows, "tour %s absent" % md
    for f in rows:
        conn.execute("UPDATE fixture SET played=1, home_goals=3, away_goals=1 WHERE id=?", (int(f["id"]),))
    conn.commit()
    app.ensure_cup_progress(conn, today)
    conn.commit()


slots = int(c.execute("SELECT value FROM meta WHERE key=?", ("cup_slots_%s" % season,)).fetchone()["value"])
total = max(1, slots.bit_length() - 1)
assert total == 6, (slots, total)
print("OK: tableau a", slots, "places ->", total, "tours")

# Tour 1 -> tour 2
play_round(c, 101)
assert round_fixtures(c, 102), "le 2e tour n'a pas ete tire"
w.refresh_cup_page()
q.processEvents()
assert w.cup_kpi_round.text().startswith(f"2/{total}"), w.cup_kpi_round.text()
assert "D'ENTRÉE" in w.cup_byes_label.text(), w.cup_byes_label.text()
print("OK: tour 2/6 |", w.cup_kpi_round.text(), "|", w.cup_byes_label.text())

# Tour 2 -> tour 3 : les exemptes ne doivent plus etre ajoutes aux survivants
play_round(c, 102)
r3 = round_fixtures(c, 103)
assert r3, "le 3e tour n'a pas ete tire"
alive = len({int(f["home_club_id"]) for f in r3} | {int(f["away_club_id"]) for f in r3})
w.refresh_cup_page()
q.processEvents()
assert w.cup_kpi_round.text().startswith(f"3/{total}"), w.cup_kpi_round.text()
assert w.cup_kpi_matches.text() == str(len(r3)), (w.cup_kpi_matches.text(), len(r3))
sub = w.cup_minnow_sub.text()
counted = sum(int(n) for n in re.findall(r"×(\d+)", sub))
assert counted == alive, (counted, alive, sub)
if "encore en lice au" in w.cup_minnow_label.text():
    assert "8es" in w.cup_minnow_label.text(), w.cup_minnow_label.text()
print("OK: tour 3/6 | survivants", counted, "=", alive, "|", w.cup_minnow_label.text())

# Deroule jusqu'a la finale
for md in (103, 104, 105, 106):
    play_round(c, md)
c.close()
w.refresh_cup_page()
q.processEvents()
print("finale |", w.cup_kpi_round.text(), "|", w.cup_banner.text(), "|", w.cup_kpi_status.text())
assert "TERMINÉE" in w.cup_banner.text(), w.cup_banner.text()
assert w.cup_kpi_status.text() in ("VAINQUEUR", "ÉLIMINÉ"), w.cup_kpi_status.text()
assert "COUPE TERMINÉE" in w.cup_minnow_label.text(), w.cup_minnow_label.text()
assert "D'ENTRÉE" in w.cup_byes_label.text(), w.cup_byes_label.text()
print("OK: fin de coupe |", w.cup_minnow_label.text())

# Bilan de coupe : message avec parcours et primes, une seule fois.
w.ensure_cup_recap(); q.processEvents()
c = app.db()
msg = c.execute("SELECT title,body FROM manager_message WHERE title LIKE 'Coupe Inter-Ligue%' ORDER BY id DESC LIMIT 1").fetchone()
count = c.execute("SELECT COUNT(*) n FROM manager_message WHERE title LIKE 'Coupe Inter-Ligue%'").fetchone()["n"]
c.close()
assert msg and "Primes du parcours" in msg["body"], msg
assert msg["title"] in ("Coupe Inter-Ligue • VAINQUEUR",) or "ÉLIMINÉ" in msg["title"], msg["title"]
w.ensure_cup_recap(); q.processEvents()
c = app.db()
count2 = c.execute("SELECT COUNT(*) n FROM manager_message WHERE title LIKE 'Coupe Inter-Ligue%'").fetchone()["n"]
c.close()
assert count2 == count == 1, (count, count2)
print("OK: bilan de coupe |", msg["title"])

w.close()
q.processEvents()
size = os.path.getsize(r"C:\FM2027V2\data\error.log")
print("error.log =", size, "octet(s)")
assert size == 0
print("RESULT: ALL OK")
