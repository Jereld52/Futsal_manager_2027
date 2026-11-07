# -*- coding: utf-8 -*-
"""Pré-contrats : temps de réflexion, contre-offre du club et décision du joueur."""
import os
import sys
import tempfile
from unittest import mock

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication

TMP = tempfile.mkdtemp(prefix="fm_prenego_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP
app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=2,
            identity={"name": "Nego FC", "arena_name": "Halle", "color1": "#2f6fed",
                      "color2": "#14171f", "division": 2})

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
app.QDialog.exec = lambda self, *a, **k: 1
w = app.MainWindow()
w.setAttribute(app.Qt.WA_DontShowOnScreen, True)
w.show_game_message = lambda *a, **k: True
w.resize(1600, 1000); w.show(); q.processEvents()
w.app_stack.setCurrentWidget(w.game_shell)

c = app.db()
c.execute("UPDATE career SET current_date='2027-01-15' WHERE id=1")
c.execute("UPDATE player SET contract_years=2 WHERE club_id=1")
targets = c.execute("""SELECT id FROM player WHERE club_id<>1 AND is_free_agent=0 AND COALESCE(retired,0)=0
                       AND age<30 AND contract_years<=1 ORDER BY id LIMIT 2""").fetchall()
assert len(targets) == 2, len(targets)
ids = [int(t["id"]) for t in targets]
c.commit(); c.close()

w.counter_terms_dialog = lambda *a, **k: {"amount": 2600, "years": 2}
assert w.sign_precontract(ids[0]) is True

# ---------- 1) L'offre est en réflexion, pas signée ----------
c = app.db()
offer = c.execute("SELECT * FROM precontract_offer WHERE player_id=?", (ids[0],)).fetchone()
player = c.execute("SELECT precontract_club FROM player WHERE id=?", (ids[0],)).fetchone()
c.close()
assert offer is not None and str(offer["status"]) == "waiting", dict(offer) if offer else None
assert str(offer["decision_date"]) > str(offer["proposed_date"]), (offer["proposed_date"], offer["decision_date"])
assert int(player["precontract_club"] or 0) == 0
assert w.sign_precontract(ids[0]) is False   # pas de doublon
print("1) offre en réflexion, décision le", offer["decision_date"])

# Bandeau : dossier visible en attente.
w.show_page(7); w.mercato_tabs.setCurrentIndex(0); q.processEvents(); w._refresh_offers_tab(); q.processEvents()
assert w.precontract_strip.isVisible()
assert "EN RÉFLEXION" in w.precontract_title.text(), w.precontract_title.text()
pending_cards = [x for x in w.precontract_strip.findChildren(app.QFrame) if x.objectName() == "PreCardPending"]
assert pending_cards, "carte en réflexion absente"
print("2) bandeau :", w.precontract_title.text())

# ---------- 2) Contre-offre du club ----------
counter_day = str(offer["counter_date"])
with mock.patch.object(app.random, "random", return_value=0.0), \
     mock.patch.object(app.random, "uniform", return_value=1.0):
    c = app.db()
    w.process_precontract_offers(c, counter_day)
    c.commit()
    row = c.execute("SELECT counter_salary,counter_date,decision_date FROM precontract_offer WHERE player_id=?", (ids[0],)).fetchone()
    msg = c.execute("SELECT title,body FROM manager_message WHERE title LIKE 'Pré-contrat • contre-offre%' ORDER BY id DESC LIMIT 1").fetchone()
    c.close()
assert int(row["counter_salary"] or 0) > 0, dict(row)
assert msg and "prolongation" in msg["body"], dict(msg) if msg else None
print("3) contre-offre :", row["counter_salary"], "€/mois ·", msg["title"])

# ---------- 3) Décision refusée ----------
w._precontract_decision = lambda *a, **k: (False, 0.1)
c = app.db()
c.execute("UPDATE precontract_offer SET decision_date=? WHERE player_id=?", (counter_day, ids[0]))
c.commit()
w.process_precontract_offers(c, counter_day)
c.commit()
left = c.execute("SELECT COUNT(*) n FROM precontract_offer WHERE player_id=?", (ids[0],)).fetchone()["n"]
signed = c.execute("SELECT precontract_club FROM player WHERE id=?", (ids[0],)).fetchone()["precontract_club"]
refused = c.execute("SELECT body FROM manager_message WHERE title='Pré-contrat refusé' ORDER BY id DESC LIMIT 1").fetchone()
c.close()
assert int(left) == 0 and int(signed or 0) == 0
assert refused and "contre-offre" in refused["body"], refused["body"] if refused else None
print("4) refus :", refused["body"][:80])

# ---------- 4) Décision acceptée (malgré une contre-offre) ----------
assert w.sign_precontract(ids[1]) is True
c = app.db()
o2 = c.execute("SELECT * FROM precontract_offer WHERE player_id=?", (ids[1],)).fetchone()
c.execute("UPDATE precontract_offer SET decision_date=? WHERE player_id=?", (counter_day, ids[1]))
c.commit()
w._precontract_decision = lambda *a, **k: (True, 0.8)
w.process_precontract_offers(c, counter_day)
c.commit()
p2 = c.execute("SELECT precontract_club,precontract_from,precontract_salary,precontract_years FROM player WHERE id=?", (ids[1],)).fetchone()
ok = c.execute("SELECT body FROM manager_message WHERE title='Pré-contrat signé' ORDER BY id DESC LIMIT 1").fetchone()
c.close()
assert int(p2["precontract_club"] or 0) == 1, dict(p2)
assert int(p2["precontract_from"] or 0) == int(o2["from_club"])
assert int(p2["precontract_salary"] or 0) == 2600 and int(p2["precontract_years"] or 0) == 2
assert ok and "rejoindra le club" in ok["body"], ok["body"] if ok else None
print("5) signature :", ok["body"][:90])

# ---------- 5) Bandeau : le signé remplace l'attente ----------
w.show_page(7); w.mercato_tabs.setCurrentIndex(0); q.processEvents(); w._refresh_offers_tab(); q.processEvents()
assert w.precontract_strip.isVisible()
assert "1 PRÉ-CONTRAT(S)" in w.precontract_title.text(), w.precontract_title.text()
assert "EN RÉFLEXION" not in w.precontract_title.text(), w.precontract_title.text()
print("6) bandeau final :", w.precontract_title.text())

w.close(); q.processEvents()
assert os.path.getsize(r"C:\FM2027V2\data\error.log") == 0
print("RESULT: ALL OK")
