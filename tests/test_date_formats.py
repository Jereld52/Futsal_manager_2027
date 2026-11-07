# -*- coding: utf-8 -*-
"""Dates affichées : toujours au format français JJ/MM/AAAA."""
import os, sys, tempfile, re
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication, QLabel, QTableWidget, QTextEdit
from PySide6.QtTest import QTest

assert app.fmt_date_fr("2026-07-01") == "01/07/2026"
assert app.fmt_datetime_fr("2026-07-01T13:51") == "01/07/2026 13:51"
assert app.fmt_datetime_fr("2026-07-01 13:51") == "01/07/2026 13:51"

TMP = tempfile.mkdtemp(prefix="fm_dates_test_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP; app.BASE_DIR = TMP
app.OPTIONS_FILE = os.path.join(TMP, "options.json")
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=3,
            identity={"name": "Dates FC", "arena_name": "A", "color1": "#c47220",
                      "color2": "#14171f", "division": 3})

c = app.db()
c.execute("INSERT INTO finance_tx(club_id,label,amount,created_at,category) VALUES(1,'Test mouvement',-1000,'2026-09-15 10:30','Divers')")
c.execute("INSERT INTO news(title,body,created_at) VALUES('Test actu','Contenu','2026-09-15 10:30')")
pid = int(c.execute("SELECT id FROM player WHERE club_id=1 ORDER BY id LIMIT 1").fetchone()["id"])
c.execute("INSERT INTO player_history(player_id,season,club_id,kind,detail,created_at) VALUES(?,1,1,'transfer','Test', '2026-09-15T10:30')", (pid,))
c.commit(); c.close()

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
w = app.MainWindow(); w.resize(1560, 900); w.show()
w.show_game_message = lambda *a, **k: True
w.app_stack.setCurrentWidget(w.game_shell); q.processEvents()

ISO = re.compile(r"\b(19|20)\d{2}[-/]\d{1,2}[-/]\d{1,2}")
bad = []

def scan(widget, where):
    for lab in widget.findChildren(QLabel):
        if ISO.search(lab.text() or ""):
            bad.append((where, lab.text()[:80]))
    for te in widget.findChildren(QTextEdit):
        if ISO.search(te.toPlainText() or ""):
            bad.append((where, te.toPlainText()[:80]))
    for table in widget.findChildren(QTableWidget):
        for r in range(table.rowCount()):
            for col in range(table.columnCount()):
                item = table.item(r, col)
                if item and ISO.search(item.text() or ""):
                    bad.append((where, item.text()[:80]))

w.show_page(0); QTest.qWait(200); q.processEvents(); scan(w.stack.currentWidget(), "dashboard")
w.show_page(9); QTest.qWait(200); q.processEvents(); scan(w.stack.currentWidget(), "finances")
w.show_page(7); QTest.qWait(200); q.processEvents()
w.mercato_tabs.setCurrentIndex(4); q.processEvents()
try: w._refresh_transfer_history()
except Exception: pass
q.processEvents(); scan(w.stack.currentWidget(), "transferts/historique")

assert not bad, bad
print("OK dates françaises : dashboard, finances et historique des transferts")
print("RESULT: ALL OK")
