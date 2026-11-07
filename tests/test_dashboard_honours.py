# -*- coding: utf-8 -*-
"""Direction sportive : palmarès chargé, lisible et défilable."""
import os, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication, QScrollArea
from PySide6.QtTest import QTest

TMP = tempfile.mkdtemp(prefix="fm_honours_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP; app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=3,
            identity={"name": "Honours FC", "arena_name": "A", "color1": "#c47220",
                      "color2": "#14171f", "division": 3})

c = app.db()
for season in range(1, 11):
    c.execute("INSERT INTO club_honours(club_id,season,division,kind,detail) VALUES(1,?,?, 'champion','')", (season, 3))
c.execute("INSERT INTO club_honours(club_id,season,division,kind,detail) VALUES(1,5,4,'promotion','')")
c.execute("INSERT INTO club_honours(club_id,season,division,kind,detail) VALUES(1,7,2,'relegation','')")
c.commit(); c.close()

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
w = app.MainWindow(); w.resize(1560, 900); w.show()
w.show_game_message = lambda *a, **k: True
w.app_stack.setCurrentWidget(w.game_shell); q.processEvents()
w.show_page(0); QTest.qWait(400); q.processEvents()

assert isinstance(w.honours_list, QScrollArea)
assert w.honours_count.text() == "10", w.honours_count.text()
assert w.honours_rows.count() >= 10
assert w.honours_list.verticalScrollBar().maximum() > 0
print("OK palmarès chargé :", w.honours_count.text(), "titres, scroll", w.honours_list.verticalScrollBar().maximum())
w.grab().save(r"C:\Users\jauvray\AppData\Local\Temp\opencode\dashboard_honours_1560.png")
print("RESULT: ALL OK")
