# -*- coding: utf-8 -*-
"""Éditeur de sauvegarde : cœur (SQL) et interface (hors écran).

Aucune sauvegarde réelle n'est modifiée : tout se passe sur une base neuve
générée dans un dossier temporaire.
"""
import importlib.util
import os
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

TMP = tempfile.mkdtemp(prefix="fm_editor_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
DB = os.path.join(TMP, "saves", "editeur.db")
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = DB
app.DB_PATH = DB
app.DATA_DIR = TMP
app.BASE_DIR = TMP
app.active_save_path = lambda: DB
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=2,
            identity={"name": "Editor FC", "arena_name": "Halle", "color1": "#2f6fed",
                      "color2": "#14171f", "division": 2})

spec = importlib.util.spec_from_file_location(
    "editeur_sauvegarde", r"C:\FM2027V2\editeur\editeur_sauvegarde.py")
ed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ed)

store = ed.SaveStore(DB)
assert not store.read_only, store.lock_message
assert len(store.clubs()) == 60, len(store.clubs())
players = store.players()
assert len(players) > 100, len(players)
assert len(store.staff()) == 8
print("1) ouverture : 60 clubs, %d joueurs, 8 postes de staff" % len(players))

# ---------- club ----------
store.update_club(1, 12_345_678, 88, 2, "Arena Test")
club = store.club(1)
assert int(club["budget"]) == 12_345_678
assert int(club["reputation"]) == 88 and int(club["division"]) == 2
assert club["arena_name"] == "Arena Test"
print("2) club : budget, réputation, division et salle enregistrés")

# ---------- infrastructures ----------
levels = {k: low for k, _l, low, _h in ed.FACILITY_LEVELS}
levels.update({"arena_level": 7, "medical_level": 6, "youth_level": 5,
               "video_level": 2, "restaurant_level": 3})
flags = {k: True for k, _l in ed.FACILITY_FLAGS}
store.update_facility(levels, flags, 21)
fac = store.facility()
assert int(fac["arena_level"]) == 7 and int(fac["medical_level"]) == 6
assert int(fac["video_level"]) == 2 and int(fac["ticket_price"]) == 21
assert all(int(fac[k]) == 1 for k, _l in ed.FACILITY_FLAGS)
print("3) infrastructures : niveaux, équipements et tarif enregistrés")

# ---------- baisse volontaire malgré un historique haut ----------
store.conn.execute("UPDATE facility SET arena_level=8,medical_level=8 WHERE id=1")
store.conn.execute("""INSERT INTO facility_project(facility_key,label,target_level,cost,duration_days,
                       start_date,due_date,status,completed_date)
                       VALUES('arena_level','Ancien chantier',8,0,0,'2020-01-01','2020-01-02','completed','2020-01-02')""")
store.conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('facility_max_arena_level','8')")
store.conn.commit()
low_levels = {k: low for k, _l, low, _h in ed.FACILITY_LEVELS}
low_levels.update({"arena_level": 3, "medical_level": 2, "video_level": 0,
                   "volunteer_level": 0, "restaurant_level": 0})
store.update_facility(low_levels, {k: False for k, _l in ed.FACILITY_FLAGS}, 15)
fac = store.facility()
assert int(fac["arena_level"]) == 3 and int(fac["medical_level"]) == 2, dict(fac)
assert int(fac["video_level"]) == 0 and int(fac["has_shop"]) == 0
cap = store.conn.execute(
    "SELECT value FROM meta WHERE key='facility_editor_cap_arena_level'").fetchone()
assert cap and int(cap["value"]) == 3, cap
proj = store.conn.execute(
    "SELECT MAX(target_level) m FROM facility_project WHERE facility_key='arena_level'").fetchone()
assert int(proj["m"] or 0) <= 3, proj
print("3b) baisse d'infrastructures : plafond manuel et historique alignés")

# ---------- joueur : attributs, potentiel, transfert ----------
first = store.players("", 1)[0]
second = store.players("", 2)[0]
target_club = 2
attrs = {"technique": 20, "passing": 18, "finishing": 17, "defense": 16,
         "stamina": 19, "speed": 18, "dribble": 17, "positioning": 16, "goalkeeper": 15}
