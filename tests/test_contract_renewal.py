# -*- coding: utf-8 -*-
"""Renouvellement de contrat : jeunes, seniors, exigences et alertes.

Couvre :
  1. Un jeune (17 ans) prolonge au salaire attendu (salaire juste +2 %).
  2. Une offre trop basse reçoit une contre-offre au bon montant.
  3. À la clôture, TOUS les U21 en fin de contrat sont signalés, même s'ils
     ont joué (message « Jeunes à prolonger »).
  4. Le filtre Effectif « Jeunes à prolonger » isole exactement ces joueurs
     et le KPI des contrats donne le détail.
"""
import json
import os
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication

TMP = tempfile.mkdtemp(prefix="fm_renewtest_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP
app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=3,
            identity={"name": "Renew FC", "arena_name": "A", "color1": "#c47220",
                      "color2": "#14171f", "division": 3})

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
app.QDialog.exec = lambda self, *a, **k: 1
w = app.MainWindow()
w.setAttribute(app.Qt.WA_DontShowOnScreen, True)
w.show_game_message = lambda *a, **k: True
w.resize(1400, 900)
w.show(); q.processEvents()
w.app_stack.setCurrentWidget(w.game_shell)


def make_player(first, last, age, salary, potential, level=10, years=1, matches=0):
    c = app.db()
    shirt = int(c.execute("SELECT COALESCE(MAX(shirt_number),0) v FROM player WHERE club_id=1").fetchone()["v"]) + 1
    c.execute("""INSERT INTO player(club_id,first_name,last_name,age,position,technique,passing,finishing,
                                     defense,goalkeeper,stamina,condition,morale,nationality,salary,contract_years,
                                     market_value,is_free_agent,shirt_number,dribble,speed,positioning,potential_fixed,
                                     season_matches)
                 VALUES(1,?,?,?,?,?,?,?,?,?,?,?,?,'Française',?,?,10000,0,?,?,?,?,?,?)""",
              (first, last, age, "Universel", level, level, level, level, 20, 60, 100, 70, salary, years,
               shirt, level, level, level, potential, matches))
    c.commit()
    pid = int(c.execute("SELECT id FROM player ORDER BY id DESC LIMIT 1").fetchone()["id"])
    c.close()
    return pid


def expectation(pid):
    c = app.db()
    p = c.execute("SELECT * FROM player WHERE id=?", (pid,)).fetchone()
    club = c.execute("SELECT * FROM club WHERE id=1").fetchone()
    c.close()
    ask, _excess = app.player_salary_demand(p, club)
    return max(int(p["salary"] * 1.02), int(ask))


def send_offer(pid, salary, years, due):
    c = app.db()
    app.queue_manager_message(c, "contract_offer", "Proposition de contrat envoyée", "Test",
                              due, due, {"player_id": pid, "offer_salary": salary,
                                         "offer_years": years}, is_read=True)
    c.commit()
    mid = int(c.execute("SELECT id FROM manager_message WHERE kind='contract_offer' ORDER BY id DESC LIMIT 1").fetchone()["id"])
    w.process_due_manager_messages(c, due)
    c.commit()
    row = c.execute("SELECT * FROM manager_message WHERE id=?", (mid,)).fetchone()
    c.close()
    return mid, json.loads(row["action_data"] or "{}")


def accept(mid):
    c = app.db()
    rows = c.execute("SELECT * FROM manager_message ORDER BY id DESC LIMIT 400").fetchall()
    c.close()
    w._manager_messages = list(rows)
    w.resolve_manager_message("accept", mid); q.processEvents()


today = app.db().execute("SELECT current_date d FROM career WHERE id=1").fetchone()["d"]

# ---------- 1) Jeune : prolongation au salaire attendu ----------
young = make_player("Jeune", "Espoir", 17, 1200, 18, 8, 1)
ask = expectation(young)
print("jeune: salaire 1200, attente agent", ask)
mid, res = send_offer(young, ask, 3, today)
assert res.get("outcome") == "accepted", res
accept(mid)
c = app.db()
p = c.execute("SELECT salary,contract_years,morale FROM player WHERE id=?", (young,)).fetchone()
c.close()
assert int(p["contract_years"]) == 3, p["contract_years"]
assert int(p["salary"]) == ask, (p["salary"], ask)
assert int(p["morale"]) >= 70
print("1) jeune prolongé:", p["contract_years"], "ans à", f"{p['salary']} €")

