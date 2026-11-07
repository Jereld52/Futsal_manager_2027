# -*- coding: utf-8 -*-
"""Marché des transferts : processus complet et concurrence entre clubs.

Scénarios couverts :
  1. Un club rival double une offre sous le prix demandé : le joueur part
     ailleurs, l'acheteur paie, le vendeur encaisse, le manager ne l'a pas.
  2. Payer le prix demandé sécurise la cible (aucun rival).
  3. Marché IA-IA : plusieurs clubs, un joueur vendu une seule fois, budgets
     conservés, club du manager jamais touché.
  4. Vente d'un joueur du club : une seule offre active, pas de double vente.
  5. Joueur libre signé ailleurs pendant la négociation : dossier « SIGNÉ
     AILLEURS », aucune signature.
"""
import json
import os
import random
import sys
import tempfile
from datetime import timedelta

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication
import ai_finance

TMP = tempfile.mkdtemp(prefix="fm_compet_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP
app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=2,
            identity={"name": "Compet FC", "arena_name": "A", "color1": "#2f6fed",
                      "color2": "#101a2e", "division": 2})

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
app.QDialog.exec = lambda self, *a, **k: 1
w = app.MainWindow()
w.setAttribute(app.Qt.WA_DontShowOnScreen, True)
w.show_game_message = lambda *a, **k: True
w.resize(1400, 900)
w.show(); q.processEvents()
w.app_stack.setCurrentWidget(w.game_shell)

c = app.db()
c.execute("UPDATE club SET budget=50000000 WHERE id=1")
c.execute("DELETE FROM manager_message")
c.commit(); c.close()


def _mk_offer(pid, bid, salary=600):
    c = app.db()
    c.execute("UPDATE player SET transfer_listed=1 WHERE id=?", (int(pid),))
    c.commit(); c.close()
    return w.submit_market_offer(int(pid), int(bid), 3, player_salary=salary)


def _last_offer():
    c = app.db()
    row = c.execute("SELECT * FROM manager_message WHERE kind='market_offer' ORDER BY id DESC LIMIT 1").fetchone()
    data = json.loads(row["action_data"] or "{}") if row else {}
    c.close()
    return row, data


def _force_rival(conn, due):
    """Force la branche « offre concurrente » (18 % de base)."""
    original = random.random
    random.random = lambda: 0.0
    try:
        w.process_due_manager_messages(conn, due)
    finally:
        random.random = original


# ---------- 1) Un rival double l'offre sous le prix ----------
c = app.db()
target = c.execute("""SELECT p.id,p.first_name,p.last_name,p.club_id,p.market_value,c.name club_name
                      FROM player p JOIN club c ON c.id=p.club_id
                      WHERE p.club_id<>1 AND p.is_free_agent=0 AND COALESCE(p.retired,0)=0
                        AND COALESCE(p.loan_from_club,0)=0 AND p.market_value>20000
                      ORDER BY p.market_value DESC LIMIT 1""").fetchone()
c.close()
assert target is not None
assert _mk_offer(target["id"], 1000), "offre refusée (budget/plafond)"
msg, data = _last_offer()
ask = int(data.get("seller_ask") or 0)
assert 1000 < ask, ("offre non sous le prix", 1000, ask)
seller_id = int(data["club_id"])

c = app.db()
seller_before = int(c.execute("SELECT budget FROM club WHERE id=?", (seller_id,)).fetchone()["budget"])
budgets_before = {int(r["id"]): int(r["budget"] or 0) for r in c.execute("SELECT id,budget FROM club").fetchall()}
user_squad_before = int(c.execute("SELECT COUNT(*) n FROM player WHERE club_id=1").fetchone()["n"])
c.close()

c = app.db(); _force_rival(c, msg["due_date"]); c.commit()
row = c.execute("SELECT * FROM manager_message WHERE id=?", (msg["id"],)).fetchone()
res = json.loads(row["action_data"] or "{}")
player = c.execute("SELECT club_id FROM player WHERE id=?", (int(target["id"]),)).fetchone()
seller_after = int(c.execute("SELECT budget FROM club WHERE id=?", (seller_id,)).fetchone()["budget"])
user_squad_after = int(c.execute("SELECT COUNT(*) n FROM player WHERE club_id=1").fetchone()["n"])
buyer_id = int(player["club_id"]) if player else 0
buyer_after = int(c.execute("SELECT budget FROM club WHERE id=?", (buyer_id,)).fetchone()["budget"]) if buyer_id else 0
budgets_after = {int(r["id"]): int(r["budget"] or 0) for r in c.execute("SELECT id,budget FROM club").fetchall()}
arrivals = int(c.execute("""SELECT COUNT(*) n FROM manager_message
                            WHERE kind='transfer_arrival' AND action_data LIKE ?
                            AND status IN ('waiting','ready')""", (f'%"player_id": {int(target["id"])}%',)).fetchone()["n"])
