# Éditeur de sauvegarde — Futsal Manager 2027

Outil **hors du jeu** : il ouvre directement un fichier `.db` de sauvegarde.
Aucun bouton, aucun raccourci n'est ajouté dans le jeu — les joueurs ne le
voient donc pas.

## Lancer

Double-clic sur `EDITEUR.bat`, ou depuis ce dossier :

```text
python editeur_sauvegarde.py
```

L'éditeur ouvre par défaut la carrière active (`data/active_save.txt`).

> **Ferme le jeu avant de modifier.** L'éditeur détecte un verrou ou des
> fichiers `-wal`/`-shm` et affiche un avertissement. Une base ouverte par le
> jeu peut réécrire les valeurs au chargement suivant.

## Onglets

| Onglet | Ce qui est modifiable |
| --- | --- |
| **Clubs** | budget, réputation, division, nom de la salle. Filtres + tri par clic sur les en-têtes (budget, réputation, division, nom). |
| **Joueurs** | identité, club (transfert direct ou joueur libre), 9 attributs, potentiel, valeur, salaire, contrat, condition, moral, blessures, suspensions, cartons, liste des transferts. Filtres par poste, âge, niveau, potentiel, valeur, contrat et statut ; tri par en-têtes (niveau, potentiel, âge, valeur…) ; export CSV. |
| **Staff** | embauche, niveau 1–5, nom, nationalité des 8 postes |
| **Infrastructures** | 9 niveaux (tribunes, médical, formation, marketing, éclairage, parking, vidéo, bénévoles, restaurant), 6 équipements, prix du billet. Concerne le **club du joueur (club 1)** : les autres clubs n'ont pas de campus séparé. Une baisse est protégée par un plafond que le jeu respecte au chargement. |
| **Sauvegardes** | création et restauration de copies de secours, intégrité de la base |

- La liste des joueurs affiche **niveau** et **potentiel** pour toute la base
  (60 clubs), avec recherche, filtres par colonne (poste, âge min/max, niveau
  mini, potentiel mini, valeur mini, contrat, statut), tri et **export CSV**.
- Le bouton **RECALCULER LA VALEUR** applique le même barème que le jeu.
- Changer le club d'un joueur remet à zéro prêt et pré-contrat pour éviter les
  incohérences ; un numéro de maillot déjà pris est libéré.
- Le potentiel est automatiquement relevé s'il devient inférieur au niveau.

## Bien démarrer : copie de travail

En haut, le bandeau indique l'état réel :
- **PRÊTE · ÉCRITURE** (vert) : la sauvegarde est modifiable ;
- **JEU OUVERT ?** (ambre) : des fichiers `-wal`/`-shm` existent, ferme le jeu ;
- **VERROUILLÉE** (rouge) : la base est verrouillée, les écritures sont bloquées.

**DUPLIQUER POUR TESTER** crée une copie `..._test.db` et bascule l'éditeur
dessus. La carrière d'origine n'est plus touchée, et la copie apparaît dans
**CHARGER UNE PARTIE** pour jouer avec les modifications.

Les écritures sont **immédiates** dans le fichier ouvert (pas de bouton
« enregistrer » global). Les copies de secours servent à revenir en arrière.

## Infrastructures : baisser un niveau

Le jeu répare automatiquement les niveaux depuis l'historique des chantiers
(et les recettes de tribunes). Une baisse faite uniquement dans la table
`facility` pouvait donc être annulée au chargement suivant.

L'éditeur pose maintenant un **plafond manuel** (`facility_editor_cap_<bâtiment>`)
que le jeu respecte :

- la baisse reste effective après chargement/rafraîchissement ;
- elle protège aussi l'arène contre la reconstruction depuis les anciens
  paiements ;
- dès qu'un **vrai chantier se termine dans le jeu**, ce plafond est retiré
  pour laisser le bâtiment monter normalement.

Réapplique une fois la baisse avec cette version de l'éditeur.

## Raccourcis

- `Ctrl+F` : recherche joueur ;
- `Ctrl+S` : sauvegarde de secours ;
- `Ctrl+D` : dupliquer la sauvegarde ouverte.

## Sécurité

- Avant la **première écriture** d'une session, une copie horodatée est créée
  dans `data/saves/editeur_backups/` (ou `editeur_backups/` à côté du fichier) :
  `ma_sauvegarde_AAAAMMJJ_HHMMSS_auto.db`.
- Ce sous-dossier n'est pas lu par le menu **CHARGER UNE PARTIE** du jeu : les
  copies de l'éditeur n'apparaissent donc pas comme des carrières.
- Les 10 copies les plus récentes sont conservées.
- **SAUVEGARDES → RESTAURER** crée d'abord une copie de sécurité de l'état
  courant, puis remplace le fichier.
- Aucune table n'est créée, supprimée ou migrée.
- Les valeurs hors limites sont refusées avec un message explicite.

## Distribution

Dossier réservé aux tests internes. Ne pas l'inclure dans une archive de bêta
publique : déplacer ou supprimer `editeur/` avant de compresser le jeu.
