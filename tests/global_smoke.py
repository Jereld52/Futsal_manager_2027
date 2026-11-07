# -*- coding: utf-8 -*-
"""Smoke test global hors écran : toutes les pages/onglets + une séquence de matchs.

Usage : python global_smoke.py fresh|save
Ne montre AUCUNE fenêtre (offscreen + WA_DontShowOnScreen)."""
import json
import os
import re
import shutil
import sys
import tempfile
import traceback

sys.path.insert(0, r"C:\FM2027V2")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import app
from PySide6.QtWidgets import (QApplication, QTabWidget, QLabel,
                               QAbstractButton, QTableWidget)
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

MODE = sys.argv[1] if len(sys.argv) > 1 else "fresh"
SRC_USER = r"C:\FM2027V2\data\saves\arbot_futsal_saison_saison_6_20261028_025341.db"
TMP = tempfile.mkdtemp(prefix=f"fm_global_{MODE}_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
DB = os.path.join(TMP, "copy.db") if MODE == "save" else os.path.join(TMP, "saves", "p.db")
if MODE == "save":
    shutil.copy(SRC_USER, DB)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = DB
app.DB_PATH = DB
app.DATA_DIR = r"C:\FM2027V2\data"
app.BASE_DIR = r"C:\FM2027V2"
app.active_save_path = lambda: DB
app.set_active_save_path = lambda p: None
if MODE != "save":
    app.init_db(fresh_universe=True, selected_division=2,
                identity={"name": "Global FC", "arena_name": "Halle", "color1": "#2f6fed",
                          "color2": "#14171f", "division": 2})

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
DIALOGS = []
app.QDialog.exec = lambda self, *a, **k: (DIALOGS.append(self), 1)[1]
w = app.MainWindow()
w.setAttribute(Qt.WA_DontShowOnScreen, True)
w.show_game_message = lambda *a, **k: True
w.resize(1600, 1000); w.show(); q.processEvents()
if MODE == "save":
    w.activate_career(DB); q.processEvents()
else:
    w.app_stack.setCurrentWidget(w.game_shell); q.processEvents()

problems = []


def scan_images(tag, root=None):
    """Images plus grandes que leur QLabel = pixmap rogné/décalé (ex. écussons)."""
    root = root or w
    for lbl in root.findChildren(app.QLabel):
        try:
            if not lbl.isVisible():
                continue
            pm = lbl.pixmap()
            if pm is None or pm.isNull():
                continue
            if pm.width() > lbl.width() + 1 or pm.height() > lbl.height() + 1:
                problems.append((f"{tag}:image",
                                 f"{lbl.width()}x{lbl.height()} <- {pm.width()}x{pm.height()} "
                                 f"[{lbl.objectName()}|{lbl.parent().objectName() if lbl.parent() else ''}|{lbl.toolTip()[:40]}]"))
        except Exception:
            pass


BAD_TEXT = re.compile(r"\bNone\b|\bNaN\b|Traceback|\bException\b|\{\}|\{[\w ]+\}|"
                      r"\[\]|<\w+ object|Ã©|Ã¨|Ã |�|\?\?\?|\bN/A\b|undefined|"
                      r"\bTODO\b|\bFIXME\b|AttributeError|KeyError|TypeError", re.I)


def scan_texts(tag, root=None):
    """Aucun résidu technique dans les textes visibles (labels, tables, onglets)."""
    root = root or w

    def add(where, text):
        t = (text or "").strip()
        if t and BAD_TEXT.search(t):
            problems.append((f"{tag}:texte:{where}", t[:140]))

    for lbl in root.findChildren(QLabel):
        add("QLabel", lbl.text()); add("infobulle", lbl.toolTip())
    for btn in root.findChildren(QAbstractButton):
        add("bouton", btn.text()); add("infobulle", btn.toolTip())
    for tab in root.findChildren(QTabWidget):
        for i in range(tab.count()):
            add("onglet", tab.tabText(i)); add("infobulle", tab.tabToolTip(i))
    for table in root.findChildren(QTableWidget):
        for r in range(min(table.rowCount(), 60)):
            for c in range(table.columnCount()):
                it = table.item(r, c)
                if it:
                    add("table", it.text()); add("infobulle", it.toolTip())


def step(label, fn):
    try:
        fn()
        q.processEvents()
    except Exception as exc:
        problems.append((label, "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))))
        print("!!", label, type(exc).__name__, exc)


def visit_all(tag):
    print("== pages/onglets", tag)
    for index in range(len(w.pages)):
        step(f"{tag}:page{index}", lambda i=index: w.show_page(i))
        scan_images(f"{tag}:page{index}")
        page = w.pages[index]
        tabs = page.findChildren(QTabWidget)
        for ti, tab in enumerate(tabs):
            for j in range(tab.count()):
                step(f"{tag}:page{index}:tab{ti}.{j}", lambda t=tab, j=j: t.setCurrentIndex(j))
                scan_images(f"{tag}:page{index}:tab{ti}.{j}")
        scan_texts(f"{tag}:page{index}")


visit_all("initial")

# Profils et fiches (sans affichage réel).
c = app.db()
own = c.execute("SELECT id FROM player WHERE club_id=1 ORDER BY id LIMIT 1").fetchone()
other = c.execute("SELECT id FROM player WHERE club_id<>1 ORDER BY id LIMIT 1").fetchone()
c.close()
if own:
    step("profil joueur", lambda: w.open_player_profile(int(own["id"])))
if other:
    step("profil joueur adverse", lambda: w.open_club_player_profile(int(other["id"])))
step("fiche club 1", lambda: w.show_club_profile(1))
step("fiche club 2", lambda: w.show_club_profile(2))
step("prêts", lambda: w.refresh_loans_tab())
step("offres", lambda: w._refresh_offers_tab())
step("pré-contrats", lambda: w._refresh_precontracts())
for dlg in DIALOGS:
    scan_images("dialogue", dlg)
    scan_texts("dialogue", dlg)

# Tactique / staff / finances : actions de lecture-écriture.
w.show_page(2); q.processEvents()
step("composition auto", lambda: w.auto_pick_lineup())
step("enregistrer tactique", lambda: w.save_tactics())
w.show_page(10); q.processEvents()
step("staff refresh", lambda: w._staff_refresh())
w.show_page(9); q.processEvents()
for i in range(4):
    step(f"finance tab {i}", lambda i=i: w.finance_tabs.setCurrentIndex(i))
w.show_page(8); q.processEvents()
for i in range(3):
    step(f"calendrier tab {i}", lambda i=i: w.championship_tabs.setCurrentIndex(i))
for filt in ("TOUT", "PROCHAINS MATCHS", "RÉSULTATS"):
    step(f"calendrier filtre {filt}", lambda f=filt: w.calendar_filter_combo.setCurrentText(f))

# Avance + matchs, puis re-visite de toutes les pages.
print("== avance calendrier")
for n in range(70):
    c = app.db()
    try:
        fx = w._today_fixture_for_user(c)
    except Exception:
        fx = None
    c.close()
    if fx:
        step(f"match {n}", lambda: (w.start_match(), q.processEvents(), w.finish_match_now()))
    else:
        step(f"jour {n}", lambda: w.advance_calendar_days(1))
visit_all("après matchs")

c = app.db()
print("date", c.execute("SELECT current_date FROM career WHERE id=1").fetchone()["current_date"])
print("matchs joués", c.execute("SELECT COUNT(*) n FROM match_record").fetchone()["n"])
c.close()
print("problèmes", len(problems))
for label, tb in problems[:12]:
    print("---", label)
    print(tb.strip().splitlines()[-1])
print("ERRLOG", os.path.getsize(r"C:\FM2027V2\data\error.log"))
w.close(); q.processEvents()
if problems:
    print("RESULT: BUGS (%d)" % len(problems))
    sys.exit(1)
print("RESULT: ALL OK")
