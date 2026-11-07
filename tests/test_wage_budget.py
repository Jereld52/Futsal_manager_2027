# -*- coding: utf-8 -*-
"""Plafond de masse salariale joueurs + staff et calcul du delta de prolongation."""
import os, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
import wage_budget as wb

TMP = tempfile.mkdtemp(prefix="fm_wagecap_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP; app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=3,
            identity={"name": "Cap FC", "arena_name": "A", "color1": "#c47220",
                      "color2": "#14171f", "division": 3})
from PySide6.QtWidgets import QApplication, QDialog
q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
w = app.MainWindow(); w.show(); w.app_stack.setCurrentWidget(w.game_shell); q.processEvents()
notices = []
w.show_game_message = lambda title, message, severity="info", **kw: (notices.append((severity, title, str(message))), True)[1]
app.QDialog.exec = lambda self, *a, **k: QDialog.Accepted

c = app.db()
st = wb.status(w, c)
print(f"plafond={st['cap']} joueurs={st['players']} staff={st['staff']} marge={st['room']}")
assert st["cap"] > 0
assert st["total"] == st["players"] + st["staff"]
assert st["room"] == st["cap"] - st["total"]
details = st["cap_details"]
assert details["income"] > 0 and details["budget"] > 0
assert details["cap"] == st["cap"]
print("détail plafond: revenus", details["income"], "budget", details["budget"],
      "réputation", details["reputation"], "facteur", details["reputation_factor"])

# Le plafond monte avec le budget puis avec la réputation.
base_budget, base_rep = details["budget"], details["reputation"]
c.execute("UPDATE club SET budget=? WHERE id=1", (base_budget + 5_000_000,)); c.commit()
cap_budget = wb.status(w, c)["cap"]
assert cap_budget > st["cap"], (cap_budget, st["cap"])
c.execute("UPDATE club SET reputation=MIN(100,reputation+25) WHERE id=1"); c.commit()
cap_rep = wb.status(w, c)["cap"]
assert cap_rep > cap_budget, (cap_rep, cap_budget)
print("plafond budget+5M:", cap_budget, "| réputation+25:", cap_rep)
c.execute("UPDATE club SET budget=?, reputation=? WHERE id=1", (base_budget, base_rep)); c.commit()
st = wb.status(w, c)

# Delta de prolongation : +500 € ne doit consommer que 500 € de marge.
row = c.execute("SELECT id,salary FROM player WHERE club_id=1 ORDER BY salary DESC LIMIT 1").fetchone()
pid, old = int(row["id"]), int(row["salary"] or 0)
ok, st2, projected = wb.can_add_player(w, c, old + 500, old)
print("renouvellement:", old, "->", old + 500, "| projeté", projected, "| attendu", st["total"] + 500)
assert projected == st["total"] + 500
assert st2["total"] == st["total"]

# Une recrue au plafond exact est refusée, une recrue dans la marge passe.
if st["room"] > 0:
    ok_room, _s, _p = wb.can_add_player(w, c, st["room"], 0)
    assert ok_room
ok_over, _s, _p = wb.can_add_player(w, c, st["cap"], 0)
assert not ok_over

# Staff : embauche simulée et refus si la masse explose.
ok_hire, st_hire, proj_staff = wb.can_set_staff_level(w, c, "comptable_hired", 1, hire=True)
print("embauche comptable:", ok_hire, "proj", proj_staff, "| staff actuel", st["staff"])
assert proj_staff >= st["staff"]
# On sature temporairement la masse pour verifier le blocage.
c.execute("UPDATE player SET salary=? WHERE id=?", (int(st["cap"]), pid)); c.commit()
st_full = wb.status(w, c)
ok_full, _st, _proj = wb.can_set_staff_level(w, c, "directeur_sportif_hired", 1, hire=True)
print("masse saturee:", st_full["total"], "/", st_full["cap"], "| staff bloque:", not ok_full)
assert not ok_full
# Une baisse de salaire reste autorisee pour revenir dans les clous.
ok_reduce, _st, _proj = wb.can_add_player(w, c, max(500, old - 500), old)
print("baisse de salaire sur masse saturee:", ok_reduce)
assert ok_reduce
c.execute("UPDATE player SET salary=? WHERE id=?", (old, pid)); c.commit()

# Affichage finances : le plafond est visible.
w._refresh_futsal_finance_panel(c.execute("SELECT * FROM club WHERE id=1").fetchone())
txt = w.wage_cap_label.text()
print("UI:", txt[:110])
assert "PLAFOND MASSE SALARIALE" in txt and "plafond" in txt.lower()
c.close()
print("RESULT: ALL OK")
