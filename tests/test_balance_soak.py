# -*- coding: utf-8 -*-
"""Test d'équilibrage : une saison simulée, seuils buts/match, effectif, budget."""
import os, sys, tempfile, time
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app

TMP = tempfile.mkdtemp(prefix="fm_balance_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP; app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=2,
            identity={"name": "Arbot Futsal", "arena_name": "A", "color1": "#c47220",
                      "color2": "#14171f", "division": 2})

from PySide6.QtWidgets import QApplication
q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
w = app.MainWindow(); w.resize(1400, 900); w.show()
w.app_stack.setCurrentWidget(w.game_shell); q.processEvents()
w.show_game_message = lambda *a, **k: True
app.QDialog.exec = lambda self, *a, **k: 1

def snapshot():
    c = app.db()
    try:
        row = c.execute("SELECT SUM(home_goals+away_goals) g, COUNT(*) n FROM fixture WHERE played=1").fetchone()
        return int(row["n"] or 0), int(row["g"] or 0)
    finally:
        c.close()

days = 300
errors = []
played = 0
total_matches = 0; total_goals = 0
prev_m, prev_g = snapshot()
t0 = time.perf_counter()
for step in range(days):
    try:
        c = app.db()
        fx = w._today_fixture_for_user(c)
        ready = c.execute("SELECT value FROM meta WHERE key='season_ready'").fetchone()
        c.close()
        if ready and str(ready["value"]) == "1":
            w.start_new_season(); q.processEvents()
        elif fx:
            w.start_match(); q.processEvents()
            w.finish_match_now(); q.processEvents(); played += 1
        else:
            w.advance_calendar_days(1); q.processEvents()
    except Exception as exc:
        errors.append(f"{step}:{exc!r}")
        if len(errors) <= 3: print("ERREUR:", repr(exc))
    try:
        m, g = snapshot()
        dm, dg = m - prev_m, g - prev_g
        if dm > 0:
            total_matches += dm; total_goals += max(0, dg)
        prev_m, prev_g = m, g
    except Exception:
        pass
dt = time.perf_counter() - t0

c = app.db()
squad = c.execute("SELECT COUNT(*) n FROM player WHERE club_id=1 AND COALESCE(is_free_agent,0)=0").fetchone()["n"]
budget = c.execute("SELECT budget FROM club WHERE id=1").fetchone()["budget"]
date_now = c.execute('SELECT "current_date" d FROM career WHERE id=1').fetchone()["d"]
season = c.execute("SELECT season FROM club WHERE id=1").fetchone()["season"]
c.close()
per = (float(total_goals) / max(1, total_matches))
print(f"jours={days} matchs_joues={played} duree={dt:.1f}s date={date_now} saison={season}")
print(f"matchs_simules={total_matches} buts/match={per:.2f} effectif={squad} budget={int(budget or 0):,}")
print(f"erreurs={len(errors)}")
assert not errors, "erreurs pendant le soak : " + " | ".join(errors[:3])
assert total_matches >= 120, f"trop peu de matchs simulés ({total_matches})"
assert 2.0 <= per <= 7.5, f"buts/match hors seuil ({per:.2f})"
assert 11 <= squad <= 22, f"effectif hors seuil ({squad})"
assert -5_000_000 <= int(budget or 0) <= 15_000_000, f"budget hors seuil ({budget})"
print("RESULT: ALL OK")
