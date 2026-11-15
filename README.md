# Futsal Manager 2027 — FM2027V2

Jeu de gestion de club de futsal en Python + PySide6. Interface 100 % Qt,
sauvegardes SQLite locales (aucun serveur, aucun compte).

## Lancer le jeu

```text
LANCER.bat
```

`LANCER.bat` installe les dépendances si besoin (`PySide6`) puis lance
`pythonw main.py` : **aucune console** ne reste ouverte. Pour voir les messages
techniques, lancer à la place :

```text
python main.py
```

Prérequis : Python 3.10+ et PySide6 6.7+ (`requirements.txt`).

## Où sont mes données

| Élément | Emplacement |
| --- | --- |
| Sauvegardes | `data/saves/*.db` |
| Carrière active | `data/active_save.txt` |
| Options du jeu | `data/game_options.json` |
| Largeurs de colonnes | `data/roster_columns.json` |
| Journal d'erreurs | `data/error.log` |
| Dernier crash Python | `data/fault.log` |
| Trace UI (diagnostic) | `data/ui_trace.log` — **désactivée par défaut** |

- `data/error.log` doit rester **vide**. S'il contient une trace, c'est un bug :
  la joindre au rapport.
- La trace UI s'active uniquement pour un diagnostic :
  `set FM2027_TRACE=1` (Windows) avant de lancer. Elle est plafonnée à 2 Mo.

## Architecture

| Fichier | Rôle |
| --- | --- |
| `main.py` | Point d'entrée minimal → `app.main()` |
| `app.py` | Fenêtre principale, pages, vues et orchestration (module central) |
| `ui_components.py` | Composants Qt réutilisables (dialogue de club, plateau tactique, maillots…) |
| `logo_data.py` | Logo officiel et ressources vectorielles |
| `help_content.py` | Contenu de l'aide interactive |
| `db.py` | Schéma SQLite, migrations idempotentes, `init_db()` |
| `match_engine.py` | Simulation des matchs IA |
| `match_pitch2d.py` | Rendu 2D du match live |
| `squad_engine.py` | Effectifs IA, effectif minimum, fin de saison |
| `loan_engine.py` | Prêts, temps de jeu et retours |
| `ai_clubs.py`, `ai_finance.py`, `ai_scouting.py` | Comportements des clubs IA |
| `club_profiles.py` | Profils et identités des clubs |
| `wage_budget.py` | Masse salariale et budget |
| `game_utils.py` | Dates, notes, formats monétaires |
| `legacy_import.py` | Import d'anciennes sauvegardes SQL |

Les sauvegardes sont écrites **en continu** dans la base de la carrière ; le
bouton de sauvegarde crée un point de reprise compacté.

## Immersion (match day)

- **Avant-match** : arrivée au gymnase, affluence estimée, ambiance du vestiaire,
  forme de l'adversaire et enjeu du board, puis vérification du cinq et causerie.
- **Direct** : bandeau de commentaire live + onglet COMMENTAIRE, sons de salle
  synthétisés (sifflet, buzzer, but, arrêt, foule) et bouton **SON : ON/MUET**.
- **Après-match** : scène de vestiaire (héros, gardien, capitaine), puis
  conférence de presse en deux questions (réaction au résultat, mot aux supporters).
- **PREMIERS PAS** : guide des 3 premiers jours (cinq, causerie, premier match,
  mercato), affiché une fois et accessible depuis la Direction sportive.
- **Signaler un bug** : bouton dans les options, crée un ZIP avec logs, version
  et copie optionnelle de la sauvegarde active.
- Les sons sont générés dans `data/audio` ; `FM2027_NO_AUDIO=1` les coupe.

## Terrain 2D du direct

- Boucle de rendu **~60 fps** avec pas physique temporel : les joueurs courent,
  accélèrent, freinent et changent de direction sans téléportation.
- Positionnement vivant : bloc qui glisse avec le ballon, pressing selon la
  tactique, courses de soutien, gardien qui suit le ballon, écartement des pions.
- Le terrain suit réellement le texte : passeur → receveur, tireur, gardien qui
  arrête, fautif, corner, buteur et célébration.
- **Phases de construction** lisibles : construction basse, construction,
  progression, dernier tiers, transition, phase arrêtée, bloc défensif.
- Les **systèmes** (2-2, 3-1, 4-0, 1-2-1, 1-1-2), la largeur, l'axe de jeu, le
  bloc, le pressing, le tempo et la mentalité modifient réellement les placements
  et la circulation du ballon.
- Les **attributs des joueurs** comptent dans le 2D : vitesse, accélération,
  passe, dribble, placement et traits cachés influencent courses et choix de passe.
- **1× = temps réel strict** (20 s réelles par tranche de 20 s simulées, match
  complet en ~40 min) ; 2× à 8× accélèrent jusqu'au mode express pour les tests
  et les matchs rapides.
- Horloge **fluide** entre les ticks du moteur ; les évènements et le score
  restent décidés par le moteur, le rendu est strictement en lecture seule.
- Entre deux actions, une circulation de balle visuelle garde le match vivant.
- Les niveaux et potentiels sont affichés par des **étoiles vectorielles**
  (demi-étoiles réelles), jamais par des caractères `★`/`☆`/`½`.

## Scouting, étoiles et attributs cachés

- Le **niveau** et le **potentiel** ne s'affichent plus en chiffres : uniquement
  en étoiles (demi-étoiles incluses).
- Les **attributs cachés** (sang-froid, régularité, matchs à enjeu, activité,
  agressivité, leadership, professionnalisme, fragilité, polyvalence) pèsent
  sur le moteur : conversion, fautes, fatigue, blessures, forme et grands matchs.
- Les **recruteurs** estiment le niveau et le potentiel avec une erreur qui
  dépend de leur niveau, du nombre de rapports et de la connaissance du joueur.
  Un faible recruteur peut surestimer ou sous-estimer un joueur.
- Les fiches affichent des **statistiques détaillées** : tirs, tirs cadrés,
  passes réussies, tacles, interceptions, fautes, minutes, arrêts, clean sheets,
  pourcentages et note moyenne.

## Tests

```text
python tests\run_tests.py            # suite complète (102 suites)
python tests\run_tests.py finances   # sous-ensemble par nom
python tests\global_smoke.py fresh   # parcours complet, univers neuf
python tests\global_smoke.py save    # idem sur une copie de sauvegarde
```

Les tests s'exécutent hors écran (`QT_QPA_PLATFORM=offscreen`), sur des bases
temporaires : ils ne touchent jamais aux sauvegardes réelles. En fin de suite :
`RESULT : ALL OK` et `data/error.log` à 0 octet.

## Bêta — checklist avant envoi

1. `python tests\run_tests.py` → **ALL OK**, `data/error.log` vide.
2. Lancer une carrière neuve : création du club, premier match, sauvegarde,
   rechargement.
3. Vérifier l'affichage en 1280×720, 1366×768 et 1920×1080.
4. En cas de bug, transmettre : action effectuée, capture, `data/error.log`
   et éventuellement `data/fault.log`. Ne jamais envoyer `data/saves/` sans
   accord (données de carrière).

## Nettoyage / archives

- `code_backups/` : copies horodatées du code (12 dernières) et archives de
  nettoyage (modules legacy, anciennes sauvegardes de test, anciens logs).
- `data/captures/` : captures d'écran d'audit (hors données de jeu).
