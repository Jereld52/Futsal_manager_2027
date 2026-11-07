# -*- coding: utf-8 -*-
"""Transferts > Offres : cartes lisibles, actions inline, anciens tableaux masqués."""
import os, sys, tempfile, json
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication, QPushButton

TMP = tempfile.mkdtemp(prefix="fm_offers_cards_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP; app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=3,
            identity={"name": "Offres FC", "arena_name": "A", "color1": "#c47220",
                      "color2": "#14171f", "division": 3})

conn = app.db()
own = conn.execute("SELECT id,first_name,last_name FROM player WHERE club_id=1 LIMIT 1").fetchone()
other = conn.execute("SELECT id,first_name,last_name FROM player WHERE club_id<>1 LIMIT 2").fetchall()
def nm(p): return p["first_name"] + " " + p["last_name"]
offers = [
    ("market_offer", "waiting", {"player_id": other[0]["id"], "player_name": nm(other[0]),
                                 "club_name": "AS Rivale", "bid": 1500000,
                                 "offer_salary": 18000, "offer_years": 3, "round": 1}, "2026-09-10"),
    ("transfer_sale", "ready", {"player_id": own["id"], "player_name": nm(own),
                                "buyer_name": "Olympique Lyonnais", "bid": 3400000}, "2026-09-12"),
]
for kind, status, data, due in offers:
    conn.execute("INSERT INTO manager_message(kind,title,body,created_date,due_date,status,action_data,is_read) "
                 "VALUES(?,?,?,?,?,?,?,0)",
                 (kind, "Dossier", "", "2026-08-20", due, status, json.dumps(data)))
conn.commit()
waiting_id = conn.execute("SELECT id FROM manager_message WHERE kind='market_offer'").fetchone()["id"]
conn.close()

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
w = app.MainWindow(); w.resize(1360, 900); w.show()
w.show_game_message = lambda *a, **k: True
w.app_stack.setCurrentWidget(w.game_shell); q.processEvents()
w.show_page(7); q.processEvents()
w.mercato_tabs.setCurrentIndex(0); q.processEvents()
w._refresh_offers_tab(); q.processEvents()

# 1) cartes présentes, tableaux hérités invisibles
out_cards = [w.offers_out_cards_layout.itemAt(i).widget()
             for i in range(w.offers_out_cards_layout.count())
             if w.offers_out_cards_layout.itemAt(i).widget() is not None
             and w.offers_out_cards_layout.itemAt(i).widget().objectName() == "OfferCard"]
in_cards = [w.offers_in_cards_layout.itemAt(i).widget()
            for i in range(w.offers_in_cards_layout.count())
            if w.offers_in_cards_layout.itemAt(i).widget() is not None
            and w.offers_in_cards_layout.itemAt(i).widget().objectName() == "OfferCard"]
assert len(out_cards) == 1 and len(in_cards) == 1, (len(out_cards), len(in_cards))
assert not w.offers_out_table.isVisible() and not w.offers_in_table.isVisible()
assert not w.offers_contract_table.isVisible()
assert not w.offers_out_empty.isVisible() and not w.offers_in_empty.isVisible()
print("OK cartes:", len(out_cards), "demarche(s),", len(in_cards), "offre(s) recue(s)")

# 2) actions inline : la carte en attente propose OUVRIR et REFUSER
labels = [b.text() for b in out_cards[0].findChildren(QPushButton)]
assert "OUVRIR" in labels and "REFUSER" in labels, labels
# 3) refuser depuis la carte
reject = [b for b in out_cards[0].findChildren(QPushButton) if b.text() == "REFUSER"][0]
reject.click(); q.processEvents()
row = app.db().execute("SELECT status FROM manager_message WHERE id=?", (waiting_id,)).fetchone()
assert row["status"] == "handled", row["status"]
print("OK refus depuis la carte")

# 4) refresh x2 : pas de reference morte sur les labels d'etat vide
w._refresh_offers_tab(); q.processEvents()
w._refresh_offers_tab(); q.processEvents()
assert w.offers_out_card_empty is not None and w.offers_in_card_empty is not None
print("OK refresh repetes")

# 5) responsive : 2 colonnes en large, 1 colonne en etroit
w.resize(1360, 900); q.processEvents(); w._fit_offers_layout(); q.processEvents()
assert w._offers_cols == 2, w._offers_cols
w.resize(1000, 700); q.processEvents(); w._fit_offers_layout(); q.processEvents()
assert w._offers_cols == 1, w._offers_cols
print("OK responsive 2 -> 1 colonne")
print("RESULT: ALL OK")
