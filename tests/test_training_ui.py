# -*- coding: utf-8 -*-
"""Entraînement : calendrier sur 2 semaines, modèles et édition des séances."""
import os, sys, tempfile
from datetime import timedelta
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app

TMP = tempfile.mkdtemp(prefix="fm_training_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP; app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=3,
            identity={"name": "Training FC", "arena_name": "Halle", "color1": "#c47220",
                      "color2": "#14171f", "division": 3})

from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
app.MainWindow.show_game_message = lambda self, *a, **k: True
w = app.MainWindow(); w.resize(1360, 900); w.show()
w.app_stack.setCurrentWidget(w.game_shell); q.processEvents(); w.show_page(4); QTest.qWait(120); q.processEvents()

assert hasattr(w, "training_calendar")
assert len(w.training_calendar.cells) == 14
assert w.training_preset_combo.count() == 4
assert w.training_kpi_load.text().endswith("/20"), w.training_kpi_load.text()
_today0 = app.parse_iso(w._career_day())
assert w.training_calendar.cells[0].date_iso >= _today0.isoformat()
print("calendrier:", len(w.training_calendar.cells), "cases |", w.training_calendar.month_label.text())

# Édition d'une séance sur le jour sélectionné.
w.training_activity_combo.setCurrentIndex(w.training_activity_combo.findData("Technique"))
w.training_intensity_combo.setCurrentText("Normale")
w._training_apply_day(); q.processEvents()
assert w.training_pending
print("séance en attente:", w.training_selected_date, w.training_pending[w.training_selected_date])
ok = w.save_training_plan(); q.processEvents()
assert ok
conn = app.db()
row = conn.execute("SELECT activity_key,completed FROM training_session WHERE planned_date=? ORDER BY id DESC LIMIT 1", (w.training_selected_date,)).fetchone()
conn.close()
assert row and row["activity_key"] == "Technique"
print("enregistrement jour: OK")

# Modèle : applique et enregistre automatiquement les 2 semaines visibles,
# même si le jour sélectionné n'est pas un lundi.
_today_sel = app.parse_iso(w._career_day())
_sel = _today_sel + timedelta(days=(2 - _today_sel.weekday()) % 7)
if _sel.weekday() == 0:
    _sel += timedelta(days=2)
w.training_selected_date = _sel.isoformat()
w.refresh_training_calendar(); q.processEvents()
w.training_preset_combo.setCurrentIndex(w.training_preset_combo.findData("development"))
w.apply_training_preset(); q.processEvents()
assert not w.training_pending, "le modèle doit être enregistré automatiquement"
_start, _end = w._training_window_bounds()
conn = app.db()
planned = conn.execute("SELECT COUNT(*) n FROM training_session WHERE completed=0 AND planned_date BETWEEN ? AND ?",
                       (_start.isoformat(), _end.isoformat())).fetchone()["n"]
conn.close()
assert planned >= 7, planned
assert "programmé" in w.training_status.text().lower(), w.training_status.text()
print("modèle développement:", planned, "jours programmés sur la quinzaine")

# Navigation par quinzaine.
old_start = w.training_calendar.window_start
old_label = w.training_week_label.text()
w._training_window_move(1); q.processEvents()
assert w.training_calendar.window_start == old_start + timedelta(days=14)
assert w.training_week_label.text() != old_label
w._training_go_today(); q.processEvents()
_today = app.parse_iso(w._career_day())
assert w.training_calendar.window_start == _today
print("navigation 2 semaines: OK")

# Onglets Individuel et Progression en cartes.
w.training_tabs.setCurrentIndex(1); q.processEvents()
assert w.training_indiv_cards and w.training_indiv_grid.count() == len(w.training_indiv_cards)

from PySide6.QtWidgets import QLabel
labels = [lbl.text() for card in w.training_indiv_cards for lbl in card.findChildren(QLabel)]
assert any(t.startswith(("CIBLE", "AUTO")) and "/20" in t for t in labels), labels
conn = app.db()
me = conn.execute("SELECT * FROM player WHERE club_id=1 ORDER BY id LIMIT 1").fetchone()
conn.close()
w._set_player_training_focus(int(me["id"]), "technique")
w.refresh_training_individual(); q.processEvents()
labels = [lbl.text() for card in w.training_indiv_cards for lbl in card.findChildren(QLabel)]
assert f"CIBLE · TECHNIQUE {app.rating20(me['technique'])}/20" in labels, labels
auto_key = app.TRAINING_AUTO_ATTRIBUTE.get(str(me["position"]), "technique")
w._set_player_training_focus(int(me["id"]), "")
w.refresh_training_individual(); q.processEvents()
labels = [lbl.text() for card in w.training_indiv_cards for lbl in card.findChildren(QLabel)]
assert f"AUTO · {app.TRAINING_ATTRIBUTE_NAMES[auto_key].upper()} {app.rating20(me[auto_key])}/20" in labels, labels
print("cible individuelle:", [t for t in labels if t.startswith(("CIBLE", "AUTO"))][:2])

# Filtres INDIVIDUEL + pastilles d'état (FOCUS / AUTO / EN HAUSSE / PLAFOND).
def _card_texts(card):
    return [lbl.text() for lbl in card.findChildren(QLabel)]