result = store.apply_player(first["id"], {
    "first_name": first["first_name"], "last_name": first["last_name"],
    "age": 22, "position": "Pivot", "nationality": "Française", "shirt_number": 77,
    "club_id": target_club, "potential": 20, "market_value": 2_500_000,
    "salary": 45_000, "contract_years": 4, "condition": 100, "morale": 90,
    "injury_matches": 0, "injury_days": 0, "suspension_matches": 0,
    "suspension_days": 0, "yellow_cards": 2, "transfer_listed": True, **attrs})
moved = store.player(first["id"])
assert int(moved["club_id"]) == target_club
assert int(moved["is_free_agent"]) == 0
assert int(moved["loan_from_club"]) == 0
assert int(moved["potential_fixed"]) == 20
assert int(moved["technique"]) == 100 and int(moved["speed"]) == 90
assert int(moved["market_value"]) == 2_500_000 and int(moved["salary"]) == 45_000
season = int(store.club(1)["season"])
base = store.conn.execute(
    "SELECT * FROM player_attr_baseline WHERE player_id=? AND season=?",
    (int(first["id"]), season)).fetchone()
assert base and int(base["technique"]) == 100, "baseline de saison non mise à jour"
print("4) joueur : attributs, potentiel, valeur, salaire et transfert validés")

# ---------- numéro de maillot déjà pris ----------
other = store.players("", target_club)[0]
if int(other["id"]) == int(first["id"]):
    other = store.players("", target_club)[1]
store.apply_player(other["id"], {
    "first_name": other["first_name"], "last_name": other["last_name"],
    "age": int(other["age"]), "position": other["position"],
    "nationality": other["nationality"], "shirt_number": 77,
    "club_id": target_club, "potential": ed.player_potential(other),
    "market_value": int(other["market_value"]), "salary": int(other["salary"]),
    "contract_years": int(other["contract_years"]), "condition": 100, "morale": 70,
    **{k: ed.rating20(other[k]) for k, _l in ed.ATTRS}})
assert int(store.player(other["id"])["shirt_number"]) == 0
print("5) numéro déjà pris : libéré automatiquement")

# ---------- joueur libre ----------
store.apply_player(other["id"], {
    "first_name": other["first_name"], "last_name": other["last_name"],
    "age": int(other["age"]), "position": other["position"],
    "nationality": other["nationality"], "shirt_number": 0, "club_id": 0,
    "potential": ed.player_potential(other), "market_value": int(other["market_value"]),
    "salary": int(other["salary"]), "contract_years": 1, "condition": 100, "morale": 70,
    **{k: ed.rating20(other[k]) for k, _l in ed.ATTRS}})
free = store.player(other["id"])
assert int(free["is_free_agent"]) == 1
print("6) joueur libre : statut enregistré sans casser le club d'origine")

# ---------- staff ----------
entries = [{"key": k, "hired": True, "level": 5, "name": "Test " + label,
            "nat": "Française"} for k, label in ed.STAFF_ROLES]
store.update_staff(entries)
staff = store.staff()
assert all(e["hired"] and e["level"] == 5 for e in staff), staff
assert all(e["name"].startswith("Test ") for e in staff)
print("7) staff : 8 postes pourvus au niveau 5 avec noms")

# ---------- valeur recalculée ----------
value = store.recompute_value(first["id"])
assert 4000 <= value <= 5_000_000, value
print("8) valeur recalculée :", ed.money(value))

# ---------- sauvegardes ----------
backup = store.backup("test")
assert os.path.isfile(backup) and os.path.getsize(backup) > 0
assert backup in store.list_backups()
assert os.path.basename(os.path.dirname(backup)) == "editeur_backups"
assert store.quick_check() == "ok"
print("9) sauvegarde de secours créée, intégrité : ok")

# ---------- filtres, export, copie de travail ----------
all_rows = store.players(include_retired=True)
pivots = ed.filter_players(all_rows, {"position": "Pivot"})
assert pivots and all(row["position"] == "Pivot" for row in pivots)
young = ed.filter_players(all_rows, {"age_max": 21})
assert young and all(int(row["age"]) <= 21 for row in young)
elite = ed.filter_players(all_rows, {"level_min": 18, "potential_min": 18})
assert all(ed.player_level(r) >= 18 and ed.player_potential(r) >= 18 for r in elite)
blessed = ed.filter_players(all_rows, {"status": "BLESSÉ"})
assert all(ed.player_status(r) == "BLESSÉ" for r in blessed)
print("10) filtres : poste, âge, niveau, potentiel, statut")

