# -*- coding: utf-8 -*-
"""Cohérence des icônes directionnelles dans toute l'interface.

Un seul langage visuel :
- →  navigation / ouvrir une fiche ou un rapport ;
- ▶  lancer ou reprendre un match (play) ;
- ▲▼ direction (tri, évolution, promotion/relégation) ;
- ◀▶ uniquement pour l'axe défense/attaque du terrain tactique.
Aucun ↗, ↑ ou ↓ ne doit subsister dans les textes visibles.
"""
import os
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import (QApplication, QLabel, QAbstractButton,
                               QComboBox, QTabWidget)
from PySide6.QtCore import Qt

SOURCE = open(r"C:\FM2027V2\app.py", encoding="utf-8").read()
for glyph in ("↗", "↑", "↓"):
    assert glyph not in SOURCE, f"glyphe directionnel obsolète dans app.py : {glyph}"
for expected in ('("NOTE ▼","note")', '("FORME ▼","forme")', '("ÂGE ▲","age")',
                 '("CONTRAT ▲","contrat")', '("SALAIRE ▼","salaire")',
                 '"FICHE →"', 'f"→  {target_label}"', '_make_icon(303',
                 '_make_icon(301,20,"#dfe8f5")'):
    assert expected in SOURCE, f"règle d'icône absente : {expected}"
assert "_gear_icon_pixmap" not in SOURCE
print("1) source : plus de ↗/↑/↓, navigation → et tri ▲▼")

TMP = tempfile.mkdtemp(prefix="fm_icons_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "default.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP
app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=2,
            identity={"name": "Icons FC", "arena_name": "Halle", "color1": "#2f6fed",
                      "color2": "#14171f", "division": 2})

q = QApplication.instance() or QApplication([])
app.QDialog.exec = lambda self, *a, **k: 1
w = app.MainWindow()
w.setAttribute(Qt.WA_DontShowOnScreen, True)
w.show_game_message = lambda *a, **k: True
w.resize(1600, 1000)
w.show()
q.processEvents()
w.app_stack.setCurrentWidget(w.game_shell)
q.processEvents()

BAD = ("↗", "↑", "↓")
texts = []


def collect(root):
    for lbl in root.findChildren(QLabel):
        texts.append(("label", lbl.text()))
        texts.append(("tooltip", lbl.toolTip()))
    for btn in root.findChildren(QAbstractButton):
        texts.append(("bouton", btn.text()))
        texts.append(("tooltip", btn.toolTip()))
    for combo in root.findChildren(QComboBox):
        for i in range(combo.count()):
            texts.append(("liste", combo.itemText(i)))
    for tab in root.findChildren(QTabWidget):
        for i in range(tab.count()):
            texts.append(("onglet", tab.tabText(i)))


collect(w)
for index in range(len(w.pages)):
    w.show_page(index)
    q.processEvents()
    collect(w.pages[index])
    for tab in w.pages[index].findChildren(QTabWidget):
        for j in range(tab.count()):
            tab.setCurrentIndex(j)
            q.processEvents()
            collect(w.pages[index])
bad = [(where, text) for where, text in texts if any(g in text for g in BAD)]
assert not bad, bad[:8]
print("2) interface : aucun ↗/↑/↓ dans les textes, listes et infobulles")

# Libellés de navigation : →, jamais ▶ ni ↗.
import re
NAV = re.compile(r"\b(FICHE|RAPPORT)\b", re.I)
for btn in w.findChildren(QAbstractButton):
    text = btn.text()
    if NAV.search(text) or "OUVRIR LE CENTRE" in text.upper():
        assert "→" in text, text
        assert "▶" not in text and "↗" not in text, text
assert "▶" not in w.resume_career_btn.text(), w.resume_career_btn.text()
print("3) navigation : fiche/rapport/match utilisent → ; reprise sans doublon ▶")

# Tri du banc : ▲ = ascendant, ▼ = descendant.
labels = [w.bench_sort.itemText(i) for i in range(w.bench_sort.count())]
assert labels == ["NOTE ▼", "POSTE", "NOM A→Z", "FORME ▼", "ÂGE ▲",
                  "CONTRAT ▲", "SALAIRE ▼"], labels
print("4) tri du banc :", " · ".join(labels))


def halves(pixmap):
    img = pixmap.toImage()
    top = bottom = 0
    for y in range(img.height()):
        for x in range(img.width()):
            if img.pixelColor(x, y).alpha() > 0:
                if y < img.height() / 2:
                    top += 1
                else:
                    bottom += 1
    return top, bottom


up_top, up_bottom = halves(w._make_icon(66, 64, "#ffffff"))
down_top, down_bottom = halves(w._make_icon(67, 64, "#ffffff"))
assert up_top > up_bottom, (up_top, up_bottom)      # pointe et tête en haut
assert down_top < down_bottom, (down_top, down_bottom)  # pointe et tête en bas
print("5) promotion ▲ et relégation ▼ : sens corrects")

# Flèches des steppers (PNG générés) : haut pointe en haut, bas en bas.
up_path, down_path = app._spin_arrow_assets()
assert up_path and down_path
from PySide6.QtGui import QPixmap
spin_up_top, spin_up_bottom = halves(QPixmap(up_path))
spin_down_top, spin_down_bottom = halves(QPixmap(down_path))
assert spin_up_top < spin_up_bottom, (spin_up_top, spin_up_bottom)
assert spin_down_top > spin_down_bottom, (spin_down_top, spin_down_bottom)
print("6) steppers : flèche haut vers le haut, flèche bas vers le bas")

# Le bouton Quitter n'utilise plus la flèche « retour ».
assert "QUITTER" in w.start_quit_btn.text()
assert not w.start_quit_btn.icon().isNull()
print("7) bouton Quitter : icône power, plus de flèche retour")

w.close()
q.processEvents()
assert os.path.getsize(r"C:\FM2027V2\data\error.log") == 0
print("RESULT: ALL OK")
