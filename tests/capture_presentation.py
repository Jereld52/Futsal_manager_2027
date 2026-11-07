# -*- coding: utf-8 -*-
"""capture_presentation.py - captures d'ecran de presentation FM2027V2.

Usage :
    python tests\\capture_presentation.py [dossier_de_sortie]

Genere les visuels des 14 pages, de tous les onglets et sous-onglets, de la
messagerie (boite + a traiter), du centre de match (avant-match, direct,
action, rapport) et de l'ecran d'accueil / creation de club.

Travaille exclusivement sur des COPIES TEMP de la sauvegarde active :
data/active_save.txt et les sauvegardes utilisateur ne sont jamais touches.
"""
import os, sys, tempfile, shutil, re, time
sys.path.insert(0, r"C:\FM2027V2")
import app
import ui_components
from PySide6.QtWidgets import QApplication, QTabWidget, QDialog
from PySide6.QtTest import QTest
from PySide6.QtGui import QImage, QPainter, QColor, QFont
from PySide6.QtCore import Qt

REAL = r"C:\FM2027V2\data\saves\arbot_futsal_saison_saison_6_20261028_025341.db"
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.expanduser("~"), "Documents", "captures_fm2027")
os.makedirs(OUT, exist_ok=True)
for old in os.listdir(OUT):
    if old.lower().endswith(".png"):
        try:
            os.remove(os.path.join(OUT, old))
        except OSError:
            pass

