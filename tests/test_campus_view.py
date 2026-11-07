# -*- coding: utf-8 -*-
"""Vue extérieure : les nouveaux bâtiments modifient réellement l'illustration."""
import os, sys, hashlib
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
from PySide6.QtWidgets import QApplication
import app

q = QApplication.instance() or QApplication([])
CLUB = {"name": "Campus FC", "arena_name": "Arena Horizon", "color1": "#c47220",
        "color2": "#14171f", "reputation": 40, "division": 3}


def digest(facility):
    view = app.FacilityCampusView(); view.resize(1100, 600)
    view.set_arena_state(facility, CLUB, capacity=6000, attendance=4000)
    pix = view.grab()
    assert not pix.isNull()
    image = pix.toImage()
    return hashlib.md5(bytes(image.constBits())).hexdigest()


base = {"arena_level": 4, "medical_level": 3, "youth_level": 1, "marketing_level": 2,
        "lighting_level": 2, "parking_level": 2, "has_bar": 0, "has_vip": 0, "has_shop": 0,
        "has_fan_zone": 0, "video_level": 0, "volunteer_level": 0, "restaurant_level": 0}
h0 = digest(base)
for key, name in (("video_level", "laboratoire vidéo"), ("volunteer_level", "bénévoles"),
                  ("restaurant_level", "restaurant"), ("youth_level", "formation")):
    changed = dict(base); changed[key] = 2
    assert digest(changed) != h0, name

full = dict(base)
full.update({"video_level": 3, "volunteer_level": 3, "restaurant_level": 3,
             "youth_level": 4, "has_bar": 1, "has_shop": 1, "has_vip": 1, "has_fan_zone": 1})
assert digest(full) != h0
print("OK vue extérieure : laboratoire vidéo, bénévoles, restaurant et formation rendus")
print("RESULT: ALL OK")
