# ÉTAT PROJET FM2027V2 — fichier de session (compact)

## Outils de session — TOUS DANS `C:\FM2027V2\tests\`
- **`tests\run_tests.py`** = point d'entrée unique des tests courts :
  `python tests\run_tests.py` (toutes suites, ~8 s) ou filtre par nom partiel.
  Tronque `data/error.log` au départ, exige 0 octet à la fin, résumé PASS/FAIL.
- Suites : `test_banqueroute.py` (4 s, chaîne banqueroute moteur),
  `test_prepaid_discard.py` (2 s, paie/verrous), `test_daily_loop.py` (2 s, boucle
  quotidienne + batch marché), `test_messagerie.py` (2 s, brief + filtres
  messagerie), `test_ui_start_render.py` (2 s, captures UI → `tests\captures\`).
  Scanners statiques : `scan_conn_leak.py`, `scan_nplusone.py`.
- Audits (hors suite courte) : `tests\audit_gameplay.py` (6 divisions × N matchs,
  invariants monde/classements/coupe/prêts) et `tests\audit_scenarios.py`
  (forfaits, club décimé, changement de club — ce dernier est aussi dans la suite).
  Audit profond : `tests\audit_deep.py` (3 changements de club, faillite forcée,
  saturation du fil d'actualité).
- Pilote saison (si, et seulement si, demande explicite de sim long) :
  `tests\sim_career10.py`. `SIM_SEASONS=N`=N−1 saisons ; `RICH=1 RICH_X=n` =
  mode "je me crois riche" (injection capital (n−1)×budget, paie complète sans
  exemption) ; `SCENARIO`, `GEM_POLICY`, `DIAG`, `MEMPROBE` contrôlent le pilote.
- Sondes PS : `ps_probe.py`, `ps_check.py`, `ps_oc.py`, `ps_shells.py`, `ps_who.py`.
- Rollback historique : `tests\archive\futsal_manager_*.zip` (2 états du 10-16).
- Sims au **premier plan** (les shells arrière-plan meurent au restart OpenCode).
- **NE PAS lancer de sims saison-complète** hors demande explicite : tests courts
  suffisent pour valider les correctifs.

## Politique de session (A RESPECTER)
- **PAS de recompilation .exe** ; tout via `C:\FM2027V2\LANCER.bat`. Compiler seulement sur demande.
- Headless : `QT_QPA_PLATFORM=offscreen`, DB via app.DB_PATH sur TEMP ; `$env:PYTHONIOENCODING='utf-8'` obligatoire.
- `data/error.log` : indicateur global — **toujours présent, 0 octet ; tronquer, jamais supprimer**.
- Ne jamais écrire `data/active_save.txt` ni toucher aux saves utilisateur (`dsddsdds_*.db`,
  `data/futsal_manager.db` = DB courante). **Purges** : uniquement artifacts de test/logs, jamais les écrans.
- Éviter `python -c` avec quotes/parenthèses imbriquées : écrire un .py temporaire, l'exécuter, puis le supprimer.
- `db()` : autocommit OFF → commit/fermeture explicites ; `current_date` mot-clé SQLite ; utiliser une **connexion
  partagée** dans les tests (les connexions multiples voient des snapshots périmés).

## État du moteur (app.py)
- **Banqueroute (2026-10-24)** : `process_board_financial_watch` (branché chaque jour, après `process_player_payroll`
  ~L11520, méthode ~L11742) : J1 rouge → news « Trésorerie négative » + embargo ; 60 j puis +60 j → « Plan de
  redressement » (vente forcée du joueur le plus dispendieux, noyau min 8 joueurs) ; retour au vert → reset+news.
  Embargo : `submit_market_offer` (~L9556) refuse si budget<0 ; `take_loan` refuse. Compteur méta `club1_red_days`.
  Clôture : réputation pénalisée (process_reputation_update). ✅ test_banqueroute ALL OK.
- Paie mensuelle joueurs le 1er du mois (après staff) ; à la signature : indemnité seule + contrôle indemnité+1 an
  salaires ; migration anti-double-paie méta `payroll_reform_season` + `prepaid_wage_ids`.
  `_prepaid_wage_discard(player_id, conn=None)` — toujours passer la conn du flux (bug « database is locked » corrigé).
- Faille salaire plombée (plancher `player_salary_demand`), fiche joueur → offre, négociation 2 temps messagerie.
- Académie verrouillée (`academy_unlocked`, 250 000 €), verrous dans `start_facility_project` ET `upgrade_facility`.
- Économie par division : RANK_BASE, PROMO_PRIZE 40k→600k, PARA_PRIZE, prime/victoire, TV `4000+6500*(7-div)`.
- Doctrine pilote validée : EFFECTIF D'ABORD (moyenne ≥ norme div +0,6 avant tout chantier ≥100k en L4-L6).

## UI (2026-10-24)
- **Page de démarrage verticale** : logo au-dessus du menu (logo = `data/logo2.png` prioritaire via `start_logo_pixmap`
  ~L3520), « ÉDITION CARRIÈRE 2027 » sous le logo, menu centré dessous.
- **Aperçu création club** (`ui_components.py` ClubIdentityPreview) : zone à ratio fixe 300×175 centrée ; widget
  sizeHint explicite (sinon largeur 0) ; 380-420 px max dans le dialogue. ✅ captures test_ui_start_render.
- `data/logo2.png` = logo officiel fourni par l'utilisateur (source : Desktop\IMGFUTSAL\logo2.png).

## Messagerie (2026-10-24)
- **Brief du club réglable** : `brief_cadence` « Hebdomadaire » (défaut, publié lundi) ou « Quotidien » ; appel de
  `generate_live_club_messages` sorti du filtre lundi de la boucle quotidienne ; titre honnête selon la cadence.
- **Filtres par catégorie** dans Options → panneau MESSAGERIE (`ui_components.py` GameOptionsDialog, `values()`
  retourne now toutes les clés) : `msg_anniversaire` (OFF par défaut — vieillissement moteur inchangé, seuls les
  messages näs), `msg_perf`, `msg_blessure`, `msg_staff` (inclut la news « Préparateur physique » du lundi),
  `msg_transfert`, `msg_contrat`. Persistance : `data/game_options.json` (load_game_options defaults complétés) ;
  `open_game_options` fait `self.game_options.update(values)` complet.
- ✅ test_messagerie (brief hebdo lundi seulement, quotidien, tout OFF → silence, anniversaires age sans message).

## Constats
- L'économie est très solvable : même en mode riche (×5, paie complète), jamais rouge en 2 saisons L6 — le moteur
  refuse toute indemnité > budget et les recettes couvrent ~30 k€/mois de paie. La banqueroute est prête et testée.
- Fuite mémoire Qt observée sur run long (14,7 Go/40 min) : purge widgets à prévoir côté pilote.

## Fluidité (2026-10-24)
- **Boucle quotidienne** : `update_player_market_values` batché en 2 `executemany` (marché + salaires IA,
  `_converge_ai_salary` devient pur) au lieu de ~1 UPDATE/joueur/jour ; `UPDATE player SET condition` filtré
  `WHERE condition<100` (600 joueurs traités en 0,07 s).
- **Index de fluidité** créés à la fin d'`ensure_schema` (TOLÉRANCE obligatoire : beaucoup de colonnes —
  is_free_agent, transfer_listed, market_value, contract_years, division, planned_date… — n'existent que via
  migration ALTER, donc PAS de CREATE INDEX dans le schema de base) : player(club_id, marché, contrats),
  fixture(date/season/club), manager_message(status/due, kind/status), finance_tx(date, category), news,
  club(division), training_session, loan, facility_project, player_attr_archive.
- 0 fuite de connexion détectée (scanner `tests\scan_conn_leak.py`) ; le scan N+1 (`tests\scan_nplusone.py`)
  liste les boucles SQL le plus souvent légitimes (batchs saisonniers, réparations une fois).

## En attente de feu vert
1. Renouvellements plafonnés (~85 % du plafond de masse) ; recalibrer WAGE_CAP L6 (20k intenable avec renouvellements
   +20 %/an — pilote `sim_career10.py` WAGE_CAP, moteur non touché) ; bradage listés (−30 %) ; purge widgets.
2. Axes de fond : retraites IA + intake indexé ; clubs <12 signent libres ; renégociation 0-an.
3. Compaction légère : lire CE FICHIER en priorité ; historique conversation = minimisé.

## Terrain 2D Match Day — niveau 1 (2026-10-24)
- **Nouveau module `match_pitch2d.py`** : `Pitch2DWidget` (terrain 40x20 ratio fixe,
  paintEvent pur, AUCUNE modification moteur — mouchard lecture-seule de
  `match_state` a chaque tick via `app._pitch_sync`), `LiveMatchBanner` =
  MatchActionBanner retransmettant chaque action (kickoff/pass/build/shot/goal/
  save/foul/corner/turnover/substitution) au terrain via `note_event`.
- **Iter. 2 (retour utilisateur : decalage texte/2D, buts invisibles, boutons)** :
  - VERROUS d'evenement hierarchises `_ball_lock_until` (but 2.2 s > tir 1.4 s >
    arrêt 1.0 s > corner 0.9 s > reprise 0.6 s > passe 0.45 s) : le tick suivant
    n'ecrase plus la cible du ballon posee par l'evenement — le texte et le 2D
    racontent la même histoire.
  - BUT visible franchement : flash fort + 3 ondes concentriques au point de but
    + libelle « BUT ! » + NOM du buteur (detail passe au banner), et
    **celebration** : le cinq qui marque accourse au coin de la zone adverse
    pendant la duree du flash (cibles protegees du re-aim : `_celebrate`).
  - Chip d'action du terrain enrichi du detail (passeur→recepteur…).
  - deplacement reduit (push 0.065 att / 0.035 def, sway 0.045) : plus de
    chevauchement au rond central.
- **Iter. 3 (retour utilisateur : trop statique, boutons + immersifs)** :
  - MOUVEMENT CONTINU a 33 fps (_step refondu) : vitesse de course plafonnee
    (MAX_STEP 0.010/frame, BALL_STEP 0.034) — plus de teleports, des courses
    visibles ; wander sinusoidal perpetuel (WANDER_A 0.014) : jamais statique.
  - PHASES DE JEU : ballon colle au porteur hors verrou ; le defenseur adverse
    le plus proche PRESSE le ballon en continu ; repli defensif proportionnel
    a la profondeur du ballon ; courses de soutien de l'attaquant en largeur ;
    attirance douce des milieux vers le ballon.
  - `MatchPlayButton` : play/pause grand + code couleur AUTOMATIQUE sur le
    libelle (▶ vert = lancer/reprendre, II ambre = pause, sinon neutre) via
    setText surcharge — zero appel moteur modifie.
  - Segment de vitesse tactile 1x..5x (QToolButton checkables, slider garde
    cache pour compatibilite moteur : ralenti-but et restaurations intacts).
  - Titres de groupes accents (FLUX vert / VITESSE violet / COACH violet).
  - `tests/test_motion_step.py` (dans run_tests) : _step sans effectif OK,
    5/5 joueurs bougent, ballon colle au porteur, cap de vitesse, verrou tir,
    grab avec flash but.
- **Iter. 4 (retour utilisateur : camp statique, vitesse 1x, menus)** :
  - FLUIDE en propre camp : wander 0.014 -> 0.024 ; BLOC GLISSANT (chaque
    ligne suit lateralement le ballon : def y-lean 0.15, att 0.11) ;
    attirance en x elargie au champ complet (0.45 de portee, coef 0.05/0.07) ;
    montee/respiration du bloc en construction (sin 0.45 Hz, 0.03) ;
    poussée continue des attaquants (sin 0.5 Hz, 0.02).
  - Vitesse par defaut 1x (slider + segment + libelle "1x - LENT").
  - MENUS VERROUILLES pendant le direct : `_match_is_live` +
    `_set_career_nav_locked(True)` au lancement (sidebar, CONTINUER,
    JOUER LE MATCH desactives) ; `show_page` refuse tout autre onglet
    (retour force au centre de match + libelle "MENUS VERROUILLES") ;
    deverouillage a la finalisation du rapport + garde-fous (reset carriere).
  - Interface : chip pill pour la phase (AVANT-MATCH/EN DIRECT...),
    barre de possession live `PossessionBar` (deux couleurs club, % centre,
    maj a chaque minute) sous le titre du terrain.
  - Tests 3b etendus : verrou au lancement, show_page(0) refuse, deverrouille
    apres finalisation.
- **Iter. 5 (bugfixes retour utilisateur)** :
  - ARENA Infrastructure : proportions FIXES — la salle garde un ratio 8:5
    quel que soit l'ecran (plus de hall/tribunes etires sur grand ecran) ;
    terrain toujours 2:1 garanti (futsal_court_geometry) ; prouve sur grabs
    1900x600 et 700x800.
  - GESTION DES SAUVEGARDES : selection multiple (ExtendedSelection,
    Ctrl/Maj+clic) ; bouton SUPPRIMER affiche le nombre ("SUPPRIMER  N
    SAUVEGARDES") ; suppression grouped en double-clic de confirmation ;
    la partie ACTIVE reste protegee (exclue de la selection suppressible).
  - `tests/test_infra_save_ui.py` (dans run_tests) : arena sans distorsion,
    suppression multi-sauvegardes via dialog (2 ZZTEST creees puis supprimees,
    nie toucher aux fichiers utilisateur).
- **Panneau « CONDUITE DU MATCH » unique** (remplace les 2 barres) : 3 groupes
  titres — FLUX DU MATCH (valider cinq, reprendre/pause/reprise 2e MT, +20 s,
  finir, rapport) | VITESSE (slider 1x-5x + libelle) | COACH (consigne, appliquer,
  remplacement, statut) — separe par traits verticaux.
- Page Match Day remise : fixture en tete, bandeau, **terrain + colonne droite**
  (onglets FIL DU MATCH / EQUIPES + stats). _pitch_sync = 1 hook,
  no-op en fast-forward, try/except log_error.
- GARANTIE testee (`test_match_pitch2d.py`, dans run_tests) : le MEME match
  (DB copiee bit-a-bit, meme seed) joue 2 fois SANS puis AVEC terrain ->
  digest de 22 cles de stats STRICTEMENT identique : le visuel ne touche rien.
  Et captures offscreen (tests\captures\matchday_2d_*.png).
- **RETOUR ARRIERE** : `code_backups\backup_20261024_100326_avant_matchday2d\`
  (app.py d'origine + RESTORER.txt : restaurer app.py + supprimer
  match_pitch2d.py ; UI/RM et moteur sont utres autresposts).
- Pieges connus : offscreen rend sans polices (carres normaux) et l'ecran
  offscreen virtuel = 800x800 —tester les pages via
  app_stack.setCurrentWidget(game_shell)+resize (entrées carriere reelle),
  sinon la page reste a 362x591 (game_shell jamais etires).
- Attention: `Pitch2DWidget.paintEvent` a un catch-тout trace stderr TEMPORAIRE
  toujours actif (viser a le garder : tres utile).

## Purge finale arborescence (2026-10-24)
- **151,7 Mo supprimés** : `dist\` (120 Mo, exé compilé obsolète), `installer\` (35 Mo, Setup obsolète), `__pycache__`,
  `tests\archive\` (zips du 10-16), 10 anciens `code_backups\backup_2026*` (le plus récent conservé :
  `backup_20261024_094556_known_good_startup`), `data\fault.log`, `data\ui_trace.log` (recréés à la demande).
- **Aides compilation supprimées aussi (choix utilisateur)** : `FM2027V2.spec`, `FM2027V2_setup.iss`,
  `build_icon.ico` — à recréer le jour d'une recompilation demandée.
- Dossier = **3,0 Mo** : moteur (`app.py`, `main.py`, `ui_components.py`, `db.py`, `model.py`, `theme.py`,
  `logo_data.py`, `league_table.py`, `calendar_service.py`, `legacy_import.py`), `LANCER.bat`, `data\`
  (sauvegarde active `arbot_futsal_*.db` non touchée, `error.log` 0 o, `game_options.json`, `logo2.png`),
  `tests\` (outillage), `README.md`, `requirements.txt`, `ETAT.md`.
- Note test : l'univers généré est aléatoire (noms/contrats) → `test_messagerie` force des noms de joueurs uniques
  (Bruno/Calixte) pour neutraliser le dédoublonnage par nom du brief.

## Fichiers clés
- `C:\FM2027V2\app.py` moteur complet · `ui_components.py` widgets · `logo_data.py` logo embarqué
- `data\logo2.png` = logo officiel fourni par l'utilisateur (source : Desktop\IMGFUTSAL\logo2.png)
- Sauvegarde active de l'utilisateur : `data\saves\arbot_futsal_*.db` (NE JAMAIS toucher ; `active_save.txt` y pointe).

## Lot << 6 demandes utilisateur >> (2026-10-24)
1. **TRICHE dans Options** : panneau dedie dans GameOptionsDialog (`cheat_cb`
   passe par `open_game_options`) : +50 000 EUR / +250 000 EUR / +1 000 000 EUR,
   CONDITION 100 %, MORAL MAXIMUM. `MainWindow.apply_cheat` agit immediatement
   sur la carriere ouverte (trace comptable "Coup de main du board (triche)"
   pour l'argent) - volontaire, sans sanction du board.
2. **Difficulte a la creation** : choix FACILE / NORMAL / DIFFICILE dans le
   ClubSetupDialog (carte descriptive + recapitulatif budget estime). Effets
   moteur dans `seed_new_career_universe` via `DIFFICULTY_MODIFIERS` (constant
   a cote de LEAGUE_DEFINITIONS) : budget x1.25 / x1.0 / x0.72, reputation
   +10 / 0 / -8, infrastructure +/-1 etage, effectif +/-6 de niveau - SEUL le
   club 1 est colore, le monde adverse reste identique. `meta('difficulty')`
   enregistre + rapport de bienvenue mentionne le contexte.
   Signature etendue : `generate_player_roster(..., quality_delta)`.
3. **Messages medias** : `generate_media_messages(conn, date)` appele chaque
   jour dans la boucle calendrier : lundi = revue des resultats des autres
   (plus gros ecarts de la semaine), rumeurs de transfert 22 % des jours
   (marche cible : joueurs d'un club <= 2 ans de contrat, acheteur d'une
   division superieure ou egale... acheteur = club de reputation haute de
   division <= club d'origine), rumeur sur NOS stars 11 % des jours.
   Deterministe par date (rng graine "media-<date>"), dedoublonnage (date,
   body). kind='media' + filtre PRESSE ajoute dans la messagerie.
4. **Finances futsal** : panneau "CLUB FUTSAL - L'EQUILIBRE DU MOIS" dans la
   vue d'ensemble (4 KPI : paie du mois [Salaire+Staff], recettes, charges,
   solde du mois) calcules sur finance_tx du mois courant via
   `_refresh_futsal_finance_panel` (appele au refresh des finances).
5. **Direction sportive = dashboard** : bandeau d'accueil HeroPanel (ligne
   dynamique "a la une : <prochain match>" + 4 KPI + jauges climat 2x2),
   rangee ACCES RAPIDE = 6 tuiles colorees (Centre de match / Effectif /
   Transferts / Centre de formation / Finances / Messagerie). Les widgets de
   refresh (stat_*, *_gauge) gardent leurs noms : aucune regression.
6. **Centre de formation sobre** : hero compacte (jauge bleu acier #8fa8e8),
   barres de note harmonisees (2 teintes), campus reduit a 250 px, accents
   violet remplaces par bleu acier.
- **Test** : `tests/test_new_features.py` (9e suite de run_tests) :
  difficulte (budget/reputation/ecart effectif-monde, tirages random ALIGNE
  par random.seed avant chaque init_db), triche (budget+trace, condition,
  moral), medias (15 messages/60 j, re-generation dedoublonnee), pages
  refaites construites. ALL OK ; run_tests complet 9 suites ALL OK,
  error.log 0 octet.
- Pieges corriges a l'ecriture du generateur : Row sqlite : utiliser les
  ALIAS SQL (ag, mv) et pas les noms de colonnes ; l'univers est ALEATOIRE
  par init_db -> comparer deux carrieres exige un tirage random aligne.

## Lot << retours joueur #2 >> (2026-10-24)
1. **Vue INTERIEURE Infrastructure** : salle BEAUCOUP plus remplie
   (`scale = min(.92, .70 + (arena-1)*.028)` au lieu de .49+... ; cadre
   .96x.82w au lieu de .94x.84h) ; toutes les polices des libelles (nom club,
   TRIBUNES..., TERRAIN 40x20, ligue, chantier) plafonnees en pt
   (13/11/17/10/12) : plus de textes geants qui debordent ni de grand vide
   noir autour du hall. Captures `tests\captures\_lot8_infra_interieur.png`.
2. **Centre de formation conditionnel** : page MASQUEE tant que le campus n'est
   pas ouvert (meta `academy_unlocked` != 1) : hero, chips KPI, corps
   (campus/composantes) et promotions caches ; panneau verrou dedie
   (`academy_locked_panel` : cadenas + explication + bouton OUVRIR LE CENTRE =
   `invest_academy`). `_refresh_academy_page` bascule la visibilite a chaque
   refresh. Teste visible/masque dans test_new_features (section 5).
3. **Options en onglets** : GameOptionsDialog = 4 onglets APPARENCE /
   MESSAGERIE / TRICHE / AIDE (QTabWidget style CenterTabs), dialogue minimum
   680x470 : plus de page interminable. `values()` inchange.
4. **Finances** : MOUVEMENTS RÉCENTS + PAR CATÉGORIE remontes juste sous les
   KPI (stretch 1, "tables ennemi des graphiques") ; graphiques ensuite ; le
   recap `CLUB FUTSAL - équilibre du mois` RÉDUIT en bas (maxHeight 104, titre
   et hint supprimes, 4 KPI seuls). Capture `_lot8_finances.png`.
5. **Palmares du club** (dashboard) : entete avec medaille (icone cadree),
   sous-titre, gros compteur + mini-stats (n promos / n relegations en
   couleur), une LIGNE D'OR par titre triee du plus recent ("SAISON X -
   CHAMPION DE LIGUE Y" chip borde or), mentions de dynastie >= 3 titres.
6. **Entrainement recalibre (retour joueur)** :
   - fatigue par seance : Faible 1 / Normale 2 / Elevee 4 (au lieu de 1/3/5)
     => une semaine chargee ne vide plus la forme ;
   - progression : +1 par seance reussie (au lieu de +2, conforme au
     docstring "1 a 2 niveaux/20 par saison") ; player_training_log delta=1 ;
     plus de "+2" en 2-3 semaines.
- run_tests 9 suites ALL OK, error.log 0 octet. NOTE offscreen : captures avec
  carres = polices manquantes, normal.

## Iter 6 — lot retour joueur #3 (2026-10-24)
- **Effectif** : boutons d'action BRIEF/RÉCUP/KINÉ/TACTIQUES retirés de l'en-tête
  (widgets conservés créés MASQUÉS pour la compatibilité refresh/attributs) ;
  page = en-tête + filtres + KPI + table. roster_match_btn inchangé (matchday).
- **Vue EXTÉRIEURE refaite d'après modelext.png** (copie de référence dans
  `data/modelext.png`) : FacilityCampusView entièrement réécrite, VUE DE JOUR
  SEULEMENT — la vue nocturne est RETIRÉE (bouton NOCTURNE supprimé, toggle +
  refresh nocturne supprimés, set_night_mode = no-op). Composition : pelouse
  unie, hall central ardoise avec TERRAIN aux couleurs du club (buts, ronds,
  demi-lunes, médiane), 2 terrains pointillés, hall grossit avec arena_level,
  bâtiment d'entrée avec porche + marches, kiosques BAR/VIP/BOUTIQUE droits,
  PÔLE MÉDICAL (plot gauche) et FORMATION (plot droit) avec barrettes de
  niveau, terrain d'entraînement TRACÉ quand youth>=2, drapeaux marketing à
  gauche, projecteurs si lighting>=2 (skylights clairs si >=3), parking avec
  places/voitures + allée + voirie, rivière bord droit, arbres, contour
  chantier orange + grue + pastille. Captures : `tests/captures/ext_view_*.png`.
- **Historique des transferts** : chargement LAZY — refresh_transfer_history(force=False)
  hors onglet courant marque juste `_transfer_history_dirty` (0.1 ms) ; la
  reconstruction a lieu à l'ouverture de l'onglet (mercato_tabs.currentChanged
  -> _mercato_tab_changed) ou via le filtre. Nouveau filtre PÉRIODE :
  VOIR TOUT (défaut) / SAISON n (reconstruit dynamiquement). LIMIT 400->250,
  hauteur de ligne 40->36 fixée par defaultSectionSize. Reconstruction
  complète ~4 ms. Suite `test_transfer_history.py` (10e suite, ALL OK).
- Tests : 10 suites ALL OK (~26 s), error.log 0 octet. Artefact de greffe
  `_splice_campus.py` purgé.

## Iter 6b — retours vue exterieure #2 (2026-10-24)
- Etiquettes annexe non coupees : pastille arrondie sombre centree SOUS le
  batiment (elidee), barrette de niveau DANS le batiment ; PÔLE MÉDICAL et
  FORMATION propres a toute langue de fontes.
- REGLE "a batir" : marketing et formation n'apparaissent QUE a partir du
  niveau 2 — au niveau 1 (depart) les plots restent VIDES (composition
  modelext.png exacte) ; drapeaux = min(4, marketing) si >= 2.
- Le hall porte le NOM DE L'ARENE (club.arena_name, fallback SALLE
  PRINCIPALE) ; le nom du club reste dans le bandeau d'entete.
- Terrain d'entrainement trace compacte dans la moitie HAUTE du plot gauche
  (fini le chevauchement avec le bloc medical, label raccourci ENTRAINEMENT).
- Rayures de tonte sur la pelouse ; caption parking raccourcie
  (VÉHICULES au lieu de VÉHICULES LE JOUR DE MATCH) et police plus petite.
- Captures par etapes de construction : `tests/captures/ext_etape0_depart.png`,
  `ext_etape1_medical.png`, `ext_etape2_formation.png`, `ext_etape3_complet.png`
  (script rejouable `tests/_capture_ext.py` conserve).
- Tests : 10 suites ALL OK, error.log 0 octet.

## Iter 6c — retours vue exterieure #3 (2026-10-25)
- Infrastructure : marketing_level / youth_level au niveau 1 = NON CONSTRUIT
  — bouton CONSTRUIRE (au lieu d'AMÉLIORER), status « Construction : X € • n
  jours », pill « NIV. 0 / 8 » + barre de niveau VIDE ; les 4 autres infras
  gardent AMÉLIORER. Refait moi-meme (point 1 dejà en place via sous-agent
  interrompu, points suivants execute en direct).
- Vue extérieure : polices des bâtiments ENCORE réduites (pastilles annexes
  bhei*.16 min 4.2, chip_h *.20 ; kiosques *.22 min 4.2).
- Caption parking : « PARKING • {places} PLACES » (mention VÉHICULES retiree ;
  cars sert toujours au dessin des voitures).
- Polish rendu : vignette sombre sur les bords du site, liseré du court
  (ombre fine + blanc plus net), vaguelettes rivière décalées en 2 rangées,
  mats de drapeaux épais avec pommeau.
- Preuve UI : tests/captures/infra_a_batir.png + probe _probe_infra.py purgé
  (2 CONSTRUIRE / NIV. 0/8, 4 AMÉLIORER). Captures 4 étapes regénérées
  (ext_etape0..3) — pastilles plus petites, parking sans véhicules.
- Tests : 10 suites ALL OK, error.log 0 octet. Sous-agents externes
  (glm-5.3 interrompu, deepseek solde 0, gemini quota 0, step-5 resté en
  fond) : reprise manuelle complète.

## Iter 7 — Centre de formation sobre et clair (2026-10-25)
- Bandeau : titre « ÉTAT DU CENTRE DE FORMATION » (+72 px, jauge NOTE en
  violet), plus de slogan litteraire.
- Compteurs raccourcis : JEUNES FORMÉS / POTENTIEL 17-20 FORMÉS /
  INVESTI CETTE SAISON.
- Doublon INVESTIR supprime : le CTA unique vit dans « FAIRE PROGRESSER LE
  CENTRE » (academy_step_invest) ; academy_page_invest_btn/hint restent
  crees mais HIDDEN (le miroir refresh_academy_panel continue sans casser).
- Textes des leviers raccourcis (un etage = +8 pts, medical +1,5 pt/niveau,
  preparateur +8 a +15 pts, recruteur +6 pts) ; titre du panneau
  « FAIRE PROGRESSER LE CENTRE » ; promos « PROMOTIONS DU CENTRE • SUIVI
  DANS LA DUREE ».
- Tous les attributs refresh conserves (academy_bar_* / _val_*, steps,
  chips, next_line, tables) — refaite sans casses.
- Preuves : tests/captures/academy_fermee.png (panneau verrou seul) et
  academy_ouverte.png (bandeau + KPI + campus + note + leviers + promos).
- Tests : 10 suites ALL OK, error.log 0 octet.

## Iter 8 — Homogeneisation globale des pages (2026-10-25)
- Audit visuel 14/14 pages via tests/_capture_pages.py (captures offscreen
  1500x880 dans tests/captures/audit/) : le theme global est bien pose partout
  (les premieres captures « blanches » etaient un ARTEFACT DE SONDE : les
  probes ne font pas app_stack.setCurrentWidget(game_shell) ; corrige dans la
  sonde — QTabWidget jamais montre = geom. internes perimees au grab).
- Sous-titres de pages normalises « DOMAINE • courte finale », 100% FR,
  separateur « • » uniforme (plus de « / », d'anglais ou de slogans) :
  Recherche, Direction sportive, Effectif, Tactiques, Calendrier (titre
  « Match Center » renomme Calendrier pour aligner nav/titre), Classement,
  Entrainement, Centre de formation, Infrastructure (« ARENA MANAGEMENT »
  retire), Messagerie, Transferts, Finances. Staff/Matchday deja conformes.
- Aucun sous-titre n'est reecrit au runtime (page_subtitle jamais setText) :
  modifications statiques sans risque.
- Balayage doublons : pas de doublon d'action reel hors variantes de
  dialogues ; unique doublon INVESTIR deja supprime en iter 7.
- Captures/audit : page 05 Infrastructure verifiee apres correction sonde
  (onglets VUE D'ENSEMBLE / GESTION / EXPLOITATION + vue interieure ok).
- Tests : 10 suites ALL OK, error.log 0 octet.
- _capture_pages.py CONSERVE volontairement (sas audit rejouable) ;
  _probe_facility(.py/_dbg.py) purges.

## Correctif urgent — NameError 'to_build' au refresh infrastructure (2026-10-25)
- Symptome remonte en jeu : toast « ERREUR UI : Une erreur est survenue
  pendant l'actualisation : name 'to_build' is not defined » (ecran d'accueil,
  carriere Ligue 6 J-1).
- Cause : `_add_facility_investment_card` (app.py ~L15373) utilisait la
  variable locale `to_build` du BOUCLE appelante (refresh_facility_page,
  ~L15200) — restant du refactor iter 6c. NameError a chaque refresh des
  cartes.Infrastructure.
- Fix : parametre explicite `to_build=False` dans la signature + passage
  `to_build=to_build` depuis la boucle upgrades (~L15211). Semantique
  conservee : pilule « A BATIR » + barre vide pour marketing/jeunes niv.1 ;
  les cartes services/divers passent to_build=False (parylle OUVERT/A BATIR
  inchangee).
- Regression verifiee : probe refresh_all (carriere neuve) → 0 exception,
  error.log 0 octet ; pilules batiments = 4 « NIV. 1/8 » + 2 exactement
  « A BATIR » ; niveaux forces 2 → « NIV. 2/8 » partout ; onglet GESTION ok.
- Tests : 10 suites ALL OK, error.log 0 octet.
- DECISION utilisateur : STOP des sous-agents (aucun nouveau lancement ;
  la relique d'arriere-plan du pas-avant est abandonnee — son travail non
  rendu ne sera PAS fusionne ; reprise manuelle uniquement).
- Probes purges : _probe_tobuild.py, _probe_errlog.py.

## Iter 9 — Tresorerie du dashboard + refonte Entrainement (2026-10-25)
- BUG Direction sportive : sous-titre « Flux recents » de la carte Budget
  (refresh ~L11293) en montants bruts -> >1 M€ repliait sur plusieurs lignes
  devant la carte a hauteur fixe. Fix double : (1) montants compacts
  « +1,76 M€ / -980 k€ » (helper _flux_eur inline, la precision reste sur
  Finances) ; (2) carte Budget elargie (stretch 2 de la bandeau hero,
  L5386). Verifie probe : budget 1 350 000 € affiche point, pas de
  debordement (label <= 48 car.), capture tests/captures/audit/
  dashboard_budget_1m.png.
- BUG transversal : _facility_kpi_chip en QSizePolicy.Ignored -> les chips
  (infra strip, progression entrainement) s'ecrasaient a 0 px de large.
  Fix : MinimumExpanding + min 96 / max 168 px.
- BUG mise en page : fit_training_layout plafonnait le panneau PLAN a
  viewport-28 -> colonne lumineuse vs panneau PROGRESSION (mode grande
  largeur). Plafonne desormais a la largeur reelle du viewport.
- REFONTE Entrainement (attributs refresh conserves) :
  * Clic sur un atelier = posed sur le PROCHAIN jour libre (alternative
    drag&drop) — _training_quick_fill.
  * Double-clic sur un jour = le vide ; status « Jour vide... ».
  * En-tete du panneau PLAN renomme ; « GLISSER OU CLIC → » ; feedback
    raccourci en une ligne.
  * Panneau progression : titre « PROGRESSION DES JOUEURS • 30 DERNIERS
    JOURS », hint « +1 point par attribut • plafonne au potentiel » ; les 3
    compteurs passent INTLIGNE a droite de l'en-tete (1 ligne verticale
    gagnee).
- Captures : tests/captures/audit/page_04_training.png (largeur reelle du
  viewport), dashboard_budget_1m.png.
- Tests : 10 suites ALL OK, error.log 0 octet. Probes purges :
  _probe_train, _probe_chips, _probe_width.


## Iter 10 (25/10/2026) — Endurance recalibree + steppers + chantiers simultanes
- ENDURANCE (retour « la condition fond tres vite ») : le vrai coupable etait le moteur match
  (apply_fatigue_and_rotation appele ~39x/rencontre, perte ~45-65 de condition/match). Recalibrage tri-palier :
  1) moteur match : perte/minute 0.6-1.6 -> 0.15-0.45 (x tempo, +0.10 pressing-haut, +0.12/+0.04 pressing) ;
     adversaire idem (0.45-1.25 -> 0.15-0.45, pressing adverse 0.35/0.12 -> 0.12/0.04).
     Resultat mesure : rentrée complete neutre 13,7 (ex ~49) / tout-effort 23,4.
  2) reglement IA (_simulate_other_fixtures) : base 5-10 -> 3-6, pressing 1.35 -> 1.25 ; banc IA +3
     (miroir du +4 du club 1, titulaires exclus via ...) ; rechargé quotidien +1 -> +2.
  Perte neutral = %s
- STEPPERS +/- LISIBLES : QSS global QSpinBox — boutons 30 px fond #1f2b3a (hover #2c3d52, presse #6b5ab5),
  padding a droite 58 px, min-height 34 ; fleches = PNG triangles genérés par l'app dans data/icons/spin_up|down.png
  (les triangles CSS ne rendent pas dans Qt) ; fallback natif si PNG impossible. Preuve : tests/captures/audit/stepper_pro.png.
- CHANTIERS SIMULTANES (nouvelle architecture) : slots = 1 + arena_level//2 (arene niv 2 -> 2 chantiers,
  niv 4 -> 3, niv 8 -> 5). facility_project_capacity() ; start_facility_project : refus cle en doublon (même
  batiment) + refusal « Places de chantier saturees (n/slots) » ; refresh_facility_panel fetch TOUS les actifs,
  statut par cle (En cours J-x par batiment, OCCUPE seulement si 0 place libre), bandeau « TRAVAUX x3/3 »,
  vue interieure prefer le chantier arena_level ; hint « Un chantier par batiment + +1 place tous les 2 niveaux de tribunes ».
- Sonde _probe_mpsim : toute validee (3 chantiers, 4e et doublon refusés, livraison x3, fatigue) — purgeb.
- Tests : 10 suites ALL OK, error.log 0 octet. ETAT.md appendé par script, UTF-8.


## Iter 11 (26/10/2026) — Pipeline transferts : lisibilite des contre-propositions + arrivee differée
- CONTRE-PROPOSITIONS (retour « on ne voit pas le salaire demandé et ça atteint des grosses sommes ») :
  1) counter_terms_dialog : param info qui affiche EN CLAIR l'exigence (SALAIRE RÉCLAMÉ PAR LE JOUEUR : X €/mois,
     PRIX DEMANDÉ PAR LE CLUB : X €, ta dernière proposition, moyens de l'acheteur) sur les 4 variantes
     (agent, joueur, indemnité club, vente).
  2) player_salary_demand : PLAFONDS de la taxe « surqualification » (ecart capé à 3 niveaux) et du déficit de
     réputation (cap 40 pts) — multiplicateur max ~1,58x la base (avant : jusqu'à ~2,5x pour une star en Ligue 6).
- JOUEUR LISTÉ = PRIX DEMANDÉ : bid >= ask d'un joueur transfer_listed accepte la vente ENTIÈRE en un seul tour
  (indemnité + contrat planché sur le salaire actuel), PAS de négociation salariale supplémentaire. Les joueurs
  non listés gardent les tours (indemnité puis le joueur négocie son salaire).
- ARRIVÉE DIFFÉRÉE : à la validation (ACCEPTER), l'indémnité est débitée et finance_tx posée, mais le joueur
  rejoint l'effectif 2-3 jours plus tard (le joueur « n'arrive pas du jour au lendemain »). Nouveau kind
  transfer_arrival (waiting → ready au jour J : maillot, contrat, historique, prepaid discard ; remboursement
  intégral si le joueur a disparu de la base). Le mercato bloque une 2e offre tant que l'arrivée est en attente.
- SUPPRESSION PROTECTRICE : delete_all_messages ne détruit plus les dossiers status='waiting' (réponses du club/
  agent/arrivée) — le retour « supprimé = plus d'offre/contre-offre » est corrigé ; message annonce le nombre de
  dossiers conservés. Icônes/labels/couleurs transfer_arrival ajoutés dans les 3 vues messagerie + catégorie DOSSIERS.
- Sonde _probe_transfer : chaîne complète validée (A plafonds, B listé direct, C jour d'arrivée, D vs non-listé
  3 tours + arrivée, E suppression protectrice) — purgée. Tests : 10 suites ALL OK, error.log 0 octet, ETAT.md UTF-8.

## Iter 12 (retouches UI transversales — demande utilisateur du 20/02)

### Effectif
- Tableau AFFINE : 21 colonnes (suppr. NAT., POTENTIELcol, ARRÊTS, ENCAISSÉS ; breve J/S) ; JOUEUR en stretch reprend la largeur -> les noms redeviennent lisibles (bug : les colonnes fixes mangeaient tout).
- Colonne ETAT = POINT DE COULEUR : vert OK / orange fatigue (<60) / rouge indisponible (blesse ou suspendu) ; violet si le joueur est sur la liste des transferts. Details (forme, duree, cartons) en tooltip.
- NIVEAU/POTENTIEL fusionnes (potentiel en tooltip), MORAL "x/20" colore, largeurs fixes serrees (somme ~876px + stretch).

### Infrastructure
-FacilityArenaView / FacilityCampusView : minimumHeight 300 / maximumHeight 520 (avant 340+Expanding debordant la page, salle enorme). Plus de debordement ni de scroll force a 1500x880 ; le vide bas est du fond de page.
- Salle et exterieur a echelle contenue ; l'exterieur modelext.png inchange (jour).

### Centre de formation (epure)
- Bande de 3 compteurs (academy_chips) MASQUEE en permanence (widgets gardes, refs saines) ; retiree du tuple de visibilite du refresh.
- Panneau "COMPOSITION DE LA NOTE" masque (academy_comp_panel, widgets conserves). A la place : UNE ligne formule dans le panneau des leviers (academy_note_formula) : "NOTE x/100 = centre +x . medical +x . prepa +x . recruteur +6".
- Remplit "CENTRE FERME : aucune promotion..." si campus construit.

### Page de demarrage
- NOUVEAU bouton OPTIONS (open_start_options) : GameOptionsDialog des l'ecran d'accueil (theme, taille texte, mode fenetre, messagerie) ; applique immediatement (setFont/stylesheet/fenetre) + refresh_save_catalog SANS refresh_all (pas de carrière chargée).
- Layout homogene, 2 boutons par rangee : [REPRENDRE|NOUVELLE CARRIÉRE] 88px (gradients), [CHARGER|SAUVEGARDES] 70px, [OPTIONS|CRÉDITS] 70px, QUITTER bandeau plein largeur 54px.

### Tactiques (clarte)
- "⚙ FINS +" -> "⚙ RÉGLAGES AVANCÉS  +" (min-height 28, tooltip).
- Infobulles explicatives sur les 9 combos (formation, mentality, tempo, press_intensity, block_height, attack_width, attack_focus, rotation_style, goalkeeper_distribution) + sur les 5 boutons de presets (preset_tips, cles equilibre/possession/contre/pressing/powerplay).

### Staff (couts trompeurs)
- Carte staff engage : affiche "Formation niv. N+1 : X EUR" (STAFF_FORMATION_COST, 2600-5800) + salaire au lieu de re-montrer le prix d'embauche deja paye. "Niveau max ~" + salaire si niv.5.

### Verifications
- py_compile OK ; 10 suites ALL OK ; error.log 0 octet ; _capture_pages ALL OK (page_01 noms visibles + dots, page_05 salle contenue, page_13 epuree, page_10 staff) ; sonde _probe_fac_h purgee.

## Iter 13 (moteur 2D + retouches match/messagerie — retour utilisateur)

### Terrain 2D (match_pitch2d.py, mouchard)
- ANCIEN MATCH au lancement : reset_teams() des start_match (avant le dialogue
  avant-match) — le pitch ne montre plus le match precedent pendant la prep.
- CONVENTION « h = CLUB DU JOUEUR » corrigee COTE APPELANT (app.py) : banner,
  match_pitch et poss_bar recoivent noms/couleurs du JOUEUR d'abord. Avant, a
  l'exterieur, les pions du club etaient peints aux couleurs de l'adversaire :
  carton rouge / remplacements semblaient toucher les deux equipes.
  set_clock passe egalement le score oriente coach (user — opp), et
  _update_live_match_widgets fournit les noms dans le meme sens.
- DOUBLE MASQUAGE EXCLUSION supprime : le moteur retire deja l'expulse de son
  lineup ; l'ancien calcul _sent_off_slot re-masquait un second slot (index
  d'avant-pop, decorre de l'ordre gardien-d'abord) -> une equipe passait a
  3 pions visibles. Sonde : rouge cote h -> h=4, a=5 (exact).
- MOUVEMENT AMPLIFIE : shift possession 0.065/0.035 -> 0.115/0.065, appel
  profond +0.55*deep_atk, largeur d'une course 0.10 -> 0.17, bloc glissant
  0.11-0.15 -> 0.17-0.22 (+0.5 rayon de suivi horizontal), repli 0.09 -> 0.13,
  wander 0.024 -> 0.030, MAX_STEP 0.010 -> 0.012. Sonde : deviation attaquants
  0.30-0.34 depuis le slot (avant ~0.12), defenseurs ~0.10.
- LIBELLE « BUT ! » borne au terrain + elichte (avant : partait hors zone).

### Popup BUT (app.py)
- goal_overlay : largeur MESUREE (QFontMetrics pixel 30) + clamp sur la page
  (+72 padding), never setFixedSize(720,150) ; setWordWrap(True) + min 420.
  Plus de texte qui depasse sur les longs noms club+buteur.

### Messagerie « Tournée des vestiaires »
- Coherence rechargee : vainqueur/perdant calcules du SCORE reel (avant : la
  ligne « a encaisse sans reagir » designait l'equipe qui MARQUAIT 5 buts) ;
  « choc serre » desormais |diff|<=1 ; phrase de chute variece.

### Ecrans
- BADGES : monogramme releve (centre optique 45% au lieu de 50% dans
  draw_badge ; drawText preview ui_components cy-0.23*s) — lettres bien dans
  les ecussons partout.
- SIDEBAR COMPLÈTE : minimumWidth 236 -> 306 (max 342), icônes 36 -> 32,
  font 10.5 -> 9.5pt, paddings serres — « Centre de formation » entier
  (228px <= 231 dispo). Captures window_sidebar.png / window_badges.png.

### Verifications
- py_compile OK ; 10 suites ALL OK (determinisme match OFF/ON strict conservé) ;
  error.log 0 octet ; sondes _probe_pitch2d / _probe_sidebar / _probe_navwidth purgees.

## Iter 14 (mi-temps 2D + équilibrage niveaux + retouches UI — retour utilisateur)

### Terrain 2D : CHANGEMENT DE COTES a la mi-temps
- _second_half = elapsed >= 1200 (note_state) ; reset a prematch.
- _side_attacks_right pivote : h attaque a droite en 1RE, a GAUCHE en 2E ;
  buts, corners et celebrations suivent automatiquement le pivot.
- _integrate_lineups : les slots PIVOTENT (h a droite, a a gauche en 2E).
- _paint_power_play : la moitie orange suit la moitie d'attaque reelle.

### Popup BUT : nom du joueur sur SA LIGNE (\n), largeur mesuree sur la
  ligne la plus longue, wrap actif.

### EQUILIBRAGE : l'ecart de niveau redevient dominant
- Analyse : le profil match_team_profile calcule attaque/defense comme moyennes
  d'attributs 0-100 ; l'ecart (attaque adv - defense) entrait dans
  attack_qualityscaled x0.0012, puis x0.40 : un ecart de 45 points ne pesait
  que ~+0.022 sur la probabilite de tir (17% -> 18.4%) — les reglages
  tactiques (+/-0.045) pesaient PLUS que la qualite sportive.
- CORRECTIFS simulate_event :
  * boost concave _gap_boost : au-dela de 15 pts d'ecart, +0.0022/pt jusqu'a
    +0.055 (40 pts) sur l'attaque ; symetrique pour l'adversaire.
  * possession_edge x0.002 -> x0.003 (maitrise du ballon plus liee a la passe).
  * shot_probability bornes [0.12;0.43] -> [0.10;0.52].
  * conversion : pente finishing-keeper 0.0015 -> 0.0022, attack_quality
    x0.24 -> x0.30, bornes [0.15;0.50] -> [0.13;0.58] — les gardiens faibles
    encaissent nettement davantage contre un attaquant solide.
  Effet : une enorme equipe domine enfin une petite (la superiorite sportive
  > la tactique) ; le sens est symetrique (un club faible subit aussi).
  Determinisme match OFF/ON conserve (10 suites ALL OK).

### UI
- SIDEBAR : le duo puce+libelle est CENTRE dans le rail (stretch de part et
  d'autre, bouton collet).
- PAGE DE DEMARRAGE : REPRENDre (96px) puis NOUVELLE CARRIÈRE (88px) en
  pleine largeur sur deux lignes distinctes (retour du "gros bouton").
- EFFECTIF : avatars 40 -> 26px, lignes 52 -> 42px, POINT D'ÉTAT 11 -> 16 pt
  gras (bien visible), colonne JOUEUR moins encombrante par les têtes.
- CLASSEMENT : lignes 72 -> 56px (compact 52 -> 40), crest 44 -> 32x34,
  rang 38 -> 28x34, points 15 -> 13.5pt — les 10 lignes + legende tiennent
  dans la page (preuve page_11_standings.png, plus de 10e ligne rognee).

### Verifications
- py_compile OK ; 10 suites ALL OK ; error.log 0 octet.


---

## ITER 16 — Menus options « jolis » + RAM tenue en DB (2026-10-25)

### A. Menus options relookés (retour « rendre plus joli les menus options »)
- **Menu carrière (`open_game_menu`, app.py ~L5170)** : coque refondue — héro avec pastille 💾
  (44 px, biseau 13 px), titre 15 pt letter-spacing, sous-titre club • date, bouton × stylé.
  Corps en **cartes de groupe** (QFrame#MenuCard, coins 14 px) : « PARTIE • SAUVEGARDE »,
  « RÉGLAGES • SESSION », « SORTIR DE LA SESSION ». Boutons pleine largeur en dégradé
  sombre (hover #203052, pressed #101a2c), CONTINUER en dégradé vert néon 48 px,
  ENREGISTRER / ENREGISTRER SOUS… côte à côte, OPTIONS pleine largeur,
  MENU PRINCIPAL + QUITTER (déclinaison rouge) côte à côte. Ligne d'info conservée.
- **Options du jeu (`GameOptionsDialog`, ui_components.py)** : héro avec pastille ⚙ 44 px,
  titre 15 pt, étiquettes de champs en petites capitales 8.5 pt (#8fa2c0),
  combo/spinbox à 34 px de haut, colonne étirée, bas de page : ANNULER fantôme
  (130 px) + ENREGISTRER LES OPTIONS (230 px, Primary) à 42 px.

### B. Historique en DB plutôt qu'en RAM (retour « montée RAM pendant la saison »)
- **Diagnostic** : la RAM grimpait car le jeu rechargait des tables entières dans des listes
  Python à CHAQUE tour : `SELECT * FROM manager_message` (tous les messages historiques),
  `SELECT * FROM match_record` (tous les rapports, textes lourds) et régénérait les
  QPixmap de blasons/avatars des dizaines de fois par refresh.
- **Nouvelle table `manager_message_archive`** (init_db + schema) : id, kind, title, body,
  created_date, due_date, status, action_data, is_read, archived_date.
- **Balayage `archive_old_history(conn, date)`** (app.py, avant init_db) : à CHAQUE avance
  de jour (hook dans advance_calendar_days avant commit), les messages **lus et résolus**
  plus vieux que 21 jours migrent vers l'archive **par lots de 400** (jamais les status
  `waiting`/`ready` — protection offre en attente de l'iter 11 intacte). Enveloppe
  try/except : une sauvegarde ancienne sans la table archive ne bloque jamais la journée.
- **Lecture sur demande** : bouton **📖 HISTORIQUE** dans la barre de recherche de la
  messagerie → `open_message_archive()` : lecteur 640 px (héro 📖, compteur, liste des 200
  derniers messages archivés avec icône par type, corps tronqué à 150 car., date
  d'archivage). La partie vivante ne charge jamais l'archive autrement.
- **Charges bornées** :
  - cache messagerie `_manager_messages` : `ORDER BY id DESC LIMIT 400` (résolution,
    refus, suppression, coursier) au lieu de la table entière ;
  - `refresh_all` : `match_record` LIMIT 400 récents ; `own_matches` fenêtre des 400
    derniers matchs du club en sous-requête (DESC puis re-tri ASC → les records/
    séries de la page Palmarès restent chronologiques).
- **Antichambre QPixmap** (le vrai creur RAM de l'UI) :
  - `draw_badge` : cache `_badge_cache` clé (initiales, taille, couleurs, motif),
    purge à 600 entrées ;
  - `draw_player_avatar` : cache `_avatar_cache` clé (id joueur, taille, numéro, poste,
    couleurs club + kit, glyphe statut blessure/suspension) — le rendu est déplacé dans
    `_render_player_avatar` ; mêmes purges. Un QLabel ne régénère plus jamais un
    portrait identique.

### C. Vérifications iter 16
- py_compile app.py / ui_components.py / sim_career10.py OK.
- Suites run_tests.py : voir ligne RESULT de la course du jour (attendu ALL OK, 10 suites).
- Journal de contrôle RAM : `journal_career_membase.txt` (SCENARIO=membase, SIM_SEASONS=4,
  MEMPROBE=1, sonde IT%150 : RSS + gc + widgets + compteurs QPixmap).
- Bogue fixé en route : sous-requête own_matches sans `id` projeté → sqlite3.OperationalError
  « no such column: id » (2242 octets d'error.log sur la première course de tests).
- Fil pilote `tests/sim_career10.py` : MEMPROBE enrichi (QLabel/QPixmap/QListWidgetItem/
  QTableWidgetItem/QTimer… compteurs Qt par type via gc.get_objects()), intervalle 150 IT.

### D. Doctrine durée de vie / performance (à retenir)
1. Les tables journalières vivantes restent en RAM **bornées** (LIMIT) ; l'historique
   consultable vit en DB et se lit à la demande (fenêtre dédiée).
2. Tout pixmap décoratif est mis en cache clé-état, jamais re-rendu à l'identique.
3. Un refresh qui aspire une table entière = bug potentiel de RAM : borné par défaut.


### E. CORRECTIF STRUCTURAL ANTI-FUITE (suite iter 16, retour « ca grimpe toujours fort »)
La sonde enrichie a montré que memes après purges + charges bornées, QLabel s'entassait
(~++80/k quart de saison : 81 927 a IT 150 = fin de saison 1 partielle). La cause réelle :
refresh_all DESTRUIT/RECONSTRUIT les listes à setItemWidget (calendrier ~30 cartes,
classement ~20 cartes, stats) à CHAQUE avance de jour — et PySide6 ne libère pas les
widgets d'items au .clear() (l'event-loop du sim/saison poussa pas les deferred delete).
**Doctrine posee : REBUILD SUR VISIBILITE.**
- Les listes très chères ne se remplissent QUE si leur page est affichée :
  - `calendar_fixture_list` + `calendar_friendly_list` : gardes `isVisible()` sur les
    boucles de cartes (division et club) ;
  - `_fill_standalone_standings` / `_fill_stats_page` : retour immediate si invisible
    (stats_leaders est un DICT -> garde par hasattr(isVisible)) ;
  - show_page provoque déjà le remplissage a l'ouverture (singleShot) → rien ne manque
    à l'utilisateur (les KPIs et labels courts restent maj a chaque jour).
- `_flush_deleted_widgets()` (SendPostedEvents None/DeferredDelete) appelé EN FIN de
  refresh_all : les deleteLater des purges sont commis immédiatement, meme pendant un
  match/sim sans tour de boucle d'event.
- `_purge_list_item_widgets(list)` : detach + deleteLater de chaque widget d'item avant
  clear().
- Requete morte supprimee : `SELECT * FROM match_record` entier dans
  _fill_standalone_standings (borne a 400).
**Preuve (sonde, meme point IT 150)** : QLabel 81 927 -> 2 182, QFrame 10 896 -> 609,
QPushButton 6 714 -> 246, objets_py 209 895 -> 46 257. QPixmap/QTableWidgetItem/QWidget
plates dans les deux runs. La mesure RSS precise (psapi/K32) renvoie -1 dans le pilote
offscreen — l'implement grippe l'appel API Windows ; la pente d'objets Qt est le
critere decideur (et le jeu reel gère ses delete differes naturellement).
Bugs attrapes en route : stats_leaders etait un dict (AttributeError isVisible) —
avant tout test : garde en hasattr(isVisible). Course final : ALL OK 10 suites,
error.log 0 octet. Sonde courte SCENARIO=memchk (2 points max, doctrine : ne plus
mesurer loin, l'utilisateur teste via LANCER.bat).


---

## ITER 17 — Effectif (nom etroit + etoiles), DayPanel texte, topbar, moteur 2D tactique (2026-10-25)

### A. Page Effectif (retour « colonne nom toujours trop grand, manque etoile du niveau et potentiel »)
- **NIV passe en etoiles** (`stars5(level)`, largeur 44 -> 70 px, trie sur le niveau).
- **Nouvelle colonne POT en etoiles** juste apres NIV (largeur 70 px, trie sur le
  potentiel, couleur d'etage vert/jaune/gris comme NIV, tooltip « potentiel estime »).
- Toutes les colonnes droites sont RENUMEROTEES (MORAL 14 ... J/S 21) avec leurs
  couleurs/tooltip conservées ; les deux colonnes etoiles prennent ~128 px qui
  n'encombrent plus la colonne JOUEUR (8 pt gras, avatar 26 px).

### B. Topbar (retour « bouton option trop decale sur la droite »)
- Marge droite du header 16 -> 34 px : l'engrenage n'est plus arrache au bord.

### C. DayPanel (retour « plus sobre sans l'ecusson, juste texte, encore moins grand »)
- Ecusson du prochain adversaire SUPPRIME (`side_opponent_badge=None`, mises a jour
  setPixmap retirees des deux branches), puce J-N retiree : le decompte s'integre au
  texte (« J-3  ·  3 jour(s) avant le coup d'envoi », « ● LIVE », « ● AUJOURD'HUI »).
- Venue affiché AVANT la journee dans la ligne texte (« EXTÉRIEUR · J4
NomAdversaire »).
- Panneau 252-300 -> **198-232 px** ; titre 7.5 pt ; date 12 -> 10.5 pt ; adversaire
  10 -> 8.5 pt ; CONTINUER 38 -> 33 px ; JOUER LE MATCH 48 -> 42 px (font 9.5 pt,
  pulse tick syncronise 9.5 pt) ; paddings/marges reduits.

### D. Moteur 2D — TACTIQUE DANS LE MOUVEMENT (retour « plus fluide, plus de deplacement
en fonction de la tactique et des options de jeu »)
- **Photo tactique** `match_state["tactics_2d"]["h"/"a"]` au start_match : pressing
  (combo), mentalite, preset (equilibre/possession/contre/pressing/powerplay) du club
  du jour ; l'adversaire donne sont `style` et `pressing` depuis son
  `opponent_tactical_identity` (Bas 0 / Médian 1 / Haut 2).
- **`match_pitch2d.note_state`** : lit la photo dans `self._tactics` ; `reset_teams`
  remet a zero par match.
- **`_aim_slot`** — la hauteur du bloc suit les consignes : preset_gain
  possession 0.100 / powerplay 0.110 / pressing 0.085 / equilibre 0.065 / contre 0.040,
  multiplie par la mentalite (prudente x0.66 / equilibree x1.0 / offensive x1.28) ;
  pressing Haut garde le bloc haut SANS ballon (+0.040), Bas l'assoit (-0.020) ;
  **CORRECTIF DE SIGNE** : l'ancien shift etait toujours +x (l'equipe « a » poussait
  vers son PROPRE but !) — desormais le push va vers l'attaque de chaque cote.
- **`_step`** — pressing quantifie : Haut = **2 presseurs** en continue, Médian = 1,
  Bas = 0 jusqu'a ce que le ballon envahisse (deep>0.10) puis 2 — repli defensif
  module (0.17 haut / 0.13 médian / 0.085 bas) ; appels d'attaque amplifies selon la
  mentalite (+28 % offensive / -30 % prudente), profondeur 0.55 -> 0.60, largeur 0.17 -> 0.19.
- Mouchard toujours lecture-seule (aucune ecriture dans match_state).

### E. Verifications iter 17
- py_compile app.py + match_pitch2d.py + sim_career10.py OK.
- Suites : **ALL OK 10 suites**, error.log 0 octet.
- **SIM ELITE5 lancee** (SCENARIO=elite5, SIM_SEASONS=6 => 5 saisons jouees, mode
  joueur assidu : matchs + mercato a chaque session, l'objectif est la montee vers
  l'elite) avec **check memoire a CHAQUE cloture de saison** (`MEMPROBE FIN SAISON X`)
  + sonde IT 150 — juge la pente de RSS sur la duree (retour « verifie la montee en
  RAM entre les saisons et regarde pourquoi »).
- Doctrine : plus de mesure longue gratuite ; les checks saisonniers du pilote font
  foi a chaque iteration engine.


### F. ITER 17b — LA VRAIE FUITE RESIDUELLE : les boites modales recurrentes (2026-10-25)
Apres elite5 (5 saisons, L6->L4, 0 erreur), le check par saison montrait RSS
178->863 Mo (+~130 Mo/saison) — plus de fuite par les listes, mais ~950 widgets
vivants en PLUS chaque saison sous des parents persistes.

**Diagnostic par le census par parent (MEMPROBE enrichi : QApplication.allWidgets
+ compte par parent + top-levels par type)** :
- top-levels constants (15) : les QDialog ne s'entassent PAS comme fenetres ;
- `QFrame#MatchPlayerCard` 912 -> 1 356 (+444/saison) : les 14 cartes de notes
  du RAPPORT DE MATCH restaient VIVANTES en C++ apres fermeture du dialogue
  (wrapper Python ressuscite via parent/compos) — ~30 matchs x 14 cartes/saison ;
- QFrame#KPI / Panel / QDialog-children montent en surmesure : les memes dialogues
  de rapport/avant-match logent aussi des tuiles KPI et des metres.

**Correctif** : `_tr_after_modal(dialog)` — setParent(None) + deleteLater +
_flush_deleted_widgets() APPLIQUE aux dialogues recurrents :
- show_match_report (rapport complet, 14329) ;
- avant-coup d'envoi (13985) ;
- show_game_message (message de jeu standard, 3896).

**Preuve (1 saison, memdiag3)** : MatchPlayerCard = ZERO au census, RSS
109 -> 109 Mo **(+0 sur la saison)**, ALLW 2149 -> 1985, QLabel shells 787 -> 637.
La pente de RAM saisonniere est coupee a la source. Les tr fermes remontent
RSS aujourd'hui a ~109 Mo de base (avant : 178 -> 863 sur 5 saisons).

Sondefonctions : pixel exacte avec `_wt.HANDLE(h)` + argtypes (restype BOOL)
dans le pilote, rss_mb retourne enfin une valeur reelle ; MEMPROBE enrichi :
ALLW, TOP par type, census par parent (diagnostic poteau puissant,
a garder pour les iters a venir).


### G. ELITE5B — VERDICT RAM SUR 5 SAISONS (post correctif F) (2026-10-25)
Carriere assidue 5 saisons (SCENARIO=elite5b, SIM_SEASONS=6, checks MEMPROBE a
chaque cloture) :
- RSS a chaque fin de saison : 108 -> 115 -> 113 -> 114 -> 121 Mo — **courbe
  PLATE sur toutes les saisons** (les micros montees +5/+7 avant matchday
  sont transitoires et se retournent a la cloture suivante) ;
- contres preuves permanentes : QLabel 642 stable, QFrame 161, ALLW
  1 996-2 265, TOP-levels 15 ; ClubStandingRow ne s'entasse plus (en
  remontee de saison puis purge) ; QPixmap +15/saison seulement (nouvelles
  couleurs L5 en cache, purge a 600) ; msgs_cache 40 (borne) ;
- comparaison AVEC la fuite : l'elite5 d'origine atteignait 863 Mo a 5
  saisons (+130/saison) ; desormais ~121 Mo (+7 max sur tout le run) ;
- gameplay : montee L6 -> L5 (promotion s4, s5 : champion 'promotion'
  plafonne au stade L5), budget 197 530 E, effectif 13 joueurs moy. 9.7,
  centre de formation achete 50 000 E en s5, sponsors signes, 0 erreur
  moteur (error.log 0 octet). Le rythme de montee depend du budget du
  pilote (masse salariale caperee par division) — parametrage du pilot,
  pas une regression.
**Doctrine retained for the next iterations: every modal recurring box must call
_tr_after_modal() after exec()** ; descendants Qt (listes remplis par setItemWidget)
remain subject to rebuild-on-visibility + purge.

---

## ITER 18 - RETOURS UTILISATEUR : BUT 2D + JOUEURS VIVANTS + EFFECTIF
CONFIGURABLE + ENGRENAGE CENTRE + CAMPUS EPURE (annexe H)

Retours juges apres essai LANCER.bat des iters 16/17 ; aucune recompilation,
tests run_tests.py 10/10 ALL OK, sonde offscreen probe_iter18.py ALL OK,
error.log 0 octet.

### Popup but 2D - agrandie et sur deux lignes
- match_pitch2d.py::_paint_overlays : le libelle une ligne "BUT ! Nom" est
  remplace par un bloc deux lignes : LIGNE 1 = club du buteur pris dans
  _names[0/1] (pixel height /8.5, environ 2x plus gros qu'avant), LIGNE 2 =
  buteur (pixel height /13). Elidage propre sur chaque ligne (plus de nom
  coupe hors zone). La ligne buteur reste invisible si le detail est vide.

### Joueurs 2D encore trop statiques - amplification douce
- WANDER_A 0.030 -> 0.039 (+30 % de balancement naturel, les joueurs vivent
  meme sur leurs slots) ; MAX_STEP 0.012 -> 0.0135 (course ~3 s /
  demi-terrain) ;
- appels en largeur 0.035 -> 0.048 et freq 0.9 -> 0.95 ; construction en
  respiration 0.05 -> 0.068 ; bloc glissant lateral 0.17/0.22 -> 0.20/0.26,
  recentrage longitudinal 0.08/0.12 -> 0.09/0.13. Le correctif de signe de
  l'iter 17 est garde (l'equipe "a" attaque toujours vers x=0).

### Page de demarrage - boutons calibres
- QUITTER 54 -> 70 px : tous les boutons secondaires (CHARGER, SAUVEGARDES,
  OPTIONS, CREDITS, QUITTER) ont maintenant la MEME taille ; seuls
  REPRENDRE (94 px) et NOUVELLE CARRIERE restent du binome plus grand
  (choix volontaire).

### Engrenage top-right - icone vectorielle centree
- le glyphe CIRCONFLEGE de police a une metrique decalee : remplace par un
  pixmap dessine par QPainter (8 dents + anneau + trou central en
  CompositionMode_Clear) - mathematiquement centre. Nouvelle methode
  MainWindow._gear_icon_pixmap(size,color) ; bouton 38x38, icone 24x24,
  styles hover inchanges.

### Effectif - choix et deplacement des colonnes
- Bouton "COLONNES" dans l'entete de la table ; dialogue de 22 lignes :
  case a cocher = visibilite, fleches HAUT/BAS = ordre, REINITIALISER,
  FERMER.
- Persistance data/roster_columns.json : ordre visuel (sequence de colonnes
  logiques) + set des colonnes cachees ; chargement tolerant (filtre
  0..21, complete si ordre incomplet) ; save relit l'ordre REEL du header
  (logicalIndex par position visuelle) donc ce qui est affiche est sauve.
- CORRECTION GEOMETRIE (retour "colonne joueur cache NIV/POT") : JOUEUR
  n'est plus en Stretch permanent - elle passe en Fixed 246 px et la
  DERNIERE colonne VISIBLE absorbe le reste (setSectionResizeMode Stretch,
  re-applique a chaque changement du dialogue). Masquer/deplacer
  redistribue l'espace sans jamais ecraser la fin du tableau.
- BUG VU AUX TESTS : visualIndex appartient a QHeaderView, pas a
  QTableWidget (AttributeError dans _apply_roster_columns qui jetait
  error.log > 0 dans 5 suites) - corrige hc.visualIndex aux deux endroits
  (apply initiale + deplacement du dialogue).
- Le toggle visibilite du dialogue met a jour _roster_col_hidden AVANT
  apply (sinon l'apply re-montre la colonne masquee) ; le deplacement
  re-synchronise _roster_col_order depuis le header avant apply+save.
- Le remplissage par index logique et le tri par cellule restent
  inchanges : la configuration n'agit QUE sur la position visuelle et la
  visibilite.

### Centre de formation - un seul terrain + page epuree
- AcademyCampusView : les DEUX terrains d'entrainement (retour "pourquoi
  2 terrains ?") sont remplaces par UNE grande pelouse unique avec la
  promotion des jeunes (points = 3 + niveau du centre), legende "TERRAIN
  D'ENTRAINEMENT DES JEUNES" ; la legende du bas (BATIMENT / AILE
  MEDICALE / TERRAINS) est supprimee.
- Les deux lignes STAFF (preparateur / recruteur, jumelles) fusionnent en
  UNE ligne "Staff dedie : preparateur (+8/+15) et recruteur (+6)" -
  bouton STAFF vers la page Staff. academy_step_prep et
  academy_step_scout pointent le MEME bouton (refs conservees pour le
  refresh) ; le chip affiche FAIT / PARTIEL / A EMBAUCHER selon les deux
  embauches ; le refresh garde le bloc scout inactif quand il designe le
  meme bouton (garde `is`).
- Rappels d'epure iter 17g toujours actifs : bande de compteurs masquee,
  panneau COMPOSITION masque.

### Tests
- run_tests.py : 10/10 ALL OK (~26 s).
- Sonde probe_iter18.py : engrenage 24x24 non-null, 22 colonnes par defaut
 visibles, masquage des colonnes operationnel, JOUEUR Fixed, derniere
 visible Stretch, re-ordre (colonne 16 en tete) OK avec coherence
 visualIndex/logicalIndex, roundtrip json OK, campus peint, popup but
 peinte, error.log 0 octet.

---

## ITER 19 - BANNIERE + COLONNES REPARÉES + VITESSE + PHASES + ENTRAINEMENT (annexe I)

Retours joueurs apres essai iter 18 : run_tests 10/10 ALL OK, sonde
probe_iter19.py ALL OK (8 blocs), error.log 0 octet, aucune recompilation.

### EFFECTIF - LE vrai bug du dialogue COLONNES trouvé et tué
- NameError QCheckBox -- la classe n'etait PAS importée dans app.py : le
  dialogue mourait a la construction de la premiere ligne (le bouton
  sem ne faisait rien). Import ajouté.
- Deuxieme couche du même bug : chk.toggled connectait _vis(chk=chk,c=c) ;
  le signal passe l'etat bool en arg POSITIONNEL qui remplait chk ->
  crash a chaque case (caché par le try/except du dialogue). Fix :
  _vis(state, chk=chk, c=c).
- Regression verifiée en sonde : decocher POT masque la colonne 13
  (interaction réelle) + persiste dans roster_columns.json ; chemin réel
  json intact (le probe a dû relire app.ROSTER_COLS_FILE, pas TMP).

### VITESSE qui retombe a 1 toute seule - cause et fix
- Deux actions rapprochées (deux buts, but + relance) : le DEUXIEME
  _slow_for_goal re-captait la vitesse courante (deja ralentie a 1x)
  comme vitesse de conservation -> le ralenti resta figé en 1x. Fix :
  si un ralentissement EST en cours (timer actif + sauvegarde non nulle),
  on conserve la vitesse d'origine et on PROLONGE le ralenti.

### VRAIE PHASE DE JEU - plus de but surprise
- simulate_event : une possession doit CONSTRUIRE avant de frapper : au
  moins 2 passes nettes (1 seulement si le pressing haut fabrique
  l'occasion), excepté sur phase arretée (corner / coup franc / 10 m
  / penalti). Pendant la construction : ni tir, ni faute, ni temps mort
  (chance forcee a 1.0 -> branche passe). La marche
  passe-passe-passe-tir devient visible en 2D.
- Meme garde dans le chrono simplifié des autres matchs (min_build si
  pressing haut).
- centrale santee : _gap_boost ecart de niveau (iter precedente) conserve.

### MOTEUR 2D - fluide + conforme aux tactiques
- MAX_STEP 0.0135 -> 0.0150, BALL_STEP 0.034 -> 0.038.
- Slots élargis (retour « ecart entre joueurs ») : defenseurs (0.27 ,
  0.24/0.76), attaquants (0.52 , 0.30/0.70) — couloirs plus larges.
- TRANSITION BURST : chaque changement de possession lance 1,7 s de
  sprint pour les pressivés + attaquants en possession (x1.5 ; preset
  « contre » x1.65) — les contre-attaques se VOIENT.

### ENTRAINEMENT vide a la reprise - filet de sécurité
- Nouveau _autofill_missing_week() : si la semaine courante n'a AUCUNE
  seance planifiable et que le preparateur physique est engagé, le staff
  compose le plan equilibre (Technique/Defense/Tactique/Repos/Finition/
  Recuperation/Repos) pour les jours restants + applique la seance du
  jour. Idempotent (per-day exists check), appele depuis
  refresh_training_schedule quand planned==0 ; le plan manuel du coach
  n'est jamais écrasé.

### BANNIERE au-dessus de la barre de recherche
- Nouveau Label top_banner dans la sidebar, AVANT la barre de recherche ;
  _load_top_banner() cherche data/ban2.png puis ban2.png racine, charge
  avec ratio conserve (286 px de large) ; absent -> invisible ; re-check
  léger dans refresh_all (le fichier peut apparaitre en cours de partie).
- PROCÉDURE COACH : copier ban2.png dans C:FM2027V2data (a cote des
  sauvegardes) puis relancer — ou a la racine C:FM2027V2.

### OPTIONS améliorées
- Combo Relance gardien : ajout "Rapide" (le preset pressing haut la
  proposait SANS que l'option existe — bug préexistant fermé) + tooltip
  explicite.
- Boutons OPTIONS (écran d'accueil + menu carrière) : le glyphe monnaie
  de police (metrique decalée) est remplacé par l'icône RENDUE (pixmap
  8 dents) via setIcon ; le carré du topbar gagne aussi padding:0 pour
  centrer l'icône dans ses 38 px (le QSS global injectait un padding
  qui decalait l'engrenage).

### Tests
- run_tests.py 10/10 ALL OK (~26 s) ; sonde iter19 : banniere chargee,
  gear pixmap, dialogue colonnes (toggle rejoué en vraie interaction),
  vitesse double-action, plan auto 7 seances, slots 2D, gardes de phase.


---

## Annexe J — Iteration 20 (retours buts / medias / amicaux / Match Day)

### CALIBRATION BUTS (retour « 0-0 et 1-0 : ne pas empecher trop les buts »)
- Le garde de phase iter 19 (min_build 2, base .17, per_build .035, build +1)-
  etouffait la production : banc Markov 60 000 matchs -> 0.60 but/match en
  live (vs 1.43 baseline). Constat confirme par les matchs reels 0-0/1-0.
- CONFIG RETENUE (appliquee aux DEUX boucles, live simulate_event ET chrono
  _simulate_other_fixtures) : min_build 2 (2 passes) + build_step 2 (une
  passe = 2 crans de build) + base .21 + per_build .055.
- Thermometres : live ~1.29 but/match (~90 % de la baseline 1.43, banc),
  chrono ~3.90 (~91 % de la baseline 4.30). Le pressing haut garde son
  court-circuit (min_build 1) : presser est toujours rentable.

### POPUP BUT 2D CLIGNOTANTE (retour « couleur clignotant sur 2 lignes »)
- _paint_overlays : les DEUX lignes de la popup alternent blanc <> couleur
  du club a ~3 Hz pendant tout le flash (blink_on = int(now*3)%2), alpha
  fonde 200 -> 145 vers la fin. Ligne 1 « BUT ! + club », ligne 2 le nom du
  buteur. Purge au reset (voir Match Day) : _goal_info/_celebrate remis a
  None dans reset_teams.

### MESSAGERIE SANS PRESSE (retour « enlever les medias des messages »)
- Option MESSAGERIE « PRESSE ET RUMEURS » (media_gate_box) : OFF par DEFAUT
  dans GameOptionsDialog -> values()["msg_media"] -> data/game_options.json.
- generate_media_messages : court-circuit TOTAUX quand l'option est coupee
  (aucun nouveau message genere, determinisme preserve si ON).
- Affichage protege aux DEUX points de lecture : _refresh_messages_ui
  (requete WHERE kind<>'media') et refresh_manager_message_queue (filtre en
  memoire via _msg_kind tolérant Row/dict) via le helper unique
  _media_messages_hidden() = not msg_media. Les anciens messages presse deja
  en boite sont masques, et revenus si l'option est rallumée.

### AMICAUX : FILTRE PAR NIVEAU (retour « liste trop longue »)
- Nouveau combo friendly_filter_combo (9 options) : TOUTES, L1..L6,
  MA LIGUE +/- 1, NIVEAU PROCHE (reputation +/- 15).
- _fill_friendly_opponents() filtre en SQL, present par ligue puis
  reputation, label « nom - Lx - rep n » ; conserve la selection courante si
  elle survit au filtre ; refresh_all passe par ce helper (plus de
  remplissage brut alphabétique tronque a 100).

### MATCH DAY : FENETRE CLEAN (retour « l'ancien match encore affiche »)
- _reset_matchday_view() : match_state=None, timer stoppé, banniere stoppee
  + clear + cachee, terrain 2D reset_all (phase prematch, possession None,
  popup/celebration purgées), journal vide, score « 0 - 0 », chrono 00:00,
  barre de progression 0, phase AVANT-MATCH. Le rapport du dernier match
  reste consultable via son bouton (last_match_report conserve).
- Appel dans show_page(3) des qu'il n'y a PAS de match en direct : ouvrir le
  centre de match part toujours d'un ecran vierge.

### Tests & sonde
- test_new_features.py aligne sur le nouveau defaut : 3a) 0 message presse
  avec l'option coupee ; 3b) option ON -> presse generee + dedoublonnage.
- run_tests.py 10/10 ALL OK ; sonde probe_iter20.py 6 blocs ALL OK
  (constantes des 2 boucles + Markov dans les bandes, popup peinte 6 frames,
  medias OFF/ON + masquage queue, filtres L1 = 10 clubs div 1 et
  MA LIGUE +/-1 = 29 clubs div 2..4, reset Match Day complet, error.log 0o).


---

## Annexe K — Iteration 21 (centre des transferts / EN VUE / couleurs ext)

### VRAI CENTRE DES TRANSFERTS (retour « voir nos offres et les offres reçues »)
- Nouveau onglet « 🤝 OFFRES • ENVOYÉES & REÇUES » EN TETE du mercato
  (tabBar().moveTab → index 0). Deux tableaux :
  • NOS OFFRES ENVOYÉES (ACHATS) : status (EN ATTENTE / ACCEPTÉ•CONFIRMER /
    CONTRE-PROPOSITION / CLOS), joueur, club visé, montant (bid), salaire
    offert, durée, tour Rn, échec/date — alimenté depuis manager_message
    kinds market_offer / free_agent_contract / transfer_arrival ;
  • OFFRES REÇUES (VENTES) : offre (fee/counter_fee/limit), club acheteur,
    dossier — kinds transfer_sale / transfer_sale_counter.
- _refresh_offers_tab() : UN SELECT borne (LIMIT 300), doctrine memoire ;
  rebuild a l'ouverture de l'onglet (dirty sinon) via _mercato_tab_changed
  et refresh_market_only (rebuild immediat si l'onglet est a l'ecran).
- Double-clic sur une ligne : fiche du joueur (_open_offer_row_in_market).
- COMPTES D'INDEX decalles (+1) : history tab devient index 4, scouting 2,
  shortlist 3, MARCHÉ 1 — _mercato_tab_changed, open_shortlist_row,
  shortlist_batch_remove, open_scouting_row_in_market, message scouting.

### DIRECTION SPORTIVE : JOUEURS EN VUE (retours 3 en 1)
- DIVISION : la requete des meilleurs buteur/gardien lit la division
  ACTUELLE du club (club["division"]) — plus jamais la vue filtre du
  calendrier (le "gardien figée"), et suit automatiquement une promotion.
- NOM TOUJOURS VISIBLE : le voile « Non observé » est supprimé — le nom + club
  s'affichent ; seule la VALEUR reste cachee ("•••") tant que knowledge<50.
- JOUEURS CLIQUABLES : player_id pose en property sur valeur et nom
  (cursor main) ; eventFilter central (MouseButtonRelease) ouvre la fiche
  via open_player_profile.

### COULEURS EXTÉRIEUR (retour « moteur 2d inverse buteur/couleur, souvent à l'extérieur »)
- CAUSE : le moteur raconte le match en cotes REELLES (h = DOMICILE), le
  bandeau/le terrain 2D en cotes COACH (h = CLUB DU JOUEUR). À domicile les
  deux coïncident ; à l'extérieur les actions/buts/possessions ADVERSES
  s'affichaient au nom et aux couleurs du club du joueur.
- FIX : helper MainWindow._bside(side) (moteur -> coach) ; goal_flash et
  goal_celebration passes par le helper ; LiveMatchBanner apprend son cote
  coach (_engine_user_side, pose au coup d'envoi, reset a l'ouverture Match
  Day) et remappe TOUTE action dans animate_action (banner + relais note_event).
- Mutin 2D (note_state) : but (hg/ag montent), possession et compteurs de
  passes/players_on sont remappes abs-> coach (fonction locale _co), donc
  celebrations, flash et porteurs apparaissent sur le bon cing.
- Barre de possession : part lue en cotes coach (100-poss a l'extérieure).

### Tests & sonde
- test_transfer_history.py aligné (5 onglets, HISTORIQUE index 4).
- run_tests.py 10/10 ALL OK ; sonde probe_iter21.py 4 blocs ALL OK
  (onglet offres rempli, tuiles EN VUE testées COMPLETES avec clic,
  banner/mutin ext. vérifiés en cotes croisées, error.log 0o).


---

## Annexe L — Iteration 22 (chantiers : simple court / lourd long ; exploitation компакт)

### TEMPS DE CONSTRUCTION REÉALISTES (retour « réduire le simple, allonger le gros »)
- Aménagements SIMPLES raccourcis : parking 45→30 j (et +5 j/niveau au lieu
  de +7), marketing 55→40 j (+6/niv), bar 70→14 j, boutique 85→18 j,
  fan zone 55→24 j, VIP 130→60 j.
- Chantiers LOURDS (structurants) allongés : tribunes 160→210 j (+28/niv),
  centre de formation 90→120 j (+18/niv), pôle médical 70→90 j (+14/niv),
  éclairage 65→80 j (+12/niv), terrains locatifs 95→130 j,
  salle d'événements 115→170 j.
- Les DEUX sources de durée sont alignées (cartes de la GESTION ↔
  buy_facility_extra) — l'affichage du délai sur une carte est fidele au
  chantier réellement lancé. Coûts inchangés ; l'architecte s'applique
  toujours (rabais coût/délai).

### EXPLOITATION : page plus compacte (retour « enlever le scenario, réduire le graphique »)
- Bloc « SCÉNARIOS DE TARIF » (4 lignes TESTER + étiquettes) SUPPRIMÉ, ainsi
  que son remplissage dans update_ticket_forecast (ticket_scenario_labels
  retiré de partout).
- Courbe des prix (TicketDemandView) bornée : min 88 / max 140 px — la page
  ne déborde plus ; prévision d'affluence/recettes inchangée.

### Tests & sonde
- run_tests.py 10/10 ALL OK ; sonde probe_iter22.py 3 blocs ALL OK
  (durées simples/lourdes aux bornes, specs extras fideles, page sans
  scenarios + graphe compact + prévision vivante, error.log 0o).


---

## Annexe M — Iteration 23 (chantiers/staff/saison étalée/Coupe nationale)

### CHANTIERS : plus de places, +1 PAR NIVEAU D'ARCHITECTE
- facility_project_capacity : 1 place de base + le NIVEAU de l'architecte
  engage (0 → 1 chantier, niveau 3 → 4, niveau 5 → 6 simultanés). L'ancienne
  règle « +1 tous les 2 niveaux de tribunes » est retirée.
- Textes de la page (hint GESTION + feedbacks) alignés.
- GROS CHANTIERS RAFFINÉS (retour « réduire tout de même ») : tribunes
  210→175 j (+22/niv), formation 120→100 j (+15), médical 90→76 j (+12),
  éclairage 80→66 j (+10), terrains locatifs 130→110 j, salle d'événements
  170→140 j. Les aménagements simples restent courts (bar 14, boutique 18,
  VIP 60, fan zone 24, parking 30, marketing 40).

### STAFF : EFFETS RÉELS VÉRIFIÉS/BRANCHES (retour « vérifier l'utilité »)
- Recruteur (scout) : missions de scouting — déjà réel (gain/accr富士 au niveau).
- Kiné : protocole quotidien 2 100 € — déjà réel.
- Préparateur physique : plan d'entraînement auto + note du centre — réel.
- NOUVEAUX EFFETS pour les 4 staffs purement cosmétiques :
  • COMPTABLE : -12 % de la paie mensuelle du staff (process_staff_payroll) ;
  • ADJOINT : +3 points de condition RÉCUPÉRÉ en plus chaque jour (club 1) ;
  • RESPONSABLE MARKETING : +1 point de réputation chaque lundi (cap 100) ;
  • DIRECTEUR SPORTIF : chaque lundi, +8 de connaissance sur la cible de la
    shortlist la moins observée (_director_scout_bump, upsert scout_report).
- Cartes de la page Staff : descriptions « EFFET RÉEL » exactes.

### SAISON ÉTALÉE (retour « étaler les matchs + trêves + saison sept→mars »)
- NOËL : trêve 21/12→4/01 conservée ; ÉTÉ : trêve naturelle (journée 1
  ONLY premier samedi de septembre, rien en juillet-août).
- Rythme par tranches de calendrier : sept-oct +7 j, nov-déc +12 j,
  janv-avril +14 j → 18 journées finissent début mars (2026-09-05 →
  2027-03-02). Sauvegardes existantes : le nouveau rythme s'applique aux
  PROCHAINES saisons (fixtures déjà écrites préservées).

### COUPE NATIONALE (retour « coupe en confrontation directe, élimination,
tirage au sort entre TOUTES les équipes de TOUTES les divisions »)
- fixture_type='cup' ; matchday = 100+tour (jamais de collision avec les
  journées de championnat nor l'index unique).
- Tirage INITIAL (ensure_cup_fixtures) fait par saison : TOUS les clubs (6
  divisions, 60 adverses + le manager) mélangés AU SORT ; 30 confrontations
  directes + 1 exempté si effectif impair ; un match aller simple.
- AVANCEMENT (ensure_cup_progress, appelé chaque jour ET après un match du
  club) : quand un tour est entièrement joué, des VAINQUEURS avance le
  tableau ; nouveau tirage date d'un mercredi ~3 semaines après, trêve sautée
  ; l'égalité de confrontation IA se règle en simulation de séance de 10 m
  (poids réputation) gravée dans le fixture/répartement.
- MATCH DU CLUB : officielle mais HORS championnat : pas d'avancement de
  journée de carrière ni de classement ; match_record matchday=0 ; si score
  égal → 10 m au coup de sifflet, vainqueur gravé et « qualifications /
  élimination » en news. La FINALE publie le vainqueur national (une fois,
  meta cup_winner_season par saison) ; si c'est NOUUS ; « LA COUPE EST À
  NOUS ! ».
- ÉTIQUETTES : helper fixture_tag(matchday,type) — AMICAL / Jxx / COUPE Rn —
  branché sur cartes calend trái, refresh_all (matchday_meta_label,
  next_tag, nav MATCHDAY), news quotidiennes et libellé du match.
- La simulation des autres (match IA) lit désormais DU : le championnat de
  la journée ET les tours de coupe arrivés à échéance (fixture_date<=aujour
  d'hui), matchday=-1 pour les tours sans championnat.

### Maintenance
- Rattrapage d'un double encodage induit par une rériture PowerShell du
  fichier (transform inverse appliqué ; accents restitués) — le reste du
  fichier est inchangé fonctionnellement.
- run_tests.py 10/10 ALL OK ; sonde probe_iter23.py 6 blocs ALL OK
  (places architecte, comptable/adjoint/marketing/directeur, calendrier
  trêves + fin début mars, tirage coupe 30 confrontations + tour 2 15
  confrontations + vainqueur final publié, error.log 0o).


---

## Annexe N — Iteration 24 (affichage repair / page COMPÉTITIONS + onglet COUPE)

### AFFICHAGE RATTRAPÉ (retour « plein de bugs d'affichage »)
- Nettoyage COMPLET des caracteres cassee (U+FFFD + octets 0x80-0x9f orphelins,
  heres des réecritures PowerShell de l'iter 23) : 260 FFFD → 0. Trois passes :
  suppression des debris d'emoji (pres/suffixes de labels), reparation des
  mots accents par table exacte (élimination, journée, égalité, réputation,
  trêve, séance, échéance, comptable/adjoint/directeur, qualification aux 10 m,
  news de coupe...) puis idem sur les 2 residus.
- Au total : PLUS AUCUN caractere remplace dans app.py ; compile + tests 10/10.

### PAGE CLASSMENT → COMPÉTITIONS (retour « changer classement »)
- Titre de page + libellé de navigation Compétitions + bouton Tableeau de bord
  « COMPÉTITIONS -> ».
- Onglets : CHAMPIONNAT / COUPE / STATISTIQUES / HISTORIQUE (routing de
  _refresh_classement_tab décalé ; le championnat garde KPI/classes/formes).

### ONGLET COUPE (retour « il faut voir la coupe »)
- _cup_page + refresh_cup_page :
  • TOUS les tours de la coupe (fixture_type='cup') affichés : R1, R2… avec
    club/vainqueurs, scores ou « à jouer », date ; la ligne du CLUB DU JOUEUR
    s Januar en surbrillance ; bandeau d'etat (tirage à venir en fin saison /
    tableau omitted à élimination directe).
  • PALMARÈS : meta JSON 'cup_palmares' ({season, club, date}) écrite quand la
    finale housse — gravée saison après saison.
- Doctrine visibilité : remplissage a l'ouverture de l'onglet et quand la
  ligne est visible, jamais gratois (RAM bornée).
- Clic sur une confrontation : fiche du joueur le plus cher du club adverse.

### Tests & sonde
- run_tests.py 10/10 ALL OK ; sonde probe_iter24.py ALL OK (4 onglets
  attendus sans 'CLASSEMENT', onglet COUPE rempli du tirage 30 confrontations,
  meta palmares opérée par la finale, error.log 0o).


---

## Annexe O — Iteration 25 (icônes de menu restaurées / hamburger)

- INCIDENT : le fichier restaure de l'iter 24 avait gardé des glyphes VIDES
  dans la navigation latérale (les icônes enlevées en même temps que les
  débris de mojiibake) — un premier correctif mal cibré a écrasé la
  construction de la barre latérale, détecté immédiatement par relecture ;
  le fichier a été restauré depuis la copie app.pre-clean.py, les 3 passes
  de nettoyage rejouées (0 FFFD re-vérifié), puis les corrections réalisées
  avec des ancres précises uniquement.
- ICÔNES RESTAUÉES et bien CENTRÉES dans leur puce 32x32 (alignement
  central + padding/margin 0 + police 12.5pt) : Direction sportive = 📋,
  Entraînement = 🏃, Infrastructure = 🏟, Transferts = 🔁 (nav ET tuile
  rapide), Compétitions = 🏆 (+ onglets CHAMPIONNAT/COUPE ré iconName).
- ROUE CRANTÉE → 3 BARRES HORIZONTALES (_gear_icon_pixmap, même appel) :
  dessin QPainter, 3 barres équidistantes, centrage parfait par construction
  (aucune métrique de police) — utilisée par le topbar et les boutons
  OPTIONS de l'écran d'accueil et du menu (18/20/22/24 px).
- Icône recherche vidée remplacée par label invisible ( placeholder la
  marge gauche existante du champ).
- run_tests.py 10/10 ALL OK ; sondes iter23/24 re-passées ALL OK ;
  error.log 0 octet.


---


---

## Annexe P — Iteration 26 (cohérence visuelle / coupe refondue)

- Navigation et titres de pages audit́s : les puces latérales et les bandeaux
  de page utilisent désormais le même moteur `_make_icon()` QPainter (pas de
  dépendance emoji/police). Le bandeau commun `page_shell()` garde une vraie
  structure QWidget compatible avec les pages Infrastructure/Formation, avec
  bloc 38x38, couleur et centrage identiques.
- Toutes les pages principales ont une icône vectorielle cohérente :
  dashboard, messages, effectif, tactiques, match, entraînement,
  infrastructure, formation, transferts, calendrier, compétitions, finances,
  staff. Le menu supérieur conserve les trois barres horizontales.
- Page COUPE refondue sur le langage du CHAMPIONNAT : hero doré avec trophée,
  KPI Tour/Confrontations/Statut, panneau TABLEAU avec aide de lecture,
  panneau PALMARÈS séparé. Les confrontations du club restent mises en avant.
- run_tests.py 10/10 ALL OK ; sonde iter24 ALL OK ; error.log 0o.


---

## Annexe Q — Iteration 27 (notifications chantiers / bilan annuel / nouvelle saison)

- FIN DE CHANTIER : `process_facility_projects()` écrit désormais une news ET
  un message de messagerie `facility_complete` non lu avec le bâtiment, la
  date de livraison et le statut opérationnel.
- FIN DE SAISON : juste après la dernière journée et avant la remise à zéro,
  `process_season_transition()` capture un bilan complet : bilan du club
  (V/N/D, buts pour/contre, division, meilleur buteur), champions des six
  divisions et les derniers faits marquants du monde (news). Le bilan est
  envoyé dans la messagerie (`season_summary`) et dans les news.
- NOUVELLE SAISON : après clôture, calendrier et compteurs repartent au
  01/07 de l'année suivante ; le bouton latéral CONTINUER devient
  `NOUVELLE SAISON` et affiche la date de reprise au 01/07. Le calendrier
  sportif est ensuite généré sur la reprise de septembre.
- run_tests.py : 10/10 ALL OK ; error.log 0 octet.


---

## Annexe R — Iteration 28 (match 2D / mercato IA / forme)

- MATCH 2D : `display_team_colors()` écarte automatiquement deux couleurs
  trop proches (distance RGB/luminosité) ; le second maillot reçoit une teinte
  contrastée. Les joueurs du côté adverse sont dessinés en losange, ceux du
  club en cercle ; le gardien reste agrandi. Le bandeau et la popup utilisent
  les mêmes couleurs corrigées.
- OFFRE DE TRANSFERT : après envoi confirmé, retour automatique à la page
  Transferts (index 7), au lieu de la Messagerie.
- SCOUTING : une ligne hors de la page marché est rechargée depuis la DB avant
  d'afficher « joueur indisponible » ; filtres/pagination ne rendent plus les
  rapports cliquables à tort.
- MOUVEMENTS IA : maximum 3 recrutements par club et 2 mouvements par joueur
  et par saison, urgence contrôlée également ; les cascades de 4/5 clubs sont
  bloquées.
- FORME : les rapports de match convertissent désormais la condition stockée
  0..100 en rating 0..20 avant affichage ; plus de `forme 100/20`.
- run_tests.py : 10/10 ALL OK ; error.log 0 octet.


---

## Annexe S — Iteration 29 (formation vendue / contrats / mercato page)

- CENTRE DE FORMATION : une promotion vendue reste visible dans l'historique
  du centre mais son statut est désormais explicite `FORMATION • VENDU •
  AILLEURS (Lx)` ; aucune action de formation ne reste disponible sur ce
  joueur sorti du club.
- TRANSFERTS : ouvrir la page force l'onglet MARCHÉ (index 1), donc ne
  reconstruit plus l'historique lourd laissé par la visite précédente.
- CONTRATS : les messages de fin de contrat alertent et proposent explicitement
  de prolonger avant le départ. Les joueurs en dernière année peuvent refuser
  si leur temps de jeu est faible ou si leur ambition dépasse le projet du
  club. À expiration réelle, un joueur manager passe immédiatement libre,
  reçoit une news et un message `contract_expired`, avec historique gravé.
- run_tests.py : 10/10 ALL OK ; error.log 0 octet.


---

## Annexe T — Iteration 30 (messagerie éditoriale / blessures entraînement)

- BRIEFS : cooldown du mode quotidien (un brief tous les 2 jours maximum),
  cadence hebdomadaire conservée le lundi, et filtre éditorial par rubrique
  sur les derniers briefs (performances 7 j, formation 7 j, médical 10 j,
  transfert 5 j). Les messages restent regroupés mais le corps reçoit un
  ton `À retenir` quand il y a blessure/contrat/offre, sinon `La vie du club`.
  Le titre stable conserve l'historique et facilite la lecture.
- BLESSURES À L'ENTRAÎNEMENT : `apply_training_schedule()` collecte les noms,
  jours d'indisponibilité et IDs ; il écrit une news et un message non lu
  `training_injury` avec le protocole médical suggéré/action_data.
- run_tests.py : 10/10 ALL OK ; test_messagerie a validé cadence, déduplication,
  quotidien, extinction complète et anniversaires ; error.log 0 octet.


---

## Annexe U — Iteration 31 (glyphes hérités / icônes oubliées)

- MESSAGES : ajout de `clean_message_text()` au rendu des détails inbox et
  dialogues : les anciens glyphes corrompus (U+FFFD, séquences `�\x81`,
  contrôles) sont remplacés visuellement sans modifier les sauvegardes.
- DIRECTION SPORTIVE : le bloc PALMARÈS reçoit désormais une vraie icône
  trophée vectorielle, centrée dans son badge.
- RECHERCHE : la loupe est redessinée QPainter (badge global + recherche
  messagerie), sans emoji ni police dépendante.
- INFRASTRUCTURE/COMPLEXE : toutes les cartes de bâtiments et services
  utilisent `_make_icon()` vectoriel (tribunes, éclairage, parking, médical,
  formation, marketing, bar, boutique, terrains, événements, fan zone).
- run_tests.py : 10/10 ALL OK ; error.log 0 octet.


---

## Annexe V — Coupe refondue (tableau 64 places + affichage lisible)

### BUG CORRIGÉ : « R4 avec 3 gagnants »
- Le club exempté était retiré du tirage mais JAMAIS réinjecté dans les
  qualifiés : à chaque tour impair un club disparaissait. Constat : 61 clubs
  -> 30 matchs (R1), 15 (R2), 7 (R3), 3 (R4)… la coupe s'arrêtait avant la
  finale et certains clubs ne jouaient jamais.
- Nouveau modèle : tableau à la PUISSANCE DE 2 supérieure (61 clubs -> 64
  places, 60 -> 64 aussi). Les places libres deviennent des EXEMPTÉS attribués
  aux clubs les plus réputés (têtes de série), enregistrés dans
  meta `cup_byes_<season>` et RÉINJECTÉS dans les qualifiés au tour suivant.
- Vérifié : 32 -> 16 -> 8 -> 4 -> 2 -> 1, six tours, un seul champion, aucun
  club perdu, palmarès écrit.

### TIRAGE PLUS RÉALISTE ET VARIÉ
- Tirage par POTS : les clubs sont classés par réputation, puis les gros sont
  appariés aux petits pour le 1er tour (pas de choc entre cadors d'entrée).
- Graine de tirage composée saison + tour + empreinte des qualifiés + date :
  deux saisons donnent des tableaux DIFFÉRENTS (vérifié en sonde).
- Exemptés annoncés dans la news du tirage.

### AFFICHAGE COUPE (fini les « R1 / R2 / R3 » bruts)
- Noms de tours explicites : 32es DE FINALE, 16es, 8es, QUARTS,
  DEMI-FINALES, FINALE.
- Filtres de tour : boutons TOUS LES TOURS + un bouton par tour.
- Chaque confrontation est une CARTE : nom du tour + date à gauche, les deux
  clubs l'un au-dessus de l'autre, score central, mention « 10 m » en cas
  d'égalité ; le club du joueur est surligné.
- Bandeau PARCOURS : nombre de tours joués, dernier résultat et adversaire, ou
  prochaine confrontation ; KPI tour en cours / matchs au tableau / statut.
- Palmarès conservé en bas de page.
- Tests : run_tests.py 10/10 ALL OK ; sondes coupe (tableau complet, tirages
  différents, affichage 28 cartes) ALL OK ; error.log 0 octet.


---

## Annexe W — Coupe : clic sur une confrontation = fiche CLUB

- `open_cup_row()` n'ouvre plus la fiche d'un joueur : un menu propose les
  DEUX clubs de la confrontation (DOMICILE / EXTÉRIEUR), et le choix ouvre
  `show_club_profile()` (effectif, classement, réputation, couleurs).
- Curseur main sur le tableau et libellé d'aide mis à jour.
- run_tests.py 10/10 ALL OK ; error.log 0 octet.


---

## Annexe X — Effectif / popup de but / tableaux de coupe

### EFFECTIF : colonnes équilibrées
- Nouvelle méthode `_fit_roster_columns()` : chaque colonne reçoit la largeur
  de son EN-TÊTE ou de son texte le plus long (+ marge), puis l'espace
  excédentaire est réparti AU PRORATA. La dernière colonne n'absorbe plus tout
  le reste. Largeur bornée 44–250 px, recalculée après chaque remplissage et
  après un changement d'ordre/visibilité.

### POPUP DE BUT (match 2D)
- Carte agrandie et lisible : fond sombre translucide + liseré à la couleur du
  club, centrée sur le terrain.
- Le CLUB s'affiche en grand avec retour à la ligne automatique (2 lignes si
  nécessaire, texte jamais coupé en plein mot), le buteur en dessous.
- Clignotement conservé : encre blanche <> couleur du club, ~3 Hz.

### VUE COUPE : tableaux plus compacts
- Cartes de confrontation réduites (hauteur 44 px) : pastille courte
  (`32es · 12/03`), clubs en 8,5 pt sur deux lignes serrées, score 56 px.
- Libellés courts des tours (32es/16es/8es/1/4/1/2/FINALE) en plus des noms
  complets dans le titre du panneau.
- run_tests.py 10/10 ALL OK ; error.log 0 octet.


---

## Annexe Y — Effectif lisible + emblèmes vectoriels partout

### EFFECTIF : l'ÉTAT est revenu, les notes remplacent les étoiles
- La colonne ÉTAT affichait une simple espace colorée : elle était donc
  INVISIBLE. Elle reçoit désormais une pastille DESSINÉE (`_status_dot_pixmap`) :
  verte = apte, orange = fatigué, rouge = blessé/suspendu, violet = sur la liste.
  Le tooltip garde le détail (jours de blessure, suspension, cartons).
- NIV et POT n'affichent plus d'étoiles mais une NOTE sèche (/20), ce qui
  libère de la place : colonnes réduites (42 px) et colonne JOUEUR agrandie
  (police 9 pt, largeur calculée jusqu'à 340 px).
- L'équilibrage `_fit_roster_columns()` tient compte de ces nouvelles largeurs.

### EMBLÈMES DE PAGES
- 15 emojis d'emblèmes remplacés par des icônes QPainter (aucune dépendance à
  la police emoji) : calendrier, statistiques, centre de match, centre de
  formation, messagerie, historique des transferts, staff, archives, sauvegarde,
  cadenas du campus fermé, cartes de match, complexe.
- Nouvelles formes ajoutées : disquette, livre/archives, cadenas, cartes.
- run_tests.py 10/10 ALL OK ; error.log 0 octet.


---

## Annexe Z — Icônes réécrites et centrées au pixel

### DESSIN
- `_make_icon()` réécrit en REPÈRE CENTRÉ : translation au centre exact du
  pixmap, plus aucune conversion en entiers (fin du décalage d'un demi-pixel).
- Compensation du demi-pixel sur les tailles PAIRES (le centre géométrique
  tombe entre deux pixels) : rendu parfaitement symétrique de 14 à 48 px.
- Épaisseur de trait PROPORTIONNELLE à la taille (1,25 px mini, 7,5 % de la
  largeur), extrémités rondes, marge de sécurité ~16 % de chaque côté.
- 20 formes vectorielles distinctes : grille, effectif, tactiques, terrain,
  chrono, bâtiment, enveloppe, transferts, calendrier, finances, staff,
  trophée, loupe, disquette, livre, cadenas, cartes, menu, engrenage, retour.
- Formes 1/5/10 recentrées verticalement (elles étaient 1 à 2,5 px trop haut).

### BLOCS
- Taille du pictogramme normalisée à ~60 % du bloc pour tous les badges.
- Icône du Centre de match : le `setText("⚽")` du rafraîchissement écrasait le
  pixmap (puce vide) — remplacé par un `setPixmap` (couleur atténuée quand
  aucun match n'est jouable).

### VALIDATION
- Sonde de centrage : boîte englobante non transparente comparée au centre du
  pixmap pour les 13 puces du menu et les 20 formes → décalage maximal 1 px,
  aucune icône vide.
- run_tests.py 10/10 ALL OK ; error.log 0 octet.


---

## Annexe AA — Vraie évolution des joueurs + endurance allégée

### POURQUOI LA FICHE SEMBLAIT STATIQUE
- Le niveau /20 est la moyenne de 5 attributs (0-100) ramenée sur 20 : +1 sur
  UN attribut ne déplace la note que d'un dixième de point. Les gains de séance
  (probabilité ~4 %) étaient donc invisibles, et les points « perdus » quand
  l'attribut de prédilection était au plafond.

### NOUVEAU MOTEUR : `process_player_development()` (chaque lundi)
- Table `player_dev_progress` : POINTS fractionnaires accumulés par joueur.
  Dès qu'un point est complet, un attribut adapté au poste gagne +1 : la fiche
  bouge régulièrement, plus seulement au hasard d'une séance.
- Facteurs : courbe d'âge (1,45 jusqu'à 18 ans → 0 après 31), écart au
  potentiel, temps de jeu, assiduité (séances des 21 derniers jours), moral,
  niveau du centre de formation du club (ou division pour les clubs IA).
- BONUS JEUNE À FORT POTENTIEL (≤20 ans, écart ≥4) : ×1,3 pour que les pépites
  décollent vraiment.
- REPLI : si les attributs de prédilection sont au plafond, les points vont vers
  un autre attribut perfectible au lieu d'être perdus.
- RÉGRESSION : dès 29 ans, points de déclin vers endurance/vitesse/placement ;
  accentué à 31, 32 et 34 ans. Journalisée 'Vieillissement'.
- Journal : chaque point écrit dans `player_training_log`
  ('Développement' / 'Vieillissement') donc la fenêtre Évolution l'affiche.
- News automatique quand un joueur change de NOTE /20.

### ENDURANCE
- Ateliers : fatigue Normale 2 → 1, Élevée 4 → 3.
- Récupération quotidienne : +2 → +3 (adjoint +2 en plus, soit +5/jour).
- Matchs IA : fatigue 3-6 → 2-4.

### CALIBRATION VÉRIFIÉE (sonde : 12 semaines)
- 8 joueurs sur 9 progressent d'un point de note, endurance +2 à +6.
- Vétéran 33 ans : 10 → 9 avec endurance 60 → 54.
- run_tests.py 10/10 ALL OK ; error.log 0 octet.


---

## Annexe AB — Bouton menu, écran de démarrage, aperçu club, écussons

### BOUTON MENU DU HAUT
- Remplacé par un **QToolButton** (conçu pour les boutons icône seule) : Qt
  centre alors réellement le pictogramme, contrairement au QPushButton vide qui
  laissait un décalage. Style conservé (fond, liseré, survol, arrondi 12).

### ÉCRAN DE DÉMARRAGE
- Panneau à largeur stable (500-560 px), marges 34/20/34/16, interligne 12.
- Hauteurs harmonisées : REPRENDRE 86 px, NOUVELLE CARRIÈRE 78 px, boutons
  secondaires 62 px, QUITTER 56 px.
- Icônes vectorielles ajoutées sur CHARGER (cartes), SAUVEGARDES (disquette),
  OPTIONS (menu), CRÉDITS (équipe), QUITTER (retour) — textes sans glyphes
  décoratifs qui se décalaient.

### APERÇU DE CRÉATION D'ÉQUIPE
- `ClubIdentityPreview` réécrit : **ratio 300x175 verrouillé**, taille fixe
  400x233, plus d'étirement ni de zone vide.
- Fond en dégradé aux couleurs du club, blason et maillot recalculés sur la
  hauteur réelle, plaque de nom lisible en bas de carte.

### ÉCUSSONS DES CLUBS IA
- `draw_badge()` valide désormais `color1/color2` : couleur invalide, vide ou
  transparente → teinte dérivée de façon stable de l'identité du club, et
  seconde couleur assombrie automatiquement. Plus aucun blason sans couleur.

### VALIDATION
- run_tests.py 10/10 ALL OK ; error.log 0 octet.


---

## Annexe AC — Aperçu de création d'équipe refait

### ÉCUSSON
- Forme HÉRALDIQUE dessinée en QPainterPath (épaules, flancs, pointe basse),
  dégradé principal → secondaire, double liseré (extérieur clair + intérieur),
  initiales centrées avec ombre portée. Plus de simple carré arrondi.

### MAILLOT
- Proportions réelles (corps large, manches courtes, encolure en V, ourlet),
  construit en un seul chemin vectoriel.
- RAYURES CLIPPÉES dans le vêtement (setClipPath) : vertical, bandes,
  écharpe, damier, dégradé — plus de rayures qui dépassent ou se déforment.
- Ombre portée douce sous le maillot, col en couleur secondaire, numéro au
  torse (9).

### CARTE D'APERÇU
- Fond « stade » : dégradé aux couleurs du club, halo radial, cercle de
  terrain et ligne médiane très discrets.
- Plaque de nom en bas avec pastilles des deux couleurs et nom du club.
- Ratio 16:9 verrouillé (320x180) : l'aperçu ne se déforme plus.

### PAGE DE CRÉATION
- Aperçu agrandi (s'étire avec la fenêtre), résumé collé dessous.
- Nouveaux boutons de MOTIF DU MAILLOT (Rayures / Bandes / Écharpe / Damier /
  Dégradé) qui mettent l'aperçu à jour en direct.
- Colonne de formulaire en zone défilante : plus de contenu coupé sur petits
  écrans ; libellés à retour à la ligne pour éviter le débordement horizontal
  (fenêtre 1180x790, minimum 900x600).

### VALIDATION
- Rendus de contrôle hors écran (4 motifs + dialogue complet) : aucun
  débordement, aucune icône vide.
- run_tests.py 10/10 ALL OK ; error.log 0 octet.


---

## Annexe AD — Page de création : tout tient sans défilement

- FENÊTRE : 1140 x 700 (minimum 900 x 540). Le contenu occupe ~585 px de haut,
  donc plus de barre de défilement sur un écran 768p ou plus.
- DESCRIPTIONS : les cartes « Ligue » et « Difficulté » (une soixantaine de
  pixels chacune) deviennent de simples lignes colorées avec liseré gauche.
- COULEURS : principale et secondaire passent en DEUX COLONNES, hauteur des
  boutons 40 → 32 px.
- CHAMPS : 38 → 32 px ; espacements du formulaire 12 → 7 px, marges 18 → 12 px.
- EN-TÊTE : titre sur une seule ligne (13 pt au lieu de 16 pt sur deux lignes).
- APERÇU : hauteur plafonnée à 230 px (le ratio 16:9 est conservé par le
  dessin, qui se centre au lieu de s'étirer).
- Le panneau reste défilant en dernier recours (petits écrans), mais le
  contenu standard s'affiche entièrement d'un coup.
- run_tests.py 10/10 ALL OK ; rendu de contrôle 1140x700 : aucun défilement,
  error.log 0 octet.


---

## Annexe AE — Création : hauteur maîtrisée et ratio du maillot

- HAUTEUR : le contenu utile passe de 585 à ~544 px.
  · MOTIF DU MAILLOT est désormais sur la MÊME LIGNE que son libellé
    (boutons de 26 px) ;
  · l'aide couleurs tient sur une seule ligne ;
  · espacements du formulaire 7 → 6 px et marges 14/12 → 14/10.
- FENÊTRE : dimensionnée à l'écran disponible (max 1180 x 720, marge 30/40 px),
  minimum 900 x 520. Sur un écran 768p, plus de barre de défilement.
- APERÇU : hauteur portée à 262 px (au lieu de 230) pour occuper la colonne.
- RATIO DU MAILLOT : largeur 0,44 → 0,52 de la hauteur (ratio ~0,84) : le
  maillot n'est plus étiré en longueur ; l'écusson garde ses proportions
  (0,36 de hauteur, ratio 1,20).
- run_tests.py 10/10 ALL OK ; rendu de contrôle 1180x720 sans scroll ;
  error.log 0 octet.


---

## Annexe AF — Écran de démarrage et fenêtre OPTIONS

### ÉCRAN DE DÉMARRAGE
- Nouvelle icône PLAY (triangle dessinée) sur REPRENDRE et PLUS sur NOUVELLE
  CARRIÈRE : les deux gros boutons ont la même hauteur (80 px) et un vrai
  pictogramme, plus de glyphes décoratifs instables.
- Libellé de section « MENU PRINCIPAL » au-dessus de la carte carrière.
- Séparateur fin avant la rangée des boutons secondaires ; icônes vectorielles
  sur CHARGER, SAUVEGARDES, OPTIONS, CRÉDITS et QUITTER (20/18 px).
- Nouvelles formes d'icônes : 17 = plus, 18 = lecture.

### FENÊTRE OPTIONS
- Feuille de style PROPRE au dialogue (thème sombre complet) : fond dégradé,
  champs sombres, listes déroulantes, cases à cocher vertes, barre de
  défilement discrète. Elle ne dépend plus du style hérité de la fenêtre
  principale (qui laissait des zones blanches).
- En-tête : icône menu dessinée localement (aucune police), titre et
  sous-titre explicites.
- Onglets en pastilles : APPARENCE / MESSAGERIE / TRICHE / AIDE (sans emoji).
- APPARENCE : chaque réglage sur une ligne « titre + description » à gauche et
  contrôle à droite, alignés en haut du panneau.
- MESSAGERIE : chaque case tient sur UNE ligne avec son explication à droite
  (gain de hauteur) ; bloc presse compacté.
- Boutons : style unifié + bouton principal violet (ENREGISTRER).
- Fenêtre 780 x 600 (minimum 740 x 520).
- run_tests.py 10/10 ALL OK ; captures de contrôle vérifiées ; error.log 0o.


---

## Annexe AG — Accueil agrandi et THÈME CLAIR

### ACCUEIL
- Panneau élargi (560-640 px) et marges 38/24 : les boutons respirent.
- REPRENDRE / NOUVELLE CARRIÈRE : 96 px de haut (au lieu de 80), libellés
  15-15,5 pt, icônes lecture + (dessinées).
- Ligne secondaire : 64 px, QUITTER 58 px ; logo 200-262 px.
- Carte carrière 104 px ; libellé « MENU PRINCIPAL » et séparateur.

### THÈME CLAIR (nouvelle option)
- OPTIONS > APPARENCE > THÈME : choix « Clair » en plus de Nuit violette,
  Vert futsal et Noir & or.
- `light_stylesheet()` transforme la feuille sombre : les SURFACES très
  sombres deviennent claires, les textes clairs sont assombris, les BORDURES
  s'éclaircissent. Les dégradés d'ACCENT (vert, bleu, violet) sont préservés.
- `apply_theme_to_tree()` applique la même conversion aux styles INLINE des
  cartes et tableaux (stockés dans `_dark_qss` pour un retour au sombre sans
  perte). Réappliqué après navigation quand le thème clair est actif.
- L'écran d'accueil a un fond clair dédié (StartBackdrop.light).
- Les couleurs de boutons restent celles du jeu : vert (reprendre), bleu
  (nouvelle carrière), violet (actions principales), ce qui donne un thème
  clair coloré plutôt qu'un gris uniforme.
- run_tests.py 10/10 ALL OK ; error.log 0 octet.


---

## Annexe AH — Thème clair gris-blanc et listes déroulantes

### THÈME CLAIR MOINS BLANC
- Les surfaces passent d'un blanc pur à un **gris-blanc** : luminosité cible
  0.84 à 0.915 selon la profondeur (au lieu de 0.885 à 0.965).
- Textes encore plus foncés (0.14 de luminosité) et bordures plus présentes
  (0.70) : la hiérarchie des cartes redevient lisible.
- Fond d'accueil clair :
  #eef1f5 → #e3e8ef → #d4dce7 (au lieu de #f7fafd → #dde9f7).

### LISTES DÉROULANTES
- Chevron DESSINÉ (PNG généré une fois dans data/icons) à la place de la
  flèche native : `QComboBox::down-arrow`.
- Bouton de liste séparé par un liseré vertical de 30 px, zone de texte avec
  padding droit adapté (plus de texte sous la flèche).
- Liste déroulante aérée : fond dédié, bordure arrondie, marge interne 6 px,
  items de 28-30 px, sélection bleu profond.
- Appliqué à la feuille GLOBALE (chevron clair en thème sombre, foncé en
  thème clair) ET à la fenêtre OPTIONS (chevron #8fa3bd, items 30 px).
- run_tests.py 10/10 ALL OK ; captures vérifiées ; error.log 0 octet.


---

## Annexe AI — Noms, nationalités, base élargie, fiche club, libres

### NOMS ET NATIONALITÉS (22 pays)
- Nouvelle banque `NAME_BANK` : prénoms ET noms issus du MÊME pays, pour
  22 nationalités (France, Espagne, Portugal, Brésil, Argentine, Italie,
  Allemagne, Belgique, Maroc, Algérie, Tunisie, Sénégal, Côte d'Ivoire,
  Cameroun, Nigeria, Turquie, Serbie, Croatie, Pologne, Pays-Bas, Angleterre,
  Japon, Suède).
- `NATIONALITY_WEIGHTS` : majorité locale pour un championnat français (44 %)
  puis forte présence futsal/immigration (Portugal, Brésil, Maroc, Algérie…).
- `random_player_name()` garantit la cohérence prénom/nom/nationalité ; il
  remplace l'ancien tirage croisé (Lucas Okonkwo n'existe plus).
- Utilisé pour les effectifs de départ, les joueurs libres, les jeunes du
  centre et les pépites. Les anciens joueurs gardent leur nationalité.

### BASE DE DONNÉES PLUS LARGE
- Effectifs : 10 → 12 joueurs par club (720 joueurs dans le monde).
- Vivier de libres : petite base 50 → **140**, moyenne 100 → **280**,
  grande 200 → **520**.
- Vérifié : 720 joueurs, 18 nationalités représentées, 140 libres en « petite ».

### FICHE CLUB
- L'onglet **EFFECTIF & JOUEURS** s'ouvre PAR DÉFAUT.
- Nouvel onglet **🏆 PALMARÈS** : champions, promotions, relégations gravés
  (club_honours) + victoires en Coupe nationale (palmarès de la coupe), avec
  compteur de titres. État vide explicite pour un club sans trophée.

### RECRUTEMENT DES JOUEURS LIBRES
- Suppression des plafonds ajoutés précédemment : plus de limite de
  recrutements pour les LIBRES (clubs IA) ni de plafond de mouvements par
  joueur libre, ni de blocage dans les signatures d'urgence.
- Les transferts payants conservent leurs garde-fous (réalisme des mouvements).

### VALIDATION
- Sonde noms : 720 joueurs, 18 nationalités, 140 libres.
- Sonde fiche club : index par défaut = EFFECTIF, onglet PALMARÈS présent.
- run_tests.py 10/10 ALL OK ; error.log 0 octet.


---

## Annexe AJ — Maillots générés et réutilisés

### GÉNÉRATEUR PARTAGÉ (`ui_components.kit_pixmap`)
- Même dessin que l'aperçu de création (manches, encolure, ourlet, col,
  rayures CLIPPÉES), exporté en pixmap avec CACHE (identité + taille + motif).
- `kit_pattern_for(club_id, nom, motif_du_club)` : motif STABLE par club —
  le club du joueur garde son motif enregistré, les clubs IA reçoivent un
  motif déterministe dérivé de leur identité (jamais deux fois différent).

### AFFICHAGE
- DIRECTION SPORTIVE : maillot du club dans le bandeau d'accueil, à côté du
  message de bienvenue, rafraîchi avec les couleurs du club.
- FICHE CLUB : maillot à côté de l'écusson dans l'en-tête.
- FICHE JOUEUR : maillot du club du joueur dans l'en-tête (à droite du
  portrait), avec info-bulle du nom du club.
- MATCH 2D : les écussons de l'en-tête de match sont remplacés par les
  MAILLOTS des deux équipes (motif stable, couleurs réelles).
- `set_fixture_visual` continue de gérer les écussons du tableau de bord :
  seuls les en-têtes de match passent au maillot.

### VALIDATION
- Sonde : pixmaps générés pour les 5 motifs (96 px) et maillot présent sur la
  page Direction sportive (58x58 non nul).
- run_tests.py 10/10 ALL OK ; error.log 0 octet.


---

## Annexe AK — Maillot : motif respecté et avatar-maillot

### BUG : LE MOTIF CHOISI ÉTAIT PERDU
- `ClubSetupDialog.values()` renvoyait `"kit_pattern":"vertical"` en dur :
  Damier, Écharpe, Bandes ou Dégradé étaient ignorés à la création.
- Correction : le dialogue renvoie maintenant le motif réellement sélectionné
  (`self.kit_state`). Vérifié : création avec Damier -> `club.kit_pattern='checker'`.

### MOTIF DES CLUBS IA
- `kit_pattern_for()` dérive un motif STABLE de l'identité du club quand aucun
  motif n'est enregistré : les clubs IA ont désormais rayures, bandes, damier,
  écharpe ou dégradé — plus de « tout en rayures ».
- Le motif du club du joueur reste celui de la création (ou du sélecteur).

### AVATAR = MAILLOT DU CLUB
- `draw_player_avatar()` dessine le maillot du CLUB DU JOUEUR (couleurs et
  motif réels, lus en base avec cache) en FOND, avec le numéro par-dessus.
- Le maillot séparé à côté du portrait dans la fiche joueur est supprimé :
  l'identité visuelle est dans l'avatar.
- Les avatars du club et des clubs IA suivent donc leur vrai maillot.

### OPTIONS : SÉLECTEUR DE MAILLOT
- Nouvelle ligne « MAILLOT DU CLUB » dans OPTIONS > APPARENCE :
  Rayures / Bandes / Écharpe / Damier / Dégradé.
- Le choix met à jour `club.kit_pattern`, vide le cache d'avatars et rafraîchit
  l'interface : utile pour corriger une carrière existante.
- run_tests.py 10/10 ALL OK ; sondes motif/avatar OK ; error.log 0 octet.


---

## Annexe AL — Couleurs du match 2D et vraie fin de saison

### MATCH 2D : COULEURS ET LOGOS
- `set_fixture_visual()` utilisait une couleur NEUTRE pour l'adversaire
  (`neutral`) : son écusson perdait ses couleurs. Il lit désormais la fiche
  du club par son nom et applique ses VRAIES couleurs.
- `display_team_colors()` (terrain 2D) renforce le contraste : déclenchement
  dès 150 de distance RGB, 46 de luminosité, 48° d'écart de teinte, ou si les
  DEUX équipes sont dans la plage verte — l'extérieur est alors décalé de
  120-170° avec une saturation/valeur lisibles. Fini les deux équipes vertes.

### FIN DE SAISON EN DEUX TEMPS
- Après le DERNIER match : plus de bascule immédiate. `check_season_end()`
  ouvre une FENÊTRE DE 18 JOURS (meta `season_end_date` / `season_deadline`),
  publie une news et un message `season_break` avec la date limite : contrats,
  prolongations, préparation.
- Pendant la fenêtre, le bouton reste **CONTINUER** et le calendrier avance
  normalement.
- À l'échéance, `maybe_open_new_season()` publie un message `season_ready` et
  le bouton devient **NOUVELLE SAISON**.
- Le clic appelle `start_new_season()` : clôture complète (primes, montées,
  descentes, archives, contrats, nouveaux effectifs), date au 1er juillet,
  nouveau calendrier généré, metas de saison nettoyées et bouton remis à
  CONTINUER. Le libellé est resynchronisé à chaque rafraîchissement
  (`sync_season_button`).
- Bug corrigé au passage : le contrôle « refuse de prolonger » lisait des
  colonnes absentes (KeyError 'technique') et cassait la clôture.

### VALIDATION
- Sonde : fenêtre ouverte à la fin des matchs, bouton CONTINUER puis
  NOUVELLE SAISON à l'échéance, clic -> 2027-07-01, 568 matchs créés, metas
  nettoyées.
- run_tests.py 10/10 ALL OK ; error.log 0 octet.


---

## Annexe AM — Mercato : cible signée ailleurs et concurrence

### « IL A SIGNÉ AILLEURS » — AVEC LE CLUB
- Nouveau `notify_rival_signing()` : toutes les offres en attente d'un joueur
  qui rejoint un autre club passent en statut `rival`, avec un message
  explicite : « X a signé à [CLUB] (détail). Ton offre est annulée — le
  dossier est clos. » + news.
- Les messages d'échéance ne disent plus « joueur indisponible » : si le
  joueur a un nouveau club (transfert) ou est parti libre, le NOM du club de
  destination est affiché. Sinon seulement, le dossier est « annulé ».
- Onglet OFFRES : statut « SIGNÉ À [CLUB] » pour ces dossiers.
- Les clubs IA qui signent un joueur LIBRE appellent aussi
  `notify_rival_signing()` (salaire indiqué) : si le manager avait une offre
  en cours, il est prévenu immédiatement.

### CONCURRENCE RÉALISTE
- Une offre SOUS le prix demandé peut être DOUBLÉE par un club rival
  (18 % de chance) : un club de réputation supérieure avec le budget suffisant
  enlève le joueur au prix demandé, l'historique du joueur est gravé et le
  manager reçoit le message « signature manquée » nommant l'acheteur.
- Conséquence : payer le prix demandé SÉCURISE la cible ; négocier à la baisse
  comporte un vrai risque sportif.

### VALIDATION
- Sonde : offre 50 000 € sur une cible vendue à un autre club -> titre
  « Mercato • signature manquée », corps nommant le club, outcome `rival`,
  onglet OFFRES « SIGNÉ À AVENIR DE LONDRES ».
- run_tests.py 10/10 ALL OK ; error.log 0 octet.


---

## Annexe AN — Centre des transferts actionnable

### ACTIONS DIRECTES DANS L'ONGLET OFFRES
- Barre d'actions sous les deux tableaux : OUVRIR LE DOSSIER, ACCEPTER,
  REFUSER, CONTRE-OFFRE.
- Elle s'active uniquement sur un dossier **prêt** (statut `ready`) et de type
  décidable (market_offer, transfer_sale, transfer_sale_counter,
  contract_offer, free_agent_contract). Sinon les boutons restent grisés.
- L'identifiant du message est stocké dans la première cellule (Qt.UserRole) :
  le tri des colonnes ne casse plus la sélection.
- ACCEPTER/REFUSER/CONTRE-OFFRE passent par le même dispatcher que la
  messagerie (`_resolve_message`), puis rafraîchissent l'onglet.
- OUVRIR LE DOSSIER bascule sur la messagerie et sélectionne le message
  correspondant (`_open_message_by_id`).

### BADGE SUR LE MENU TRANSFERTS
- Nouvelle pastille orange sur l'entrée **Transferts** du menu latéral :
  compte les dossiers `ready` (offres reçues/envoyées, contrats) à traiter.
- Mise à jour à chaque rafraîchissement, masquée quand tout est réglé.

### VALIDATION
- Sonde : sélection d'une offre reçue -> trois boutons actifs ; badge visible
  et compteur = 1 ; clic REFUSER -> message `handled` et onglet rafraîchi.
- run_tests.py 10/10 ALL OK ; error.log 0 octet.


---

## Annexe AO — Coupe Inter-Ligue

### RENOMMAGE
- « Coupe nationale » → **Coupe Inter-Ligue** partout (news, messages, fiches,
  palmarès, onglet, libellés de match).

### EXEMPTÉS ALÉATOIRES
- Les places libres du tableau (61 clubs → 64) sont attribuées par **tirage au
  sort**, plus par réputation : `rng_byes` mélange tous les clubs et sort les
  exemptés. Vérifié : exemptés avec réputations 79 / 45 / 64 / 28.

### PRIMES
- Barème par tour franchi (versé au club du manager, catégorie « Coupe » dans
  les finances + news) :
  32es 15 000 €, 16es 30 000 €, 8es 55 000 €, quarts 100 000 €,
  demies 200 000 €, finale 300 000 €, **vainqueur 1 000 000 €**.

### ESPACEMENT
- `_cup_round_date()` vérifie désormais les matchs du CLUB DU JOUEUR : un tour
  n'est programmé que s'il est à **4 jours ou plus** de tout autre match.
  Avec le calendrier hebdomadaire d'automne, la coupe démarre donc en novembre
  (semaines libres), puis tous les ~4 semaines (trêve hivernale sautée).
  Plus de rafales « tous les 3 jours ».

### RAPPORTS
- Les matchs de coupe du manager écrivent un rapport `ai_match_report` : le
  clic dans le calendrier affiche les buteurs (plus de « pas de rapport »).
- Libellés corrigés : plus de « JOURNÉE 03 » pour un tour de coupe —
  `fixture_tag()` affiche **COUPE R1/R2…** dans l'en-tête, le sous-titre, la
  news du match et le rapport simplifié. La news de résultat utilise aussi
  l'étiquette de coupe.
- run_tests.py 10/10 ALL OK ; sonde coupe 5 (exemptés, primes, écart ≥ 4 j,
  6 tours, palmarès) OK ; error.log 0 octet.


---

## Annexe AP — Coupe : exemptés vérifiés et visibles

### CALCUL (60 équipes)
- Tableau à la puissance de 2 supérieure : **64 places**.
- Exemptés = 64 − 60 = **4** ; matchs du 1er tour = (60 − 4) / 2 = **28**.
- Qualifiés au tour 2 = 28 vainqueurs + 4 exemptés = **32** (tableau parfait :
  32 → 16 → 8 → 4 → 2 → 1).
- Contrôlé pour 58 à 64 équipes : `matchs + exemptés = places/2` à chaque fois.

### AFFICHAGE
- Nouveau bandeau « **EXEMPTÉS DU 1ER TOUR (4) : club A • club B • …** »
  sous le parcours du club.
- Dans le tableau, chaque exempté apparaît comme une ligne dédiée
  « 32es · EXEMPTÉ · Nom du club » (liseré pointillé violet), donc le premier
  tour affiche bien **28 matchs + 4 exemptés = 32 lignes**.
- Sonde : 60 clubs → 4 exemptés, 28 matchs, 32 lignes, libellé correct.
- run_tests.py 10/10 ALL OK ; error.log 0 octet.


---

## Annexe AQ — Page Coupe immersive

### IDENTITÉ DU TOURNOI
- Héros dédié (dégradé violet/bleu nuit, trophée vectoriel 36 px) avec le nom
  **COUPE INTER-LIGUE** en 15 pt, une ligne d'édition
  « ÉDITION n • SAISON n • 60 CLUBS • 6 DIVISIONS • 4 EXEMPTÉ(S) » (chiffres
  calculés en base) et le rappel des règles.
- Encart « EN JEU » à droite : prime du prochain tour du club
  (« 16es DE FINALE : 30 000 € »), « ÉLIMINÉ • 1 000 000 € au vainqueur » si
  le club est sorti, ou la cagnotte finale.

### DIVISIONS VISIBLES
- Chaque club des cartes de match porte une **pastille de division**
  (`L1` or, `L2` argent, `L3` vert, `L4+` orange) en texte riche.
- Légende dans l'en-tête du tableau : « Lx = division du club (L1 = élite) ».

### PETITS POUCETS
- Bandeau « **PETIT POUCET • L6 • AS Avignon (+5 autres en L6) · encore en
  lice au 16es** » (club de la plus petite division encore en course).
- Sous-ligne « Survivants par division : L1 ×7 · L2 ×5 · … · L6 ×6 — 25
  club(s) hors L1 encore en course ».
- **Badge EXPLOIT** (bordure or + étiquette) sur toute confrontation où un club
  sort un adversaire situé **au moins deux divisions au-dessus**.
- Les exemptés restent listés par leur nom dans le bandeau et en lignes
  « 32es · EXEMPTÉ · club » (hauteur réduite à 32 px pour gagner de la place).

### VALIDATION
- Sonde rendu : éditions/divisions/exemptés corrects (60 clubs, 6 divisions,
  4 exemptés), prime en jeu 15 000 € puis 30 000 € après qualification,
  petit poucet qui suit les survivants (10 → 6 clubs de L6), 3 cartes EXPLOIT
  au 1er tour simulé.
- run_tests.py 10/10 ALL OK ; error.log 0 octet.


---

## Annexe AR — Champion de Ligue 1, classement et fin de saison

### CAUSE RACINE (sauvegarde réelle analysée en lecture seule)
- `user_season_aggregate()` comptait les matchs de **coupe** (seuls les amicaux
  étaient filtrés) : la ligne de classement du club affichait 22 matchs au lieu
  de 18 et `reconcile_user_results()` en déduisait un `career.matchday` faux
  (J23 au lieu de J19).
- `finish_match()` simulait les autres matchs avec ce compteur de carrière au
  lieu de la **journée du match** : après une journée de coupe, la simulation
  visait une journée inexistante. Résultat : les 29 matchs IA de la dernière
  journée (2032-03-01) n'ont jamais été joués.
- `check_season_end()` exigeant **zéro match non joué**, la saison ne pouvait
  plus se clôturer : ni titre, ni prime, ni fenêtre de fin de saison, ni bouton
  NOUVELLE SAISON.

### CORRECTIFS
- `user_season_aggregate()` : filtre strict
  `fixture_type='championship'` + `matchday < 100`. Le classement, les points et
  le compteur de journée ne comptent plus que le championnat.
- `finish_match()` : la simulation des matchs IA utilise la `matchday` du
  **fixture joué** (repli sur le compteur carrière) — plus de dérive.
- Nouveau `simulate_overdue_championship()` : rattrape chaque jour les journées
  de championnat passées mais non simulées. Les sauvegardes déjà bloquées
  s'auto-réparent au premier CONTINUER.
- `check_season_end()` et `process_season_transition()` filtrent la saison en
  cours et lancent le rattrapage avant de compter.

### TITRE ET PRIME
- Nouveau `crown_season_champion()` : dès que le **championnat** est terminé
  (même si la coupe continue), le leader de la division du club est couronné.
  Idempotent via `meta season_crowned_<saison>`.
- Si c'est le club du joueur : news « **CHAMPION DE LIGUE n** », message
  « Champion de Ligue n ! » dans la messagerie et **prime de titre** :
  L1 1 500 000 €, L2 500 000 €, L3 250 000 €, L4 150 000 €, L5 80 000 €,
  L6 40 000 € (catégorie Performance dans les finances).
- La clôture de saison grave ensuite le palmarès (`club_honours`) sans repayer
  la prime.

### TEST BOUT EN BOUT (copie de la sauvegarde bloquée)
- Classement club 1 : 22 matchs → **18** (10V 6N 2D, 36 pts) ; J23 → **J19**.
- Rattrapage : **29** matchs IA rejoués, 0 restant.
- Titre : +**1 500 000 €**, news CHAMPION, message « Champion de Ligue 1 ! ».
- Fenêtre : `season_end_date=2032-04-13`, `season_deadline=2032-05-01`, bouton
  qui passe à **NOUVELLE SAISON**.
- Transition : saison **7**, **568** fixtures générées, palmarès saison 6
  enregistré, prime payée **une seule fois**.
- run_tests.py 10/10 ALL OK ; error.log 0 octet.


---

## Annexe AS — Page Staff immersive et effets progressifs

### ICÔNES
- Les emojis des 8 postes sont remplacés par des **icônes vectorielles**
  dessinées dans `_make_icon` : loupe (recruteur), croix médicale (kiné),
  haltère (préparateur), calculatrice (comptable), presse-papiers (directeur
  sportif), sifflet (adjoint), mégaphone (marketing), équerre (architecte).
  Rendu identique quelle que soit la police Windows.

### IMMERSION
- Héros « PERSONNEL DU CLUB » en dégradé avec trophée vectoriel, masse
  salariale en grand et compteur « n/8 postes · niveau moyen x.x ».
- Bandeau **EFFETS ACTIFS** : une chip par employé présent, mise à jour en
  direct (`SCOUTING ×3`, `PAIE −8 %`, `FORME +3/j`, `RÉPUTATION +2/sem`…).
- Chaque employé reçoit un **nom et une nationalité** cohérents (générés une
  fois, stockés en meta `staff_name_<poste>` / `staff_nat_<poste>`), affiché
  avec son rang : DÉBUTANT, CONFIRMÉ, EXPERT, ÉLITE, LÉGENDE.
- Liseré de carte coloré selon le niveau (gris/vert/bleu/violet/or).
- Chaque carte montre l'effet **ACTUEL** (vert) et l'effet au **NIVEAU
  SUIVANT** (ambre), pour rendre la progression lisible.
- Bouton de formation dynamique : « FORMER • 3 600 € » avec coût et durée
  croissants ; bandeau de formation avec jours restants.

### EFFETS PROGRESSIFS (petit au début, fort au niveau 5)
| Poste | Niveau 1 | Niveau 5 |
|---|---|---|
| Recruteur | 1 mission parallèle | 5 missions |
| Kiné | −1 j soigné, +0 % | −3 j, +12 % |
| Préparateur | +10 % progression | +50 % |
| Comptable | −4 % paie staff | −12 % |
| Directeur sportif | +2 connaissance/lundi | +10 |
| Adjoint | +1 forme/jour | +5 |
| Marketing | +1 réputation/lundi | +3 |
| Architecte | −1 % devis, −3 % délais, 1 chantier | −7 %, −15 %, 5 chantiers |

- Formation : coût `base × (1 + 40 % par niveau)`, durée
  `14 j + 3 j par niveau` (3 600 € / 14 j au niveau 1, 5 000 € / 17 j au
  niveau 2…), un seul staff formé à la fois.
- Les effets sont réellement appliqués dans la simulation : paie du staff,
  récupération quotidienne, réputation hebdomadaire, connaissance shortlist,
  protocoles du kiné (jours + chance), progression à l'entraînement,
  chantiers de l'architecte, slots de scouting.

### VALIDATION
- Sonde : 8 cartes, noms générés, effets N1/N5 corrects, 6 embauches,
  masse salariale 16 000 €/mois, 7 chips actives, formation préparateur
  3 600 €/14 j → niveau 2 (+20 %), coût suivant 5 000 €/17 j, paie comptable
  progressive.
- run_tests.py 10/10 ALL OK ; error.log 0 octet.


---

## Annexe AT — Maillots et avatars corrigés partout

### CAUSES TROUVÉES
- La colonne `club.kit_pattern` vaut **« vertical » par défaut** : comme elle
  était toujours passée en « explicite », **tous les clubs IA portaient le même
  maillot à rayures**, quel que soit leur écusson.
- L'en-tête du match calculait le motif avec `kit_pattern_for(0, nom)` alors que
  la fiche club utilisait `(id, nom, motif)` : un club pouvait donc changer de
  maillot entre la fiche et le match.
- Le cache d'avatars ne contenait **pas le club** : un joueur transféré gardait
  les couleurs de son ancien club (d'où des maillots « pas les bons »).
- Le changement de motif dans OPTIONS ne purgeait ni le cache des clubs ni
  celui des avatars.

### CORRECTIFS
- `kit_pattern_for()` : pour un club IA, « vertical » (valeur par défaut) est
  traité comme **automatique** ; le motif est tiré d'un hash stable de l'ID du
  club. Le club du joueur conserve son choix. Répartition constatée sur 60
  clubs : 13 checker, 12 diagonal, 11 horizontal, 12 gradient, 12 vertical.
- Fiche club, en-tête de match et avatars utilisent désormais **le même motif**
  (vérifié club par club).
- Cache d'avatars : clé = joueur + taille + numéro + poste + **club + couleurs
  + motif + statut**. Un transfert rafraîchit immédiatement le maillot.
- `set_club_kit()` purge les deux caches.

### NOUVEAU RENDU
- Moteur unique `paint_kit()` dans `ui_components` : silhouette de maillot avec
  épaules courbes, manches, col, poignets, dégradé de tissu, reflet d'épaule,
  ombres latérales et de bas, contour net.
- Motifs **remplis** (rayures verticales/horizontales, sash, damier, dégradé)
  au lieu de simples traits.
- Vignettes `kit_pixmap` : mêmes couleurs, lisibles de 26 à 96 px.
- Avatars joueurs : **buste** de maillot aux couleurs du club, col rond,
  numéro contrasté (blanc ou marine selon la luminosité du maillot), halo aux
  couleurs du club, badges poste et blessure/suspension.
- L'aperçu de création de club utilise le même moteur que le jeu (plus de
  divergence entre l'aperçu et la fiche).

### VALIDATION
- Sonde cohérence : fiche = avatar pour les 12 premiers clubs, motif d'en-tête
  identique, 60 clubs bien répartis sur les 5 motifs.
- Planche sur copie de la sauvegarde : Arbot (orange/noir damier), Paris
  (rayé diagonal), Londres (rayures), Madrid (dégradé)… et avatars assortis.
- run_tests.py 10/10 ALL OK ; error.log 0 octet.


---

## Annexe AU — Écussons en relief et numéros lisibles

### ÉCUSSONS (moteur unique `paint_crest`)
- Formes nettes : **bouclier** à coins arrondis et pointe, cercle, losange,
  carré moderne, monogramme (cercle + bande diagonale).
- Rendu en couches : **ombre portée**, émail en dégradé vertical, bande basse
  plus dense, **reflet diagonal**, double liseré (interne + anneau extérieur).
- Monogramme **contrasté** : lettres sombres sur écusson clair, blanches sur
  écusson sombre, avec ombre et liseré opposé — plus de sigle illisible sur un
  blason blanc.
- Utilisé par `draw_badge()` (classements, fiche club, en-têtes, sauvegardes,
  rapports) **et** par l'aperçu de création de club : plus de divergence entre
  l'aperçu et le jeu.

### NUMÉROS DE MAILLOT
- Le numéro est désormais dessiné en **chemin vectoriel** avec :
  - une **ombre portée** décalée ;
  - un **contour contrasté** épais (sombre sur numéro clair, clair sur numéro
    sombre) ;
  - une couleur de base calculée sur la luminosité du maillot.
- Résultat : lisible sur les damiers, rayures et dégradés, y compris
  blanc sur blanc.

### VALIDATION
- Planche de contrôle : 5 formes d'écussons × 6 paires de couleurs, lisibles de
  24 à 108 px ; numéros testés sur damier blanc, rayures, dégradé clair et
  maillot sombre.
- Planche finale sur copie de la sauvegarde : écussons, maillots et avatars
  cohérents pour 8 clubs.
- run_tests.py 10/10 ALL OK ; error.log 0 octet.


---

## Annexe AV — Joueurs libres : maillot uni

### PROBLÈME
- Dans les sauvegardes, un joueur libre conserve souvent un `club_id` non nul
  (dernier club) avec `is_free_agent=1`. L'avatar affichait donc le maillot de
  son **ancien club**, ce qui le rendait indistinguable d'un joueur sous
  contrat.

### CORRECTIF
- `_club_jersey_identity()` teste désormais **`is_free_agent` en priorité** :
  tout joueur libre (ou sans club) reçoit une identité neutre
  `(0, #565f6d, #232831, "solid")` → **maillot uni graphite**, col et poignets
  sombres, sans motif ni couleurs de club.
- Le numéro reste dessiné avec son contour contrasté (lisible sur le gris).
- Le cache d'avatars inclut cette identité : un joueur qui signe dans un club
  reprend immédiatement les couleurs de ce club, et inversement s'il est libéré.

### VALIDATION
- Comparatif sur copie de sauvegarde : 4 joueurs de clubs (damier orange,
  sash bleu, rayures, dégradé) puis 4 libres en gris uni — distinction
  immédiate.
- run_tests.py 10/10 ALL OK ; error.log 0 octet.


---

## Annexe AW — Transferts : dossiers clos, page OFFRES et offres spontanées

### BUG « L'ACTION RESTE BLOQUÉE »
- Une contre-offre acceptée était bien traitée en base (message `handled`,
  indemnité débitée, arrivée programmée) mais l'onglet OFFRES continuait à
  afficher **« CONTRE-OFFRE REÇUE »** : le libellé des dossiers fermés était
  déduit de `outcome`, pas du statut.
- Correctifs :
  - les dossiers fermés affichent **« ACCORD • CLOS »** (achat) ou
    **« VENDU • ACCEPTÉ »** (vente) ;
  - l'issue `accepted` + `final_fee` est désormais **écrite dans
    `action_data`** à l'acceptation ;
  - une case **« AFFICHER LES DOSSIERS CLOS »** (décochée par défaut) masque
    les dossiers traités : plus de faux « en attente » à l'écran ;
  - `_offers_dirty` est posé à chaque résolution pour forcer le rebuild.
- L'acceptation d'une contre-offre paie exactement le **prix demandé**
  (`counter_fee`) et respecte le **salaire réclamé** (`counter_salary`).

### PAGE OFFRES IMMERSIVE
- Héros « CENTRE DES TRANSFERTS » (dégradé, icône vectorielle) avec **budget
  transferts** en grand et **prochaine échéance**.
- Bandeau de synthèse : achats actifs, offres reçues à traiter, dossiers clos
  (masqués ou non).
- Statuts **colorés** : attente (ambre), contre-offre (violet), décision
  attendue (vert), dossier clos (gris), signé ailleurs (rouge).
- **Avatar du joueur** dans chaque ligne, dossiers actifs triés avant les clos,
  arrivées annoncées libellées « ARRIVÉE PROGRAMMÉE ».

### OFFRES SPONTANÉES (hors liste)
- `generate_transfer_interest()` peut désormais viser un joueur **non listé** :
  - environ 5 % par jour, limité à **une offre tous les 18 jours** ;
  - cible parmi les joueurs de valeur du club (effectif > 9) ;
  - prix **au-dessus de la valeur** (`max(prix demandé ×1,05 ; valeur ×1,22
    à ×1,85)`), acheteur solvable uniquement ;
  - message « **Offre spontanée • Club** », prime affichée en %, news Mercato.
- Les offres reçues restent négociables (accepter / refuser / contre-offre) et
  se terminent proprement dans l'onglet OFFRES.

### VALIDATION
- Sonde achat : contre-offre acceptée → message `handled`, budget −150 000 €
  (prix demandé), arrivée programmée, ligne « ACCORD • CLOS ».
- Sonde vente : offre spontanée acceptée → budget +300 000 €, joueur transféré,
  ligne « VENDU • ACCEPTÉ ».
- Sonde génération : 3 à 5 offres spontanées sur 120 jours, toutes sur des
  joueurs **non listés**, primes de +56 % à +119 %.
- run_tests.py 10/10 ALL OK ; error.log 0 octet.


---

## Annexe AX — Fins de contrat, durées et prétentions salariales

### 1) LES JOUEURS À 0 AN RESTAIENT AU CLUB
- La « réparation » d'anciennes sauvegardes remettait `contract_years=2` aux
  contrats à 0 an : les joueurs expirés restaient donc dans l'effectif.
- Correctifs :
  - la réparation **libère** désormais le joueur (`is_free_agent=1`,
    `contract_years=0`, retiré de la liste des transferts) ;
  - nouvelle migration `free_agents_clean_v1` pour les sauvegardes existantes ;
  - nouveau **contrôle quotidien** `process_contract_expiries()` : tout joueur à
    0 an part libre immédiatement, avec news + message s'il appartient au club
    du manager.

### 2) LES LIBRES APPARAISSAIENT SUR LES FICHES DE CLUB
- Un joueur libre conserve souvent son ancien `club_id` : les requêtes
  d'effectif le listaient encore.
- Filtre `COALESCE(is_free_agent,0)=0` ajouté à : fiche club, page Effectif,
  compteurs d'effectif, disponibilités (6 requêtes), paie des joueurs,
  développement hebdomadaire. Un libre n'est plus ni listé, ni payé, ni entraîné.

### 3) « LES JOUEURS N'ACCEPTENT QUE 2 ANS »
- La durée exigée valait `max(2, contract_years)` : un libre (0 an) demandait
  donc toujours 2 ans, un joueur sous contrat pouvait exiger 4-5 ans.
- Nouveau `contract_demand_years()` : **3-4 ans** pour les 21 ans et moins,
  **3 ans** jusqu'à 24 ans, **2 ans** jusqu'à 30 ans, **1 an** au-delà.
  Une offre plus longue que la durée demandée est acceptée.

### 4) PRÉTENTIONS SALARIALES TROP ÉLEVÉES
- La demande partait du **salaire actuel** (`salaire × 1,06 + bonus`) : un
  salaire déjà surpayé faisait boule de neige à chaque renouvellement.
- La demande est désormais **ancrée sur le salaire juste** :
  `base = max(salaire juste × 1,02 ; salaire actuel × 0,85)` puis
  **plafond `salaire juste × 1,35`**, avant les ajustements de surqualification
  et de réputation.
- Exemple mesuré sur la sauvegarde : un niveau 19 de Ligue 1 passait de
  **110 000 €/mois** de demande à **18 000 €/mois**.
- Les exigences des joueurs libres suivent : médiane à 2 000 €, maximum 12 000 €
  au lieu de 14 000 € + fourchette haute.

### VALIDATION
- Sonde effectifs : club 1 → 33 joueurs en base mais **32 listés** (1 libre
  exclu) ; club 3 → 12 listés / 1 libre exclu ; paie filtrée < paie brute.
- Sonde expiration : 2 joueurs à 0 an (club 1 et club 2) → libres immédiatement.
- Sonde durées : 3 ans accepté pour un jeune libre, 1 an refusé avec
  contre-proposition à 3 ans, 4 ans accepté.
- run_tests.py 10/10 ALL OK ; error.log 0 octet.


---

## Annexe AY — Terrain 2D, popup de but et rapport de match

### COULEURS DES PIONS
- `display_team_colors()` changeait la TEINTE du club adverse dès que les deux
  maillots étaient un peu proches : Arbot (orange) contre Metz (rouge) donnait
  des pions adverses **verts**. La fonction conserve désormais les couleurs
  réelles ; si les maillots sont vraiment identiques, elle se contente
  d'éclaircir/assombrir l'extérieur.

### MAILLOTS SUR LE TERRAIN
- Nouveau `Pitch2DWidget.set_team_kits(home_pix, away_pix)` : les pions sont
  dessinés avec le **maillot du club** (couleurs + motif, via `kit_pixmap`),
  numéro de dossard contrasté sur la poitrine, anneau discret et **anneau doré
  pour le gardien**.
- `start_match()` transmet les maillots des deux clubs (motif compris) ;
  la fenêtre propre du centre de match les efface (`set_team_kits(None,None)`).
- Repli automatique sur les formes cercle/losange si aucun maillot n'est fourni.

### POPUP DE BUT
- La popup plein écran mesurait la largeur sur le nombre de caractères et
  restait bloquée à 420 px : « ARBOT FUTSAL » passait sur deux lignes.
- Largeur calculée sur la **métrique réelle** de la ligne « BUT ! CLUB »
  (lettrage + padding), hauteur fixe 138 px, police réduite si nécessaire :
  le nom du club reste sur une seule ligne.
- La popup 2D du terrain réduit aussi sa police au lieu de couper le nom
  (`TextSingleLine`).

### RAPPORT DE MATCH
- Les écussons étaient dessinés avec des couleurs codées en dur (violet/bleu).
- Le rapport lit désormais `club.color1/color2/logo_pattern` : **écusson réel**
  de chaque club, accompagné de son **maillot** (couleurs + motif) de part et
  d'autre du score.

### VALIDATION
- Sonde couleurs : Arbot (#c47220) / Metz (#c0392b) restent orange et rouge.
- Rendu terrain : 10 maillots miniatures (damier orange/noir contre rayures
  rouges/blanches), gardiens cerclés d'or, numéros lisibles.
- Popup : largeur 592 px, texte « BUT !   ARBOT FUTSAL » sur une ligne.
- Rapport : écusson + maillot réels pour les deux clubs.
- run_tests.py 10/10 ALL OK ; error.log 0 octet.


---

## Annexe AZ — Exploitation, onglet Coupe et suivi des jeunes

### INFRASTRUCTURE • EXPLOITATION
- Le bouton **APPLIQUER LE TARIF** était poussé tout en bas du panneau (le
  graphique prenait tout l'espace disponible) : il est désormais **juste sous
  le prix**, pleine largeur, toujours visible.
- Nouveau **héros** « EXPLOITATION DU MATCH » (dégradé, icône finances) avec
  tarif, affluence attendue et recette estimée du prochain match.
- Les onglets Infrastructure portent des **icônes vectorielles**
  (complexe / gestion / exploitation) et le contenu du panneau tarif est
  regroupé en haut (plus de grand vide au milieu).

### CALENDRIER • ONGLET COUPE
- Nouvel onglet **COUPE** dans le calendrier, distinct du championnat et des
  amicaux :
  - héros trophée + résumé (« n tour(s) • n qualification(s) • statut ») ;
  - liste des tours du club (COUPE R1/R2…, date, DOM/EXT, adversaire, score),
    lignes colorées (vert = qualifié, rouge = éliminé, ambre = à jouer) ;
  - clic sur un tour : **rapport** du match (score + buteurs) ou prochaine
    rencontre si le match n'est pas joué ;
  - liste dimensionnée au nombre de tours, le rapport occupe le reste.

### CENTRE DE FORMATION • SUIVI ET BONUS
- Nouveau panneau **SUIVI DES JEUNES • MOINS DE 18 ANS AU CLUB** : tableau
  (joueur, âge, poste, niveau, potentiel, forme, bonus académie). Les joueurs
  de 18 ans et plus n'y figurent pas.
- **Bonus académie** : à l'entraînement, les -18 ans utilisent le meilleur
  facteur entre le préparateur physique et le centre de formation
  (`+10 % par niveau au-dessus du 1`) ; au développement hebdomadaire, leur
  progression est encore multipliée par `1 + 10 % × (niveau − 1)`.
  → dès le **niveau 6**, le centre dépasse l'entraînement d'équipe ; au
  niveau 8, le bonus atteint **+70 %** (affiché dans le panneau).
- Le panneau est masqué tant que le centre n'est pas ouvert, comme le reste
  de la page.

### VALIDATION
- Exploitation : bouton visible à y=72, héros « Tarif 12 € • 1 223
  spectateurs • recette 16 987 € ».
- Calendrier : 3 onglets (SAISON, AMICAUX, COUPE), 1 tour listé et cliquable.
- Jeunes : 2 joueurs de -18 ans suivis, le joueur de 19 ans exclu,
  bonus affiché « +70 % » au niveau 8.
- run_tests.py 10/10 ALL OK ; error.log 0 octet.


---

## Annexe BA — Finance : refonte, santé mensuelle et viabilité

### PRÊT BANCAIRE
- Héros dédié (icône, dégradé bleu nuit) avec la **dette restante** en grand.
- Simulateur restructuré : montant / durée / bouton, 5 KPI (taux, échéance,
  coût total, frais, capacité) et une **phrase de synthèse** :
  « Tu rembourseras X € au total : Y € d'intérêts + Z € de frais • sur N semaines ».
- Panneau « PRÊT EN COURS » avec jauge de remboursement et remboursement
  anticipé ; tableau d'historique restylé (en-têtes, lignes, alignements).

### SPONSORS
- Héros compact (mégaphone vectoriel) : accord en cours ou invitation à
  négocier, bouton d'action à droite.
- Cartes d'offres refaites : **monogramme du partenaire**, liseré coloré par
  profil (stable / performance / prestige), versement hebdomadaire en grand,
  prime par victoire, prime à la signature et bouton « SIGNER CE CONTRAT ».

### SANTÉ FINANCIÈRE MENSUELLE
- Nouvelle estimation `estimate_monthly_finance()` : billetterie (2 matchs),
  TV, sponsors, installations locatives vs salaires joueurs, staff et prêts.
- Le bandeau de la page affiche désormais :
  - **SANTÉ FINANCIÈRE • SAINE / TENDU / DÉFICIT • ±X €/mois** ;
  - le détail revenus/charges et la **réserve en mois** en cas de déficit.

### VIABILITÉ GLOBALE (test)
Ratios revenus mensuels / masse salariale sur des clubs neufs, sponsor
« stable » signé, sans staff ni installation de revenus :

| Division | Revenus/mois | Salaires/mois | Ratio |
|---|---|---|---|
| L1 | 188 587 € | 65 200 € | 2,89 |
| L2 | 147 323 € | 38 000 € | 3,88 |
| L3 | 112 903 € | 25 400 € | 4,45 |
| L4 | 85 956 € | 20 900 € | 4,11 |
| L5 | 62 238 € | 14 600 € | 4,26 |
| L6 | 41 830 € | 14 400 € | 2,90 |

- Tous les clubs sont **bénéficiaires** : le système est viable dans les six
  divisions, avec une marge plus confortable en bas de pyramide (elle finance
  les chantiers et la montée).
- **Plancher salarial** relevé de 400 € à **1 200 €/mois** : les masses
  salariales de L5/L6 redeviennent réalistes (ratio ramené de ~7,2 à ~2,9).

### RÉÉQUILIBRAGE DES SAUVEGARDES EXISTANTES
- Migration `salary_balance_v1` : tout contrat payé **plus de 1,7× sa valeur
  sportive** est ramené à **1,6×**. Sur la sauvegarde de test :
  masse salariale **670 672 € → 324 872 €**, solde mensuel
  **−271 707 € → +75 517 €** (santé « SAINE »).
- Les nouvelles demandes restent plafonnées (annexe AX), donc la dérive ne
  peut plus se reproduire.

### VALIDATION
- Onglets Finance : santé « SAINE +66 338 €/mois », 3 offres sponsors,
  résumé de prêt cohérent, dette affichée.
- Sauvegarde réelle : santé « SAINE +75 517 €/mois » après migration.
- run_tests.py 10/10 ALL OK ; error.log 0 octet.


---

## Annexe BB — Retraites, offres périmées et fin de carrière

### PLUS D'OFFRE SUR UN JOUEUR PARTI
- Une offre reçue pour un joueur **libéré** (ou retraité) restait active dans
  l'onglet OFFRES et pouvait encore être acceptée.
- Correctifs :
  - `process_contract_expiries()` et les retraites appellent
    **`cancel_player_offers()`** : toute offre en cours sur le joueur passe en
    `handled` / `unavailable` ;
  - l'acceptation d'une vente vérifie que le joueur est **toujours au club,
    sous contrat et non retraité** ;
  - l'onglet OFFRES affiche « **JOUEUR PARTI • DOSSIER CLOS** » pour ces
    dossiers et ne les compte plus comme actifs ;
  - `generate_transfer_interest()` ne cible plus que les joueurs **listés,
    sous contrat et actifs**.

### RETRAITES
- Nouvelles colonnes `retired` / `retired_date` (migration automatique).
- `process_retirements()` à chaque clôture de saison : à partir de **31 ans**,
  probabilité croissante (31-32 : 4-6 %, 33-34 : 12-16 %, 35-36 : 30-38 %,
  37-38 : 55-62 %, 39+ : 85 %, **40 ans : retraite automatique**).
- Le retraité quitte l'effectif (`club_id=0`, salaire 0, contrat 0), entre dans
  l'historique (`retraite — Fin de carrière`) et disparaît du marché.
- News + message « Retraites au club » pour les joueurs du manager.

### FICHE JOUEUR
- Le nom affiche « **• RETRAITÉ** » et la fiche présente un bandeau doré
  « JOUEUR RETRAITÉ • aucun contrat ni transfert possible » — les boutons de
  contrat, de mise sur le marché et de licenciement sont remplacés.
- Le club affiché devient « RETRAITÉ ».

### VÉTÉRANS : PRÉTENTIONS PLUS DOUCES
- `compute_fair_salary()` accentue la décote d'âge : ×1,00 jusqu'à 30 ans,
  ×0,85 (31-32), ×0,70 (33-34), ×0,58 (35-36), ×0,45 au-delà.
- Exemple (niveau 15, Ligue 3) : **3 500 €/mois à 28 ans → 2 000 € à 36 ans
  → 1 700 € à 38 ans**. Les petits clubs peuvent les recruter pour finir leur
  carrière, avec un contrat d'un an (durée demandée selon l'âge).

### VALIDATION
- Retraite forcée (40 ans) : `retired=1`, club 0, hors effectif.
- Offre sur un joueur libéré : message `handled/unavailable`, ligne
  « JOUEUR PARTI • DOSSIER CLOS ».
- Fiche retraité : bandeau doré, aucun bouton de contrat.
- run_tests.py 10/10 ALL OK ; error.log 0 octet.


---

## Annexe BC — Maillot dans l'en-tête et écussons premium

### MAILLOT À CÔTÉ DE L'ÉCUSSON (EN HAUT)
- L'en-tête global affiche désormais l'**écusson ET le maillot du club**
  côte à côte (62 px chacun), dans le cadre lumineux du club.
- Le maillot suit les couleurs et le motif du club (`kit_pixmap` +
  `kit_pattern_for`) et se met à jour avec l'écusson à chaque `refresh_all`.

### ÉCUSSONS PLUS BEAUX, PARTOUT
- `paint_crest()` enrichi :
  - **médaillon central** derrière les initiales, avec contraste automatique
    (plaque claire + lettres sombres sur écusson clair, plaque sombre +
    lettres blanches sur écusson sombre) ;
  - **anneau extérieur métallique** en dégradé argent + liseré sombre intérieur ;
  - halo bombé en haut, reflet diagonal, bande basse plus dense, liseré
    intérieur ;
  - ombre portée renforcée.
- Comme `draw_badge()` et l'aperçu de création passent tous par ce moteur, la
  mise à niveau est **globale** : en-tête, classements, fiches club, rapports,
  sélection de sauvegarde, messagerie, etc., pour **tous les clubs**.
- Lisible de 24 à 108 px (médaillon et anneau adaptés à la taille).

### VALIDATION
- Capture de l'en-tête : écusson orange/medaillon + maillot orange/noir côte
  à côte, pixmap non nul, hauteur 100 px conservée.
- Planche d'écussons : 5 formes × 6 couleurs, contraste correct sur les
  écussons clairs comme sombres.
- run_tests.py 10/10 ALL OK ; error.log 0 octet.


---

## Annexe BD — Infrastructure immersive

### VUE INTÉRIEURE (`FacilityArenaView`)
- Tribunes aux **couleurs du club**, sièges occupés/vides, escaliers, vomitoires
  et sections lettrées (déjà en place), désormais éclairées par :
  - **quatre halos de projecteurs** aux coins du terrain (mode additif) ;
  - une **vignette** douce qui donne du relief à la salle ;
  - un **tableau de score suspendu** au-dessus de la tribune haute, aux couleurs
    du club, affichant `affluence / capacité` ;
  - une étiquette **TUNNEL** au centre de la tribune basse.
- Bandes LED périphériques, loge VIP, bancs, table de marque et éclairage de
  plafond conservés.

### VUE EXTÉRIEURE (`FacilityCampusView`)
- **Parquet de futsal** (dégradé bois + bandes + liseré club) à la place du
  rectangle aux couleurs du club.
- **Allée d'entrée** reliant le hall à la voirie, avec passages piétons.
- **Arbres** le long du site et **parking avec voitures** dès le niveau 2.
- **Projecteurs** aux quatre coins du hall (halos + points lumineux).
- **Auvent d'entrée** aux couleurs du club.
- Terrain d'entraînement, pôle médical, services et rivière conservés.

### GESTION (évolutions)
- Cartes redessinées : fond en dégradé, **badge d'icône radial** à la couleur de
  la catégorie, **pastilles de niveau** (8 points, remplis selon le niveau),
  pastille « NIV. x / 8 » / « À BÂTIR », statut détaillé et **bouton bordé**
  de la couleur de la catégorie, avec survol éclairci.
- Les garde-fous existants (chantier en cours, budget, centre fermé) restent
  inchangés.

### VALIDATION
- Captures : intérieur (scoreboard, projecteurs, vignette), extérieur (parquet,
  allée, arbres, parking, projecteurs, auvent), gestion (cartes).
- run_tests.py 10/10 ALL OK ; error.log 0 octet.


---

## Annexe BE — Gestion de l'infrastructure réorganisée

### HÉROS « PLAN DE DÉVELOPPEMENT »
- Bandeau dédié en haut de l'onglet GESTION : icône complexe, titre, sous-titre
  **dynamique** (« n améliorations possibles • x/y chantiers • niveau moyen
  z/8 ») et deux compteurs : **BUDGET** et **CHANTIERS** (en cours / places).

### SECTIONS CLAIRES
Trois bandeaux de section colorés, avec icône et description :
- **BÂTIMENTS DU COMPLEXE** (vert) — tribunes, médical, formation, éclairage,
  parking, marketing ;
- **SERVICES SUPPORTERS** (cyan) — bar, loge VIP, boutique ;
- **REVENUS HORS MATCH** (or) — terrains locatifs, salle d'événements,
  fan zone.
- Le panneau du centre de formation reste au-dessus des cartes bâtiments.

### CARTES EN DEUX COLONNES
- Les cartes passent en **grille 2 colonnes** (au lieu d'une longue liste) :
  page plus courte, lecture par blocs.
- Chaque carte conserve son badge d'icône radial, ses **8 pastilles de niveau**,
  sa pastille « NIV. x / 8 » / « À BÂTIR », son statut détaillé et son bouton
  bordé à la couleur de la catégorie, avec survol éclairci.

### VALIDATION
- Capture : héros + 3 sections + cartes sur 2 colonnes, compteurs budget et
  chantiers renseignés.
- run_tests.py 10/10 ALL OK ; error.log 0 octet.


---

## Annexe BF — Icônes et vues d'infrastructure

### NOUVELLES ICÔNES DÉDIÉES (vectorielles)
- Tribunes (gradins), projecteur (éclairage), parking (P), chapeau de formation,
  verre (bar), étoile (loge VIP), sac (boutique), drapeau (fan zone),
  calendrier (événements), croix médicale, mégaphone (marketing), terrain.
- Mappées sur les cartes de GESTION **et** sur les bandeaux de section
  (bâtiments = gradins, services = verre, revenus = drapeau).
- Plus aucune icône générique ou emoji dans la page.

### VUE INTÉRIEURE PLUS RÉELLE
- **Ombre portée sous le terrain** pour le détacher du sol.
- **Poutres de toit** légères et **luminaires suspendus** avec halo (7 points
  lumineux au-dessus du terrain).
- **Chantier** : ruban de sécurité jaune pointillé autour de la salle et
  **barre de progression** (pourcentage + jours restants) sous le titre ;
  l'ancien texte central redondant est supprimé.
- Écusson, scoreboard, LEDs, loge VIP, bancs et tunnel conservés.

### VUE EXTÉRIEURE PLUS RÉELLE
- **Verrières et caissons de ventilation** sur le toit du hall.
- **Clôture** pointillée autour du site.
- **Chantier** : **grue** (mât, flèche, contrepoids, câble) contenue dans le
  site, **échafaudage** le long de la façade et **barre de progression**
  sous l'en-tête.
- Déjà en place : parquet bois, allée d'entrée, arbres, parking avec voitures,
  projecteurs d'angle, auvent aux couleurs du club.

### VALIDATION
- Captures : intérieur (scoreboard, LEDs, chantier), extérieur (toit, grue,
  échafaudage, barre), gestion (nouvelles icônes + sections + 2 colonnes).
- run_tests.py 10/10 ALL OK ; error.log 0 octet.


---

## Annexe BG — Vue extérieure : ratio et rendu

### PROBLÈME
- La vue extérieure utilisait toute la surface du widget : sur un panneau large,
  le hall et le terrain étaient **écrasés** (hall ~2,4:1, terrain ~4:1).

### CORRECTIFS
- **Cadre de dessin à ratio fixe 2,1:1**, centré dans le widget : la scène garde
  ses proportions quelle que soit la taille de la fenêtre (fini l'écrasement).
- **Hall proportionné** : largeur/hauteur verrouillées à **1,6:1** (et réduites
  ensemble si la hauteur manque) ; le terrain intérieur passe de ~4:1 à ~2,2:1.
- En-tête aligné sur la largeur du site, marge haute réservée.
- Site : **vignette** douce, liseré, ombre du hall renforcée et **liseré club**
  sur le pourtour du bâtiment.
- Parcelles : fond vert uni arrondi au lieu d'un simple rectangle pointillé.
- Conservés : parquet bois, allée d'entrée, arbres, parking avec voitures,
  projecteurs d'angle, auvent club, verrières/ventilation, grue, échafaudage et
  barre de progression du chantier.

### VALIDATION
- Capture 1222 × 520 : site 983 × 468, hall ≈ 347 × 215, terrain ≈ 230 × 104 —
  proportions stables, plus de tassement.
- run_tests.py 10/10 ALL OK ; error.log 0 octet.


---

## Annexe BH — Gestion infrastructure : explications et teintes douces

### PANNEAU ACADÉMIE RETIRÉ
- Le bloc « CENTRE DE FORMATION • LA MACHINE À TALENTS DU CLUB » a été retiré de
  la page Infrastructure → GESTION (le centre garde sa page dédiée).
- Aucun impact sur les investissements : les cartes BÂTIMENTS conservent la
  ligne « Centre de formation ».

### COULEURS ADOUCIES
- Palette des icônes et des accents remplacée par des tons désaturés :
  vert sauge, cyan ardoise, lavande douce, ocre, or pâle, bleu gris.
- Fond des badges d'icônes moins lumineux (alpha 0x38 au lieu de 0x55) et
  bandeaux de section aux mêmes teintes feutrées.

### EXPLICATIONS ET RATIOS
- Nouveau texte sous le héros : « Comment ça marche » (coût → chantier →
  effet à la livraison, un chantier par bâtiment, +1 place par architecte).
- Chaque carte affiche désormais :
  - la **description** du bâtiment (auparavant seulement en infobulle) ;
  - une **ligne d'effet** « niveau actuel → niveau suivant » :
    - Tribunes : `Capacité 4 010 → 4 9xx places` ;
    - Éclairage : `Affluence +3,6 % → +4,8 % • diffusion dès niv. 2` ;
    - Parking : `Stationnement : n → n+1 niveaux` ;
    - Médical : `Risque de blessure −0,3 % → −0,4 % • soins +15 % → +20 %` ;
    - Formation : `Qualité d'atelier +8 → +10 • bonus jeunes +30 % → +40 %` ;
    - Marketing : `Attractivité +5,4 % → +7,2 %` ;
    - Services / revenus : recette par spectateur ou montant hebdomadaire.
  - le **statut** (coût, durée, financement) et le bouton d'action.

### VALIDATION
- Capture : académie absente, 3 sections, cartes avec description + effet + statut,
  deux colonnes, teintes douces.
- run_tests.py 10/10 ALL OK ; error.log 0 octet.


---

## Annexe BI — Page Tactiques et restauration du code

### PAGE TACTIQUES
- **Réglages rangés** : ligne des styles (presets), puis grille propre
  `SYSTÈME / MENTALITÉ / RYTHME` sur trois colonnes, lecture
  compatibilité/risque/contrôle en dessous, bouton « RÉGLAGES AVANCÉS »
  à droite et message de retour en bas. Fini l'empilement de widgets sur une
  seule ligne.
- **Terrain plus petit** : hauteur plafonnée à 390 px (min 280), marges
  réduites ; le splitter passe en 2:1 (terrain / banc).
- **Lecture du plan sous le terrain** : les trois phases (avec ballon,
  transition, sans ballon) sont désormais juste sous le terrain.
- **Zones de joueurs redessinées** : tuile avec **maillot du club**, numéro,
  poste, nom (élidé), note /20 et forme ; bordure colorée selon la note/le
  statut ; état vide en pointillés « + DÉPOSER ». Le clic ouvre la fiche,
  le glisser-déposer reste actif.
- **Banc** : tous les joueurs disponibles ont maintenant leur **avatar**
  (maillot + numéro), lignes de 64 px, en plus des blessés/suspendus grisés.

### INCIDENT ET RESTAURATION
- Un remplacement de bloc destiné aux réglages tactiques a matché un
  `row2` situé dans `_search_page` et supprimé ~2 249 lignes
  (`page_shell`, `_dashboard`, `_roster`, `show_club_profile`,
  `add_club_standing_card`, helpers et début de `_tactics`).
- **Restauration** depuis la sauvegarde `app.pre-clean.py` du 27/10 :
  méthodes réinjectées, puis réapplication des correctifs du jour
  (filtre `is_free_agent` sur la fiche club, `_fit_roster_columns`, nouvelle
  page Tactiques).
- Le fichier corrompu est conservé (`app.py.corrupt.bak`) et une sauvegarde
  saine a été créée dans `code_backups/backup_*_known_good_tactics/`.
- Vérifications : démarrage, Direction sportive, Effectif, Fiche club,
  Tactiques se construisent et s'affichent.

### VALIDATION
- Captures : dashboard, effectif, fiche club, tactiques (kit sur les zones,
  avatars sur le banc, réglages en grille, terrain réduit).
- run_tests.py 10/10 ALL OK ; error.log 0 octet.


---

## Annexe BJ — Page Transferts : historique, contrats internes et badge

### HISTORIQUE DES TRANSFERTS (performance)
- **Reconstruction LAZY fiable** : hors onglet HISTORIQUE, un rafraîchissement
  ne pose plus que le drapeau `_transfer_history_dirty` ; la construction se
  déclenche à l'ouverture de l'onglet, via `QTimer.singleShot(0, ...)`, donc
  la bascule d'onglet rend la main immédiatement.
- **Plus de reconstruction inutile** : si le tableau est déjà construit et
  propre, l'appel est ignoré.
- **Build allégé** : `setUpdatesEnabled(False)` pendant le remplissage,
  `fee_map` (label + date) au lieu d'une double boucle sur `finance_tx`,
  suppression des `setRowHeight` ligne par ligne (hauteur par défaut posée à
  la création).
- **Index SQL ajoutés** : `idx_history_kind` sur `player_history(kind, club_id,
  season)` et `idx_history_date` sur `player_history(created_at)`.
- **Robustesse** : les drapeaux ne sont validés qu'après un build réussi ; en
  cas d'exception, l'historique reste marqué à reconstruire.
- Mesure de contrôle : reconstruction complète 250 lignes ≈ **35 ms**,
  rappel immédiat ≈ 0 ms, bascule d'onglet ≈ 45 ms (Qt + build).

### BANDEAU DE SYNTHÈSE (immersion)
- Sous le filtre de période : nombre d'**arrivées**, de **départs**,
  **dépenses**, **recettes** et **solde** coloré (vert / rouge), calculés sur
  la période affichée. Message dédié quand aucun mouvement n'existe.

### CONTRATS INTERNES DANS L'ONGLET OFFRES
- Nouveau bloc **« CONTRATS INTERNES : n DOSSIER(S) EN COURS »** entre les
  achats et les ventes, avec compteur, phrase d'aide et tableau dédié :
  `STATUT / JOUEUR / POSTE / SALAIRE PROPOSÉ / DURÉE / ÉCHÉANCE`.
- Statuts explicites : *EN ATTENTE DE RÉPONSE*, *CONTRE-PROPOSITION DE
  L'AGENT*, *ACCORD • À CONFIRMER*, *REFUS • DOSSIER MORT*, *DOSSIER CLOS*.
- **Décision prise depuis la page** : sélection d'une ligne puis ACCEPTER /
  REFUSER / CONTRE-OFFRE (les contrats internes étaient auparavant renvoyés
  vers la messagerie). Le bouton principal devient **« SIGNER LE CONTRAT »**
  (ou « SIGNER LE JOUEUR » pour un joueur libre).
- **Redirection après une offre** : `open_contract_offers_tab()` ouvre la page
  Transferts sur OFFRES, rafraîchit et sélectionne la ligne du joueur concerné
  (y compris quand une négociation est déjà en cours).
- Le tableau s'ajuste au nombre de lignes (42 à 190 px) et disparaît au profit
  d'un message d'aide quand aucun dossier n'est en cours.

### ÉTATS VIDES ET LISIBILITÉ
- Achats et ventes ont désormais leurs messages d'état vide ; les tableaux
  vides sont masqués pour laisser la place aux sections actives.
- Échéances affichées au format français (`jj/mm/aaaa`) dans les trois
  tableaux, au lieu de la date ISO.
- Confirmation de signature dédiée : « Contrat signé — X an(s) à Y €/mois ».
  L'issue (`outcome`, salaire et durée finaux) est persistée dans
  `action_data` pour que le dossier reste correctement classé.

### BADGE TRANSFERTS
- Le badge de navigation ne compte plus les `contract_offer` (renouvellements
  internes) : plus d'alerte déclenchée par une simple offre de contrat à un
  joueur de son propre club. Il conserve `market_offer`, `transfer_sale`,
  `transfer_sale_counter` et `free_agent_contract`.
- Le suivi des renouvellements se fait désormais dans l'onglet OFFRES et dans
  le sous-titre du bandeau (`n prolongation(s)`).

### VALIDATION
- Sonde dédiée : 4 contrats internes (accord, attente, contre-proposition),
  badge à 0, acceptation depuis la page (salaire et durée mis à jour, message
  classé, ligne retirée), historique 250 lignes en ~35 ms.
- `tests/run_tests.py` : **10/10 ALL OK** ; `data/error.log` : 0 octet.
- Sauvegarde saine : `code_backups/backup_*_known_good_transfers/`.


---

## Annexe BK — Offres reçues actionnables et durée de contrat

### OFFRES REÇUES / SPONTANÉES : DÉCISION IMMÉDIATE
- **Cause** : les offres d'achat (`transfer_sale`) étaient créées au statut
  `waiting` (« le club prépare une offre ») pendant 1 à 3 jours. Dans l'onglet
  OFFRES, un dossier `waiting` désactivait ACCEPTER / REFUSER / CONTRE-OFFRE :
  le manager voyait l'offre sans pouvoir agir.
- `queue_manager_message()` accepte désormais un paramètre `ready=True`.
- Les offres reçues (joueur listé) et les **offres spontanées** sont créées
  **directement prêtes**, avec une **échéance de décision de 2 à 4 jours** ;
  titre explicite (« Offre reçue • <club> », « Offre spontanée • <club> »).
- Le statut affiché devient **« DÉCISION ATTENDUE • À TOI DE JOUER »** (fini le
  renvoi systématique vers la messagerie).

### REFUS SUR UN DOSSIER ENCORE EN PRÉPARATION
- Les anciens dossiers `waiting` (sauvegardes existantes) restent refusables :
  REFUSER est actif dès qu'un dossier existe, même sans réponse formelle.
- `_offer_action("reject")` court-circuite la messagerie pour ces dossiers :
  classement immédiat, message « Dossier écarté ».
- ACCEPTER / CONTRE-OFFRE restent réservés aux dossiers `ready`.

### SÉLECTION ET ACTIONS
- `_current_offer_id()` retrouve le dossier sélectionné même si le refresh a
  nettoyé l'identifiant interne (sélection conservée par le modèle Qt) : plus de
  « Sélectionne un dossier » alors qu'une ligne est visiblement sélectionnée.
- `_fill()` vide la sélection avant de remplir : l'état des boutons ne reste
  plus bloqué sur un dossier traité.
- Les trois tableaux (achats, contrats internes, ventes) partagent la même
  logique d'action directe ; états vides compacts.

### DURÉE DE CONTRAT : ELLE REMPLACE, ELLE NE S'AJOUTE PAS
- **Cause** : pour une prolongation, l'agent imposait sa durée de sécurité
  (`contract_demand_years` : 2 ans pour un joueur de 25-30 ans). Proposer 1 an
  à un joueur ayant 1 an restant déclenchait donc une contre-offre à 2 ans,
  puis la signature appliquait 2 ans : le contrat semblait s'ajouter.
- Désormais, pour un **renouvellement interne** (`contract_offer`), la durée
  proposée par le manager **fait foi** : l'agent ne négocie plus que le salaire.
  La durée minimale exigée ne subsiste que pour les **joueurs libres**.
- Le nouveau contrat **remplace** l'ancien (`contract_years = durée proposée`).
- Le tableau CONTRATS INTERNES affiche les termes qui seront réellement signés :
  salaire et durée de la contre-proposition de l'agent, ou termes définitifs
  d'un accord, au lieu de toujours montrer l'offre initiale.
- Le dialogue de renouvellement affiche une phrase dynamique :
  « Nouveau contrat : 1 an(s). Il REMPLACE le contrat actuel (1 an(s)
  restant(s)) : la durée ne s'y ajoute pas. »
- Enchaînement vérifié : joueur à 1 an, offre 1 an → contre-proposition
  salariale uniquement → signature à **1 an**, pas 2.

### VALIDATION
- Sondes : offre reçue créée prête (échéance 2-4 jours), refus/contre-offre
  depuis la page, acceptation réelle (joueur transféré, budget crédité),
  refus d'un dossier `waiting`, renouvellement 1 an → 1 an signé.
- `tests/run_tests.py` : **10/10 ALL OK** ; `data/error.log` : 0 octet.
- Sauvegarde saine : `code_backups/backup_*_known_good_offers/`.


---

## Annexe BL — Sélection persistante dans l'onglet OFFRES

- **Symptôme corrigé** : après un rafraîchissement (ou l'ouverture de la page
  depuis une négociation), une ligne pouvait rester visuellement sélectionnée
  alors que l'identifiant interne était perdu : REFUSER / ACCEPTER /
  CONTRE-OFFRE semblaient morts, ou répondaient « Sélectionne un dossier ».
- `_fill()` remet explicitement la cellule courante à `(-1, -1)` : la sélection
  suivante émet toujours un vrai signal.
- `_offer_selection_changed()` accepte un tableau explicite, ce qui permet de
  l'appliquer hors signal (ouverture automatique d'un dossier).
- `_refresh_offers_tab()` mémorise le dossier sélectionné (`_current_offer_id`),
  remet les boutons à neutre puis **restaure la ligne** par identifiant si elle
  est toujours à l'écran ; les `QTimer.singleShot` de rafraîchissement ne
  cassent donc plus une sélection en cours.
- Validation : ouverture d'un contrat interne depuis une négociation →
  ligne sélectionnée, bouton « SIGNER LE CONTRAT » actif, signature effective
  en une action ; 10/10 tests OK ; error.log 0 octet.


---

## Annexe BM — Page Tactiques : terrain 2:1, banc riche et trié

### TERRAIN : PLUS DÉFORMÉ NI ÉCRASÉ
- **Cause** : le terrain (`FutsalCourt`) était étiré par un `QGridLayout`
  occupant tout le widget ; dès que le panneau changeait de proportions, les
  lignes du terrain et les tuiles se déformaient, et les cinq zones (3 lignes
  × 5 colonnes, largeur minimale 136 px) débordaient du panneau.
- **Nouveau moteur** : `TacticalBoard` (dans `ui_components.py`) peint le
  terrain dans un **rectangle 2:1 centré** (`court_rect()`), quelle que soit la
  taille du widget.
- Les **zones sont des enfants positionnés en coordonnées relatives** au
  terrain (`COL_X` / `ROW_Y`), redimensionnées à chaque `resizeEvent` : elles
  restent toujours à l'intérieur du tracé (vérifié : ratio 2,00 et zones
  contenues à 1600×1000 comme à 1280×820).
- Les formations (`3-1`, `4-0`, `2-2`, `1-2-1`, `1-1-2`, gardien volant)
  réordonnent les zones par `set_positions()` ; plus de `removeWidget` /
  `addWidget` sur une grille.
- `heightForWidth()` donne au terrain une hauteur cohérente avec sa largeur,
  plafonnée à 430 px : moins de bandes vertes inutiles.

### BANC : PLUS D'INFOS, TRI ET RECHERCHE
- Chaque joueur disponible affiche deux lignes :
  `#numéro  Prénom Nom  •  note/20`, puis
  `Poste · âge · forme · contrat` (+ `FIN DE CONTRAT` / `LISTÉ` si applicable).
- Couleur du nom selon le niveau (vert ≥ 15, jaune ≥ 12, neutre sinon).
- **Infobulle complète** : poste, âge, note + étoiles, forme, moral, contrat,
  salaire mensuel, rappel glisser-déposer / double-clic.
- **Tri** : NOTE (défaut), POSTE, NOM, FORME, ÂGE, CONTRAT, SALAIRE — le tri
  s'applique aux disponibles puis aux indisponibles.
- **Recherche** par nom ou poste, avec bouton d'effacement.
- Les blessés/suspendus restent visibles, grisés, en fin de liste.
- Aperçu bas de panneau enrichi (poste, âge, note, étoiles, contrat, technique,
  défense, finition, salaire) et libellés **élidés** : l'aperçu ne mange plus la
  moitié du banc.

### FIN DES TEXTES QUI DÉBORDENT
- Nouveau `ElidedLabel` (ui_components) : coupe le texte avec « … », garde le
  texte complet en infobulle, se réévalue au redimensionnement.
- Utilisé pour la description du préréglage, les trois cartes de phase
  (avec/sans ballon, transition) et l'aperçu du banc.
- Le message de retour tactique passe en multi-lignes.
- Libellé de direction corrigé (`◀ DÉFENSE • ATTAQUE ▶`, l'ancien caractère
  était corrompu) ; largeur du banc garantie (340 px mini) et splitter 3:2.

### VALIDATION
- Sondes : ratio du terrain 2,00 à toutes les tailles, zones dans le tracé,
  repositionnement sur changement de formation, drop sur une zone, tri POSTE et
  recherche « gard » (1 résultat), compteurs terrain/banc cohérents.
- `tests/run_tests.py` : **10/10 ALL OK** ; `data/error.log` : 0 octet.
- Sauvegarde saine : `code_backups/backup_*_known_good_tactics2/`.


---

## Annexe BN — Tuiles de terrain lisibles et banc en cartes

### TUILES DU TERRAIN (textes incomplets / superposés)
- `PitchZone.paintEvent` entièrement réécrit avec des **zones de texte
  mesurées** (`QFontMetrics`) : plus de coordonnées devinées.
- Colonne gauche : maillot (30-40 px) + numéro ; colonne droite : poste
  (8 px, élidé), nom (10 px gras, élidé), puis **note en évidence** (`19.1`),
  `/20` discret et forme (`F17`) sur la même ligne.
- Chaque texte est **élidé à la largeur réellement disponible** ; la forme est
  masquée si la place manque (plus jamais de texte coupé net).
- Liseré coloré à gauche selon la note / le statut, fond en dégradé, bordure
  éclaircie au survol, état vide en pointillés « + DÉPOSER ».
- Tuiles légèrement agrandies (116-190 × 58-82) et colonnes recalées
  (`COL_X` 0,155 → 0,845) pour ne plus mordre sur la ligne de touche.

### BANC : CARTES PREMIUM ET TRI VISIBLE
- Nouveau `BenchItemDelegate` (ui_components) : chaque joueur est une **carte**
  avec avatar 38 px, numéro superposé, nom, ligne d'infos
  (`Poste · âge · contrat`), **pastille de note** colorée à droite (vert ≥ 15,
  jaune ≥ 12, neutre sinon) et forme juste en dessous.
- Drapeaux `FIN DE CONTRAT` / `LISTÉ` / blessure sur une 3e ligne colorée.
- Fonds, bordures et liseré violet sur la carte sélectionnée ; survol éclairci.
- Sélecteur de tri renommé et explicite : `TRI` puis `NOTE ↓`, `POSTE`,
  `NOM A→Z`, `FORME ↓`, `ÂGE ↑`, `CONTRAT ↑`, `SALAIRE ↓`.
- Compteur raccourci en `5/5 TITULAIRES` (il était tronqué à côté de
  « ENREGISTRER ») et largeur autorisée portée à 150 px.

### VALIDATION
- Sondes : ratio du terrain 2,00, 5 tuiles dans le tracé (180×77), formations
  repositionnées, drop, tri/recherche ; captures à 1600 et 1280 px.
- `tests/run_tests.py` : **10/10 ALL OK** ; `data/error.log` : 0 octet.
- Sauvegarde saine : `code_backups/backup_*_known_good_tactics3/`.


---

## Annexe BO — Tuiles du terrain compactes (plus de chevauchement)

- **Cause** : les colonnes du terrain étaient espacées de 0,17 à 0,18 de la
  largeur du terrain, alors que les tuiles mesuraient jusqu'à 190 px
  (0,25 de la largeur). Le gardien et le défenseur se recouvraient donc de
  ~30 px sur un terrain large.
- **Colonnes rééquilibrées** : `COL_X = 0.115 / 0.305 / 0.500 / 0.695 / 0.885`
  (écart minimal 0,19 de la largeur).
- **Tuile dimensionnée sur l'écart** : largeur
  `min(146, max(84, 16 % de la largeur du terrain))`, hauteur
  `min(70, max(50, 18,5 % de la hauteur))`. Sur un terrain de 720 px :
  115×66 px au lieu de 190×82.
- **Contenu resserré** : maillot 26-32 px, marges réduites, poste 7 px,
  nom 9 px, note 9 px — tous les textes restent élidés.
- **Vérification automatique** : les 6 formations × 3 tailles de fenêtre
  (1600, 1280, 1100) ne présentent **aucun chevauchement** ; l'écart
  gardien → défenseur est de 22 px sur un grand écran, 16 px en 1280, 3 px au
  minimum. Les tuiles restent entièrement dans le tracé 2:1.
- `tests/run_tests.py` : **10/10 ALL OK** ; `data/error.log` : 0 octet.
- Sauvegarde saine : `code_backups/backup_*_known_good_tactics4/`.


---

## Annexe BP — Performance, audit UI, découpage et tests moteur

### PERFORMANCE (mesures hors écran, 1600×1000)
| Page | Avant | Après |
|---|---|---|
| Effectif | 712 ms | **66-88 ms** |
| Transferts | 578 ms | **97-126 ms** |
| Recherche | 527 ms | **270-313 ms** |
| Classement | 260 ms | **106-109 ms** |
| `refresh_all` | 152-160 ms | **62-70 ms** |

- **Effectif** : `_fit_roster_columns` passait les 21 colonnes en
  `ResizeToContents`, donc Qt recalculait toutes les largeurs à **chaque
  repeint**. Largeurs fixes + colonne joueur étirée : plus de recalcul.
- **Mercato** : même piège (12 colonnes `ResizeToContents`) + `setRowHeight`
  par ligne. Colonnes fixes, hauteur de ligne globale.
- **Rafraîchissements lourds conditionnés à la page visible** : centre
  d'entraînement, infrastructure, académie, classement autonome, scouting et
  shortlist ne se reconstruisent plus quand leur page est hors écran. Fin des
  doubles constructions (show_page + refresh_all).
- **Recherche** : 60 résultats affichés au lieu de 80 (moins de widgets).
- Libellés serrés raccourcis (barre d'actions OFFRES, compteurs achats/ventes/
  contrats) pour éviter les textes coupés.

### AUDIT UI
- **10 icônes/emojis corrompus** (caractères de remplacement dans les titres
  Recherche, Direction sportive, trophées, records, salle) remplacés par des
  symboles valides ; la quote cassée « TOUT LE FOOTBALL » est corrigée.
- Scan automatique des 14 pages : **0 texte « None » / « nan » / caractère
  cassé** dans les libellés, tableaux, listes et boutons.
- Les faux positifs restants du scan de débordement concernent des onglets non
  affichés (géométrie non calculée), pas des textes visibles.

### DÉCOUPAGE
- Nouveau module **`game_utils.py`** : helpers purs partagés (`parse_iso`,
  `fmt_date_fr`, `fmt_match_time`, `iso_today`, `rating20`, `stars5`,
  `round_money`, `format_euros`). Aucun accès base/UI, testables seuls.
- `app.py` les importe : les 37 000 lignes restantes peuvent être découpées
  progressivement sans casser les tests (`import app` expose toujours les
  mêmes noms).

### TESTS MOTEUR / DURÉE DE VIE (`soak_test.py`)
- Carrière simulée **420 jours** (plus d'une saison complète + début de la
  suivante) : **0 erreur**, passage en **saison 2** réussi.
- 30 matchs du club joués, 270 matchs au total : **4,4 buts/match** ;
  budget 1,95 M€ → 3,20 M€ ; 28 retraites traitées ; 59 messages actifs.
- 120 jours : 8 matchs joués, 240 matchs simulés, 4,3 buts/match, 0 erreur.
- Coût moyen : **~210 ms par jour simulé** (dont matchs), stable.
- Le moteur de match en direct (`start_match`/`step_match_minute`) dépend des
  interactions d'écran (mi-temps, reprise) ; la simulation complète
  (`finish_match_now`) sert de test d'endurance du moteur de résultat.

### VALIDATION
- `tests/run_tests.py` : **10/10 ALL OK** ; `data/error.log` : 0 octet.
- Sauvegarde saine : `code_backups/backup_*_known_good_perf/`.


---

## Annexe BQ — Moteur de match en direct : test de bout en bout

- Match joué **minute par minute** via `start_match()` / `step_match_minute()`,
  avec reprise de la seconde période (`resume_second_half()`).
- Résultat du test : **121 pas de simulation**, chrono jusqu'à **40:00**, coup
  de sifflet final automatique (`finished=True`, phase « COUP DE SIFFLET
  FINAL »).
- Score **3–1**, 4 buts détaillés (minute, seconde, équipe, buteur, type),
  `player_goals` cohérent, mi-temps gérée (1–0 à la pause).
- Aucun crash ni exception ; le rapport de match se construit correctement
  (`build_match_report` : mi-temps, tirs, issue).
- À noter pour les futurs tests headless : la mi-temps **bloque volontairement**
  le chrono tant que `resume_second_half()` n'est pas appelé, et le match se
  termine au pas suivant 40:00.

### BILAN MOTEUR / DURÉE DE VIE
- 420 jours simulés : 0 erreur, passage en saison 2, 270 matchs, 4,4 buts/match.
- Match en direct : 40 minutes, buteurs et rapport complets.
- `tests/run_tests.py` : **10/10 ALL OK** ; `data/error.log` : 0 octet.


---

## Annexe BR — Découpage des widgets tactiques et audit visuel

### DÉCOUPAGE
- **`PitchZone`** et **`DraggableBench`** (195 lignes) quittent `app.py` pour
  `ui_components.py`, où vivent déjà `TacticalBoard`, `ElidedLabel` et
  `BenchItemDelegate`.
- `ui_components` importe désormais `Signal` et `QMimeData` (QtCore) ; `app.py`
  les réimporte (`from ui_components import ... PitchZone, DraggableBench`) :
  tous les usages existants et les tests restent compatibles.
- `app.py` : ~1 526 000 octets (contre ~1 535 000), sans changement de
  comportement. Les modules déjà séparés (`db`, `theme`, `model`,
  `calendar_service`, `league_table`, `logo_data`, `game_utils`) forment
  désormais un socle clair ; la suite du découpage peut se poursuivre
  composant par composant.

### AUDIT VISUEL (14 pages, 1584×862)
- Captures enregistrées pour chaque page : Direction, Effectif, Tactiques,
  Match, Entraînement, Infrastructure, Messages, Transferts, Calendrier,
  Finances, Staff, Classement, Recherche, Académie.
- **0 bouton coupé** (aucun dépassement du parent), **0 débordement
  horizontal** dans les zones défilantes, **0 texte « None » / « nan » /
  caractère cassé**.
- Les seuls artefacts des captures sont les glyphes manquants du rendu
  hors écran (police absente), pas des défauts de l'application.

### PERFORMANCES (contrôle après découpage)
- `refresh_all` : **76 ms** ; Effectif **88-95 ms** ; Transferts **124-176 ms** ;
  la majorité des pages reste sous **150 ms**.
- La Recherche reste la plus lourde (305-359 ms) à cause de ses 60 cartes
  joueurs construites à la volée ; piste suivante : réutiliser les widgets ou
  passer en tableau.

### VALIDATION
- `tests/run_tests.py` : **10/10 ALL OK** ; `data/error.log` : 0 octet.
- Sauvegarde saine : `code_backups/backup_*_known_good_split/`.


---

## Annexe BS — Accueil Effectif, fiche club immersive et palmarès

### ACCUEIL PAR DÉFAUT : EFFECTIF
- `_build_ui`, reprise de carrière et création de carrière atterrissent désormais
  sur la page **Effectif** (index 1) au lieu du tableau de bord.
- Le retour après un rapport de match reste sur la Direction sportive.

### FICHE CLUB PLUS IMMERSIVE
- En-tête enrichi : écusson **+ maillot du club** (motif cohérent avec les
  autres vues), nom, ligue, réputation, saison et **salle** (`arena_name`) avec
  le nombre de joueurs sous contrat.
- Les couleurs du club restent le fond du bandeau, avec le rang et les points
  dans une pastille à droite.

### PALMARÈS DANS LA FICHE CLUB (onglet rétabli)
- Nouvel onglet **« 🏆 PALMARÈS »** (4 onglets maintenant : SAISON, EFFECTIF,
  SALLE, PALMARÈS) avec des libellés raccourcis pour que les 4 tiennent à
  l'écran.
- KPI : **titres**, **montées**, **descentes**, **Coupe Inter-Ligue**.
- Liste des titres gravés (`club_honours`) : saison, détail, ligue, plus les
  victoires en Coupe (`cup_palmares`).
- Tableau des **saisons archivées** : saison, division, rang, points,
  différence de buts, issue (CHAMPION / MONTÉE / DESCENTE / MAINTIEN) colorée.

### PALMARÈS DANS LE CLASSEMENT (onglet ajouté)
- La page Classement possède désormais un onglet **« 🏆 PALMARÈS »** :
  sélecteur de ligue (1-6), tableau saison / champion / montées / descentes,
  et rappel du nombre de titres du club.
- Rafraîchissement à l'ouverture de l'onglet (`_refresh_palmares_page`).

### RECHERCHE : CACHE DE PAGE
- `_refresh_search_page` mémorise une signature (texte + filtres + tri + ids) :
  revenir sur la page avec les mêmes critères **ne reconstruit plus les 60
  cartes**.
- Mesure : 2e ouverture **~80 ms** au lieu de ~305 ms ; la première construction
  reste à ~345 ms.

### MOTEUR DE RÉSULTAT DÉPLACÉ (`match_engine.py`)
- `_simulate_other_fixtures` (441 lignes) est extrait dans
  **`match_engine.py`** sous la forme `simulate_other_fixtures(host, conn, …)` ;
  `MainWindow` ne garde qu'une délégation de 4 lignes.
- Le module n'importe `career_timestamp` qu'à l'exécution (pas de cycle
  d'import) et n'a aucune dépendance UI : il est testable en headless.
- Validation immédiate : un match se finalise correctement, puis **soak de
  180 jours, 434 matchs, 4,5 buts/match, 0 erreur**.

### VALIDATION
- `tests/run_tests.py` : **10/10 ALL OK** ; `data/error.log` : 0 octet.
- Sauvegarde saine : `code_backups/backup_*_known_good_club_palmares/`.


---

## Annexe BT — Dossiers fantômes et page Entraînement

### PLUS DE « RÉPONSE À CONSULTER » APRÈS UN RECRUTEMENT
- **Cause** : un joueur pouvait être recruté (offre d'achat acceptée ou signature
  libre) alors qu'une autre négociation pour le MÊME joueur restait au statut
  `ready` (contre-proposition, autre offre). L'onglet OFFRES affichait donc
  « RÉPONSE À CONSULTER » pour un joueur déjà arrivé.
- Nouveau `close_player_dossiers(conn, player_id, keep_id)` : à chaque arrivée
  effective, tous les autres dossiers ouverts du joueur sont classés
  (`status='handled'`, `outcome='joined'`) — offres d'achat, contre-offres,
  prolongations, signatures libres.
- Appelé à la **signature d'un joueur libre**, à l'**accord d'achat** (le joueur
  est engagé même si son arrivée est annoncée à J+2/3) et à l'**arrivée
  officielle** (`transfer_arrival`). Le message d'arrivée lui-même reste actif.

### PAGE ENTRAÎNEMENT : STAFF, OPTIONS ET STATS
- **Niveau du préparateur corrigé** : le moteur lisait
  `preparateur_physique_level` alors que le Staff écrit
  `preparateur_physique_hired_level` — le niveau restait donc bloqué à 1. Les
  deux clés sont désormais lues (avec repli).
- **Effets réels du préparateur** : progression `+10 % × niveau`, risque de
  blessure réduit de `0,09 % × (niveau-1)`, fatigue et qualité de séance
  inchangées par ailleurs. Le panneau affiche le niveau et les bonus exacts.
- **Nouvelles options globales** (enregistrées dans `meta`) :
  - **Intensité globale** : Légère / Normale / Intense — décale chaque séance
    d'un cran (fatigue, risque, progression).
  - **Focus collectif** : Équilibré / Technique / Finition / Défense / Physique
    / Tactique — pondère à la hausse les attributs travaillés (+45 % de poids).
  - **Récupération automatique après un match** (option conservée pour
    l'auto-composition).
- **KPI en direct** : charge hebdomadaire (%), forme moyenne de l'effectif,
  risque de blessure (Faible/Moyen/Élevé + %), points d'attributs gagnés sur
  30 jours.
- **Auto-composition** : le plan automatique utilise le focus et l'intensité
  choisis (deux repos conservés).
- L'ancien bouton caché « PRÉPARATEUR » est désormais visible et mène au Staff
  (ou propose le recrutement à 30 000 €).

### VALIDATION
- Sonde dossiers : offre d'achat acceptée + contre-proposition en attente →
  la contre-proposition passe à `handled/joined`, l'arrivée reste planifiée.
- Sonde entraînement : préparateur niveau 4/5 → « +40 % / risque -27 % » ;
  intensité Intense + focus Physique appliqués aux séances ; application réelle
  d'une séance sans erreur (gains d'attributs, fatigue dosée).
- `tests/run_tests.py` : **10/10 ALL OK** ; `data/error.log` : 0 octet.
- Sauvegarde saine : `code_backups/backup_*_known_good_training/`.


---

## Annexe BU — Fenêtre « Python » fantôme (bouton préparateur)

- **Symptôme** : une petite fenêtre intitulée « python » apparaissait en plus du
  jeu, en lien avec le préparateur physique / le Staff.
- **Cause exacte** : le bouton `training_trainer_btn` (« PRÉPARATEUR PHYSIQUE •
  STAFF ») était créé **sans parent** et n'était ajouté à aucun layout. Il était
  masqué jusqu'ici ; en le rendant visible pour la nouvelle page Entraînement,
  Qt en a fait une **fenêtre de premier niveau** (d'où l'icône/titre Python).
- **Correctif** : le bouton est désormais ajouté au panneau du préparateur
  (`pb.addWidget`), donc enfant de la carte : plus aucune fenêtre séparée.
- **Contrôle automatisé** : après ouverture des pages Entraînement et Staff,
  `QApplication.topLevelWidgets()` ne renvoie **aucune fenêtre supplémentaire** ;
  `training_trainer_btn.isWindow()` est `False` et son parent est le cadre du
  préparateur.
- `tests/run_tests.py` : **10/10 ALL OK** ; `data/error.log` : 0 octet.
- Sauvegarde saine : `code_backups/backup_*_known_good_ghost/`.


---

## Annexe BV — Vague 1 / étape 1 : fenêtres de transfert

### RÈGLE
- **Mercato d'été** : 1er juillet → 15 septembre.
- **Mercato d'hiver** : 1er → 31 janvier.
- Hors fenêtre : les **transferts** et les **signatures de joueurs libres**
  sont refusés ; les **prolongations** de tes propres joueurs restent ouvertes
  toute l'année.

### AFFICHAGE
- Page **Transferts → MARCHÉ** : ligne de statut sous le titre
  (« MERCATO D'ÉTÉ • ferme le 15/09/2026 » en vert, ou
  « MERCATO FERMÉ • réouverture le 01/01/2027 » en rouge).
- Page **Transferts → OFFRES** : le statut est rappelé dans le sous-titre du
  bandeau, avec les compteurs de dossiers.

### APPLICATION
- `submit_market_offer` vérifie la fenêtre avant toute offre (achat ou joueur
  libre) et affiche un message clair avec la date de réouverture.
- Les offres déjà envoyées continuent leur cours (elles ne sont pas annulées
  par la fermeture) ; les dossiers fantômes restent fermés à l'arrivée du
  joueur (annexe BT).

### VALIDATION
- Tests de dates : 01/07 et 15/09 ouverts, 16/09 et 20/12 fermés (réouverture
  01/01), 10/01 ouvert, 01/02 et 30/06 fermés (réouverture 01/07).
- Offre hors fenêtre → refusée avec message ; offre en fenêtre → dossier créé.
- `tests/run_tests.py` : **10/10 ALL OK** ; `data/error.log` : 0 octet.
- Sauvegarde saine : `code_backups/backup_*_known_good_windows/`.

### SUITE DE LA VAGUE 1 (à venir)
1. Prêts de joueurs (salaire partagé, option d'achat, retour en fin de saison).
2. Pré-contrats pour les joueurs en fin de contrat.
3. Entraînement individuel par joueur (attribut ciblé, charge).
4. Objectifs du board + confiance détaillée.
5. Tactique avancée (rôles individuels, coups de pied arrêtés, momentum).


---

## Annexe BW — Entraînement individuel et refonte de la page

### PAGE ENTRAÎNEMENT EN TROIS ONGLETS
- **📅 SEMAINE** : plan des sept jours, palette d'ateliers, options globales
  (intensité, focus collectif, récupération auto), statut et retour.
- **🎯 INDIVIDUEL** : nouveau tableau du plan individuel.
- **📈 PROGRESSION** : évolution des 30 derniers jours (tableau existant).
- Le bandeau supérieur reste commun : préparateur (niveau/effets), KPI (charge,
  forme, risque, points 30 j), auto-composition et enregistrement.
- Passage d'onglet → rafraîchissement ciblé du tableau individuel.

### PLAN INDIVIDUEL
- Nouvelle colonne `player.training_focus` (migration automatique).
- Tableau par joueur : **nom, poste, âge, niveau, potentiel, FOCUS (liste
  déroulante), progression +30 j, forme**.
- Focus disponibles : Automatique, Technique, Passe, Finition, Défense,
  Physique (endurance), Vitesse, Dribble, Placement, Gardien.
- **Double-clic** sur une ligne → fiche du joueur.
- Actions groupées : **FOCUS AUTO PAR POSTE** (gardien → arrêts, défenseur →
  défense, ailier → technique, pivot → finition, universel → passe) et
  **TOUT EN AUTO**.

### EFFET SUR LE MOTEUR
- **Développement hebdomadaire** : le focus individuel pèse **×2,4** dans le
  choix de l'attribut, s'ajoute au plan du poste s'il n'y figure pas, et donne
  **+4 %** de progression globale.
- **Séance d'entraînement** : le focus pèse **×2,2** sur les attributs de
  l'atelier et peut ajouter l'attribut ciblé (poids 0,40) même hors atelier.
- Validation : gardien avec focus Finition, 8 points de développement →
  **+6 en finition** (contre +1 en passe/endurance), sans erreur.
- Soak 90 jours après refonte : **0 erreur**, 120 matchs, 4,5 buts/match.

### VALIDATION
- `tests/run_tests.py` : **10/10 ALL OK** ; `data/error.log` : 0 octet.
- Sauvegarde saine : `code_backups/backup_*_known_good_training_indiv/`.


---

## Annexe BX — Stats de match, notes et homme du match

### NOUVELLES STATS DANS LE RAPPORT
- **TIRS** (total), **TIRS CADRÉS**, **ARRÊTS** (déduits des tirs cadrés
  adverses moins les buts), **PASSES RÉUSSIES** avec pourcentage par équipe,
  en plus de la possession, des fautes, corners, interceptions, cartons,
  changements et blessures.
- Les arrêts sont exposés dans `build_match_report` (`report["saves"]`).

### NOTES INDIVIDUELLES ENRICHIES
- Formule revue : base 11,4 + **buts ×2,3**, **passes ×0,07** (plafonné à
  +1,2), **arrêts ×0,30**, bonus/malus de résultat (+0,5 victoire / −0,4
  défaite), évolution de forme, **cartons** (−0,4 jaune, −2,0 rouge) et
  blessure (−1,2). Note bornée 4-20.
- Seuls les joueurs **ayant réellement participé** sont notés (titulaires et
  entrés en jeu avec contribution) : les remplaçants non utilisés ne
  polluent plus le classement.
- Chaque note embarque désormais buts, passes, arrêts et cartons, réutilisés
  par la carte homme du match et le journal `player_match_log`.

### HOMME DU MATCH MIS EN AVANT
- Nouvelle **carte dorée** en tête des notes : avatar du joueur, nom, note
  /20 avec étoiles, et contributions (« 1 but • 8 arrêts • 2 passes »).
- Le classement des notes reste trié (note, buts, passes, arrêts) et
  double-cliquable vers la fiche du joueur.

### VALIDATION
- Rapport testé : 3–1, tirs 16-13, cadrés 12-5, arrêts 4-9 ; homme du match
  buteur 13,2 ; gardien 8 arrêts noté 13,0 ; aucun remplaçant non entré dans
  les notes.
- `tests/run_tests.py` : **10/10 ALL OK** ; `data/error.log` : 0 octet.
- Sauvegarde saine : `code_backups/backup_*_known_good_matchstats/`.


---

## Annexe BY — Prêts de joueurs et pré-contrats (vague 1, étape 2)

### PRÊTS DE JOUEURS
- Nouvelles colonnes joueur : `loan_from_club`, `loan_until_season`.
- Bouton **« DEMANDER UN PRÊT »** sur la fiche d'un joueur d'un autre club,
  pendant une fenêtre de transfert.
- Conditions : joueur non libre, sous contrat ≥ 2 ans, pas déjà prêté.
- Le club propriétaire **refuse de prêter un cadre** (joueur dans le top 2 de
  valeur du club) sauf effectif large (14+) ; sinon il accepte.
- Le joueur rejoint l'effectif immédiatement (salaire conservé, pris en charge
  par le club), est utilisable en match, et **retourne automatiquement à son
  club en fin de saison** (transition), numéro libéré.
- Garde-fous : pas de prolongation, pas de mise sur la liste des transferts,
  pas de licenciement ; la fiche affiche **« PRÊT »** au lieu de la durée.

### PRÉ-CONTRATS
- Nouvelles colonnes : `precontract_club`, `precontract_from`,
  `precontract_salary`, `precontract_years`.
- Bouton **« PRÉ-CONTRAT (FIN DE SAISON) »** sur la fiche d'un joueur dont le
  contrat se termine (`contract_years <= 1`), pendant une fenêtre.
- Boîte de négociation : salaire + durée (demande du joueur en plancher),
  rappel de son contrat actuel et de sa valeur.
- Stockage du pré-contrat, news + message, puis **arrivée officielle à la
  transition de saison** avec le salaire et la durée convenus.
- Sécurité : annulation si le joueur a changé de club ou prolongé entre-temps ;
  la durée signée reste exacte malgré la décrémentation annuelle des contrats.

### VALIDATION
- Sonde complète : prêt accepté → `club_id=1`, retour au club en fin de saison ;
  pré-contrat signé → arrivée au club avec 2 ans et 3 500 €/mois après
  transition ; `process_season_transition` exécuté sans erreur.
- Soak 400 jours (transition de saison incluse) : **0 erreur**, 210 matchs,
  4,3 buts/match.
- `tests/run_tests.py` : **10/10 ALL OK** ; `data/error.log` : 0 octet.
- Sauvegarde saine : `code_backups/backup_*_known_good_loans/`.

### OBSERVATION D'ÉQUILIBRAGE
- Le soak montre un effectif qui descend à **9 joueurs** après une saison.
  Prochaine priorité d'équilibrage : garde-fou d'effectif minimum (promotion
  de jeune / recrutement d'appoint encadré + alerte du board).


---

## Annexe BZ — Prêts avec analyse, visibilité et garde-fou d'effectif

### DEMANDE DE PRÊT PUIS VALIDATION DU CLUB
- **Plus de prêt immédiat** : « DEMANDER UN PRÊT » envoie désormais une
  **demande** au club propriétaire (message `loan_request`, réponse sous 1 à
  3 jours de carrière).
- À l'échéance, le club **analyse le dossier** (`_loan_analysis`) :
  - effectif trop court + joueur indispensable → **refus** ;
  - jeune (≤ 22 ans) peu utilisé → **accord** (« jeune à faire jouer ») ;
  - temps de jeu < 35 % → **accord** ;
  - prêt vers une division inférieure pour un joueur de rotation → **accord** ;
  - temps de jeu < 60 % → **accord** ;
  - sinon → refus (« le club compte sur lui »).
- En cas d'accord, le joueur rejoint l'effectif immédiatement et un message
  « Prêt accepté » explique la décision ; en cas de refus, « Prêt refusé » avec
  le motif.
- La réponse est informative (pas d'action à valider) et n'ajoute pas de badge
  permanent ; elle reste dans la messagerie et dans les news.

### PRÊTS VISIBLES DANS L'EFFECTIF
- Colonne **CONTRAT** : affiche **« PRÊT »** en violet pour un joueur prêté,
  avec infobulle « Prêté par <club> — retour en fin de saison ».
- La fiche joueur affiche déjà **« PRÊT »** à la place de la durée.
- Retour automatique au club propriétaire à la transition, numéro libéré.

### GARDE-FOU D'EFFECTIF MINIMUM
- `maintain_minimum_squad(conn, 12)` s'exécute à la clôture de saison.
- Sous 12 joueurs sous contrat, le club **recrute automatiquement des joueurs
  libres** (les meilleurs disponibles), puis, si le vivier ne suffit pas,
  **promeut de jeunes joueurs formés** (17-20 ans, attributs calibrés sur la
  division, date de naissance et salaire corrects).
- News + message « Effectif complété » listent les arrivées.
- Vérifié : effectif 9 → **12** (3 recrues), et après un soak de 400 jours
  l'effectif reste à **12** (contre 9 auparavant).

### VALIDATION
- Sonde : demande → message « waiting » → réponse « Prêt accepté » → joueur au
  club, colonne PRÊT et infobulle correctes.
- Soak 400 jours, transition incluse : **0 erreur**, effectif 12, 210 matchs,
  4,5 buts/match.
- `tests/run_tests.py` : **10/10 ALL OK** ; `data/error.log` : 0 octet.
- Sauvegarde saine : `code_backups/backup_*_known_good_loanflow/`.


---

## Annexe CA — Fin de prêt (retour au club propriétaire)

### BOUTON DE FICHE
- Pour un joueur **prêté**, le bouton « LICENCIER » devient
  **« METTRE FIN AU PRÊT »** (teinte ambre, infobulle explicite).
- Les actions incompatibles sont **masquées** : mise sur le marché et
  négociation de contrat (un joueur prêté appartient à un autre club).

### ACTION
- Confirmation claire : « Il retournera immédiatement à <club> et ne sera pas
  libre. »
- `terminate_loan(player_id)` :
  - remet le joueur dans son **club propriétaire** (`club_id` d'origine), avec
    `is_free_agent=0`, `loan_from_club=0`, `loan_until_season=0` ;
  - **libère le numéro** et relance `repair_shirt_numbers` pour éviter les
    doublons au club d'origine ;
  - enregistre l'historique « Fin de prêt — retour au club » et une news ;
  - ferme les dossiers en cours du joueur (`close_player_dossiers`) ;
  - le retire du terrain et de la sélection, puis rafraîchit l'effectif.
- Si le club d'origine n'existe plus (cas extrême), le joueur est placé
  **proprement** en joueur libre (`club_id=0`, `is_free_agent=1`, champs de prêt
  effacés) — jamais un fantôme rattaché au club.

### FIN DE CONTRAT PENDANT UN PRÊT
- `process_contract_expiries` traite désormais les joueurs prêtés à part :
  le prêt est clôturé, les champs `loan_*` remis à zéro et le joueur devient un
  **vrai joueur libre** (`club_id=0`) au lieu de rester attaché au club avec un
  contrat nul.
- Vérifié : prêt + contrat 0 → `club_id=0`, `is_free_agent=1`, `loan_from_club=0`.

### VALIDATION
- Sonde : fin de prêt → joueur au club parent (id 42/55), non libre, numéro
  réattribué, historique correct.
- Fiche : bouton « METTRE FIN AU PRÊT », actions de vente/contrat masquées.
- Soak 150 jours : **0 erreur**, effectif 12, 4,4 buts/match.
- `tests/run_tests.py` : **10/10 ALL OK** ; `data/error.log` : 0 octet.
- Sauvegarde saine : `code_backups/backup_*_known_good_loanend/`.


---

## Annexe CB — Enjeux de carrière (vague 2, étape 1)

### OBJECTIFS DU BOARD
- Nouveau panneau **« OBJECTIFS DU BOARD »** sur le tableau de bord :
  - **CLASSEMENT** : objectif de place calculé selon la division et la
    réputation (top 8 en L1-2, top 6 en L3-4, top 3 en L5-6, ajusté à la hausse
    pour les clubs réputés) ;
  - **FINANCES** : terminer avec une trésorerie positive ;
  - **JEUNES** : au moins 2 joueurs de 21 ans ou moins avec du temps de jeu.
- Chaque objectif est affiché en pastille verte (atteint), jaune (limite) ou
  rouge (en danger), avec la **confiance du board en %**.
- Les objectifs sont générés au début de chaque saison (`board_objective_*`
  dans `meta`) et conservés tant que la saison ne change pas.

### CONFIANCE ET CONSÉQUENCES
- Confiance calculée à partir du classement, de la trésorerie, des jeunes
  utilisés et du bilan récent (`board_confidence`).
- **Avertissement** : sous 30 %, un message du board + une news sont envoyés
  une seule fois par saison.
- **Gel des transferts** : sous 22 %, les achats sont bloqués
  (« Le board gèle les transferts ») ; les signatures de joueurs libres restent
  autorisées pour ne pas bloquer le garde-fou d'effectif.
- **Licenciement** : à la clôture de saison, si la confiance est sous 15 %,
  `manager_sacked=1` est gravé ; le board met fin à la mission et l'interface
  revient à l'accueil avec un message explicite.

### CONFIANCE DES SUPPORTERS
- `fan_confidence` est recalculé (résultats, points, réputation, position) et
  remplace l'ancien calcul dans la jauge **SUPPORTERS**.
- L'**affluence** dépend désormais de cette confiance : la demande de places est
  modulée de ×0,85 à ×1,15 dans `projected_attendance`, ce qui fait varier la
  billetterie et l'ambiance des matchs à domicile.

### VALIDATION
- Tableau de bord : objectif top 7, classement 1er (vert), finances positives
  (vert), jeunes 0/2 (jaune), confiance 73 %.
- Gel : achat payant refusé, joueur libre accepté.
- Licenciement : confiance 10 % à la clôture → `manager_sacked=1` + message.
- `tests/run_tests.py` : **10/10 ALL OK** ; `data/error.log` : 0 octet.
- Soak 150 jours : **0 erreur**, effectif 12, 4,6 buts/match.
- Sauvegarde saine : `code_backups/backup_*_known_good_board/`.

### RESTE DE LA VAGUE 2
- **Offres d'autres clubs en fin de saison** : l'acceptation implique un
  changement de club complet (échange d'identité et de références en base) ;
  à traiter comme une opération dédiée et testée à part pour ne pas risquer la
  sauvegarde.
- Derbies et ambiance de stade (affluence déjà liée à la confiance).


---

## Annexe CC — Changement de club (offres de carrière)

### OFFRES DE CLUBS
- Après la clôture de saison, `generate_job_offers` analyse le parcours :
  place finale, titre/montée, confiance du board. Un bon parcours
  (top quart, champion, promotion ou confiance ≥ 68 %) attire **1 à 2 offres**
  de clubs de la même division (plus réputés) ou de la division supérieure.
- Les offres sont stockées dans `meta.job_offers` et affichées sur le tableau
  de bord dans un panneau **« OFFRES DE CLUBS • CARRIÈRE »**, avec
  **ACCEPTER LE POSTE** / **REFUSER**.
- Refuser retire l'offre ; accepter demande confirmation puis bascule le club.

### BASCULE COMPLÈTE (`change_manager_club`)
- Les **prêts en cours** retournent immédiatement à leurs clubs d'origine.
- Les **dossiers en attente** (transferts, contrats, prêts) sont classés et les
  **pré-contrats** annulés : rien ne reste promis au club quitté.
- Échange d'identité des deux clubs (id 1 ↔ club cible) puis permutation de
  **toutes les références** : joueurs, calendrier (`home/away`), classements,
  palmarès, archives de saison, historique des joueurs, mouvements financiers.
- Le club quitté redevient un club IA avec **son effectif et son palmarès** ;
  le manager récupère l'effectif et l'histoire du nouveau club.
- **Installations** : le manager ne conserve pas l'infrastructure du club
  quitté — le profil du nouveau club (estimation division/réputation) est
  appliqué à la base `facility`.
- Le **board repart de zéro** : objectifs, confiance, gel des transferts,
  supporter et offres sont purgés puis recalculés pour le nouveau club.
- Le terrain est vidé et la tactique rechargée pour éviter de garder des
  joueurs de l'ancien club dans le cinq.

### UI ET SÉCURITÉ
- Panneau visible uniquement quand des offres existent ; boutons par offre.
- Confirmation explicite : « Tu emmènes ton staff et tes méthodes, mais tu
  laisses l'effectif et l'infrastructure derrière toi. »
- En cas d'exception, rollback complet : la sauvegarde n'est pas modifiée.

### VALIDATION
- Nouvelle suite **`tests/test_club_swap.py`** : génère une offre, accepte la
  bascule, vérifie noms/divisions, effectifs échangés, calendrier, absence de
  doublons d'identifiants, palmarès conservé par le club quitté et offres
  purgées.
- `tests/run_tests.py` : **11/11 ALL OK** ; `data/error.log` : 0 octet.
- Soak 400 jours (transition + offres) : **0 erreur**, effectif 12, 4,5 buts/match.
- Sauvegarde saine : `code_backups/backup_*_known_good_joboffers/`.


---

## Annexe CD — Profondeur tactique (vague 3)

### CONSIGNES INDIVIDUELLES
- Nouveau bouton **« CONSIGNES & COUPS DE PIED »** sur la page Tactiques.
- Onglet **RÔLES & CONSIGNES** : tableau de l'effectif avec, par joueur,
  **RÔLE** (Gardien / Fixo / Ala / Pivot / Universel), **PRESSING**
  (Bas / Normal / Haut) et **DÉFENSE** (Relâché / Normal / Agressif).
- Bouton **RÔLES AUTOMATIQUES PAR POSTE** pour tout réinitialiser.
- Stockage dans `tactical_instruction` ; les consignes des cinq titulaires
  sont agrégées (moyenne géométrique) dans le profil de l'équipe :
  - rôle conforme au poste : +1,2 % défense (fixo/gardien), +1 % attaque (ala),
    +1,5 % finition (pivot) ; rôle inadapté : −1,5 % attaque/défense ;
  - pressing haut : +2 % défense ; pressing bas : −1 % attaque ;
  - défense agressive : +1,5 % défense / −0,5 % attaque ; relâchée : +1,5 %
    attaque / −1 % défense.

### COUPS DE PIED ARRÊTÉS ET POWERPLAY
- Onglet **COUPS DE PIED** : CORNERS (Poteau / Court / Retrait), COUPS FRANCS
  (Direct / Combiné), SORTIE DE PRESSING (Court / Long), POWERPLAY
  (Automatique / Toujours / Jamais).
- Effets dans le moteur : corner au poteau +1 % attaque, corner court +1 %
  passe, coup franc direct +2 % finition, sortie courte +1,2 % passe, sortie
  longue +0,6 % attaque.
- **Powerplay** : dans les 5 dernières minutes, si l'équipe est menée, attaque
  +10 % et défense −10 % (sauf réglage « Jamais »).

### FAMILIARITÉ TACTIQUE
- `tactics_familiarity` (0-100) et `tactics_signature` en base.
- Un plan identique d'un match à l'autre : **+8 points** ; un plan modifié
  (formation, consignes, coups de pied…) : **−35** (plancher 30). Première
  évaluation : 60.
- Effet : multiplicateur de 0,93 à 1,03 sur attaque/passe/finition et 0,92 à
  1,02 sur la défense.
- Affichage **« FAMILIARITÉ xx % »** dans la ligne de lecture de la page
  Tactiques (vert ≥ 80, jaune ≥ 55, rouge sinon) + infobulle.
- Mise à jour automatique au coup d'envoi (`start_match`).

### MOMENTUM ET CAUSERIE
- `momentum` dans l'état du match : +12 pour un but marqué, −12 encaissé,
  décroissance de 1,5 % par minute, borné ±20 ; effet ±8 % sur l'attaque.
- À la mi-temps, une **causerie non bloquante** propose trois choix :
  - **CALME** : défense +2 %, forme +2, momentum remis à 0 ;
  - **MOTIVANT** : attaque +4 %, moral +3, momentum +8 ;
  - **TACTIQUE** : défense +4 %, attaque −2 %, momentum remis à 0 ;
  - bouton **PASSER** pour ne rien changer.
- L'effet est appliqué à la seconde période et journalisé dans les temps forts.

### PERFORMANCE
- Les facteurs statiques (familiarité, consignes, coups de pied) sont calculés
  **une seule fois par match** et mis en cache dans l'état ; seuls le momentum,
  le powerplay et la causerie sont recalculés par minute.

### VALIDATION
- Sonde : consignes enregistrées, familiarité 60 → 68 après un match avec le
  même plan, modificateurs cohérents, causerie motivante appliquée.
- `tests/run_tests.py` : **11/11 ALL OK** ; `data/error.log` : 0 octet.
- Soak 150 jours : **0 erreur**, 358 matchs, 4,4 buts/match.
- Sauvegarde saine : `code_backups/backup_*_known_good_tactical/`.


---

## Annexe CE — Immersion (vague 4)

### CAUSERIE D'AVANT-MATCH
- Au lancement du match, une boîte propose trois tons (+ PASSER) :
  - **CONFIANCE** : moral +2, attaque +2 % en première période ;
  - **SOLIDARITÉ** : forme +3, défense +2 % en première période ;
  - **PRESSION** : moral +1, attaque +3 % / défense −2 % en première période.
- Effet stocké pour la première période uniquement (remis à zéro à la mi-temps)
  et journalisé dans les news (« Vestiaire »).

### INTERVIEW D'APRÈS-MATCH
- Après le coup de sifflet, trois réponses selon le résultat :
  - **FÉLICITER LE GROUPE** : moral +2, supporters +2 ;
  - **RESTER HUMBLE** : moral +1, image du club renforcée ;
  - **POINTER LES ERREURS** : moral −1, exigence saluée par le board.
- News « Presse » + message d'information ; bouton PASSER disponible.

### DERBIES
- Un **rival** est choisi automatiquement dans la même division (réputation la
  plus proche) et stocké dans `meta.rival_club_id`.
- Le prochain match contre ce club affiche **DERBY** sur le tableau de bord et
  dans l'en-tête du match ; la causerie d'avant-match ajoute un bonus de moral.
- **Affluence +15 %** à domicile pour un derby (billetterie et ambiance).
- Après le match : moral +3 (victoire), +1 (nul), −2 (défaite) et news dédiée.

### CENTRE DE NOTIFICATIONS
- Nouveau panneau sur le tableau de bord : messages `ready` regroupés par
  famille — **Transferts / Contrats / Matchs / Board / Presse / Système** —
  avec compteurs colorés, total et bouton **OUVRIR LA MESSAGERIE**.
- Masqué quand il n'y a rien à consulter.

### AUTRES
- Les records, nominations et palmarès restent couverts par l'héritage du club
  et le fil d'actualité existant ; les nouvelles causeries/derbies ajoutent
  leurs propres lignes.

### VALIDATION
- Sonde : rival attribué (Racing Club de Copenhague), centre de notifications
  5 messages regroupés, derby détecté au lancement, affluence et morale
  appliquées, interview sans blocage.
- `tests/run_tests.py` : **11/11 ALL OK** ; `data/error.log` : 0 octet.
- Soak 150 jours : **0 erreur**, 358 matchs, 4,5 buts/match.
- Sauvegarde saine : `code_backups/backup_*_known_good_immersion/`.


---

## Annexe CF — Équilibrage et durée de vie (vague 5)

### MODE DIFFICILE
- Nouveau choix **DIFFICULTÉ : Normale / Difficile** dans les options du jeu
  (onglet Apparence). Le choix est enregistré dans les options et appliqué en
  base au démarrage (`difficulty_mode`).
- En **Difficile** :
  - objectif de classement **une place plus haut** et **3 jeunes** à faire jouer
    (au lieu de 2) ;
  - confiance du board **−6 points** ;
  - **sponsors et recettes de match −10 %** ;
  - IA plus agressive : recrutement 30 % → 40 %, offres reçues 14 % → 20 %,
    offres spontanées 5 % → 8 %.

### EFFECTIF : GARDE-FOU HEBDOMADAIRE
- En plus de la clôture de saison, `process_player_development` vérifie chaque
  semaine l'effectif : sous 12 joueurs, `maintain_minimum_squad` recrute des
  libres puis promeut des jeunes, avec news/message.
- Vérifié : effectif 9 → 12 en une passe.

### MARCHÉ IA
- Nouveau `process_ai_squad_rebuild` (le lundi) : les clubs IA sous 11 joueurs
  signent jusqu'à 2 joueurs libres (budget vérifié), et le vivier de libres est
  réapprovisionné (`ensure_free_agents`).
- Limité à 4 signatures par semaine pour éviter de vider le marché et de
  déstabiliser les effectifs.

### PROGRESSION DES JEUNES
- Les générations du club profitent du **centre de formation** :
  `base × (1 + 0,02 × (niveau-1))`.
- **Mentorat** : un jeune (≤ 21 ans) du club dont l'effectif compte un vétéran
  (≥ 30 ans, moyenne technique/passe/défense/finition ≥ 65) progresse
  **+6 %**.
- Les prêts sortants de jeunes restent à implémenter (nécessite un club IA
  demandeur et un retour automatique).

### VALIDATION
- Sonde : `hard_mode` vrai, objectif top 6 + 3 jeunes, sponsor 10 000 → 9 000,
  effectif 9 → 12, IA reconstruit, vivier de libres maintenu.
- `tests/run_tests.py` : **11/11 ALL OK** ; `data/error.log` : 0 octet.
- Soak 90 jours : **0 erreur**, 120 matchs, 4,6 buts/match.
- Sauvegarde saine : `code_backups/backup_*_known_good_balance/`.


---

## Annexe CG — Technique (vague 7)

### DÉCOUPAGE : squad_engine.py
- `maintain_minimum_squad` et `process_ai_squad_rebuild` sont sortis de
  `app.py` vers **`squad_engine.py`** (6 Ko). `app.py` ne garde que des
  méthodes de délégation d'une ligne, comme pour `match_engine.py`.
- Bilan des modules extraits :
  - `game_utils.py` : helpers purs (dates, notes, montants) ;
  - `match_engine.py` : simulation des matchs IA ;
  - `squad_engine.py` : garde-fou d'effectif et reconstruction IA ;
  - `ui_components.py` : widgets (dont `TacticalBoard`, `GameOptionsDialog`).
- `app.py` reste le point d'entrée et le cœur UI/marché/finances ; la suite du
  découpage (UI, marché, finances) reste ouverte.

### TEST DE SOAK AUTOMATISÉ
- Nouveau `tests/test_balance_soak.py`, ajouté à `SUITES` dans
  `tests/run_tests.py` (**12 suites**).
- Il joue **300 jours** (deux étés, une intersaison) avec dialogue patché,
  puis vérifie :
  - `matchs_simulés ≥ 120` ;
  - `buts/match` entre **2,0 et 7,5** ;
  - `effectif` du club entre **11 et 22** ;
  - `budget` entre **−5 M et 15 M** ;
  - **0 erreur** pendant la boucle.
- Les matchs sont comptés par **delta successif** de `fixture`, car l'historique
  est remis à zéro au changement de saison.
- Mesure actuelle : **300 jours, 22 matchs joués, 599 matchs simulés,
  4,40 buts/match, effectif 12, budget 2,61 M, 0 erreur** (~76 s).

### RAPPORT DE CRASH
- Nouvelle fonction `install_crash_reporter()` appelée dans `main()` juste
  après `init_db()` :
  - `faulthandler` alimente `data/crashes/fault.log` (crash natif Qt/Python) ;
  - `sys.excepthook` écrit `data/crashes/crash_AAAAMMJJ_HHMMSS.txt` avec date,
    **club et date de carrière**, puis la trace complète ;
  - le même contenu est ajouté à `data/error.log` (journal lisible existant) ;
  - l'ancien comportement (affichage console) est conservé via
    `sys.__excepthook__`.
- Vérifié par sonde : dossier créé, hook installé, rapport lisible contenant
  `ZeroDivisionError` et la fonction fautive, `error.log` alimenté.

### VALIDATION
- `tests/run_tests.py` : **12/12 ALL OK** ; `data/error.log` : **0 octet**.
- Sauvegarde saine :
  `code_backups/backup_*_known_good_technical/` (app, ui_components,
  match_engine, squad_engine, game_utils, tests).


---

## Annexe CH — Prêts sortants (jeunes)

### PRINCIPE
- Un jeune du club (**23 ans ou moins**) peut être prêté à un club IA de la même
  division ou d'une division inférieure, jusqu'à la fin de la saison.
- Le joueur quitte l'effectif (`club_id` = club d'accueil, `loan_from_club = 1`,
  `loan_until_season` = saison en cours) et son salaire sort des charges.
- **Trois prêts sortants maximum** ; il faut conserver au moins 11 joueurs
  (le garde-fou hebdomadaire reconstruit ensuite un effectif de 12).
- Fenêtre de transfert obligatoire, joueur ni blessé ni déjà prêté.

### DÉCISION DU CLUB IA
- Trois clubs candidats sont proposés (effectif de 8 à 15 joueurs, niveau
  compatible).
- Le club compare le niveau du joueur à la moyenne de son groupe :
  - écart < −4 : refus ;
  - promesse TITULAIRE et écart < −0,8 : refus ;
  - 12 % de refus aléatoire (« autre piste »).
- La réponse arrive **1 à 3 jours** plus tard dans la messagerie
  (`loan_out_request`) ; le dossier est aussi suivi dans l'onglet PRÊTS.

### TEMPS DE JEU ET PROGRESSION
- Chaque lundi (`process_outgoing_loans`) :
  - 88 % de chance de jouer avec la promesse TITULAIRE, 55 % en ROTATION
    (+8 % si le joueur domine le groupe) ;
  - note calculée sur l'écart de niveau, buts/passes selon le poste, forme et
    moral ajustés ;
  - progression : +1 dans un attribut avec 55 % (titulaire) / 38 % (rotation),
    plafonnée au potentiel.
- Le club IA continue par ailleurs son entraînement normal.

### RAPPEL ET RETOUR
- Bouton **RAPPELER LE JOUEUR** dans l'onglet PRÊTS : retour immédiat,
  confirmation demandée, numéro de maillot réattribué, place tactique purgée.
- **Fin de saison** : retour automatique AVANT la remise à zéro des statistiques,
  avec bilan gravé dans l'historique
  (« Retour de prêt (N match(s), X but(s), Y passe(s), note Z) »).
- Un prêt sortant est cassé proprement si le manager change de club.
- Impossible d'acheter un joueur actuellement prêté (garde-fou du marché).

### INTERFACE
- Nouvel onglet **PRÊTS • ENTRANTS & SORTANTS** dans le mercato :
  - tableau des sortants (club, division, promesse, matchs, note, statut) avec
    rappel ;
  - tableau des entrants (club propriétaire, matchs, note) avec fin de prêt ;
  - bouton **PRÊTER UN JEUNE** (choix du joueur, du club, de la promesse).
- Bouton **PRÊTER** dans la fiche d'un joueur de 23 ans ou moins.
- Rafraîchissement à l'ouverture de l'onglet et pendant `refresh_all`.

### TECHNIQUE
- Nouveau module **`loan_engine.py`** (10 fonctions) : éligibilité, candidats,
  demande, décision, temps de jeu, retour, rappel. `app.py` ne garde que des
  délégations (`_resolve_loan_out`, `process_outgoing_loans`,
  `return_outgoing_loans`).
- Colonne `player.loan_promise` ajoutée par migration douce.
- Nouveau test `tests/test_loans.py` : éligibilité, candidats, demande,
  acceptation, temps de jeu, onglet, rappel, retour, dialogue.

### VALIDATION
- `tests/run_tests.py` : **13/13 ALL OK** ; `data/error.log` : **0 octet**.
- Sonde saison complète (320 jours, prêt actif) : **0 erreur**, retour
  automatique au club à la clôture, sauvegarde saine.
- Changement de club avec prêt en cours : prêt cassé proprement, joueur laissé
  au club quitté.
- Sauvegarde saine : `code_backups/backup_*_known_good_loans/`.


---

## Annexe CI — Phase de debug et de test (audit complet)

### DEMARCHE
- Audit **statique** : compilation des 8 modules, detection des fonctions et
  methodes definies deux fois, recherche des `except` nus. Resultat : aucun
  doublon, aucun `except` nu (117 `except Exception: pass` historiques, sans
  impact fonctionnel identifie).
- Audit **d'integrite de base** (script dedie) : `PRAGMA integrity_check`,
  references de clubs, coherence libre/contrat/pret, ages, attributs, notes,
  moral, forme, contrats, numeros de maillot, classements (V+N+D et points),
  matchs, messages, finances, historique, effectifs.
- **Soaks chaos** : navigation dans les 14 pages et les 10 QTabWidget, ouverture
  des dialogues (options, fiches, prets, colonnes, consignes, credits, archives,
  sauvegardes), matchs joues, saisons enchainees, prets sortants/entrants,
  sauvegardes regulieres, audit de la base apres chaque run.
- Scenarios cibles : mercato (achat + libre), pre-contrat, fenetres ete/hiver,
  paie (nouvelle carriere et migration), changement de club, licenciement du
  board, migration d'une ancienne sauvegarde, effectifs IA de cloture.

### CAMPAGNE DE SOAKS
| Jours | Seed | Mode | Division | Erreurs | Audit | Effectif min | Buts/match |
|-------|------|------|----------|---------|-------|--------------|------------|
| 90    | 1    | Normale | 3 | 0 | OK | 12 | 4,55 |
| 300   | 2    | Normale | 6 | 0 | OK | 12 | 4,60 |
| 300   | 3    | Difficile | 1 | 0 | OK | 12 | 4,60 |
| 300   | 7    | Normale | 6 | 0 | OK | 11 | 4,55 |
| 500   | 11   | Difficile | 1 | 0 | OK | 11 | — (fin d'intersaison) |
| 600   | 9    | Normale | 3 | 0 | OK | 12 | 4,41 |
| 900   | 5    | Normale | 2 | 0 | OK | 12 | 4,75 |

- Tous les soaks : **0 exception**, `error.log` 0 octet, base saine.
- Sauvegardes de 2 a 3 Mo apres plusieurs saisons ; aucun emballement memoire.
- Economie apres correction de la paie : budget club 0,27 M en Ligue 6,
  1,88 M en Ligue 3, 2,17 M en Ligue 2 ; aucun club IA en negatif.

### BUGS TROUVES ET CORRIGES
1. **Marche libre qui vidait les clubs** : `ensure_free_agents` liberait
   140 joueurs deja sous contrat (tri par valeur croissante), laissant des
   clubs de Ligue 6 a 1-4 joueurs. Desormais `generate_free_agents` cree de
   vrais libres : **60 clubs x 12 joueurs + 140 libres**.
2. **Libres rattaches au club du manager** : le generateur pouvait choisir
   club_id=1 ; ces joueurs apparaissaient dans les briefs (test messagerie
   casse) et faussaient les comptages. Invariant + reparation au chargement.
3. **Fins de contrat** : un joueur du club 1 libere gardait club_id=1 ; un
   joueur prete libere passait a club_id=0 (invisible du marche). Les deux
   chemins lui donnent maintenant un club d'affichage IA valide.
4. **Notes de match sur deux echelles** : matchs IA notes 4,0-9,8, matchs du
   manager 4,0-20. Les notes IA sont alignees sur 20 (base 11,4, buts/passes,
   arrets, resultat) ; les classements et valeurs marchandes melangent enfin
   des notes comparables.
5. **Numeros de maillot en double** : les recrutements IA (hebdo, urgence,
   rival) changeaient de club sans nouveau numero. 5 chemins corriges +
   `repair_shirt_numbers` chaque lundi + filet a la cloture.
6. **Aucune masse salariale en nouvelle carriere** : la migration "prepaid"
   (pensee pour les anciennes sauvegardes) exemptait tous les contrats
   initiaux, et la premiere paie marquait tout le monde comme prepaye. Une
   nouvelle carriere paie des le premier mois ; la migration legacy exclut
   correctement la premiere paie des contrats deja pre-escomptes.
7. **Clubs IA a 9-10 joueurs apres la cloture** : les vagues de fins de
   contrat n'etaient compensees qu'au lundi suivant. `ensure_ai_squads`
   recomplete immediatement a 11 des la fin de saison, et **au chargement de
   toute sauvegarde** dont un club IA serait incomplet.
8. **Pret sortant hors fenetre** : le dialogue bloquait, mais l'API
   `request_loan_out` ne verifiait pas la fenetre. Controle ajoute au moteur.
9. **Tests fragiles** : `test_messagerie` (joueur deja cite dans le brief) et
   `test_club_swap` (libres complets dans les effectifs) rendaient des echecs
   aleatoires. Les tests fixent maintenant les contrats et comptent les joueurs
   sous contrat.

### COUVERTURE AJOUTEE
- Nouveau `tests/test_world_integrity.py` : 60 clubs complets, vivier de
  140 libres, libres hors club 1 et avec club valide, paie mensuelle deux mois
  de suite, unicite des maillots, comblement IA a la cloture.
- `tests/run_tests.py` : **14 suites**, toutes vertes deux fois de suite.
- `data/error.log` : **0 octet** apres chaque campagne.

### VALIDATION FINALE
- `python tests/run_tests.py` : **14/14 ALL OK**.
- Audit statique : **aucun probleme**.
- Audit de base fraiche : **0 probleme** (860 joueurs, 60 clubs de 12,
  140 libres).
- Sauvegarde saine : `code_backups/backup_*_known_good_debug/`.


---

## Annexe CJ — Perception IA et libres non désirés

### MARCHÉ LIBRE : DATE D'ENTRÉE ET RETRAITE
- Nouvelle colonne `player.free_agent_since` : date à laquelle le joueur est
  arrivé sur le marché libre.
- Elle est renseignée à la génération, aux fins de contrat (quotidiennes et de
  clôture), aux libérations d'effectifs IA et par la réconciliation du lundi
  (filet de sécurité pour les anciennes sauvegardes).
- Elle est effacée à chaque signature (manager, IA, urgence).
- À la **clôture de saison**, `retire_unwanted_free_agents` fait raccrocher
  tout libre présent depuis **330 jours ou plus**, **sans condition d'âge** :
  un jeune de 18 ans que personne n'a signé met fin à sa carrière.
- Bilan dans les news et la messagerie ; le joueur sort du marché
  (`retired=1`, `is_free_agent=0`, salaire et numéro remis à zéro).
- Le vivier est ensuite réapprovisionné par `generate_free_agents` (pas en
  vidant les clubs).

### PERCEPTION DES CLUBS IA
- Nouvelle table `ai_scout_knowledge(club_id, player_id, knowledge, updated_date)`.
- Chaque club **supervise** les joueurs : la connaissance progresse de
  9 + réputation/10 (+ bonus divisions hautes) à chaque observation, plafond 100.
- Le niveau perçu = vrai niveau + erreur gaussienne dont l'écart type passe de
  **4,9 niveaux** (connaissance nulle) à **0,35** (connaissance 100). Un club
  peut donc surestimer un joueur, passer à côté d'une pépite ou recruter un
  joueur moins fort que prévu.
- `rank_free_agents` supervise un **échantillon aléatoire de 14 libres** plus
  jusqu'à 5 joueurs déjà connus, puis classe selon la perception.
- Appliqué au recrutement du week-end (`process_ai_recruitment`), au
  réapprovisionnement hebdomadaire (`rebuild_ai_squads`) et au comblement de
  clôture (`ensure_ai_squads`). L'IA ne trie donc plus le marché par valeur
  réelle : elle prend ce qu'elle **croit** être le meilleur pour elle.
- Le recrutement d'urgence sur match reste basé sur le niveau réel (il faut un
  joueur valide immédiatement), mais il reste rare.

### BUG TROUVÉ PENDANT L'INTÉGRATION
- Les joueurs **retraités** étaient remis sur le marché par les fins de contrat
  (`contract_years<=0`, `is_free_agent=0`) et par `ensure_free_agents` : ils
  réapparaissaient comme libres, avec une nouvelle date. Tous les chemins
  d'expiration et de réapprovisionnement excluent désormais `retired=1`.
- Les retraités conservent `club_id=0`, `is_free_agent=0`, sans date de libre.
- Au chargement d'une ancienne sauvegarde, les retraités encore marqués libres
  sont nettoyés automatiquement.

### VALIDATION
- Nouveau `tests/test_ai_scouting.py` : perception initiale imparfaite,
  convergence après 9 observations, recrutements IA réels sur 6 week-ends,
  purge des dates, retraite d'un libre de 19 ans, non-retour sur le marché.
- `tests/run_tests.py` : **15/15 ALL OK** ; `data/error.log` : **0 octet**.
- Soak 400 jours : 0 erreur, audit sain, 4,35 buts/match.
- Soak 600 jours : 0 erreur, audit sain, 982 joueurs, vivier 79 libres,
  **183 retraites dont 114 libres non signés (âges 18 à 37)**, 4,77 buts/match,
  effectif minimum 12.
- Sauvegarde saine : `code_backups/backup_*_known_good_ai_scouting/`.


---

## Annexe CK — Budgets réels et identités des clubs IA

### FINANCES MENSUELLES
- Nouveau module **`ai_finance.py`**.
- Le 1er de chaque mois (`process_ai_monthly_finances`) :
  - **revenus** = base division / 36 (plancher 28 000 €) × facteur de
    réputation × multiplicateur du profil ;
  - **salaires** = somme réelle des salaires de l'effectif ;
  - **entretien** = base mensuelle × coefficient du profil ;
  - le solde est crédité/débité du budget.
- Un garde `ai_finance_month` empêche de payer deux fois le même mois (saut de
  date de la clôture).
- L'ancienne dotation annuelle (`process_ai_season_finance`) est désactivée :
  elle aurait fait double emploi.
- Les primes de classement/compétition restent versées séparément.

### PRESSION FINANCIÈRE
- Budget négatif ou masse salariale > 95 % des revenus : le club place son
  plus gros salaire sur le marché (news).
- Effectif > 13 : un joueur peut être placé sur le marché pour dégraisser.
- Un club ne descend jamais sous 11 joueurs via une mise sur la liste.
- Un club sous 11 se renforce en priorité (le ratio salarial ne bloque pas la
  survie sportive).

### MARCHÉ SECONDAIRE IA-IA
- Le mercredi (`process_ai_transfer_market`), des clubs achètent les joueurs
  listés par d'autres clubs IA (jamais ceux du manager, qui passent par la
  messagerie).
- Prix = valeur marchande ; l'acheteur paie, le vendeur encaisse ; le joueur
  reçoit un numéro, un contrat de 2 ans minimum, et l'historique est gravé.
- Contrôles : budget, ratio de transfert du profil, salaire, effectif du
  vendeur > 11, effectif de l'acheteur < 15, joueur toujours listé (anti
  double vente).

### TRANSFERTS AVEC LE MANAGER
- Achat d'un joueur IA : le club vendeur encaisse désormais l'indemnité.
- Vente d'un joueur du manager : le club acheteur est débité et doit pouvoir
  financer l'opération.
- Les offres reçues vérifient la solvabilité de l'acheteur (budget + salaire).

### PROFILS DE CLUB (7 IDENTITÉS)
| Profil | Idée | Recrutement | Style | Finances |
|--------|------|-------------|-------|----------|
| **Formateur** | jeunes et centre | ≤25 ans, potentiel, salaires bas | possession, patient | revenus 0,95 ; entretien 0,13 ; ratio salarial 0,82 |
| **Riche** | stars, résultats | tous âges, notes élevées | possession, pressing haut | revenus 1,22 ; transferts 0,35 |
| **Spectacle** | jeu et public | attaquants, spectacle | pressing haut, rapide | revenus 1,10 ; transferts 0,20 |
| **Économe** | chaque euro compte | joueurs bon marché, vétérans | contre, bloc bas | revenus 0,90 ; entretien 0,07 ; transferts 0,06 |
| **Bâtisseur** | patience et équilibre | profils équilibrés | équilibré | revenus 1,00 ; transferts 0,16 |
| **Opportuniste** | acheter bas, revendre haut | coups de marché | contre, rapide | revenus 0,95 ; transferts 0,20 |
| **Guerrier** | intensité et mental | profils défensifs | pressing haut | revenus 0,90 ; entretien 0,09 |

- Les profils sont **stables par club** (déterminés par l'identifiant) et
  assignés à la création ou au chargement (`club_profiles.ensure_profiles`).
- Le club du manager est **Manager** : ses choix restent libres.
- En cas de changement de club, le nouveau club devient Manager et l'ancien
  reçoit un profil IA.
- Effets : score de recrutement (âge, niveau perçu, poste, salaire), plafond de
  salaires, ratio de transfert, revenus, entretien, qualité des jeunes
  (`youth_mult` 0,92 à 1,30), style tactique du moteur de match.

### INTERFACE
- Fiche club : nom du profil, devise, budget, masse salariale, solde mensuel.
- Le style de l'adversaire suit son profil (possession, contre, pressing…).

### BUGS CORRIGÉS PENDANT L'INTÉGRATION
- `ensure_free_agents` pouvait retirer 10 joueurs au même club pour remplir le
  vivier (club à 3 joueurs). Plafond : jamais sous 13, au plus `taille-13`.
- Marché IA : relecture du joueur avant exécution pour empêcher une double
  vente.
- Transferts : l'indemnité n'était ni encaissée par le vendeur IA ni débitée
  par l'acheteur IA.
- Ancienne dotation annuelle IA + nouvelles finances mensuelles = double
  revenu ; l'ancienne est désactivée.
- Offres de vente : l'acheteur doit être solvable (budget, salaire, ratio).

### VALIDATION
- Nouveau `tests/test_ai_profiles.py` : 7 profils, finances cohérentes, impact
  mensuel réel, mise sur la liste en cas de découvert, style tactique,
  préférences Formateur/Riche/Guerrier.
- `tests/run_tests.py` : **16/16 ALL OK** ; `data/error.log` : **0 octet**.
- Soak 600 jours difficile L1 : 0 erreur, audit sain, effectif min 11,
  **253 transferts IA-IA**, 27 joueurs listés, budgets de 0,32 M à 7,61 M,
  aucune trésorerie négative, 5,04 buts/match.
- Soak 600 jours normal L2 : 0 erreur, audit sain, effectif min 11.
- Sauvegarde saine : `code_backups/backup_*_known_good_ai_finance/`.


---

## Annexe CL — Plafond de masse salariale (joueurs + staff)

### CALCUL
- Nouveau module **`wage_budget.py`**.
- Plafond mensuel :
  `base_division / 55 + 18 000 €`, ajusté par la réputation
  (`× 0,90 à × 1,10`), puis par la santé de la trésorerie
  (`× 0,85` si budget négatif, `× 1,05` si budget > 1,5× base).
- Arrondi à 50 €. Exemples sur une carrière neuve :
  - Ligue 1 : ~95 500 €/mois ;
  - Ligue 2 : ~64 750 €/mois ;
  - Ligue 3 : ~47 550 €/mois ;
  - Ligue 6 : ~24 200 €/mois.
- La masse salariale compte **joueurs sous contrat + staff** (remise du
  comptable incluse, comme la paie réelle).

### REGLES APPLIQUEES
- **Recrue** : `masse actuelle + nouveau salaire ≤ plafond`.
- **Prolongation interne** : `masse actuelle − ancien salaire + nouveau salaire
  ≤ plafond`. Le salaire actuel est **remplacé**, jamais cumulé ; seule la
  différence consomme la marge. Une **baisse** de salaire reste autorisée même
  si le club est au-dessus du plafond : c'est le seul moyen de revenir dans les
  clous sans vendre.
- **Prêt entrant** : contrôle à la demande et à l'acceptation.
- **Pré-contrat** : contrôle avant signature.
- **Transfert** : contrôle à l'offre et à la finalisation (salaire ajusté).
- **Staff** : embauche et formation vérifient le salaire projeté (niveau
  suivant) avant paiement. La formation terminée reste honorée.
- Si un dossier est bloqué, le message reste « à traiter » : on peut réduire
  le salaire, vendre un joueur ou refuser.

### INTERFACE
- Page Finances : ligne « PLAFOND MASSE SALARIALE • total / plafond • marge ou
  dépassement • joueurs / staff », colorée.
- Page Staff : sous-titre avec staff, total/plafond et marge.
- Fiche joueur (offre) et dialogue de prolongation : rappel de la marge et du
  remplacement de salaire.
- Les clubs IA gardent leur plafond de profil (`income × wage_ratio`) ; leur
  encadrement est inclus dans l'entretien mensuel.

### VALIDATION
- Nouveau `tests/test_wage_budget.py` : plafond, total joueurs+staff, delta de
  prolongation, refus au-delà du plafond, blocage d'une embauche staff, affichage
  finances.
- Sonde des flux réels : offre hors plafond refusée, offre normale acceptée,
  prolongation hors plafond refusée, embauche comptable acceptée dans la marge.
- `tests/run_tests.py` : **17 suites** ; les **16 suites ciblées** (hors soak
  d'équilibrage, non relancé sur consigne) passent ; `data/error.log` 0 octet.
- Soak court 45 jours : 0 erreur, audit sain, min effectif 11.
- Sauvegarde saine : `code_backups/backup_*_known_good_wage_cap/`.


---

## Annexe CM — Correction du drag du banc (QDrag)

- Erreur observée : `NameError: name 'QDrag' is not defined` dans
  `ui_components.py`, méthode `DraggableBench.startDrag`, à chaque tentative de
  glisser un joueur du banc vers le terrain.
- Cause : `QDrag` vit dans `PySide6.QtGui` et n'était plus importé après
  l'extraction des widgets ; `QMimeData` (QtCore) l'était déjà.
- Correction : `QDrag` ajouté à l'import `PySide6.QtGui` de `ui_components.py`.
- Le comportement « joueur blessé/suspendu non glissable » est conservé.
- Nouveau test `tests/test_bench_drag.py` : vérifie la présence de `QDrag`,
  simule `startDrag` (sans boucle de drag) et confirme qu'un joueur indisponible
  ne déclenche aucun drag.
- Validation ciblée : test drag OK, `test_ui_start_render`, `test_new_features`,
  smoke UI des 14 pages et 10 onglets : 0 erreur, `data/error.log` 0 octet.


---

## Annexe CN — Infrastructure lisible + centre de formation resserré

### INFRASTRUCTURE / GESTION
- L'onglet **GESTION** est désormais dans une **zone défilante** : plus de
  cartes coupées en bas de fenêtre.
- Les cartes de chantier s'adaptent à la largeur :
  - **1 colonne** sous 1080 px (petite fenêtre, lecture confortable) ;
  - **2 colonnes** au-dessus.
- Les gros boutons du panneau « FAIRE PROGRESSER LE CENTRE » ont été réduits
  (100 px au lieu de 112, pastille 68 au lieu de 78) et le texte dispose d'une
  hauteur minimale pour ne plus être écrasé sur petit écran.
- Les onglets VUE D'ENSEMBLE (déjà défilant) et GESTION restent cohérents.

### CENTRE DE FORMATION
- La page ne suit plus que les **jeunes du club, 18 ans ou moins** :
  - table « SUIVI DES JEUNES • 18 ANS OU MOINS AU CLUB » ;
  - KPI « jeunes formés au club » et « potentiels 17-20 chez les jeunes »
    limités aux jeunes actuels ;
  - tableau et compteurs rafraîchis à l'ouverture de la page.
- Le panneau **PROMOTIONS DU CENTRE • SUIVI DANS LA DURÉE** (anciens, joueurs
  vendus, plus de 18 ans) est retiré de la page et n'est plus jamais rendu
  visible.
- Le panneau du tableau de bord parle désormais de **JEUNES ACTUELS** et ne
  liste que les jeunes du club de 18 ans ou moins.
- Les anciens restent consultables via leur fiche/historique, mais plus dans le
  centre de formation.

### VALIDATION
- Nouveau `tests/test_academy_facility.py` : 17/18 ans affichés, 19 ans exclu,
  panneau des anciens absent, GESTION défilante, une seule colonne en petite
  fenêtre.
- `test_new_features.py` mis à jour : vérifie le suivi des jeunes à la place du
  panneau des anciens.
- Smoke UI des 14 pages / 10 onglets + tests ciblés : 0 erreur,
  `data/error.log` 0 octet. Le soak d'équilibrage n'a pas été relancé.
- Sauvegarde saine : `code_backups/backup_*_known_good_facility_academy/`.


---

## Annexe CO — Écran de démarrage immersif

### CE QUI CHANGE (UNIQUEMENT L'ACCUEIL)
- **Composition en deux colonnes** : identité + carrière à gauche, menu à droite.
- **Grand logo** Futsal Manager 2027 avec halo qui respire, titre
  « LA CARRIÈRE FUTSAL COMMENCE ICI ».
- **Fiche de carrière** : écusson aux couleurs du club, nom, division, saison,
  journée, date, **budget compact**, **bilan V/N/D**, dernière sauvegarde.
- **Dernières sauvegardes** : liste des 3 plus récentes, double-clic pour
  reprendre.
- **Fond immersif** : complexe du club en filigrane, projecteurs, balayage
  lumineux animé, cour de futsal en perspective et vignettage.
- **Bandeau bas** : statut (sauvegardes locales, build), **conseil tournant**
  (profil des clubs IA, prêts, plafond salarial, libre sans club, etc.) et
  crédits.
- **Menu plein panneau** : reprendre, nouvelle carrière, charger, sauvegardes,
  options, crédits, quitter.
- **Petite fenêtre** : la colonne gauche devient défilante ; plus de
  chevauchement logo/titre à 960×620.
- Aucune page du jeu, tactique, budget ou match n'est modifiée par cette étape.

### TECHNIQUE
- `StartBackdrop` : image `modelext.png` mise en cache, projecteurs et balayage
  animés à basse fréquence.
- `save_catalog` enrichi (budget, V/N/D) pour la fiche.
- `_start_screen_tick` : animation + conseil tournant, uniquement quand
  l'accueil est affiché.
- `_start_recent_open` : reprise directe d'une sauvegarde récente.
- Aucun nouvel asset requis : `logo2.png` et `modelext.png` existants.

### VALIDATION
- Nouveau `tests/test_start_screen.py` : fiche, budget, sauvegardes récentes,
  ticker, animation.
- Scénario sans sauvegarde : placeholder, liste masquée, reprise désactivée.
- `test_ui_start_render.py` : capture de l'accueil OK, logo chargé.
- `data/error.log` : 0 octet. Pas de soak long relancé.
- Sauvegarde saine : `code_backups/backup_*_known_good_start_screen/`.


---

## Annexe CP — Direction sportive par défaut et fiche club IA

### PAGE DE DÉMARRAGE DANS LE JEU
- Le jeu s'ouvre désormais sur **Direction sportive** (page 0), et non plus sur
  l'Effectif :
  - au lancement de la fenêtre ;
  - à la reprise d'une carrière ;
  - à la création d'une nouvelle carrière.
- Le titre interne du tableau de bord est aligné sur « DIRECTION SPORTIVE ».

### FICHE CLUB IA
- La fiche d'un club IA s'ouvre directement sur **EFFECTIF**, qui devient le
  premier onglet.
- L'onglet **SAISON / CLASSEMENT** n'est plus ajouté pour les clubs IA.
- Le rang/points de la fiche est masqué pour les clubs IA (plus de classement
  dans la fiche).
- Onglets restants : **EFFECTIF**, **SALLE**, **PALMARÈS**.

### EFFECTIF PLUS LISIBLE
- Bandeau de synthèse : effectif, niveau moyen, âge moyen, masse salariale,
  valeur totale, fin de contrat.
- Cartes joueurs enrichies :
  - liseré coloré par poste ;
  - nom complet, poste, âge, niveau ;
  - buts/arrêts et statut ;
  - **valeur, contrat, moral, forme** sur une seconde ligne ;
  - pastille de niveau à droite.
- Les noms de joueurs disposent de toute la largeur utile.

### DERNIERS MATCHS
- Nouveau tableau **DERNIERS MATCHS • NOMS COMPLETS** dans la fiche IA :
  - date, compétition, **club domicile complet**, score, **club extérieur
    complet** ;
  - couleurs de score selon le résultat ;
  - hauteur adaptée au nombre de matchs (plus de grande zone vide).
- Fini l'affichage à l'ancienne qui ne montrait que l'adversaire tronqué.

### VALIDATION
- Nouveau `tests/test_club_sheet_ai.py` : accueil Direction sportive, onglets IA
  sans SAISON, Effectif en premier, synthèse, tableau des derniers matchs avec
  noms complets.
- Tests ciblés : club sheet, start screen, new features, club swap, UI start :
  **OK**, `data/error.log` 0 octet. Pas de soak long relancé.
- Sauvegarde saine : `code_backups/backup_*_known_good_club_sheet/`.


---

## Annexe CQ — Palette sobre (identité club, infrastructure, navigation)

### PRINCIPE
- Nouveau helper `_mix_color(color, base="#0b1220", ratio=0.35)` : mélange
  toute couleur de club avec une base sombre avant de l'utiliser en fond ou
  en bordure. Les couleurs d'identité restent reconnaissables, sans saturation.
- Les accents violets historiques de l'interface (boutons principaux, survols,
  focus, onglets, sélections) sont remplacés par des tons ardoise.

### FICHE CLUB IA
- En-tête : dégradé de l'identité mélangé à une base sombre (`ratio` 0,24 /
  0,26), bordure atténuée et liseré gauche discret.
- Bandeau de synthèse : couleurs KPI adoucies (mauve, bleu-gris, sable, rose
  poudré, vert sauge, ocre).
- Liserés de poste : tons désaturés.
- Pied de fiche : bouton « FERMER » en ardoise (plus de violet vif).

### INFRASTRUCTURE
- Héros Gestion / Exploitation : fonds sombres, bordures et icônes atténuées.
- Accents des sections (bâtiments, services, revenus) et des cartes
  d'investissement : teintes désaturées.
- Grille de cartes : en une seule colonne, les cartes occupent désormais toute
  la largeur (plus de moitié droite vide).
- Vue d'ensemble : sièges et bandeaux LED utilisent l'identité du club
  mélangée au fond sombre ; tableau de score et lignes du terrain adoucis.

### EN-TÊTE GLOBAL ET NAVIGATION
- Bandeau supérieur : dégradé d'identité beaucoup plus sombre, liseré bas de
  2 px atténué, halo d'écusson réduit.
- Boutons `Primary`, `ContinueMain`, survols, focus, sélections de listes,
  onglets sélectionnés et steppers : ardoise au lieu du violet.
- Pastilles de navigation (messages, transferts) et tuiles d'accès rapide du
  tableau de bord : couleurs désaturées.

### VALIDATION
- Tests ciblés : fiche club IA, accueil, nouvelles fonctions, changement de
  club, rendu accueil, académie/infrastructure : **OK**.
- `data/error.log` : **0 octet**.
- Pas de soak long relancé.
- Sauvegarde saine : `code_backups/backup_*_known_good_sober/`.


---

## Annexe CR — Clubs IA crédibles : tous les socles

### NOUVEAU MODULE `ai_clubs.py`
Deux tables ajoutées automatiquement (`ensure_schema`) :
- `ai_club_plan` : projet d'un club IA pour la saison ;
- `ai_manager_history` : entraîneurs remerciés et raison.

Chaque club IA reçoit un projet stable mais recalculé à chaque saison :
- **ambition** : Titre, Montée, Haut de tableau, Milieu de tableau, Maintien ;
- **objectif de rang** cohérent avec la division, la réputation et l'identité ;
- **patience du board** (24–95) ;
- **entraîneur** (nom + style) conservé tant que le projet tient ;
- **dynamique** : Animé / Équilibré / Prudent ;
- **besoins** par poste, âge, niveau et fins de contrat.

L'identité du club nuance le projet :
- Riche / Spectacle visent un cran plus haut et recrutent plus ;
- Économe / Formateur / Guerrier sécurisent leur saison ;
- les profils « bâtisseurs » renouvellent davantage leurs contrats.

### MIXTE ANIMÉ / PRUDENT
La dynamique combine :
- la base du profil de club (`club_profiles.py`) ;
- l'ambition de la saison ;
- la santé financière (trésorerie, marge salariale).

Exemple de monde généré : environ 1/3 Animé, 1/3 Équilibré, 1/3 Prudent,
avec des clubs riches actifs et des clubs économes attentistes.

Effets concrets :
- **marché IA-IA** : nombre de clubs candidats, probabilité d'agir, plafond de
  transfert et effectif maximal dépendent du projet ;
- **recrutement de libres** : probabilité et priorité de poste dépendent des
  besoins réels ;
- **renouvellements de contrats** : plus fréquents dans les clubs prudents ;
- **pression du board** : mise à jour mensuelle selon le rang réel.

### ENTRAÎNEURS
- Nom et style générés de façon déterministe par club et saison.
- En fin de saison, un club qui rate nettement son objectif (ou descend) peut
  changer d'entraîneur ; l'ancien est archivé dans `ai_manager_history`.
- Le nouvel entraîneur est immédiatement visible dans la fiche club.

### FICHE CLUB IA
Nouveau bandeau compact **PROJET** :
- ambition et objectif de rang, état de la saison ;
- entraîneur et style ;
- dynamique et patience du board ;
- besoins prioritaires.

### VISIBILITÉ
- Une brève « Ambitions de la saison » est publiée à la création des projets.
- Les changements d'entraîneur et les pertes de patience produisent des news.
- Aucun spam : un entrefilet par saison, et des news seulement sur événement.

### ROBUSTESSE
- `save_catalog` tolère désormais les anciennes sauvegardes sans colonnes
  `color1`, `color2`, `budget` ou `season` (catalogue au lieu d'un abandon).
- Les projets manquants sont créés sans casser une sauvegarde existante.
- `test_ai_clubs.py` ajouté à `run_tests.py`.

### VALIDATION
- Tests courts (hors soak) : **toutes les suites OK**.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_ai_clubs/`.


---

## Annexe CS — Les projets IA parlent au joueur

### OFFRES CIBLÉES
`generate_transfer_interest` ne tire plus un acheteur au hasard :
- chaque club candidat est pondéré par son **projet** (`interest_weight`) ;
- un besoin de poste **Haute** pèse beaucoup plus qu'une simple envie ;
- les clubs **Animés** se penchent plus vite sur les dossiers ;
- Titre / Montée ajoutent un supplément d'intérêt.

Les offres (liste et spontanées) transportent désormais `interest_reason` :
« Maintien • objectif top 8 • entraîneur Diego Rossi ».
Le manager comprend pourquoi le club veut recruter.

### RUMEURS
- Une rumeur ciblée peut apparaître tous les 10 jours minimum.
- Elle oppose un club qui a un **besoin Haute** à un joueur du manager du bon
  poste : « X (projet) surveille Y pour son poste de pivot ».
- Aucune offre n'est créée : c'est de l'ambiance et de l'information.

### BOARD DU CLUB DU JOUEUR
`ensure_board_objectives` utilise maintenant le même barème que les clubs IA :
- rang de réputation dans la division ;
- ambition : Titre, Montée, Haut de tableau, Milieu de tableau, Maintien ;
- objectif de rang cohérent.

Nouveau meta `board_objective_label`, affiché :
- dans la pastille du tableau de bord (`MAINTIEN • 7e / top 8`) ;
- dans le sous-titre du board ;
- dans les messages d'avertissement du board.

Les objectifs sont recalculés à chaque nouvelle saison ; les anciennes
sauvegardes reçoivent le libellé au premier passage.

### VALIDATION
- `test_ai_clubs.py` vérifie : projets, besoins, dynamiques, changement
  d'entraîneur, objectif board aligné, offres motivées par le projet.
- Toutes les suites courtes passent.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_ai_links/`.


---

## Annexe CT — Logo logo1 et rendu des Options

### ECRAN DE DEMARRAGE
- `data/logo1.png` devient le logo prioritaire (`logo1.png`, puis `logo2.png`,
  `assets/logo.png`, dessin vectoriel, image embarquée).
- Logo affiché **grand** (340 px de haut), **centré horizontalement sur la
  colonne de gauche**, sans déformation (AspectLogo).
- Halo bleu discret adapté au logo ; la colonne gauche reste défilante sur les
  petites hauteurs d'écran.
- Le test de rendu indique désormais `data/logo1.png`.

### FENETRE OPTIONS
Refonte complète de `GameOptionsDialog` :
- format 900 × 680 (minimum 820 × 600), en-tête avec icône, titre et bouton
  **FERMER** ;
- palette sobre : ardoise au lieu du violet, accents discrets ;
- onglets **APPARENCE / MESSAGERIE / TRICHE / AIDE** ;
- chaque réglage est une carte lisible : titre, explication, contrôle à droite ;
- sections séparées (affichage, identité du club, brief, messages reçus) ;
- maillots présentés en boutons compacts ;
- messages expliqués sous chaque case à cocher (plus de textes écrasés) ;
- ascenseur vertical propre sur les onglets longs ;
- aide réécrite avec titres, listes et rappel des projets de clubs IA ;
- coups de pouce en grille, tons dorés atténués ;
- pied de page avec note d'enregistrement et boutons **ANNULER /
  ENREGISTRER**.

### VALIDATION
- Toutes les suites courtes passent.
- `data/error.log` : **0 octet**.
- Captures vérifiées en 1280 × 800 et 960 × 620.
- Sauvegarde saine : `code_backups/backup_*_known_good_logo_options/`.


---

## Annexe CU — Aide interactive complete

### CONTENU
Nouveau module `help_content.py` :
- **9 thèmes** : Démarrage, Direction sportive, Effectif, Tactiques & match,
  Entraînement & staff, Transferts, Finances & complexe, Compétitions,
  Interface & aide ;
- **26 sujets** détaillés couvrant tous les menus, écrans et actions :
  boucle de jeu, création/reprise de carrière, sauvegardes, board, messagerie,
  effectif, fiche joueur, contrats, tactiques, consignes, match en direct,
  entraînement, staff, formation, marché, négociation, prêts, clubs IA,
  finances, infrastructure, calendrier, compétitions, options, navigation,
  dépannage et glossaire.

Chaque article contient des listes d'actions, des conseils, des avertissements
et des liens vers les sujets liés.

### PANNEAU AIDE INTERACTIF
Nouveau `HelpPanel` dans `ui_components.py` :
- **sommaire par thème** dans une arborescence à gauche ;
- **recherche instantanée** multi-mots, insensible aux accents et à la casse
  (ex. « offre transfert », « salaire », « coupe ») ;
- compteur de résultats et message clair si aucun sujet ne correspond ;
- **navigation interne** : les liens « Voir aussi » ouvrent directement le
  sujet concerné, sans quitter la fenêtre ;
- bouton **TOUT** pour revenir au sommaire ;
- article d'accueil « boucle de jeu » ;
- rendu sobre : panneau sombre, sélection ardoise, conseils bleu-gris,
  avertissements ocre.

### INTEGRATION
- L'onglet **AIDE** des Options utilise désormais ce panneau complet à la place
  du texte statique.
- Le nouveau test `test_help_panel.py` vérifie le nombre de sujets, la
  recherche simple et multi-mots, le cas « aucun résultat », la navigation
  interne et l'intégration dans les Options.

### VALIDATION
- Toutes les suites courtes passent.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_help_panel/`.


---

## Annexe CV — Messagerie immersive et options enrichies

### THÈME CLAIR RETIRÉ
- Le thème « Clair » n'est plus proposé dans Options.
- Un ancien fichier d'options contenant `Clair` est automatiquement ramené
  sur « Nuit violette » au chargement.
- Les trois thèmes restants : Nuit violette, Vert futsal, Noir & or.

### OPTIONS DE MESSAGERIE
Nouvelles familles visibles / masquables :
- dossiers (transferts, contrats, prêts) ;
- rapports de scouting ;
- rapports de match ;
- vie du club et alertes ;
- bilans et transitions de saison ;
- informations système.

Nouvelle option de lecture :
- **Marquer comme lu à l'ouverture** (activée par défaut). Décochée, un message
  reste non lu jusqu'à action manuelle.
Les anciennes options restent : cadence du brief, anniversaires, performances,
blessures, staff, rappels d'offres, fins de contrat, presse.

### PAGE MESSAGERIE REFONDUE
- Hero « Centre de courrier » : messages, non lus, à traiter, dossiers.
- Barre de recherche + tri (récents, anciens, prioritaires) + historique.
- Pastilles de familles avec compteurs : Tout, Non lus, À traiter, Dossiers,
  Scouting, Matchs, Club, Saison, Presse, Système.
- Liste dessinée par un delegate dédié : carte, pastille de type, titre,
  aperçu, date, état (à traiter / attente / rapport / lu), liseré non-lu.
- Panneau de lecture enrichi : badge de type, état, titre, dates, tableau
  d'informations (joueur, club, montant, salaire, durée, projet), corps.
- Actions contextuelles : accepter, refuser, signer, voir le rapport ;
  les actions secondaires (contre-offre, fiche joueur, marquer non lu,
  supprimer) sont regroupées dans le menu **PLUS** pour éviter les boutons
  coupés.
- Marquage lu/non lu, suppression unitaire protégée pour les dossiers en
  attente, purge et « tout lu » conservés.
- Synchronisation des compteurs et des badges après chaque action.

### VALIDATION
- Nouveau `tests/test_messaging_ui.py` : compteurs, filtres, recherche, tri,
  détail, actions, marquer non lu, option de lecture, familles masquées,
  thème Clair retiré et repli des anciennes options.
- Toutes les suites courtes passent.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_messaging/`.


---

## Annexe CW — Audit visuel 1360/1000 et corrections

### MÉTHODE
- Campagne de captures hors-ligne sur base temporaire : écran de démarrage,
  **14 pages** en 1360 × 900 et 1000 × 700, Options (4 onglets), fiche club IA
  et fiche joueur.
- Aucun avancement de saison, aucun soak : uniquement rendu, navigation,
  états vides et densité d'interface.
- Mesure des temps de bascule et des rafraîchissements lourds.

### GLITCHS REPÉRÉS ET CORRIGÉS
1. **Centre de match sans rencontre** : le clic ne faisait rien (retour
   silencieux) et laissait l'écran Tactiques. Un message explicite indique
   désormais l'absence de match et la date du prochain rendez-vous.
2. **Filtres du mercato** : la rangée recherche + 6 filtres débordait à droite
   en 1000 px (et frôlait la limite en 1360). Passage sur **deux rangées**
   (recherche + grille 3 × 2 de filtres).
3. **Régression attrapée pendant l'audit** : les listes « Atout recherché » et
   « Statistiques » du mercato avaient perdu leurs valeurs lors du passage en
   grille. Restaurées : le tableau affiche de nouveau les 20 premiers joueurs
   sur 848 candidats.
4. **Accès rapides du tableau de bord** : 6 tuiles sur une seule ligne étaient
   coupées en 1000 px. Passage en **3 × 2**, icônes vectorielles au lieu des
   emojis (plus de glyphes manquants).
5. **Hero du tableau de bord** : les 4 KPI et les 4 jauges se comprimaient en
   1000 px. Le hero passe sur **deux rangées** : accueil + jauges, puis KPI.
6. **Graphe financier plat** : une série constante dessinait un énorme bloc
   vert plein. Une série plate affiche maintenant une **ligne médiane discrète**
   et la valeur, sans aplatissement.
7. **Recherche globale** : ajout d'un **debounce de 130 ms** pour éviter une
   requête à chaque frappe ; limite de scan ramenée à 800 joueurs (60 affichés).

### OPTIMISATIONS
- Tableau de bord : grille d'accès rapides, moins de widgets étirés.
- Mercato : filtres sur deux lignes, largeurs souples, valeurs restaurées.
- Finance : rendu des séries plates sans géométrie aberrante.
- Recherche : debounce + taille d'échantillon réduite.
- Messagerie : rafraîchissement mesuré à ~6 ms, marché ~29 ms,
  `refresh_all` ~78 ms.
- Bascule des pages entre ~95 et ~180 ms hors recherche (première ouverture
  de la recherche ~280 ms, contre ~290 ms avant).

### VALIDATION
- Nouveau `tests/test_visual_glitches.py` : absence de match, 6 tuiles,
  mercato alimenté, filtres complets, graphe plat, rendu des 14 pages en
  1000 × 700, debounce de recherche.
- Toutes les suites courtes passent.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_visual_audit/`.


---

## Annexe CX — Entraînement réaliste et page allégée

### PAGE
- Hero simplifié : titre, semaine, sélecteur de **modèle de semaine** et bouton
  d'enregistrement. Les actions passent sous le titre pour tenir en 1000 px.
- Bandeau de contexte : **préparateur**, **prochain match** (adversaire, date,
  J-…, domicile/extérieur), **charge de la semaine**, **forme et risque**.
- Panneau de réglages : intensité globale, focus collectif, récupération auto,
  avec l'aide sur une ligne pleine largeur.
- Les onglets **INDIVIDUEL** et **PROGRESSION** masquent le contexte et les
  réglages pour laisser toute la place aux tableaux.
- Palette d'ateliers plus sobre, sans emojis, lisible en 1000 px.
- Chaque jour est une **ligne** claire : jour, date, séance, description,
  intensité et état. Fini les sept colonnes étroites.

### PLANIFICATION PLUS RÉELLE
- Quatre modèles : **Semaine de match**, **Développement**, **Récupération**,
  **Bloc intensif**.
- Le modèle match se cale sur la date réelle du prochain match : charge en
  début de semaine, activation la veille, repos le jour du match, récupération
  après.
- La charge hebdomadaire tient compte de l'activité et de l'intensité
  (repos = 0, récupération = 0,3, séance = 1 à 3).
- Alertes si la charge dépasse 85 %, descend sous 30 % ou si une séance élevée
  est placée à moins de deux jours du match.
- La charge affichée se met à jour dès qu'un atelier ou une intensité change.
- Le préparateur, le centre de formation, le médical et le repos restent pris
  en compte par le moteur existant.

### TESTS
- Nouveau `tests/test_training_ui.py` : 7 jours, 7 ateliers, 4 modèles,
  application et charge, masquage du contexte sur les autres onglets,
  enregistrement de la semaine, modèles récupération/intensif.
- Toutes les suites courtes passent.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_training/`.


---

## Annexe CY — Calendrier mensuel d'entraînement

### LISIBILITÉ DE L'INTENSITÉ
- Les anciennes valeurs « Faible / Normale / Élevée » sont désormais affichées
  **Légère / Normale / Intense** (les valeurs moteur restent inchangées).
- Les états des jours sont explicites : **FAIT**, **À VENIR**, aucune séance.
- Plus de libellé tronqué du type « Fail / No » : combos élargis et libellés
  complets.

### CALENDRIER MENSUEL
- L'onglet **SEMAINE** est remplacé par **CALENDRIER**.
- Grille mensuelle 7 colonnes (lundi → dimanche), navigation
  **PRÉCÉDENT / AUJOURD'HUI / SUIVANT**.
- Chaque case affiche :
  - le numéro du jour ;
  - le **match** du jour (domicile/extérieur, championnat ou amical) ;
  - la séance planifiée et son intensité ;
  - l'état (fait / à venir / repos).
- Le jour courant et le jour sélectionné sont distingués visuellement.

### ÉDITION D'UN JOUR
- Clic sur une case : le panneau d'édition affiche la date, le match et la
  séance.
- Choix de l'atelier (Technique, Finition, Défense, Physique, Tactique,
  Récupération, Repos, Aucune) et de l'intensité.
- **APPLIQUER** prépare la modification, **VIDER** efface la séance.
- **ENREGISTRER** écrit les modifications en base (les séances terminées ne
  sont jamais écrasées).
- Les jours passés sont en lecture seule.

### MODÈLES DE SEMAINE
- Les modèles **Semaine de match / Développement / Récupération / Bloc
  intensif** s'appliquent à la semaine du jour sélectionné.
- Le modèle match cherche le match dans cette semaine et cale la charge :
  activation la veille, repos le jour du match, récupération après.
- La charge de la semaine et les alertes (match trop proche, charge trop haute
  ou trop basse) restent actives.

### TESTS
- `tests/test_training_ui.py` mis à jour : calendrier mensuel, édition d'un
  jour, enregistrement, modèles de semaine, navigation de mois, match visible
  dans une case.
- Toutes les suites courtes passent.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_training_month/`.


---

## Annexe CZ — Calendrier d'entraînement lisible

### CORRECTIONS VISUELLES
- Cases plus aérées : jour en 10,5 pt, séance en 8,5 pt, match en 7,5 pt,
  intensité en pastille.
- Chaque séance a un **liseré coloré** selon l'atelier (technique, finition,
  défense, physique, tactique, récupération, repos).
- Les jours de match ont un fond et un liseré dorés, avec le badge
  **MATCH / AMICAL / TERMINÉ**.
- Le jour sélectionné et le jour courant sont clairement distincts.
- Les jours sans séance affichent simplement « — » au lieu de répéter
  « Repos » partout.
- Légende dans l'en-tête du calendrier (Match / Séance / Fait).
- Boutons de navigation compacts : **‹ / AUJOURD'HUI / ›**.
- Largeur maximale du calendrier pour éviter des cases géantes sur très grand
  écran.

### INTENSITÉ
- Libellés lisibles : **Légère / Normale / Intense**.
- Les cellules affichent « FAIT » pour une séance terminée, sinon l'intensité.

### VALIDATION
- `tests/test_training_ui.py` et `tests/test_visual_glitches.py` passent.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_training_calendar/`.


---

## Annexe DA — Finitions visuelles et personnalisation

### LECTURE DES MESSAGES
- Fond du lecteur harmonisé : bleu nuit, bordure discrète, sélection ardoise.
- Le message est présenté dans une **carte** avec en-tête, badge de type, état,
  dates, tableau d'informations et corps.
- Plus de grande zone noire brute derrière le texte.

### CENTRE DE FORMATION
- Le panneau verrouillé devient un vrai **projet de club** :
  - colonne « campus à construire » avec installations, recrutement, médical
    et promotion ;
  - colonne projet avec avantages, coût et bouton d'ouverture.
- Trois cartes de synthèse sous le panneau : promotion, progression des -18,
  niveau maximum.
- Feuille de route en quatre étapes : ouvrir, structurer, former, promouvoir.
- Mise en page compacte, sans grand vide, et palette sobre.

### EFFECTIF : COLONNES PERSONNALISABLES
- Toutes les colonnes du tableau sont en mode **Interactive** : chaque largeur
  peut être agrandie ou réduite à la souris.
- Les largeurs sont mémorisées dans `meta.roster_column_widths` et restaurées
  au prochain lancement / rafraîchissement.
- Le réglage de visibilité des colonnes existant est conservé.

### OPTIONS
- Fond des onglets explicitement transparent.
- Listes déroulantes et popups en fond sombre, y compris les items et l'état
  ouvert ; plus de zones blanches sur les onglets ou les menus.

### VALIDATION
- `test_visual_glitches.py` vérifie désormais que les colonnes de l'effectif
  sont interactives et que la largeur choisie survit à un rafraîchissement.
- Toutes les suites courtes passent.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_finishes/`.


---

## Annexe DB — Calendrier : saison, amicaux et coupe

### CORRECTION DU VIDE
- La page Calendrier se rafraîchit désormais **à l'ouverture** (page 8) et à
  chaque **changement d'onglet**.
- Les listes de saison, d'amicaux et de coupe ne restent plus vides après un
  changement d'onglet ou un retour depuis une autre page.
- Ajout d'états vides explicites : « Aucun match dans ce filtre », « Aucun
  amical programmé », « Aucune rencontre de coupe ».

### ONGLET SAISON
- Double panneau liste / rapport conservé et élargi.
- Lecteur de rapport en fond sombre, plus de grande zone blanche.
- Filtre PROCHAINS / RÉSULTATS / TOUT et sélection automatique du prochain
  match ou du dernier rapport.

### ONGLET AMICAUX
- Programmeur d'amical en haut (date, niveau, adversaire, quota, suggestions).
- En dessous : **liste des amicaux à gauche** et **rapport à droite**.
- Plus de lecture empilée sous la liste : meilleure visibilité.
- Message clair quand aucun amical n'est programmé.

### ONGLET COUPE
- En-tête de parcours conservé.
- Liste des tours à gauche, rapport à droite.
- Fond sombre homogène pour les listes et le lecteur.
- État vide explicite quand la coupe n'a pas encore commencé.

### FINITIONS
- Listes du calendrier forcées en fond bleu nuit (viewport compris), plus de
  flash blanc sur les listes vides ou les onglets.
- Correction d'une règle CSS globale qui pouvait casser les fonds des listes
  et des menus.

### VALIDATION
- `test_visual_glitches.py` vérifie que la liste de saison est remplie à
  l'ouverture, après changement d'onglet, et que les onglets amicaux/coupe
  restent fonctionnels.
- Toutes les suites courtes passent.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_calendar/`.


---

## Annexe DC — Check visuel global et sobriété

### AUDIT
- Captures de toutes les pages en **1360×900** et **1000×700**, plus Options,
  fiches club et joueur.
- Recherche des accents trop saturés, boutons néon, zones blanches et
  incohérences de fond.

### CORRECTIONS
- **Bouton CONTINUER** de la barre latérale : vert néon remplacé par un vert
  sauge sombre, texte clair.
- **Bouton REPRENDRE** de secours : même palette.
- **Pulsation MATCHDAY** : plus de halo vert fluo ; respiration discrète en
  sauge, bordure fine.
- **Graphes financiers** : vert/rouge vifs remplacés par sauge et rose poudré,
  courbe bleu-gris.
- **Classement / compétitions** :
  - zones promotion / relégation / champion adoucies ;
  - préfixes emoji remplacés par CHAMPION / MONTÉE / DESCENTE ;
  - liseré des clubs mélangé à une base sombre hors club du joueur.
- **Emblème du calendrier** : violet saturé remplacé par ardoise.
- **Titres de section** et badges : vert menthe atténué.
- **Barres d'attributs joueur** : dégradé vert adouci.
- **Options** : onglets et listes déroulantes sur fond sombre transparent,
  sans zones blanches.

### VALIDATION
- Toutes les suites courtes passent.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_sober_audit/`.


---

## Annexe DD — Centre de formation clarifié et calendrier sans popups

### CENTRE DE FORMATION
- Sous-titre plus explicite : « 1 à 3 jeunes par saison • installations,
  médical et staff ».
- Suppression du grand terrain générique qui n'avait aucun rapport avec un
  centre de formation.
- Nouveau tableau de bord du centre :
  - grande carte « NOTE DU CENTRE » avec quatre barres lisibles :
    centre de formation, pôle médical, préparateur, recruteur ;
  - prochaine génération affichée clairement ;
  - panneau d'actions à droite : installations, médical, staff, investissement ;
  - tableau des jeunes conservé en bas.
- Hauteur du bloc central maîtrisée : plus de grand vide vertical entre la
  synthèse et le tableau des jeunes.
- Panneau verrouillé conservé sous forme de projet de club (campus, avantages,
  coût, feuille de route).

### CALENDRIER / FENÊTRES
- Le champ de date des amicaux n'ouvre plus de calendrier natif intempestif :
  la saisie se fait au clavier ou via les dates libres suggérées.
- Objectif : éviter les petites fenêtres qui s'ouvrent et se ferment pendant
  le chargement de la page Calendrier.
- Les listes Saison / Amicaux / Coupe restent en fond sombre et se rafraîchissent
  à l'ouverture et au changement d'onglet.

### VALIDATION
- Toutes les suites courtes passent.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_academy_clean/`.


---

## Annexe DE — Centre de transfert lisible et centre de formation clarifié

### CENTRE DE TRANSFERT
- Le tableau passe de **12 à 16 colonnes** :
  État, N°, Joueur, Club, Poste, Âge, Nationalité, Niveau, Potentiel, Forme,
  Contrat, Valeur, **Ligue, Salaire, Scout, Moral**.
- Colonnes redimensionnables, largeurs compactes, en-têtes plus lisibles,
  lignes sans retour à la ligne et hauteur de ligne plus aérée.
- Le tableau occupe **toute la largeur** : le panneau de détail est masqué par
  défaut et s'ouvre avec le bouton **DÉTAIL / OFFRE**.
- Styles dédiés : fond bleu nuit, alternance de lignes, sélection ardoise,
  en-têtes sombres.
- Le panneau de négociation/scouting reste accessible en un clic ; il ne
  comprime plus le tableau.
- Filtres sur deux rangées, recherche pleine largeur, pagination conservée.

### CENTRE DE FORMATION
- Sous-titre explicite : « 1 à 3 jeunes par saison • installations, médical
  et staff ».
- Suppression du terrain générique sans rapport avec le centre.
- Vue débloquée : carte **NOTE DU CENTRE** avec quatre barres
  (centre, médical, préparateur, recruteur), prochaine génération, panneau
  d'actions à droite et tableau des jeunes.
- Vue verrouillée : projet de club (campus, avantages, coût, feuille de route)
  sans grand vide.
- Hauteur du bloc central limitée pour remonter le tableau des jeunes.

### CALENDRIER
- Le sélecteur de date des amicaux n'ouvre plus de calendrier natif
  intempestif : saisie clavier ou dates suggérées.
- Objectif : supprimer les petites fenêtres qui apparaissaient/disparaissaient
  au chargement.

### VALIDATION
- `test_visual_glitches.py` vérifie les 16 colonnes du mercato et le
  repli/dépli du panneau détail.
- Toutes les suites courtes passent.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_transfer_academy/`.


---

## Annexe DF — Optimisation du match 2D

### RENDU
- **Cache du terrain** : lignes, zones, buts et fond sont dessinés une seule
  fois dans un QPixmap, puis simplement recopiés à chaque frame. Le terrain
  n'est plus reconstruit 30 fois par seconde.
- Le cache est invalidé uniquement au redimensionnement ou au changement de
  ratio d'écran.
- `WA_OpaquePaintEvent` + `WA_NoSystemBackground` : Qt ne repeint plus le fond
  du parent derrière le terrain.
- Les maillots restent mis en cache par taille (cache déjà existant).

### ANIMATION
- L'animation s'arrête automatiquement quand le terrain n'est plus visible.
- Elle ne démarre plus si le widget n'a jamais été affiché.
- `reset_teams` coupe le timer pour éviter qu'une ancienne rencontre continue
  à animer la nouvelle.
- La boucle conserve son plafond de vitesse et son arrêt automatique quand
  tout est stabilisé.

### NETTOYAGE
- Suppression d'un doublon de `_update_training_load_ui`.
- Correction d'une règle CSS globale qui contenait des `\n` littéraux et
  pouvait casser les fonds de listes/menus.
- Vérification `compileall` sur tout le projet.

### VALIDATION
- `test_match_pitch2d.py` et `test_motion_step.py` passent.
- Toutes les suites courtes passent.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_match_perf/`.


---

## Annexe DG — Bandeau d'identité unique sur toutes les pages

### PRINCIPE
- Un seul en-tête par page, commun à toutes les pages principales :
  icône vectorielle dans un médaillon, titre, sous-titre, fond bleu nuit
  dégradé, liseré ardoise et coins arrondis.
- Style repris du bloc « Personnel du club » : c'est désormais l'identité
  visuelle du jeu.
- Le sous-titre peut être dynamique (nombre de joueurs, résumé du courrier,
  masse salariale du staff) sans ajouter un second bandeau.

### DOUBLONS SUPPRIMÉS
- Direction sportive : titre interne « DIRECTION SPORTIVE » retiré.
- Effectif : bandeau « ÉQUIPE PREMIÈRE » retiré, son résumé passe en
  sous-titre de page.
- Entraînement : titre interne « PLAN D'ENTRAÎNEMENT » retiré, les actions
  restent dans une barre compacte.
- Infrastructure : emblème et titre « LE COMPLEXE DU CLUB » retirés, les
  jauges restent.
- Messagerie : titre « CENTRE DE COURRIER » retiré, le bandeau ne garde que
  la synthèse (non lus, à traiter, dossiers).
- Transferts : emblème, « CENTRE DE RECRUTEMENT » et son sous-titre retirés ;
  la fenêtre de mercato et le budget restent.
- Calendrier : bandeau « SAISON EN DIRECT » retiré ; le classement devient le
  sous-titre et le bouton « RAPPORT RÉCENT » rejoint la ligne des KPI.
- Finances : titre « CENTRE DE CONTRÔLE FINANCIER » retiré, l'équilibre et le
  solde restent.
- Personnel du club : le grand bloc interne devient le bandeau commun, avec
  la masse salariale à droite.
- Centre de formation : « ÉTAT DU CENTRE DE FORMATION » retiré, la note et la
  jauge restent. Le composant « Centre de formation » de la note est renommé
  « Installations » pour rester lisible.
- Compétitions : titre « COMPÉTITION • TABLEAU OFFICIEL » retiré, le
  sélecteur de division reste dans une barre compacte.

### FINITIONS
- Liserés latéraux résiduels retirés des bandeaux secondaires.
- Un seul ajout du conteneur du centre de formation (doublon de layout).
- Bouton « RAPPORT RÉCENT » dimensionné pour rester lisible en 1000 px.

### VALIDATION
- `test_visual_glitches.py` vérifie désormais, sur les 14 pages :
  présence du bandeau `PageHero`, titre attendu, et absence de tout autre
  libellé identique (pas de titre en double).
- Toutes les suites courtes passent.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_page_headers/`.


---

## Annexe DH — Aide des options : rendu visuel soigné

### EN-TÊTE
- Nouveau bandeau « CENTRE D'AIDE » : pastille « ? » dessinée en vectoriel,
  titre, sous-titre court et champ de recherche intégré.
- Loupe dessinée en vectoriel (aucune dépendance à une police d'icônes).
- Champ de recherche plus haut, bordure accentuée au focus, bouton d'effacement.

### SOMMAIRE
- Les thèmes portent une **puce de couleur discrète** et une ligne plus aérée.
- Un seul thème est déplié : celui du sujet consulté (ou tous les résultats
  pendant une recherche).
- Clic sur un thème : ouverture/fermeture. La sélection utilise une palette
  ardoise, plus le bleu système.
- Compteur de sujets compact dans l'en-tête du sommaire.
- Bouton « REVENIR AU SOMMAIRE » en bas du panneau, plus lisible que l'ancien
  bouton « TOUT ».

### ARTICLE
- Marges internes de lecture (18 px), interlignage plus généreux.
- Titres, sous-titres, listes, liens et encadrés `tip`/`warn` retravaillés.
- Eyebrow « AIDE • THÈME » conservé, plus lisible.
- État vide centré : grand « ? » discret, message clair et suggestions de
  mots-clés.

### INTÉGRATION
- Marges du panneau pour éviter le double cadre avec l'onglet des options.
- Le panneau reste autonome (aucune dépendance à app.py).
- Compatible avec la recherche instantanée, la navigation par liens et
  l'onglet AIDE des options.

### VALIDATION
- `test_help_panel.py` vérifie le bandeau, la loupe, les puces de thème et
  l'eyebrow de l'article.
- Toutes les suites courtes passent.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_help_ui/`.


---

## Annexe DI — Messagerie : vraie boîte mail du club

### IDENTITÉ
- Le club possède une **fausse adresse** : `direction@<nom-du-club>.fm`,
  affichée dans le bandeau de page, dans le compte du rail et dans chaque
  message (« à … »).
- Chaque message a un **expéditeur crédible** : club acheteur, cellule de
  recrutement, staff technique, président, staff médical, ligue, presse,
  système, avec adresse fictive et initiales.

### TROIS COLONNES
- **Rail des dossiers** à gauche : compte du club, compteurs (non lus,
  à traiter, dossiers), puis sections « Courrier » et « Dossiers ».
  - Boîte de réception, Non lus, À traiter ;
  - Dossiers, Scouting, Matchs, Club & alertes, Saison, Presse, Système ;
  - Historique et Purger en bas.
- **Liste au centre** : recherche + tri, titre du dossier et compteur,
  lignes type e-mail (avatar d'initiales, expéditeur, objet, aperçu, date,
  point d'état, liseré non-lu).
- **Lecture à droite** : en-tête expéditeur/adresse/date/état, objet,
  tableau de faits, corps du message et **signature** en pied.

### RESPONSIVE
- Grand écran : rail visible.
- Fenêtre étroite (moins de 1180 px) : le rail disparaît, un **sélecteur de
  dossier** prend sa place et le tri devient un bouton-menu compact.
- Plus de barre de défilement horizontale dans la liste.

### CONSERVÉ
- Filtres par famille, recherche instantanée, tri (récent / ancien /
  prioritaire), marquage lu/non lu, actions contextuelles (accepter,
  refuser, contre-offre, fiche joueur, supprimer), historique et purge.
- Les options de messagerie (familles, lecture) restent inchangées.

### VALIDATION
- `test_messaging_ui.py` vérifie l'adresse du club, les compteurs de
  dossiers, les expéditeurs, le rail, le mode étroit et le sélecteur.
- Toutes les suites courtes passent.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_mail_client/`.


---

## Annexe DJ — Classement : couronne de champion honnête

### RÈGLE
- Le mot « CHAMPION » n'est plus écrit devant le premier : une **couronne
  vectorielle** le remplace, et seulement quand le titre est réellement acquis.
- Titre acquis si :
  - la saison est terminée (plus aucun match à jouer), ou
  - le premier ne peut plus être rejoint : pour chaque poursuivant,
    `points + 3 × matchs restants < points du leader`.
- En cours de saison, le premier reste dans la zone de promotion (ou neutre
  en division 1) sans couronne.

### AFFICHAGE
- Couronne dessinée en vectoriel (aucune dépendance à une police d'icônes),
  placée devant le nom du club, avec l'infobulle « Champion — titre acquis ».
- Légende revue : couronne + CHAMPION, flèche haut + PROMOTION, flèche bas +
  RELÉGATION, toutes dessinées en vectoriel.

### CODE
- Nouvelle méthode `_champion_is_clinched(standings, remaining, remaining_known)`,
  testable et réutilisable.
- Les matchs restants sont comptés depuis les fixtures de championnat non
  jouées de la division affichée.

### VALIDATION
- `test_visual_glitches.py` vérifie : pas de couronne tant que le titre n'est
  pas acquis, couronne présente ensuite, et aucun texte « CHAMPION » dans la
  ligne du club.
- Toutes les suites courtes passent.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_champion_crown/`.


---

## Annexe DK — Calendrier, centre de formation et direction sportive

### CALENDRIER — FENÊTRES FANTÔMES
- Cause : les cartes de match étaient détachées de leur liste
  (`setParent(None)`) avant d'être supprimées ; Qt les affichait alors comme
  de vraies fenêtres top-level (icône Python) le temps d'une frame.
- Correction : les widgets d'items sont **masqués**, retirés de la liste puis
  détachés avant `deleteLater` ; ils sont aussi reparentés à la vue **avant**
  d'être ajoutés.
- Résultat : plus aucune fenêtre ne s'ouvre/se ferme en parcourant le
  calendrier, le classement ou les autres listes à cartes.

### CENTRE DE FORMATION
- Vue verrouillée : le suivi des jeunes reste affiché et remplit le bas de
  page ; plus de grand vide.
- Le panneau projet ne déborde plus à 1000 px : coût et bouton tiennent dans
  la largeur, le titre ne chevauche plus l'icône.
- Vue ouverte : les leviers sont plus compacts (libellés courts, boutons
  réduits) et le corps a une hauteur stable ; le suivi des jeunes ne passe
  plus sous les panneaux.
- La page défile proprement au lieu de comprimer/chevauchement les cartes.

### DIRECTION SPORTIVE
- Le bloc dirigeants / supporters / moral / réputation passe sur **une seule
  ligne**, sous un libellé « CLIMAT DU CLUB ».
- Le texte d'accueil occupe la ligne au-dessus ; les quatre jauges prennent
  toute la largeur disponible.
- Plus de grand vide à gauche ; les cartes Budget / Points / Bilan / Effectif
  restent juste en dessous.

### MISE EN PAGE GÉNÉRALE
- La hauteur de la zone défilante tient compte du `sizeHint` de la page
  courante : les panneaux ne sont plus écrasés quand des libellés passent à
  la ligne.

### VALIDATION
- Contrôle des fenêtres top-level sur 11 pages : **0 fenêtre fantôme**.
- Toutes les suites courtes passent.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_calendar_academy_dashboard/`.


---

## Annexe DL — Entraînement : calendrier sur 2 semaines

### AFFICHAGE
- Le calendrier mensuel (4 à 5 lignes de petites cases) est remplacé par
  **2 semaines = 14 jours**, sur 2 lignes de 7.
- Les cases s'étirent pour remplir le panneau : jours plus grands, séances et
  matchs plus lisibles.
- Libellé d'en-tête : « 2 SEMAINES • 29 JUIN → 12 JUIL. 2026 ».
- Une case sans séance affiche « Aucune séance » au lieu d'un simple tiret.

### NAVIGATION
- Précédent / Suivant déplacent la fenêtre de **14 jours**.
- « AUJOURD'HUI » revient à la semaine en cours (lundi → dimanche).
- Les données (matchs, séances, modifications en attente) sont chargées sur
  exactement la fenêtre affichée.

### COMPACITÉ
- Le bandeau du haut tient sur une seule ligne : libellé + modèle + appliquer +
  enregistrer.
- À 1360 × 900, les 2 semaines et l'éditeur du jour sont visibles sans
  défilement.

### VALIDATION
- `test_training_ui.py` vérifie 14 cases, la navigation de 14 jours, le retour
  à aujourd'hui, l'édition et l'enregistrement d'une séance.
- Toutes les suites courtes passent.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_training_fortnight/`.


---

## Annexe DM — Infrastructure : intérieur et extérieur retravaillés

### PANNEAU LATÉRAL COMMUN
- Nouveau bloc à droite du stade, visible en INTÉRIEUR comme en EXTÉRIEUR :
  - « TRAVAUX EN COURS » : places occupées, une carte par chantier avec
    libellé, jours restants, barre de progression et avancement ;
  - « SERVICES DU STADE » : Loges VIP, Bar, Boutique avec statut
    OUVERT / À CONSTRUIRE ;
  - dernier chantier livré en pied de panneau.
- Fenêtre étroite (< 1180 px) : le panneau se masque pour laisser toute la
  largeur au stade ; les travaux restent dans l'onglet Gestion.

### INTÉRIEUR
- Les chantiers ne s'affichent plus avec une grande barre au-dessus du terrain :
  seul un contour doré discret reste, le détail vit dans le panneau latéral.
- Loge VIP redessinée : bloc doré avec auvent, sièges et pastille « VIP »,
  intégré à la tribune latérale.

### EXTÉRIEUR
- Suppression de la grue dessinée et de la pastille chantier flottante.
- Contour de chantier plus fin, vue plus sobre et plus aérée.
- Le plan du complexe profite de la largeur libérée.

### VALIDATION
- `test_infra_save_ui.py` vérifie le panneau latéral, les cartes de chantier
  et les statuts VIP / bar / boutique.
- Toutes les suites courtes passent.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_facility_visual/`.


---

## Annexe DN — Relecture de code et corrections

### BUG RÉEL TROUVÉ ET CORRIGÉ
- **Entraînement** : en déplaçant le libellé de quinzaine dans le calendrier,
  le calcul de `week_rows`/`planned` avait disparu alors que le bloc KPI
  l'utilisait encore. L'erreur était avalée par le `except` et n'apparaissait
  que dans le journal. Calcul restauré ; le KPI de charge est de nouveau rempli.
- Ajout d'une assertion de test sur `training_kpi_load` pour empêcher ce type
  de régression silencieuse.

### INCOHÉRENCES NETTOYÉES
- Entraînement : `TrainingMonthCalendar` → `TrainingFortnightCalendar`,
  `_training_month_data` → `_training_window_data`,
  `_training_month_move` → `_training_window_move`.
  Suppression des attributs année/mois devenus inutiles.
- Le libellé du haut suit maintenant la navigation de quinzaine (il restait
  figé auparavant).
- Messagerie en mode étroit : « Historique » et « Purger » redeviennent
  accessibles via un menu d'actions compact (le rail étant masqué).
- Menu de la messagerie : connexions protégées contre l'argument booléen de
  `QAction.triggered`.
- En-tête Centre de formation : icône dédiée (chapeau) au lieu du bâtiment
  partagé avec Infrastructure.

### VÉRIFICATIONS
- `compileall` sur tout le projet : OK.
- Aucun doublon de définition de fonction/classe détecté (AST).
- Aucune référence aux anciens noms supprimés (`roster_title`,
  `squad_header`, `market_title`, `training_calendar_month`, etc.).
- Smoke test complet : 14 pages, onglets Infrastructure, calendrier
  d'entraînement, dossiers/recherche/tri de la messagerie, onglets
  Compétitions, Options/Aide, rendu en 1360 et 1000 px.
- Journal applicatif réel : **0 octet**, aucune exception avalée.
- Toutes les suites courtes passent.
- Sauvegarde saine : `code_backups/backup_*_known_good_code_review/`.


---

## Annexe DO — Direction sportive allégée

### SUPPRIMÉ
- Les **raccourcis rapides** vers Effectif, Transferts, Centre de formation,
  Finances, Messagerie et Centre de match.
- Le **centre de notifications** (panneau, résumé et rafraîchissement dédié).
- Le code mort associé (`quick_tile`, `_quick_buttons`,
  `refresh_notification_center`).

### CLIMAT DU CLUB
- Les quatre jauges sont regroupées dans un **panneau arrondi** avec un
  dégradé sombre, un liseré et un sous-titre explicite.
- Chaque jauge devient une **carte arrondie** avec une couleur d'accent
  propre : dirigeants (sauge), supporters (bleu), moral (ambre), réputation
  (violet).
- Barres plus épaisses, coins arrondis, meilleure respiration.

### VALIDATION
- `test_visual_glitches.py` vérifie la disparition des raccourcis et du centre
  de notifications, et la présence du panneau Climat.
- Smoke test complet : 0 exception, journal applicatif réel à 0 octet.
- Toutes les suites courtes passent.
- Sauvegarde saine : `code_backups/backup_*_known_good_dashboard_clean/`.


---

## Annexe DP — Messagerie : fond de message nettoyé

### CAUSE
- Le séparateur avant le corps du message était un `<div>` avec
  `height:1px;background:#22344c`. Le moteur de texte de Qt ignore `height`
  sur un bloc vide et peignait ce fond sur une zone bien plus haute,
  donnant l'impression que le paragraphe était sélectionné.

### CORRECTION
- Le bloc est remplacé par un filet `<hr>` fin. Le corps du message repose
  désormais sur le fond normal de la zone de lecture.
- Aucun autre changement de la messagerie.

### VALIDATION
- Contrôle pixel : le fond derrière le corps est `#0c1622` comme le panneau.
- `test_messagerie.py`, `test_messaging_ui.py`, `test_visual_glitches.py`
  et le smoke complet passent.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_mail_body/`.


---

## Annexe DQ — Tactiques : terrain à la verticale

### TERRAIN
- Le terrain passe en **portrait 1:2** (environ 230 × 460 px à 1360).
- Buts en haut et en bas, ligne médiane horizontale, surface et points de
  penalty adaptés à l'orientation.
- Attaque vers le haut, défense vers le bas : le libellé du bandeau suit
  (« ATTAQUE ▲ • DÉFENSE ▼ »).
- Les tuiles de joueurs sont repositionnées sur trois colonnes et cinq lignes
  de profondeur, sans chevauchement.

### BANC ET AGENCEMENT
- Le panneau du terrain est limité en largeur ; le **banc récupère l'espace**
  (environ 620 px à 1360 contre 330 px pour le terrain).
- Les lignes du banc sont plus larges et plus lisibles ; recherche, tri et
  aperçu respirent.
- Suppression du libellé redondant « GLISSER-DÉPOSER » dans l'en-tête du
  terrain.
- Le splitter est recalculé à l'ouverture et au redimensionnement pour
  conserver ce rapport terrain/banc.

### VALIDATION
- `test_visual_glitches.py` vérifie le terrain vertical et un banc plus large
  que le terrain.
- Toutes les suites courtes passent ; smoke complet sans exception.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_tactics_vertical/`.


---

## Annexe DR — Entraînement : aujourd'hui, cartes et progression visuelle

### CALENDRIER
- La fenêtre de 2 semaines démarre désormais à la **date du jour en jeu**,
  plus au lundi de la semaine : plus de séances passées affichées.
- Les en-têtes de jours sont dynamiques (ils suivent la date de départ).
- « Précédent » est désactivé quand la fenêtre commence aujourd'hui ;
  la navigation reste par quinzaine.
- La date sélectionnée est ramenée à aujourd'hui si elle était dans le passé.

### INDIVIDUEL
- Le tableau est remplacé par des **cartes joueur** :
  avatar, nom, poste, âge, niveau, potentiel, focus individuel, barre de forme,
  progression sur 30 jours et bouton FICHE.
- Cartes sur **2 colonnes** en grand écran, **1 colonne** en fenêtre étroite,
  avec réagencement au redimensionnement.

### PROGRESSION
- Le tableau est remplacé par des **cartes de progression** :
  avatar, nom, poste/âge/niveau, total de points gagnés et cinq barres
  d'attributs (TEC, PAS, FIN, DEF, ENDU) avec valeur actuelle et delta 30 jours.
- Les KPI (points gagnés, joueurs en progression, meilleure montée) restent.
- Même logique de colonnes que l'individuel et accès direct à la fiche joueur.

### VALIDATION
- `test_training_ui.py` vérifie la première date du calendrier >= aujourd'hui,
  le retour à aujourd'hui, et la présence des cartes dans les deux onglets.
- Toutes les suites courtes passent ; smoke complet sans exception.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_training_cards/`.


---

## Annexe DS — Infrastructure : VIP, travaux et extérieur

### VIP INTÉRIEUR
- La loge VIP ne couvre plus une grande partie de la tribune : petite plaque
  dorée compacte (environ 18 % de la hauteur de la tribune), liseré et texte
  « VIP » réduits.
- Les sièges et la grande pastille qui débordaient dans la zone de texte sont
  supprimés.

### TRAVAUX EN COURS
- Les cartes répétées (« Tribunes niv 2 • J-0 • 0 % • 0/5 ») venaient
  d'anciennes cartes non détruites immédiatement lors du rafraîchissement,
  pas des emplacements libres.
- Les anciennes cartes sont désormais **masquées et détachées** avant
  suppression, et les projets sont **dédoublonnés par identifiant**.
- Le panneau affiche donc une seule carte par chantier réel.
- Test ajouté : deux rafraîchissements successifs ne doivent pas empiler les
  cartes.

### EXTÉRIEUR
- Suppression de **tous** les effets de chantier sur la vue 2D : contour
  pointillé, grue, échafaudage et barre de progression.
- Le plan du complexe reste propre ; les travaux sont uniquement listés dans
  le panneau latéral.

### VALIDATION
- `test_infra_save_ui.py` vérifie le panneau latéral et l'absence d'empilement.
- Toutes les suites courtes passent ; smoke complet sans exception.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_facility_clean/`.


---

## Annexe DT — Centre de formation : tableau de bord campus

### NOUVELLE STRUCTURE
- **Bandeau campus** en haut : note du centre sur 100 avec jauge, statut,
  prochaine génération et bouton d'ouverture quand le campus est fermé.
- **Trois colonnes** en dessous :
  1. **Moyens du centre** : installations, pôle médical, préparateur,
     recruteur (barres + valeurs) puis les leviers d'action.
  2. **Projet du campus** : statut, carte « campus à construire » quand il est
     fermé, puis feuille de route en quatre étapes.
  3. **Jeunes au club** : tableau des moins de 18 ans, avec état vide explicite.
- **Promotions** en bas, pleine largeur, uniquement quand il y en a.

### RESPONSIVE
- 3 colonnes en grand écran (≥ 1180 px).
- 2 colonnes en fenêtre moyenne : Moyens + Projet, puis Jeunes en pleine largeur.
- 1 colonne en fenêtre étroite.
- Réagencement automatique à l'ouverture et au redimensionnement.

### ÉTATS
- Campus fermé : le bandeau et les trois colonnes restent visibles ; la carte
  projet, les avantages et le bouton d'ouverture apparaissent dans la colonne
  centrale.
- Campus ouvert : la carte projet disparaît, la feuille de route et les moyens
  restent ; le bouton d'ouverture est masqué.
- Aucun jeune : message d'attente à la place du tableau vide.

### VALIDATION
- `test_academy_facility.py` et `test_new_features.py` adaptés à la nouvelle
  visibilité (bandeau toujours visible, contenu projet masqué à l'ouverture).
- Toutes les suites courtes passent ; smoke complet sans exception.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_academy_dashboard/`.


---

## Annexe DU — Transferts : offres envoyées / reçues en cartes

### OBJECTIF
Remplacer les tableaux denses de l'onglet OFFRES par deux colonnes de cartes
lisibles, avec les actions directement sur chaque dossier.

### STRUCTURE
- **Bandeau compact** : budget transferts, prochaine échéance et option
  « afficher les dossiers clos ». Plus de second grand en-tête.
- **Deux colonnes** :
  1. **NOS DÉMARCHES** : achats envoyés, puis contrats internes séparés par un
     intertitre « CONTRATS INTERNES ».
  2. **OFFRES REÇUES** : offres des clubs sur notre effectif.
- Chaque **carte** affiche : avatar, joueur, club, statut coloré, offre,
  salaire, durée, échéance, puis les actions utiles.
- Actions inline : **OUVRIR**, **CONTRE**, **REFUSER**, **ACCEPTER** selon
  l'état du dossier.
- Titres de colonnes enrichis des compteurs actifs.

### ÉTATS VIDES
- Aucun achat ni contrat : message d'attente + bouton **EXPLORER LE MARCHÉ**.
- Aucune offre reçue : message d'attente explicite.
- Les états vides sont conservés et réutilisés (pas de référence morte).

### RESPONSIVE
- Deux colonnes au-delà de 1180 px.
- Une colonne en dessous : « Nos démarches » puis « Offres reçues ».
- Barres de défilement discrètes, listes défilantes indépendantes.

### COMPATIBILITÉ
- Les anciens tableaux (`offers_out_table`, `offers_contract_table`,
  `offers_in_table`) restent remplis mais invisibles : sélection, ouverture
  et rafraîchissement continuent de fonctionner.
- Les anciens labels vides et boutons historiques restent présents et masqués.

### VALIDATION
- Nouveau test court `tests/test_offers_cards.py` : cartes, actions inline,
  refus depuis une carte, refresh répétés, bascule 2 → 1 colonne.
- Toutes les suites courtes passent ; smoke complet sans exception.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_offers_cards/`.


---

## Annexe DV — Direction sportive : bandeau compact

### OBJECTIF
Faire tenir toute la page Direction sportive dans la fenêtre, sans défilement,
en réduisant le bandeau d'accueil et la carte « Prochain match ».

### BANDEAU D'ACCUEIL
- Le message de bienvenue est intégré à la ligne « CLIMAT DU CLUB ».
- Les quatre jauges (dirigeants, supporters, moral, réputation) restent sur
  une seule rangée.
- Les quatre statistiques passent en cartes compactes de 54 px :
  intitulé, valeur et sous-titre resserrés.
- Le sous-titre du budget affiche un flux court : « Flux : +1,25 M€ / -980 k€ ».

### OBJECTIFS DU BOARD
- Une seule ligne : titre, trois pastilles courtes et score de confiance.
- Libellés raccourcis et compressibles, avec info-bulle pour le détail.
- Plus de largeur minimale excessive : la page ne déborde plus horizontalement.

### PROCHAIN MATCH
- Carte ramenée à 160 px maximum (au lieu de 220).
- Écussons 36 px, nom du match en 10,5 pt, textes et marges resserrés.
- Le panneau « Actualités » suit la même hauteur.

### HÉRITAGE ET RECORDS
- Records réorganisés en 3 colonnes × 2 lignes.
- Palmarès, compteur de titres et marges compactés.
- Panneaux limités à 200 px.

### JOUEURS EN VUE
- Bandeau ramené à 112 px, tuiles plus denses.

### VALIDATION
- Nouveau test court `tests/test_dashboard_fit.py` : à 1360×900, la page tient
  exactement dans la pile, sans défilement vertical ni horizontal.
- Toutes les suites courtes passent ; smoke complet sans exception.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_dashboard_fit/`.


---

## Annexe DW — Tactiques : terrain horizontal large et banc enrichi

### PROBLÈME
Le terrain vertical était étroit, les tuiles affichaient des noms tronqués et des
initiales, et le banc laissait un grand vide à droite de la page.

### TERRAIN
- Retour à un **terrain horizontal 2:1**, orienté défense à gauche / attaque à droite.
- Le panneau du terrain occupe désormais ~68 % de la largeur disponible.
- Tuiles joueurs agrandies (jusqu'à 208 px de large) avec :
  poste, nom, note /20, forme et **TEC · FIN · DÉF**.
- Le splitter remplit toute la largeur : plus de colonne vide à droite.
- Poignée de séparation de 10 px entre terrain et banc.

### BANC
- Cartes de joueur agrandies à **76 px**.
- Trois lignes d'informations :
  1. nom et numéro,
  2. poste, âge, contrat,
  3. **TEC · PAS · FIN · DÉF · END · MOR**.
- Pastille de note et forme conservées à droite.
- L'aperçu du joueur sélectionné affiche les mêmes statistiques + le salaire.

### RESPONSIVE
- Fenêtre large : terrain à gauche, banc à droite.
- Fenêtre étroite (< 1080 px de contenu) : terrain au-dessus, banc en dessous,
  terrain toujours horizontal et lisible.

### VALIDATION
- Nouveau test `tests/test_tactics_layout.py` : largeur du splitter, terrain
  horizontal ≥ 900 px, tuiles ≥ 150 px, statistiques sur le terrain, six
  statistiques sur le banc, bascule responsive.
- `test_visual_glitches.py` adapté au terrain horizontal.
- Toutes les suites courtes passent ; smoke complet sans exception.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_tactics_wide/`.


---

## Annexe DX — Match 2D : affichage restauré

### CAUSE
Le cache du terrain 2D (`Pitch2DWidget._paint_court`) crée un `QPixmap`, mais
`QPixmap` n'était plus importé dans `match_pitch2d.py`. Chaque `paintEvent`
levait donc un `NameError`, avalé par le `try/except` défensif : le terrain
restait noir, sans joueurs ni ballon.

### CORRECTIF
- Import de `QPixmap` ajouté à `match_pitch2d.py`.
- Le cache du terrain se remplit de nouveau : lignes, zones, buts, joueurs,
  ballon et animations réapparaissent.

### NON-RÉGRESSION
- Nouveau test `tests/test_pitch_render.py` : rend le terrain hors écran et
  vérifie que les pixels du court sont verts (et non le fond noir).
- Sauvegardes des captures de match : `matchday_2d_prematch.png`,
  `matchday_2d_live.png`, `matchday_2d_fulltime.png`.
- Toutes les suites courtes passent ; smoke complet sans exception.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_match2d_fix/`.


---

## Annexe DY — Plafond de masse salariale élargi

### OBJECTIF
Le plafond était trop bas (environ 109 000 €/mois en Ligue 1) et ne tenait
compte que de la division, de la réputation et du signe du budget.

### NOUVELLE FORMULE
Le plafond mensuel combine désormais :
- **90 % des revenus mensuels estimés** (billetterie, TV, sponsors, installations),
- **2,5 % du budget disponible** par mois (matelas de trésorerie),
- **l'ambition du club** liée à sa division (2 % de la base de division),
- le tout ajusté par un **facteur de réputation** de 0,95 à 1,20.

Un plancher historique par division est conservé. Un budget négatif applique
une pénalité de 12 %.

### ORDRES DE GRANDEUR (club frais, difficulté normale)
- Ligue 1 : ~302 000 €/mois (au lieu de ~95 000 €)
- Ligue 2 : ~196 000 €/mois
- Ligue 3 : ~130 000 €/mois
- Ligue 4 : ~84 000 €/mois
- Ligue 5 : ~51 000 €/mois
- Ligue 6 : ~29 000 €/mois

### TRANSPARENCE
- `wage_budget.wage_cap_details()` expose les revenus, le budget, la
  réputation, le facteur et les composantes du calcul.
- L'infobulle du libellé « PLAFOND MASSE SALARIALE » détaille ces facteurs.

### VALIDATION
- `tests/test_wage_budget.py` vérifie que le plafond augmente avec le budget
  puis avec la réputation, et que le détail est cohérent.
- Toutes les suites courtes passent ; smoke complet sans exception.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_wage_cap/`.


---

## Annexe DZ — Entraînement : affichage simplifié et modèles automatiques

### APPLICATION DU MODÈLE
- « APPLIQUER LE MODÈLE » couvre désormais **les 2 semaines visibles**, même si
  le jour sélectionné n'est pas un lundi.
- Chaque jour reçoit la séance correspondant à sa semaine et au match de cette
  semaine.
- Le plan est **enregistré automatiquement** : plus besoin d'un second clic sur
  ENREGISTRER. Les jours passés et les séances déjà terminées sont préservés.

### AFFICHAGE SIMPLIFIÉ
- Bandeau d'accueil avec une phrase claire sur l'application automatique.
- Cartes de contexte (préparateur, match, charge, forme/risque) resserrées.
- Réglages généraux compactés, texte d'aide sur une ligne.
- Éditeur de séance avec libellés **SÉANCE** et **INTENSITÉ**, bouton
  « PROGRAMMER CE JOUR ».

### INDIVIDUEL
- Ligne de synthèse : nombre de joueurs, focus manuels et automatiques.
- Badge **AUTO / FOCUS** sur chaque joueur.
- Cartes aérées : nom, poste, âge, niveau /20, potentiel /20, focus et forme.

### PROGRESSION
- Fini les cinq micro-barres : chaque joueur affiche deux barres lisibles,
  **NIVEAU /20** et **POTENTIEL /20**.
- Gain des 30 derniers jours mis en avant à droite.
- Le détail des attributs (TEC, PAS, FIN, DÉF, END) reste disponible en
  infobulle.
- La **charge de la semaine** est désormais notée **sur 20** (plus de %).

### VALIDATION
- `tests/test_training_ui.py` vérifie l'application sur la quinzaine, sans
  sélection d'un lundi, l'enregistrement automatique et l'affichage /20.
- Toutes les suites courtes passent ; smoke complet sans exception.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_training_simple/`.


---

## Annexe EA — Infrastructure : onglet GESTION compact

### OBJECTIF
Réduire les blocs de l'onglet GESTION pour que les chantiers tiennent dans la
page sans défilement sur grand écran.

### CARTES DE CHANTIER
- Hauteur ramenée à ~68 px (au lieu de ~100).
- Icône 36 px, textes resserrés, bouton compact 118 × 30.
- Description et effet sur une seule ligne, avec le texte complet en infobulle.
- Les huit pastilles de niveau sont supprimées : la pastille **NIV. x / 8**
  suffit et reste lisible.
- Statut (coût, durée, livraison) sur une ligne.

### MISE EN PAGE
- **3 colonnes** dès 1100 px de large : 6 bâtiments sur 2 rangées, services et
  revenus hors match sur une rangée chacun.
- **2 colonnes** entre 760 et 1100 px, **1 colonne** en dessous.
- Réorganisation automatique au redimensionnement (`_reflow_facility_grids`).
- Bandeau de gestion, ligne d'explication et en-têtes de section compactés.

### RÉSULTAT
- À 1560 px et 1920 px : **aucune barre de défilement** dans GESTION.
- À 1360 px : passage en 2 colonnes, cartes lisibles ; un léger défilement
  reste possible sur les fenêtres étroites.

### VALIDATION
- Nouveau test `tests/test_facility_gestion_fit.py` : absence de défilement à
  1560 px, 3 colonnes, cartes ≤ 80 px, bascule en 2 colonnes à 1360 px.
- Toutes les suites courtes passent ; smoke complet sans exception.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_infra_compact/`.


---

## Annexe EB — Centre de formation : vie du campus et recrutement de jeunes

### JOURNÉE DE DÉTECTION
- Coût : **12 000 €**, une fois tous les **14 jours**.
- Génère **3 à 5 prospects** de 15 à 17 ans, présentés dans un dialogue.
- Chaque prospect peut être **signé** (il rejoint le club et le centre) ou
  **écarté**.
- La qualité dépend de la note du centre, du recruteur, du partenariat local
  et du partenariat étranger.

### PROJETS DE CAMPUS
- **École de football** : 3 niveaux (45 k / 90 k / 160 k €), +5 % de
  progression des jeunes par niveau.
- **Partenariat clubs locaux** : 3 niveaux (30 k / 70 k / 120 k €),
  +2 détection et +3 % de progression par niveau.
- **Partenariat étranger** : 3 niveaux (90 k / 180 k / 300 k €),
  +4 détection, +3 % de progression et prospects étrangers avec potentiel
  renforcé.
- Les niveaux sont accessibles depuis la page Centre de formation via
  **TOUTES LES OPTIONS**.

### ÉDUCATEURS SPÉCIFIQUES
- **Éducateur technique** : +4 % technique et passe par niveau.
- **Éducateur mental** : +3 % progression et meilleur moral.
- **Éducateur physique** : +4 % physique et défense par niveau.
- Trois niveaux chacun, coûts progressifs.

### RECRUTEMENT DES MOINS DE 18 ANS
- Les prospects signés arrivent avec un contrat de 3 ans, un salaire de jeune,
  une date de naissance et un historique « Formation — recruté au centre ».
- Ils apparaissent immédiatement dans **JEUNES AU CLUB** et profitent des
  bonus du campus.

### NOTE DU CENTRE
- Les projets ajoutent jusqu'à **+14 points** à la note du centre.
- La formule affichée dans MOYENS DU CENTRE inclut désormais « projets +X ».

### VALIDATION
- Nouveau test `tests/test_academy_development.py` : achat de projets, note en
  hausse, prospect étranger, signature d'un jeune, coût et cooldown de la
  détection.
- Toutes les suites courtes passent ; smoke complet sans exception.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_academy_dev/`.


---

## Annexe EC — Calendrier : affichage homogène et simplifié

### ONGLETS
- Libellés courts et identiques : **SAISON**, **AMICAUX**, **COUPE**.
- Une icône vectorielle sobre sur chaque onglet, même taille et même couleur.
- Le bandeau de KPI (prochain match, journée, bilan, amicaux) reste commun aux
  trois onglets.

### EN-TÊTES
- L'ancien grand bandeau doré de la COUPE est remplacé par un en-tête compact
  et neutre, identique à celui des AMICAUX.
- L'en-tête AMICAUX est réduit : icône 24 px, titre 9 pt, sous-titre 7 pt,
  quota compact.
- Les titres de panneaux (calendrier, mes amicaux, tours, rapports) utilisent
  désormais la même taille, la même graisse et la même couleur.

### MISE EN PAGE
- Mêmes panneaux, mêmes séparateurs et mêmes largeurs de poignée sur les trois
  onglets.
- Listes à gauche, rapport à droite, avec des proportions proches.
- Formulaires et filtres conservés, mais resserrés.

### RÉSULTAT
- Passage d'un onglet à l'autre sans rupture visuelle.
- Aspect plus calme : plus de dégradé doré ni de héros surdimensionné.
- Les informations utiles restent toutes accessibles.

### VALIDATION
- Rendu des trois onglets en 1560 px vérifié.
- Toutes les suites courtes passent ; smoke complet sans exception.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_calendar_clean/`.


---

## Annexe ED — Compétitions : coupe, historique et palmarès

### COUPE
- En-tête compact : nom de la compétition, édition, prime et statut.
- Trois KPI seulement : tour en cours, matchs au tableau, statut du club.
- Le **tableau** occupe la colonne de gauche, avec les filtres de tour juste
  au-dessus.
- La colonne de droite regroupe les repères :
  - **Mon parcours**
  - **Repères** : exemptés, petit poucet, survivants par division
  - **Palmarès**
- Fini les bandeaux empilés de parcours, exemptés et petit poucet au-dessus du
  tableau.
- État vide explicite quand le tirage n'a pas encore eu lieu.

### HISTORIQUE
- En-tête compact « Archives de la carrière » avec sélecteur de saison.
- Les quatre KPI restent alignés.
- Tableaux d'archive homogènes avec le reste du jeu :
  fond sombre, en-têtes sobres, lignes alternées, police et espacements
  identiques.
- Les noms de clubs ne prennent plus la couleur criarde du club : texte neutre,
  club du joueur en doré.

### PALMARÈS
- En-tête compact avec sélecteur de ligue.
- Trois KPI : titres du club, saisons archivées, dernier champion.
- Tableau unique et lisible : saison, champion, montées, relégations.
- État vide centré et propre quand aucune saison n'est encore archivée.

### VALIDATION
- Nouveau test `tests/test_competitions_ui.py`.
- Toutes les suites courtes passent ; smoke complet sans exception.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_competitions_clean/`.


---

## Annexe EE — Finances : exploitation du match

### NOUVEL ONGLET EXPLOITATION
L'onglet **EXPLOITATION** remplace l'ancien onglet du même nom dans
Infrastructure. Il regroupe :
- la **billetterie** : prix par place, affluence prévue, remplissage ;
- le **bar** : prix des boissons et des snacks ;
- la **boutique** : prix du maillot, de l'écharpe et de la casquette ;
- une synthèse par match et une projection sur 19 rencontres à domicile.

### PRIX ET DEMANDE
Les recettes ne sont plus des montants fixes :
- le prix de la boisson et du snack modifie le taux d'achat des spectateurs ;
- le prix du maillot, de l'écharpe et de la casquette modifie les ventes ;
- le prix de la place modifie l'affluence et la billetterie.

Chaque ligne affiche les **unités estimées** et la **recette par match**.
Les prix sont enregistrés dans `meta` et utilisés immédiatement par le calcul
des recettes du match.

### SI LE BAR OU LA BOUTIQUE N'EXISTE PAS
- Le panneau affiche un message clair et un bouton **VOIR L'INFRASTRUCTURE**.
- Le bouton ouvre directement **Infrastructure → GESTION** pour construire le
  service manquant.

### INFRASTRUCTURE
- L'onglet EXPLOITATION d'Infrastructure est retiré de la navigation.
- La page historique reste conservée en mémoire, cachée, pour la compatibilité
  des widgets et des rafraîchissements.

### VALIDATION
- Nouveau test `tests/test_finance_exploitation.py` : onglets, prix du bar,
  prix boutique, billetterie, persistance et recalcul.
- Toutes les suites courtes passent ; smoke complet sans exception.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_finance_exploitation/`.


---

## Annexe EF — Staff : affichage sobre et sans répétition

### CARTES
- Passage de grandes cartes verticales à des **lignes compactes** (86–108 px).
- Une icône discrète, le poste, la personne, l'effet actuel et le coût.
- Le niveau reste visible sous forme de cinq pastilles, dans un bleu-gris
  unique.
- Les descriptions détaillées passent en **infobulle** au lieu d'occuper la
  carte.

### COULEURS
- Suppression des bordures colorées par niveau et des statuts vert/rouge vifs.
- Accent unique bleu-gris, statut **EN POSTE** en vert doux, **VACANT** en gris.
- Boutons **FORMER** / **EMBAUCHER** / **LICENCIER** en style neutre, sans
  bouton primaire agressif.

### MOINS DE RÉPÉTITION
- Le bandeau de synthèse des effets est masqué : les effets sont déjà sur les
  cartes.
- Le sous-titre ne répète plus le salaire et le plafond : il indique seulement
  les postes pourvus et le niveau moyen.
- Le salaire et la note restent dans le bandeau supérieur.

### VALIDATION
- Nouveau test `tests/test_staff_ui.py` : 8 cartes compactes, synthèse masquée,
  poste pourvu lisible.
- Toutes les suites courtes passent ; smoke complet sans exception.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_staff_sober/`.


---

## Annexe EG — Shortlist : les recrues en sortent automatiquement

### REGLE
Un joueur qui rejoint le club ne doit plus rester dans la shortlist : la cible
est déjà atteinte.

### MISE EN ŒUVRE
- Nouvelle méthode `purge_shortlist_owned()` : supprime toutes les lignes
  `shortlist` dont le joueur a `club_id=1`.
- La purge est exécutée :
  - au début de `refresh_all()` (après chaque transfert, signature, prêt ou
    changement de club) ;
  - à chaque lecture de `shortlist_rows()` ;
  - donc à l'ouverture de l'onglet SHORTLIST.
- Les cibles extérieures au club sont conservées.

### VALIDATION
- Nouveau test `tests/test_shortlist_cleanup.py` : une recrue est retirée, une
  cible externe reste.
- Toutes les suites courtes passent ; smoke complet sans exception.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_shortlist_cleanup/`.


---

## Annexe EH — Nettoyage des noms et affichages

### NOMS INTERNES SUPPRIMÉS
- L'en-tête de l'historique des transferts affichait encore
  `player_history` et une phrase trop technique.
- Remplacé par : « arrivées et départs • indemnité issue des finances •
  double-clic : fiche du joueur ».

### ONGLETS HARMONISÉS
- Transferts : `OFFRES`, `MARCHÉ`, `SCOUTING`, `SHORTLIST`, `HISTORIQUE`,
  `PRÊTS`.
- L'onglet `PRÊTS • ENTRANTS & SORTANTS` devient simplement `PRÊTS`.
- Compétitions : `CHAMPIONNAT`, `COUPE`, `STATISTIQUES`, `HISTORIQUE`,
  `PALMARÈS`.
- Calendrier : `SAISON`, `AMICAUX`, `COUPE`.
- Finances : `VUE D'ENSEMBLE`, `EXPLOITATION`, `PRÊT BANCAIRE`, `SPONSORS`.
- Infrastructure : `VUE D'ENSEMBLE`, `GESTION`.
- Classements archivés : `CLASSEMENTS FINAUX`, `MES RÉSULTATS`,
  `PALMARÈS PAR LIGUE`.
- Statistiques : `BUTEURS`, `GARDIENS • ARRÊTS`.
- Fiche club et consignes tactiques : libellés sans emoji ni espace parasite.

### GARDE-FOU
- Nouveau test `tests/test_ui_labels_clean.py` : parcourt 889 libellés
  (labels, boutons, onglets, en-têtes de tableaux, listes déroulantes) et
  refuse tout underscore ou nom interne (`player_history`, `finance_tx`,
  `ENTRANTS_SORTANTS`, etc.).
- `tests/test_transfer_history.py` aligné sur le nouvel onglet `HISTORIQUE`.

### VALIDATION
- Toutes les suites courtes passent ; smoke complet sans exception.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_labels_clean/`.


---

## Annexe EI — Infrastructure : chantiers niv. 2 qui revenaient

### CAUSE
D'anciens projets `Tribunes niv. 2` étaient restés dans `facility_project`.
À chaque échéance, `process_facility_projects` appliquait aveuglément leur
`target_level` : il réécrivait `arena_level` à 2, même si le bâtiment était
déjà au niveau 8.

### CORRECTIFS
- **Réparation automatique** (`_repair_facility_levels`) :
  - relit l'historique des chantiers terminés ;
  - remonte chaque bâtiment au **niveau maximum déjà atteint** ;
  - plafonne à 8 ;
  - marque comme terminés les chantiers actifs inférieurs ou égaux au niveau
    déjà acquis.
- **Plus de downgrade** : la fin d'un chantier applique désormais
  `max(niveau actuel, niveau cible)`.
- **Garde-fou au lancement** : `upgrade_facility` tient compte du meilleur
  niveau historique, pas seulement de la valeur courante.
- La réparation tourne au chargement, à l'ouverture d'Infrastructure et lors du
  traitement quotidien des chantiers.

### EFFET SUR LA PARTIE
- Les doublons « Tribunes niv. 2 » sont neutralisés.
- L'arène remonte à son vrai niveau (8 dans la sauvegarde vérifiée).
- Aucun chantier inférieur ne peut plus faire redescendre un bâtiment.

### VALIDATION
- Nouveau test `tests/test_facility_project_repair.py`.
- Vérification sur une **copie** de la sauvegarde réelle : arène 2 → 8,
  12 chantiers actifs parasites → 0, sauvegarde source intacte.
- Toutes les suites courtes passent ; smoke complet sans exception.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_facility_repair/`.


---

## Annexe EJ — Nouveaux bâtiments et onglets d'investissement

### LABORATOIRE D'ANALYSE VIDÉO
- 3 niveaux, chantier dédié.
- Effet : **+2 % de familiarité tactique par niveau**.
- Ajoute un **rapport vidéo** dans le centre de match :
  adversaire, division, forme sur 5 matchs et meilleur buteur.

### CENTRE DES BÉNÉVOLES
- 3 niveaux, coût faible.
- Effet : **−8 % de frais de match par niveau** (sécurité, stewards,
  logistique).
- Réduit aussi les frais d'exploitation quotidiens de 6 % par niveau.

### RESTAURANT & FOOD TRUCK
- Démarre en **food truck**, puis évolue jusqu'au restaurant (3 niveaux).
- Effet : recette supplémentaire par spectateur à chaque match :
  - niveau 1 : +1,2 € / spectateur
  - niveau 2 : +2,4 € / spectateur
  - niveau 3 : +3,6 € / spectateur
- La recette apparaît dans le détail du match et dans la synthèse Finances.

### ONGLETS D'INVESTISSEMENT
La page GESTION est découpée en trois sous-onglets :
- **BÂTIMENTS** : tribunes, éclairage, parking, médical, formation, marketing,
  laboratoire vidéo.
- **SERVICES** : bar, loge VIP, boutique, restaurant / food truck.
- **REVENUS** : terrains locatifs, salle d'événements, fan zone, centre des
  bénévoles.

### TECHNIQUE
- Ajout automatique des colonnes `video_level`, `volunteer_level`,
  `restaurant_level` aux sauvegardes existantes.
- Chantiers intégrés au système existant : coûts, durées, architecte, places
  simultanées et réparation des niveaux.

### VALIDATION
- Nouveau test `tests/test_facility_new_buildings.py`.
- Toutes les suites courtes passent ; smoke complet sans exception.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_new_facilities/`.


---

## Annexe EK — Direction sportive : palmarès du club

### AVANT
Le palmarès utilisait un QLabel RichText avec une ligne dorée par titre. Plus
le club gagnait, plus le bloc grandissait : texte qui débordait, hauteur
écrasée et vitrine difficile à lire.

### APRÈS
- Le palmarès devient une **liste défilante compacte**.
- Chaque titre tient sur une ligne : saison, icône trophée, « Champion • Ligue X ».
- Les lignes utilisent un fond sombre discret et un liseré, sans gros blocs dorés.
- Le compteur de titres, les promotions et les relégations restent dans la
  colonne de gauche.
- En cas de charge importante, la liste défile proprement au lieu de déborder.
- État vide explicite : « Aucun titre pour l'instant ».

### VALIDATION
- Nouveau test `tests/test_dashboard_honours.py` : 10 titres simulés,
  compteur correct, liste défilante.
- Toutes les suites courtes passent ; smoke complet sans exception.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_dashboard_honours/`.


---

## Annexe EL - Messagerie : fin du spam scouting, rapport mensuel

### AVANT
Le centre de recrutement envoyait un message `scout_report` par joueur observe,
plus un message d'annonce par mission. La boite de reception se remplissait de
rapports individuels difficiles a trier.

### APRES
- Les rapports unitaires ne s'affichent plus dans la boite de reception.
  Ils restent disponibles dans Transferts -> Scouting, ou ils sont utiles.
- Un seul message par mois : **Rapport mensuel - Recrutement**.
- Ce digest resume les fiches ouvertes le mois precedent (12 maximum) sous
  forme de cartes compactes : nom, club et division, poste, age, fiabilite de
  la fiche, valeur estimee.
- Le message est généré une seule fois par mois (cle `meta.scout_digest_month`),
  le premier jour du mois suivant.
- Badge dedie `RAPPORT MENSUEL` dans le detail, categorie Scouting, et bouton
  d'acces direct a Transferts -> Scouting.
- Etat vide : aucun digest n'est cree si le staff n'a observe personne.

### VALIDATION
- `tests/test_scouting_digest.py` : rapports individuels masques de la boite,
  digest unique, cartes presentes dans le detail.
- `tests/test_messaging_ui.py` mis a jour : 9 messages visibles, 4 non lus,
  8 avec la categorie Matchs masquee.
- Toutes les suites courtes passent ; smoke complet sans exception.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_scouting_digest/`.


---

## Annexe EM - Tactique : tuiles du terrain compactes et lisibles

### AVANT
Les tuiles des joueurs etaient hautes. Sur les fenetres moyennes, la rangee
des defenseurs chevauchait celle du gardien : les cartes se superposaient et
le texte devenait difficile a lire.

### APRES
- Tuiles **plus basses** : hauteur bornee pour laisser un ecart franc entre
  les rangees (defense / gardien / attaque), quelle que soit la resolution.
- Largeur bornee par l'ecart entre colonnes : plus de tuiles qui se touchent
  horizontalement non plus.
- Contenu **agrandi** : maillot plus grand, nom en 11-12 px gras, note et forme
  plus lisibles, numero en haut a droite.
- Si le nom complet ne tient pas, il est raccourci en « P. Nom » avant ellipse.
- Le poste et le numero restent sur la premiere ligne, la note sur la derniere.
- Les notes TEC / FIN / DEF passent dans l'infobulle pour alleger la tuile.
- Tuiles vides : « + DEPOSER » reste centre et lisible meme en 44 px de haut.

### VALIDATION
- `tests/test_tactics_layout.py` enrichi : aucune intersection entre tuiles,
  hauteur comprise entre 44 et 78 px, verifie a 1920x900 et en fenetre etroite.
- Balayage 1920, 1600, 1360, 1200, 1000 et 940 px : **0 chevauchement**.
- Toutes les suites courtes passent ; smoke complet sans exception.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_tactics_tiles/`.


---

## Annexe EN - Entrainement : cible visible et evolution depuis le debut de saison

### INDIVIDUEL
- Chaque carte affiche desormais la **cible reellement travaillee** :
  - focus choisi : « CIBLE · TECHNIQUE 14/20 » en violet ;
  - aucun focus : « AUTO · DRIBBLE 12/20 » en vert, avec l'attribut
    prioritaire du poste (gardien : arrets, defenseur : defense,
    ailier : dribble, pivot : finition, universel : technique).
- La cible se met a jour immediatement quand on change le focus.
- Une infobulle explique le choix manuel ou automatique.

### PROGRESSION
- Le panneau compare maintenant au **debut de la saison** (1er juillet) et non
  plus aux 30 derniers jours.
- Niveau et potentiel restent affiches en barres.
- Une ligne « SAISON » liste les attributs qui ont evolue :
  - hausse en **vert** (« TEC +2 »),
  - baisse en **ambre** (« END -1 »),
  - maximum 6 pastilles, le reste regroupe avec une infobulle detaillee.
- Sans evolution : « Aucune evolution d'attribut ».
- L'infobulle de chaque pastille donne la valeur /20 avant et apres.
- Les totaux de l'en-tete et le compteur de droite sont alignes sur la saison
  (« PTS / SAISON »).

### TECHNIQUE
- Nouvelle table `player_attr_baseline` : attributs figes au debut de saison.
- Pour les sauvegardes existantes, la base est reconstruite a la premiere
  ouverture en retirant les gains journalises depuis le 1er juillet.
- Aucune ecriture dans la sauvegarde active pendant les tests.

### VALIDATION
- `tests/test_training_ui.py` enrichi : cible CIBLE/AUTO affichee, evolution
  saison presente avec la bonne couleur.
- Toutes les suites courtes passent ; smoke complet sans exception.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_training_season/`.


---

## Annexe EO - Infrastructure : refonte de GESTION et lancement des nouveaux chantiers

### DEUX BUGS QUI BLOQUAIENT LES NOUVEAUX BATIMENTS
1. `start_facility_project` filtrait les cles autorisees avec une liste qui ne
   contenait pas `video_level`, `volunteer_level` ni `restaurant_level` : le clic
   sortait en silence (`return False`), aucun message, aucun chantier.
2. `_repair_facility_levels` forcait `niveau 0 -> 1` pour ces batiments. Un
   chantier de niveau 1 etait donc considere comme deja livre et passait
   immediatement en « termine » : le batiment semblait ne jamais se construire.

### REACTION DES BOUTONS
- Les cartes ne sont plus silencieusement desactivees quand le budget manque ou
  que les places de chantier sont saturees : le bouton reste cliquable et
  affiche un message clair (« Budget insuffisant », « Places de chantier
  saturees »).
- Les boutons EN COURS / MAX / INSTALLE restent, eux, inactifs (rien a lancer).
- Le statut de la carte explique le blocage en couleur ambre.

### REFONTE VISUELLE DE GESTION
- Bandeau de pilotage compact : budget, chantiers occupes, ameliorations
  disponibles, niveau moyen.
- Sous-onglets BÂTIMENTS / SERVICES / REVENUS en pastilles sobres, sans
  deuxieme bandeau de section redondant.
- Cartes uniformes (128 px) : icone, nom, niveau, effet attendu, description,
  statut et bouton d'action aligne a droite.
- Rangees equilibrees : 3/2/2 pour les batiments, 4 en ligne pour les services
  et revenus (2x2 en fenetre moyenne). Plus de carte isolee en bas.
- Aucun defilement a 1560x900 sur l'onglet BÂTIMENTS.

### VALIDATION
- Nouveau `tests/test_facility_gestion_actions.py` : clic reel sur Restaurant ->
  chantier en cours ; places saturees -> message ; budget nul -> message.
- `tests/test_facility_new_buildings.py` : les trois nouveaux chantiers
  demarrent et restent `in_progress`.
- `tests/test_facility_gestion_fit.py` mis a jour (cartes 128 px, 3 colonnes).
- Toutes les suites courtes passent ; smoke complet sans exception.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_facility_gestion_redesign/`.


---

## Annexe EP - Centre de formation : options visibles et effectifs séparés

### AVANT
- Les vraies options (école, partenariats, éducateurs) étaient cachées dans une
  fenêtre « TOUTES LES OPTIONS ».
- La page répétait les mêmes éléments : barres Installations / Pôle médical
  puis « leviers » Installations / Pôle médical, panneau « Campus à construire »
  en doublon du bouton d'ouverture, synthèse des projets en doublon des cartes.
- Elle mélangeait l'équipe première : bouton STAFF vers la page du staff
  professionnel, et tableau « jeunes au club » qui listait tous les U18 de
  l'effectif, même ceux qui n'étaient pas passés par le centre.

### APRES
- **Toutes les options sont sur la page**, dans une grille de 8 cartes :
  - Journée de détection (coût, cooldown, prospects) ;
  - École de football, partenariat local, partenariat étranger ;
  - Éducateurs technique, mental et physique ;
  - Moyens renforcés (+8 de note, une fois par saison).
- Chaque carte affiche son niveau /3, son effet, son statut et son bouton.
- Plus de doublons : les « leviers » et le panneau « Campus à construire » sont
  supprimés. Un seul bouton « GÉRER LES INSTALLATIONS » renvoie vers
  Infrastructure → GESTION au lieu de dupliquer les chantiers.
- Séparation nette :
  - plus aucun lien vers le staff de l'équipe première ;
  - le préparateur et le recruteur du club restent une ligne d'information
    « Soutien du club (compté dans la note) », sans action ;
  - le tableau « JEUNES DU CENTRE » ne liste que les joueurs formés au centre
    (promotions et signatures), pas les U18 recrutés pour l'équipe première.
- Grille responsive : 4 cartes par ligne en grand écran, 3 puis 2 en fenêtre
  moyenne.
- Tableau des jeunes élargi (2/3 de la largeur) pour éviter le défilement
  horizontal.

### VALIDATION
- Nouveau `tests/test_academy_options.py` : 8 cartes visibles, clic direct sur
  l'école, détection et moyens renforcés présents, aucun bouton STAFF, jeunes
  du centre uniquement.
- `tests/test_academy_facility.py`, `test_academy_development.py` et
  `test_new_features.py` mis à jour.
- Toutes les suites courtes passent ; smoke complet sans exception.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_academy_clear/`.


---

## Annexe EQ - Marché : colonnes personnalisables et tableau pleine largeur

### AVANT
Le tableau du marché laissait un vide à droite : les largeurs étaient figées
(sauf deux colonnes) et leur total était inférieur à la largeur de la page.
Impossible de masquer les colonnes inutiles ni de réordonner les en-têtes.

### APRES
- La colonne **JOUEUR** est extensible : le tableau occupe toute la largeur
  disponible, sans bande vide à droite.
- Toutes les autres colonnes sont **redimensionnables** en glissant leur
  séparation.
- Les en-têtes sont **déplaçables** pour réordonner les colonnes.
- Nouveau bouton **COLONNES** à côté de DÉTAIL / OFFRE :
  - cocher / décocher les 16 colonnes ;
  - régler chaque largeur en pixels (40 à 600) ;
  - boutons TOUT AFFICHER et LARGEURS PAR DÉFAUT ;
  - le nom du joueur reste toujours visible et s'adapte à la page.
- La disposition (ordre, largeurs, colonnes masquées) est mémorisée dans les
  options du joueur (`market_header_state`) et restaurée au lancement.
- Le panneau DÉTAIL / OFFRE reste optionnel : masqué, le tableau profite de
  toute la page.

### VALIDATION
- Nouveau `tests/test_market_columns.py` : largeur totale = largeur du tableau,
  colonne extensible, colonnes masquables/réaffichables, largeur personnalisée,
  état mémorisé.
- Toutes les suites courtes passent ; smoke complet sans exception.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_market_columns/`.


---

## Annexe ER - Finances : exploitation immersive et complète

### AVANT
Onglet EXPLOITATION plat : un bandeau, quatre chiffres, trois blocs de prix
et un résumé. Aucune ambiance de soirée de match, pas de visualisation de la
demande, pas de détail des autres recettes.

### APRES
- **Bandeau « Soirée de match »** dessiné sur mesure : stade de nuit aux
  couleurs du club, projecteurs, tribunes et terrain ; nom de l'arène, prochaine
  réception, recette du match, projection saison et jauge d'affluence.
- **5 indicateurs** : billetterie, bar, boutique, restauration, total / match,
  chacun avec son icône.
- **Billetterie** : courbe de demande prix → affluence avec repère du tarif
  courant, boutons − / +, application du tarif.
- **Bar & restauration** : cartes produits illustrées (boisson, snack), unités
  et recette par produit, ligne restaurant, boutons d'application.
- **Boutique** : le **maillot du club** est dessiné à côté de « Maillot »,
  l'écharpe et la casquette ont leurs icônes vectorielles ; prix, unités et
  recettes par article.
- **Autres recettes** : loges VIP, fan zone, parking, diffusion nocturne et
  restaurant, avec montant du match et statut (actif / à construire).
- **Projection saison** : total sur 19 matchs, recette par match et barres de
  répartition billetterie / bar-restaurant / boutique / autres.
- **Conseil du soir** : prix conseillé, taux de remplissage et bouton pour
  l'appliquer, plus trois rappels d'exploitation.
- Défilement propre de la page ; les panneaux restent lisibles en fenêtre
  étroite.

### VALIDATION
- `tests/test_finance_exploitation.py` enrichi : bandeau, restaurant, maillot
  dessiné, autres recettes, répartition et prix conseillé.
- Toutes les suites courtes passent ; smoke complet sans exception.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_exploitation_immersive/`.


---

## Annexe ES - Coaching et interviews : plus d'options

### AVANT-MATCH
Trois causeries seulement (confiance, solidarité, pression). Des choix
supplémentaires arrivent, avec un contexte de match :
- **Sang-froid** : consignes précises, attaque et défense +1,5 %, forme +1.
- **Capitaine** : les cadres parlent, moral +3, supporters +1, forme +1.
- **Coup de punch** : audace maximale, attaque +4 %, défense −3 %, moral −1.
- **Laisser faire** : aucun bonus tactique, forme +2.
- L'écran indique si le club est **favori**, **outsider** ou en match équilibré,
  et rappelle le derby.

### MI-TEMPS
Huit causeries au lieu de trois, avec le score et le momentum affichés :
- **Bloc bas** : protéger le résultat (défense +5 %, attaque −4 %, momentum −6).
- **Jeu direct** : attaque +3 %, défense +1 %, momentum +3.
- **Coup de gueule** : attaque +5 %, défense −4 %, moral −1, momentum +5.
- **Confiance** : attaque et défense +2 %, moral +1, forme +2.
- **Laisser jouer** : pas de causerie, forme +3.
Les effets sur le moral, la forme et le momentum sont réellement appliqués
(avant, certains bonus n'étaient qu'affichés).

### INTERVIEW D'APRÈS-MATCH
Les réponses dépendent du résultat :
- **Victoire** : féliciter, rester humble, remercier les supporters, saluer
  l'adversaire, pointer les erreurs.
- **Match nul** : humble, supporters, promettre du travail, protéger les
  joueurs, pointer les erreurs.
- **Défaite** : assumer, protéger les joueurs, remercier les supporters,
  promettre du travail, contester l'arbitrage, pointer les erreurs.
- Le score est affiché dans l'en-tête (du point de vue du club).
- Les effets **supporters** passent par `fan_confidence` et sont donc réels ;
  le moral de l'effectif est ajusté selon la réponse.

### VALIDATION
- Nouveau `tests/test_coaching_options.py` : 7 options avant-match, 8 à la
  mi-temps, 5 à 6 réponses par résultat, effets de moral, forme, momentum et
  supporters vérifiés.
- Toutes les suites courtes passent ; smoke complet sans exception.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_coaching_interviews/`.


---

## Annexe ET - Passe de propreté des textes et du classement

### CLASSEMENT
- Suppression du préfixe texte **« DESCENTE »** (et « MONTÉE ») collé au nom
  des clubs : la zone est déjà signalée par la couleur et la légende.
- Une **petite flèche** monte / descend devant le nom, avec une infobulle
  « Zone de promotion / de relégation ».
- Stats de ligne légèrement agrandies (7,5 pt), meilleur contraste.
- Légende conservée : CHAMPION / PROMOTION / RELÉGATION.

### VOCABULAIRE UNIFIÉ
- « DESCENTE(S) » remplacé par **RELÉGATION(S)** dans le palmarès, l'historique
  et les compteurs de la direction sportive.
- En-têtes du palmarès nettoyés (plus d'espace parasite, pluriels cohérents).
- Sous-titre du palmarès : « montées et relégations ».

### TAILLES ET COULEURS
- Toutes les légendes à **6 pt** passent à **6,5 pt** (lisibilité).
- Coûts et titulaires du staff : **7 pt** (au lieu de 6,2–6,8).
- Hints d'entraînement : **7 pt**.
- Texte secondaire trop sombre `#6f829c` remplacé par `#8b9cb5`.
- Stats du classement : `#a9b8cc`, captions « POINTS » à 6,5 pt.

### STAFF
- Ligne redondante « Poste à pourvoir — aucune personne en poste » remplacée
  par **« Aucun titulaire »**.
- Bouton **FORMER** masqué quand le poste est vacant (seul EMBAUCHER reste).

### VALIDATION
- Audit runtime des 12 pages : aucun doublon de mot, aucun préfixe de zone.
- `tests/test_competitions_ui.py` vérifie l'absence de DESCENTE/MONTÉE et la
  présence des infobulles de zone.
- `tests/test_ui_labels_clean.py` : 923 textes contrôlés, aucun nom interne.
- Toutes les suites courtes passent ; smoke complet sans exception.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_text_audit/`.


---

## Annexe EU - Centre de match : fin de l'avertissement libpyside

### SYMPTOME
À chaque rafraîchissement du centre de match :

    RuntimeWarning: libpyside: Failed to disconnect (None) from signal
    "itemClicked(QListWidgetItem*)"

Le code appelait `lst.itemClicked.disconnect()` à chaque tick, même quand le
signal n'était pas connecté. Le `try/except` évitait le crash mais pas
l'avertissement de PySide.

### CORRECTION
- Le signal est désormais connecté **une seule fois**, avec un garde
  `_instruction_handler_connected`.
- La connexion pointe vers une méthode dédiée
  `_on_live_team_item_clicked`, qui ouvre la consigne individuelle si la ligne
  correspond à un joueur.
- Plus de `disconnect()` à chaque rafraîchissement : aucun avertissement, et le
  clic fonctionne toujours sur les consignes individuelles.

### VALIDATION
- Nouveau `tests/test_live_team_signal.py` : quatre rafraîchissements du centre
  de match, connexion unique, aucun avertissement.
- Toutes les suites courtes passent ; smoke complet sans exception.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_live_signal/`.


---

## Annexe EV - Coupe : un match joué ne redevient plus « à jouer »

### CAUSE
Chaque match de coupe du manager reçoit un `ai_match_report` pour alimenter le
rapport consultable dans le calendrier. Or le correctif de démarrage
`repair_phantom_user_fixtures` considérait **tout** match du club avec un
`ai_match_report` comme un « fantôme » simulé par l'IA. Au redémarrage (ou lors
d'une réouverture de la sauvegarde), le dernier match de coupe était donc remis
à `played=0` : il réapparaissait comme « à jouer » sur le centre de match.

Le même correctif soustrayait aussi les scores de coupe des classements de
championnat, alors que la coupe n'alimente pas ces classements.

### CORRECTION
- Un match n'est déclaré fantôme que s'il n'a **aucun `match_record`**
  correspondant. Un match de coupe réellement joué est donc conservé.
- La réparation ne touche aux classements que pour les matchs de
  **championnat** (jamais coupe ou amical).
- Nouvelle réparation au démarrage `restore_cup_results_from_records` : si une
  sauvegarde a déjà subi l'ancien bug, un match de coupe resté « à jouer » mais
  dont le `match_record` daté existe est restauré avec son score, et un rapport
  calendrier vide est recréé.

### VALIDATION
- Nouveau `tests/test_phantom_cup_repair.py` :
  - match de coupe joué + rapport IA + match_record → conservé ;
  - vrai fantôme de coupe → remis à jouer sans modifier les classements ;
  - sauvegarde déjà touchée → score restauré, amical d'une autre date ignoré.
- Toutes les suites courtes passent ; smoke complet sans exception.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_cup_results_repair/`.


---

## Annexe EW - Staff : délégations de causeries et d'interview

### PAGE STAFF
- Nouvel onglet **DÉLÉGATIONS** à côté d'EFFECTIF.
- Trois tâches peuvent être confiées à l'adjoint :
  - **Causerie d'avant-match** ;
  - **Causerie de mi-temps** ;
  - **Interview d'après-match**.
- Chaque ligne propose **JE GÈRE / DÉLÉGUÉ À L'ADJOINT**, plus deux boutons
  TOUT DÉLÉGUER et TOUT REPRENDRE.
- Sans adjoint, les boutons sont verrouillés et l'écran indique
  « ADJOINT : À RECRUTER ». Les délégations se débloquent dès que l'adjoint est
  engagé dans l'onglet EFFECTIF.
- Les choix sont enregistrés dans la carrière (`delegate_*` dans meta), pas
  dans une option globale : chaque partie peut avoir sa façon de jouer.

### COMPORTEMENT EN MATCH
- **Avant-match** : l'adjoint choisit selon le contexte (derby → pression,
  moral bas → capitaine, forme basse → laisser faire, outsider → solidarité,
  sinon confiance). Le dialogue n'apparaît plus.
- **Mi-temps** : l'adjoint protège un avantage (bloc bas), réagit quand le club
  est mené (motivant ou coup de gueule) ou garde le cap (confiance/tactique).
- **Interview** : l'adjoint répond selon le résultat, le moral et la confiance
  des supporters (remercier, assumer, protéger, promettre du travail…).
- Si l'adjoint est licencié, les délégations redeviennent automatiquement
  inactives : le manager reprend la main.

### VALIDATION
- Nouveau `tests/test_staff_delegations.py` : onglet présent, verrou sans
  adjoint, activation, causeries avant-match / mi-temps sans dialogue, interview
  déléguée, reprise en main.
- Toutes les suites courtes passent ; smoke complet sans exception.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_staff_delegations/`.


---

## Annexe EX - Dates : format français partout

### AUDIT
Un scan runtime de toutes les pages et de leurs onglets a recherché les dates
au format ISO (`AAAA-MM-JJ`, avec ou sans heure). Trois affichages restaient
au format technique :
- le fil d'actualités du tableau de bord ;
- la colonne Date des mouvements financiers ;
- la colonne Date de l'historique des transferts.

### CORRECTION
- Nouveau helper `fmt_datetime_fr` : `2026-07-01T13:51` → `01/07/2026 13:51`.
- Fil d'actualités : date et heure françaises.
- Mouvements financiers : `JJ/MM/AAAA HH:MM`.
- Historique des transferts : `JJ/MM/AAAA`.
- Les autres écrans (calendrier, messagerie, coupes, prêts, chantiers,
  formations, rapports) passaient déjà par `fmt_date_fr`.
- Le sélecteur de date des amicaux reste en `dd/MM/yyyy`.

### VALIDATION
- Nouveau `tests/test_date_formats.py` : helper vérifié, puis scan du tableau
  de bord, des finances et de l'historique des transferts → aucune date ISO.
- Scan runtime global : 0 date ISO visible sur les pages et onglets.
- Toutes les suites courtes passent ; smoke complet sans exception.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_dates_fr/`.


---

## Annexe EY - Infrastructure extérieure : campus illustré 2.5D

### REFONTE
La vue EXTÉRIEURE n'est plus un plan plat de rectangles : c'est une
illustration 2.5D du campus, dessinée entièrement en vectoriel.
- Bâtiments en volume avec toiture, façade vitrée, porte, ombres et liserés.
- Arène centrale avec verrières de toiture, enseigne, blason, entrée vitrée et
  auvent.
- Parvis, allées courbes, terrain d'entraînement avec buts, parking avec voitures,
  rivière et pont, route, arbres, lampadaires, drapeaux, bancs, panneaux.
- Enseigne monumentale du club à l'entrée.

### NOUVEAUX BÂTIMENTS
Tous les équipements récents apparaissent selon leur niveau :
- **Laboratoire vidéo** (antenne + écran) ;
- **Centre des bénévoles** ;
- **Restaurant & food truck** avec terrasse et parasols ;
- **Formation**, **pôle médical**, **bar**, **boutique**, **loges VIP**,
  **fan zone**, **parking**.
- Les bâtiments non construits affichent un emplacement pointillé « À BÂTIR ».

### DETAILS
- Labels plus grands et lisibles, kiosques avec enseigne sur le toit.
- Niveaux affichés en pastilles, couleurs du club sur l'arène et les accents.
- Éclairage : projecteurs aux angles de l'arène et lampadaires allumés dès le
  niveau 2.

### VALIDATION
- Nouveau `tests/test_campus_view.py` : laboratoire vidéo, bénévoles, restaurant
  et formation modifient réellement le rendu (empreintes différentes).
- `test_infra_save_ui` et `test_visual_glitches` passent.
- Toutes les suites courtes passent ; smoke complet sans exception.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_campus_2_5d/`.


---

## Annexe EZ - Exploitation : palette sobre et contrastes doux

### AVANT
Trop d'accents saturés se disputaient l'écran : icônes KPI vertes, violettes et
orange, valeurs colorées, boutons bleus vifs, jauges vert/jaune très lumineuses.

### APRES
- **Une seule couleur d'icône** pour les KPI (acier #a8bccf), seul le total
  garde le sable #d8bc8a.
- **Valeurs en blanc cassé** (#e8f0f8) pour une lecture immédiate ; total en
  sable.
- En-têtes de panneaux uniformisés en acier ; projection saison en sable.
- Revenus des produits dans un **vert doux unique** (#a9c8b8).
- Montants des autres recettes en acier clair, icônes discrètes.
- Jauges d'affluence et de remplissage en dégradé **gris-vert/sable** très doux.
- Boutons secondaires neutres ; seule l'action « appliquer le tarif » reste
  légèrement teintée.
- Textes secondaires éclaircis (#91a5bb / #9fb1c4) pour rester lisibles sans
  briller.

### VALIDATION
- `tests/test_finance_exploitation.py` passe (bandeau, restaurant, maillot,
  projection et prix conseillé).
- `test_visual_glitches` : 14 pages rendues sans anomalie.
- Toutes les suites courtes passent ; smoke complet sans exception.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_exploitation_sober/`.


---

## Annexe FA - Ouverture du jeu : JGames, intro, menu

### SEQUENCE
1. Au lancement, une fenêtre plein écran sans bordure affiche
   `data/jgames.png` (logo du studio).
2. Au clic (ou Espace / Entrée), fondu vers `data/intro1.png`.
3. Au clic suivant, fondu final puis ouverture du **menu de démarrage** de la
   carrière, avec un léger fondu d'apparition de la fenêtre principale.
- Échap passe directement au menu.
- Des points discrets en bas indiquent l'étape courante.

### DETAILS
- Fond sombre dégradé avec vignettage, images centrées en `KeepAspectRatio`.
- Fondus de 420 ms (sortie puis entrée) sur l'opacité de l'image.
- Les visuels sont lus depuis `DATA_DIR` : `data/jgames.png` et
  `data/intro1.png`.
- Si une image manque ou est illisible, l'étape est ignorée ; si aucune n'est
  disponible, le menu s'ouvre normalement.
- Le jeu ne quitte pas quand la fenêtre d'ouverture se ferme
  (`setQuitOnLastWindowClosed(False)` jusqu'à l'affichage du menu).

### VALIDATION
- Nouveau `tests/test_splash_sequence.py` : logo, fondu vers l'intro, fondu
  final, repli si les images manquent.
- Toutes les suites courtes passent ; smoke complet sans exception.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_splash/`.


---

## Annexe FB - Staff : chargement rapide et délégations étendues

### CHARGEMENT
- La page Personnel ne déclenche plus le `refresh_all` global à chaque ouverture :
  seul `_staff_refresh` est exécuté.
- L'effet d'opacité de transition est désactivé sur cette page lourde.
- La synthèse masquée n'est plus reconstruite à chaque rafraîchissement.
- Salaire effectif calculé avec le niveau déjà connu (une requête de moins par
  carte).
- Mesure locale : **~240 ms → ~50 ms** pour l'ouverture de la page.

### DELÉGATIONS (7 TÂCHES)
Chaque tâche se débloque avec le membre du staff correspondant :
- **Adjoint** : causerie d'avant-match, causerie de mi-temps, interview
  d'après-match, composition du cinq.
- **Préparateur physique** : **entraînement hebdomadaire, actif par défaut dès
  son embauche**.
- **Comptable** : tarif de billetterie.
- **Recruteur** : veille du marché.

### COMPORTEMENTS
- **Entraînement** : si aucune séance n'est programmée sur les 7 prochains jours,
  le préparateur applique un plan match / développement / récupération selon le
  calendrier et la forme du groupe.
- **Composition** : l'adjoint aligne automatiquement le meilleur cinq avant le
  coup d'envoi.
- **Billetterie** : le comptable applique le tarif conseillé avant chaque
  réception.
- **Veille du marché** : le recruteur épingle une cible pertinente chaque lundi.
- Chaque délégation reste reprenable en main (JE GÈRE / DÉLÉGUÉ) et est
  enregistrée dans la carrière.

### VALIDATION
- `tests/test_staff_ui.py`, `test_staff_delegations.py` et nouveau
  `test_staff_delegations_extended.py` (7 tâches, entraînement par défaut,
  billetterie, veille du marché).
- Toutes les suites courtes passent ; smoke complet sans exception.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_staff_fast/`.


---

## Annexe FC - Transferts : environnement nettoyé, scouting réparé

### ONGLETS
- Les six onglets du mercato utilisent désormais des **pastilles sobres**
  (acier/slate), au lieu des onglets bruts.
- Même hiérarchie visuelle sur MARCHÉ, OFFRES, SCOUTING, SHORTLIST, HISTORIQUE
  et PRÊTS.

### SCOUTING
- Le tableau ne passe plus le texte à la ligne : plus de cellules qui se
  chevauchent.
- Colonnes fixées : joueur et club extensibles, statut, avancement,
  connaissance, rapports, échéance.
- La jauge n'affiche plus tout le statut dans la barre (source du débordement) :
  seulement « 75 % », le statut restant dans sa colonne.
- Couleurs douces : en cours (sable), à consulter (sauge), consulté (acier).
- Tri désactivé sur cette table : les barres de progression restent alignées.
- **État vide** dédié : « Aucune mission de scouting » avec accès direct au
  marché.
- Les **joueurs libres** sont maintenant inclus dans les missions et ouvrables
  (jointure club rendue facultative).

### SHORTLIST
- Lignes sur une seule ligne, colonnes fixes, plus de texte empilé.
- Libellés sans emoji : RETIRER LA SÉLECTION / VIDER LA SHORTLIST.
- État vide dédié avec accès au marché.

### OFFRES
- Titres de colonnes adoucis (acier / sable).
- États vides centrés et explicites : aucun dossier en cours, aucune offre
  reçue.

### VALIDATION
- Nouveau `tests/test_transfer_scouting_ui.py` : missions lisibles, jauge courte,
  joueurs libres, états vides scouting et shortlist.
- `test_offers_cards`, `test_transfer_history`, `test_loans` et
  `test_ui_labels_clean` passent.
- Toutes les suites courtes passent ; smoke complet sans exception.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_transfers_clean/`.


---

## Annexe FD - Campus extérieur : plan aéré et libellés protégés

### MISE EN PAGE
- Le campus est réorganisé en trois bandes lisibles : terrain + arène + formation
  en haut, pôle médical + bénévoles + parvis au centre, parking + fan zone +
  restaurant en bas.
- Chaque bâtiment dispose désormais d'une bande de libellé réservée : plus aucun
  toit ni aucune façade ne recouvre un texte.
- Les bâtiments de la colonne droite (formation, labo vidéo, restaurant) sont
  espacés verticalement ; le food truck est décalé à droite du restaurant.
- Le parvis et les kiosques (bar, boutique, VIP) sont contenus dans une zone
  dédiée, sans déborder sur l'arène.

### LIBELLÉS
- Les libellés sont mis en file puis dessinés en dernier, au-dessus de tous les
  bâtiments : plus de texte masqué, quel que soit l'ordre de dessin.
- Chips légèrement agrandies, bordure fine et fond plus opaque pour la lisibilité.
- Étiquette « BOUTIQUE » élargie : plus de texte tronqué sur les kiosques.
- En-tête : nom du club et sous-titre sur deux lignes, sans chevauchement.

### DÉCOR
- Moins de buissons et d'arbres, placés uniquement dans les angles libres.
- Deux allées seulement (entrée principale et accès restaurant) pour un rendu
  plus calme.
- Pelouse allégée (moins de mouchetures) et enseigne monumentale recentrée à
  l'entrée.

### VALIDATION
- `test_campus_view`, `test_facility_gestion_fit`, `test_facility_project_repair`,
  `test_facility_new_buildings`, `test_facility_gestion_actions`,
  `test_ui_start_render`, `test_visual_glitches` et `test_ui_labels_clean`
  passent.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_campus_air/`.


---

## Annexe FE - Entraînement : bandeau collectif isolé et onglets retravaillés

### BANDEAU COLLECTIF
- Le bandeau « modèle de groupe » (choix du modèle, APPLIQUER, ENREGISTRER),
  les cartes de contexte et les réglages d'intensité/focus sont désormais
  regroupés dans un conteneur unique.
- Ce conteneur n'est visible que sur l'onglet **2 SEMAINES**. Il disparaît
  totalement sur **INDIVIDUEL** et **PROGRESSION** : plus de barre de modèle
  de groupe au-dessus des focus individuels ou des courbes de progression.
- La visibilité est réappliquée à chaque rafraîchissement de la page, donc
  elle reste correcte après un changement d'onglet ou un retour sur la page.

### ONGLETS
- Les trois onglets utilisent les pastilles sobres du reste de l'application
  (acier/slate), avec un espacement régulier.
- Sous-titre de page neutre : « PLAN COLLECTIF • FOCUS INDIVIDUELS • PROGRESSION ».

### INDIVIDUEL
- Nouvelle barre d'outils : compteurs (joueurs, focus manuels, automatiques,
  gain sur 30 jours) et actions AUTO PAR POSTE / TOUT EN AUTO.
- Cartes réorganisées : identité + poste + badge FOCUS/AUTO + fiche sur une
  ligne, focus et cible sur une ligne, forme et gain 30 jours en pied.
- La cible devient une puce lisible (CIBLE · TECHNIQUE 14/20 ou AUTO · DÉFENSE 12/20).
- Plus de colonne « — » isolée à droite : le gain est intégré au pied de carte.

### PROGRESSION
- Barre d'outils dédiée avec la date de départ de saison et trois KPI lisibles
  (points gagnés, joueurs en progression, meilleure montée), sans troncature.
- Cartes retravaillées : nom, poste, âge, gain de saison en puce, niveau,
  potentiel et évolutions d'attributs.
- Le libellé « Aucune évolution depuis le début de saison » remplace le texte
  tronqué.

### CALENDRIER
- Les styles des cases sont ciblés sur `QFrame#TrainingDayCell` : les libellés
  enfants ne reçoivent plus de bordures parasites (fini les petits carrés).
- Le libellé de séance est centré verticalement dans la case.
- Le jour de l'éditeur est affiché en français (« Mercredi » et non « Wednesday »).
- Les cartes de contexte ne coupent plus les noms ni les détails.

### VALIDATION
- `test_training_ui` vérifie que le bandeau collectif est absent sur INDIVIDUEL
  et PROGRESSION, et présent sur 2 SEMAINES.
- `test_training_ui`, `test_visual_glitches`, `test_ui_labels_clean`,
  `test_daily_loop`, `test_new_features`, `test_motion_step`,
  `test_dashboard_fit`, `test_tactics_layout`, `test_help_panel`,
  `test_ui_start_render`, `test_academy_development` et les tests de
  délégations staff passent.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_training_tabs/`.


---

## Annexe FF - Tactique : CONSIGNES & COUPS DE PIED, immersion futsal

### DIALOGUE
- Fenêtre 900 × 700, en-tête dédié : icône tactique, titre, sous-titre et
  jauge de familiarité du plan (72 % dans l'exemple).
- Onglets en pastilles sobres : **LE CINQ** et **COUPS DE PIED**.
- Pied de dialogue discret : « Enregistré automatiquement • Échap pour fermer ».

### LE CINQ
- Le tableau dense est remplacé par des cartes joueur sur deux colonnes :
  avatar, nom, poste, rôle naturel, puis RÔLE / PRESSING / DÉFENSE.
- Compteur « 12 JOUEURS » et bouton **RÔLES AUTOMATIQUES** dans la barre.
- Les rôles automatiques sont appliqués sans fermer la fenêtre : les combos
  se mettent à jour sur place et un message confirme la réinitialisation.
- Chaque changement reste enregistré immédiatement.

### COUPS DE PIED
- Quatre cartes de réglage : CORNERS, COUPS FRANCS, SORTIE DE PRESSING,
  POWERPLAY, avec une phrase d'explication qui s'adapte au choix.
- Nouvel aperçu vectoriel `SetPieceBoard` : demi-terrain futsal, but avec filet,
  surface, marques de penalty, pelouse rayée, joueurs et ballon.
- Le schéma s'anime selon le choix :
  - Corner Poteau / Court / Retrait (courses et retrait),
  - Coup franc Direct / Combiné (mur, une-deux, frappe).
- Légende ATTAQUE / DÉFENSE / BALLE, titre du schéma et note d'aperçu.
- Carte **REPÈRES FUTSAL** : Fixo, Ala, Pivot, Gardien.

### VALIDATION
- Nouveau `tests/test_tactical_instructions_ui.py` : deux onglets, 12 cartes de
  rôle, aperçu corner puis coup franc combiné, écriture en base du rôle et du
  schéma.
- `test_tactical_instructions_ui`, `test_tactics_layout`, `test_visual_glitches`,
  `test_ui_labels_clean` et `test_match_pitch2d` passent.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_tactical_setpieces/`.


---

## Annexe FG - Centre de formation : bandeau compact, campus vivant et 2 détections

### BANDEAU CAMPUS
- Le bloc « note du campus » passe de 128 px à **96 px** : note en grand,
  jauge sage courte, statut sur deux lignes.
- Trois puces de synthèse : **JEUNES**, **TALENTS**, **DÉTECTIONS**.
- Le bouton d'ouverture reste à droite quand le campus est fermé ; la jauge
  est vide et la note affiche « FERMÉ ».

### DÉVELOPPEMENT DU CENTRE
- Cartes avec icône vectorielle, pastille de niveau et bouton neutre :
  l'accent reste sur la bordure gauche et la pastille.
- Effets raccourcis sur les cartes (détail complet en infobulle) pour éviter
  les textes tronqués en 4 colonnes.
- « Journée de détection » affiche **1/2** et « 2 journées max par saison ».

### DEUX DÉTECTIONS PAR SAISON
- Nouvelle limite `ACADEMY_DETECTION_SEASON_LIMIT = 2`, compteur et saison
  stockés dans `meta`.
- Le bouton passe à « 2/2 CETTE SAISON » quand les deux journées sont utilisées.
- Le dialogue de développement et la carte de la page affichent le même état.
- Le compteur se réinitialise automatiquement au changement de saison.

### MOYENS / JEUNES
- Carte « LE MOT DU RESPONSABLE » : prochain chantier, conseil de fin de saison
  ou détections épuisées.
- Tableau des jeunes plus large (ratio 1:3), colonne « BONUS » raccourcie,
  noms complets visibles.
- Niveau et potentiel colorés discrètement (sauge / sable).

### VALIDATION
- `test_academy_development` vérifie le plafond de 2 détections par saison.
- `test_academy_facility`, `test_academy_options`, `test_academy_development`,
  `test_new_features` et `test_ui_labels_clean` passent.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_academy_live/`.


---

## Annexe FH - Compétitions : les matchs de coupe ne sont plus des amicaux

### CAUSE
- `match_record` ne stockait pas le type du match. Coupe et amical étaient
  tous les deux enregistrés avec `matchday = 0`.
- L'onglet HISTORIQUE > MES RÉSULTATS affichait donc « AMICAL » pour les deux.

### CORRECTION
- Ajout de `match_record.fixture_type` (`championship`, `cup`, `friendly`).
- Le type est écrit à chaque fin de match.
- Reprise automatique des sauvegardes existantes : pour chaque ancien match
  sans type, le calendrier (`fixture`) est consulté avec la saison, la date et
  les deux clubs pour retrouver s'il s'agissait d'une coupe ou d'un amical.
- L'historique affiche désormais :
  - **COUPE** en sable pour les matchs de coupe,
  - **AMICAL** en gris pour les amicaux,
  - **Jx** pour le championnat.
- La reprise tourne au chargement de la partie et ne touche plus rien une fois
  les types renseignés.

### VALIDATION
- Nouveau `tests/test_history_match_types.py` : un championnat, une coupe et un
  amical, reprise des types puis affichage J2 / COUPE / AMICAL.
- Vérification sur une **copie** de la sauvegarde utilisateur : les matchs de
  coupe de la saison 7 ressortent en COUPE, les amicaux en AMICAL.
- La sauvegarde réelle n'a pas été modifiée (empreinte MD5 identique).
- `test_history_match_types`, `test_competitions_ui`, `test_phantom_cup_repair`,
  `test_new_features`, `test_daily_loop` et `test_ui_labels_clean` passent.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_history_types/`.


---

## Annexe FI - Finances : exploitation compacte et sponsors incarnés

### EXPLOITATION
- Réduction verticale : bandeau de match ramené à 100 px, KPI compacts,
  billetterie/bar/boutique sur une seule rangée.
- Les panneaux « Projection saison » et « Conseil du soir » sont supprimés :
  la projection reste dans le bandeau, le prix conseillé et le bouton
  UTILISER sont intégrés à la billetterie.
- « Autres recettes » devient un bandeau horizontal de cinq mini-cartes
  (VIP, fan zone, parking, diffusion, restaurant).
- Résultat mesuré à 1360 × 900 : contenu 589 px pour un viewport de 732 px,
  **aucune barre de défilement** dans l'onglet Exploitation.

### PALETTE
- Courbe billetterie, jauge d'affluence et barres passent de vert à
  **acier / sable**.
- Revenus, prix conseillé et total utilisent le sable ; les autres libellés
  restent en acier doux.

### SPONSORS
- Générateur de **logos fictifs vectoriels** : plaque sombre, symbole unique
  par sponsor, initiales, couleur déterministe.
- Les trois cartes d'offres affichent leur logo (52 px) au lieu d'un simple
  monogramme.
- Nouveau **RÉSEAU DE PARTENAIRES** : 10 logos sur deux rangées, pour un
  onglet vivant même sans offre en cours.
- Le sponsor signé est mis en avant (bordure sable, mention OFFICIEL) et son
  logo remplace l'icône du bandeau.
- Après signature, le bouton **TROUVER DES SPONSORS** et son statut sont
  masqués ; les offres sont closes et le mur de partenaires reste consultable.

### VALIDATION
- Nouveau `tests/test_finance_sponsors_ui.py` : 10 logos de partenaires,
  3 offres avec logos, signature, bouton masqué, tuile OFFICIEL et logo dans
  le bandeau.
- `test_finance_exploitation`, `test_finance_sponsors_ui`, `test_loans`,
  `test_visual_glitches`, `test_ui_labels_clean` et `test_dashboard_fit`
  passent.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_finance_sponsors/`.


---

## Annexe FJ - Infrastructure : chantier « Tribunes niv. 2 » réparé définitivement

### CAUSE
- Un ancien projet `Tribunes niv. 2` restait dans `facility_project`.
- L'historique des projets supérieurs (niv. 8) et les anciens mouvements
  financiers avaient été purgés par le temps : la réparation ne pouvait plus
  retrouver le vrai niveau et l'arène retombait à 1/2.
- Le chantier niv. 2 était alors relancé, terminé, puis relancé encore.

### CORRECTIFS
- **Plafond historique persistant** : `facility_max_<bâtiment>` mémorise le plus
  haut niveau jamais atteint. Il survit aux purges de news et de finances.
- **Récupération multi-sources** de l'arène : projets terminés, mouvements
  financiers, actualités de chantier (`démarre pour X €`), puis motif de
  corruption (plusieurs « Tribunes niv. 2 » + reste du campus au niveau 6+).
- **Garde-fou** : un chantier dont la cible est inférieure ou égale au niveau
  courant / au plafond est refusé. Impossible de relancer un niv. 2 quand
  l'arène est déjà au niv. 8.
- **Fin de chantier** : `max(niveau actuel, cible, plafond)` ; aucun downgrade.
- **Pas d'anticipation** : un vrai chantier niv. 8 en cours n'est pas appliqué
  avant sa livraison ; un ancien niv. 2 obsolète est neutralisé.
- `upgrade_facility` s'appuie aussi sur le plafond : l'interface ne propose plus
  un chantier inférieur.

### PARTIE UTILISATEUR
- L'arène est restaurée à **8/8** et le chantier fantôme « Tribunes niv. 2 »
  est marqué terminé sans nouvelle actualité.
- Le plafond `facility_max_arena_level = 8` est enregistré : même si une
  ancienne version relançait le bug, le prochain lancement restaurerait 8.
- Il faut **fermer complètement le jeu puis le relancer** pour charger le
  nouveau code.

### TESTS
- Nouveau `tests/test_facility_arena_repair.py` : récupération par finances,
  par actualités, par motif de corruption, garde-fou niv. 2, absence de
  downgrade et non-anticipation d'un chantier niv. 8 en cours.
- `test_infra_save_ui` isolé : il n'active plus jamais une vraie sauvegarde
  (vérifié par empreinte MD5 inchangée).
- Suites infrastructure, académie, visuels et démarrage : toutes passent.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_arena_repair/`.


---

## Annexe FJ-bis - Infrastructure : plafond persistant et sauvegarde réellement réparée

### COMPLÉMENTS
- `facility_max_<bâtiment>` conserve le plus haut niveau atteint, même après
  purge des actualités et des mouvements financiers.
- L'arène est reconstituée depuis : projets terminés, finances, actualités
  (`démarre pour X €`), puis motif de corruption (plusieurs « Tribunes niv. 2 »
  + au moins trois installations principales au niveau 6+).
- Un chantier dont la cible est inférieure ou égale au niveau/plafond est
  refusé. Un vrai chantier supérieur en cours n'est pas appliqué avant sa
  livraison, mais un ancien niv. 2 est neutralisé.
- `upgrade_facility` et `process_facility_projects` utilisent le plafond.

### ÉTAT DE LA SAUVEGARDE ACTIVE
- Arène restaurée à **8/8**.
- Aucun chantier `in_progress` restant.
- `facility_max_arena_level = 8` enregistré.
- Intégrité SQLite : **ok**.
- `data/active_save.txt` restauré sur la sauvegarde réelle et inchangé par les
  tests.

### TESTS
- `test_facility_arena_repair` couvre : finances, actualités, motif de
  corruption, garde-fou niv. 2, non-downgrade et non-anticipation.
- `test_infra_save_ui` n'active plus aucune carrière réelle et ne modifie plus
  `data/active_save.txt` (vérifié par empreinte).
- Suites infrastructure, académie, visuels et démarrage : toutes passent.
- `data/error.log` : **0 octet**.
- Sauvegarde saine finale : `code_backups/backup_*_known_good_arena_repair_final/`.


---

## Annexe FK - Mercato : accords hors fenêtre, changements à l'ouverture

### RÈGLE
- Acheter, vendre ou signer un joueur libre reste **possible hors mercato**.
- Le **changement de club** n'intervient qu'à l'ouverture de la prochaine
  fenêtre (1er juillet ou 1er janvier). Le joueur reste dans son club actuel
  jusqu'à cette date.
- Pendant une fenêtre ouverte, les délais habituels restent : arrivée sous 2-3
  jours pour un achat, signature immédiate pour un joueur libre, vente immédiate.

### ACHATS
- L'offre n'est plus bloquée hors fenêtre.
- L'indemnité est réglée à l'accord ; l'arrivée est programmée à l'ouverture.
- À l'arrivée : vérification du club vendeur, du plafond salarial et
  remboursement de l'indemnité si le joueur n'est plus disponible ou si le
  plafond est atteint.

### VENTES
- Une offre reçue hors fenêtre peut être acceptée.
- Un message `transfer_departure` est programmé à l'ouverture : le joueur
  reste disponible pour le club jusque-là, puis part et le club encaisse
  l'indemnité à cette date.
- À l'ouverture : contrôle du budget acheteur et de l'effectif valide (5
  joueurs minimum) ; annulation propre sinon.

### JOURS LIBRES
- Une signature de joueur libre acceptée hors fenêtre est programmée via
  `transfer_arrival` à l'ouverture ; le joueur reste libre jusque-là.
- Si un autre club le signe avant, la signature est annulée.

### UI
- Le bandeau mercato affiche : « MERCATO FERMÉ • accords possibles •
  changements le JJ/MM/AAAA ».
- Le message final indique « Accord enregistré » et la date effective, au lieu
  d'annoncer une signature immédiate.
- Le joueur n'est pas retiré du terrain pour une vente différée.

### VALIDATION
- Nouveau `tests/test_transfer_window_deferral.py` : offre hors fenêtre
  acceptée, joueur libre + achat + vente programmés au 01/01/2027, frais
  d'achat réglés, puis changements exécutés à l'ouverture.
- `test_transfer_history`, `test_transfer_scouting_ui`, `test_offers_cards`,
  `test_loans`, `test_market_columns`, `test_daily_loop`,
  `test_new_features`, `test_ui_labels_clean` et `test_visual_glitches`
  passent.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_transfer_windows/`.


---

## Annexe FL - Onglets : style pastille Transferts généralisé, ligne blanche retirée

### STYLE GLOBAL
- `QTabBar::tab` reprend exactement le style de la page Transferts :
  fond acier `#101b2a`, bordure `#26374d`, rayon 8, texte `#9fb0c6`,
  padding 6 × 16, espacement 6, gras 900, letter-spacing 0.5.
- Onglet sélectionné : fond `#1b3045`, bordure `#4f6c8b`, texte `#edf5fc`.
- Survol identique au Transferts ; état désactivé adouci.

### LIGNE BLANCHE
- `QTabWidget::pane` passe en fond transparent, bordure 0, marge haute 6.
- `QTabBar` passe en fond transparent, bordure 0, et `qproperty-drawBase: 0`
  pour supprimer la ligne de base dessinée derrière les onglets.
- Les onglets d'investissement qui avaient un liseré vert local utilisent
  désormais le style global comme les autres.

### PORTÉE
- Finances, Compétitions (Championnat/Coupe/Statistiques/Historique/Palmarès),
  Staff, Entraînement, Transferts, Infrastructure, Centre de formation,
  Profil joueur, historique et sous-onglets héritent du même rendu.

### VALIDATION
- `test_visual_glitches`, `test_ui_labels_clean`, `test_finance_exploitation`,
  `test_competitions_ui`, `test_staff_ui`, `test_training_ui` et
  `test_dashboard_fit` passent.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_tabs_pills/`.


---

## Annexe FM - Transferts : plus d'Accepter/Refuser après l'arrivée

### CAUSE
- Le message `transfer_arrival` qui confirme l'arrivée était laissé au statut
  `ready` **sans outcome**.
- L'onglet OFFRES interprétait tout message `ready` sans outcome comme
  « RÉPONSE À CONSULTER » et affichait CONTRE / REFUSER / ACCEPTER.
- Le joueur était déjà dans l'effectif, mais le dossier restait actionnable.

### CORRECTIFS
- Une arrivée réussie enregistre désormais `outcome = completed`.
- État dédié `arrival` :
  - arrivée programmée (waiting) : carte « ARRIVÉE PROGRAMMÉE », uniquement
    OUVRIR, aucun bouton de décision ;
  - arrivée confirmée (ready/handled) : « ARRIVÉE CONFIRMÉE », classée close
    et masquée quand les dossiers clos sont cachés ;
  - arrivée annulée : « ARRIVÉE ANNULÉE », classée close.
- Les anciennes sauvegardes avec un `transfer_arrival` ready sans outcome sont
  aussi classées closes : plus de boutons fantômes.

### VALIDATION
- `test_transfer_window_deferral` vérifie :
  - arrivée programmée sans Accepter/Refuser ;
  - après l'ouverture, aucun bouton de décision fantôme ;
  - ancien message ready sans outcome classé clos.
- `test_transfer_history`, `test_offers_cards`, `test_transfer_scouting_ui`,
  `test_daily_loop`, `test_ui_labels_clean` et `test_visual_glitches`
  passent.
- `data/error.log` : **0 octet**.
- Sauvegarde saine : `code_backups/backup_*_known_good_transfer_arrival_clean/`.

## Annexe FN - Performance : navigation instantanée et rafraîchissements ciblés

### CAUSE
- `show_page` terminait par un `refresh_all()` différé : chaque clic de menu
  reconstruisait tout le jeu (effectif, marché, finances, classements, messages)
  alors que rien n'avait changé depuis la dernière action.
- `refresh_all` recalculait en plus des blocs invisibles : exploitation,
  statistiques, prévisualisation de fréquentation, cartes d'entraînement.
- La messagerie reconstruisait sa liste complète à chaque rafraîchissement,
  même quand la page n'était pas affichée.
- Le mode de difficulté était relu en base plusieurs fois par rafraîchissement,
  et l'inférence d'arène relançait ses requêtes même au niveau maximum.

### CORRECTIFS
- **Navigation sans `refresh_all`** : `show_page` ne rafraîchit plus le jeu.
  Les données restent à jour car chaque action (journée, transfert, match,
  réglage) appelle déjà son propre rafraîchissement.
- **Drapeaux « dirty »** par page :
  `_finance_dirty`, `_finance_exploitation_dirty`, `_facility_dirty`,
  `_market_dirty`, `_training_dirty`, `_calendar_dirty`, `_messages_dirty`,
  `_staff_dirty`.
  Une page n'est recalculée qu'à sa première ouverture ou après une action
  qui l'a marquée périmée.
- **Rafraîchissements ciblés** : `_refresh_finance_page`,
  `_refresh_training_page`, `_refresh_calendar_page`, `_refresh_market_page`,
  `_refresh_facility_page`, `_refresh_competitions_page`, `_staff_refresh`.
- **`refresh_all(ui_only=True)`** : le calendrier peut se rafraîchir sans
  marquer Finance / Infrastructure / Marché comme périmés.
- **Entraînement paresseux** : `refresh_training_schedule` ne construit plus
  les cartes Progression et Individuel ; elles sont créées à l'activation de
  leur onglet, puis conservées.
- **Messagerie paresseuse** : la liste n'est reconstruite que si la page est
  visible ; sinon un simple drapeau est posé.
- **Staff** : `_staff_refresh` enveloppe l'implémentation et remet le drapeau
  à zéro ; le calcul complet n'a lieu qu'à l'ouverture ou après une action.
- **Cache du mode de difficulté** : lu une fois par session, invalidé au
  changement d'options.
- **Inférence d'arène** : arrêt immédiat si le niveau courant est déjà 8.

### MESURES (sauvegarde réelle, rendu hors écran)
- Démarrage : `init_db` ~120 ms, `MainWindow` ~1,7 s.
- `refresh_all` : ~125 ms (contre ~350 ms avant la phase).
- Navigation stable (2e passage) : **2 à 7 ms** par page.
- Pages lourdes, premier passage seulement :
  - Entraînement ~47 ms (au lieu de ~950 ms) ;
  - Infrastructure ~127 ms (une fois) ;
  - Transferts ~120 ms (une fois) ;
  - Calendrier ~120 ms (une fois) ;
  - Finances ~28 ms (une fois) ;
  - Staff ~33 ms (une fois) ;
  - Messagerie ~17 ms ;
  - Recherche ~250 ms (une fois), ~8 ms ensuite.
- Total d'un tour complet de 14 pages : ~670 ms au premier passage,
  ~100 ms ensuite (contre ~5 400 ms avant la phase).

### VALIDATION
- Suite complète `python tests\run_tests.py` : **ALL OK**.
- `data\error.log` : **0 octet** après la suite et après les benchmarks.
- `data\active_save.txt` inchangé ; aucune écriture dans les sauvegardes
  utilisateur (tests sur copies TEMP).
- Sauvegarde active : intégrité SQLite `ok`, arène 8/8,
  `facility_max_arena_level = 8`.
- Sauvegarde saine :
  `code_backups/backup_*_known_good_perf_fluid/`.

## Annexe FO - Captures de presentation et finitions reperees a l'ecran

### BESOIN
- Produire un jeu de visuels propre pour presenter FM2027V2 : ecran d'accueil,
  creation de club, 14 pages, tous les onglets et sous-onglets, messagerie,
  centre de match (avant-match, direct, action, rapport).

### INCOHERENCES REPEREES EN CAPTURANT
- La liste « DERNIERES SAUVEGARDES » de l'accueil affichait la date ISO
  (`2033-01-02`) au lieu du format francais.
- Le bouton de lancement du match etait tronque a l'ecran : « VALIDER L' ».

### CORRECTIFS
- Accueil : la date des sauvegardes recentes passe par `fmt_date_fr`, donc
  **JJ/MM/AAAA** comme partout ailleurs.
- Centre de match : libelle court « VALIDER » (le detail reste dans l'infobulle
  « Verifier le cinq de depart avant le coup d'envoi »), plus de troncature.
- Nouvel outil reutilisable : `tests/capture_presentation.py`.
  - capture les 14 pages, les onglets visibles et leurs sous-onglets ;
  - capture la messagerie (boite de reception + dossiers a traiter) ;
  - capture le centre de match (avant-match, direct, action, rapport) ;
  - capture l'accueil et la creation de club ;
  - travaille sur une **copie TEMP** de la sauvegarde active, jamais sur
    `data/active_save.txt` ni sur les sauvegardes utilisateur.

### LIVRABLES
- Dossier `captures_fm2027/` (55 PNG, 1600x1000 sauf le rapport en 1240x920) :
  - `01_ecran_daccueil.png`, `creation_club.png` ;
  - 14 pages numerotees de la Direction sportive au Centre de formation ;
  - onglets Transferts (6), Entrainement (3), Finances (4), Calendrier (3),
    Infrastructure (2 + 3 sous-onglets), Staff (2), Competitions (5 + 5
    sous-onglets) ;
  - messagerie « a traiter », reglages tactiques avances ;
  - centre de match : avant-match, direct, action, rapport de match.
- `index.md` : table des captures.
- `planche_contact_pages.png` : vue d'ensemble des 14 pages.

### VALIDATION
- Regeneration : `python tests\capture_presentation.py [dossier]`.
- Suites ciblees : `date_formats`, `ui_start_render`, `visual_glitches`,
  `match_pitch2d`, `ui_labels_clean`, `splash_sequence` -> **ALL OK**.
- `data/error.log` : **0 octet**.
- Aucune ecriture dans la sauvegarde active (copies TEMP uniquement).

## Annexe FP - Saison test par difficulte et sauvegarde « changement de club »

### TEST : UNE SAISON PAR NIVEAU
- Outil : `tests/sim_season_difficulties.py` (univers neuf a chaque fois,
  Ligue 3, une saison jouee match par match puis transition de saison).
- Niveaux : Facile (creation Facile), Normal (creation Normal),
  Difficile (creation Difficile + mode en jeu Difficile).

| Niveau | Rang | Pts | Buts | Budget debut | Budget fin | Board | Offres |
|---|---|---|---|---|---|---|---|
| Facile | 2e (promotion) | 32 | 47-36 | 1 593 750 € | 2 099 533 € | 79 | 2 |
| Normal | 10e (relegation) | 14 | 33-52 | 1 275 000 € | 1 583 759 € | 65 | 0 |
| Difficile | 9e (relegation) | 17 | 35-53 | 918 000 € | 1 098 385 € | 61 | 0 |

- Les moyens de depart suivent exactement les modificateurs (1,25 / 1,00 /
  0,72) et l'ecart de niveau d'effectif est bien applique.
- Le classement reste une photo d'une seule saison : la variance des matchs
  peut inverser deux niveaux voisins. Le test sert de fumee d'equilibrage,
  pas de preuve statistique.

### BUG CORRIGE : OFFRES DE CLUB
- Un manager en **Ligue 1** ne pouvait jamais recevoir d'offre : la liste des
  clubs candidats ne regardait que les divisions superieures (`cdiv < div`),
  donc vide au sommet de la pyramide.
- Une **relegation** pouvait aussi declencher des offres de clubs plus huppes
  des que la confiance du board depassait 68.
- Correctifs dans `generate_job_offers` :
  - une relegation n'est plus consideree comme une saison « forte » ;
  - si aucun club n'est au-dessus, proposition de **mouvement lateral** parmi
    les six meilleurs clubs de la meme division.

### SAUVEGARDE PREPAREE
- Fichier : `data/saves/test_changement_club_20261030_194018.db`
  (nom de slot « Test - Changement de club »).
- Contenu : Arbot Futsal, saison 8 au 01/07/2033, champion de Ligue 1 la saison
  precedente (48 pts, 71-28), deux offres en attente sur la Direction sportive :
  - **Union Sportive de Rome** (Ligue 1, 2e la saison passee) ;
  - **Amicale Laique de Lisbonne** (Ligue 1, 3e la saison passee).
- Chaque offre propose ACCEPTER LE POSTE / REFUSER. La sauvegarde active et
  `data/active_save.txt` ne sont pas touches : il faut la charger depuis
  CHARGER / SAUVEGARDES.
- Outil : `tests/prepare_club_change_save.py` (copie TEMP, fin de saison,
  transition, ecriture d'une nouvelle sauvegarde, relecture de controle).

### VALIDATION
- `sim_season_difficulties` : **ALL OK** (3 saisons, 0 erreur).
- `prepare_club_change_save` : sauvegarde creee et relue, 2 offres, panneau
  visible.
- Suites : `balance_soak`, `club_swap`, `daily_loop`, `new_features`,
  `ui_start_render`, `date_formats`, `visual_glitches` -> **ALL OK**.
- `data/error.log` : **0 octet**.

### COMPLEMENT
- Nouvelle suite de non-regression : `tests/test_job_offers.py` (ajoutee au
  registre `run_tests.py`).
  - champion de Ligue 1 -> 2 offres laterales dans la meme division ;
  - relegation -> aucune offre ;
  - saison moyenne sans confiance -> aucune offre.
- Acceptation testee sur une **copie** de la sauvegarde preparee :
  Arbot Futsal -> Union Sportive de Rome, budget 6 818 001 €, reputation 92,
  offres videes, integrite SQLite `ok`.

## Annexe FQ - Changement de club : messagerie videe, club neuf et accueil

### DEMANDE
- Vider la messagerie lors d'un changement de club.
- Appliquer les elements du nouveau club (et non ceux du club quitte).
- Ajouter un message de bienvenue.

### CORRECTIFS DANS `change_manager_club`
- **Messagerie remise a zero** : `manager_message`, `manager_message_archive`
  et le journal `news` du club quitte sont supprimes.
- **Elements du club quitte effaces** : chantiers `facility_project`, prets
  bancaires `loan`, sessions d'entrainement et journal d'actions d'effectif.
- **Nouveau club sans heritage** :
  - sponsor (`sponsor_deal`, `sponsor_used_season`) supprime : a ressigner ;
  - centre de formation recale sur le niveau de jeunes du club cible
    (`academy_unlocked` = 1 si `youth_level` >= 6), detections remises a zero ;
  - rival supprime puis recalcule pour le nouveau club ;
  - installations et **plafonds `facility_max_*`** recalcules depuis le profil
    estime du club cible (plus de niveaux 8 herites) ;
  - plans et connaissances IA (`ai_club_plan`, `ai_scout_knowledge`,
    `ai_manager_history`) echanges avec l'ancien club ;
  - objectifs du board recrees pour le nouveau club avant l'accueil.
- **Message de bienvenue** : message persistant `club_news`
  « Bienvenue a <club> » dans la boite de reception (non lu), actualite
  « Nouveau club » sur la Direction sportive, et toast de confirmation.
- **Messagerie re-identifiee** : le rail (nom, adresse, avatar) et l'en-tete
  suivent le nouveau club ; les noms/adresses longs sont elides avec infobulle.
- Toast corrige en `success` (etait `succes`).

### SAUVEGARDE DE TEST
- `data/saves/test_changement_club_20261030_201049.db`
  (slot « Test - Changement de club (v2) »).
- Saison 8 au 01/07/2033, champion de Ligue 1, deux offres :
  Union Sportive de Rome (2e) et Renaissance de Bruxelles (1er).
- Apres ACCEPTER LE POSTE : club, effectif, budget, installations, sponsors,
  centre de formation, messagerie et objectifs basculent sur le nouveau club,
  avec un seul message « Bienvenue ».
- Capture : `captures_fm2027/bienvenue_nouveau_club.png`.

### VALIDATION
- Nouvelle suite `tests/test_club_change_elements.py` :
  - club bascule, messagerie videe + 1 message de bienvenue ;
  - archives/actualites/chantiers/prets effaces ;
  - sponsor, centre de formation, rival, offres remis a zero ;
  - installations et plafonds du nouveau club ;
  - objectif du board et messagerie re-identifiee.
- Suite complete `python tests\run_tests.py` : **ALL OK**.
- `data/error.log` : **0 octet**.

### COMPLEMENT - INFRASTRUCTURES DU NOUVEAU CLUB
- Les batiments secondaires suivaient encore l'ancien club : location de
  terrains, salle evenementielle, fan zone, laboratoire video, benevoles et
  restaurant. Ils sont desormais estimes depuis le profil du club cible
  (`club_facility_profile`) et ecrits en base au changement de club.
- Bug corrige : la conversion `est.get(col,1) or 1` transformait un `0` en `1`
  et reactivait les drapeaux (VIP, boutique, salle evenementielle) du club
  quitte. Les valeurs `0` sont maintenant conservees.
- La suite `test_club_change_elements` bascule vers un club de **Ligue 4** :
  les niveaux passent bien de 8/8 a 3/3/2 (arene/medical/jeunes), avec
  VIP 0, salle evenementielle 0, video 1, restaurant 1.

## Annexe FR - Fiche club : effectif respire et onglet DERNIERS MATCHS

### DEMANDE
- Meilleur affichage de la fiche des autres clubs.
- Effectif trop a l'etroit.
- Separer les derniers matchs sur un onglet dedie.

### CORRECTIFS
- Fenetre de fiche club agrandie : **1280 x 940** (minimum 1000 x 720).
- Les six indicateurs passent sur **une seule ligne** : budget, effectif,
  bilan, differentiel, forme (5 derniers), top buteur.
- La synthese d'effectif devient une ligne compacte : niveau moyen, age moyen,
  masse salariale, valeur, fins de contrat.
- Cartes joueurs plus denses : hauteur 74 px, avatar 40 px.
- Le tableau « derniers matchs » ne mange plus l'onglet EFFECTIF : celui-ci
  occupe toute la hauteur restante (5 a 6 joueurs visibles d'un coup).
- **Nouvel onglet DERNIERS MATCHS** (tous les clubs) :
  - 10 dernieres rencontres, toutes competitions ;
  - date JJ/MM/AAAA, competition (Jxx / COUPE), domicile, score colore
    (vert victoire, jaune nul, rouge defaite), exterieur ;
  - resume « N match(s) • xV yN zD » et legende.
- Pour les autres clubs, l'onglet EFFECTIF reste l'onglet d'ouverture.

### VALIDATION
- Nouvelle suite `tests/test_club_sheet_ui.py` : taille de la fiche, onglets,
  effectif sans tableau de matchs, onglet DERNIERS MATCHS avec 8 lignes.
- `tests/test_club_sheet_ai.py` mis a jour pour la nouvelle synthese d'effectif
  et l'onglet dedie.
- Suite complete `python tests\run_tests.py` : **ALL OK**.
- `data/error.log` : **0 octet**.
- Captures : `captures_fm2027/fiche_club_effectif.png` et
  `captures_fm2027/fiche_club_derniers_matchs.png`.

## Annexe FS - Coupe : le bloc REPÈRES suit vraiment les tours

### CAUSE
- Le dénominateur du KPI valait `len(rounds)` : comme les tours sont créés au
  fur et à mesure, il affichait toujours `N/N` (et `1/1` au premier tour).
- Les exemptés étaient annoncés « DU 1ER TOUR » en permanence.
- Le PETIT POUCET rajoutait les exemptés du 1er tour à chaque tour : au moment
  de la finale, 4 clubs éliminés depuis longtemps réapparaissaient comme
  « encore en lice ».
- Après la finale, le statut restait « QUALIFIÉ », la bannière « EN COURS » et
  l'enjeu « VAINQUEUR : 1 000 000 € ».
- À l'ouverture, le tableau affichait « TOUS LES TOURS » et commençait donc
  toujours par les 32es, ce qui donnait l'impression de rester au 1er tour.

### CORRECTIFS
- Nombre total de tours calculé depuis `cup_slots` (64 places -> 6 tours).
  Le KPI affiche désormais `2/6 · 16es`, `3/6 · 8es`, etc.
- Le KPI « MATCHS AU TABLEAU » devient **MATCHS DU TOUR** (nombre de
  confrontations du tour courant).
- À l'ouverture de l'onglet, le filtre se place sur le **tour courant** ; les
  rafraîchissements de fond conservent le filtre choisi par le joueur.
- EXEMPTÉS : « DU 1ER TOUR » avant le 2e tour, puis « D'ENTRÉE (N) : intégrés au
  2e tour ».
- PETIT POUCET : les exemptés ne sont ajoutés qu'au 1er tour ; le tour affiché
  est le tour courant (ou le suivant si le tour vient de se terminer), et le
  nombre de survivants par division est exact.
- Coupe terminée :
  - bannière « SAISON X · TERMINÉE » ;
  - statut « VAINQUEUR » pour le club du manager, sinon « ÉLIMINÉ » ;
  - parcours « vainqueur de la Coupe Inter-Ligue » ou « éliminé · X remporte » ;
  - enjeu « COUPE GAGNÉE · +1 000 000 € » ;
  - repères « COUPE TERMINÉE · VAINQUEUR : X ».

### VALIDATION
- Nouvelle suite `tests/test_cup_reperes.py` : tableau 64 -> 6 tours,
  passage 2/6 puis 3/6, exemptés au 2e tour, survivants du 3e tour = 16,
  finale -> « TERMINÉE » + « VAINQUEUR » + « COUPE TERMINÉE ».
- Suite complète `python tests\run_tests.py` : **ALL OK**.
- `data/error.log` : **0 octet**.
- Capture : `captures_fm2027/coupe_reperes.png`.

## Annexe FT - Centre de formation : un chantier à la fois, avec délai

### DEMANDE
- Limiter les actions du centre de formation.
- Mettre un temps de développement avant qu'une amélioration soit active.

### CORRECTIFS
- **Un seul chantier de développement à la fois** : lancer une structure ou un
  éducateur bloque les autres cartes (`BLOQUÉ`) jusqu'à la livraison.
- **Délais de livraison** :
  - niveau 1 : **14 jours** ;
  - niveau 2 : **21 jours** ;
  - niveau 3 : **28 jours**.
- Le coût est payé au lancement (ligne de trésorerie « chantier »), mais le
  niveau n'est appliqué qu'à l'échéance.
- Suivi quotidien (`complete_academy_dev_project`) + vérification paresseuse à
  l'ouverture de la page : pas de chantier bloqué si le joueur avance plusieurs
  jours d'un coup.
- UI :
  - carte active : pastille `NIV. 1→2`, statut `Chantier en cours · J-21`,
    bouton `EN COURS` ;
  - autres cartes : `Un chantier est en cours` / `BLOQUÉ` ;
  - en-tête : `... • chantier : École de football J-21`.
- Fin de chantier : actualité + message `club_news`
  « Chantier terminé : ... » et application immédiate du bonus.
- La journée de détection (2/saison, cooldown 14 jours) et les moyens renforcés
  (1/saison) restent les autres actions limitées du centre.
- Le dialogue secondaire de développement affiche le même état de chantier.

### VALIDATION
- Nouvelle suite `tests/test_academy_project.py` : lancement, blocage du
  deuxième chantier, livraison à l'échéance, message, niveau 2 à 21 jours.
- `test_academy_options` et `test_academy_development` adaptés au flux chantier.
- Suite complète `python tests\run_tests.py` : **ALL OK**.
- `data/error.log` : **0 octet**.
- Capture : `captures_fm2027/centre_formation_chantier.png`.

## Annexe FV - Prêts : suivi, évolution, fiche et fin de prêt

### DEMANDE
- Suivre nos joueurs prêtés.
- Cliquer sur un joueur pour ouvrir sa fiche.
- Voir son évolution.
- Mettre fin au prêt s'il ne joue pas.

### CORRECTIFS
- Nouvel onglet PRÊTS enrichi :
  - colonnes `NIVEAU`, `ÉVOLUTION`, `TEMPS DE JEU` (au lieu du simple compteur
    de matchs) ;
  - `ÉVOLUTION` compare le niveau actuel à la référence
    `player_attr_baseline` de début de saison (`+1 niv.`, `+12 pts`, `stable`) ;
  - `TEMPS DE JEU` affiche `matchs depuis le prêt / matchs du club depuis le
    prêt` pour les nouveaux prêts, et `X m. saison` pour les prêts plus anciens.
- Deux nouvelles colonnes `player.loan_start_matches` et
  `player.loan_start_date`, remplies à la signature du prêt (sortant et
  entrant). Le temps de jeu est donc calculé depuis l'arrivée, sans compter les
  matchs joués avant le prêt.
- Double-clic sur une ligne = **fiche complète du joueur** ; bouton
  `FICHE DU JOUEUR` pour la même action.
- Alerte de sous-utilisation : promesse TITULAIRE = 65 % des matchs du club,
  ROTATION = 35 % (à partir de 3 matchs du club). La cellule passe en rouge
  avec `⚠` et un bandeau indique `N prêt(s) sans temps de jeu`.
- `METTRE FIN AU PRÊT` :
  - prêt sortant qui ne joue pas : rappel immédiat (confirmation) ;
  - prêt sortant qui joue assez : action bloquée avec renvoi vers
    `RAPPELER LE JOUEUR` ;
  - prêt entrant : fin de prêt classique.
- Les anciennes sauvegardes sont migrées automatiquement (colonnes ajoutées,
  valeurs par défaut).

### VALIDATION
- Nouvelle suite `tests/test_loan_tracking.py` : colonnes, évolution, temps de
  jeu, double-clic fiche, fin de prêt si le joueur ne joue pas, blocage s'il
  joue, fin de prêt entrant.
- Suite complète `python tests\run_tests.py` : **ALL OK**.
- `data/error.log` : **0 octet**.
- Capture : `captures_fm2027/prets_suivi.png`.

## Annexe FW - Messagerie : badge leger, notifications sans charger la page

### CAUSE
- Le badge etait calcule a partir des 40 messages `waiting/ready` charges par
  `refresh_all`. Ces 40 lignes etaient majoritairement des rapports de scouting,
  filtres ensuite de la liste : le compteur tombait a 0 et le badge restait
  cache.
- Depuis la navigation paresseuse, la page Messagerie n'est plus reconstruite
  hors écran : sans compteur dedie, plus aucune notification visible.

### CORRECTIF
- `message_badge_count()` : une seule requete `COUNT(*)` sur les messages non
  lus, sans charger la liste ni les widgets. Les catégories masquées sont
  exclues (`scout_report`, et `media` si l'option est coupee), comme dans la
  boite de reception.
- `_apply_message_badges()` met a jour la pastille de la barre laterale et celle
  du compte messagerie, sans toucher a la liste.
- `refresh_message_badges()` est appele :
  - par un **timer leger de 30 s** ;
  - apres chaque `refresh_all` / journee ;
  - a l'ouverture de la Messagerie (meme compteur complet).
- La page n'est toujours PAS chargee pour afficher la notification : le drapeau
  `_messages_dirty` reste arme jusqu'a son ouverture.

### VALIDATION
- Nouvelle suite `tests/test_message_badges.py` :
  - 2 infos + 5 rapports scouting non lus -> badge `2` (scouting ignore) ;
  - badge mis a jour sans ouvrir la messagerie ;
  - `_messages_dirty` reste vrai ;
  - timer de 30 s ;
  - ouverture de la messagerie -> compteur synchronise.
- Suite complete `python tests\run_tests.py` : **ALL OK**.
- `data/error.log` : **0 octet**.
- Capture : `captures_fm2027/notif_messagerie.png`.

## Annexe FX - Ventes différées : plus d'offres sur un joueur déjà vendu

### CAUSE
- `generate_transfer_interest` excluait seulement les joueurs ayant déjà une
  offre de vente active. Un joueur dont le départ était programmé au 01/07
  restait donc ciblable : de nouvelles offres apparaissaient.
- L'acceptation d'une vente ne vérifiait pas qu'un départ était déjà programmé :
  un même joueur pouvait accumuler plusieurs `transfer_departure` (3 pour un
  joueur dans la sauvegarde active).
- Les anciennes offres restaient au statut `ready` dans l'onglet OFFRES.

### CORRECTIF
- `pending_departure_ids()` : liste des joueurs avec un départ déjà programmé.
- `repair_pending_departures()` :
  - ne conserve qu'un seul départ par joueur (le premier accord),
  - classe les doublons (`duplicate`),
  - classe toutes les offres de vente encore ouvertes (`already_sold`),
  - retire le joueur de la liste des transferts.
- Le nettoyage tourne au chargement (une fois par session) et à chaque ouverture
  de l'onglet OFFRES.
- `generate_transfer_interest` exclut désormais ces joueurs (offres listées et
  spontanées).
- Accepter une offre sur un joueur déjà vendu ne crée plus un second départ :
  l'offre est classée et un message l'explique.

### VALIDATION SUR LA SAUVEGARDE ACTIVE (copie)
- 7 départs en attente -> **5 départs uniques** (doublons classés).
- 4 offres fantômes sur ces joueurs -> **0**.
- Joueurs concernés retirés de la liste des transferts.
- Aucune écriture dans la vraie sauvegarde : réparation appliquée à l'ouverture.

### TESTS
- Nouvelle suite `tests/test_sold_player_offers.py` : doublon de départ,
  offres classées, joueur retiré de la liste, offre tardive refusée et classée.
- Suite complète `python tests\run_tests.py` : **ALL OK**.
- `data/error.log` : **0 octet**.

## Annexe FY - Coupe : message de bilan du parcours et primes

### DEMANDE
- Recevoir un message retraçant le parcours de coupe.
- Avoir un récapitulatif et l'argent gagné.

### CORRECTIF
- `send_cup_recap()` construit un message unique par saison avec :
  - le parcours tour par tour (domicile/exterieur, adversaire, score, V/D) ;
  - le statut final : VAINQUEUR ou ÉLIMINÉ au tour X ;
  - le total des primes du parcours, dont le 1 000 000 € du titre.
- Envoi automatique :
  - à l'élimination (match de coupe perdu) ;
  - a la victoire en finale ;
  - vérification paresseuse `ensure_cup_recap()` au chargement et a l'ouverture
    de l'onglet COUPE, pour les sauvegardes ou la coupe est déjà terminée.
- Un drapeau `cup_recap_<saison>` garantit un seul message.
- Le panneau REPÈRES affiche aussi `PRIMES DU PARCOURS : X €` en permanence.

### VALIDATION SUR LA SAUVEGARDE ACTIVE (copie)
- Coupe saison 7 déjà terminée : le message est généré au chargement.
- Parcours complet affiche (32es -> finale), statut VAINQUEUR.
- Total : **1 700 000 €** (6 primes de tour + 1 000 000 € de titre).
- Un seul message créé, meme apres plusieurs rafraîchissements.

### TESTS
- `tests/test_cup_reperes.py` vérifie désormais le message de bilan, son
  contenu (parcours + primes) et l'absence de doublon.
- Suite complete `python tests\run_tests.py` : **ALL OK**.
- `data/error.log` : **0 octet**.
- Capture : `captures_fm2027/coupe_bilan_message.png`.

## Annexe FZ - Marché : le tri porte sur tout le marché (30/10/2026)

### DEMANDE
- En triant le marché (ex. POTENTIEL), les meilleurs profils apparaissaient en
  page 3 : il fallait changer de page pour les voir alors qu'on avait trié.

### CAUSE
- La pagination découpait d'abord `filtered` en pages de 20, puis
  `QTableWidget.sortItems()` triait **uniquement les 20 lignes affichées**.
- Le tri Qt restait actif : un clic d'en-tête réordonnait la page courante sans
  recharger le marché.

### CORRECTIF
- `refresh_market_only()` trie désormais **toute la liste filtrée** avant la
  pagination, via `_market_sorted_rows()` + `_market_sort_key()` (mêmes valeurs
  de tri que le tableau : niveau, potentiel, forme, valeur, scout, etc.).
- Ordre : valeurs connues d'abord (asc/desc selon l'en-tête), puis colonnes
  texte (nom, club, poste, nationalité), puis valeurs inconnues en fin de liste.
- Tri Qt désactivé (`setSortingEnabled(False)`) pour éviter le double tri ;
  `_market_header_clicked()` gère le clic d'en-tête : bascule asc/desc,
  affiche la flèche (`setSortIndicator`) et **revient page 1**.
- L'ordre par défaut du marché (libres puis listés puis valeur) est conservé
  tant qu'aucun en-tête n'a été cliqué.

### VALIDATION
- Sauvegarde active (copie TEMP) : 736 joueurs, 37 pages.
- Tri POTENTIEL décroissant : les 5 premiers (20/20) sont en page 1.
- Tri ÂGE décroissant : 39, 38, 38… en page 1 ; la page 2 continue l'ordre.
- Tri conservé après changement de page et rafraîchissement.
- Capture : `data/apercu_marche_tri_potentiel.png`.

### TESTS
- Nouvelle suite `tests/test_market_sort.py` (tri global, pagination, retour
  page 1, ordre par défaut) branchée dans `tests/run_tests.py`.
- Suite complète `python tests\run_tests.py` : **ALL OK**.
- `data/error.log` : **0 octet**.

## Annexe GA - Offres de club : message SECRET / privé (30/10/2026)

### DEMANDE
- Quand un club veut recruter le manager (propositions de changement de club),
  recevoir **en plus** un message privé, du genre SECRET / confidentiel.

### MISE EN PLACE
- Nouveau type de message `job_offer` :
  - titre `🔒 SECRET — <Club> veut vous recruter` ;
  - corps « CONFIDENTIEL — ne pas diffuser. » + club, ligue, projet, marche à
    suivre (répondre dans Direction sportive) et rappel que décliner ne casse
    rien ;
  - expéditeur = le club, adresse `secret@<club>.fm` ;
  - badge `SE` doré et libellé « SECRET • OFFRE DE CLUB » ;
  - pastille d'état **CONFIDENTIEL** dans la lecture du message.
- Nouvelle famille de messagerie **Carrière** (`job_offer`), avec pastille de
  compteur, dossier dédié et option `msg_cat_carriere` dans Options →
  MESSAGERIE (« Offres de club (SECRET) »).
- Bouton **VOIR LES OFFRES DE CLUB** dans le message : ouvre la Direction
  sportive (panneau OFFRES DE CLUB où l'on accepte ou refuse).
- Génération dans `generate_job_offers()` via `_notify_job_offers()` :
  - un message par club recruteur, créé en même temps que la news publique ;
  - **une seule vague par saison** (méta `job_offer_notified`) : pas de doublon
    si la génération repasse ;
  - refuser une offre (`_decline_job_offer`) clôt son message
    (`status='handled'`, lu) et rafraîchit la boîte.
- Sauvegardes existantes : `refresh_job_offers()` crée à la volée les messages
  SECRET manquants pour les offres déjà en attente (aucun doublon).

### VALIDATION
- Sauvegarde de test (Ligue 1, champion) : 2 offres → 2 messages SECRET.
- Sauvegarde active (copie) : 2 offres déjà en attente (Rome, Milan) → les 2
  messages SECRET apparaissent à l'ouverture, sans doublon au rafraîchissement.
- Dossier Carrière : 2 messages, 2 non lus ; lecture = badge CONFIDENTIEL +
  bouton VOIR LES OFFRES DE CLUB.
- Refus : le message lié passe en « traité », l'offre disparaît du panneau.
- Capture : `data/apercu_message_secret.png`.

### TESTS
- `tests/test_job_offers.py` étendu : création des messages, contenu SECRET,
  absence de doublon, famille `carriere`, badge `SE`, clôture au refus.
- `tests/test_messaging_ui.py` mis à jour : 7 familles d'options, présence de
  `msg_cat_carriere` (coché par défaut).
- Suite complète : **ALL OK** · `data/error.log` : **0 octet**.

## Annexe GB - Moteur de match v2 : mentalités, dynamique et réalisme (31/10/2026)

### DEMANDE
- Analyser en profondeur le moteur entre les équipes, exploiter le maximum de
  stats et de réglages, pousser le réalisme, garder de l'aléatoire et de la
  surprise, et faire en sorte que **les mentalités se ressentent** en jeu.

### ANALYSE
- Document complet : `ANALYSE_MOTEUR_MATCH.md` (architecture, ce qui était
  modélisé, les 10 manques, le plan v2, les mesures).

### CORRECTIFS
- **Identité tactique complète** (`club_profiles.py`) : chaque profil de club
  reçoit mentalité, hauteur de bloc, largeur, axe de jeu et discipline, en plus
  du style/formation/pressing/tempo. `identity_for_club()` remplace
  `style_for_club()` dans `opponent_tactical_identity()` (les 4 clés
  historiques restent identiques).
- **Moteur IA v2** (`match_engine.py`) :
  - forme du jour (moral + condition + hasard), arbitre tiré par match ;
  - possession pondérée (passe, style, pressing, tempo, fatigue, momentum) ;
  - duel individuel porteur/défenseur à chaque séquence (les stars pèsent) ;
  - occasion nette / normale / spéculative avec conversions distinctes ;
  - erreur de gardien, frappe déviée, corner, 6e faute → 10 m, blessures en match ;  - fautes liées à la discipline et au pressing, cartons liés à l'arbitre,
    **rouge = 2 minutes à 4** avec vrai malus ;
  - momentum (buts, grosses occasions) et effet du score dans le money-time ;
  - **fatigue en direct** (pressing/tempo se paient, endurance amortit) ;
  - notes, cartons, buts, passes et fatigue cohérents avec le déroulé.
- **Moteur manager** (`app.py`) : la mentalité devient un arbitrage symétrique
  (Offensive +6 % attaque / −4,5 % défense / conversion +3 % ; Prudente
  −4,5 % attaque / +5 % défense / conversion −3 %), appliqué aussi à l'IA.
  Gestion de score des 8 dernières minutes selon la mentalité, momentum amplifié
  pour l'offensive et amorti pour la prudente.

### VALIDATION
- 400 matchs/scénario : équipes égales **4,69 buts/match**, domicile **48 %**,
  nul 15 %, extérieur 37 % ; +20 points de niveau → **75 %** de victoires mais
  **11,5 %** d'exploits.
- Mentalités à niveau égal : offensive **2,75** marqués / **2,44** encaissés ;
  prudente **2,60** / **2,08** — aucune n'est dominante.
- Discipline : 2,5 cartons/match, 0,13 rouge/match.
- Soak 599 matchs : **4,82 buts/match**, 0 erreur, `error.log` 0 octet.

### TESTS
- Nouvelle suite `tests/test_match_engine_v2.py` (déterminisme, domicile,
  hiérarchie, buts/match, mentalités, discipline, rapport) branchée dans
  `tests/run_tests.py`.
- `tests/test_ai_profiles.py` adapté à l'identité enrichie (les 4 clés
  historiques restent vérifiées).
- Suite complète : **ALL OK** · `data/error.log` : **0 octet**.

## Annexe GC - Rendu 2D fluide et lisible (31/10/2026)

### DEMANDE
- Rendre le terrain 2D plus fluide, « comme un vrai match de futsal »,
  améliorer la retranscription des textes et supprimer les sauts brusques
  entre temps réel et actions.

### CORRECTIFS (`match_pitch2d.py`)
- **Course lissée** : chaque pion a une vitesse (`vx/vy`) et une accélération ;
  plus de changement de direction instantané, les trajectoires décrivent des
  courbes (freinage à l'arrivée inclus).
- **Ballon physique** : vitesse, inertie, impulsions de frappe/passe, conduite
  de balle sur le porteur, ombre portée et **traînée** sur les actions vives.
- **Porteur réaliste** : le porteur est le joueur le plus proche du ballon (et
  non plus un index qui tournait) ; sur une passe, le ballon vise **le joueur
  nommé** dans le détail (« Cissé → Roussel »).
- **Cadence adaptative** : `set_pace(intervalle_ms)` raccourcit les verrous
  d'action quand la simulation accélère (1× → 5×), pour que le ballon suive
  toujours l'action au lieu de sauter d'une cible à l'autre.
- **Textes** : libellés d'action enrichis (TIR CADRÉ, RÉCUPÉRATION,
  INTERCEPTION, CARTON JAUNE/ROUGE, 10 M, TEMPS MORT, CONSIGNE…), pastille
  d'action en **pilule arrondie** (couleur du club, détail sur deux lignes,
  fondu entrée/sortie), overlay AVANT-MATCH / MI-TEMPS / FIN DU MATCH en pilule.
- **Popup BUT** recalibrée : plus compacte, descendue sous le centre, le
  terrain et les joueurs restent visibles pendant la célébration.
- **Changement de côté / remplacement** : vitesses remises à zéro pour éviter
  les glissades fantômes.

### VALIDATION
- 3 captures successives (220 ms d'écart) : ballon et joueurs avancent en
  continu, aucun saut (pas max mesuré 0,064 sur une frappe).
- 5× : `pace_k = 0,35`, match joué sans erreur, ballon toujours sur l'action.
- Captures : `data/apercu_pitch_1..3.png`, `data/apercu_pitch_5x.png`.

### TESTS
- Nouvelle suite `tests/test_pitch_flow.py` (vitesse bornée joueurs/ballon,
  cadence 1×/5×, passe nommée, rendu sans exception) branchée dans
  `tests/run_tests.py`.
- `test_pitch_render.py` et `test_visual_glitches.py` inchangés et verts.
- Suite complète : **ALL OK** · `data/error.log` : **0 octet**.

## Annexe GD - Audit de jeu : 6 divisions, styles et scénarios (31/10/2026)

### DEMANDE
- Lancer des tests de jeu pour trouver des bugs et les corriger, sur
  différentes divisions et différents styles de club.

### MATRICE JOUÉE
| Division | Durée | Matchs manager | Transition | Résultat |
|---|---|---|---|---|
| L1 | 400 j (2 saisons) | 26 | 1 | OK |
| L2 | 300 j | 19 | 1 | OK |
| L3 | 300 j | 19 | 1 | OK |
| L4 | 300 j | 19 | 1 | OK |
| L5 | 300 j | 19 | 1 | OK |
| L6 | 400 j (2 saisons) | 26 | 1 | OK |

- Les 7 profils IA sont présents dans chaque univers (Bâtisseur, Formateur,
  Guerrier, Opportuniste, Riche, Spectacle, Économe) et leurs identités
  complètes sont lues par le moteur.

### INVARIANTS VÉRIFIÉS (tous les 6 jours + fin de saison)
- matchs joués avec score valide, aucun score négatif ;
- classements : joués = V+N+D, points = 3V+N, GF = GA par division ;
- calendrier sans doublon, coupe sans match nul, finale unique et jouée ;
- archives : 10 clubs/division, rangs 1→10 uniques ;
- montées/descentes (2 par division) réellement appliquées et primes versées ;
- classements remis à zéro + nouveau calendrier après clôture ;
- effectifs 5-30, numéros de maillot uniques, joueurs sans club orphelins ;
- prêts expirés rentrés, budgets > -50 M€, messagerie < 900 messages ;
- buts/match par division entre 1,8 et 8,0 ; pas plus de 35 % de 0-0 ;
- `error.log` : **0 octet**.

### SCÉNARIOS EXTRÊMES (`tests/audit_scenarios.py`, dans la suite)
- **Forfait** : club IA décimé (tous blessés) + aucun libre recrutable →
  défaite 0-3, classement adverse +3, rapport « forfait », effectif conservé ;
- **Deux forfaits consécutifs** : aucun crash ;
- **Changement de club en cours de saison** : ids uniques, une seule ligne de
  classement par club, effectif 5-30, puis match joué normalement (2-5) sans
  erreur.

### RÉSULTAT
- Aucune anomalie fonctionnelle détectée sur ces parcours.
- Un défaut du **harnais** d'audit a été corrigé (la boucle d'avance de
  calendrier s'arrêtait un jour avant la date du match).
- `tests/audit_gameplay.py` (long) et `tests/audit_scenarios.py` (court, intégré
  à `run_tests.py`) restent disponibles pour les prochaines sessions.
- Suite complète : **ALL OK** · `data/error.log` : **0 octet**.

### SCÉNARIOS PROFONDS (`tests/audit_deep.py`)
- **3 changements de club successifs** (L1, puis L5, puis L2) : ids uniques,
  un seul club id=1, effectif 11-13, classements non dupliqués, calendrier
  présent, et un match joué après chaque bascule.
- **Faillite forcée** (budget -4 M€, confiance 15) sur 160 jours :
  - alerte « Trésorerie négative » au 1er jour rouge ;
  - **Plan de redressement** au 60e jour rouge (joueur le plus cher mis en vente) ;
  - remontée temporaire au vert → compteur remis à zéro, puis nouvelle série ;
  - effectif jamais sous 8, aucune exception, `error.log` 0.

### BUG TROUVÉ ET CORRIGÉ — fil d'actualité saturé par le marché
- Constat : 84-87 % des news étaient « Marché des transferts » (listings,
  signatures de libres et transferts IA), ce qui masquait les news utiles
  (trésorerie, coupe, saison) et polluait les « faits marquants » du bilan.
- Correctif :
  - `ai_finance._market_news()` : **2 news marché par jour maximum**, partagées
    entre listings, signatures de libres et transferts ;
  - listings annoncés seulement au-dessus de 60 k€ ; transferts seulement
    au-dessus de 50 k€ ou si l'acheteur a une réputation ≥ 60 ;
  - le bilan de saison exclut les news « Marché des transferts » de ses
    faits marquants.
- Après correctif : **58 %** de news marché (au lieu de 87 %), news financières
  de nouveau visibles dans le fil.
- Suite complète : **ALL OK** · `data/error.log` : **0 octet**.

## Annexe GE - Chargement, Options et Aide (31/10/2026)

### BUG D'AFFICHAGE — « Saison SAISON 6 » dans Charger une partie
- Cause : le nom de sauvegarde était pré-rempli avec
  `"{club} - Saison {self.season_label...}"` où l'étiquette contenait déjà
  « SAISON 8 » → « Arbot Futsal - Saison SAISON 6 », figé pour toujours.
- Correctifs :
  - `save_display_name()` nettoie le nom affiché (retire « Saison SAISON N »,
    « - Saison N ») et garde un éventuel nom personnalisé ;
  - le pré-remplissage « Enregistrer sous » n'extrait plus que le **numéro**
    de saison (« Arbot Futsal - Saison 8 ») ;
  - le nom de club est utilisé comme repli si le nom nettoyé est vide.

### CHARGER UNE PARTIE — plus lisible
- Fenêtre 720×560, en-tête et sous-titre explicites, rappel « double-clic ».
- Chaque sauvegarde affiche **3 lignes** :
  1. nom nettoyé + pastille `PARTIE ACTIVE` ;
  2. `LIGUE 1 • SAISON 8 • J1 • 31/07/2033` ;
  3. `166 match(s) • 96V 20N 10D • sauv. 31/10 12:22`.
- Icônes d'écusson 40 px, liste sobre (fond transparent, sélection en carte).
- Plus de doublon de saison : la saison affichée est **celle du fichier**.

### OPTIONS — finition sobre
- Fond plat, cartes discrètes, bordures fines.
- Onglets **soulignés** (APPARENCE / MESSAGERIE / AIDE) au lieu de boîtes.
- En-tête plus compact, bouton principal plat, moins de dégradés.

### AIDE — 4 nouveaux sujets (26 → 30)
- **Mentalités : doser le risque** (attaque/défense/conversion, momentum,
  money-time).
- **Lire le terrain 2D** (pions, traînée, pilule d'action, popup but, vitesses
  1×-5×, pause/mi-temps).
- **Offres de club et messages SECRET** (news publique vs message confidentiel,
  accepter/refuser, conséquences).
- **Trésorerie négative : embargo et redressement** (alerte, plan à 60 jours,
  noyau de 8, retour au vert, primes).

### VALIDATION
- Captures : `data/apercu_charger_partie.png` (nom « Arbot Futsal », SAISON 8),
  `data/apercu_options.png`, `data/apercu_aide.png` (30 sujets).
- Suite complète : **ALL OK** · `data/error.log` : **0 octet**.

## Annexe GF - Effectif, fins de contrat et pré-contrats (31/10/2026)

### DEMANDE
- L'état de l'effectif n'est pas bien filtré / lisible.
- Aucune offre reçue pour les joueurs à 1 an de contrat.
- Pas de visibilité des pré-contrats signés dans Transferts.
- Les pré-contrats doivent être possibles au mercato d'hiver (6 mois restants).

### CORRECTIFS
- **Colonne ÉTAT** : elle n'affichait qu'un point de couleur (texte vide).
  Elle affiche maintenant `OK`, `FATIGUÉ`, `SUSPENDU`, `BLESSÉ` ou `MARCHÉ`,
  avec le point de couleur et une largeur dédiée (92 px).
- **Filtres Effectif** : `Tout l'effectif`, `Disponibles`, `Fatigués`, `Blessés`,
  `Suspendus`, `Sur le marché`, `Fin de contrat`. L'état d'un joueur listé est
  désormais `MARCHÉ` pour que le filtre et la colonne racontent la même chose.
- **Offres pour les fins de contrat** : `generate_transfer_interest()` cible
  aussi les joueurs du club à **1 an de contrat**, même non listés
  (~7 %/jour, 10 % en difficile), avec une indemnité décotée (55-85 % de la
  valeur). Le dossier `transfer_sale` est marqué `expiring: true` et le message
  explique « à un an de la fin de son contrat ».
- **Pré-contrats** :
  - la règle est explicite : possible pendant la **dernière année** de contrat,
    donc au **mercato d'hiver à 6 mois** (fenêtre 1-31 janvier) ;
  - bouton `PRÉ-CONTRAT • fin de contrat` ajouté au panneau du marché (visible
    seulement pour un joueur éligible) en plus de la fiche joueur ;
  - message d'erreur clarifié pour un contrat > 1 an.
- **Visibilité** : bandeau `ARRIVÉES PRÉVUES • N PRÉ-CONTRAT(S)` en haut de
  l'onglet OFFRES, avec une carte par joueur (poste, club quitté, salaire,
  durée). Il disparaît quand aucun pré-contrat n'est signé.

### VALIDATION
- Effectif : 22 joueurs, filtres Blessés/Suspendus/Marché/Fatigués renvoient
  chacun la bonne ligne, colonne ÉTAT lisible.
- Hiver (15/01/2027) : pré-contrat accepté pour un contrat à 1 an, refusé à 2 ans.
- OFFRES : bandeau visible avec 2 cartes.
- Offres IA : une offre « fin de contrat » générée sur l'échantillon.
- Captures : `data/apercu_effectif_etats.png`, `data/apercu_precontrats.png`.

### TESTS
- Nouvelle suite `tests/test_transfer_contracts.py` branchée dans
  `tests/run_tests.py` (états/filtres, pré-contrat hiver, bandeau, offre IA).
- `tests/test_visual_glitches.py` : colonnes de l'effectif de nouveau
  **Interactive** (redimensionnables) après l'ajout de la colonne ÉTAT.
- Suite complète : **ALL OK** · `data/error.log` : **0 octet**.

## Annexe GG - Objectifs du board explicites (31/10/2026)

### DEMANDE
- « Objectif du board, jeunes 0/2 : comment c'est calculé ? Il faut peut-être
  quelque chose de plus parlant. »

### CALCUL EXACT
- Compteur : `SELECT COUNT(*) FROM player WHERE club_id=1 AND age<=21
  AND season_matches>=3` (retirés/libres exclus par construction : ils ne sont
  plus `club_id=1`).
- Cible : `board_objective_youth` = **2** (3 en mode difficile).
- Un U21 avec 1 ou 2 matchs ne compte donc pas encore.

### CORRECTIFS UI
- Pastille renommée `JEUNES (U21) • 1/2` (au lieu de `JEUNES • 1/2`).
- Infobulle détaillée : règle, joueurs validés / cible, nombre d'U21 dans
  l'effectif, et le meilleur jeune avec son nombre de matchs.
- Sous-ligne visible sous les pastilles : `Saison N • ambition (top X) •
  jeunes U21 avec au moins 3 matchs : 1/2 • confiance 79 %`.
- Panneau passé en deux lignes (pastilles au-dessus, explication en dessous)
  pour rester lisible à 1000 px de large.
- Message d'avertissement du board reformulé avec la même règle.
- Aide : nouveau sujet `objectifs-board` (31 sujets au total) avec tableau
  pastille / mesure / condition de réussite et l'exemple `0/2`.

### VALIDATION
- Scénario : 1 U21 à 4 matchs + 1 U21 à 2 matchs → chip `⚠ JEUNES (U21) • 1/2`,
  infobulle `Validé(s) : 1/2 • U21 dans l'effectif : 4 • Meilleur : Héldon Brito
  (4 match(s))`, sous-ligne `jeunes U21 avec au moins 3 matchs : 1/2`.
- Capture : `data/apercu_dashboard_objectifs.png`
  (copiée dans `Documents\Projet par défaut\apercu_ui\`).
- Suite complète : **ALL OK** · `data/error.log` : **0 octet**.

## Annexe GH - Entraînement individuel et progression lisibles (02/11/2026)

### DEMANDE
- « Je veux encore plus de clarté / visibilité sur l'entraînement individuel et la
  progression, c'est encore trop usine à gaz. »

### RÈGLES RENDUES EXPLICITES
- Un joueur suit **un** attribut prioritaire :
  - `FOCUS` = ton choix, il pèse **×2,2** dans la séance en plus du plan collectif ;
  - `AUTO` = attribut prioritaire du poste (gardien → arrêts, défenseur → défense,
    ailier → technique, pivot → finition, universel → passe).
- `PLAFOND` = niveau ≈ potentiel : plus aucun point à gagner.
- « Points gagnés » = **somme des deltas positifs** depuis le début de saison
  (les baisses de fatigue/matchs ne viennent plus annuler les gains).

### CORRECTIFS UI
- **INDIVIDUEL**
  - légende pleine largeur : `FOCUS = ton choix (×2,2) • AUTO = poste • PLAFOND = potentiel atteint` ;
  - chips : `JOUEURS`, `FOCUS MANUELS`, `AUTO`, `PLAFOND`, `30 J : +N PTS` ;
  - filtre : `Tous / Focus manuels / Auto / Plafond atteint / Sans gain sur 30 j` ;
  - chaque carte dit sa marge (`reste 3,0 pt avant le plafond` ou `plafond atteint`),
    affiche un état `EN HAUSSE / EN ATTENTE / PLAFOND`, le total 30 jours et la date
    du dernier gain positif.
- **PROGRESSION**
  - une seule barre : **niveau actuel sur potentiel** (`12 / 16`) au lieu de deux barres ;
  - état `EN HAUSSE / STABLE / PLAFOND` par carte ;
  - ligne `INFO` : dernière progression + marge restante ;
  - pastilles `SAISON` = gains en vert ; les baisses sont regroupées dans une pastille
    neutre `↓ END −1` (infobulle qui explique la fatigue/les matchs) ;
  - filtre : `Tous / En progression / Plafond atteint / Sans évolution` ;
  - KPI `MEILLEURE MONTÉE` affiche `+N PTS`, le nom du joueur passe en infobulle.
- **Aide** : sujet `Entraînement et progression` réécrit (FOCUS/AUTO, plafond, lecture
  d'une carte, filtres, que faire quand un joueur stagne).

### BUGS CORRIGÉS AU PASSAGE
- `tot30` additionnait gains et pertes : un joueur à `TEC +1` et `END −1` affichait
  `0 PT` et disparaissait du filtre « En progression ». Il ne somme plus que les gains.
- `refresh_training_evolution` recevait l'entier de `currentIndexChanged` et le prenait
  pour une date → fenêtre de saison erronée au changement de filtre.
- « Dernier gain » se basait sur le dernier log, y compris une baisse : il ne considère
  plus que les deltas positifs.

### VALIDATION
- Cartes : marge/plafond visibles, états cohérents, infobulles détaillées.
- Filtres testés : manuels 1 / auto 11 ; progression 8/12, plafond 4, sans évolution 4.
- Captures : `data/apercu_entrainement_individuel.png`,
  `data/apercu_entrainement_progression.png`
  (copiées dans `Documents\Projet par défaut\apercu_ui\`).
- `tests/test_training_ui.py` étendu : filtres INDIVIDUEL et PROGRESSION, marge/plafond,
  pastille de plafond. Suite complète : **ALL OK** · `data/error.log` : **0 octet**.

## Annexe GI - Vérification des bugs potentiels (02/11/2026)

### DEMANDE
- « Vérifie les bugs potentiels. »

### BUGS RÉELS TROUVÉS ET CORRIGÉS
1. **Pré-contrats : cartes dupliquées.** `deleteLater()` n'est pas traité tant que
   la boucle d'événements n'a pas repris : trois rafraîchissements laissaient 8 fiches
   visibles au lieu de 2. Les widgets sont maintenant détachés (`setParent(None)`)
   avant suppression. Vérifié : 3 rafraîchissements → 2 fiches, aucun doublon.
2. **Compteurs INDIVIDUEL figés.** `_update_training_indiv_summary()` sortait
   immédiatement sur `training_indiv_summary`, un attribut qui n'existe pas : passer un
   joueur de AUTO à FOCUS ne mettait pas les chips à jour. Garde supprimée ; les
   compteurs se mettent à jour, et le total affiche le filtre (`3 / 12 JOUEURS`).
3. **Changement de focus sous filtre.** Un joueur passé de FOCUS à AUTO restait affiché
   dans le filtre « Auto (poste) ». Un rafraîchissement différé (`QTimer.singleShot`)
   réévalue le filtre après la sélection.
4. **Filtre vide muet.** Zone blanche sans explication. Message ajouté sur les deux
   onglets : « Aucun joueur ne correspond à ce filtre. ».
5. **Point d'état incohérent dans l'effectif.** Un joueur listé ET fatigué montrait un
   point orange alors que la colonne disait `MARCHÉ`. Le violet (marché) est prioritaire,
   sauf blessure/suspension (rouge).
6. **Offres « fin de contrat ».** Un club pouvait proposer une indemnité pour un joueur
   ayant déjà signé un pré-contrat ailleurs. Les joueurs `precontract_club>0` sont exclus.
7. **Bandeau pré-contrats > 6.** Seules 6 fiches étaient affichées sans le dire.
   Ajout de `+N autre(s) — voir la messagerie`.
8. **Infobulle board jeunes.** « Meilleur : X (0 match) » s'affichait alors que personne
   n'avait encore joué : messages adaptés (aucun U21 dans l'effectif / aucun U21 à 3 matchs).
9. **Toolbar entraînement illisible en fenêtre réduite (1000 px).** Titre tronqué,
   chips coupées, combo vide. Les deux toolbars passent en 3 lignes :
   titre + filtre + actions / légende / compteurs.
10. **Infobulle des baisses.** Elle parlait de matchs/fatigue ; la baisse d'`END` vient
    de l'inactivité (endurance −1). Formulation corrigée.

### SONDE DE RÉGRESSION (exécutée)
- Filtres vides, changements rapides de filtre (pas de doublon), focus sous filtre.
- 20 jours d'entraînement : `points gagnés = somme des deltas positifs`, pertes suivies
  à part, aucun total négatif.
- Pré-contrats : 3 rafraîchissements → aucune fiche en double.
- Board sans U21 : `0/2` et infobulle adaptée.
- `data/error.log` : 0 octet après la sonde.

### VALIDATION
- `tests/test_training_ui.py` : ajout de l'état vide (aucune carte, message visible,
  compteur `0 / N`).
- Suite complète : **ALL OK** · `data/error.log` : **0 octet**.

## Annexe GJ - Campagne de tests approfondis (02/11/2026)

### DEMANDE
- « Continue les tests. »

### NOUVEAUX TESTS
- **`tests/test_precontract_season.py`** (branché dans `run_tests.py`) :
  pré-contrats de bout en bout — signature au mercato d'hiver, clôture de saison,
  arrivée réelle au club, durée et salaire respectés, nettoyage des champs, historique,
  bandeau OFFRES vidé. Couvre aussi les deux annulations : joueur transféré dans un
  autre club, joueur qui prolonge. Vérifie qu'un joueur pré-signé n'est plus ciblé par
  les offres « fin de contrat ».
- **`tests/audit_training_soak.py`** (audit long, hors suite) : 60 jours de séances
  « Défense », moitié de l'effectif en focus manuel. Vérifie les plafonds de potentiel
  (aucun attribut ne dépasse, aucun gain au-delà du plafond), les bornes forme/moral,
  l'absence de blessures négatives, la cohérence KPI = gains positifs, et le ratio
  d'efficacité du focus (×2,2).

### RÉSULTATS
- **Pré-contrats** : 3 signés → 1 arrivée effective, 2 annulations correctes,
  contrat net 2 ans / 2 100 €, bandeau vidé, `error.log` 0.
- **Soak entraînement** : 60 jours, **21 gains** et 27 pertes (inactivité, par design),
  KPI `21 PTS` cohérent, ratio focus/auto **2,20**, plafonds respectés.
- **`audit_deep.py`** : 3 changements de club successifs + faillite forcée (budget
  −3,85 M€, 147 jours rouges, 56 % de news marché) → **ALL OK**.
- **`audit_gameplay.py`** : 6 divisions × 116 jours, 8 matchs manager par division.
  Aucune anomalie d'invariant (scores, classements, calendrier, coupe, effectifs,
  maillots, finances, messages, prêts, distributions de buts). Profils IA stables
  (7 profils représentés). `error.log` 0 à chaque division.

### NOTE TECHNIQUE
- Les seuls deltas de journal autres que ±1 pour le club sont les **+2 de
  l'entraînement des clubs IA** (`process_ai_training`) ; le soak vérifie donc ±1
  uniquement pour les joueurs du club 1.

### VALIDATION
- Suite complète (avec `test_precontract_season.py`) : **ALL OK** ·
  `data/error.log` : **0 octet**.

## Annexe GK - Processus de transfert et concurrence entre clubs (02/11/2026)

### DEMANDE
- « Process transfert : teste bien, et surtout la concurrence entre les clubs. »

### BUG RÉEL TROUVÉ ET CORRIGÉ
- **Offre concurrente non facturée.** Quand un club rival doublait une offre
  insuffisante (`bid < prix demandé`, 18 % de chance), le joueur changeait de club
  sans que l'acheteur soit débité ni le vendeur crédité : transfert gratuit et
  trésorerie incohérente. Le moteur débite désormais l'acheteur du prix demandé et
  crédite le vendeur (mêmes règles que le marché IA-IA).

### NOUVEAU TEST `tests/test_transfer_competition.py` (branché dans la suite)
1. **Rival plus offrant** : offre sous le prix demandé → un club rival souffle le
   joueur. Vérifie l'issue `rival` + club nommé, le joueur hors du club vendeur,
   **+prix pour le vendeur**, **−prix pour l'acheteur**, aucun autre budget modifié,
   aucune arrivée programmée chez le manager.
2. **Payer le prix demandé sécurise** : avec `bid ≥ seller_ask`, aucun rival,
   la cible reste au vendeur et l'offre est acceptée.
3. **Marché IA-IA** (5 mercredis) : au plus 4 transferts par journée, **somme des
   budgets conservée**, club du manager jamais touché.
4. **Vente d'un joueur du club** : un départ programmé classe les offres
   concurrentes (`already_sold`), sort le joueur de la liste, une seule vente.
5. **Joueur libre signé ailleurs** : dossier `SIGNÉ AILLEURS` avec le nom du club,
   aucune signature chez le manager.

### VALIDATION
- Exécution : 5/5 scénarios OK, `data/error.log` 0.
- Suite complète : **ALL OK** · `data/error.log` : **0 octet**.

## Annexe GL - Réalisme des tactiques (02/11/2026)

### DEMANDE
- « Teste maintenant les différentes tactiques pour le réalisme. »

### MÉTHODE : `tests/audit_tactics_realism.py`
- **A. Facteurs déterministes** (`_attack_score` / `_defense_score`) : chaque plan
  (5 presets, 6 formations, 4 mentalités, rythme, pressing) doit avoir un effet réel,
  ordonné et borné (0,80–1,25).
- **B. Matchs simulés** : 400 matchs par preset, 300 par formation/rythme/pressing,
  domicile et extérieur alternés. Contrôle des buts/match, victoires/nuls/défaites,
  possession, tirs/cadrés/buts, cartons et rouges.

### CORRECTIFS DE RÉALISME
1. **Possession** : le style ne contrôlait que ~51,5 % du ballon.
   `STYLE.possession.poss` 1,10 → **1,28** (≈53 % en match, 4-0 + largeur + ailes).
2. **Powerplay sans risque** dans le moteur IA : le gardien volant donnait +3 %
   d'attaque sans exposer la cage. L'adversaire reçoit désormais **+8,5 % d'attaque**
   (but à découvert) — total 5,20 buts/match contre 4,60 en équilibré.
3. **1-2-1 et 1-1-2 sans effet** (purement cosmétiques) : ajout de modificateurs
   d'attaque (+1,2 % / +2,5 %) dans le moteur IA **et** le moteur live du manager.
4. **Pressing haut trop propre** : cartons +0,07 seulement. Multiplicateur de faute
   1,12 → **1,28** : 3,27 cartons/match contre 2,64 en équilibré.
5. **Mentalité prudente strictement supérieure** : son bonus de conversion (+5 %)
   compensait sa baisse d'attaque. Conversion remise à 1,00 et offensive 1,075 → 1,085 :
   l'offensive marque et encaisse plus, la prudente défend mieux.

### MESURES APRÈS CORRECTIFS
| Plan | Buts | Total | V / N / D | Possession |
|---|---|---|---|---|
| Équilibré (miroir) | 2,25–2,34 | 4,60 | 40,5 / 15,5 / 44,0 | 50 % |
| Possession | 2,60–2,18 | 4,78 | 47,2 / 20,2 / 32,5 | 52,6 % |
| Contre | 2,19–2,27 | 4,46 | 38,0 / 19,8 / 42,2 | 48,9 % |
| Pressing | 2,50–2,56 | 5,05 | 41,8 / 15,2 / 43,0 | 50,2 % |
| Powerplay | 2,57–2,63 | 5,20 | 41,8 / 16,5 / 41,8 | 50,2 % |

- Formations : 4,60 à 4,77 buts/match, victoires 41,7–43,3 % — aucune cassée.
- Tirs ≥ cadrés ≥ buts sur chaque match ; rouges ≤ 0,4/match.
- Aucune tactique ne dépasse 60 % de victoires.

### VALIDATION
- `audit_tactics_realism.py` : **ALL OK**.
- `test_match_engine_v2.py` : **ALL OK** (4,64 buts/match, domicile 45,5 %).
- `test_balance_soak.py` : 300 jours, 599 matchs, **4,69 buts/match**, 0 erreur.
- Suite complète : **ALL OK** · `data/error.log` : **0 octet**.

## Annexe GM - Filière de formation des joueurs (02/11/2026)

### DEMANDE
- « Teste le process de formation des joueurs. »

### NOUVEAU TEST `tests/test_academy_pipeline.py` (branché dans la suite)
1. **Promotion annuelle** : 1 à 3 jeunes par saison, âges 15-17, postes variés,
   contrat 3 ans, salaire > 0, forme 85-100, moral 62-84, attributs ≤ potentiel×5,
   numéros de maillot uniques, historique `formation`, news de promotion.
2. **Campus fermé** : aucune promotion générée.
3. **Investissement de saison** (50 000 €) : note +8, mentionnée dans la news,
   puis consommée (une seule génération).
4. **Entraînement quotidien** : 60 séances à campus fermé puis 60 à campus ouvert
   (niveau 8). Le U18 progresse plus que le senior, et plus vite campus ouvert.
5. **Développement hebdomadaire** (`process_player_development`) : 30 semaines.
   Le jeune monte de niveau, le vétéran de 34 ans régresse physiquement,
   aucun attribut ne dépasse le potentiel.

### RÉSULTATS MESURÉS
- Promotion : 2 jeunes (17 ans, potentiels 15 et 18/20), campus fermé → 0.
- Investissement : « investissement +8 » appliqué puis consommé.
- Quotidien : U18 **+6** (fermé) → **+8** (ouvert) ; senior **+3** → **+1**.
- Hebdo : U18 **7,0 → 12,0/20** (+159 points d'attributs en 30 semaines, rythme
  conforme à la calibration « ~1 note / 6-8 semaines » pour un centre élite) ;
  vétéran **22 régressions**, endurance **60 → 49**.
- Plafonds de potentiel respectés partout, `error.log` 0.

### STABILISATION AU PASSAGE
- `test_precontract_season.py` : les cibles sont désormais **âgées de moins de
  30 ans** (`retired=0`). Un pré-contrat signé avec un joueur qui prend sa retraite
  à la clôture faisait varier l'effectif de 0 au lieu de +1 (test instable, pas un
  bug produit : le joueur arrivait puis prenait sa retraite le même jour).
  Vérifié 3 exécutions consécutives : ALL OK.

### VALIDATION
- Suite complète (avec `test_academy_pipeline.py`) : **ALL OK** ·
  `data/error.log` : **0 octet**.

## Annexe GN - Renouvellement de contrat, priorité aux jeunes (02/11/2026)

### DEMANDE
- « Revois le process de renouvellement de contrat des joueurs, surtout les jeunes. »

### PROBLÈMES TROUVÉS
1. **Demande de l'agent incohérente.** Pour une prolongation, l'agent réclamait
   `salaire + 250 €` ou `+6 %` (sans tenir compte du potentiel), alors que les
   pré-contrats utilisaient le **salaire juste** (`player_salary_demand`).
   Un jeune à fort potentiel sous-payé était donc prolongé trop facilement, et
   l'offre conseillée dans le dialogue ne correspondait pas à la réponse.
2. **Dialogue aveugle.** La proposition démarrait à `salaire actuel +8 %` au
   hasard, sans indiquer l'attente de l'agent.
3. **Jeunes non signalés.** À la clôture, seuls les joueurs ayant peu joué
   (55 % de chance) recevaient l'alerte « hésite à rester ». Un U21 titulaire
   en fin de contrat partait libre **sans aucun avertissement**.
4. **Visibilité faible.** Aucun filtre dédié aux jeunes à prolonger.

### CORRECTIFS
- **Demande unifiée** : `player_salary_demand` (niveau, âge, potentiel, division)
  avec plancher **+2 %** du salaire actuel, arrondi sans jamais passer sous le
  salaire actuel. Les pré-contrats, prolongations et l'UI parlent le même langage.
- **Dialogue de prolongation** : proposition pré-remplie à l'attente de l'agent,
  avec la ligne « Attente de l'agent : environ X € / mois (actuel : Y) ».
- **Alerte dédiée « Jeunes à prolonger »** à chaque clôture : **tous** les U21 en
  fin de contrat sont listés (nom + âge), même s'ils ont joué, avec consigne de
  prolonger avant la clôture.
- **Effectif** : nouveau filtre `Jeunes à prolonger` (U21, ≤1 an, hors prêt) et
  infobulle du KPI contrats : « N contrats à 1 an ou moins, dont X jeunes U21 ».

### NOUVEAU TEST `tests/test_contract_renewal.py`
1. Jeune 17 ans, 1 200 €, 1 an : offre à l'attente (**1 224 €**) sur 3 ans →
   acceptée, contrat 3 ans, salaire 1 224 €, moral conservé.
2. Offre trop basse → contre-offre au bon montant (**3 060 €**), puis acceptation.
3. Filtre `Jeunes à prolonger` : seuls les U21 en fin de contrat ressortent
   (2 lignes), KPI « 5 contrats, dont 2 jeunes U21 ».
4. Clôture : message « Jeunes à prolonger » listant **les 3 U21**, y compris
   celui qui a joué 9 matchs.

### STABILISATION
- `test_academy_pipeline.py` : le volet quotidien utilise 200 séances et vérifie
  le **facteur académie déterministe** (0,0405 → 0,0810 par séance) au lieu de
  comparer deux phases bruitées.

### VALIDATION
- Suite complète : **ALL OK** · `data/error.log` : **0 octet**.

## Annexe GO - Audit de la messagerie (02/11/2026)

### DEMANDE
- « Audit de la messagerie : la plus propre et la plus immersive possible. »

### PROBLÈMES TROUVÉS
1. **`transfer_departure` sans dossier** : les messages de vente programmée tombaient
   dans « Club & alertes » au lieu de « Dossiers ».
2. **Dossiers clos présentés comme à traiter** : un accord accepté, refusé ou un
   joueur signé ailleurs restait compté dans « À traiter » et affichait encore
   ACCEPTER / REFUSER / SIGNER.
3. **Pastilles d'état muettes** : un dossier clos s'affichait « LU » ou « À TRAITER »,
   sans dire son issue.
4. **Échéance affichée sur un dossier clos**.
5. **Boutons fantômes** : les boutons d'action précédents restaient visibles un
   instant au changement de message (`deleteLater` non détaché).
6. **Expéditeurs génériques** : rapports mensuels et arrivées signés « Direction
   sportive », négociations de contrat sans nom d'agent.
7. **Layout étroit** : sous 1180 px, le volet de lecture était écrasé (400/640).

### CORRECTIFS
- `transfer_departure` ajouté au dossier **Dossiers**.
- **`_message_is_actionable()`** : un dossier n'est actionnable que si `status=ready`
  ET sans issue terminale (accepté, refusé, rival, indisponible, déjà vendu, clos).
  Le filtre « À traiter », le compteur et les boutons utilisent cette règle.
- Pastilles d'issue : **ACCEPTÉ** (vert), **SIGNÉ AILLEURS** (rouge, club nommé),
  **REFUSÉ** / **DOSSIER CLOS** (gris), **CONTRE-OFFRE** (ambre).
- Boutons adaptés : `ACCEPTER LE PRIX` (transfert après contre-offre),
  `ACCEPTER LA CONTRE-OFFRE` (contrat).
- Échéance masquée pour les dossiers clos.
- Boutons d'action détachés avant suppression (plus de fantômes).
- Expéditeurs : `Cellule de recrutement` pour le digest et les arrivées ;
  `Agent de <joueur>` + `agents@<joueur>.fm` pour les négociations.
- Layout : split 50/50 sous 1180 px, 400/640 au-dessus.
- Infobulle du dossier Scouting : les fiches détaillées sont dans Transferts → Scouting.
- **Badge de non-lus** : il respecte désormais les familles masquées dans les options
  (un match masqué ne fait plus clignoter le badge) et reste cohérent avec la liste.
- **Pas de lecture automatique** : ouvrir la messagerie ou changer de filtre ne
  marque plus le premier message comme lu. Le volet affiche « Sélectionne un message »
  jusqu'au clic. 	est_message_badges.py a été adapté (badge 2 après ouverture,
  1 après lecture réelle).

### NOUVEAU TEST `tests/test_messaging_audit.py` (branché dans la suite)
- **23 types** de messages répartis sur **8 familles** : chacun tombe dans le bon dossier.
- Expéditeur crédible (nom + adresse + initiales) pour chaque type.
- Offre fraîche actionnable ; acceptée / rivale / refusée non.
- Filtre « À traiter » : 2 dossiers, les clos exclus ; boutons ACCEPTER/REFUSER présents.
- Dossiers clos : pastilles ACCEPTÉ / SIGNÉ AILLEURS, aucun bouton d'action.
- Contre-offre : pastille CONTRE-OFFRE + bouton ACCEPTER LA CONTRE-OFFRE.
- Dossiers : 13 messages ; recherche « Diomandé » → 4 résultats.
- Badge non lus = compteur de la liste = valeur du badge.
- Aucun message vide.

### CAPTURES
- `data/apercu_messagerie.png` (boîte de réception, 1600×1000).
- `data/apercu_messagerie_dossier.png` (dossier SIGNÉ AILLEURS).
- `data/apercu_messagerie_1000.png` (layout compact).

### VALIDATION
- Suite complète (avec `test_messaging_audit.py`) : **ALL OK** ·
  `data/error.log` : **0 octet**.

## Annexe GP - Audit du calendrier (02/11/2026)

### DEMANDE
- « Audit du calendrier. »

### PROBLÈMES TROUVÉS
1. **Coupe reléguée en fin de liste** : la liste était triée par `matchday`, donc le
   tour de coupe (matchday 101) apparaissait après la J18 alors qu'il se joue en
   novembre.
2. **Carte coupe illisible** : elle affichait `J101` (au lieu d'une étiquette coupe).
3. **Vue « autre division » mélangée** : la liste contenait les 90 matchs de la
   division choisie **et** les 19 matchs du club (90 L1 + 19 L2). Le filtre
   « prochains / résultats » y était ignoré et les en-têtes affichaient
   `JOURNÉE 101` pour la coupe.
4. **« RAPPORT RÉCENT » pointait le plus ancien** (liste `matches` en ordre
   chronologique, `next()` prenait la première entrée).
5. **Sous-titre trompeur** : « Classement en direct » sur la page calendrier.
6. **Titre cassé** : « CALENDRIER DE LA SAISON » se coupait sur trois lignes.
7. **UnboundLocalError** : `friendly_fixtures` défini dans le bloc « division du
   club » mais utilisé par l'onglet AMICAUX hors de ce bloc.

### CORRECTIFS
- Tri de la liste par **date** (matchday en second) : coupe insérée à sa date.
- Carte coupe : étiquette **🏆 / C1 / COUPE**, date préfixée « COUPE ».
- Vue autre division : **championnat seul**, filtre prochains/résultats appliqué,
  plus de `JOURNÉE 101`.
- `latest_match_report` : parcours **reversed(matches)**.
- Sous-titre : « JOURNÉES, COUPE ET AMICAUX • Ligue X ».
- Titre sur une ligne (`wordWrap=False`).
- `friendly_fixtures` défini avant le bloc conditionnel.

### NOUVEAU TEST `tests/test_calendar_audit.py` (branché dans la suite)
1. Championnat : 6 × 90 matchs, 18 journées, 5 matchs / 10 clubs, paires aller-retour,
   9 domicile / 9 extérieur, trêve hivernale, une seule rencontre par club et par date.
2. Coupe : 28 matchs, 56 clubs distincts, mercredis, repos ≥ 3 j avec le championnat
   du club.
3. Affichage : lignes chronologiques, carte coupe étiquetée COUPE.
4. Filtres : résultats 0 / prochains 19 / tout 19.
5. Autre division : 0 résultat, 90 à venir (filtre appliqué).
6. Amicaux : date occupée et veille refusées, 5 programmés, 6e bloqué par le quota.
7. Résultat joué : score affiché, filtre RÉSULTATS = 1.
8. Nouvelle saison : 540 matchs + 28 coupe régénérés, ancienne saison purgée,
   club 9/9.

### CAPTURES
- `data/apercu_calendrier.png` (calendrier 1600×1000).
- `data/apercu_calendrier_resultats.png` (filtre résultats vide).

### VALIDATION
- `test_calendar_audit.py` : **ALL OK** · `data/error.log` : **0 octet**.
- Suite complète : **ALL OK** · `data/error.log` : **0 octet**.

## Annexe GQ - Audit de la Direction sportive (02/11/2026)

### DEMANDE
- « Audit de la page Direction sportive : la plus classe possible, c'est la page de
  démarrage, le tableau de bord du club. »

### AMÉLIORATIONS
1. **Bandeau FORME** : les 5 derniers résultats de championnat en pastilles
   `V` / `N` / `D` (vert / ambre / rouge), avec le bilan (`1V 1N 1D`) et une
   infobulle par match (journée, date, score). Ordre chronologique, le plus récent
   à droite.
2. **Prochain match** : pastille `DOMICILE` / `EXTÉRIEUR` + compte à rebours
   (`J−6`, `AUJOURD'HUI`), masquée en fin de saison.
3. **OBJECTIFS DU BOARD** : légende **CONFIANCE** au-dessus du pourcentage (le
   `85%` flottait sans libellé) ; sous-ligne simplifiée, plus de doublon
   « maintien / top 8 / confiance ».
4. **ACTUALITÉS** : flux compact de 5 entrées (date, titre, corps tronqué),
   séparateurs supprimés, barre de défilement discrète.
5. **PALMARÈS vide** : état centré avec trophée et phrase d'accroche
   (« Le premier trophée écrira la première ligne d'or »).
6. **JOUEURS EN VUE** : valeur mise en avant à droite (chiffre doré), nom en
   dessous ; pour un joueur non observé, `•••` + infobulle expliquant le scouting.
7. **Accroche** : « au programme : … » au lieu de « à la une aujourd'hui » (le
   prochain match n'est pas forcément le jour même).

### NOUVEAU TEST `tests/test_dashboard_audit.py` (branché dans la suite)
1. Aucun match : 5 cases `—`, résumé « aucun match ».
2. Trois matchs V/N/D : pastilles dans l'ordre, `1V 1N 1D`.
3. Prochain match : pastille lieu + `J−…`, journée `J04`.
4. Board : légende CONFIANCE + valeur en `%`.
5. Actualités : titre affiché une fois, flux compact.

### VALIDATION
- `test_dashboard_fit.py` : page 996×786 dans 996×786, prochain match 160 px.
- `test_dashboard_honours.py` : palmarès 10 titres, scroll 166.
- Captures : `data/apercu_direction.png`, `data/apercu_direction_1280.png`.
- Suite complète : **ALL OK** · `data/error.log` : **0 octet**.

## Annexe GR - Audit de la page Compétitions (02/11/2026)

### DEMANDE
- « Audit de la page Compétitions. »

### PROBLÈMES TROUVÉS ET CORRIGÉS
1. **Forme du classement polluée par la coupe** : elle était calculée sur tous les
   matchs hors amicaux, et affichée du plus récent au plus ancien. Désormais
   **championnat uniquement**, du plus ancien au plus récent (comme le tableau de bord).
2. **Noms décalés dans le classement** : les lignes avec flèche de promotion ou
   couronne avaient leur nom décalé de 16 px. Un emplacement fixe de 16 px est
   réservé sur toutes les lignes.
3. **Historique / Palmarès sur Ligue 1 par défaut** : les sélecteurs de ces onglets
   ignorent la division du club. Ils s'ouvrent maintenant sur la **Ligue du club**
   et suivent le sélecteur global (MON CLUB / Ligue 1..6).
4. **Onglet « CLASSEMENTS FINAUX »** : pour la saison en cours il affiche le
   classement live. Renommé **« CLASSEMENTS »**, l'en-tête précise « CLASSEMENT LIVE ».
5. **KPI « SAISONS 0 »** ambigu : renommé **« SAISONS ARCHIVÉES »**.
6. **Statuts live vides** : la colonne STATUT affiche maintenant
   **EN TÊTE / PROMOTION / RELÉGATION** selon la position (au lieu de « — »).
7. **Repères de coupe tronqués** : « PETIT POUCET » et « Survivants par division »
   étaient coupés (hauteur insuffisante). Hauteurs minimales ajoutées ; le texte
   complet s'affiche.
8. **Palmarès vide** : état centré avec trophée et message explicite.

### NOUVEAU TEST `tests/test_competitions_audit.py` (branché dans la suite)
1. Classement : 10 clubs, MJ = V+N+D, points = 3V+N, GF = GA.
2. Liste : zones promotion/relégation, club du manager surligné, noms alignés.
3. Forme : 5 derniers résultats de championnat, coupe exclue.
4. Sélecteurs : historique/palmarès synchronisés avec la division globale.
5. Historique : statuts EN TÊTE / PROMOTION / RELÉGATION.
6. Palmarès : Ligue 2 par défaut, état vide lisible.
7. Coupe : 28 matchs, repères non tronqués (hauteur 56 px).

### CAPTURES
- `data/apercu_competitions_championnat.png`, `_coupe.png`, `_stats.png`,
  `_historique.png`, `_palmares.png`.

### VALIDATION
- `test_competitions_audit.py` : **ALL OK** · `data/error.log` : **0 octet**.
- Suite complète : **ALL OK** · `data/error.log` : **0 octet**.

## Annexe GS - Audit des finances (02/11/2026)

### DEMANDE
- « Audit des finances. »

### VÉRIFICATIONS COMPTABLES
- **Budget = somme des transactions** : exact (1 950 000 € à la création, 0 € d'écart).
- **Paie mensuelle** : le débit du 1er du mois est exactement la masse salariale
  (45 500 €) et la baisse de trésorerie correspond à la transaction.
- **Prêt** : `coût total = échéance × semaines` (104 000 € pour 100 000 € sur 52
  semaines), frais de dossier 1 % (1 000 €), capacité et taux cohérents.
- **Sponsors** : 10 partenaires, session disponible, bouton actif.

### PROBLÈMES TROUVÉS ET CORRIGÉS
1. **Santé « TENDU » alors que le club gagne de l'argent** : un net positif
   (+49 926 €/mois) était étiqueté « TENDU » à cause du seuil 50 000 €.
   Libellés revus : **SAINE** (≥ 50 000 €/mois), **ÉQUILIBRÉE** (≥ 0),
   **TRÉSORERIE CRITIQUE** (déficit et réserve < 3 mois), **DÉFICIT**.
2. **Prêt : « intérêts » incohérents avec le taux** (3,16 % affiché mais 4 000 €
   d'intérêts). L'écart vient de l'échéance arrondie à 100 € supérieurs ;
   le résumé parle maintenant de **coût du crédit (échéance arrondie)**.
3. **Historique des emprunts vide** : tableau vide massif. État vide centré
   (« Aucun emprunt souscrit — la banque suit le club »), tableau masqué.
4. **Onglet Sponsors** : grand vide sous le réseau. Ajout d'un **parcours guidé
   en 3 étapes** : lancer la session → comparer les offres → signer le contrat,
   puis d'un panneau **HISTORIQUE DES ACCORDS** (date, opération, montant) avec
   état vide centré et ligne créée dès la signature d'un partenaire.

### NOUVEAU TEST `tests/test_finances_audit.py` (branché dans la suite)
1. Budget = transactions à la création.
2. Paie mensuelle = masse salariale, budget après paie = transactions.
3. Simulateur de prêt : taux, échéance, total, frais, état vide de l'historique.
4. Santé financière : jamais « TENDU » sur un net positif.
5. KPI entrées/sorties/solde affichés.
6. Sponsors : session disponible, 10 partenaires, parcours en 3 étapes,
   historique vide au départ.
7. Signature d'un sponsor : prime créditée, transaction `Sponsoring`,
   budget = transactions, une ligne dans l'historique.

### CAPTURES
- `data/apercu_finances_vue.png`, `_exploitation.png`, `_pret.png`,
  `_sponsors.png`, `_sponsors_accord.png` (accord signé).

### VALIDATION
- `test_finances_audit.py` : **ALL OK** · `data/error.log` : **0 octet**.
- Suite complète : **ALL OK** · `data/error.log` : **0 octet**.

## Annexe GT - Audit du staff et de son utilité (02/11/2026)

### DEMANDE
- « audit des staffs et de leur utilité »

### VÉRIFICATIONS
- 8 postes : recruteur, kiné, préparateur physique, comptable, directeur
  sportif, adjoint, responsable marketing, architecte.
- Chaque dépense (embauche, formation, protocole kiné) crée une transaction :
  budget = somme des transactions (vérifié à chaque étape).
- Effets mesurés un par un : missions de scouting, soin, progression,
  placements/paie, shortlist, forme, réputation, chantiers.

### PROBLÈMES TROUVÉS ET CORRIGÉS
1. **Comptable = piège économique.** Sa remise ne portait que sur la paie du
   staff (100 € au niveau 1) pour un salaire de 2 200 €/mois : jamais rentable.
   Il **place désormais la trésorerie** (0,15 %/niveau et par mois du solde
   positif, plafond 12 000 €). La carte affiche le gain réel en euros.
2. **Recruteur : formation bradée.** « FORMER » coûtait 3 200 €/14 j pour +1
   niveau, alors que la mise à niveau officielle du scouting coûte 30 000 €.
   Le bouton devient **AMÉLIORER** au tarif officiel (immédiat) ; `train_staff`
   redirige vers ce tarif.
3. **Architecte : places de chantier fantômes.** `facility_project_capacity()`
   sans argument fermait sa connexion puis l'utilisait : elle renvoyait
   toujours 1 place. Corrigé. Le libellé annonçait « l chantier(s) » au lieu de
   **1 + l** (3 → 4 chantiers).
4. **Directeur sportif quasi inutile** (+2 connaissance/lundi sur une seule
   cible, quand une mission standard donne 32+ points en 4 jours). Il traite
   maintenant **2 cibles par niveau** (+2 connaissance/niveau sur chacune).
5. **Libellés faux.** Kiné « bonus +0 % » → « pts de réussite » ; adjoint
   « +l » → « en plus des +3 quotidiens » ; préparateur « risque −9 % » →
   « moins de blessures » (+ infobulle avec les risques exacts) ; « Kine » et
   « Prepareur » accentués.
6. **Effet du niveau suivant calculé mais invisible.** Ajout de la ligne
   « → niv. N : … » sur chaque carte : on voit ce que la formation apporte.
7. **Licenciement sans confirmation.** Désormais confirmation explicite :
   niveau, formation et effet sont perdus, aucune indemnité.
8. **Masse salariale nette non expliquée.** L'en-tête affiche
   « REMISE COMPTABLE −X € » (la somme des salaires des cartes est brute) et un
   bandeau « Embaucher / Former / Effets réels » guide les postes vacants.

### NOUVEAU TEST `tests/test_staff_audit.py` (branché dans la suite)
1. 8 cartes, effet annoncé et tarif sur chacune.
2. Comptable : embauche payée, placement + remise > salaire.
3. Paie : salaires remisés + placements crédités, budget = transactions.
4. Adjoint +2 forme/jour, marketing +2 réputation le lundi, directeur sportif
   +8 connaissance sur 3 cibles.
5. Recruteur : mise à niveau à 30 000 € (aucune formation à 3 200 €).
6. Architecte : devis et délai réduits, 4 places de chantier au niveau 3.
7. Préparateur : progression ×1,10 (niv. 1) et ×1,50 (niv. 5), planification.
8. Kiné : blessure 10 → 9 j, forme 60 → 66, protocole −2 100 €.
9. Paie complète : remise comptable appliquée, budget = transactions.

### CAPTURES
- `data/apercu_staff_vacant.png` (0/8), `data/apercu_staff_equipe.png` (8/8).

### VALIDATION
- `test_staff_audit.py` : **ALL OK** · `data/error.log` : **0 octet**.
- Suite complète : **ALL OK** · `data/error.log` : **0 octet**.

## Annexe GU - Audit de la page Tactiques : rendu (02/11/2026)

### DEMANDE
- « audit de la page tactique le meilleur rendu possible »

### PROBLÈMES DE RENDU TROUVÉS ET CORRIGÉS
1. **Débordement horizontal de la barre de réglages.** Les listes déroulantes
   imposaient 379 + 249 + 171 px (largeur du plus long libellé) et la barre
   mesurait 1513 px pour une page de 1245 : les boutons de droite étaient
   rognés. Passage en `AdjustToMinimumContentsLengthWithIcon`, boutons empilés
   dans une seule colonne et lecture sur 4 colonnes : **960 px**.
2. **« DÉFENSE ◀ • ATTAQUE ▶ » invisible** : la politique `Ignored` réduisait
   le libellé à 0 px. Politique `Preferred` : le sens de jeu s'affiche.
3. **Bandeau de lecture du plan tronqué** sous le terrain
   (« Récupération : Médian … »). Il devient un bandeau **pleine largeur
   au-dessus du terrain**, avec deux lignes (phase + valeur) et des textes
   reformulés : « largeur équilibrée », « pressing médian », etc.
4. **Traits pointillés parasites** en haut et en bas du terrain (artefacts de
   peinture) : supprimés.
5. **Tuiles de joueurs tronquées** : le maillot occupait trop de largeur et
   l'espace du statut était réservé même sans statut. Maillot adaptatif et
   réservation corrigée → « GARDIEN », noms complets et notes lisibles même à
   1366 px.
6. **« VIDER LE TERRAIN » rogné** en bas du banc. Les deux actions passent
   côte à côte (« COMPOSER AUTO » + « VIDER ») : plus de rognage.
7. **Aperçu du banc illisible** (6 attributs + salaire sur une ligne) :
   4 attributs clés affichés, le reste (END, MOR, salaire) dans l'infobulle.
8. **Responsive** : le seuil de bascule (1080 px) mettait le banc hors écran à
   1366. Seuil ramené à **920 px**, partage terrain/banc 68/32 avec banc
   ≥ 400 px : terrain et banc côte à côte à 1366, colonne seulement sous 920.
   La description du preset est masquée sous 900 px (elle ne tenait pas).
9. **État vide** : message explicite dans le banc (« Tous les joueurs
   disponibles sont sur le terrain » / « Aucun joueur ne correspond »).
10. **Lecture plus parlante** : compatibilité/risque/contrôle colorés avec
    séparateurs, légende des notes sur le terrain (● ≥ 15 / ● < 15), bouton
    « RÉGLAGES + / − » et « CONSIGNES & CPA ».

### NOUVEAU TEST `tests/test_tactics_render_audit.py` (branché dans la suite)
1. Barre de réglages ≤ 1050 px, largeur = page.
2. Bandeau de phases pleine largeur, au-dessus du terrain, aucun texte tronqué.
3. Lecture colorée + séparateurs.
4. Sens de jeu visible, 5 tuiles ≥ 130 px, terrain 2:1.
5. Banc : actions visibles et non rognées, aperçu complet en infobulle.
6. État vide propre (0/5, 12 joueurs au banc).
7. Responsive : colonne à 1000 px, côte à côte à 1600 px.
8. Enregistrement : retour « PLAN ENREGISTRÉ » lisible.

### CAPTURES
- `data/apercu_tactiques_1600.png` (référence),
  `_1366.png` (portable), `_avance.png` (réglages fins),
  `_vide.png` (état vide), `_1000.png` (colonne).

### VALIDATION
- `test_tactics_render_audit.py` : **ALL OK** · `data/error.log` : **0 octet**.
- Suite complète : **ALL OK** · `data/error.log` : **0 octet**.

## Annexe GV - Bug coupe : étiquette J<n> et calendrier (02/11/2026)

### DEMANDE
- « Il m'affiche J13 dans la messagerie alors que c'était un match de coupe,
  le calendrier aussi est bizarre, il n'affiche plus nos propres matchs. »

### DIAGNOSTIC
1. **Titre du rapport de match** : construit avec `career.matchday` (journée de
   championnat) même pour une coupe. Le quart de finale du 08/02/2034 (tour 4)
   s'appelait donc « J17 », et le 16e du 07/12/2033 « J13 ».
2. **Lien rapport/coupe perdu** : un match de coupe est stocké avec
   `match_record.matchday=0` (hors championnat). Le calendrier refusait donc
   explicitement le rapport détaillé de coupe (`record=None`) et affichait le
   rapport simplifié de l'IA, sans lien « RAPPORT ↗ ».
3. **Bouton « dernier rapport »** : il parcourait les matchs à l'envers et
   ouvrait le plus ANCIEN (J1), en ignorant la coupe.
4. **Calendrier perçu vide** : filtre par défaut « PROCHAINS MATCHS » — en fin
   de saison il ne reste qu'une ligne. De plus la requête chargeait les
   fixtures de toutes les saisons sans filtre.
5. **Libellés de coupe** : détail « COUPE R1 » au lieu du vrai tour
   (32es de finale) et trophée affiché dès le premier tour.

### CORRECTIONS
- Titre et corps du message : `_match_tag` (« COUPE R4 », « AMICAL », « J17 »).
  `action_data` contient désormais `fixture_type`, `matchday` (101+ pour la
  coupe) et `fixture_id`.
- Calendrier : les rapports sont reliés par **(date, domicile, extérieur)**,
  ce qui couvre la coupe. Les cartes de coupe affichent « RAPPORT ↗ » et le
  panneau de droite ouvre le **rapport complet archivé**.
- Bouton « dernier rapport » : dernier match officiel par `id` (coupe incluse),
  libellé « RAPPORT • COUPE ↗ » ou « RAPPORT • J17 ↗ ».
- Filtre par défaut **TOUT**, fixtures limitées à la **saison en cours**.
- Détail de coupe : nom réel du tour (« 32es DE FINALE », « QUARTS DE FINALE »…),
  étiquette de carte C1…C6 (plus de trophée au 1er tour).
- **Réparation des anciennes sauvegardes** : `repair_match_report_labels()`
  corrige les messages « Rapport de match • J<n> » créés un jour de coupe
  (titre + « journée n » dans le corps), y compris quand les fixtures de la
  saison ont été purgées (repli sur `match_record`). Vérifié sur une copie de
  la sauvegarde : J13 → COUPE R2, J17 → COUPE R4.

### NOUVEAU TEST `tests/test_cup_report_links.py` (branché dans la suite)
1. Un vrai match de coupe joué produit « Rapport de match • COUPE R1 »,
   `action_data` cohérent, corps sans « journée ».
2. Calendrier en TOUT : carte coupe « C1 » + « RAPPORT ↗ ».
3. Détail : « 32es DE FINALE » et rapport complet (pas le simplifié).
4. « Dernier rapport » ouvre l'enregistrement de coupe.
5. Réparation d'un ancien « J5 » de coupe, sans toucher au « J6 » de championnat.

### CAPTURES
- `data/apercu_calendrier_fix.png` (calendrier complet, filtre TOUT),
  `data/apercu_calendrier_coupe_rapport.png` (rapport complet de coupe).

### VALIDATION
- `test_cup_report_links.py` : **ALL OK** · `data/error.log` : **0 octet**.
- Suite complète : **ALL OK** · `data/error.log` : **0 octet**.


## Annexe GW - Coupe : séance de 10 m visible (03/11/2026)

### DEMANDE
- « 2-2 en fin de match de coupe, et dès la 40e hop je perds 3-2 ...
  il n'y a pas eu les tirs au but à 10 m ? »

### DIAGNOSTIC
1. À égalité en coupe, le code **ajoutait un but au score** (2-2 → 3-2) pour
   désigner le qualifié, avec une seule ligne « 10 m — qualifié/éliminé ».
   Aucun tir n'était simulé ni affiché : le score officiel mentait.
2. Le qualifié était tiré par un simple aléa (attaque/défense), pas par une
   séance de tirs.
3. Le bilan de coupe comparait `notre score > leur score` : une victoire aux
   10 m était lue comme une **élimination**.
4. Le tableau de coupe et les cartes utilisaient `hg>ag` : mauvais vainqueur.

### CORRECTIONS
- **Vraie séance de 10 m** : 5 tirs chacun puis mort subite, arrêt dès que le
  sort est scellé. Chaque tentative est visible dans le direct (tireur,
  but/échec, score courant) et reprise dans un bloc **« SÉANCE DE 10 M »** du
  rapport ; l'en-tête affiche « 2 — 2 · 10 m : 4 — 2 · X qualifié ».
- **Le score du temps réglementaire reste 2-2**. Nouvelles colonnes
  `pen_home` / `pen_away` sur `fixture` et `match_record` ; `_cup_winner_of`
  les utilise pour le tableau et la progression.
- News : « COUPE R1 : QUALIFIÉ » / « ÉLIMINÉ » au lieu de « NUL ».
- Bilan de coupe, tableau et cartes lisent le vainqueur des 10 m : une
  victoire aux tirs n'est plus une élimination.
- Les matchs IA à égalité en coupe enregistrent aussi des 10 m (4-3) **sans
  gonfler le score**.
- Calendrier : mention « 10 m 4-2 » sur la carte et « (4 — 2 aux 10 m) » dans
  le détail. L'audit interne n'accepte un nul de coupe que s'il est résolu.
- Les matchs de coupe déjà joués avant ce correctif (3-2) restent tels quels :
  le score d'origine n'était pas conservé, on ne peut pas le reconstituer.

### NOUVEAU TEST `tests/test_cup_shootout.py` (branché dans la suite)
1. Égalité 2-2 : score conservé, `pen_home/pen_away` renseignés et différents.
2. Le qualifié du tableau est bien le vainqueur des 10 m.
3. Le direct contient les tentatives et le qualifié.
4. Calendrier : carte « 10 m x-y », détail 2-2 + tir au but, rapport complet.
5. Bilan de coupe : une victoire aux 10 m donne « VAINQUEUR » (pas « ÉLIMINÉ »).

### CAPTURES
- `data/apercu_coupe_10m_direct.png` (rapport : 2-2 + séance),
  `data/apercu_coupe_10m_rapport.png` (calendrier + rapport archivé).

### VALIDATION
- `test_cup_shootout.py` : **ALL OK** · `data/error.log` : **0 octet**.
- Suite complète : **ALL OK** · `data/error.log` : **0 octet**.


## Annexe GX - Pré-contrats : réflexion et contre-offre (03/11/2026)

### DEMANDE
- « Les pré-contrats semblent signés rapidement sans même un temps de réflexion
  du joueur ; cela pourrait inciter son club à faire une contre-offre pour le
  faire rester. »

### CE QUI A CHANGÉ
- **Plus de signature immédiate.** Une proposition de pré-contrat crée un
  dossier `precontract_offer` : le joueur réfléchit **6 à 9 jours** et le club
  actuel a **3 jours** pour réagir.
- **Contre-offre du club** : selon l'importance du joueur et le montant offert,
  son club propose une prolongation (salaire calculé, souvent au-dessus de
  l'offre). Le dossier affiche alors « Contre-offre de son club : X €/mois »,
  et un message « Pré-contrat • contre-offre » arrive dans la messagerie.
- **Décision du joueur** : elle dépend du salaire proposé face à sa demande,
  de l'écart de réputation/division entre les deux clubs et de la contre-offre.
  Issue visible par message et news :
  - « Pré-contrat signé : X rejoindra le club… » ;
  - « Pré-contrat refusé : X ne rejoindra pas le club. Son club a réagi avec
    une contre-offre à Y €/mois et il prolonge. »
- **Bandeau ARRIVÉES PRÉVUES** : il distingue désormais les **pré-contrats
  signés** et les **dossiers en réflexion** (carte ambre avec la date de
  décision et la contre-offre éventuelle). Le titre annonce
  « N PRÉ-CONTRAT(S) • M EN RÉFLEXION ».
- **Pas de doublon** : une deuxième offre sur le même joueur est refusée
  (« Offre déjà en cours — décision le … »).
- **Fin de saison** : les dossiers encore ouverts sont tranchés puis nettoyés
  avant l'arrivée officielle des pré-contrats signés.
- Les anciens pré-contrats déjà signés restent valides.

### TESTS
- `tests/test_precontract_season.py` mis à jour : l'offre est en attente,
  la décision est appliquée via `finalize_precontract`, puis l'arrivée à la
  nouvelle saison est vérifiée.
- Nouveau `tests/test_precontract_negotiation.py` (branché dans la suite) :
  1. offre en réflexion, aucune signature immédiate, date de décision future ;
  2. bandeau « EN RÉFLEXION » et carte d'attente ;
  3. contre-offre du club visible (message + salaire) ;
  4. refus argumenté (le joueur prolonge) ;
  5. acceptation malgré la contre-offre, champs pré-contrat corrects ;
  6. bandeau final : le signé remplace l'attente.

### CAPTURE
- `data/apercu_precontrat_attente.png` (dossier en réflexion + contre-offre).

### VALIDATION
- `test_precontract_negotiation.py` : **ALL OK** · `data/error.log` : **0 octet**.
- Suite complète : **ALL OK** · `data/error.log` : **0 octet**.


## Annexe GY - Audit Effectif / fiche joueur / fiche club (03/11/2026)

### DEMANDE
- « Audit de la page effectif / fiche joueur / fiche club. »

### EFFECTIF
- **Tableau qui débordait** : les largeurs mémorisées dans la sauvegarde
  (N° 174, POSTE 124, VALEUR 141, BUTS 188… soit 1 822 px) dépassaient la page
  (1 212 px) : les colonnes après CONTRAT étaient hors écran. Les largeurs
  mémorisées ne sont conservées que si elles restent raisonnables ; au-delà de
  145 % de l'espace disponible, le tableau revient aux largeurs de référence.
  Toutes les colonnes tiennent maintenant à 1600 px.
- **Cellules plus courtes** : SALAIRE sans « € / mois » (le titre suffit),
  VALEUR sans le préfixe « VALEUR », MORAL sans « /20 », J/S en `2J/1S`.
- En-têtes lisibles (padding réduit, largeur minimale 28 px) et dernière
  colonne qui absorbe l'espace restant.
- **Fiche express invisible** : le panneau n'était jamais affiché
  (`setVisible(True)` manquant). Il apparaît désormais dès qu'une ligne est
  sélectionnée, **au-dessus du tableau**, avec un résumé sur deux lignes
  (niveau/forme/moral/contrat/salaire) et les 6 barres d'attributs bornées.
- Hauteur du tableau plafonnée : la fiche express reste visible sans devoir
  faire défiler toute la page.

### FICHE JOUEUR
- **Contrat approximatif pour nos propres joueurs** : « ≈ 2-4 an(s) » alors que
  le contrat est connu. Le contrôle de connaissance ignorait `is_own` :
  affichage exact désormais (« 2 ans », « 1 an »), au lieu d'une fourchette.
- Pluriels corrigés (an/ans) dans la tuile contrat.

### FICHE CLUB
- **Classement illisible** : « 61 » (buts pour/contre collés) devient
  **« BP 6 · BC 1 »**.
- **Singuliers** : « 1 PT » (au lieu de 1 PTS), « 1 MATCH » (au lieu de
  1 MATCHS), « 1 but » (au lieu de 1 buts), « 1 arrêt », « Contrat 1 an /
  N ans » dans les effectifs IA.

### BONUS (trouvé pendant la validation)
- Tableau de bord : le prochain match contre le rival affichait « DERBY » et
  perdait le numéro de journée. Il affiche maintenant **« J04 • DERBY »**.

### NOUVEAU TEST `tests/test_squad_audit.py` (branché dans la suite)
1. Tableau : aucun dépassement horizontal, en-têtes présents, contrat « 1 an »,
   salaire sans « /mois », valeur sans préfixe, moral sans /20, J/S compact.
2. Fiche express visible, au-dessus du tableau, résumé contrat/forme/moral.
3. Fiche joueur : contrat exact (« 1 an »), aucune fourchette « ≈ ».
4. Fiche club : « BP 2 · BC 2 », « 1 PT », « 1 MATCH », « 1 but ».
5. Fiche club IA : aucun « an(s) », « 1 but » correct.

### CAPTURES
- `data/apercu_effectif.png`, `apercu_fiche_joueur.png`,
  `apercu_fiche_club.png`, `apercu_fiche_club_ia.png`.

### VALIDATION
- `test_squad_audit.py` : **ALL OK** · `data/error.log` : **0 octet**.
- Suite complète : **ALL OK** · `data/error.log` : **0 octet**.


## Annexe GZ - Audit visuel des images : fonds et placement (03/11/2026)

### DEMANDE
- « Audit visuel des images pour leur placement, fond, que ce soit le plus
  propre et beau. »

### CE QUI N'ALLAIT PAS
1. **Bandeau de la barre latérale** (`ban2.png`) : le PNG a un **fond blanc**
   opaque. Affiché dans la barre sombre, il formait un **rectangle blanc** en
   haut à gauche, avec un bord net et sans cadre.
2. **Logo de l'écran de démarrage** (`logo1.png`) : le logo a un **fond noir**
   carré. Sur le dégradé sombre du démarrage, le carré noir restait visible
   autour de l'écusson.
3. Vérification des autres images : écussons, maillots, avatars (coins
   arrondis transparents), logos sponsors (vectoriels transparents) — rien à
   corriger.

### CORRECTIONS
- Nouveau détourage `_transparent_key_pixmap(path, key)` : le fond uni (blanc
  ou noir) **relié aux bords** est rendu transparent par flood-fill. Les zones
  claires **internes** (lettres « FUTSAL », écusson) restent opaques.
- **Bandeau** : détouré (fond blanc), centré, posé sur une **plaque sombre
  arrondie** avec un liseré discret (`border-radius`, dégradé) et scalé
  286×96 au-dessus de la barre de recherche.
- **Logo de démarrage** : `logo1.png` détouré de son fond noir (flood-fill),
  le logo flotte sur le fond du StartBackdrop au lieu d'un carré noir.
- Les avatars restent des vignettes arrondies transparentes (64×64 dans la
  fiche express, 88 dans la fiche joueur), les écussons/maillots sont déjà
  transparents.

### NOUVEAU TEST `tests/test_images_audit.py` (branché dans la suite)
1. Détourage du bandeau : coins alpha 0, logo central conservé.
2. Bandeau en place : 223×96, centré, cadre arrondi, au-dessus de la recherche.
3. Logo de démarrage : fond noir supprimé, centre opaque.
4. Avatars : 64×64, coins transparents, fiche express alimentée.

### CAPTURES
- `data/apercu_images_demarrage.png` (écran de démarrage, logo détouré),
  `data/apercu_images_banniere.png` (bandeau dans la barre latérale).

### VALIDATION
- `test_images_audit.py` : **ALL OK** · `data/error.log` : **0 octet**.
- Suite complète : **ALL OK** · `data/error.log` : **0 octet**.


## Annexe HA - Écussons, tarifs finances et fenêtres Python (03/11/2026)

### DEMANDE
- « Certaines images sont décalées, notamment les écussons des clubs pour les
  rencontres sur la page Direction sportive ; bugs d'affichage sur les
  applications de tarifs dans Finances ; plein de fenêtres Python qui s'ouvrent
  et se ferment quand j'ouvre les entraînements. » (+ « relance »)

### ÉCUSSONS (DIRECTION SPORTIVE)
- **Cause** : `set_fixture_visual` demandait des écussons de **48 px** pour les
  badges du prochain match, alors que les labels du tableau de bord sont
  **36×36**. Le pixmap était rogné et le blason apparaissait décalé.
- **Correction** : la taille du badge suit désormais la largeur réelle du label
  (36 px au tableau de bord, 66 px au centre de match). Les deux écussons sont
  centrés et complets.
- Test : `test_images_audit.py` vérifie `dashboard 36×36`, `match 66×66`.

### TARIFS (FINANCES > EXPLOITATION)
- **Cause** : « APPLIQUER LE TARIF » (et les prix bar/boutique) appelaient
  `refresh_all()`. Ce refresh global recalculait la **confiance des
  supporters** (68 → 71) et donc l'affluence estimée : la projection changeait
  sous les yeux juste après l'application.
- **Correction** : rafraîchissement **ciblé** de l'onglet Exploitation et des
  visuels finances, sans rechargement global. Le tarif appliqué, l'affluence,
  la recette et l'onglet restent stables ; la confiance des supporters ne bouge
  plus sur une simple application de tarif.
- Test : 8e contrôle de `test_finances_audit.py` (tarif 25 €, projection et
  confiance identiques avant/après, onglet conservé).

### FENÊTRES PYTHON (ENTRAÎNEMENT)
- Vérification : la page Entraînement ne crée **aucun processus** ni fenêtre
  supplémentaire (un seul `MainWindow` visible avant/après, tous les onglets).
- Les fenêtres qui clignotaient venaient du **lanceur** : `LANCER.bat` faisait
  `pip install` puis `python main.py` dans une console visible.
- `LANCER.bat` installe maintenant en silence et démarre avec **`pythonw`**
  (aucune console). Le jeu a été relancé : processus `pythonw`, fenêtre JGames.

### FINITION
- Les tuiles « JOUEURS EN VUE » affichaient des emojis (🥅/🧤) rendus en barres
  verticales/tofu selon la police. Les libellés texte sont conservés, sans
  emoji, pour un rendu net.

### CAPTURES
- `data/apercu_direction_fix.png` (écussons alignés),
  `data/apercu_finances_tarifs.png` (tarifs bar/boutique + prix appliqué stable).

### VALIDATION
- `test_images_audit.py`, `test_finances_audit.py`, `test_dashboard_audit.py`
  rejoués : **ALL OK** · `data/error.log` : **0 octet**.
- Suite complète : **ALL OK** · `data/error.log` : **0 octet**.


## Annexe HB - Prêts : fiches complètes et mentions (03/11/2026)

### DEMANDE
- « Nos joueurs prêtés doivent être visibles sans scouting et complets ; la
  mention "prêté par tel club" doit être visible sur la fiche du joueur. »

### CE QUI A ÉTÉ CORRIGÉ
1. **Joueur prêté PAR NOUS** (club_id = club d'accueil, loan_from_club = 1) : la
   fiche le considérait comme un joueur adverse (`is_own` = club_id==1), donc
   attributs masqués par le scouting. `is_own` inclut désormais **nos prêts
   sortants** : niveau, potentiel, salaire, valeur et attributs sont complets.
2. **Mention dans la fiche** (bandeau ambre sous l'identité) :
   - joueur prêté **chez nous** : « PRÊTÉ PAR [club propriétaire] • retour en fin
     de saison » ;
   - notre joueur **prêté ailleurs** : « PRÊTÉ À [club d'accueil] • il appartient
     à votre club » ;
   - joueur d'un autre club lui-même prêté : « PRÊTÉ PAR [club propriétaire] ».
3. **Fiche express de l'Effectif** : la ligne de résumé affiche aussi
   « PRÊTÉ PAR [club] » pour un joueur prêté chez nous.
4. L'onglet **Transferts > PRÊTS** reste la vue complète : prêts sortants (club
   d'accueil, division, promesse, niveau, évolution, temps de jeu, note) et
   prêts entrants (club propriétaire, niveau, évolution, temps de jeu).

### NOUVEAU TEST `tests/test_loan_profiles.py` (branché dans la suite)
1. Un prêt sortant et un prêt entrant sont listés dans l'onglet PRÊTS.
2. Fiche du prêt sortant : niveau exact (pas de « ≈ »), attributs visibles,
   « PRÊTÉ À … ».
3. Fiche du prêt entrant : niveau exact, attributs visibles, « PRÊTÉ PAR … ».
4. Fiche express : mention « PRÊTÉ PAR … ».

### CAPTURES
- `data/apercu_prets.png` (les deux listes),
  `data/apercu_fiche_pret_entrant.png` (PRÊTÉ PAR),
  `data/apercu_fiche_pret_sortant.png` (PRÊTÉ À).

### VALIDATION
- `test_loan_profiles.py` : **ALL OK** · `data/error.log` : **0 octet**.
- Suite complète : **ALL OK** · `data/error.log` : **0 octet**.


## Annexe HC - Audit global : parcours complet et images (03/11/2026)

### DEMANDE
- « Test des bugs sur la globalité, attention ne lance pas l'appli au premier
  plan. »

### MÉTHODE (hors écran, aucune fenêtre au premier plan)
- Nouveau `tests/global_smoke.py` : instancie la vraie fenêtre en
  `QT_QPA_PLATFORM=offscreen` + `WA_DontShowOnScreen`, puis :
  1. visite **toutes les pages** et **tous les onglets** (`QTabWidget`) ;
  2. ouvre fiches joueur (notre club et adversaire), fiches club 1/2, prêts,
     offres, pré-contrats, dialogues ;
  3. exerce la composition auto, l'enregistrement de tactique, le staff, les
     4 onglets Finances, les 3 onglets Calendrier et les 3 filtres ;
  4. avance 70 jours et joue les matchs du jour (`start_match` +
     `finish_match_now`) ;
  5. re-visite toutes les pages après matchs ;
  6. scanne chaque **pixmap visible** : tout pixmap plus grand que son QLabel
     révèle un écusson rogné/décalé (nom du label, parent, infobulle).
- Deux modes : `fresh` (univers neuf) et `save` (copie TEMP de la sauvegarde
  utilisateur, jamais modifiée).

### BUGS TROUVÉS ET CORRIGÉS
1. **Écusson d'en-tête rogné** : le pixmap était dessiné en 64x64 dans un
   QLabel de 62x62. `draw_badge` reçoit désormais `size=62` → plus aucun
   débordement (constaté sur toutes les pages).
2. **Icône maillot de la boutique rognée** : pixmap 30x30 dans un label 28x28
   (rangée produit « Maillot »). Taille ramenée à **28**.
- Aucun autre débordement d'image, aucune exception de page/onglet, sur
  univers neuf **et** sur la sauvegarde réelle.

### TESTS
- `tests/global_smoke.py` ajouté en fin de `SUITES` (`tests/run_tests.py`) :
  il se termine par `RESULT: ALL OK` et sort en code 1 au moindre problème.
- `tests/test_images_audit.py` : nouveau contrôle **3c** — pixmap de l'écusson
  d'en-tête ≤ label, icône boutique ≤ label (boutique activée pour le test).

### VALIDATION
- `global_smoke.py fresh` : **problèmes 0**, `error.log` 0 octet (33 s).
- `global_smoke.py save` : **problèmes 0**, `error.log` 0 octet.
- Suite complète : **89 suites PASS, 0 FAIL** · `RESULT : ALL OK` ·
  `data/error.log` : **0 octet** (≈ 8 min).

### CAPTURES
- `data/apercu_global_header.png` : en-tête, écusson + maillot 62x62 nets.
- `data/apercu_global_boutique.png` : Finances > Exploitation > Boutique,
  icône maillot 28x28 et tarifs appliqués proprement.


## Annexe HD - Préparation bêta : propreté technique (03/11/2026)

### OBJECTIF
- « Je veux le jeu le plus clean possible avant de lancer une bêta test. »

### NETTOYAGE APPLIQUÉ
1. **Trace UI coupée par défaut** : `log_trace` écrivait à chaque changement de
   page ; `data/ui_trace.log` pesait **14 Mo**. Désormais muette sauf
   `FM2027_TRACE=1`, avec plafond 2 Mo et rotation en `.1`. Après la suite
   complète : le fichier **n'est pas recréé**.
2. **Journal de crash plafonné** : `data/fault.log` tourne en `.1` au-delà de
   512 Ko (conservé, il sert au diagnostic).
3. **Racine nettoyée** : `app.py.corrupt.bak` (1,4 Mo) archivé. Quatre modules
   morts (jamais importés) archivés : `calendar_service.py`, `league_table.py`,
   `model.py`, `theme.py`. `__pycache__/` supprimé.
4. **Données rangées** : 65 captures d'audit déplacées de `data/` vers
   `data/captures/`. Les 5 sauvegardes de test (`test_*.db`) sorties du dossier
   `data/saves/` : le menu **CHARGER UNE PARTIE** n'affiche plus que les
   4 carrières réelles.
5. **README réécrit** : il décrivait des fichiers inexistants (`views/`,
   `app_assembly.py`) et affichait des caractères corrompus. Il reflète
   maintenant l'architecture réelle, les emplacements de données, les tests et
   une checklist bêta (résolutions, rapport de bug, `error.log`).
6. **Table des transferts** : une nationalité vide affiche **« — »** au lieu de
   « N/A ».

### TESTS AJOUTÉS
- `tests/test_beta_clean.py` :
  1. scan des labels, boutons, onglets, tables et infobulles des 14 pages :
     **0 résidu** (« None », « NaN », « Traceback », « N/A », `{}`, mojibake…) ;
  2. trace muette par défaut, écriture et rotation quand activée ;
  3. racine sans fichier corrompu/backup.
- `tests/test_old_save_boot.py` : vrai boot (`init_db()` puis `MainWindow`) sur
  une copie de **chaque** sauvegarde présente — les 4 carrières réelles
  s'ouvrent sans erreur (migrations comprises). Ignoré si aucune sauvegarde.
- `tests/global_smoke.py` : scan des textes ajouté, en plus des images, sur
  univers neuf **et** sur copie de sauvegarde.

### VÉRIFICATIONS COMPLÉMENTAIRES
- Premier lancement **sans aucune sauvegarde** : écran de démarrage, catalogue
  vide, `error.log` 0 octet.
- `data/error.log` : **0 octet** après tous les essais.
- Aucun chemin absolu `C:\FM2027V2` / `C:\Users` codé dans les modules.

### VALIDATION
- Suite complète : **91 suites PASS, 0 FAIL** · `RESULT : ALL OK` ·
  `data/error.log` **0 octet** (≈ 7 min 15).
- `python tests\global_smoke.py fresh` et `save` : 0 problème.

### CAPTURE
- `data/captures/apercu_charger_partie_beta.png` : menu de chargement propre,
  4 carrières réelles, plus aucune sauvegarde de test.


## Annexe HE - Éditeur de sauvegarde autonome (03/11/2026)

### DEMANDE
- « Autre chose qu'un simple module triche : un éditeur permettant de modifier
  les stats des joueurs, les budgets des clubs, le niveau des infras, le staff,
  voir toute la base des joueurs avec leur potentiel et les changer de club…
  sans qu'il soit trop visible en jeu. »

### CHOIX D'INTÉGRATION : HORS DU JEU
- Aucun bouton, onglet, raccourci ni texte n'est ajouté dans le jeu. Rien ne
  pointe vers l'éditeur depuis l'interface : impossible de le confondre avec
  une fonction de jeu.
- L'éditeur est un programme séparé dans `editeur/` :
  - `EDITEUR.bat` (lancement) ;
  - `editeur_sauvegarde.py` (application) ;
  - `LISEZMOI.md` (mode d'emploi + « ne pas distribuer »).
- Il ouvre directement un fichier `.db` de `data/saves/` et travaille sur la
  copie choisie. Pour une bêta publique, il suffit de retirer le dossier
  `editeur/` de l'archive.

### FONCTIONS
1. **Clubs** : budget, réputation, division, nom de la salle. Table des 60 clubs.
2. **Joueurs** : toute la base (860+ joueurs), recherche, filtre par club,
   filtre « joueurs libres », tri par nom / niveau / potentiel / valeur / âge.
   - identité : prénom, nom, âge, poste, nationalité, numéro ;
   - club : transfert direct vers n'importe quel club ou statut « joueur libre » ;
   - 9 attributs affichés **/20 comme dans le jeu** (stockés 0-100 en base) ;
   - potentiel (`potential_fixed`), valeur, salaire, contrat, condition, moral ;
   - blessures, suspensions, cartons, liste des transferts ;
   - bouton **RECALCULER LA VALEUR** avec le même barème que le jeu.
3. **Staff** : 8 postes (adjoint, architecte, comptable, directeur sportif,
   marketing, kiné, préparateur physique, recruteur) : embauche, niveau 1-5,
   nom, nationalité.
4. **Infrastructures** : 9 niveaux (tribunes, médical, formation, marketing,
   éclairage, parking, vidéo, bénévoles, restaurant), 6 équipements, prix du billet.
5. **Sauvegardes** : intégrité SQLite, nombre de joueurs/clubs, création et
   restauration de copies de secours.

### GARDE-FOUS
- **Aucune migration de schéma** : l'éditeur ne crée, ne supprime et ne modifie
  aucune table ; il n'écrit que des colonnes existantes.
- **Copie automatique avant la première écriture** :
  `data/saves/editeur_backups/<sauvegarde>_AAAAMMJJ_HHMMSS_auto.db` ; 10 copies
  conservées. Ce sous-dossier n'est pas lu par le menu **CHARGER UNE PARTIE** :
  les copies de l'éditeur n'apparaissent jamais comme des carrières.
- **Restauration** : copie de sécurité de l'état courant avant remplacement.
- **Détection jeu ouvert** : verrou SQLite ou fichiers `-wal`/`-shm` → bandeau
  d'avertissement ; écritures bloquées si la base est verrouillée.
- **Validation stricte** : âge 15-60, attributs 1-20, potentiel 1-20,
  budget ≥ 0, etc. Les valeurs hors limites sont refusées avec un message.
- **Cohérence** :
  - changement de club → prêt et pré-contrat remis à zéro ;
  - numéro de maillot déjà pris → libéré automatiquement ;
  - potentiel < niveau → potentiel relevé au niveau ;
  - `player_attr_baseline` de la saison recalé sur les nouvelles valeurs pour
    que la progression affichée dans le jeu reparte de zéro.

### TESTS (`tests/test_save_editor.py`, 13 contrôles)
1. ouverture d'une sauvegarde neuve (60 clubs, 860 joueurs, 8 postes) ;
2. club : budget, réputation, division, salle ;
3. infrastructures : niveaux, équipements, tarif ;
4. joueur : 9 attributs, potentiel, valeur, salaire, transfert ;
5. numéro déjà pris → libéré ;
6. joueur libre sans casser le club d'origine ;
7. staff : 8 postes niveau 5 avec noms ;
8. valeur recalculée ;
9. copie de secours + intégrité `ok` ;
10. valeurs hors limites refusées ;
11. **la sauvegarde éditée s'ouvre dans le jeu sans erreur** (`init_db` +
    `MainWindow` + `refresh_all`) ;
12. modifications réelles via l'interface (joueur, staff, club, infras) ;
13. interface : 5 onglets peuplés, ouverture/fermeture propres.

### VALIDATION
- `test_save_editor.py` : **ALL OK**, `data/error.log` 0 octet.
- Suite complète : **92 suites PASS, 0 FAIL** · `RESULT : ALL OK` ·
  `data/error.log` 0 octet.

### CAPTURES
- `data/captures/apercu_editeur_clubs.png`
- `data/captures/apercu_editeur_joueurs.png`
- `data/captures/apercu_editeur_staff.png`
- `data/captures/apercu_editeur_infrastructures.png`
- `data/captures/apercu_editeur_sauvegardes.png`


## Annexe HE-bis - Éditeur : filtres et lisibilité des sauvegardes (03/11/2026)

### DEMANDE
- « Plus de filtres sur les colonnes, et que ce soit plus clair sur la
  sauvegarde de la base pour jouer avec. »

### FILTRES AJOUTÉS (onglet JOUEURS)
- **Poste** (Gardien, Défenseur, Universel, Pivot, Ailier).
- **Âge minimum / maximum** (0 = sans limite).
- **Niveau minimum** (0–20).
- **Potentiel minimum** (0–20).
- **Valeur minimum** (pas de 250 000 €, 0 = toutes).
- **Contrat** : tous, ≤ 1 an, ≤ 2 ans, ≤ 3 ans, expiré.
- **Statut** : disponible, blessé, suspendu, sur la liste, prêté, libre, retraité.
- Combinés à la recherche par nom, au filtre club, au filtre « joueurs libres »,
  à l'inclusion des retraités et au tri (club / nom / niveau / potentiel /
  valeur / âge).
- Compteur **« X / Y joueur(s) »** et bouton **RÉINITIALISER LES FILTRES**.
- **EXPORTER CSV** : exporte exactement la liste filtrée (séparateur `;`,
  UTF-8 BOM pour Excel), avec niveau, potentiel, 9 attributs /20, valeur,
  salaire, contrat, condition, moral et statut.

### FILTRES AJOUTÉS (onglet CLUBS)
- Recherche par nom, filtre par division, tri (division / nom / budget /
  réputation), compteur de clubs.

### SAUVEGARDE PLUS CLAIRE
- En-tête en deux lignes :
  - **chip d'état** : `PRÊTE · ÉCRITURE` (vert), `JEU OUVERT ?` (ambre, fichiers
    `-wal`/`-shm`), `VERROUILLÉE` (rouge) ;
  - métadonnées : fichier, taille, date de modification, club/division/saison,
    nombre de joueurs ;
  - bouton **DUPLIQUER POUR TESTER**.
- **DUPLIQUER POUR TESTER** crée `..._test.db` et bascule l'éditeur dessus :
  la carrière d'origine n'est plus touchée, la copie apparaît dans
  **CHARGER UNE PARTIE** pour jouer avec les modifications.
- Onglet SAUVEGARDES restructuré :
  - carte **SAUVEGARDE OUVERTE** : chemin complet, taille, date, intégrité
    SQLite, joueurs/clubs, boutons dupliquer / copier le chemin / ouvrir le
    dossier ;
  - section **COPIES DE SECOURS** : dossier affiché, explication « écriture
    immédiate », liste datée, création/restauration, ouverture du dossier.
- Les copies automatiques vont dans `editeur_backups/` : **invisibles** dans
  CHARGER UNE PARTIE.
- Bandeau permanent : « écriture immédiate + utiliser DUPLIQUER POUR TESTER ».
- Raccourcis : `Ctrl+F` recherche, `Ctrl+S` copie de secours, `Ctrl+D` dupliquer.
- Correction d'affichage : le formulaire suit désormais la ligne réellement
  sélectionnée après un changement de filtre.

### TESTS
`tests/test_save_editor.py` passe à **17 contrôles** :
- filtres cœur : poste, âge, niveau, potentiel, statut ;
- export CSV (en-tête + nombre de lignes) ;
- copie de travail indépendante (même base, autre fichier) ;
- filtres dans l'interface + compteur + réinitialisation ;
- filtre clubs + panneau sauvegarde (chemin, copie, liste).

### VALIDATION
- `test_save_editor.py` : **ALL OK**, `error.log` 0 octet.
- Suite complète : **92 suites PASS, 0 FAIL** · `RESULT : ALL OK` ·
  `data/error.log` 0 octet.

### CAPTURES MISES À JOUR
- `apercu_editeur_clubs.png` (recherche + division + tri)
- `apercu_editeur_joueurs.png` (filtres poste/âge/tri + export)
- `apercu_editeur_sauvegardes.png` (sauvegarde ouverte + copies de secours)
- `apercu_editeur_staff.png`, `apercu_editeur_infrastructures.png`


## Annexe HF - Cohérence des icônes directionnelles (03/11/2026)

### PROBLÈME SIGNALÉ
- « Les icônes de formes ne sont jamais toutes dans le bon sens entre les
  différents affichages, c'est perturbant. »

### LANGAGE VISUEL UNIFIÉ
| Glyphe | Usage unique |
| --- | --- |
| **→** | navigation / ouvrir une fiche, un rapport, une page |
| **▶** | lancer ou reprendre un match (play) |
| **▲ / ▼** | direction : tri, évolution, promotion / relégation |
| **◀ / ▶** | uniquement l'axe défense → attaque du terrain tactique |

Les glyphes **↗**, **↑** et **↓** ont été supprimés de toute l'interface.

### CORRECTIONS
1. **Bouton REPRENDRE** : il affichait à la fois une icône play et un `▶` dans
   le texte. Le doublon est retiré ; l'icône play reste seule.
2. **Bouton QUITTER LE JEU** : il utilisait l'icône « flèche retour » (kind 302).
   Nouvelle icône **power** dédiée (kind 303).
3. **Bouton OPTIONS** : il affichait trois barres (icône menu). Il utilise
   maintenant une **roue crantée** (kind 301) ; le bouton menu du bandeau garde
   les trois barres. L'ancien helper `_gear_icon_pixmap` (qui dessinait des
   barres) est renommé `_menu_icon_pixmap`.
4. **Navigation** : `FICHE ↗`, `RAPPORT ↗`, `RAPPORT RÉCENT ↗` et
   `RAPPORT • COUPE ↗` passent à **→** ; tous les boutons `FICHE` (classements,
   recherche, banc, prêts) affichent `FICHE →` ; `RAPPORT DU MATCH →`.
5. **Actions de message** : `▶ Voir le Mercato` et le lien
   `▶ Ouvrir le centre de match` passent à **→**.
6. **Tri du banc** : `NOTE ↓`, `FORME ↓`, `SALAIRE ↓`, `ÂGE ↑`, `CONTRAT ↑`
   deviennent **`NOTE ▼`, `FORME ▼`, `SALAIRE ▼`, `ÂGE ▲`, `CONTRAT ▲`**, avec
   une infobulle « ▼ = plus haut d'abord, ▲ = plus bas d'abord ».
7. **Évolutions** : la perte d'entraînement `↓` devient **▼** ; le badge de
   niveau de saison utilise **▲ / ▼** au lieu de `+1` / `▼` (le détail chiffré
   reste dans l'infobulle).
8. **Consignes individuelles** : l'icône `↗` de « Montée en puissance » devient
   **▲**, cohérente avec les autres indicateurs de progression.

### NOUVEAU TEST `tests/test_icon_consistency.py`
1. Source : plus aucun `↗`, `↑`, `↓` ; présence des libellés de tri ▲▼ et des
   icônes power/engrenage.
2. Interface : scan des labels, boutons, listes, onglets et infobulles de toutes
   les pages → aucun `↗/↑/↓`.
3. Navigation : tout bouton FICHE/RAPPORT/OUVRIR LE CENTRE utilise `→`, jamais
   `▶` ni `↗` ; le bouton REPRENDRE ne contient plus `▶` (icône seule).
4. Tri du banc : ordre et glyphes exacts.
5. **Orientation réelle** des icônes promotion/relégation : analyse des pixels
   opaques (tête en haut pour ▲, en bas pour ▼).
6. **Orientation réelle** des flèches de steppers QSpinBox (PNG générés).
7. Le bouton QUITTER n'utilise plus l'icône « retour ».

### VALIDATION
- `test_icon_consistency.py` : **ALL OK**.
- Suites ciblées (démarrage, calendrier, coupe, tactiques, dashboard) : **ALL OK**.
- Suite complète : **93 suites PASS, 0 FAIL** · `RESULT : ALL OK` ·
  `data/error.log` **0 octet**.

### CAPTURES
- `data/captures/apercu_icones_demarrage.png` (play, engrenage, power, menu)
- `data/captures/apercu_icones_tactiques.png` (tri ▼, FICHE →, axe ◀▶)
- `data/captures/apercu_icones_calendrier.png` (RAPPORT →)


## Annexe HG - Calendrier : étiquette « TON CLUB » sur les autres ligues (03/11/2026)

### PROBLÈME SIGNALÉ
- « Sur calendrier, sur les autres ligues c'est écrit TON CLUB, c'est
  perturbant et inutile. »

### CAUSE
- `build_division_fixture_card` créait une étiquette `TON CLUB` pour **chaque**
  match de division. Pour les matchs sans le club du joueur, seul le fond et la
  bordure étaient neutralisés (`border:none`) : le **texte restait visible**.
  Résultat : toutes les cartes des autres championnats affichaient « TON CLUB ».

### CORRECTION
- L'étiquette est désormais **créée et ajoutée uniquement si le match implique
  le club du joueur** (`is_own`). Les autres ligues n'affichent plus aucun
  « TON CLUB ».
- Le comportement reste correct si le club du joueur apparaît dans une vue de
  division (par exemple après un changement de division via l'éditeur) :
  l'étiquette est alors présente uniquement sur ses matchs.

### TEST (`tests/test_calendar_audit.py`, section 5)
- Passage en **Ligue 1** (autre division que le club de test) : les **90 cartes**
  sont contrôlées, aucune ne contient « TON CLUB ».
- Carte synthétique avec le club du joueur : « TON CLUB » présent.
- Carte synthétique entre deux autres clubs : « TON CLUB » absent.

### VALIDATION
- `test_calendar_audit.py` : **ALL OK**.
- Suite complète : **93 suites PASS, 0 FAIL** · `RESULT : ALL OK` ·
  `data/error.log` **0 octet**.

### CAPTURE
- `data/captures/apercu_icones_calendrier.png` : calendrier complet de la
  Ligue 2 (autre ligue) sans aucune étiquette « TON CLUB ».


## Annexe HH - Forme VND : même sens partout (03/11/2026)

### PROBLÈME SIGNALÉ
- « L'affichage de la forme des équipes VND n'est pas dans le même sens dans
  tous les menus. »

### CONSTAT
- **Direction du tableau de bord** : du plus ancien (gauche) au plus récent
  (droite), avec l'infobulle « le plus récent à droite ».
- **Classement autonome** : même sens (oldest → newest).
- **Fiche club** : sens inverse (plus récent à gauche) pour la tuile FORME, le
  bandeau de pastilles et les cartes de classement.
- **Périmètre incohérent** : le tableau de bord et le classement ne comptaient
  que le championnat, tandis que la fiche club incluait la coupe (et les
  amicaux dans sa tuile FORME).

### CORRECTION
1. **Sens unique** : toutes les séquences VND se lisent désormais **du plus
   ancien (gauche) au plus récent (droite)**, comme le tableau de bord.
2. **Périmètre unique** : la forme ne compte que les **matchs de championnat**
   partout (dashboard, classement, cartes de clubs, tuile et pastilles de la
   fiche club). Coupe et amicaux sont exclus.
3. **Fiche club** :
   - `form_by_club` repasse en ordre chronologique avant affichage des cartes ;
   - la tuile « FORME • 5 DERNIERS » et le bandeau de pastilles utilisent les
     5 derniers matchs de championnat dans le bon sens ;
   - la liste **DERNIERS RÉSULTATS** est également chronologique et son titre
     indique « DU PLUS ANCIEN AU PLUS RÉCENT » (elle garde toutes compétitions,
     avec leurs étiquettes COUPE/AMICAL).
4. **Infobulles** ajoutées sur les pastilles, la tuile FORME et le KPI du
   classement : « Forme en championnat : du plus ancien (gauche) au plus récent
   (droite) ».

### TESTS RENFORCÉS
- `test_dashboard_audit.py` : V N D déjà vérifié de gauche à droite.
- `test_competitions_audit.py` : la KPI **et** les pastilles de la carte du club
  doivent afficher exactement la même séquence chronologique ; la coupe reste
  exclue.
- `test_club_sheet_ui.py` : la tuile FORME et les pastilles de la fiche club
  doivent correspondre aux 5 derniers matchs de championnat, dans l'ordre
  chronologique (test ouvert sur le club du joueur).

### VALIDATION
- `test_club_sheet_ui.py`, `test_competitions_audit.py`,
  `test_dashboard_audit.py` : **ALL OK**.
- Suite complète : **93 suites PASS, 0 FAIL** · `RESULT : ALL OK` ·
  `data/error.log` **0 octet**.

### CAPTURES
- `data/captures/apercu_forme_dashboard.png` : tableau de bord, forme N V.
- `data/captures/apercu_forme_fiche_club.png` : fiche club, tuile N V, pastilles
  N V, cartes de classement N V, liste chronologique N puis V.


## Annexe HI - Objectifs du board : indulgence en début de saison (03/11/2026)

### DEMANDE
- « Direction sportive > objectif du board : être indulgent quand la saison
  démarre. C'est normal de ne pas pouvoir atteindre l'objectif en 1 ou 2 matchs ;
  il faut juger selon la possibilité de l'atteindre. »

### ANCIEN COMPORTEMENT
- Le classement actuel était comparé directement à la place visée : après une
  ou deux journées, une position provisoire pouvait afficher une alerte rouge,
  faire baisser la confiance et déclencher un avertissement du board.

### NOUVEAU COMPORTEMENT
1. **Phase de lancement : les 3 premiers matchs de championnat.**
   - pastille bleue **« … OBJECTIF • Xe/Y »** au lieu d'un verdict ;
   - sous-titre : « début de saison : évaluation après 3 matchs » ;
   - confiance neutre (`+5` ou `+8`), **aucun avertissement**, **aucun gel des
     transferts** ;
   - la confiance des supporters ne baisse pas sur cette phase.
2. **Après 3 matchs : évaluation par la faisabilité**, pas seulement le rang :
   - retard en points sur la place visée ;
   - matchs restants et points encore gagnables (`+3 par match`) ;
   - écart de places encore rattrapable (`slack` calculé sur les matchs restants).
   - **✔ sous contrôle** : place visée déjà atteinte ;
   - **⚠ atteignable** (ambre) : retard compatible avec les matchs restants ;
   - **⚠ compromis** (rouge) : retard trop important pour la fin de saison.
3. **Infobulle détaillée** : position, matchs joués/restants, retard en points,
   maximum encore gagnable, statut.
4. **Avertissement du board et gel des transferts** uniquement après 3 matchs
   et si la confiance passe sous les seuils (30 % / 22 %).
5. Le nombre de matchs joués est lu dans les **fixtures de championnat** (plus
   fiable que le classement, y compris après édition d'une sauvegarde).

### TESTS (`test_dashboard_audit.py`)
- **0 match** : pastille « … », sous-titre « début de saison », confiance 65 %.
- **2 défaites** : toujours en lancement, confiance 65 %, pas de gel, pas
  d'avertissement.
- **3 matchs** : la phase de lancement se termine et le board évalue.

### VALIDATION
- `test_dashboard_audit.py` : **ALL OK**.
- Suite complète : **93 suites PASS, 0 FAIL** · `RESULT : ALL OK` ·
  `data/error.log` **0 octet**.

### CAPTURE
- `data/captures/apercu_forme_dashboard.png` : saison 9, 2 matchs joués,
  « … TITRE • 2e/1 », sous-titre « début de saison : évaluation après
  3 matchs », confiance 70 %.


## Annexe HJ - Éditeur : tri par colonnes et baisse des infrastructures (03/11/2026)

### DEMANDES
- « Éditeur : il faut des tris sur les colonnes. »
- « J'ai tenté de baisser les infras sur un club mais ça ne semble pas avoir
  marché. »

### 1) TRI PAR CLIC SUR LES EN-TÊTES
- **Clubs** : ID, nom, division, réputation, budget, saison, salle.
- **Joueurs** : ID, nom, club, poste, âge, niveau, potentiel, valeur, salaire,
  contrat, statut.
- **Sauvegardes** : fichier, date, taille.
- Tri **numérique réel** (pas alphabétique) grâce à `SortableItem` : budget
  16 129 924 € passe avant 600 000 €, âge 9 avant 40, etc.
- Le tri est conservé après une modification/actualisation ; la ligne
  sélectionnée est retrouvée par son ID, pas par son ancienne position.
- Le tri par liste déroulante reste disponible (club / nom / niveau / potentiel
  / valeur / âge) et sert d'ordre initial.

### 2) BAISSE DES INFRASTRUCTURES
**Cause :** le jeu répare automatiquement les niveaux au chargement depuis :
- `meta.facility_max_<bâtiment>` (plus haut niveau historique) ;
- les chantiers `facility_project` terminés ;
- pour l'arène, les anciens paiements/actualités « Tribunes ».
Une baisse écrite seulement dans `facility` était donc remontée.

**Correction :**
- L'éditeur pose un **plafond manuel** `facility_editor_cap_<bâtiment>` et
  abaisse aussi `facility_max_<bâtiment>` et les cibles historiques ;
- les chantiers **en cours** au-dessus du nouveau niveau sont annulés ;
- `_repair_facility_levels` respecte ce plafond (niveaux et équipements) ;
- `_infer_arena_level_from_finance` ne peut plus reconstruire l'arène au-dessus ;
- dès qu'un **vrai chantier se termine dans le jeu**, le plafond de ce bâtiment
  est supprimé pour laisser une progression normale.
- Seuls les champs **modifiés** reçoivent un plafond : ouvrir puis appliquer
  sans rien changer ne verrouille pas les autres bâtiments.

**Précision :** l'onglet INFRASTRUCTURES concerne le **club du joueur (club 1)**.
Les autres clubs n'ont pas de campus séparé dans la base ; l'écran l'indique
désormais explicitement.

### TESTS
`tests/test_save_editor.py` :
- **3b** : création d'un historique arena 8 + plafond 8, puis baisse éditeur à 3
  → `facility` = 3, plafond = 3, chantiers historiques alignés ;
- **14** : au chargement réel du jeu (`init_db` + `MainWindow` + `refresh_all`),
  l'arène reste à 3 et le médical à 2 (pas de réparation vers le haut) ;
- **15** : tri par en-tête vérifié sur niveau, âge, budget et nom ; la sélection
  suit le bon joueur après tri.

### VALIDATION
- `test_save_editor.py` : **ALL OK** (18 contrôles).
- Suites infrastructures : **ALL OK**.
- Suite complète : **93 suites PASS, 0 FAIL** · `RESULT : ALL OK` ·
  `data/error.log` **0 octet**.

### CAPTURES
- `data/captures/apercu_editeur_clubs.png` : tri budget décroissant.
- `data/captures/apercu_editeur_joueurs.png` : tri potentiel décroissant.
- `data/captures/apercu_editeur_infrastructures.png` : club concerné affiché.


## Annexe HK - Installateur bêta Windows (03/11/2026)

### LIVRABLE
- `release\FutsalManager2027_Setup_2027.2.exe` — **70 478 056 octets** (~67 Mo).
- `release\SHA256.txt`.
- `release\LISEZMOI_BETA.txt`.
- SHA256 : `4B0BBAEE2D8F1EC6594E01332FBCB30DF37239959B350E59A5FE33ABB759827E`.

### COMPILATION
- PyInstaller **6.22.0**, Python 3.13.2, PySide6.
- Jeu : `FutsalManager2027.exe` (one-dir, `_internal` inclus).
- Éditeur : `FutsalManager2027Editeur.exe` (one-dir séparé, installé dans
  `Editeur\`).
- Icône **data/fm27.ico** sur les deux exécutables, le setup et les raccourcis.
- Installateur : Inno Setup **6.7.3**, français, installation **par utilisateur**
  (aucun droit administrateur).

### ADAPTATIONS POUR LA VERSION COMPILÉE
- `BASE_DIR` = `%APPDATA%\FM2027V2` (sauvegardes, logs, options) ;
- nouveaux chemins d'assets en lecture seule (`ASSET_DIR`) pour logo, bannière,
  fond, splash : les images restent dans l'installation ;
- icônes de combos/steppers générées dans `%APPDATA%\FM2027V2\data\icons`
  (dossier inscriptible, plus dans Program Files) ;
- sauvegardes de code désactivées en mode compilé (inutiles et non inscriptibles) ;
- l'éditeur compilé lit/écrit aussi `%APPDATA%\FM2027V2\data` pour retrouver les
  carrières du jeu.

### INSTALLATEUR
- Dossier : `%LOCALAPPDATA%\Programs\Futsal Manager 2027`.
- Groupe Démarrer : **Futsal Manager 2027**.
  - `Futsal Manager 2027` (jeu) ;
  - `Futsal Manager 2027 — Éditeur` (si l'option est cochée) ;
  - `Désinstaller Futsal Manager 2027`.
- Case optionnelle **« Installer l'éditeur de sauvegarde (outil avancé) »**,
  décochée par défaut : le jeu reste propre pour une bêta publique, l'éditeur
  est proposé aux testeurs avancés.
- Raccourci bureau optionnel pour le jeu.
- **Aucune sauvegarde utilisateur n'est incluse** : seuls les assets du jeu
  (logo, bannière, fond, splash) sont embarqués. Une mise à jour ou une
  désinstallation ne touche pas `%APPDATA%\FM2027V2`.
- `LISEZMOI_BETA.txt` installé dans le dossier du jeu (chemins des sauvegardes,
  error.log, éditeur, rapport de bug).

### VÉRIFICATIONS
- Jeu compilé lancé hors écran (APPDATA temporaire) : processus stable,
  `error.log` 0 octet, assets chargés.
- Jeu compilé avec une **vraie sauvegarde** (copie de la carrière saison 9) :
  démarrage stable, `error.log` et `fault.log` 0 octet.
- Éditeur compilé lancé hors écran : stable, retrouve les sauvegardes APPDATA.
- Installation silencieuse testée : jeu + éditeur + `fm27.ico` + readme + désinstalleur.
- Raccourcis vérifiés : cibles correctes, icône `fm27.ico` pour le jeu et l'éditeur.
- Désinstallation testée : dossier et groupe Démarrer supprimés, sauvegardes
  APPDATA conservées.
- Suite complète : **93 suites PASS, 0 FAIL** · `data/error.log` **0 octet**.

### REMARQUE BÊTA
- L'installateur n'est **pas signé** : Windows SmartScreen peut afficher un
  avertissement « Éditeur inconnu ». Pour le supprimer, il faudra un certificat
  de signature de code.


## Annexe HL - Immersion match day : avant-match, direct, vestiaire (07/11/2026)

### DEMANDE
- Avant-match + causerie.
- Commentaire live + sons de salle.
- Après-match : vestiaire + conférence de presse.

### AVANT-MATCH
- Le dialogue de confirmation affiche désormais une mise en scène :
  - **ARRIVÉE AU GYMNASE** : affluence estimée et remplissage ;
  - **VESTIAIRE** : ambiance selon derby / moral du groupe ;
  - **ADVERSAIRE** : forme récente et joueur dangereux ;
  - **ENJEU** : objectif du board et position actuelle.
- La causerie d'avant-match garde ses effets réels et ajoute une citation du
  capitaine (derby ou match normal).
- Les données viennent de `league_standing`, `fixture`, `player`, `facility` et
  `meta` (rival, objectif).

### COMMENTAIRE LIVE + SONS
- Nouveau module `immersion.py` :
  - `commentary_line()` : lignes de commentaire courtes, nettoyées du HTML et
    des timestamps, avec préfixes par catégorie (but, arrêt, carton, pause…).
  - `ArenaSound` : WAV synthétisés à la première utilisation dans `data/audio`
    (sifflet, buzzer, but, arrêt, frappe, foule, applaudissements).
- Centre de match :
  - bandeau de commentaire sous le chrono ;
  - nouvel onglet **COMMENTAIRE** avec historique coloré ;
  - bouton **SON : ON / SON : MUET**, choix conservé dans `game_options.json` ;
  - ambiance de fond démarrée au coup d'envoi, arrêtée au coup de sifflet final ;
  - sons déclenchés par les événements (but, arrêt, carton, temps mort, etc.).
- Aucun asset externe. En mode hors écran ou avec `FM2027_NO_AUDIO=1`, tout est
  silencieux et aucun WAV n'est créé (tests reproductibles).

### APRÈS-MATCH
- Nouvelle scène **VESTIAIRE** avant le rapport :
  - ambiance selon le résultat ;
  - citations du héros du match, du gardien et du capitaine ;
  - avatars et score.
- La conférence de presse s'ouvre ensuite si le joueur continue :
  - première question adaptée au résultat (réponses existantes) ;
  - deuxième question **« le mot aux supporters »** avec effet réel sur la
    confiance des supporters et ajout dans les actualités.
- `PASSER` permet de sauter la scène ; le mode accéléré ignore tout.

### TESTS
- Nouveau `tests/test_immersion.py` branché dans la suite :
  1. commentaire nettoyé et préfixé ;
  2. sons désactivés hors écran, aucun fichier créé ;
  3. ticker + journal branchés sur un but ;
  4. avant-match : salle, vestiaire, adversaire, enjeu ;
  5. vestiaire accepté → passage en conférence.
- `test_coaching_options.py` et `test_staff_delegations.py` restent OK
  (causeries/interviews déléguées).
- Suite complète : **94 suites PASS, 0 FAIL** · `data/error.log` **0 octet**.

### CAPTURES
- `apercu_avant_match.png` : arrivée, vestiaire, adversaire, enjeu.
- `apercu_causerie.png` : citation du capitaine + tons de causerie.
- `apercu_commentaire_live.png` : ticker, onglet COMMENTAIRE, bouton SON.
- `apercu_vestiaire.png` : héros, gardien, capitaine.
- `apercu_conference_presse.png` : salle de presse et première question.


## Annexe HM - QA immersion, rapport de bug et onboarding (07/11/2026)

### 1) QA IMMERSION
- Nouveau `tests/test_immersion_flow.py` : parcours complet avec une vraie
  sauvegarde copiée :
  1. avant-match accepté → match lancé ;
  2. commentaire de coup d'envoi présent, chrono/timer actifs ;
  3. fin de match : vestiaire et presse ignorés proprement, rapport enregistré,
     `error.log` à 0.
- Vérifications complémentaires :
  - `tests/test_immersion.py` : commentaire, sons coupés hors écran, avant-match,
    vestiaire ;
  - génération réelle des WAV testée à part (7 fichiers, QSoundEffect chargé) ;
  - captures d'écran des 5 scènes.
- Petits bugs corrigés pendant la QA :
  - doublon possible du même joueur dans le vestiaire (héros = capitaine) ;
  - en-tête de la presse renommé **CONFÉRENCE DE PRESSE** ;
  - import manquant `QPlainTextEdit` pour le formulaire de rapport.

### 2) RAPPORT DE BUG
- Nouveau `support.py` : `create_bug_report()` construit un ZIP autonome avec :
  - `rapport.txt` (version, OS, Python/PySide6, club/saison/date, description) ;
  - `error.log`, `fault.log`, `game_options.txt`, `ui_trace.log` si présents ;
  - **copie optionnelle de la sauvegarde active** via `sqlite3.backup` (jamais
    le fichier original).
- UI : bouton **SIGNALER UN BUG** dans les options (accueil et en jeu), dialogue
  avec description et case « inclure la sauvegarde » cochée par défaut.
- Les rapports vont dans `data/reports/rapport_bug_AAAAMMJJ_HHMMSS.zip`.
- `tests/test_bug_report.py` : contenu du ZIP, copie SQLite valide, sauvegarde
  intacte, option sans copie.

### 3) ONBOARDING
- Panneau **PREMIERS PAS** accessible depuis la Direction sportive et affiché
  une seule fois après le premier lancement d'une carrière (hors écran/tests :
  auto-affichage désactivé).
- Quatre étapes suivies en base :
  1. composer le cinq ;
  2. choisir une causerie avant-match ;
  3. jouer le premier match ;
  4. repérer une recrue au mercato.
- Boutons directs TACTIQUES / MATCH / MERCATO, **PLUS TARD** et **NE PLUS
  AFFICHER**. L'auto-affichage s'arrête après 3 matchs de championnat.
- `tests/test_onboarding.py` : 4 étapes, causerie/mercato marqués, pas
  d'auto-affichage en mode test.

### VALIDATION
- Suite complète : **97 suites PASS, 0 FAIL** · `RESULT : ALL OK` ·
  `data/error.log` **0 octet**.

### CAPTURES
- `apercu_onboarding.png`, `apercu_rapport_bug.png`
- `apercu_avant_match.png`, `apercu_causerie.png`,
  `apercu_commentaire_live.png`, `apercu_vestiaire.png`,
  `apercu_conference_presse.png`


## Annexe HN - Audit moteur / equilibrage (07/11/2026)

### 1) PROTOCOLE
- Trois echantillons deterministes, hors ecran, sans toucher aux sauvegardes :
  1. **800 matchs** avec appariements aleatoires dans l'univers (comparaison
     avant/apres) ;
  2. **1200 matchs** stratifies (favoris, divisions, cartons, 10 m) ;
  3. **1320 matchs intra-division** (conditions reelles de championnat).
- Diagnostic supplementaire : distribution des fautes par equipe et des 10 m
  par match, grace a deux compteurs non intrusifs ajoutes a l'etat d'equipe
  (`fouls`, `ten_meter`).

### 2) CE QUE L'AUDIT A REVELE
- **Regle du 10 m incorrecte** : le compteur de fautes etait remis a zero au
  6e coup franc. Une mi-temps ne pouvait donc produire qu'un seul 10 m, alors
  que la regle futsal accorde un 10 m pour la 6e faute **et chacune des
  suivantes**.
- **Fautes trop dispersees** : jusqu'a 18 fautes pour une equipe dans un match,
  ce qui produisait des fins de mi-temps irrealistes.
- Le reste etait dans les clous : buts, avantage du terrain, cartons, favoris.

### 3) CORRECTIONS
- `match_engine.py` :
  - 10 m accorde a chaque faute a partir de la 6e de la mi-temps ;
  - le 10 m compte desormais comme une frappe (cadree si but ou arret) ;
  - frein de prudence : a partir de 5 fautes dans la mi-temps, la probabilite
    de faute est reduite (x0,65), comme une equipe qui evite le 10 m ;
  - compteurs `fouls` et `ten_meter` exposes pour les audits.
- `app.py` (match en direct) : meme frein de prudence, et le journal affiche
  desormais la bonne faute (« 7e faute cumulee », plus « 6e » a chaque fois).
- Aucun changement aux sauvegardes, a `data/active_save.txt` ou aux builds.

### 4) MESURES AVANT / APRES (800 matchs, meme protocole)
| Indicateur | Avant | Apres |
|---|---|---|
| Buts / match | 4,88 | 4,92 |
| 1X2 | 44,6 / 16,4 / 39,0 % | 45,5 / 15,6 / 38,9 % |
| Tirs (cadres) | 33,1 (17,0) | 33,8 (17,5) |
| Arrets / corners | 12,5 / 4,4 | 12,8 / 4,4 |
| Cartons (rouges) | 3,58 (0,21) | 3,45 (0,21) |
| Buts sur 10 m | 0,14 | 0,19 |
| Clean sheets / 0-0 | 22,2 % / 0,8 % | 21,0 % / 0,9 % |
| Matchs a 8 buts et + | 12,5 % | 13,1 % |

### 5) MESURES INTRADIVISION (1320 matchs, conditions de championnat)
- **4,69 buts/match**, 33,8 tirs, 45,6 / 18,6 / 35,8 % (domicile/nul/exterieur).
- Par division : 4,46 a 5,01 buts/match ; ecart domicile/extérieur stable.
- **11,7 fautes/match** (5,9 par equipe), **3,35 cartons** (3,16 jaunes,
  0,19 rouge).
- **10 m : 0,80 tir/match**, 0,196 but, **24,6 % de conversion**, et 35,8 % des
  matchs avec au moins un 10 m.
- 18,1 % de clean sheets, 0,6 % de 0-0, 9,5 % de matchs a 8 buts et plus.
- Favoris (reputation) : +20 -> 79,2 % de victoires a domicile ; +10 a 19 ->
  64,2 % ; equilibre -> 47,9 / 15,7 / 36,4 % ; outsider -20 -> 20,5 %.
- Le taux de nuls global plus bas (15,6 %) vient des appariements aleatoires
  entre divisions ; en conditions reelles (intra-division) il remonte a 18,6 %.

### 6) TEST DE REGRESSION
- Nouveau `tests/test_engine_balance.py` (2 s, sans base de donnees) :
  1. buts/match, 1X2, tirs, arrets, clean sheets, 0-0, matchs a 8 buts ;
  2. fautes, cartons, rouges ;
  3. 10 m avec profil discipline ;
  4. profil agressif : plusieurs 10 m dans une mi-temps possible (max >= 3),
     conversion et coherence fautes/10 m ;
  5. favori nettement superieur : victoires et exploits bornes ;
  6. determinisme du score, des tirs, des fautes et des buteurs.
- Ajoute a `tests/run_tests.py` (98 suites).

### 7) VALIDATION
- Suite complete : **98 suites PASS, 0 FAIL** - `RESULT : ALL OK` -
  `data/error.log` **0 octet** (554 s).
- `test_balance_soak.py` (saison complete) : 599 matchs simules,
  4,68 buts/match, 0 erreur.
- Aucun `.exe` reconstruit.