csv_path = os.path.join(TMP, "joueurs.csv")
ed.export_players_csv(csv_path, pivots[:5])
with open(csv_path, encoding="utf-8-sig") as handle:
    lines = [line for line in handle.read().splitlines() if line]
assert lines[0].startswith("ID;Prénom;Nom;Club")
assert len(lines) == 1 + min(5, len(pivots))
print("11) export CSV :", len(lines) - 1, "joueur(s)")

copy_path = os.path.join(TMP, "saves", "copie_test.db")
created = store.duplicate(copy_path)
assert os.path.isfile(created)
copy_store = ed.SaveStore(created)
assert len(copy_store.players(include_retired=True)) == len(all_rows)
copy_store.close()
print("12) copie de travail : même base, fichier indépendant")

# ---------- refus des valeurs invalides ----------
bad = {"first_name": "X", "last_name": "Y", "age": 5, "position": "Pivot",
       "nationality": "FR", "shirt_number": 1, "club_id": 1, "potential": 10,
       "market_value": 1000, "salary": 100, "contract_years": 1,
       "condition": 100, "morale": 70, **{k: 10 for k, _l in ed.ATTRS}}
for mutate in (lambda d: d.update(age=5), lambda d: d.update(technique=99),
               lambda d: d.update(club_id=99999), lambda d: d.update(potential=0)):
    data = dict(bad); mutate(data)
    try:
        store.apply_player(first["id"], data)
    except ed.SaveError:
        continue
    raise AssertionError("valeur invalide acceptée :", data)
try:
    store.update_club(1, -1, 50, 1, "X")
    raise AssertionError("budget négatif accepté")
except ed.SaveError:
    pass
print("13) valeurs hors limites refusées")

# ---------- interface hors écran ----------
q = QApplication.instance() or QApplication([])

# Le jeu doit pouvoir ouvrir la sauvegarde éditée sans erreur.
store.close()
app.DB_PATH = DB
app.active_save_path = lambda: DB
app.init_db()
app.QDialog.exec = lambda self, *a, **k: 1
gw = app.MainWindow()
gw.setAttribute(Qt.WA_DontShowOnScreen, True)
gw.show_game_message = lambda *a, **k: True
gw.resize(1600, 1000); gw.show(); q.processEvents()
gw.app_stack.setCurrentWidget(gw.game_shell); q.processEvents()
gw.refresh_all(); q.processEvents()
c = app.db()
fac = c.execute("SELECT * FROM facility WHERE id=1").fetchone()
cap = c.execute("SELECT value FROM meta WHERE key='facility_editor_cap_arena_level'").fetchone()
c.close()
assert int(fac["arena_level"]) == 3 and int(fac["medical_level"]) == 2, dict(fac)
assert int(fac["video_level"]) == 0 and int(fac["has_shop"]) == 0, dict(fac)
assert cap and int(cap["value"]) == 3, cap
gw.show_page(1); q.processEvents()
gw.close(); gw.setParent(None); gw.deleteLater(); q.processEvents()
assert os.path.getsize(r"C:\FM2027V2\data\error.log") == 0
print("14) la sauvegarde éditée s'ouvre dans le jeu sans erreur")

win = ed.EditorWindow(auto_open=False)
win.setAttribute(Qt.WA_DontShowOnScreen, True)
win.resize(1500, 900)
win.show(); q.processEvents()
assert win.open_path(DB), "ouverture UI impossible"
q.processEvents()
assert win.clubs_table.rowCount() == 60
assert win.players_table.rowCount() > 0
assert win.staff_table.rowCount() == 8
for i in range(win.tabs.count()):
    win.tabs.setCurrentIndex(i); q.processEvents()

