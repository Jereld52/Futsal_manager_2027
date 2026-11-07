# -*- coding: utf-8 -*-
"""Audit des finances : budget = transactions, paie, prêt, santé, sponsors."""
import os
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
import wage_budget as wb
from PySide6.QtWidgets import QApplication, QLabel

TMP = tempfile.mkdtemp(prefix="fm_finaudit_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP
app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=2,
            identity={"name": "Money FC", "arena_name": "A", "color1": "#2f6fed",
                      "color2": "#101a2e", "division": 2})

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
app.QDialog.exec = lambda self, *a, **k: 1
w = app.MainWindow()
w.setAttribute(app.Qt.WA_DontShowOnScreen, True)
w.show_game_message = lambda *a, **k: True
w.resize(1600, 1000)
w.show(); q.processEvents()
w.app_stack.setCurrentWidget(w.game_shell)
w.show_page(0); q.processEvents()


def snap():
    c = app.db()
    b = int(c.execute("SELECT budget FROM club WHERE id=1").fetchone()["budget"] or 0)
    t = int(c.execute("SELECT COALESCE(SUM(amount),0) s FROM finance_tx WHERE club_id=1").fetchone()["s"] or 0)
    d = c.execute("SELECT current_date FROM career WHERE id=1").fetchone()["current_date"]
    c.close()
    return b, t, d


# ---------- 1) Budget = somme des transactions ----------
b0, t0, d0 = snap()
assert b0 == t0, (b0, t0)
print("1) budget = transactions :", b0, "€")

# ---------- 2) Paie mensuelle : budget, transactions et masse salariale ----------
c = app.db()
b_before = int(c.execute("SELECT budget FROM club WHERE id=1").fetchone()["budget"] or 0)
w.process_player_payroll(c, "2026-12-01")
w.process_staff_payroll(c, "2026-12-01")
c.commit()
pay = c.execute("""SELECT label,amount,created_at FROM finance_tx WHERE club_id=1
                   AND category='Salaire'""").fetchall()
st = wb.status(w, c)
b_after = int(c.execute("SELECT budget FROM club WHERE id=1").fetchone()["budget"] or 0)
t_after = int(c.execute("SELECT COALESCE(SUM(amount),0) s FROM finance_tx WHERE club_id=1").fetchone()["s"] or 0)
c.close()
assert pay, "aucune paie générée"
total_paid = -sum(int(r["amount"]) for r in pay)
assert total_paid == st["total"], (total_paid, st["total"], [dict(r) for r in pay])
assert (b_after - b_before) == -total_paid, (b_after - b_before, total_paid)
assert b_after == t_after, (b_after, t_after)
print("2) paie:", total_paid, "€ = masse salariale", st["total"], "| budget = transactions", b_after)

# ---------- 4) Simulateur de prêt cohérent ----------
c = app.db()
_club = c.execute("SELECT * FROM club WHERE id=1").fetchone()
_fac = c.execute("SELECT * FROM facility WHERE id=1").fetchone()
c.close()
rate, weekly, total = w.loan_terms(_club, _fac, 100000, 52)
fee = w.loan_fee(100000)
assert total == weekly * 52
assert total >= 100000
assert fee == 1000, fee
w.show_page(9); q.processEvents(); w.finance_tabs.setCurrentIndex(2); q.processEvents()
w.loan_amount_spin.setValue(100000)
w.loan_term_combo.setCurrentIndex(w.loan_term_combo.findData(52) if w.loan_term_combo.findData(52) >= 0 else 2)
q.processEvents()
w.update_loan_offer(); q.processEvents()
assert w.loan_kpi_rate.text() == f"{rate/100.0:.2f} %", (w.loan_kpi_rate.text(), rate)
assert w.loan_kpi_total.text().replace(" ", "") == f"{total}€", w.loan_kpi_total.text()
assert "coût du crédit" in w.loan_summary.text()
assert w.loan_history_empty.isVisible() and not w.loan_history_table.isVisible()
print("4) prêt :", rate / 100.0, "% |", w.loan_kpi_weekly.text(), "/sem |", w.loan_kpi_total.text())

