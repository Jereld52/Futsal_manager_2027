# -*- coding: utf-8 -*-
"""Hors mercato : accords possibles, changements de club à l'ouverture."""
import os, sys, tempfile, json
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication

TMP = tempfile.mkdtemp(prefix="fm_window_defer_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP; app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=3,
            identity={"name": "Window FC", "arena_name": "A", "color1": "#c47220",
                      "color2": "#14171f", "division": 3})

c = app.db()
c.execute('UPDATE career SET "current_date"=? WHERE id=1', ("2026-10-15",))
c.execute("UPDATE club SET budget=5000000 WHERE id=1")
clubs = c.execute("SELECT id,name FROM club WHERE id<>1 ORDER BY id LIMIT 3").fetchall()
buyer_id = int(clubs[0]["id"]); buyer_name = clubs[0]["name"]
seller_id = int(clubs[1]["id"]); seller_name = clubs[1]["name"]
# Joueur libre.
free_id = int(c.execute("SELECT id,first_name,last_name FROM player WHERE club_id=? LIMIT 1", (seller_id,)).fetchone()["id"])
c.execute("UPDATE player SET club_id=0,is_free_agent=1,contract_years=0,free_agent_since='2026-10-01' WHERE id=?", (free_id,))
# Joueur à vendre.
sale_id = int(c.execute("SELECT id FROM player WHERE club_id=1 AND injury_matches<=0 ORDER BY id LIMIT 1").fetchone()["id"])
# Joueur à acheter.
buy_id = int(c.execute("SELECT id FROM player WHERE club_id=? ORDER BY id LIMIT 1", (seller_id,)).fetchone()["id"])
now = "2026-10-15"
app.queue_manager_message(c, "free_agent_contract", "Offre de contrat", "Test", now, now,
                          {"player_id": free_id, "offer_salary": 800, "offer_years": 2}, is_read=True, ready=True)
app.queue_manager_message(c, "transfer_sale", "Offre reçue", "Test", now, now,
                          {"player_id": sale_id, "buyer_id": buyer_id, "buyer_name": buyer_name,
                           "fee": 100000, "final_fee": 100000, "player_name": "Joueur à vendre"},
                          is_read=True, ready=True)
app.queue_manager_message(c, "market_offer", "Offre acceptée", "Test", now, now,
                          {"player_id": buy_id, "club_id": seller_id, "club_name": seller_name,
                           "outcome": "accepted", "final_fee": 50000, "final_salary": 900,
                           "final_years": 3, "bid": 50000, "player_name": "Cible"},
                          is_read=True, ready=True)
c.commit()
free_msg = int(c.execute("SELECT id FROM manager_message WHERE kind='free_agent_contract' ORDER BY id DESC LIMIT 1").fetchone()["id"])
sale_msg = int(c.execute("SELECT id FROM manager_message WHERE kind='transfer_sale' ORDER BY id DESC LIMIT 1").fetchone()["id"])
buy_msg = int(c.execute("SELECT id FROM manager_message WHERE kind='market_offer' ORDER BY id DESC LIMIT 1").fetchone()["id"])
before_budget = int(c.execute("SELECT budget FROM club WHERE id=1").fetchone()["budget"])
c.close()

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
app.MainWindow.show_game_message = lambda self, *a, **k: True
w = app.MainWindow(); w.resize(1360, 900); w.show()
w.app_stack.setCurrentWidget(w.game_shell); q.processEvents()

# Hors mercato, une offre peut toujours être déposée.
other_id = int(app.db().execute("SELECT id FROM player WHERE club_id=? AND id NOT IN (?,?) ORDER BY id LIMIT 1",
                                (seller_id, free_id, buy_id)).fetchone()["id"])
assert w.submit_market_offer(other_id, 1000, 2, 900)
c = app.db(); open_offer = c.execute("SELECT COUNT(*) n FROM manager_message WHERE kind='market_offer' AND action_data LIKE ?",
                                    (f'%{other_id}%',)).fetchone()["n"]; c.close()
assert open_offer >= 1

w._resolve_message(free_msg, "accept"); q.processEvents()
w._resolve_message(sale_msg, "accept"); q.processEvents()
w._resolve_message(buy_msg, "accept"); q.processEvents()

