# -*- coding: utf-8 -*-
"""Démarrage : pas de logo dupliqué et ouverture automatique sans double clic."""
import os
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap
import app

q = QApplication.instance() or QApplication([])
TMP = tempfile.mkdtemp(prefix="fm_splash_")
paths = []
for name, color in (("jgames.png", "#112233"), ("intro1.png", "#223344")):
    path = os.path.join(TMP, name)
    pix = QPixmap(40, 20); pix.fill(color); pix.save(path)
    paths.append(path)
# Le même nom dans data/ et assets/ ne doit produire qu'un écran.
dup = app.unique_splash_paths([paths[0], paths[0], paths[1], paths[1]])
assert len(dup) == 2 and dup[0] == paths[0] and dup[1] == paths[1], dup

w = app.SplashWindow(dup)
w.effect.setOpacity(1.0)
w._fade_done()
assert w._auto_timer.isActive(), "l'ouverture doit avancer automatiquement"
assert "PASSER" in w.hint.text(), w.hint.text()
w._auto_timer.stop(); w.close(); q.processEvents()
print("1) logos dédupliqués :", [os.path.basename(x) for x in dup])
print("2) ouverture automatique :", w.hint.text())
print("RESULT: ALL OK")
