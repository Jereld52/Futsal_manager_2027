# -*- coding: utf-8 -*-
"""Délégations staff : onglet, activation et exécution automatique."""
import os, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtTest import QTest

TMP = tempfile.mkdtemp(prefix="fm_deleg_")
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
c = app.db(); pid = int(c.execute("SELECT id FROM player WHERE club_id=1 ORDER BY id LIMIT 1").fetchone()["id"]); c.close()

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
w = app.MainWindow(); w.resize(1560, 900); w.show()
msgs = []
w.show_game_message = lambda *a, **k: msgs.append(a)
w.app_stack.setCurrentWidget(w.game_shell); q.processEvents()
w.show_page(10); QTest.qWait(250); q.processEvents()

assert w.staff_tabs.count() == 2
assert [w.staff_tabs.tabText(i) for i in range(w.staff_tabs.count())] == ["EFFECTIF", "DÉLÉGATIONS"]
assert all(not btn.isEnabled() for btn in w.delegation_buttons.values())
print("OK onglet délégations : verrouillé sans adjoint")

# Adjoint recruté : les délégations se débloquent.
c = app.db()
c.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('adjoint_hired','1')")
c.commit(); c.close()
w._staff_refresh(); q.processEvents()
adjoint_tasks={"prematch_talk","halftime_talk","postmatch_interview","lineup"}
for key,btn in w.delegation_buttons.items():
    assert btn.isEnabled()==(key in adjoint_tasks),(key,btn.isEnabled())
w._toggle_staff_delegation("prematch_talk")
c = app.db(); val = c.execute("SELECT value FROM meta WHERE key='delegate_prematch_talk'").fetchone(); c.close()
assert val and val["value"] == "1"
assert w.delegation_buttons["prematch_talk"].text() == "DÉLÉGUÉ"
print("OK délégation avant-match activée")

# La causerie ne doit plus ouvrir de dialogue : l'adjoint choisit.
original_exec = app.QDialog.exec
app.QDialog.exec = lambda *a, **k: (_ for _ in ()).throw(AssertionError("dialogue inattendu"))
w._current_derby = False
w._show_prematch_talk(None)
assert w._prematch_mods, "l'adjoint doit avoir appliqué une causerie"
app.QDialog.exec = original_exec
print("OK causerie avant-match déléguée :", w._prematch_mods)

# Mi-temps déléguée.
w._set_delegation("halftime_talk", True)
w.match_state = {"lineup": [{"id": pid}], "conditions": {pid: 70}, "momentum": -2,
                 "hg": 0, "ag": 1, "is_home": True, "minute": 20}
w._halftime_dialog = None
w._show_halftime_talk()
assert w.match_state["talk_mods"], "l'adjoint doit avoir parlé à la mi-temps"
assert w._halftime_dialog is None
print("OK causerie mi-temps déléguée :", w.match_state["talk_mods"])

# Interview déléguée.
w._set_delegation("postmatch_interview", True)
app.QDialog.exec = lambda *a, **k: (_ for _ in ()).throw(AssertionError("dialogue inattendu"))
msgs.clear()
w._show_postmatch_interview({"outcome": "VICTOIRE"}, {"hg": 3, "ag": 1, "is_home": True})
app.QDialog.exec = original_exec
assert msgs and "Interview" in msgs[-1][0]
print("OK interview déléguée :", msgs[-1][1][:60])

# Reprendre la main.
w._toggle_staff_delegation("prematch_talk")
c = app.db(); val = c.execute("SELECT value FROM meta WHERE key='delegate_prematch_talk'").fetchone(); c.close()
assert val and val["value"] == "0"
assert w.delegation_buttons["prematch_talk"].text() == "JE GÈRE"
print("OK reprise en main")
print("RESULT: ALL OK")
