# -*- coding: utf-8 -*-
"""Le terrain 2D doit réellement peindre le court (non-régression QPixmap)."""
import os, sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from match_pitch2d import Pitch2DWidget

q = QApplication.instance() or QApplication([])
w = Pitch2DWidget(); w.resize(820, 420); w.show(); q.processEvents()
img = w.grab().toImage()
assert not img.isNull()
cx, cy = int(img.width() * 0.30), int(img.height() * 0.30)
center = img.pixelColor(cx, cy)
cx2, cy2 = int(img.width() * 0.70), int(img.height() * 0.65)
quarter = img.pixelColor(cx2, cy2)
for name, c in (("gauche", center), ("droite", quarter)):
    assert c.green() > c.red() + 8, (name, c.red(), c.green(), c.blue())
print("OK terrain 2D peint : gauche rgb", center.red(), center.green(), center.blue())
print("RESULT: ALL OK")