c = app.db()
free_row = c.execute("SELECT club_id,is_free_agent FROM player WHERE id=?", (free_id,)).fetchone()
sale_row = c.execute("SELECT club_id FROM player WHERE id=?", (sale_id,)).fetchone()
buy_row = c.execute("SELECT club_id FROM player WHERE id=?", (buy_id,)).fetchone()
arr = c.execute("SELECT due_date,action_data FROM manager_message WHERE kind='transfer_arrival' AND action_data LIKE ? ORDER BY id DESC LIMIT 1", (f'%{free_id}%',)).fetchone()
dep = c.execute("SELECT due_date,action_data FROM manager_message WHERE kind='transfer_departure' AND action_data LIKE ? ORDER BY id DESC LIMIT 1", (f'%{sale_id}%',)).fetchone()
buy_arr = c.execute("SELECT due_date FROM manager_message WHERE kind='transfer_arrival' AND action_data LIKE ? ORDER BY id DESC LIMIT 1", (f'%{buy_id}%',)).fetchone()
budget_after = int(c.execute("SELECT budget FROM club WHERE id=1").fetchone()["budget"])
c.close()
assert int(free_row["club_id"] or 0) == 0 and int(free_row["is_free_agent"] or 0) == 1, dict(free_row)
assert int(sale_row["club_id"] or 0) == 1, dict(sale_row)
assert int(buy_row["club_id"] or 0) == seller_id, dict(buy_row)
assert arr and arr["due_date"] == "2027-01-01", (arr["due_date"] if arr else None)
assert dep and dep["due_date"] == "2027-01-01", (dep["due_date"] if dep else None)
assert buy_arr and buy_arr["due_date"] == "2027-01-01", (buy_arr["due_date"] if buy_arr else None)
assert budget_after == before_budget - 50000, (before_budget, budget_after)
print("OK hors mercato : accords conservés, changements au 01/01/2027, frais d'achat réglés")

# Avant l'ouverture : l'arrivée programmée n'est pas un dossier à accepter/refuser.
w.show_page(7); q.processEvents()
w.mercato_tabs.setCurrentIndex(0); w._refresh_offers_tab(); q.processEvents()
def _cards_for(names):
    out=[]
    for i in range(w.offers_out_cards_layout.count()):
        card=w.offers_out_cards_layout.itemAt(i).widget()
        if card is None or card.objectName()!="OfferCard": continue
        labels=[l.text() for l in card.findChildren(app.QLabel)]
        if any(name in labels for name in names): out.append(card)
    return out
free_name=app.db().execute("SELECT first_name||' '||last_name n FROM player WHERE id=?",(free_id,)).fetchone()["n"]
buy_name=app.db().execute("SELECT first_name||' '||last_name n FROM player WHERE id=?",(buy_id,)).fetchone()["n"]
cards=_cards_for({free_name,buy_name})
texts=[b.text() for card in cards for b in card.findChildren(app.QPushButton)]
assert cards and "ACCEPTER" not in texts and "REFUSER" not in texts and "CONTRE" not in texts, texts
print("OK offres : arrivée programmée sans bouton Accepter/Refuser")

# Ouverture : les trois changements s'exécutent.
c = app.db()
c.execute('UPDATE career SET "current_date"=? WHERE id=1', ("2027-01-01",))
c.commit()
w.process_due_manager_messages(c, "2027-01-01"); c.commit()
free_row = c.execute("SELECT club_id,is_free_agent,salary FROM player WHERE id=?", (free_id,)).fetchone()
sale_row = c.execute("SELECT club_id FROM player WHERE id=?", (sale_id,)).fetchone()
buy_row = c.execute("SELECT club_id FROM player WHERE id=?", (buy_id,)).fetchone()
budget_after2 = int(c.execute("SELECT budget FROM club WHERE id=1").fetchone()["budget"])
c.close()
assert int(free_row["club_id"] or 0) == 1 and int(free_row["is_free_agent"] or 0) == 0, dict(free_row)
assert int(sale_row["club_id"] or 0) == buyer_id, dict(sale_row)
assert int(buy_row["club_id"] or 0) == 1, dict(buy_row)
assert budget_after2 == budget_after + 100000, (budget_after, budget_after2)
print("OK ouverture : libre + achat arrivent, vente créditée, joueurs aux bons clubs")

w.mercato_tabs.setCurrentIndex(0); w._refresh_offers_tab(); q.processEvents()
cards=[card for card in _cards_for({free_name,buy_name})]
texts=[b.text() for card in cards for b in card.findChildren(app.QPushButton)]
assert "ACCEPTER" not in texts and "REFUSER" not in texts and "CONTRE" not in texts, texts
print("OK offres après arrivée : plus aucun bouton de décision fantôme")

# Ancienne sauvegarde : un transfer_arrival ready sans outcome doit être clos.
c = app.db()
row = c.execute("SELECT id,action_data FROM manager_message WHERE kind='transfer_arrival' AND action_data LIKE ? ORDER BY id DESC LIMIT 1",
                (f'%{buy_id}%',)).fetchone()
d = json.loads(row["action_data"] or "{}"); d.pop("outcome", None)
c.execute("UPDATE manager_message SET status='ready',action_data=? WHERE id=?", (json.dumps(d), int(row["id"])))
c.commit(); c.close()
w._refresh_offers_tab(); q.processEvents()
cards=[card for card in _cards_for({free_name,buy_name})]
texts=[b.text() for card in cards for b in card.findChildren(app.QPushButton)]
assert "ACCEPTER" not in texts and "REFUSER" not in texts and "CONTRE" not in texts, texts
print("OK sauvegarde existante : arrivée ready sans outcome classée close")
print("RESULT: ALL OK")
