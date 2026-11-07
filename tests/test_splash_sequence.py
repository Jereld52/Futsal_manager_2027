# -*- coding: utf-8 -*-
"""Ouverture : logo studio, image intro, puis menu, avec fondus."""
import os, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap, QColor
from PySide6.QtTest import QTest

TMP = tempfile.mkdtemp(prefix="fm_splash_")
q = QApplication.instance() or QApplication([])
p1 = os.path.join(TMP, "jgames.png")
p2 = os.path.join(TMP, "intro1.png")
for path, color in ((p1, "#c47220"), (p2, "#1f8a4d")):
    pix = QPixmap(480, 270); pix.fill(QColor(color)); pix.save(path)

win = app.SplashWindow([p1, p2]); win.resize(800, 450); win.show(); q.processEvents()
QTest.qWait(650)
assert win._index == 0 and win._current is not None
assert win.image.pixmap() is not None and not win.image.pixmap().isNull()
print("OK logo studio affiché")

win.advance(); QTest.qWait(1000)
assert win._index == 1, win._index
assert win.effect.opacity() > 0.9
print("OK fondu vers l'image d'introduction")

finished = []
win.finished.connect(lambda: finished.append(True))
win.advance(); QTest.qWait(650)
assert finished and not win.isVisible()
print("OK fondu final vers le menu")

# Aucun visuel disponible : on ne bloque pas le démarrage.
empty = app.SplashWindow([os.path.join(TMP, "absent.png")])
done = []
empty.finished.connect(lambda: done.append(True))
empty.show(); q.processEvents(); QTest.qWait(100)
assert done
print("OK repli si les images manquent")
print("RESULT: ALL OK")
