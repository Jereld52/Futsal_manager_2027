# -*- coding: utf-8 -*-
"""Démarrage sur les anciennes sauvegardes : migrations + première page.

Reproduit le vrai boot de `main()` (init_db puis MainWindow) sur une COPIE de
chaque sauvegarde présente dans data/saves. Aucune sauvegarde réelle n'est
modifiée. Le test est ignoré si aucune sauvegarde n'existe.
"""
import os
import shutil
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

SRC_DIR = r"C:\FM2027V2\data\saves"
saves = sorted(
    os.path.join(SRC_DIR, n) for n in os.listdir(SRC_DIR)
    if n.endswith(".db") and os.path.getsize(os.path.join(SRC_DIR, n)) > 0
) if os.path.isdir(SRC_DIR) else []
if not saves:
    print("aucune sauvegarde à tester — ignoré")
    print("RESULT: ALL OK")
    sys.exit(0)

TMP = tempfile.mkdtemp(prefix="fm_oldsave_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "default.db")
app.DATA_DIR = TMP
app.BASE_DIR = TMP
q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
app.QDialog.exec = lambda self, *a, **k: 1

ERR = r"C:\FM2027V2\data\error.log"
before = os.path.getsize(ERR)
tested = 0
for src in saves:
    dst = os.path.join(TMP, "saves", os.path.basename(src))
    shutil.copy(src, dst)
    app.DB_PATH = dst
    app.active_save_path = lambda p=dst: p
    app.set_active_save_path = lambda p: None
    app.init_db()                      # migrations, comme main()
    w = app.MainWindow()
    w.setAttribute(Qt.WA_DontShowOnScreen, True)
    w.show_game_message = lambda *a, **k: True
    w.resize(1600, 1000)
    w.show()
    q.processEvents()
    w.app_stack.setCurrentWidget(w.game_shell)
    q.processEvents()
    w.refresh_all()
    q.processEvents()
    for index in (0, 1, 2, 9, len(w.pages) - 1):
        if 0 <= index < len(w.pages):
            w.show_page(index)
            q.processEvents()
    w.close()
    w.setParent(None)
    w.deleteLater()
    q.processEvents()
    assert os.path.getsize(ERR) == before, (src, open(ERR, encoding="utf-8", errors="replace").read()[:600])
    tested += 1
    print("OK", os.path.basename(src))

print(f"{tested} sauvegarde(s) ouverte(s) sans erreur")
print("RESULT: ALL OK")
