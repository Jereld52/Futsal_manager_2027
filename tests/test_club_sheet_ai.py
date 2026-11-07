# -*- coding: utf-8 -*-
"""Fiche club IA : effectif par defaut, sans classement, derniers matchs complets."""
import os, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app

TMP = tempfile.mkdtemp(prefix="fm_clubsheet_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP; app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=2,
            identity={"name": "Sheet FC", "arena_name": "A", "color1": "#c47220",
                      "color2": "#14171f", "division": 2})
from PySide6.QtWidgets import QApplication, QTabWidget, QListWidget, QTableWidget, QLabel, QDialog
q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
w = app.MainWindow(); w.resize(1280, 800); w.show()
w.app_stack.setCurrentWidget(w.game_shell); q.processEvents()
w.show_game_message = lambda *a, **k: True
assert w.stack.currentIndex() == 0, "l'accueil dans le jeu doit etre Direction sportive"
captured = []
def _exec(self, *a, **k):
    self.resize(1020, 820); self.show(); QApplication.processEvents()
    captured.append(self); return QDialog.Rejected
app.QDialog.exec = _exec

c = app.db()
ai = int(c.execute("SELECT id FROM club WHERE id<>1 AND division=2 ORDER BY id LIMIT 1").fetchone()["id"])
c.execute("""UPDATE fixture SET played=1,home_goals=4,away_goals=2
             WHERE id=(SELECT id FROM fixture WHERE home_club_id=? OR away_club_id=? LIMIT 1)""", (ai, ai))
c.commit(); c.close()

w.show_club_profile(ai); q.processEvents()
dlg = captured[-1]
tabs = dlg.findChildren(QTabWidget)[0]
texts = [tabs.tabText(i) for i in range(tabs.count())]
print("onglets:", texts, "| courant:", tabs.currentIndex())
assert not any("SAISON" in t for t in texts), texts
assert tabs.currentIndex() == 0 and "EFFECTIF" in tabs.tabText(0)
roster = dlg.findChild(QListWidget, "ClubRosterCards")
assert roster.count() >= 10, roster.count()
stats = [l.text() for l in dlg.findChildren(QLabel) if "NIVEAU MOYEN" in l.text()]
assert stats and "MASSE" in stats[0] and "FINS DE CONTRAT" in stats[0], stats
recent = None
for t in dlg.findChildren(QTableWidget):
    if t.columnCount() == 5 and t.horizontalHeaderItem(2) and t.horizontalHeaderItem(2).text() == "DOMICILE":
        recent = t; break
assert recent is not None, "table derniers matchs absente"
assert "DERNIERS MATCHS" in texts, texts
assert tabs.widget(texts.index("DERNIERS MATCHS")).isAncestorOf(recent), "tableau hors onglet"
assert recent.rowCount() >= 1
home = recent.item(0, 2).text(); away = recent.item(0, 4).text()
print("dernier match:", home, "|", recent.item(0, 3).text(), "|", away)
assert home and away, "noms de clubs incomplets"
dlg.close()
print("RESULT: ALL OK")
