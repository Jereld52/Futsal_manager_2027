# -*- coding: utf-8 -*-
"""Messagerie : badge leger (COUNT) sans charger la page."""
import os, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication

TMP = tempfile.mkdtemp(prefix="fm_msgbadge_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP
app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=3,
            identity={"name": "Badge FC", "arena_name": "A", "color1": "#2f6fed",
                      "color2": "#101a2e", "division": 3, "difficulty": "Normal"})
try:
    open(r"C:\FM2027V2\data\error.log", "r+b").truncate(0)
except FileNotFoundError:
    open(r"C:\FM2027V2\data\error.log", "wb").close()

c = app.db()
c.execute("DELETE FROM manager_message")
for i in range(2):
    c.execute("INSERT INTO manager_message(kind,title,body,created_date,due_date,status,action_data,is_read) "
              "VALUES('club_news',?,'test','2026-07-01','2026-07-01','waiting','{}',0)", ("Info %d" % i,))
for i in range(5):
    c.execute("INSERT INTO manager_message(kind,title,body,created_date,due_date,status,action_data,is_read) "
              "VALUES('scout_report',?,'test','2026-07-01','2026-07-01','waiting','{}',0)", ("Rapport %d" % i,))
c.commit(); c.close()

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
w = app.MainWindow()
w.show_game_message = lambda *a, **k: True
w.resize(1300, 800)
w.show()
q.processEvents()
w.app_stack.setCurrentWidget(w.game_shell)
w.show_page(0)
q.processEvents()
w.refresh_message_badges()
q.processEvents()
assert w.inbox_nav_badge.text() == "2", w.inbox_nav_badge.text()
assert w.inbox_nav_badge.isVisible()
assert w._messages_dirty is True, "la page messagerie ne doit pas avoir ete chargee"
assert w.msg_notify_timer.interval() == 30000, w.msg_notify_timer.interval()
print("OK: badge leger = 2 (scout reports ignores)")

c = app.db()
c.execute("UPDATE manager_message SET is_read=1 WHERE kind='club_news' AND title='Info 0'")
c.execute("INSERT INTO manager_message(kind,title,body,created_date,due_date,status,action_data,is_read) "
          "VALUES('transfer_sale','Offre','test','2026-07-01','2026-07-01','ready','{}',0)")
c.commit(); c.close()
w.refresh_message_badges(); q.processEvents()
assert w.inbox_nav_badge.text() == "2", w.inbox_nav_badge.text()
w.show_page(0); w.refresh_all(); q.processEvents()
assert w.inbox_nav_badge.text() == "2", w.inbox_nav_badge.text()
print("OK: badge mis a jour sans ouvrir la messagerie")

w.show_page(6); q.processEvents()
assert w.inbox_nav_badge.text() == "2", "ouvrir la boîte ne doit pas marquer les messages lus"
# Lire un message met le badge à jour.
target = None
for i in range(w.action_message_list.count()):
    if bool(w.action_message_list.item(i).data(app.MessageListDelegate.ROLE_UNREAD)):
        target = i; break
if target is None:
    target = 0
w.action_message_list.setCurrentRow(target); q.processEvents()
assert w.inbox_nav_badge.text() == "1", w.inbox_nav_badge.text()
print("OK: ouverture sans lecture automatique, badge après lecture = 1")

w.close(); q.processEvents()
size = os.path.getsize(r"C:\FM2027V2\data\error.log")
print("error.log =", size, "octet(s)")
assert size == 0
print("RESULT: ALL OK")
