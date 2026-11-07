# -*- coding: utf-8 -*-
"""Audit du rendu de la page Tactiques : largeur, lecture du plan, terrain, banc."""
import os
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication, QLabel, QPushButton
from PySide6.QtCore import Qt, QPoint

TMP = tempfile.mkdtemp(prefix="fm_tacrender_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP
app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=2,
            identity={"name": "Tactics FC", "arena_name": "A", "color1": "#2f6fed",
                      "color2": "#14171f", "division": 2})

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
app.QDialog.exec = lambda self, *a, **k: 1
w = app.MainWindow()
w.setAttribute(app.Qt.WA_DontShowOnScreen, True)
w.show_game_message = lambda *a, **k: True
w.resize(1600, 1000); w.show(); q.processEvents()
w.app_stack.setCurrentWidget(w.game_shell)
w.show_page(2); q.processEvents()
w.auto_pick_lineup(); q.processEvents()
w.refresh_tactical_bench(); q.processEvents()
page = w.stack.currentWidget()

# ---------- 1) La barre tient dans la page : plus de débordement horizontal ----------
toolbar_min = w.tactics_presets_panel.minimumSizeHint().width()
assert toolbar_min <= 1050, toolbar_min
assert w.tactics_splitter.width() >= page.width() - 6, (w.tactics_splitter.width(), page.width())
print(f"1) barre {toolbar_min} px ≤ 1050 · page {page.width()} px · splitter {w.tactics_splitter.width()} px")

# ---------- 2) Lecture du plan : bandeau pleine largeur, au-dessus du terrain ----------
strip = w.tactics_phase_strip
assert strip.width() >= page.width() - 6, (strip.width(), page.width())
assert strip.mapTo(page, QPoint(0, 0)).y() < w.tactics_splitter.mapTo(page, QPoint(0, 0)).y()
for label in w.tactic_phase_cards:
    full = label.full_text()
    assert full and full != "—", full
    need = label.fontMetrics().horizontalAdvance(full)
    assert need <= label.width() - 2, (full, need, label.width())
print("2) phases lisibles :", " | ".join(l.full_text() for l in w.tactic_phase_cards))

# ---------- 3) Lecture colorée : valeurs mises en avant, séparateurs ----------
for lbl in (w.tactic_fit_label, w.tactic_risk_label, w.tactic_control_label):
    assert "font-weight:900" in lbl.text() and "color:" in lbl.text(), lbl.text()
assert w.tactic_fit_label.text().find("COMPATIBILITÉ") >= 0
assert w.tactic_risk_label.text().find("RISQUE") >= 0
assert w.tactic_control_label.text().find("CONTRÔLE") >= 0
dots = [lbl for lbl in page.findChildren(QLabel) if lbl.text() == "•" and lbl.parent() is not None]
assert len(dots) >= 3, len(dots)
print("3) lecture colorée + séparateurs")

# ---------- 4) Terrain : sens de jeu visible, 5 tuiles lisibles ----------
assert not w.pitch.vertical
texts = [lbl.text() for lbl in w.tactics_court_panel.findChildren(QLabel)]
assert "TERRAIN • CINQ" in texts, texts[:5]
assert any("ATTAQUE" in t and "DÉFENSE" in t for t in texts), texts
for name, zone in w.pitch_zones.items():
    assert zone.width() >= 130, (name, zone.width())
    assert zone.player_id is not None, name
court = w.pitch.court_rect()
assert court.width() > court.height() * 1.5
print("4) terrain", int(court.width()), "×", int(court.height()), "· tuiles", min(z.width() for z in w.pitch_zones.values()))

# ---------- 5) Banc : vue rapide, actions visibles et non rognées ----------
assert w.tactic_bench.count() >= 5
assert "DISPO" in w.bench_count.text()
buttons = {b.text(): b for b in w.tactics_bench_panel.findChildren(QPushButton)}
auto = next(b for t, b in buttons.items() if "COMPOSER" in t)
clear = next(b for t, b in buttons.items() if t == "VIDER")
for btn in (auto, clear):
    pos = btn.mapTo(page, QPoint(0, 0))
    assert pos.y() + btn.height() <= page.height() + 2, (btn.text(), pos.y() + btn.height(), page.height())
assert "TEC" in w.bench_preview_stats.full_text() and "END" in w.bench_preview_stats.toolTip()
print("5) banc :", w.bench_count.text(), "· actions visibles")

# ---------- 6) État vide propre ----------
w.reset_drag_lineup(); q.processEvents()
assert all(z.player_id is None for z in w.pitch_zones.values())
assert w.lineup_counter.text() == "0/5 TITULAIRES", w.lineup_counter.text()
assert w.tactic_bench.count() == 12, w.tactic_bench.count()
assert w.bench_count.text().startswith("12 DISPO"), w.bench_count.text()
print("6) état vide : 5 zones '+ DÉPOSER', 12 joueurs au banc")

# ---------- 7) Responsive : colonne + description masquée en fenêtre étroite ----------
w.resize(1000, 700); q.processEvents(); w.fit_tactics_layout(); q.processEvents()
assert w.tactics_splitter.orientation() == Qt.Vertical
assert w.tactics_splitter.width() <= w.main_scroll.viewport().width()
assert not w.preset_description.isVisible()
w.resize(1600, 1000); q.processEvents(); w.fit_tactics_layout(); q.processEvents()
assert w.tactics_splitter.orientation() == Qt.Horizontal
assert w.preset_description.isVisible()
print("7) responsive : colonne à 1000 px, côte à côte à 1600 px")

# ---------- 8) Enregistrement : retour lisible ----------
w.auto_pick_lineup(); q.processEvents()
w.save_tactics(); q.processEvents()
assert "PLAN ENREGISTRÉ" in w.tactic_feedback.text(), w.tactic_feedback.text()
print("8) enregistrement :", w.tactic_feedback.text()[:70])

w.close(); q.processEvents()
assert os.path.getsize(r"C:\FM2027V2\data\error.log") == 0
print("RESULT: ALL OK")
