# -*- coding: utf-8 -*-
"""Pré-contrats de bout en bout : signature hiver -> arrivée à la nouvelle saison.

Couvre aussi les annulations (joueur transféré, contrat prolongé) et l'exclusion
des joueurs pré-signés des offres « fin de contrat ».
"""
import os, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication

TMP = tempfile.mkdtemp(prefix="fm_preseason_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP
app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=2,
            identity={"name": "PreSeason FC", "arena_name": "A", "color1": "#2f6fed",
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
c.execute("UPDATE career SET current_date='2027-01-15' WHERE id=1")
c.execute("UPDATE player SET contract_years=2 WHERE club_id=1")
# Trois cibles : deux pré-contrats valides, une qui sera annulée.
targets = c.execute("""SELECT id,contract_years,club_id FROM player
                       WHERE club_id<>1 AND is_free_agent=0 AND COALESCE(retired,0)=0
                         AND age<30 AND contract_years<=1
                       ORDER BY id LIMIT 3""").fetchall()
c.commit(); c.close()
assert len(targets) == 3, len(targets)
ids = [int(t["id"]) for t in targets]

w.counter_terms_dialog = lambda *a, **k: {"amount": 2100, "years": 2}
signed = [w.sign_precontract(pid) for pid in ids]
assert all(signed), signed
print("offres de pré-contrat envoyées:", signed)

# Les offres sont désormais en réflexion : on tranche la première (acceptée).
c = app.db()
offer0 = c.execute("SELECT * FROM precontract_offer WHERE player_id=?", (ids[0],)).fetchone()
pending0 = c.execute("SELECT precontract_club FROM player WHERE id=?", (ids[0],)).fetchone()
assert offer0 is not None and str(offer0["status"]) == "waiting", dict(offer0) if offer0 else None
assert int(pending0["precontract_club"] or 0) == 0, "aucune signature immédiate"
assert w.finalize_precontract(c, offer0, True) is True
c.commit(); c.close()
print("décision du joueur 1 : acceptée")

# A) le joueur 2 est transféré dans un autre club -> pré-contrat annulé.
c = app.db()
other = c.execute("SELECT id FROM club WHERE id<>1 AND id<>?", (int(targets[1]["club_id"]),)).fetchone()["id"]
c.execute("UPDATE player SET club_id=? WHERE id=?", (int(other), ids[1]))
# B) le joueur 3 prolonge son contrat -> pré-contrat annulé à la clôture.
c.execute("UPDATE player SET contract_years=3 WHERE id=?", (ids[2],))
c.commit(); c.close()

# Exclusion des offres « fin de contrat » pour un joueur déjà pré-signé.
c = app.db()
for pid in (ids[0],):
    for _ in range(120):
        w.generate_transfer_interest(c, "2027-01-15")
    bad = c.execute("""SELECT COUNT(*) n FROM manager_message
                       WHERE kind='transfer_sale' AND status IN ('waiting','ready')
                       AND action_data LIKE ?""", (f'%"player_id": {pid}%',)).fetchone()["n"]
    assert int(bad) == 0, ("offre pour un joueur pré-signé", bad)
c.rollback(); c.close()
print("offres fin de contrat: joueur pré-signé exclu")

# Clôture de saison : le joueur 1 doit arriver, les deux autres non.
# Raccourci de test : on retire les matchs non joués (la clôture exige une
# saison complète ; le moteur de matchs est couvert par les autres suites).
c = app.db()
c.execute("DELETE FROM fixture WHERE played=0")
c.execute("UPDATE career SET current_date='2027-06-30' WHERE id=1")
c.commit(); c.close()
before = app.db()
squad_before = before.execute("SELECT COUNT(*) n FROM player WHERE club_id=1").fetchone()["n"]
before.close()
assert w.start_new_season() is True
c = app.db()
joined = c.execute("""SELECT * FROM player WHERE id=? AND club_id=1 AND COALESCE(precontract_club,0)=0""",
                   (ids[0],)).fetchone()
assert joined is not None, "le pré-contrat valide doit rejoindre le club"
# Durée convenue = 2 ans. Le moteur crédite +1 à l'arrivée car la décrémentation
# globale de fin de saison s'applique ensuite : le solde doit valoir 2.
assert int(joined["contract_years"] or 0) == 2, joined["contract_years"]
assert int(joined["salary"] or 0) == 2100, joined["salary"]
for pid in ids[1:]:
    row = c.execute("SELECT club_id,precontract_club,precontract_from FROM player WHERE id=?", (pid,)).fetchone()
    assert int(row["club_id"]) != 1, ("pré-contrat annulé ne doit pas rejoindre", pid)
    assert int(row["precontract_club"] or 0) == 0, ("champs pré-contrat nettoyés", pid)
squad_after = c.execute("SELECT COUNT(*) n FROM player WHERE club_id=1").fetchone()["n"]
hist = c.execute("""SELECT COUNT(*) n FROM player_history WHERE player_id=? AND club_id=1 AND kind='free'""",
                 (ids[0],)).fetchone()["n"]
c.close()
assert int(squad_after) >= int(squad_before), (squad_before, squad_after)
assert int(hist) >= 1, "historique d'arrivée manquant"
print("arrivée effective:", joined["first_name"], joined["last_name"], "| effectif", squad_before, "->", squad_after)

# Le bandeau ne doit plus rien afficher après la clôture.
w.show_page(7); q.processEvents()
w._refresh_offers_tab(); q.processEvents()
assert getattr(w, "precontract_strip", None) is None or w.precontract_strip.isHidden()
print("bandeau pré-contrats vidé")

w.close(); q.processEvents()
size = os.path.getsize(r"C:\FM2027V2\data\error.log")
assert size == 0, size
print("RESULT: ALL OK")
