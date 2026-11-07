# -*- coding: utf-8 -*-
"""Audit de la messagerie : dossiers, états, actions, recherche, immersion.

Vérifie qu'un message de chaque type tombe dans le bon dossier, que les
dossiers clos ne sont plus « à traiter » (ni boutons d'action), que les
expéditeurs sont crédibles, et que la liste/recherche/compteurs restent
cohérents.
"""
import json
import os
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication, QPushButton

TMP = tempfile.mkdtemp(prefix="fm_msgaudit_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP
app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=2,
            identity={"name": "Mail FC", "arena_name": "A", "color1": "#2f6fed",
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

DAY = "2026-09-12"

# (kind, titre, corps, catégorie attendue, statut, outcome, données)
CORPUS = [
    ("market_offer", "Offre de transfert • SC Paris",
     "SC Paris propose 12 000 € pour Amadou Diomandé, plus un contrat de 2 100 €/mois.",
     "dossiers", "ready", "", {"player_id": 1, "player_name": "Amadou Diomandé",
                               "buyer_name": "SC Paris", "fee": 12000, "offer_salary": 2100,
                               "offer_years": 3}),
    ("market_offer", "Mercato • accord au prix demandé",
     "Le club accepte de vendre Amadou Diomandé à son prix demandé : 15 000 €.",
     "dossiers", "ready", "accepted", {"player_id": 1, "player_name": "Amadou Diomandé",
                                       "buyer_name": "SC Paris", "fee": 15000}),
    ("contract_offer", "Contrat • offre acceptée",
     "L'agent de Yanis Moreau accepte ta proposition.",
     "dossiers", "ready", "accepted", {"player_id": 2, "player_name": "Yanis Moreau",
                                       "offer_salary": 2200, "offer_years": 3}),
    ("contract_offer", "Mercato • signature manquée",
     "Yanis Moreau a signé à ES Amsterdam. Ton offre est annulée.",
     "dossiers", "ready", "rival", {"player_id": 2, "player_name": "Yanis Moreau",
                                    "rival_club": "ES Amsterdam"}),
    ("contract_offer", "Contrat • contre-offre reçue",
     "L'agent de Yanis Moreau réclame 2 600 €/mois sur 3 ans.", 
     "dossiers", "ready", "counter", {"player_id": 2, "player_name": "Yanis Moreau",
                                      "counter_salary": 2600, "counter_years": 3}),
    ("transfer_sale", "Offre reçue • Stade Brestois",
     "Stade Brestois propose 8 000 € pour Théo Petit.",
     "dossiers", "ready", "refused", {"player_id": 3, "player_name": "Théo Petit",
                                      "buyer_name": "Stade Brestois", "fee": 8000}),
    ("transfer_sale_counter", "Contre-offre de vente", "Ta demande de 9 000 € est partie.",
     "dossiers", "waiting", "", {"player_id": 3, "player_name": "Théo Petit",
                                 "buyer_name": "Stade Brestois", "counter_fee": 9000}),
    ("transfer_departure", "Vente • départ à l'ouverture",
     "Théo Petit rejoindra Stade Brestois à l'ouverture du mercato.",
     "dossiers", "waiting", "", {"player_id": 3, "player_name": "Théo Petit",
                                 "buyer_name": "Stade Brestois", "fee": 8000}),
    ("transfer_arrival", "Recrutement • arrivée annoncée",
     "Amadou Diomandé quitte SC Paris pour 15 000 €. Arrivée officielle le 15/09.",
     "dossiers", "handled", "joined", {"player_id": 1, "player_name": "Amadou Diomandé",
                                       "club_name": "SC Paris", "fee": 15000}),
    ("loan_request", "Prêt accepté", "SC Paris accepte de prêter Amadou Diomandé.",
     "dossiers", "ready", "accepted", {"player_id": 1}),
    ("loan_out_request", "Prêt • réponse du club", "Le club prête Yanis Moreau.",
     "dossiers", "ready", "accepted", {"player_id": 2}),
    ("contract_departure", "Un joueur hésite à rester",
     "Théo Petit hésite à rester : temps de jeu insuffisant.", "dossiers", "handled", "",
     {"player_ids": [3]}),
    ("contract_expired", "Contrat arrivé à terme", "Le contrat de Théo Petit est terminé.",
     "dossiers", "handled", "", {"player_id": 3}),
    ("scout_digest", "Rapport mensuel • Recrutement (septembre)",
     "Le staff a observé 4 joueurs en septembre.", "scouting", "handled", "", {}),
    ("scout_report", "Rapport de scouting • Amadou Diomandé",
     "Fiche complète d'Amadou Diomandé.", "scouting", "handled", "", {"player_id": 1}),
    ("match_report", "Rapport de match • Mail FC 3-2 SC Paris",
     "Victoire 3-2 au terme d'un match engagé.", "matchs", "ready", "", {}),
    ("club_news", "Le président vous fait confiance",
     "Le board valide votre projet pour la saison.", "club", "ready", "", {}),
    ("facility_complete", "Chantier terminé • tribune",
     "La nouvelle tribune est ouverte.", "club", "handled", "", {}),
    ("training_injury", "Blessure à l'entraînement",
     "Yanis Moreau sera absent 4 jours.", "club", "handled", "", {"player_ids": [2], "days": 4}),
    ("season_summary", "Bilan de saison", "Le club termine 4e de Ligue 2.", "saison", "handled", "", {}),
    ("season_title", "Titre de saison", "Vous êtes champion !", "saison", "handled", "", {}),
    ("season_break", "Trêve hivernale", "Reprise le 10 janvier.", "saison", "handled", "", {}),
    ("season_ready", "Saison terminée", "La nouvelle saison peut commencer.", "saison", "ready", "", {}),
    ("job_offer", "Offre confidentielle • Real Munich",
     "Un club de Ligue 1 vous propose un entretien.", "carriere", "ready", "",
     {"club_name": "Real Munich"}),
    ("media", "La presse en parle", "Votre début de saison intrigue.", "presse", "handled", "", {}),
    ("system", "Sauvegarde effectuée", "La partie a été sauvegardée.", "systeme", "handled", "", {}),
]

c = app.db()
c.execute("DELETE FROM manager_message")
c.commit(); c.close()
for kind, title, body, _cat, status, outcome, data in CORPUS:
    c = app.db()
    payload = dict(data)
    if outcome:
        payload["outcome"] = outcome
    app.queue_manager_message(c, kind, title, body, DAY, DAY, payload,
                              is_read=(status != "ready"), ready=(status == "ready"))
    c.commit()
    mid = int(c.execute("SELECT id FROM manager_message ORDER BY id DESC LIMIT 1").fetchone()["id"])
    if status != "ready":
        c.execute("UPDATE manager_message SET status=? WHERE id=?", (status, mid))
        c.commit()
    c.close()

w.show_page(6); q.processEvents()

# ---------- 1) Chaque type tombe dans le bon dossier ----------
bad = []
for kind, _t, _b, expected, *_rest in CORPUS:
    got = w._message_category(kind)
    if got != expected:
        bad.append((kind, got, expected))
assert not bad, bad
print("1) dossiers:", len(set(c[3] for c in CORPUS)), "familles |",
      len(set(c[0] for c in CORPUS)), "types classés")

# ---------- 2) Expéditeurs crédibles ----------
for kind, *_rest in CORPUS:
    row = {"kind": kind, "action_data": "{}", "status": "ready"}
    name, address, initials, color = w._message_sender(row)
    assert name and "@" in address and initials, (kind, name, address)
print("2) expéditeurs: nom + adresse + initiales pour chaque type")

# ---------- 3) Dossiers clos non actionnables ----------
def row_of(kind, outcome, status):
    c = app.db()
    rows = c.execute("SELECT * FROM manager_message WHERE kind=? AND status=?", (kind, status)).fetchall()
    c.close()
    for r in rows:
        try:
            d = json.loads(r["action_data"] or "{}")
        except Exception:
            d = {}
        if str(d.get("outcome") or "") == outcome:
            return r
    return None

fresh = row_of("market_offer", "", "ready")
accepted = row_of("market_offer", "accepted", "ready")
rival = row_of("contract_offer", "rival", "ready")
refused = row_of("transfer_sale", "refused", "ready")
assert fresh and accepted and rival and refused
assert w._message_is_actionable(fresh) is True
assert w._message_is_actionable(accepted) is False
assert w._message_is_actionable(rival) is False
assert w._message_is_actionable(refused) is False
print("3) actionnable: offre fraîche oui ; acceptée/rival/refusée non")

# Filtre « À traiter » : seule l'offre fraîche (et le rapport de match n'est pas un dossier).
w._set_message_filter("action"); q.processEvents()
ids = [w.action_message_list.item(i).data(app.Qt.UserRole) for i in range(w.action_message_list.count())]
assert int(fresh["id"]) in ids, ids
assert int(accepted["id"]) not in ids and int(rival["id"]) not in ids and int(refused["id"]) not in ids
assert w.msg_hero_action.text() == "2", w.msg_hero_action.text()
print("4) « À traiter »:", len(ids), "dossier(s), les clos exclus")

# ---------- 4) Lecture : pastilles d'issue + boutons ----------
def select(mid):
    for i in range(w.action_message_list.count()):
        if int(w.action_message_list.item(i).data(app.Qt.UserRole)) == int(mid):
            w.action_message_list.setCurrentRow(i); q.processEvents(); return True
    return False

w._set_message_filter("all"); q.processEvents()
assert select(fresh["id"]), "offre fraîche introuvable"
buttons = [b.text() for b in w.msg_action_bar.parentWidget().findChildren(QPushButton) if b.isVisible()]
assert any("ACCEPTER" in t for t in buttons) and any("REFUSER" in t for t in buttons), buttons
html = w.action_message_detail.toHtml()
assert "À TRAITER" in html
print("5) offre fraîche: boutons", buttons[:2])

assert select(accepted["id"])
html = w.action_message_detail.toHtml()
assert "ACCEPTÉ" in html
buttons = [b.text() for b in w.msg_action_bar.parentWidget().findChildren(QPushButton) if b.isVisible()]
assert not any("ACCEPTER" in t for t in buttons), buttons
assert select(rival["id"])
html = w.action_message_detail.toHtml()
assert "SIGNÉ AILLEURS" in html
assert "ES Amsterdam" in html or "ES AMSTERDAM" in html
print("6) dossiers clos: ACCEPTÉ / SIGNÉ AILLEURS, sans boutons d'action")

counter = row_of("contract_offer", "counter", "ready")
assert counter is not None
assert select(counter["id"])
html = w.action_message_detail.toHtml()
assert "CONTRE-OFFRE" in html
buttons = [b.text() for b in w.msg_action_bar.parentWidget().findChildren(QPushButton) if b.isVisible()]
assert any("CONTRE-OFFRE" in t for t in buttons), buttons
print("7) contre-offre: pastille + bouton", [t for t in buttons if "CONTRE" in t])

# ---------- 5) Dossier, recherche, compteurs ----------
w._set_message_filter("dossiers"); q.processEvents()
dossiers = sum(1 for c0 in CORPUS if c0[3] == "dossiers")
assert w.action_message_list.count() == dossiers, (w.action_message_list.count(), dossiers)
assert w.msg_folder_counts["dossiers"].text() == str(dossiers)
w.msg_search.setText("Diomandé"); q.processEvents()
found = w.action_message_list.count()
assert found >= 1, found
w.msg_search.clear(); q.processEvents()
print("7) dossiers:", dossiers, "| recherche Diomandé:", found, "résultat(s)")

w._set_message_filter("unread"); q.processEvents()
unread_visible = w.action_message_list.count()
_badge_conn = app.db()
badge = _badge_conn.execute("SELECT COUNT(*) n FROM manager_message WHERE is_read=0 AND kind<>'scout_report'").fetchone()["n"]
_badge_conn.close()
assert int(badge) == unread_visible, (badge, unread_visible)
assert w.msg_badge.text() == str(int(badge)), (w.msg_badge.text(), badge)
assert w.message_badge_count() == int(badge), (w.message_badge_count(), badge)
print("8) non lus:", badge, "= badge = liste")

# Famille masquée dans les options : le badge et la liste doivent l'ignorer.
base_unread = int(badge)
w.game_options["msg_cat_matchs"] = False
w._refresh_messages_ui(); q.processEvents()
_c = app.db()
_unread_rows = _c.execute("SELECT kind FROM manager_message WHERE is_read=0").fetchall()
_c.close()
_match_unread = sum(1 for r in _unread_rows if w._message_category(r["kind"]) == "matchs")
assert w.message_badge_count() == base_unread - _match_unread, (
    w.message_badge_count(), base_unread, _match_unread,
    [(r["kind"], w._message_category(r["kind"])) for r in _unread_rows])
assert w.msg_badge.text() == str(base_unread - _match_unread), w.msg_badge.text()
w._set_message_filter("unread"); q.processEvents()
assert w.action_message_list.count() == base_unread - _match_unread, w.action_message_list.count()
w.game_options["msg_cat_matchs"] = True
w._refresh_messages_ui(); q.processEvents()
assert w.message_badge_count() == base_unread
print("9) famille masquée: badge et liste ignorent les messages cachés")

# ---------- 6) Hygiène du corpus ----------
c = app.db()
bad_rows = c.execute("""SELECT id,kind,title,body FROM manager_message
                        WHERE TRIM(COALESCE(title,''))='' OR TRIM(COALESCE(body,''))=''""").fetchall()
c.close()
assert not bad_rows, [dict(r) for r in bad_rows]
print("9) aucun message vide")

w.close(); q.processEvents()
size = os.path.getsize(r"C:\FM2027V2\data\error.log")
assert size == 0, size
print("RESULT: ALL OK")
