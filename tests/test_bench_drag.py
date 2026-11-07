# -*- coding: utf-8 -*-
"""Regression : le drag du banc ne doit pas lever NameError (QDrag importe)."""
import os, sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import ui_components
from PySide6.QtWidgets import QApplication, QListWidgetItem
from PySide6.QtCore import Qt

q = QApplication.instance() or QApplication([])
assert hasattr(ui_components, "QDrag"), "QDrag absent de ui_components"
bench = ui_components.DraggableBench()
item = QListWidgetItem("Joueur test")
item.setData(Qt.UserRole, 42)
item.setData(Qt.UserRole + 1, False)
bench.addItem(item); bench.setCurrentItem(item)

calls = []
orig = ui_components.QDrag.exec
ui_components.QDrag.exec = lambda self, *a, **k: calls.append(a) or 0
try:
    bench.startDrag(Qt.MoveAction)
finally:
    ui_components.QDrag.exec = orig
assert calls, "startDrag n'a pas appele QDrag.exec"
item.setData(Qt.UserRole + 1, True)
calls.clear()
ui_components.QDrag.exec = lambda self, *a, **k: calls.append(a) or 0
try:
    bench.startDrag(Qt.MoveAction)
finally:
    ui_components.QDrag.exec = orig
assert not calls, "un joueur blesse ne doit pas etre glisse"
print("RESULT: ALL OK")
