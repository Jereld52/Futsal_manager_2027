# -*- coding: utf-8 -*-
"""Effectif / transferts : états filtrables, pré-contrats hiver et visibilité."""
import os, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication

TMP = tempfile.mkdtemp(prefix="fm_contracts_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP
app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=2,
            identity={"name": "Contrat FC", "arena_name": "A", "color1": "#2f6fed",
                      "color2": "#101a2e", "division": 2})

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
w = app.MainWindow()
w.setAttribute(app.Qt.WA_DontShowOnScreen, True)
w.show_game_message = lambda *a, **k: True
app.QDialog.exec = lambda self, *a, **k: 1
w.resize(1500, 950)
w.show(); q.processEvents()
w.app_stack.setCurrentWidget(w.game_shell)

c = app.db()
ids = [int(r["id"]) for r in c.execute("SELECT id FROM player WHERE club_id=1 ORDER BY id LIMIT 5").fetchall()]
c.execute("UPDATE player SET injury_days=5 WHERE id=?", (ids[0],))
c.execute("UPDATE player SET suspension_matches=2 WHERE id=?", (ids[1],))
c.execute("UPDATE player SET transfer_listed=1 WHERE id=?", (ids[2],))
c.execute("UPDATE player SET condition=40 WHERE id=?", (ids[3],))
c.commit(); c.close()

# 1) Colonne ETAT lisible + filtres.
w.show_page(1); q.processEvents()
assert w.roster_table.columnWidth(0) >= 80, w.roster_table.columnWidth(0)
for label, shown in (("Blessés", "BLESSÉ"), ("Suspendus", "SUSPENDU"),
                     ("Sur le marché", "MARCHÉ"), ("Fatigués", "FATIGUÉ")):
    w.roster_status_filter.setCurrentText(label); q.processEvents()
    assert w.roster_table.rowCount() >= 1, label
    texts = [w.roster_table.item(r, 0).text() for r in range(w.roster_table.rowCount())]
    assert all(shown in t for t in texts), (label, texts)
print("OK états et filtres :", [w.roster_status_filter.itemText(i) for i in range(w.roster_status_filter.count())])

# 2) Pré-contrat au mercato d'hiver (dernière année) + refus à 2 ans.
c = app.db()
c.execute("UPDATE career SET current_date='2027-01-15' WHERE id=1")
c.commit()
tgt = c.execute("""SELECT id FROM player WHERE club_id<>1 AND is_free_agent=0
                   AND contract_years<=1 ORDER BY id LIMIT 1""").fetchone()
c.close()
w.counter_terms_dialog = lambda *a, **k: {"amount": 2200, "years": 2}
assert w.sign_precontract(int(tgt["id"])) is True
c = app.db()
c.execute("UPDATE player SET contract_years=2 WHERE club_id<>1 AND id<>?", (int(tgt["id"]),))
c.commit()
t2 = c.execute("SELECT id FROM player WHERE club_id<>1 AND contract_years=2 AND id<>? LIMIT 1", (int(tgt["id"]),)).fetchone()
c.close()
assert w.sign_precontract(int(t2["id"])) is False
print("OK pré-contrat hiver (1 an) accepté, 2 ans refusé")

# 3) Visibilité des pré-contrats dans l'onglet OFFRES.
w.show_page(7); q.processEvents()
w.mercato_tabs.setCurrentIndex(0)
w._refresh_offers_tab(); q.processEvents()
assert w.precontract_strip is not None and not w.precontract_strip.isHidden()
assert "PRÉ-CONTRAT" in w.precontract_title.text()
print("OK bandeau pré-contrats :", w.precontract_title.text())

# 4) Offres IA pour un joueur à un an de contrat.
c = app.db()
c.execute("DELETE FROM manager_message WHERE kind='transfer_sale'")
c.execute("UPDATE player SET transfer_listed=0 WHERE club_id=1")
c.execute("UPDATE player SET contract_years=1 WHERE club_id=1")
c.execute("UPDATE career SET current_date='2026-08-10' WHERE id=1")
c.commit(); c.close()
found = 0
for _ in range(70):
    c = app.db(); w.generate_transfer_interest(c, "2026-08-10"); c.commit()
    found = int(c.execute("""SELECT COUNT(*) n FROM manager_message WHERE kind='transfer_sale'
                             AND action_data LIKE '%"expiring": true%'""").fetchone()["n"])
    c.close()
    if found:
        break
assert found >= 1
print("OK offres fin de contrat :", found)

w.close(); q.processEvents()
size = os.path.getsize(os.path.join(r"C:\FM2027V2\data", "error.log"))
assert size == 0, size
print("RESULT: ALL OK")
