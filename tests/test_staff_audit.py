# -*- coding: utf-8 -*-
"""Audit du staff : coûts, effets réellement appliqués et rentabilité.

Chaque poste doit avoir un effet mesurable, payé par une transaction, et un
rapport coût/bénéfice qui ne soit pas un piège (cas du comptable).
"""
import os
import sys
import tempfile
from unittest import mock

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
import wage_budget as wb
from PySide6.QtWidgets import QApplication

TMP = tempfile.mkdtemp(prefix="fm_staffaudit_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP
app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=2,
            identity={"name": "Staff FC", "arena_name": "A", "color1": "#2f6fed",
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
w.show_page(10); q.processEvents()


def snap():
    c = app.db()
    b = int(c.execute("SELECT budget FROM club WHERE id=1").fetchone()["budget"] or 0)
    t = int(c.execute("SELECT COALESCE(SUM(amount),0) s FROM finance_tx WHERE club_id=1").fetchone()["s"] or 0)
    c.close()
    return b, t


# ---------- 1) Page : 8 postes, tous avec un effet annoncé ----------
assert len(w.staff_cards) == 8, len(w.staff_cards)
for key, info in w.staff_cards.items():
    assert info["status"].text() == "VACANT", (key, info["status"].text())
    eff = info["eff_now"].text()
    assert eff and eff != "—", (key, eff)
    assert "€" in info["cost_lbl"].full_text(), (key, info["cost_lbl"].full_text())
texts = [lbl.text() for lbl in w.staff_tabs.widget(0).findChildren(app.QLabel)]
assert "Embaucher" in texts and "Former" in texts and "Effets réels" in texts, texts[-8:]
print("1) page: 8 postes, effet + tarif affichés sur chaque carte")

# ---------- 2) Comptable : embauche payée, puis rentable (paie + placements) ----------
b0, t0 = snap()
assert w.hire_generic_staff("comptable_hired", "comptable", 22000) is not False
q.processEvents(); w._staff_refresh(); q.processEvents()
b1, t1 = snap()
assert b1 - b0 == -22000, (b1 - b0)
assert b1 == t1, (b1, t1)
c = app.db()
tx = c.execute("SELECT label,amount,category FROM finance_tx WHERE club_id=1 AND category='Staff' ORDER BY id DESC LIMIT 1").fetchone()
placement = w.comptable_placement_monthly(c)
salary = w.staff_effective_salary(c, "comptable_hired")
st = wb.status(w, c)
c.close()
assert tx and tx["category"] == "Staff" and "comptable" in tx["label"].lower() and int(tx["amount"]) == -22000, dict(tx) if tx else None
assert placement > 0 and salary == 2200 and st["staff"] == 2100, (placement, salary, st["staff"])
saving = salary - st["staff"]
assert placement + saving > salary, (placement, saving, salary)
info = w.staff_cards["comptable_hired"]
assert info["status"].text() == "EN POSTE"
assert "placements" in info["eff_now"].text(), info["eff_now"].text()
assert info["eff_next"].isVisible() and info["eff_next"].text().startswith("→ niv. 2"), info["eff_next"].text()
assert "REMISE COMPTABLE" in w.staff_hero_grade.text(), w.staff_hero_grade.text()
print(f"2) comptable: 22 000 € · placement {placement} €/mois + remise {saving} € > salaire {salary} €")

# ---------- 3) Paie : salaires remisés + placements crédités, budget = transactions ----------
c = app.db()
b_before, t_before = snap()
before_staff = wb.staff_bill(w, c)
w.process_staff_payroll(c, "2026-12-01")
c.commit()
pay = c.execute("SELECT amount FROM finance_tx WHERE club_id=1 AND category='Salaire' AND label LIKE 'Salaires du staff%'").fetchone()
place = c.execute("SELECT amount FROM finance_tx WHERE club_id=1 AND label LIKE 'Placements du comptable%'").fetchone()
b_after = int(c.execute("SELECT budget FROM club WHERE id=1").fetchone()["budget"] or 0)
t_after = int(c.execute("SELECT COALESCE(SUM(amount),0) s FROM finance_tx WHERE club_id=1").fetchone()["s"] or 0)
c.close()
assert pay and -int(pay["amount"]) == before_staff, (dict(pay) if pay else None, before_staff)
assert place and int(place["amount"]) == w.comptable_placement_monthly(app.db())
assert b_after - b_before == int(place["amount"]) - before_staff, (b_after - b_before, before_staff, int(place["amount"]))
assert b_after == t_after, (b_after, t_after)
print(f"3) paie: staff {before_staff} € (−remise) + placements {int(place['amount'])} € · budget = transactions")

# ---------- 4) Effets quotidiens : adjoint, marketing, directeur sportif ----------
c = app.db()
c.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('adjoint_hired','1')")
c.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('adjoint_hired_level','2')")
c.execute("UPDATE player SET condition=50 WHERE club_id=1")
c.commit()
w.process_daily_staff_effects(c, "2026-12-02")   # mercredi
c.commit()
cond = c.execute("SELECT MIN(condition) mn,MAX(condition) mx FROM player WHERE club_id=1").fetchone()
assert int(cond["mn"]) == 52 and int(cond["mx"]) == 52, (cond["mn"], cond["mx"])

c.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('marketing_hired','1')")
c.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('marketing_hired_level','3')")
c.execute("UPDATE club SET reputation=20 WHERE id=1")
c.commit()
w.process_daily_staff_effects(c, "2026-12-07")   # lundi : +2 réputation (niv. 3)
c.commit()
rep = int(c.execute("SELECT reputation FROM club WHERE id=1").fetchone()["reputation"])
assert rep == 22, rep
w.process_daily_staff_effects(c, "2026-12-08")   # mardi : rien
c.commit()
assert int(c.execute("SELECT reputation FROM club WHERE id=1").fetchone()["reputation"]) == 22

targets = [int(r["id"]) for r in c.execute("SELECT id FROM player WHERE club_id<>1 ORDER BY id LIMIT 3").fetchall()]
for t in targets:
    c.execute("INSERT OR REPLACE INTO shortlist(player_id,added_date,added_value,added_knowledge) VALUES(?, '2026-12-01', 0, 0)", (t,))
c.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('directeur_sportif_hired','1')")
c.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('directeur_sportif_hired_level','4')")
c.commit()
w.process_daily_staff_effects(c, "2026-12-14")   # lundi : +2 × 4 connaissance sur les cibles
c.commit()
know = c.execute("SELECT player_id,knowledge FROM scout_report WHERE player_id IN (?,?,?)", tuple(targets)).fetchall()
c.close()
assert len(know) == 3 and all(int(r["knowledge"]) == 8 for r in know), [dict(r) for r in know]
now, _nxt = w._staff_effect_texts("directeur_sportif_hired", 4)
assert "+8/lundi sur 8 cibles" in now, now
print("4) effets: adjoint +2 forme/j, marketing +2 réputation le lundi, DS +8 connaissance sur 3 cibles")

# ---------- 5) Recruteur : la formation ne brade pas la mise à niveau officielle ----------
c = app.db()
c.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('scout_staff_hired','1')")
c.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('scout_level','1')")
c.commit(); c.close()
w.scout_level = 1; w.scout_staff_hired = True
w._staff_refresh(); q.processEvents()
scout = w.staff_cards["scout_staff_hired"]
assert scout["train"].text() == "AMÉLIORER" and scout["train"].isEnabled(), scout["train"].text()
assert "mise à niveau 30 000 €" in scout["cost_lbl"].full_text(), scout["cost_lbl"].full_text()
b0, t0 = snap()
assert w._staff_train_action("scout_staff_hired", "Recruteur") is not False
q.processEvents()
b1, t1 = snap()
c = app.db()
lvl = c.execute("SELECT value FROM meta WHERE key='scout_level'").fetchone()["value"]
cheap = c.execute("SELECT COUNT(*) n FROM finance_tx WHERE club_id=1 AND label LIKE 'Formation Recruteur%'").fetchone()["n"]
txs = c.execute("SELECT label,amount FROM finance_tx WHERE club_id=1 AND category='Staff' ORDER BY id DESC LIMIT 1").fetchone()
c.close()
assert b1 - b0 == -30000, (b1 - b0)
assert b1 == t1, (b1, t1)
assert int(lvl) == 2, lvl
assert int(cheap) == 0, cheap
assert "scouting niveau 2" in txs["label"], dict(txs)
print("5) recruteur: mise à niveau au tarif officiel (30 000 €), pas de formation à 3 200 €")

# ---------- 6) Architecte : devis, délais et places de chantier ----------
base_cost, base_days = w.facility_upgrade_terms("medical_level", 1)
base_slots = w.facility_project_capacity()
b0, t0 = snap()
assert w.hire_architect() is not False
q.processEvents()
b1, t1 = snap()
assert b1 - b0 == -32000 and b1 == t1, (b1 - b0, b1, t1)
c = app.db()
c.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('architecte_level','3')")
c.commit(); c.close()
cost, days = w.facility_upgrade_terms("medical_level", 1)
slots = w.facility_project_capacity()
assert cost < base_cost and days < base_days, (cost, base_cost, days, base_days)
assert slots == base_slots + 3, (slots, base_slots)
now, nxt = w._staff_effect_texts("architecte_hired", 3)
assert "4 chantiers" in now, now
print(f"6) architecte: devis {base_cost}→{cost} €, délai {base_days}→{days} j, {slots} chantiers")

# ---------- 7) Préparateur physique : +10 %/niveau et planification ----------
b0, t0 = snap()
assert w.hire_physical_trainer() is not False
q.processEvents()
b1, t1 = snap()
assert b1 - b0 == -30000 and b1 == t1, (b1 - b0, b1, t1)
p0 = app.training_growth_probability(70, "Normale", .62, 22, 1.0, 1.0)
p1 = app.training_growth_probability(70, "Normale", .62, 22, 1.0, 1.10)
p5 = app.training_growth_probability(70, "Normale", .62, 22, 1.0, 1.50)
assert abs(p1 / p0 - 1.10) < .01 and abs(p5 / p0 - 1.50) < .01, (p0, p1, p5)
now, nxt = w._staff_effect_texts("preparateur_physique_hired", 1)
assert "+10 %" in now and "+20 %" in nxt, (now, nxt)
c = app.db()
c.execute("DELETE FROM training_session")
c.commit(); c.close()
w._autofill_missing_week("2026-12-16")
c = app.db()
planned = c.execute("SELECT COUNT(*) n FROM training_session WHERE completed=0").fetchone()["n"]
c.close()
assert int(planned) >= 5, planned
print(f"7) préparateur: progression ×{p1/p0:.2f} (niv.1) ×{p5/p0:.2f} (niv.5), {planned} séances planifiées")

# ---------- 8) Kiné : protocole payé, soin réel ----------
b0, t0 = snap()
assert w.hire_physiotherapist() is not False
q.processEvents()
b1, t1 = snap()
assert b1 - b0 == -30000 and b1 == t1, (b1 - b0, b1, t1)
c = app.db()
pid = int(c.execute("SELECT id FROM player WHERE club_id=1 ORDER BY id LIMIT 1").fetchone()["id"])
c.execute("UPDATE player SET injury_days=10, condition=60 WHERE id=?", (pid,))
c.execute("DELETE FROM squad_action_log WHERE action_key='physio'")
c.commit(); c.close()
b0, t0 = snap()
with mock.patch.object(app.random, "random", return_value=0.0):
    assert w.send_player_to_physio(pid) is True
q.processEvents()
b1, t1 = snap()
c = app.db()
p = c.execute("SELECT injury_days,condition FROM player WHERE id=?", (pid,)).fetchone()
med = c.execute("SELECT amount FROM finance_tx WHERE club_id=1 AND category='Médical' ORDER BY id DESC LIMIT 1").fetchone()
c.close()
assert int(p["injury_days"]) == 9, p["injury_days"]
assert int(p["condition"]) == 66, p["condition"]
assert med and int(med["amount"]) == -2100, dict(med) if med else None
assert b1 - b0 == -2100 and b1 == t1, (b1 - b0, b1, t1)
now, nxt = w._staff_effect_texts("physio_hired", 3)
assert "−2 j" in now and "+6 pts" in now, now
print("8) kiné: blessure 10→9 j, forme 60→66, protocole 2 100 € enregistré")

# ---------- 9) Paie complète : la remise comptable s'applique à tout le staff ----------
c = app.db()
st = wb.status(w, c)
gross = sum(w.staff_effective_salary(c, key) for key in w.STAFF_BASE_SALARY
            if (c.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone() or {"value": "0"})["value"] == "1")
w.process_staff_payroll(c, "2027-01-01")
c.commit()
pay = c.execute("SELECT amount FROM finance_tx WHERE club_id=1 AND category='Salaire' AND label LIKE 'Salaires du staff · mois 01%'").fetchone()
b_after = int(c.execute("SELECT budget FROM club WHERE id=1").fetchone()["budget"] or 0)
t_after = int(c.execute("SELECT COALESCE(SUM(amount),0) s FROM finance_tx WHERE club_id=1").fetchone()["s"] or 0)
c.close()
assert pay and -int(pay["amount"]) == st["staff"], (dict(pay) if pay else None, st["staff"])
assert b_after == t_after, (b_after, t_after)
assert st["staff"] < gross, (st["staff"], gross)
print(f"9) paie complète: {st['staff']} € remisés (brut {gross} €), budget = transactions")

w.close(); q.processEvents()
assert os.path.getsize(r"C:\FM2027V2\data\error.log") == 0
print("RESULT: ALL OK")
