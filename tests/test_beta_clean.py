# -*- coding: utf-8 -*-
"""Propreté avant bêta : aucun résidu technique visible + trace UI opt-in.

1. Parcours de toutes les pages/onglets : aucun texte « None », « NaN »,
   « Traceback », « N/A » isolé, « {} », mojibake… dans les labels, boutons,
   onglets, tables ou infobulles.
2. `log_trace` n'écrit RIEN par défaut ; activé, il écrit et tourne au-delà
   du plafond (fichier .1).
3. La racine ne contient plus de fichier de code corrompu/backup.
"""
import os
import re
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import (QApplication, QLabel, QAbstractButton,
                               QTableWidget, QTabWidget)
from PySide6.QtCore import Qt

TMP = tempfile.mkdtemp(prefix="fm_betaclean_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "default.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP
app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=2,
            identity={"name": "Beta FC", "arena_name": "Halle", "color1": "#2f6fed",
                      "color2": "#14171f", "division": 2})

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
CAPTURED = []
app.QDialog.exec = lambda self, *a, **k: (CAPTURED.append(self), 1)[1]
w = app.MainWindow()
w.setAttribute(Qt.WA_DontShowOnScreen, True)
w.show_game_message = lambda *a, **k: True
w.resize(1600, 1000)
w.show()
q.processEvents()
w.app_stack.setCurrentWidget(w.game_shell)
q.processEvents()

BAD = re.compile(r"\bNone\b|\bNaN\b|Traceback|\bException\b|\{\}|\{[\w ]+\}|"
                 r"\[\]|<\w+ object|Ã©|Ã¨|Ã |�|\?\?\?|\bN/A\b|undefined|"
                 r"\bTODO\b|\bFIXME\b|AttributeError|KeyError|TypeError", re.I)
found = []


def check(text, where):
    t = (text or "").strip()
    if t and BAD.search(t):
        found.append((where, t[:150]))


def scan(root):
    for lbl in root.findChildren(QLabel):
        check(lbl.text(), "QLabel")
        check(lbl.toolTip(), "infobulle")
    for btn in root.findChildren(QAbstractButton):
        check(btn.text(), "bouton")
        check(btn.toolTip(), "infobulle")
    for tab in root.findChildren(QTabWidget):
        for i in range(tab.count()):
            check(tab.tabText(i), "onglet")
            check(tab.tabToolTip(i), "infobulle")
    for table in root.findChildren(QTableWidget):
        for r in range(min(table.rowCount(), 80)):
            for c in range(table.columnCount()):
                it = table.item(r, c)
                if it:
                    check(it.text(), "table")
                    check(it.toolTip(), "infobulle")


assert len(w.pages) >= 11, len(w.pages)
for index in range(len(w.pages)):
    w.show_page(index)
    q.processEvents()
    scan(w.pages[index])
    for tab in w.pages[index].findChildren(QTabWidget):
        for j in range(tab.count()):
            tab.setCurrentIndex(j)
            q.processEvents()
            scan(w.pages[index])
assert not found, found[:10]
print("1) texte visible : %d page(s)/onglet(s) scannés, 0 résidu technique" % len(w.pages))

# ---------- Trace UI : muette par défaut, active sur demande ----------
trace_path = os.path.join(TMP, "trace.log")
app.TRACE_LOG = trace_path
app.TRACE_ENABLED = False
w.log_trace("ne doit pas être écrit")
assert not os.path.exists(trace_path), "trace écrite alors qu'elle est désactivée"
app.TRACE_ENABLED = True
w.log_trace("écrit quand activée")
assert os.path.exists(trace_path) and os.path.getsize(trace_path) > 0
app.TRACE_MAX_BYTES = 40
for _ in range(6):
    w.log_trace("rotation " + "x" * 40)
assert os.path.exists(trace_path + ".1"), "pas de rotation de la trace"
app.TRACE_ENABLED = False
print("2) trace UI : muette par défaut, écriture et rotation quand activée")

root_bad = [n for n in os.listdir(r"C:\FM2027V2")
            if n.endswith((".bak", ".corrupt")) or "corrupt" in n.lower()]
assert not root_bad, root_bad
print("3) racine : aucun fichier corrompu/backup résiduel")

w.close()
q.processEvents()
assert os.path.getsize(r"C:\FM2027V2\data\error.log") == 0
print("RESULT: ALL OK")
