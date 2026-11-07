# -*- coding: utf-8 -*-
"""Audit des images : fonds blancs/noirs supprimés, placement et tailles."""
import os
import shutil
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QSize

TMP = tempfile.mkdtemp(prefix="fm_imgaudit_")
DATA = os.path.join(TMP, "data")
os.makedirs(DATA, exist_ok=True)
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
for name in ("ban2.png", "logo1.png", "modelext.png"):
    src = os.path.join(r"C:\FM2027V2\data", name)
    if os.path.isfile(src):
        shutil.copy(src, os.path.join(DATA, name))
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = DATA
app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=2,
            identity={"name": "Image FC", "arena_name": "Halle", "color1": "#2f6fed",
                      "color2": "#14171f", "division": 2})

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
app.QDialog.exec = lambda self, *a, **k: 1
w = app.MainWindow()
w.setAttribute(app.Qt.WA_DontShowOnScreen, True)
w.show_game_message = lambda *a, **k: True
w.resize(1600, 1000); w.show(); q.processEvents()
w.app_stack.setCurrentWidget(w.game_shell)

# ---------- 1) Détourage du bandeau (fond blanc) ----------
clean = app._transparent_key_pixmap(os.path.join(DATA, "ban2.png"), "white")
assert clean and not clean.isNull()
img = clean.toImage()
corner_a = img.pixelColor(0, 0).alpha()
center_a = img.pixelColor(img.width() // 2, img.height() // 2).alpha()
assert corner_a == 0, corner_a
assert center_a > 0, center_a
opaque = sum(1 for x in range(0, img.width(), 8) for y in range(0, img.height(), 8)
             if img.pixelColor(x, y).alpha() > 0)
assert opaque > 50, opaque
print("1) bandeau : coins transparents, logo conservé ·", opaque, "points opaques")

# ---------- 2) Bandeau dans la barre latérale : centré, détouré, encadré ----------
pix = w.top_banner.pixmap()
assert pix and not pix.isNull(), "bandeau absent"
assert pix.width() <= 286 and pix.height() <= 96
bimg = pix.toImage()
assert bimg.pixelColor(0, 0).alpha() == 0, "fond blanc résiduel"
assert int(w.top_banner.alignment()) & int(Qt.AlignHCenter)
assert "border-radius" in w.top_banner.styleSheet()
assert w.top_banner.mapTo(w, w.top_banner.rect().topLeft()).y() < w.search_input.mapTo(w, w.search_input.rect().topLeft()).y()
print("2) bandeau placé :", pix.size().width(), "x", pix.size().height(), "· au-dessus de la recherche")

# ---------- 3) Logo de démarrage : fond noir détouré ----------
logo = app.start_logo_pixmap(220)
assert logo and not logo.isNull()
limg = logo.toImage()
assert limg.pixelColor(0, 0).alpha() == 0, "fond noir résiduel"
assert limg.pixelColor(limg.width() // 2, limg.height() // 2).alpha() > 0
print("3) logo démarrage : fond noir détouré")

# ---------- 3b) Écussons du tableau de bord : taille du label, jamais rognés ----------
w.show_page(0); w.refresh_all(); q.processEvents()
for lbl in (w.dashboard_home_badge, w.dashboard_away_badge):
    pm = lbl.pixmap()
    assert pm and not pm.isNull(), "écusson du prochain match manquant"
    assert pm.width() == lbl.width() and pm.height() == lbl.height(), (pm.size(), lbl.size())
assert w.dashboard_home_badge.width() == 36, w.dashboard_home_badge.width()
pm = w.match_home_badge.pixmap()
assert pm and pm.width() == w.match_home_badge.width() == 66, (pm.size() if pm else None, w.match_home_badge.width())
print("3b) écussons : dashboard 36x36, match 66x66, centrés")

# ---------- 3c) En-tête et icône boutique : aucun pixmap plus grand que son label ----------
w.show_page(0); w.refresh_all(); q.processEvents()
pm = w.header_club_badge.pixmap()
assert pm and pm.width() <= w.header_club_badge.width() and pm.height() <= w.header_club_badge.height(), (pm.size(), w.header_club_badge.size())
c = app.db(); c.execute("UPDATE facility SET has_shop=1 WHERE id=1"); c.commit(); c.close()
w.show_page(9); w.finance_tabs.setCurrentIndex(1); w.refresh_finance_exploitation(); q.processEvents()
pm = w.fin_shop_jersey_icon.pixmap()
assert pm and pm.width() <= w.fin_shop_jersey_icon.width(), (pm.size(), w.fin_shop_jersey_icon.size())
print("3c) en-tête et icône boutique : pixmaps bornés aux labels")

# ---------- 4) Avatars joueurs : coins arrondis transparents, taille respectée ----------
c = app.db()
p = c.execute("SELECT * FROM player WHERE club_id=1 ORDER BY id LIMIT 1").fetchone()
c.close()
av = w.draw_player_avatar(p, 64)
assert av.size() == QSize(64, 64), av.size()
aimg = av.toImage()
assert aimg.pixelColor(0, 0).alpha() == 0, "coin d'avatar opaque"
assert aimg.pixelColor(32, 40).alpha() > 0
w.show_page(1); q.processEvents()
w.roster_table.setCurrentCell(0, 2); w.update_player_panel(0); q.processEvents()
assert w.player_avatar.pixmap() and w.player_avatar.pixmap().size() == QSize(64, 64)
print("4) avatars : 64x64, coins transparents, fiche express alimentée")

w.close(); q.processEvents()
assert os.path.getsize(r"C:\FM2027V2\data\error.log") == 0
print("RESULT: ALL OK")