# Filtres de colonnes dans l'interface.
win.tabs.setCurrentIndex(1); q.processEvents()
total_rows = win.players_table.rowCount()
win.f_position.setCurrentIndex(win.f_position.findData("Pivot")); q.processEvents()
assert win.players_table.rowCount() < total_rows
assert all(win.players_table.item(r, 3).text() == "Pivot"
           for r in range(win.players_table.rowCount()))
win.f_level_min.setValue(18); q.processEvents()
assert win.players_table.rowCount() < total_rows
win._reset_filters(); q.processEvents()
assert win.players_table.rowCount() == total_rows
# Tri par clic d'en-tête : valeurs numériques, pas alphabétiques.
win.players_table.sortItems(6, Qt.DescendingOrder); q.processEvents()
pots = [int(win.players_table.item(i, 6).text()) for i in range(win.players_table.rowCount())]
assert pots == sorted(pots, reverse=True), pots[:8]
win.players_table.sortItems(4, Qt.AscendingOrder); q.processEvents()
ages = [int(win.players_table.item(i, 4).text()) for i in range(win.players_table.rowCount())]
assert ages == sorted(ages), ages[:8]
win.players_table.selectRow(0); q.processEvents()
assert win._current_pid == int(win.players_table.item(0, 0).data(Qt.UserRole))
win.tabs.setCurrentIndex(0); q.processEvents()
win.clubs_table.sortItems(4, Qt.DescendingOrder); q.processEvents()
budgets = [int(win.clubs_table.item(i, 4).data(ed.SORT_ROLE))
           for i in range(win.clubs_table.rowCount())]
assert budgets == sorted(budgets, reverse=True), budgets[:5]
win.clubs_table.sortItems(1, Qt.AscendingOrder); q.processEvents()
names = [win.clubs_table.item(i, 1).text() for i in range(win.clubs_table.rowCount())]
assert names == sorted(names, key=str.casefold), names[:5]
print("15) interface : tri par en-tête (niveau, âge, budget, nom)")
win.tabs.setCurrentIndex(0); q.processEvents()
needle = str(win.store.club(1)["name"]).split()[0]
win.club_search.setText(needle); q.processEvents()
assert win.clubs_table.rowCount() >= 1
assert all(needle.casefold() in win.clubs_table.item(r, 1).text().casefold()
           for r in range(win.clubs_table.rowCount()))
win.club_search.clear(); q.processEvents()
win.tabs.setCurrentIndex(4); q.processEvents()
win._manual_backup(); q.processEvents()
assert win.backups_table.rowCount() >= 1
assert win.backup_open_path.text().endswith(".db")
print("16) interface : filtres joueurs/clubs et panneau sauvegarde")

# Actions réelles via l'interface.
win.tabs.setCurrentIndex(1); q.processEvents()
win.players_table.selectRow(0); q.processEvents()
pid = int(win.players_table.item(0, 0).data(Qt.UserRole))
win.p_attrs["technique"].setValue(19)
win._apply_player(); q.processEvents()
assert int(win.store.player(pid)["technique"]) == 95, win.store.player(pid)["technique"]
win.tabs.setCurrentIndex(3); q.processEvents()
win.fac_spins["arena_level"].setValue(6)
win._apply_facility(); q.processEvents()
assert int(win.store.facility()["arena_level"]) == 6
win.tabs.setCurrentIndex(2); q.processEvents()
win.staff_checks[0].setChecked(True); win.staff_levels[0].setValue(4)
win.staff_names[0].setText("Adjoint Test")
win._apply_staff(); q.processEvents()
assert win.store.staff()[0]["level"] == 4 and win.store.staff()[0]["name"] == "Adjoint Test"
win.tabs.setCurrentIndex(0); q.processEvents()
win.clubs_table.selectRow(0); q.processEvents()
win.club_budget.setValue(7_500_000)
win._apply_club(); q.processEvents()
club_id = int(win.clubs_table.item(0, 0).data(Qt.UserRole))
assert int(win.store.club(club_id)["budget"]) == 7_500_000
print("17) interface : modifications joueur, staff, club et infrastructures appliquées")

win.close(); q.processEvents()
print("18) interface : 5 onglets peuplés, ouverture/fermeture propres")

store.close()
assert os.path.getsize(r"C:\FM2027V2\data\error.log") == 0
print("RESULT: ALL OK")