w._set_player_training_focus(int(me["id"]), "technique")
w.refresh_training_individual(); q.processEvents()
w.training_indiv_filter.setCurrentIndex(w.training_indiv_filter.findText("Focus manuels")); q.processEvents()
assert w.training_indiv_cards and all("AUTO" not in _card_texts(c) for c in w.training_indiv_cards)
print("filtre focus manuels:", len(w.training_indiv_cards), "carte(s)")
w.training_indiv_filter.setCurrentIndex(w.training_indiv_filter.findText("Auto (poste)")); q.processEvents()
assert w.training_indiv_cards and all("AUTO" in _card_texts(c) for c in w.training_indiv_cards)
print("filtre auto:", len(w.training_indiv_cards), "carte(s)")
w.training_indiv_filter.setCurrentIndex(0); q.processEvents()
assert any(any(("reste " in t or "plafond atteint" in t) for t in _card_texts(c))
           for c in w.training_indiv_cards), "chaque carte doit dire sa marge restante"
assert w.training_indiv_cap.text().endswith("PLAFOND"), w.training_indiv_cap.text()
print("marge/plafond visibles:", w.training_indiv_cap.text())

# Filtre sans résultat : message clair, grille vide, compteur filtré.
w._set_player_training_focus(int(me["id"]), "")
w.training_indiv_filter.setCurrentIndex(w.training_indiv_filter.findText("Focus manuels")); q.processEvents()
assert not w.training_indiv_cards, len(w.training_indiv_cards)
assert w.training_indiv_empty.isVisible(), "le message 'aucun joueur' doit s'afficher"
assert w.training_indiv_grid.count() == 0
assert w.training_indiv_count.text().startswith("0 / "), w.training_indiv_count.text()
print("filtre vide:", w.training_indiv_count.text(), "| message visible")
w.training_indiv_filter.setCurrentIndex(0); q.processEvents()
assert w.training_indiv_cards and not w.training_indiv_empty.isVisible()

# Progression : les attributs gagnés depuis le début de saison ressortent en couleur.
season_start = w._season_start_for(w._career_day()).isoformat()
conn = app.db()
conn.execute("INSERT INTO player_training_log(player_id,attribute_key,delta,activity_key,created_at) "
             "VALUES(?, 'technique', 1, 'Test', ?)", (int(me["id"]), season_start))
conn.execute("DELETE FROM player_attr_baseline WHERE player_id=?", (int(me["id"]),))
conn.commit(); conn.close()
w.training_tabs.setCurrentIndex(2); q.processEvents()
assert w.training_evo_cards and w.training_evo_grid.count() == len(w.training_evo_cards)
chips = [lbl for card in w.training_evo_cards for lbl in card.findChildren(QLabel)
         if lbl.objectName() == "SeasonEvoChip"]
assert any(c.text().startswith("TEC +") for c in chips), [c.text() for c in chips]
assert any("#7de0aa" in c.styleSheet() for c in chips)
print("évolution saison:", [c.text() for c in chips][:3])

# Filtres PROGRESSION : chaque carte affichée correspond au filtre.
def _evo_texts(card):
    return [lbl.text() for lbl in card.findChildren(QLabel)]
assert any(t in ("EN HAUSSE", "STABLE", "PLAFOND") for c in w.training_evo_cards for t in _evo_texts(c))
for label in ("En progression", "Plafond atteint", "Sans évolution"):
    idx = w.training_evo_filter.findText(label)
    assert idx >= 0, label
    w.training_evo_filter.setCurrentIndex(idx); q.processEvents()
    assert w.training_evo_grid.count() == len(w.training_evo_cards), label
    for card in w.training_evo_cards:
        txts = _evo_texts(card)
        if label == "En progression":
            assert w.training_evo_cards, "un joueur avec un gain doit ressortir"
            assert ("0 PT" not in txts), (label, txts)
        elif label == "Plafond atteint":
            assert "PLAFOND" in txts, (label, txts)
        else:
            assert "0 PT" in txts, (label, txts)
    print(f"filtre progression {label.lower()}:", len(w.training_evo_cards), "carte(s)")
w.training_evo_filter.setCurrentIndex(0); q.processEvents()
assert len(w.training_evo_cards) >= 1
w.training_tabs.setCurrentIndex(0); q.processEvents()
print("onglets cartes: OK")

# Bandeau collectif réservé à l'onglet « 2 SEMAINES ».
w.training_tabs.setCurrentIndex(1); q.processEvents()
assert not w.training_group_panel.isVisible(), "le bandeau collectif ne doit pas s'afficher sur Individuel"
assert not w.training_context_panel.isVisible() and not w.training_settings_panel.isVisible()
w.training_tabs.setCurrentIndex(2); q.processEvents()
assert not w.training_group_panel.isVisible(), "le bandeau collectif ne doit pas s'afficher sur Progression"
w.training_tabs.setCurrentIndex(0); q.processEvents()
assert w.training_group_panel.isVisible()
assert w.training_context_panel.isVisible() and w.training_settings_panel.isVisible()
print("bandeau collectif: uniquement sur 2 SEMAINES")

# Un match affiché dans une case du calendrier (mois du prochain match).
fixture = w._next_match_for_training()
if fixture:
    target = app.parse_iso(str(fixture["fixture_date"]))
    w.training_selected_date = target.isoformat()
    w.refresh_training_calendar(); q.processEvents()
    texts = [c.match_text.text() for c in w.training_calendar.cells]
    print("match dans le calendrier:", [t for t in texts if t][:2])
    assert any(t for t in texts)
w.close()
print("RESULT: ALL OK")