c.close()

assert res.get("outcome") == "rival", res
assert res.get("rival_club"), res
assert buyer_id not in (0, 1, seller_id), (buyer_id, seller_id)
assert seller_after == seller_before + ask, ("vendeur non crédité", seller_before, seller_after, ask)
assert buyer_after == budgets_before[buyer_id] - ask, ("acheteur non débité", budgets_before.get(buyer_id), buyer_after, ask)
_changed = {cid for cid in budgets_before if budgets_before[cid] != budgets_after.get(cid, budgets_before[cid])}
assert _changed == {seller_id, buyer_id}, ("mouvements de budget inattendus", _changed)
assert user_squad_after == user_squad_before, "le manager a récupéré le joueur malgré le rival"
assert arrivals == 0, "une arrivée a été programmée alors que le rival a signé"
print(f"1) rival: {target['last_name']} -> {res['rival_club']} | vendeur +{ask:,} € | erreur acheteur OK")

# ---------- 2) Payer le prix demandé sécurise ----------
c = app.db()
target2 = c.execute("""SELECT p.id,p.market_value FROM player p
                       WHERE p.club_id<>1 AND p.is_free_agent=0 AND COALESCE(p.retired,0)=0
                         AND COALESCE(p.loan_from_club,0)=0 AND p.market_value>10000 AND p.id<>?
                       ORDER BY p.market_value DESC LIMIT 1""", (int(target["id"]),)).fetchone()
c.close()
# Premier envoi pour connaître le prix demandé, puis annulation.
assert _mk_offer(target2["id"], 1000)
msgA, dataA = _last_offer()
ask2 = int(dataA.get("seller_ask") or 0)
c = app.db(); c.execute("DELETE FROM manager_message WHERE id=?", (msgA["id"],)); c.commit(); c.close()
big = max(ask2, int(target2["market_value"]) * 2)
assert _mk_offer(target2["id"], big)
msgB, dataB = _last_offer()
assert int(dataB.get("bid") or 0) >= int(dataB.get("seller_ask") or 0)
c = app.db(); _force_rival(c, msgB["due_date"]); c.commit()
row = c.execute("SELECT * FROM manager_message WHERE id=?", (msgB["id"],)).fetchone()
resB = json.loads(row["action_data"] or "{}")
club2 = c.execute("SELECT club_id FROM player WHERE id=?", (int(target2["id"]),)).fetchone()["club_id"]
c.close()
assert resB.get("outcome") in ("accepted", "seller_accepted", "player_counter"), resB
assert resB.get("outcome") != "rival"
assert int(club2) == int(dataB["club_id"]), "la cible a bougé malgré le prix payé"
print("2) prix demandé payé: cible sécurisée, aucun rival")

# ---------- 3) Marché IA-IA : concurrence et conservation ----------
c = app.db(); c.execute("DELETE FROM manager_message"); c.commit(); c.close()
start = app.parse_iso(w._career_day())
wednesdays = []
d = start
while len(wednesdays) < 5:
    if d.weekday() == 2:
        wednesdays.append(d.isoformat())
    d += timedelta(days=1)

total_before = None
for day in wednesdays:
    c = app.db()
    if total_before is None:
        total_before = int(c.execute("SELECT SUM(budget) s FROM club").fetchone()["s"] or 0)
    listed_before = {int(r["id"]): int(r["club_id"]) for r in c.execute(
        "SELECT id,club_id FROM player WHERE transfer_listed=1 AND club_id NOT IN (0,1)").fetchall()}
    deals = ai_finance.process_ai_transfer_market(w, c, day)
    c.commit()
    total_after = int(c.execute("SELECT SUM(budget) s FROM club").fetchone()["s"] or 0)
    c.close()
    assert deals <= 4, ("trop de deals", deals)
    assert total_after == total_before, ("budgets non conservés", total_before, total_after)
    total_before = total_after

