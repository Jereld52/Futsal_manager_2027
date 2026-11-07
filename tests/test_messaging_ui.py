# -*- coding: utf-8 -*-
"""Messagerie refondue : filtres, tri, lecture et options."""
import os, sys, tempfile, json
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app, ui_components

TMP = tempfile.mkdtemp(prefix="fm_msgui_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP; app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=3,
            identity={"name": "Mail FC", "arena_name": "Halle", "color1": "#c47220",
                      "color2": "#14171f", "division": 3})

conn = app.db()
msgs = [
    ("transfer_sale", "Offre reçue de CS Berlin", "CS Berlin propose 120 000 € pour Alexis Janssens.", "ready",
     {"player_id": 1, "player_name": "Alexis Janssens", "buyer_name": "CS Berlin", "fee": 120000,
      "interest_reason": "Haut de tableau • objectif top 3"}),
    ("contract_offer", "Prolongation de Nuno Silva", "Nouveau contrat de 3 ans proposé.", "ready",
     {"player_id": 2, "player_name": "Nuno Silva", "offer_salary": 4200, "offer_years": 3}),
    ("scout_report", "Rapport de Marco Rossi", "Observation approfondie terminée.", "ready",
     {"player_id": 3, "player_name": "Marco Rossi"}),
    ("match_report", "Rapport du match", "Victoire 4-2.", "ready", {}),
    ("club_news", "Le board fait le point", "La confiance reste stable.", "handled", {}),
    ("training_injury", "Blessure à l'entraînement", "Absent 8 jours.", "handled", {}),
    ("season_summary", "Bilan de la saison", "Le club termine 6e.", "handled", {}),
    ("system", "Sauvegarde automatique", "Sauvegarde mise à jour.", "handled", {}),
    ("media", "Rumeur de transfert", "Un club surveille ton pivot.", "handled", {}),
    ("market_offer", "Négociation en cours", "Le club vendeur étudie ton offre.", "waiting",
     {"player_id": 4, "player_name": "Ivan Petrov", "buyer_name": "SC Paris", "fee": 90000}),
]
for kind, title, body, status, data in msgs:
    conn.execute("""INSERT INTO manager_message(kind,title,body,created_date,due_date,status,action_data,is_read)
                    VALUES(?,?,?,?,?,?,?,?)""",
                 (kind, title, body, "2026-09-10", "2026-09-14", status, json.dumps(data),
                  0 if kind in ("transfer_sale", "contract_offer", "scout_report", "match_report") else 1))
conn.commit(); conn.close()

from PySide6.QtWidgets import QApplication, QToolButton, QTabWidget
q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
app.MainWindow.show_game_message = lambda self, *a, **k: True
w = app.MainWindow(); w.resize(1360, 900); w.show()
w.app_stack.setCurrentWidget(w.game_shell); q.processEvents(); w.show_page(6); q.processEvents()

assert w.action_message_list.count() == 9, w.action_message_list.count()
assert "4 non lu" in w.msg_hero_sub.text()
labels = {k: w.msg_folder_names[k].text() for k in w.msg_filter_chips}
counts = {k: w.msg_folder_counts[k].text() for k in w.msg_filter_chips}
print("dossiers:", labels, counts)
assert labels["dossiers"] == "Dossiers"
assert counts["dossiers"] == "3"
assert labels["unread"] == "Non lus"
assert counts["unread"] == "4"

# Boîte mail : adresse du club, rail visible en grand écran, expéditeurs.
assert "@" in w.mail_club_address and w.mail_club_address.endswith(".fm")
assert w.mail_rail.isVisible()
assert w.mail_folder_title.text() == "Boîte de réception"
sender = w.action_message_list.item(0).data(ui_components.MessageListDelegate.ROLE_SENDER)
assert sender, "expéditeur manquant"
print("boîte mail:", w.mail_club_address, "| expéditeur:", sender)

w._set_message_filter("dossiers"); q.processEvents()
assert w.action_message_list.count() == 3
assert w.mail_folder_title.text() == "Dossiers"
w.msg_search.setText("contrat"); q.processEvents()
assert w.action_message_list.count() == 1
w.msg_search.clear(); w._set_message_filter("all"); q.processEvents()