# ---------- 2) Offre trop basse : contre-offre au bon montant ----------
senior = make_player("Vieux", "Cadre", 30, 3000, 14, 13, 1, 10)
mid2, res2 = send_offer(senior, 500, 2, today)
assert res2.get("outcome") == "counter", res2
claim = int(res2.get("counter_salary") or 0)
assert claim >= int(3000 * 1.02), ("contre-offre sous le salaire actuel", claim)
mid3, res3 = send_offer(senior, claim, 2, today)
assert res3.get("outcome") == "accepted", (claim, res3)
accept(mid3)
c = app.db(); p2 = c.execute("SELECT salary,contract_years FROM player WHERE id=?", (senior,)).fetchone(); c.close()
assert int(p2["salary"]) == claim and int(p2["contract_years"]) == 2
print("2) contre-offre:", claim, "€, puis acceptée")

# ---------- 3) Filtre Effectif « Jeunes à prolonger » ----------
young_expiring = make_player("Jeune", "FinContrat", 19, 1500, 16, 9, 1, 5)
old_expiring = make_player("Ancien", "FinContrat", 29, 2500, 14, 12, 1, 8)
young_ok = make_player("Jeune", "SousContrat", 18, 1400, 17, 8, 3, 2)
w.show_page(1); q.processEvents()
w.roster_status_filter.setCurrentText("Jeunes à prolonger"); q.processEvents()
shown = []
for r in range(w.roster_table.rowCount()):
    item = w.roster_table.item(r, 2)
    shown.append(item.text() if item else "")
c = app.db()
expected = [f"{r['first_name']} {r['last_name']}" for r in c.execute(
    """SELECT * FROM player WHERE club_id=1 AND age<=21 AND contract_years<=1
       AND COALESCE(loan_from_club,0)=0 ORDER BY CASE position WHEN 'Gardien' THEN 0
       WHEN 'Défenseur' THEN 1 WHEN 'Ailier' THEN 2 WHEN 'Pivot' THEN 3 ELSE 4 END, last_name""").fetchall()]
c.close()
assert "Jeune FinContrat" in " ".join(shown), shown
assert "Ancien FinContrat" not in " ".join(shown), shown
assert "Jeune SousContrat" not in " ".join(shown), shown
tooltip = w.roster_contracts_value.toolTip()
assert "U21" in tooltip, tooltip
print("3) filtre jeunes:", sum(1 for s in shown if s), "ligne(s) |", tooltip.splitlines()[0])
w.roster_status_filter.setCurrentText("Tout l'effectif"); q.processEvents()

# ---------- 4) Clôture : alerte « Jeunes à prolonger » même si le jeune joue ----------
t2 = tempfile.mkdtemp(prefix="fm_renewseason_")
os.makedirs(os.path.join(t2, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(t2, "saves")
app.DB_PATH = os.path.join(t2, "saves", "p.db")
app.init_db(fresh_universe=True, selected_division=3,
            identity={"name": "Renew Season FC", "arena_name": "A", "color1": "#c47220",
                      "color2": "#14171f", "division": 3})
w2 = app.MainWindow()
w2.setAttribute(app.Qt.WA_DontShowOnScreen, True)
w2.show_game_message = lambda *a, **k: True
w2.resize(1200, 800); w2.show(); q.processEvents()
w2.app_stack.setCurrentWidget(w2.game_shell)
a = make_player("Titulaire", "Jeune", 18, 1500, 17, 10, 1, 9)
b = make_player("Remplaçant", "Jeune", 20, 1400, 15, 9, 1, 2)
c0 = make_player("Sans", "Match", 17, 1200, 16, 8, 1, 0)
loaned = make_player("Prêté", "Jeune", 19, 1400, 15, 9, 1, 4)
c = app.db()
c.execute("UPDATE player SET loan_from_club=2 WHERE id=?", (loaned,))
c.execute("DELETE FROM fixture WHERE played=0")
c.execute("UPDATE career SET current_date='2027-06-30' WHERE id=1")
c.commit(); c.close()
assert w2.start_new_season()
c = app.db()
msg = c.execute("""SELECT * FROM manager_message WHERE kind='contract_departure'
                   AND title='Jeunes à prolonger' ORDER BY id DESC LIMIT 1""").fetchone()
data = json.loads(msg["action_data"] or "{}") if msg else {}
c.close()
assert msg is not None, "aucune alerte jeunes à prolonger"
assert data.get("youth") is True
for name in ("Titulaire Jeune", "Remplaçant Jeune", "Sans Match"):
    assert name in msg["body"], (name, msg["body"])
assert "Prêté Jeune" not in msg["body"], "un joueur prêté ne peut pas être prolongé"
print("4) clôture:", msg["body"][:120], "...")

w2.close(); w.close(); q.processEvents()
size = os.path.getsize(r"C:\FM2027V2\data\error.log")
assert size == 0, size
print("RESULT: ALL OK")