TMP = tempfile.mkdtemp(prefix="fm_shots_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
COPY = os.path.join(TMP, "saves", "presentation.db")
shutil.copy2(REAL, COPY)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = COPY
app.DATA_DIR = TMP
app.BASE_DIR = TMP
app.OPTIONS_FILE = os.path.join(TMP, "options.json")
app.active_save_path = lambda: COPY
app.set_active_save_path = lambda p: None
app.init_db()

qapp = QApplication.instance() or QApplication([])
qapp.setStyleSheet(app.style_for_theme("Nuit violette"))

manifest = []          # (fichier, titre, categorie)
main_page_files = []
counter = [0]


def slug(text):
    text = str(text)
    for a, b in (("à", "a"), ("â", "a"), ("ä", "a"), ("é", "e"), ("è", "e"), ("ê", "e"),
                 ("ë", "e"), ("î", "i"), ("ï", "i"), ("ô", "o"), ("ö", "o"), ("ù", "u"),
                 ("û", "u"), ("ü", "u"), ("ç", "c"), ("œ", "oe"), ("’", ""), ("'", "")):
        text = text.replace(a, b).replace(a.upper(), b.upper())
    text = re.sub(r"[^0-9A-Za-z]+", "_", text).strip("_")
    return text.lower() or "vue"


def pump(ms=300):
    QTest.qWait(ms)
    qapp.processEvents()
    qapp.processEvents()


def shot(widget, title, category, prefix=None):
    counter[0] += 1
    base = "%02d_%s" % (counter[0], prefix or slug(title))
    path = os.path.join(OUT, base + ".png")
    pm = widget.grab()
    pm.save(path)
    manifest.append((os.path.basename(path), title, category))
    print("capture", os.path.basename(path), pm.width(), "x", pm.height())


# ------------------------------------------------------------------ #
# 1) Ecran d'accueil + creation de club (avant la carriere)
# ------------------------------------------------------------------ #
w = app.MainWindow()
w.show_game_message = lambda *a, **k: True
w.setAttribute(Qt.WA_DontShowOnScreen, True)
w.resize(1600, 1000)
w.show()
pump(700)
w.app_stack.setCurrentWidget(w.start_screen)
pump(500)
shot(w.start_screen, "Écran d'accueil", "Accueil")

try:
    dlg = ui_components.ClubSetupDialog(w, app.LEAGUE_DEFINITIONS, app.facility_capacity)
    dlg.setAttribute(Qt.WA_DontShowOnScreen, True)
    dlg.resize(1200, 800)
    dlg.show()
    pump(500)
    dlg.grab().save(os.path.join(OUT, "creation_club.png"))
    counter[0] += 1
    manifest.append(("creation_club.png", "Création de club", "Accueil"))
    print("capture creation_club.png")
    dlg.close()
except Exception as exc:
    print("creation club ignoree:", exc)

# ------------------------------------------------------------------ #
# 2) Carriere : pages + onglets
# ------------------------------------------------------------------ #
w.app_stack.setCurrentWidget(w.game_shell)
pump(600)

# Le centre de match ne s'ouvre que s'il y a un match aujourd'hui : on place la
# prochaine rencontre du club a la date de carriere (copie TEMP uniquement).
try:
    _c = app.db()
    _fx = _c.execute("SELECT id FROM fixture WHERE (home_club_id=1 OR away_club_id=1) "
                     "AND played=0 ORDER BY fixture_date LIMIT 1").fetchone()
    if _fx:
        _c.execute("UPDATE fixture SET fixture_date=? WHERE id=?",
                   (w._career_day(), int(_fx["id"])))
        _c.commit()
    _c.close()
    w.refresh_all()
    pump(400)
except Exception as _exc:
    print("fixture du jour non deplacee:", _exc)

PAGE_NAMES = ["Direction sportive", "Effectif", "Tactiques", "Match", "Entraînement",
              "Infrastructure", "Messagerie", "Transferts", "Calendrier", "Finances",
              "Staff", "Compétitions", "Recherche", "Centre de formation"]
CAPTIONS = {"Messagerie": "Messagerie", "Staff": "Staff"}

page_shots = {}

for index, name in enumerate(PAGE_NAMES):
    w.show_page(index)
    pump(650)
    path_title = CAPTIONS.get(name, name)
    shot(w, path_title, "Pages")
    page_shots[name] = counter[0]
    main_page_files.append(manifest[-1][0])

# Tactiques : panneau avance deplie (vue immersive supplementaire)
try:
    w.show_page(2)
    pump(300)
    if hasattr(w, "tactical_advanced_panel"):
        w.tactical_advanced_panel.setVisible(True)
        pump(350)
        shot(w, "Tactiques — réglages avancés", "Pages", prefix="tactiques_reglages_avances")
        w.tactical_advanced_panel.setVisible(False)
except Exception as exc:
    print("tactiques avance ignore", exc)

# Messagerie : dossier « A traiter »
try:
    w.show_page(6)
    pump(500)
    w._set_message_filter("action")
    pump(500)
    shot(w, "Messagerie — dossiers à traiter", "Pages", prefix="messagerie_a_traiter")
    w._set_message_filter("all")
    pump(300)
except Exception as exc:
    print("messagerie a traiter ignoree", exc)


def capture_tabs(root_widget, prefix, depth=0, visited=None):
    if depth > 2:
        return
    if visited is None:
        visited = set()
    for tabs in root_widget.findChildren(QTabWidget):
        if not tabs.isVisible() or id(tabs) in visited:
            continue
        visited.add(id(tabs))
        for i in range(tabs.count()):
            label = tabs.tabText(i)
            if not label.strip():
                continue
            tabs.setCurrentIndex(i)
            pump(700 if tabs.count() > 1 else 400)
            sub_prefix = "%s__%s" % (prefix, slug(label))
            shot(w, "%s — %s" % (title_for_prefix(prefix), label), "Onglets",
                 prefix=sub_prefix)
            capture_tabs(tabs.currentWidget(), sub_prefix, depth + 1, visited)


def title_for_prefix(prefix):
    p = prefix.split("__")[-1]
    for key, value in (("entrainement", "Entraînement"), ("infrastructure", "Infrastructure"),
                       ("transferts", "Transferts"), ("calendrier", "Calendrier"),
                       ("finances", "Finances"), ("staff", "Staff"),
                       ("competitions", "Compétitions")):
        if key in p:
            return value
    return p.replace("_", " ").capitalize()


TAB_PAGES = {4: "entrainement", 5: "infrastructure", 7: "transferts",
             8: "calendrier", 9: "finances", 10: "staff", 11: "competitions"}
for index, prefix in TAB_PAGES.items():
    w.show_page(index)
    pump(600)
    capture_tabs(w.pages[index], prefix)

# ------------------------------------------------------------------ #
# 3) Centre de match : avant-match / direct / fin
# ------------------------------------------------------------------ #
try:
    MATCH_DB = os.path.join(TMP, "saves", "match.db")
    shutil.copy2(REAL, MATCH_DB)
    app.DB_PATH = MATCH_DB
    app.active_save_path = lambda: MATCH_DB
    c = app.db()
    fx = c.execute("SELECT f.* FROM fixture f WHERE (f.home_club_id=1 OR f.away_club_id=1) "
                   "AND f.played=0 ORDER BY f.fixture_date LIMIT 1").fetchone()
    fx_id = int(fx["id"]) if fx else None
    c.close()

    app.QDialog.exec = lambda self, *a, **k: QDialog.Accepted

    def _exec_capture(self, *a, **k):
        try:
            if self.windowTitle() == "Rapport de match":
                self.setAttribute(Qt.WA_DontShowOnScreen, True)
                self.resize(1240, 920)
                self.show()
                qapp.processEvents()
                QTest.qWait(450)
                qapp.processEvents()
                shot(self, "Rapport de match — après le match", "Match",
                     prefix="rapport_de_match")
        except Exception as exc:
            print("rapport non capture:", exc)
        return QDialog.Accepted

    app.QDialog.exec = _exec_capture
    mw = app.MainWindow()
    mw.show_game_message = lambda *a, **k: True
    mw.setAttribute(Qt.WA_DontShowOnScreen, True)
    mw.resize(1600, 1000)
    mw.show()
    pump(800)
    mw.app_stack.setCurrentWidget(mw.game_shell)
    if fx_id:
        today = mw._career_day()
        c = app.db()
        c.execute("UPDATE fixture SET fixture_date=? WHERE id=?", (today, fx_id))
        c.commit()
        c.close()
        mw.refresh_all()
        pump(400)
    mw.show_page(3)
    pump(900)
    shot(mw, "Centre de match — avant-match", "Match")

    if mw._launch_match_after_confirmation() is None:
        pump(800)
        shot(mw, "Centre de match — direct", "Match", prefix="match_direct")
        for _ in range(12):
            if mw.match_state and mw.match_state.get("half_time_break"):
                break
            mw.advance_minute()
            qapp.processEvents()
        pump(700)
        shot(mw, "Centre de match — action en cours", "Match", prefix="match_action")
        mw.finish_match_now()
        pump(900)
    mw.close()
    pump(200)
except Exception as exc:
    print("captures match ignorees:", exc)

# ------------------------------------------------------------------ #
# 4) Index Markdown
# ------------------------------------------------------------------ #
lines = ["# Captures FM2027V2", "",
         "Captures générées automatiquement depuis une copie de la sauvegarde active.",
         "", "| Fichier | Vue |", "|---|---|"]
for fn, title, cat in manifest:
    lines.append("| `%s` | %s |" % (fn, title.replace("|", "/")))
lines += ["", "Catégories : Accueil, Pages, Onglets, Match."]
with open(os.path.join(OUT, "index.md"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")

# ------------------------------------------------------------------ #
# 5) Planche contact des pages principales
# ------------------------------------------------------------------ #
try:
    main_files = list(main_page_files)
    thumbs = [QImage(os.path.join(OUT, fn)) for fn in main_files[:14]]
    cols = 4
    tw, th = 380, 238
    rows = (len(thumbs) + cols - 1) // cols
    pad = 18
    sheet = QImage(cols * tw + pad * (cols + 1), rows * (th + 26) + pad * (rows + 1), QImage.Format_RGB32)
    sheet.fill(QColor("#0b1220"))
    painter = QPainter(sheet)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    for i, img in enumerate(thumbs):
        r, cidx = divmod(i, cols)
        x = pad + cidx * (tw + pad)
        y = pad + r * (th + 26 + pad)
        painter.drawImage(x, y, img.scaled(tw, th, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        painter.setPen(QColor("#c9d7e8"))
        painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
        painter.drawText(x, y + th + 18, os.path.basename(main_files[i])[3:-4].replace("_", " "))
    painter.end()
    sheet.save(os.path.join(OUT, "planche_contact_pages.png"))
    print("planche contact OK")
except Exception as exc:
    print("planche contact ignoree:", exc)

print("TOTAL", len(manifest), "captures ->", OUT)
