# -*- coding: utf-8 -*-
"""Coaching et interviews : plus d'options et effets réels."""
import os, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication

TMP = tempfile.mkdtemp(prefix="fm_coaching_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP; app.BASE_DIR = TMP
app.OPTIONS_FILE = os.path.join(TMP, "options.json")
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=3,
            identity={"name": "Coaching FC", "arena_name": "A", "color1": "#c47220",
                      "color2": "#14171f", "division": 3})

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
w = app.MainWindow(); w.show()
msgs = []
w.show_game_message = lambda *a, **k: msgs.append(a)

assert len(app.PREMATCH_TALKS) >= 6
assert len(app.HALFTIME_TALKS) >= 6
assert all(len(app.POSTMATCH_ANSWERS[k]) >= 5 for k in ("VICTOIRE", "NUL", "DÉFAITE"))
print("OK options :", len(app.PREMATCH_TALKS), "avant-match |", len(app.HALFTIME_TALKS), "mi-temps |",
      {k: len(v) for k, v in app.POSTMATCH_ANSWERS.items()})

c = app.db(); pid = int(c.execute("SELECT id FROM player WHERE club_id=1 ORDER BY id LIMIT 1").fetchone()["id"])
before = c.execute("SELECT morale,condition FROM player WHERE id=?", (pid,)).fetchone()
c.close()

w._apply_prematch_talk("sangfroid")
assert abs(w._prematch_mods.get("attack", 1) - 1.015) < 1e-6
assert abs(w._prematch_mods.get("defense", 1) - 1.015) < 1e-6
c = app.db(); after = c.execute("SELECT morale,condition FROM player WHERE id=?", (pid,)).fetchone(); c.close()
assert int(after["condition"]) == min(100, int(before["condition"]) + 1)
print("OK causerie sang-froid :", w._prematch_mods)

# Derby : bonus de moral supplémentaire.
c = app.db(); morale0 = int(c.execute("SELECT morale FROM player WHERE id=?", (pid,)).fetchone()["morale"]); c.close()
w._apply_prematch_talk("pression", derby=True)
c = app.db(); morale1 = int(c.execute("SELECT morale FROM player WHERE id=?", (pid,)).fetchone()["morale"]); c.close()
assert morale1 == min(100, morale0 + 3), (morale0, morale1)
print("OK derby : moral", morale0, "->", morale1)

# Mi-temps : bloc bas protège le résultat.
w.match_state = {"lineup": [{"id": pid}], "conditions": {pid: 70}, "momentum": 0,
                 "hg": 1, "ag": 2, "is_home": True, "minute": 20}
w._apply_halftime_talk("bloc")
assert w.match_state["talk_mods"].get("defense") == 1.05
assert w.match_state["momentum"] == -6
assert w.match_state["conditions"][pid] == 70
print("OK mi-temps bloc bas :", w.match_state["talk_mods"], "momentum", w.match_state["momentum"])

# Interview : les supporters et le moral bougent vraiment.
c = app.db()
fan0 = int((c.execute("SELECT value FROM meta WHERE key='fan_confidence'").fetchone() or {"value": 55})["value"] or 55)
c.close()
w._apply_postmatch_answer("supporters", "VICTOIRE")
c = app.db()
fan1 = int(c.execute("SELECT value FROM meta WHERE key='fan_confidence'").fetchone()["value"])
c.close()
assert fan1 == min(100, fan0 + 4), (fan0, fan1)
assert msgs and "supporters" in msgs[-1][1].lower()
print("OK interview : supporters", fan0, "->", fan1)

# Chaque résultat a ses réponses propres.
assert any(a["key"] == "assumer" for a in app.POSTMATCH_ANSWERS["DÉFAITE"])
assert any(a["key"] == "adversaire" for a in app.POSTMATCH_ANSWERS["VICTOIRE"])
assert any(a["key"] == "travail" for a in app.POSTMATCH_ANSWERS["NUL"])
w.match_state = None
print("RESULT: ALL OK")