# ---------- 5) Santé financière et KPI ----------
w.finance_tabs.setCurrentIndex(0); q.processEvents()
w.refresh_finance_visuals([], _club)
health = w.finance_health_label.text()
assert "TENDU" not in health, health
assert ("ÉQUILIBRÉE" in health or "SAINE" in health), health
income_lbl = w.finance_income_card.findChild(QLabel, "BigNumber").text()
expense_lbl = w.finance_expense_card.findChild(QLabel, "BigNumber").text()
net_lbl = w.finance_net_card.findChild(QLabel, "BigNumber").text()
assert income_lbl.startswith("+") or income_lbl.startswith("0"), income_lbl
assert expense_lbl.startswith("-") or expense_lbl.startswith("0"), expense_lbl
print("5) santé:", health, "| entrées", income_lbl, "| sorties", expense_lbl, "| net", net_lbl)

# ---------- 6) Sponsors : session et parcours guidé ----------
w.finance_tabs.setCurrentIndex(3); q.processEvents()
assert w.sponsor_btn.isEnabled(), "bouton sponsors désactivé"
assert len(w.sponsor_wall_tiles) == 10, len(w.sponsor_wall_tiles)
texts = [lbl.text() for lbl in w.finance_tabs.widget(3).findChildren(QLabel)]
assert "Lancer la session" in texts and "Signer le contrat" in texts, texts[-6:]
print("6) sponsors: session disponible, 10 partenaires, parcours en 3 étapes")
assert w.sponsor_history_empty.isVisible() and not w.sponsor_history_table.isVisible()

# ---------- 7) Signature d'un sponsor → ligne dans l'historique ----------
c = app.db(); budget_before = int(c.execute("SELECT budget FROM club WHERE id=1").fetchone()["budget"] or 0); c.close()
assert w.negotiate_sponsor() is not False, "session de sponsoring refusée"
q.processEvents()
first = w.sponsor_offer_cards[0]["offer"]
sign_on = int(first.get("sign_on", 0))
assert w.sign_sponsor(0) is not False, "signature refusée"
q.processEvents()
c = app.db()
tx = c.execute("SELECT label,amount FROM finance_tx WHERE club_id=1 AND category='Sponsoring' ORDER BY id DESC LIMIT 1").fetchone()
budget_after = int(c.execute("SELECT budget FROM club WHERE id=1").fetchone()["budget"] or 0)
total_tx = int(c.execute("SELECT COALESCE(SUM(amount),0) s FROM finance_tx WHERE club_id=1").fetchone()["s"] or 0)
c.close()
assert tx and "Signature sponsor" in tx["label"] and int(tx["amount"]) == sign_on, (dict(tx) if tx else None, sign_on)
assert budget_after - budget_before == sign_on, (budget_after - budget_before, sign_on)
assert budget_after == total_tx, (budget_after, total_tx)
assert w.sponsor_history_table.rowCount() == 1 and w.sponsor_history_table.isVisible()
assert w.sponsor_history_table.item(0, 1).text() == tx["label"]
assert not w.sponsor_history_empty.isVisible()
print("7) sponsor signé:", first.get("name"), "| prime", sign_on, "€ | historique 1 ligne, budget = transactions")

# ---------- 8) Tarif : appliquer ne doit pas faire bouger l'affluence estimée ----------
w.finance_tabs.setCurrentIndex(1); q.processEvents()
c = app.db(); _fr = c.execute("SELECT value FROM meta WHERE key='fan_confidence'").fetchone(); fan_before = int((_fr["value"] if _fr else 55) or 0); c.close()
w.fin_ticket_spin.setValue(25); q.processEvents()
preview_forecast = w.fin_ticket_forecast.text()
preview_total = w.fin_exploit_total.text()
w.fin_ticket_apply_btn.click(); q.processEvents()
c = app.db()
new_price = int(c.execute("SELECT ticket_price FROM facility WHERE id=1").fetchone()["ticket_price"] or 0)
fan_after = int((c.execute("SELECT value FROM meta WHERE key='fan_confidence'").fetchone() or {"value": 55})["value"] or 0)
c.close()
assert new_price == 25, new_price
assert w.fin_ticket_spin.value() == 25
assert w.fin_ticket_forecast.text() == preview_forecast, (preview_forecast, w.fin_ticket_forecast.text())
assert w.fin_exploit_total.text() == preview_total, (preview_total, w.fin_exploit_total.text())
assert fan_after == fan_before, (fan_before, fan_after)
assert w.finance_tabs.currentIndex() == 1 and w.stack.currentIndex() == 9
print("8) tarif appliqué:", new_price, "€ · affluence stable ·", preview_forecast.split(" • ")[0])

w.close(); q.processEvents()
size = os.path.getsize(r"C:\FM2027V2\data\error.log")
assert size == 0, size
print("RESULT: ALL OK")