# Mode étroit : le rail laisse la place au sélecteur de dossier.
w.resize(1000, 700); q.processEvents(); w._fit_mail_layout(); q.processEvents()
assert not w.mail_rail.isVisible() and w.mail_folder_combo.isVisible()
assert w.mail_overflow_btn.isVisible()
actions = [a.text() for a in w.mail_overflow_btn.menu().actions()]
assert "Historique" in actions and "Purger la boîte" in actions, actions
w.mail_folder_combo.setCurrentIndex(w.mail_folder_combo.findData("dossiers")); q.processEvents()
assert w.msg_filter == "dossiers" and w.action_message_list.count() == 3
w._set_message_filter("all")
w.resize(1360, 900); q.processEvents(); w._fit_mail_layout(); q.processEvents()
assert w.mail_rail.isVisible()
assert not w.mail_overflow_btn.isVisible()
print("mode étroit: OK")

# Tri prioritaires : les messages à traiter d'abord.
w.msg_sort.setCurrentText("Prioritaires"); q.processEvents()
first_status = w.action_message_list.item(0).data(ui_components.MessageListDelegate.ROLE_STATUS)
assert first_status in ("ready", "report"), first_status
w.msg_sort.setCurrentText("Plus récents"); q.processEvents()

# Sélection d'une offre : détail + actions.
row = next(i for i in range(w.action_message_list.count())
           if w.action_message_list.item(i).data(ui_components.MessageListDelegate.ROLE_KIND) == "VENTE")
w.action_message_list.setCurrentRow(row); q.processEvents()
detail = w.action_message_detail.toPlainText()
assert "Alexis Janssens" in detail and "120 000" in detail, detail[:200]
buttons = [b.text() for b in w.msg_action_bar.parentWidget().findChildren(app.QPushButton)]
assert "ACCEPTER" in buttons and "REFUSER" in buttons
assert any(isinstance(b, QToolButton) and b.text() == "PLUS" for b in w.msg_action_bar.parentWidget().findChildren(QToolButton))
print("détail et actions: OK")

# Marquer non lu : le message doit rester non lu après resynchronisation.
mid = w.action_message_list.currentItem().data(app.Qt.UserRole)
w._mark_message_unread(mid); q.processEvents()
conn = app.db(); state = conn.execute("SELECT is_read FROM manager_message WHERE id=?", (int(mid),)).fetchone()["is_read"]; conn.close()
print("marqué non lu:", state)
assert int(state) == 0

# Options : famille masquée + lecture.
w.game_options["msg_cat_matchs"] = False
w._refresh_messages_ui(); q.processEvents()
assert w.action_message_list.count() == 8
w.game_options["msg_cat_matchs"] = True
w.game_options["msg_mark_read"] = False
conn = app.db(); conn.execute("UPDATE manager_message SET is_read=0 WHERE kind='contract_offer'"); conn.commit(); conn.close()
w._refresh_messages_ui(); q.processEvents()
row = next(i for i in range(w.action_message_list.count())
           if w.action_message_list.item(i).data(ui_components.MessageListDelegate.ROLE_KIND) == "CONTRAT")
if w.action_message_list.currentRow() == row:
    w._on_message_selected(row)
else:
    w.action_message_list.setCurrentRow(row)
q.processEvents()
conn = app.db(); state = conn.execute("SELECT is_read FROM manager_message WHERE kind='contract_offer'").fetchone()["is_read"]; conn.close()
print("lecture sans marquer lu:", state)
assert int(state) == 0
w.game_options["msg_mark_read"] = True

# Options : thème clair retiré + nouvelles cases présentes.
opts_dlg = ui_components.GameOptionsDialog(w.game_options, w)
themes = [opts_dlg.theme.itemText(i) for i in range(opts_dlg.theme.count())]
print("thèmes:", themes)
assert "Clair" not in themes
assert hasattr(opts_dlg, "msg_category_boxes") and len(opts_dlg.msg_category_boxes) == 7
val_ids = opts_dlg.values()
assert "msg_cat_dossiers" in val_ids and "msg_mark_read" in val_ids
# Nouvelle famille : offres de club confidentielles (SECRET).
assert "msg_cat_carriere" in val_ids and val_ids["msg_cat_carriere"] is True
assert "msg_cat_carriere" in opts_dlg.msg_category_boxes
opts_dlg.deleteLater()

# Ancienne option « Clair » : repli propre sur le thème sombre.
import json
old_file = app.OPTIONS_FILE
tmp_opts = os.path.join(TMP, "options_clair.json")
with open(tmp_opts, "w", encoding="utf-8") as fh:
    json.dump({"theme": "Clair"}, fh)
app.OPTIONS_FILE = tmp_opts
try:
    fallback = app.load_game_options()
finally:
    app.OPTIONS_FILE = old_file
print("ancien thème Clair ->", fallback["theme"])
assert fallback["theme"] == "Nuit violette"

w.close()
print("RESULT: ALL OK")