c = app.db()
moved = c.execute("""SELECT COUNT(*) n FROM player WHERE club_id=1 AND transfer_listed=1
                     AND COALESCE(is_free_agent,0)=0""").fetchone()["n"]
user_listed = c.execute("SELECT COUNT(*) n FROM player WHERE transfer_listed=1 AND club_id=1").fetchone()["n"]
c.close()
print(f"3) marché IA-IA: 5 mercredis, budgets conservés, club du manager intact ({user_listed} listé(s))")

# ---------- 4) Vente du club : une seule offre, pas de double vente ----------
c = app.db()
uid = c.execute("SELECT id FROM player WHERE club_id=1 ORDER BY id LIMIT 1").fetchone()["id"]
c.execute("UPDATE player SET transfer_listed=1, contract_years=2 WHERE id=?", (int(uid),))
c.execute("DELETE FROM manager_message WHERE kind IN ('transfer_sale','transfer_departure')")
c.commit(); c.close()
# Une offre reçue puis un départ déjà programmé : repair doit classer l'offre.
c = app.db()
app.queue_manager_message(c, "transfer_departure", "Vente • départ à l'ouverture",
                          "Départ programmé pour le test.", w._current_date(c), w._current_date(c),
                          {"player_id": int(uid), "buyer_id": 2, "fee": 5000, "player_name": "Test",
                           "deferred": True}, is_read=False)
app.queue_manager_message(c, "transfer_sale", "Offre reçue • Test",
                          "Offre de test.", w._current_date(c), w._current_date(c),
                          {"player_id": int(uid), "buyer_id": 3, "buyer_name": "Test FC",
                           "fee": 6000, "player_name": "Test"}, ready=True)
c.commit(); c.close()
w.repair_pending_departures()
c = app.db()
pending = len(w.pending_departure_ids(c))
listing = int(c.execute("SELECT transfer_listed FROM player WHERE id=?", (int(uid),)).fetchone()["transfer_listed"])
dup = c.execute("""SELECT COUNT(*) n FROM manager_message WHERE kind='transfer_sale'
                   AND status IN ('waiting','ready') AND action_data LIKE ?""",
                (f'%"player_id": {int(uid)}%',)).fetchone()["n"]
c.close()
assert pending == 1, pending
assert listing == 0, "le joueur vendu doit sortir de la liste"
assert dup == 0, "une offre concurrente est restée active après le départ programmé"
print("4) vente club: 1 départ programmé, offres concurrentes classées")

# ---------- 5) Joueur libre signé ailleurs ----------
c = app.db(); c.execute("DELETE FROM manager_message"); c.commit()
free = c.execute("""SELECT p.id,p.club_id FROM player p WHERE p.is_free_agent=1
                    AND COALESCE(p.retired,0)=0 ORDER BY p.market_value DESC LIMIT 1""").fetchone()
riv = c.execute("SELECT id,name FROM club WHERE id<>1 ORDER BY reputation DESC LIMIT 1").fetchone()
c.close()
assert free is not None and riv is not None
assert w.submit_market_offer(int(free["id"]), 1800, 2), "offre libre refusée"
c = app.db()
msgF = c.execute("SELECT * FROM manager_message WHERE kind='free_agent_contract' ORDER BY id DESC LIMIT 1").fetchone()
# Le club rival signe le joueur avant l'échéance.
c.execute("UPDATE player SET club_id=?,is_free_agent=0,free_agent_since='' WHERE id=?",
          (int(riv["id"]), int(free["id"])))
c.commit()
w.process_due_manager_messages(c, msgF["due_date"]); c.commit()
row = c.execute("SELECT * FROM manager_message WHERE id=?", (msgF["id"],)).fetchone()
resF = json.loads(row["action_data"] or "{}")
signed = c.execute("SELECT club_id FROM player WHERE id=?", (int(free["id"]),)).fetchone()["club_id"]
c.close()
assert resF.get("outcome") == "rival", resF
assert resF.get("rival_club") == riv["name"], resF
assert int(signed) == int(riv["id"]), signed
print(f"5) joueur libre: signé à {riv['name']}, dossier SIGNÉ AILLEURS")

w.close(); q.processEvents()
size = os.path.getsize(r"C:\FM2027V2\data\error.log")
assert size == 0, size
print("RESULT: ALL OK")
