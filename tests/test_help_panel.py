# -*- coding: utf-8 -*-
"""Page AIDE interactive : sommaire, recherche et navigation interne."""
import os, sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app, ui_components
from PySide6.QtWidgets import QApplication, QTabWidget, QFrame
from PySide6.QtCore import QUrl

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))

assert len(ui_components.HELP_TOPICS) >= 24, len(ui_components.HELP_TOPICS)
assert len(ui_components.HELP_THEMES) >= 8, len(ui_components.HELP_THEMES)
print("aide:", len(ui_components.HELP_TOPICS), "sujets /", len(ui_components.HELP_THEMES), "thèmes")

panel = ui_components.HelpPanel(); panel.resize(860, 540); panel.show(); q.processEvents()
assert panel.view.toPlainText().strip(), "article d'accueil vide"
assert panel.findChild(QFrame, "HelpHero") is not None, "bandeau d'aide manquant"
assert panel.search.actions(), "loupe de recherche manquante"
assert not panel.tree.topLevelItem(0).icon(0).isNull(), "puce de thème manquante"
assert "AIDE" in panel.view.toHtml().upper()
print("bandeau et sommaire visuels: OK")

panel.search.setText("salaire"); q.processEvents()
assert "résultat" in panel.count.text().lower() or "trouvé" in panel.count.text().lower()
assert panel.tree.topLevelItemCount() >= 1
print("recherche salaire:", panel.count.text())

panel.search.setText("offre transfert"); q.processEvents()
assert panel.tree.topLevelItemCount() >= 1
print("recherche multi-mots:", panel.count.text())

panel.search.setText("zzzz-introuvable"); q.processEvents()
assert "Aucun résultat" in panel.view.toPlainText()
print("recherche vide: OK")

panel._reset(); q.processEvents()
assert "boucle de jeu" in panel.view.toPlainText()
panel._on_link(QUrl("topic:prets")); q.processEvents()
assert "prêts" in panel.view.toPlainText().lower()
print("navigation interne: OK")

opts = {"theme": "Nuit violette", "font_size": 10, "window_mode": "Maximisé",
        "difficulty": "Normale", "brief_cadence": "Hebdomadaire"}
dlg = ui_components.GameOptionsDialog(opts, None)
tabs = dlg.findChild(QTabWidget)
labels = [tabs.tabText(i) for i in range(tabs.count())]
assert "AIDE" in labels, labels
idx = labels.index("AIDE")
tabs.setCurrentIndex(idx); dlg.resize(900, 680); dlg.show(); q.processEvents()
assert dlg.findChild(ui_components.HelpPanel) is not None
print("onglet AIDE intégré: OK")
dlg.close()
panel.close()
print("RESULT: ALL OK")
