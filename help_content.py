# -*- coding: utf-8 -*-
"""Contenu de l'aide du jeu : themes, sujets, mots-cles et articles HTML.

Le panneau AIDE des Options construit automatiquement son sommaire a partir de
ces donnees. Chaque article peut renvoyer vers un autre sujet avec un lien
`topic:identifiant` (navigation interne, sans quitter la fenetre).
"""

HELP_THEMES = [
    ("demarrage", "Démarrage", "Lancer, créer et reprendre une carrière."),
    ("direction", "Direction sportive", "Board, objectifs, messagerie et décisions."),
    ("effectif", "Effectif", "Joueurs, contrats, évaluation et départs."),
    ("tactiques", "Tactiques & match", "Composer, consignes et match en direct."),
    ("entrainement", "Entraînement & staff", "Progression, staff et centre de formation."),
    ("mercato", "Transferts", "Marché, négociations, prêts et clubs IA."),
    ("finances", "Finances & complexe", "Trésorerie, sponsors, infrastructure."),
    ("competitions", "Compétitions", "Calendrier, classements, coupe et archives."),
    ("interface", "Interface & aide", "Options, navigation, dépannage et glossaire."),
]

HELP_TOPICS = [
    {
        "id": "vue-ensemble",
        "theme": "demarrage",
        "title": "Vue d'ensemble : la boucle de jeu",
        "keywords": "but objectif boucle avancer continuer carriere saison match message entrainement",
        "html": """
        <h2>La boucle de jeu</h2>
        <p>Futsal Manager se joue par <b>journées</b>. Le bouton d'avancement fait défiler le calendrier
        jusqu'au prochain événement important : un match, un message, une offre, une fin de chantier ou
        une décision du board.</p>
        <h3>Le rythme d'une saison</h3>
        <ul>
          <li><b>Pré-saison</b> : effectif, amicaux, entraînement, mercato et préparation tactique.</li>
          <li><b>Championnat</b> : une journée à la fois, avec classement et rapports de match.</li>
          <li><b>Coupe</b> : tours à élimination directe, en parallèle du championnat.</li>
          <li><b>Clôture</b> : bilan, montées/descentes, fin de contrats, nouvelle saison.</li>
        </ul>
        <h3>Les trois réflexes</h3>
        <ol>
          <li>Vérifier la <b>Direction sportive</b> : board, prochain match, alertes.</li>
          <li>Préparer l'<b>Effectif</b> et les <b>Tactiques</b> avant la journée.</li>
          <li>Lire la <b>Messagerie</b> : offres, blessures, contrats et rapports.</li>
        </ol>
        <div class="tip">Tu peux avancer sans ouvrir chaque page : le jeu s'arrête de lui-même sur les
        décisions qui demandent une réponse.</div>
        <p class="see">Voir aussi : <a href="topic:carriere">Créer une carrière</a> ·
        <a href="topic:direction">Direction sportive</a> ·
        <a href="topic:calendrier">Calendrier</a></p>
        """,
    },
    {
        "id": "carriere",
        "theme": "demarrage",
        "title": "Créer, reprendre ou charger une carrière",
        "keywords": "nouvelle carriere reprendre charger sauvegarde club nom couleurs division difficulte",
        "html": """
        <h2>Démarrer une carrière</h2>
        <p>Depuis l'écran de démarrage :</p>
        <ul>
          <li><b>NOUVELLE CARRIÈRE</b> : choisis le nom du club, les couleurs, l'écusson, le maillot,
          la division et la difficulté. L'univers (6 divisions, clubs IA, calendrier) est généré
          automatiquement.</li>
          <li><b>REPRENDRE</b> : recharge la dernière carrière active, celle affichée dans la fiche
          de gauche.</li>
          <li><b>CHARGER</b> : ouvre la liste complète des sauvegardes.</li>
          <li><b>SAUVEGARDES</b> : renommer, exporter ou supprimer une sauvegarde.</li>
        </ul>
        <h3>Choisir la difficulté</h3>
        <p><b>Normale</b> donne un budget et un effectif équilibrés. <b>Difficile</b> réduit les moyens,
        renforce l'exigence du board et rend les clubs IA plus agressifs sur le marché.</p>
        <h3>Après la création</h3>
        <p>Tu arrives sur la <b>Direction sportive</b>. Le club possède déjà un effectif, un staff de
        départ, des installations et un calendrier. La première décision consiste souvent à compléter
        le cinq et à vérifier les contrats.</p>
        <div class="tip">Le nom et les couleurs du club restent modifiables dans les options
        (motif du maillot) et dans les écrans d'identité.</div>
        <p class="see">Voir aussi : <a href="topic:sauvegardes">Sauvegardes</a> ·
        <a href="topic:options">Options</a> · <a href="topic:effectif">Effectif</a></p>
        """,
    },
    {
        "id": "sauvegardes",
        "theme": "demarrage",
        "title": "Sauvegardes et sécurité",
        "keywords": "sauvegarde charger exporter renommer supprimer fichier db active save perte",
        "html": """
        <h2>Sauvegardes</h2>
        <p>Chaque carrière est un fichier de base de données locale. Le jeu enregistre les décisions
        au fil de la partie ; il est conseillé de garder plusieurs sauvegardes aux moments clés
        (avant un mercato, avant une fin de saison).</p>
        <h3>Gérer les sauvegardes</h3>
        <ul>
          <li><b>CHARGER</b> : sélectionne une sauvegarde et ouvre la carrière.</li>
          <li><b>SAUVEGARDES</b> : renomme, exporte ou supprime une sauvegarde.</li>
          <li>La fiche de l'écran de démarrage indique la dernière sauvegarde active.</li>
        </ul>
        <h3>Bonnes pratiques</h3>
        <ul>
          <li>Ne modifie pas les fichiers de sauvegarde à la main.</li>
          <li>Ne supprime pas le dossier des sauvegardes pendant que le jeu tourne.</li>
          <li>En cas de doute, exporte une copie avant une décision importante.</li>
        </ul>
        <div class="warn">Le jeu ne réécrit jamais une sauvegarde utilisateur pendant les tests.
        Les sauvegardes de test sont créées dans un dossier temporaire.</div>
        <p class="see">Voir aussi : <a href="topic:depannage">Dépannage</a> ·
        <a href="topic:carriere">Créer une carrière</a></p>
        """,
    },
    {
        "id": "direction",
        "theme": "direction",
        "title": "Direction sportive et board",
        "keywords": "board objectif classement finances jeunes confiance licenciement offre carriere",
        "html": """
        <h2>La Direction sportive</h2>
        <p>C'est le tableau de bord du club. On y trouve le prochain match, le classement, les objectifs
        du board, les jauges de confiance, le palmarès, les records et les raccourcis vers les écrans
        utiles.</p>
        <h3>Objectifs du board</h3>
        <ul>
          <li><b>Classement</b> : une ambition (Titre, Montée, Haut de tableau, Milieu de tableau,
          Maintien) et un rang cible.</li>
          <li><b>Finances</b> : trésorerie positive et respect du plafond de masse salariale.</li>
          <li><b>Jeunes</b> : nombre de joueurs de 21 ans ou moins réellement utilisés.</li>
        </ul>
        <p>La confiance évolue avec les résultats, la santé financière, les jeunes et la différence
        victoires/défaites. Trop basse, elle déclenche un avertissement puis un risque de licenciement
        en fin de saison.</p>
        <h3>Décisions de carrière</h3>
        <p>Des clubs peuvent proposer un poste d'entraîneur. Une offre peut être acceptée ou refusée ;
        changer de club remet à zéro les objectifs du board et l'effectif à disposition.</p>
        <div class="tip">Les clubs IA ont aussi un projet : ambition, objectif, entraîneur et besoins.
        Consulte leur fiche club pour comprendre leurs offres.</div>
        <p class="see">Voir aussi : <a href="topic:clubs-ia">Clubs IA</a> ·
        <a href="topic:finances">Finances</a> · <a href="topic:messages">Messagerie</a></p>
        """,
    },
    {
        "id": "messages",
        "theme": "direction",
        "title": "Messagerie et décisions",
        "keywords": "message courrier offre accepter refuser contre-offre archive presse filtre lu supprimer",
        "html": """
        <h2>La messagerie</h2>
        <p>Toutes les décisions qui demandent une réponse arrivent ici : offres de transfert, contrats,
        prêts, blessures, rapports de match, avertissements du board et nouvelles du monde.</p>
        <h3>Lire et agir</h3>
        <ul>
          <li>Clique un message pour l'ouvrir dans le panneau de lecture.</li>
          <li>Les boutons <b>ACCEPTER / SIGNER</b>, <b>REFUSER</b> et <b>FAIRE UNE CONTRE-OFFRE</b>
          répondent directement quand le message le permet.</li>
          <li><b>TOUT MARQUER LU</b> nettoie les pastilles sans supprimer le contenu.</li>
          <li><b>TOUT SUPPRIMER</b> efface définitivement les messages affichés.</li>
          <li><b>HISTORIQUE</b> retrouve les messages archivés.</li>
        </ul>
        <h3>Recherche et filtres</h3>
        <p>Le centre de courrier propose des familles de messages : Tout, Non lus, À traiter,
        Dossiers (transferts, contrats, prêts), Scouting, Matchs, Club, Saison, Presse et Système.
        Chaque pastille affiche son compteur.</p>
        <p>La barre de recherche filtre par message, joueur ou club. Le tri peut être chronologique
        (récents ou anciens) ou prioritaire (messages à traiter et non lus d'abord).</p>
        <p>Les options de messagerie permettent de choisir les familles visibles, de couper les
        anniversaires, les performances, les blessures, les rappels d'offres ou la presse, et de
        décider si un message est marqué lu à l'ouverture.</p>
        <div class="tip">Une offre non répondue finit par expirer. Garde un œil sur les messages marqués
        d'une échéance.</div>
        <p class="see">Voir aussi : <a href="topic:negociation">Négociation</a> ·
        <a href="topic:options">Options de messagerie</a></p>
        """,
    },
    {
        "id": "effectif",
        "theme": "effectif",
        "title": "Gérer l'effectif",
        "keywords": "effectif joueur colonne tri recherche contrat moral forme blessure numero consigne",
        "html": """
        <h2>L'effectif</h2>
        <p>L'écran Effectif liste tous les joueurs sous contrat : poste, âge, niveau, forme, moral,
        salaire, valeur, contrat et statistiques. Il sert à préparer le cinq et à repérer les urgences.</p>
        <h3>Actions courantes</h3>
        <ul>
          <li><b>Rechercher</b> : nom, nationalité, poste.</li>
          <li><b>COLONNES</b> : choisir les colonnes affichées et leur ordre ; le réglage est mémorisé.</li>
          <li><b>FICHE</b> : ouvre le profil complet d'un joueur.</li>
          <li><b>BRIEF ÉQUIPE</b> : petit gain de moral pour le groupe.</li>
          <li><b>RÉCUP</b> et <b>KINÉ</b> : récupération de forme ou soins selon le staff et le budget.</li>
        </ul>
        <h3>Comprendre les indicateurs</h3>
        <ul>
          <li><b>Niveau /20</b> : qualité globale estimée du joueur.</li>
          <li><b>Forme</b> : condition physique ; basse, elle réduit les performances et augmente
          le risque de blessure.</li>
          <li><b>Moral</b> : influe sur la constance et les négociations de contrat.</li>
          <li><b>Contrat</b> : années restantes ; à zéro, le joueur peut partir libre.</li>
        </ul>
        <div class="warn">Un effectif sous le minimum est complété automatiquement, mais dans l'urgence
        et parfois avec des joueurs de complément.</div>
        <p class="see">Voir aussi : <a href="topic:fiche-joueur">Fiche joueur</a> ·
        <a href="topic:contrats">Contrats</a> · <a href="topic:tactiques">Tactiques</a></p>
        """,
    },
    {
        "id": "fiche-joueur",
        "theme": "effectif",
        "title": "Fiche joueur et évaluation",
        "keywords": "fiche joueur attribut potentiel scouting note historique statistique comparer",
        "html": """
        <h2>La fiche joueur</h2>
        <p>Elle rassemble l'identité, le poste, l'âge, le niveau, le potentiel, les attributs, le contrat,
        la valeur, la forme, le moral et l'historique de carrière.</p>
        <h3>Attributs</h3>
        <p>Technique, passe, finition, défense, gardien, endurance, dribble, vitesse et placement.
        Le <b>niveau /20</b> est une synthèse pondérée selon le poste.</p>
        <h3>Potentiel et progression</h3>
        <p>Le potentiel est fixé à la création du joueur. Un jeune peut encore progresser ; un joueur
        âgé décline. Le temps de jeu, l'entraînement et le staff accélèrent ou freinent la courbe.</p>
        <h3>Scouting</h3>
        <p>Pour un joueur extérieur, les attributs peuvent être partiellement masqués. Un rapport
        <b>express</b> est rapide et moins fiable ; un rapport <b>approfondi</b> coûte plus cher mais
        révèle mieux le joueur. La shortlist suit l'évolution de la valeur.</p>
        <div class="tip">Compare toujours le poste réel, l'âge, le salaire et la durée de contrat avant
        de te fier au seul niveau affiché.</div>
        <p class="see">Voir aussi : <a href="topic:mercato">Marché</a> ·
        <a href="topic:entrainement">Entraînement</a></p>
        """,
    },
    {
        "id": "contrats",
        "theme": "effectif",
        "title": "Contrats, salaires et départs",
        "keywords": "contrat salaire renouveler prolongation precontrat libre fin de contrat plafond masse salariale",
        "html": """
        <h2>Contrats et salaires</h2>
        <p>Un joueur coûte son salaire chaque mois et peut partir libre à la fin de son contrat.
        Anticipe les échéances : un départ non remplacé affaiblit l'effectif.</p>
        <h3>Renouveler</h3>
        <ul>
          <li>Ouvre la fiche joueur ou l'écran des contrats.</li>
          <li>Propose une durée et un salaire ; le joueur peut refuser ou demander mieux.</li>
          <li>Le moral, le temps de jeu et le projet du club influencent la réponse.</li>
        </ul>
        <h3>Pré-contrats et joueurs libres</h3>
        <p>Un joueur en fin de contrat peut signer un pré-contrat ailleurs. Les joueurs libres peuvent
        être recrutés hors période de transfert, avec un salaire et une durée à négocier.</p>
        <h3>Plafond de masse salariale</h3>
        <p>Le club doit respecter un plafond qui additionne les salaires des joueurs et du staff.
        Un dépassement bloque certaines signatures et inquiète le board.</p>
        <div class="warn">Vérifie toujours le coût total : salaire mensuel, prime éventuelle et
        conséquences sur le plafond.</div>
        <p class="see">Voir aussi : <a href="topic:finances">Finances</a> ·
        <a href="topic:effectif">Effectif</a></p>
        """,
    },
    {
        "id": "tactiques",
        "theme": "tactiques",
        "title": "Composer et choisir une tactique",
        "keywords": "tactique composition cinq terrain banc glisser deposer formation auto composer vider",
        "html": """
        <h2>L'écran Tactiques</h2>
        <p>Le futsal se joue à cinq : un gardien et quatre joueurs de champ. L'écran permet de placer
        les titulaires, de choisir un plan et de préparer les consignes.</p>
        <h3>Composer</h3>
        <ul>
          <li>Glisse un joueur du banc vers une zone du terrain.</li>
          <li><b>COMPOSER AUTO</b> choisit le meilleur cinq disponible selon le poste et la forme.</li>
          <li><b>VIDER LE TERRAIN</b> remet la composition à zéro.</li>
          <li><b>ENREGISTRER</b> conserve la composition et les réglages.</li>
        </ul>
        <h3>Plans et réglages</h3>
        <p>Les plans (2-2, 3-1, 4-0) changent l'équilibre entre défense et attaque. Le pressing,
        le tempo et la participation défensive modifient le comportement collectif.</p>
        <p>La <b>familiarité tactique</b> progresse avec les matchs et l'entraînement : un plan
        nouvellement choisi est moins bien exécuté au début.</p>
        <div class="tip">Un joueur hors de son poste perd de l'efficacité. Utilise les postes naturels
        autant que possible.</div>
        <p class="see">Voir aussi : <a href="topic:consignes">Consignes</a> ·
        <a href="topic:match">Centre de match</a></p>
        """,
    },
    {
        "id": "consignes",
        "theme": "tactiques",
        "title": "Consignes, coups de pied et familiarité",
        "keywords": "consigne individuelle role pressing coup franc corner sortie powerplay familiarite",
        "html": """
        <h2>Consignes et coups de pied arrêtés</h2>
        <p>Le bouton <b>CONSIGNES & COUPS DE PIED</b> ouvre les réglages fins :</p>
        <ul>
          <li><b>Rôles individuels</b> : montée en puissance, dribbles, passes, pressing, etc.</li>
          <li><b>Participation défensive</b> : qui reste derrière, qui monte.</li>
          <li><b>Coups de pied arrêtés</b> : corner, coup franc, sortie de balle, powerplay.</li>
        </ul>
        <p>Chaque consigne a un effet réel dans le moteur : plus de tirs, plus de dribbles, plus de
        sécurité défensive, mais aussi plus de fatigue ou de fautes selon le choix.</p>
        <h3>Familiarité</h3>
        <p>Les réglages avancés sont moins efficaces s'ils changent sans cesse. La familiarité monte
        avec la répétition et l'entraînement tactique.</p>
        <div class="tip">En fin de match, une consigne très offensive peut aider à égaliser — mais
        expose la défense.</div>
        <p class="see">Voir aussi : <a href="topic:tactiques">Composer</a> ·
        <a href="topic:entrainement">Entraînement</a></p>
        """,
    },
    {
        "id": "match",
        "theme": "tactiques",
        "title": "Centre de match et match en direct",
        "keywords": "match direct mi-temps remplacement finir rapport vingt secondes chrono note homme du match",
        "html": """
        <h2>Le Centre de match</h2>
        <p>Le match se joue en <b>2 × 20 minutes effectives</b>. Le chrono se bloque à la mi-temps
        pour permettre les changements et les consignes.</p>
        <h3>Commandes</h3>
        <ul>
          <li><b>VALIDER LE CINQ</b> : confirme la composition avant le coup d'envoi.</li>
          <li><b>REPRENDRE</b> : relance le direct après une pause.</li>
          <li><b>+ 20 SECONDES</b> : simule une courte séquence.</li>
          <li><b>REMPLACEMENT</b> : ouvre le choix des changements.</li>
          <li><b>FINIR</b> : simule instantanément le reste du match.</li>
          <li><b>RAPPORT DU MATCH</b> : rouvre le dernier compte-rendu.</li>
        </ul>
        <h3>Pendant le match</h3>
        <p>Le fil du match raconte les buts, arrêts, fautes, cartons et blessures. L'onglet
        <b>ÉQUIPES EN DIRECT</b> montre les statistiques et les notes. Les consignes peuvent être
        appliquées en cours de rencontre.</p>
        <p>Après le coup de sifflet, le rapport détaille possession, tirs, arrêts, fautes, notes et
        homme du match.</p>
        <div class="warn">Un match en direct verrouille les autres menus : termine-le ou reviens au
        centre de match avant de naviguer.</div>
        <p class="see">Voir aussi : <a href="topic:tactiques">Tactiques</a> ·
        <a href="topic:calendrier">Calendrier</a></p>
        """,
    },
    {
        "id": "entrainement",
        "theme": "entrainement",
        "title": "Entraînement et progression",
        "keywords": "entrainement semaine intensite seance auto completer individuel focus progression fatigue blessure",
        "html": """
        <h2>Entraînement</h2>
        <p>L'écran Entraînement sert à construire la semaine : choisir les séances, doser l'intensité
        et préserver la forme avant le match.</p>
        <h3>Onglets</h3>
        <ul>
          <li><b>2 SEMAINES</b> : le calendrier des séances et des matchs ; clique un jour pour l'éditer.</li>
          <li><b>INDIVIDUEL</b> : un attribut prioritaire par joueur, en plus du plan collectif.</li>
          <li><b>PROGRESSION</b> : le niveau de chacun par rapport à son potentiel.</li>
        </ul>
        <h3>INDIVIDUEL : FOCUS ou AUTO</h3>
        <p>Chaque joueur a <b>un</b> attribut prioritaire. Deux états possibles :</p>
        <ul>
          <li><b>FOCUS</b> (violet) : tu as choisi l'attribut (Technique, Passe, Finition, Défense,
          Physique, Vitesse, Dribble, Placement, Gardien). Il pèse <b>×2,2</b> dans la séance,
          en plus du plan collectif.</li>
          <li><b>AUTO</b> (vert) : l'attribut prioritaire du poste est appliqué sans intervention
          (gardien → arrêts, défenseur → défense, ailier → technique, pivot → finition).</li>
        </ul>
        <p>La pastille <b>PLAFOND</b> signale un joueur qui a atteint son potentiel : il ne gagnera
        plus de points, inutile d'insister. Les boutons <b>AUTO PAR POSTE</b> et <b>TOUT EN AUTO</b>
        règlent tout l'effectif en un clic. Le filtre de droite isole les focus manuels, les joueurs
        en auto, ceux qui plafonnent ou ceux qui n'ont rien gagné sur 30 jours.</p>
        <h3>PROGRESSION : lire une carte</h3>
        <ul>
          <li><b>NIVEAU 12 / 16</b> : la barre se remplit du niveau actuel vers le potentiel
          (le plafond). Plus la barre est pleine, plus le joueur approche de son maximum.</li>
          <li><b>+3 PTS</b> et les pastilles <b>TEC +2, PAS +1…</b> : les points d'attribut gagnés
          depuis le début de saison (vert = gain).</li>
          <li><b>EN HAUSSE</b> : a progressé ; <b>STABLE</b> : aucun gain ; <b>PLAFOND</b> :
          potentiel atteint.</li>
          <li><b>INFO</b> : date de la dernière progression et marge restante avant le plafond.</li>
        </ul>
        <p>Le filtre <b>Tous / En progression / Plafond atteint / Sans évolution</b> trie les cartes
        pour repérer immédiatement qui travaille et qui stagne.</p>
        <div class="tip">Un joueur qui stagne alors qu'il a de la marge : vérifie qu'une séance est
        bien programmée, que son focus correspond à un attribut utile, et qu'il n'est pas fatigué
        (forme basse = progression plus lente).</div>
        <h3>Modèles de semaine</h3>
        <p>Le sélecteur propose quatre modèles : <b>Semaine de match</b>, <b>Développement</b>,
        <b>Récupération</b> et <b>Bloc intensif</b>. Le modèle match se cale automatiquement sur la
        date du prochain rendez-vous : charge en début de semaine, activation la veille, repos le
        jour du match.</p>
        <h3>Charge et contexte</h3>
        <p>La page affiche le prochain match, le préparateur, la charge de la semaine et la forme
        moyenne. La charge conseillée se situe autour de <b>55–80 %</b>. Une séance élevée trop proche
        du match déclenche un avertissement.</p>
        <p>Le <b>calendrier mensuel</b> affiche les matchs (domicile/extérieur, championnat ou amical)
        et les séances planifiées. Utilise PRÉCÉDENT / SUIVANT / AUJOURD'HUI pour changer de mois,
        puis clique un jour pour choisir l'atelier, l'intensité et enregistrer.</p>
        <h3>Intensité et risque</h3>
        <p>Une intensité élevée fait progresser plus vite mais fatigue et augmente le risque de
        blessure. <b>ENREGISTRER</b> valide le programme et applique la séance du jour.</p>
        <p>Le préparateur physique améliore la progression et peut planifier automatiquement les
        séances. L'adjoint accélère la récupération.</p>
        <div class="tip">Avant un match important, réduis la charge : une équipe fraîche vaut souvent
        mieux qu'un gain de progression marginal.</div>
        <p class="see">Voir aussi : <a href="topic:staff">Staff</a> ·
        <a href="topic:effectif">Effectif</a> · <a href="topic:formation">Formation</a></p>
        """,
    },
    {
        "id": "staff",
        "theme": "entrainement",
        "title": "Staff et effets réels",
        "keywords": "staff recruteur kine preparateur comptable directeur sportif adjoint marketing architecte embaucher former",
        "html": """
        <h2>Le staff</h2>
        <p>Huit postes peuvent être pourvus. Chaque employé a un niveau de 1 à 5 et un effet réel
        affiché avant l'embauche.</p>
        <ul>
          <li><b>Recruteur</b> : révèle les attributs et le potentiel via des rapports.</li>
          <li><b>Kiné</b> : soigne les blessures, avec un risque d'échec.</li>
          <li><b>Préparateur physique</b> : planifie l'entraînement et améliore la progression.</li>
          <li><b>Comptable</b> : optimise la trésorerie et la masse salariale du staff.</li>
          <li><b>Directeur sportif</b> : fait avancer l'observation de la shortlist.</li>
          <li><b>Adjoint</b> : accélère la récupération et aide la préparation tactique.</li>
          <li><b>Responsable marketing</b> : fait monter la réputation chaque semaine.</li>
          <li><b>Architecte</b> : réduit les coûts et délais des chantiers, ajoute une place de chantier.</li>
        </ul>
        <h3>Former un employé</h3>
        <p>Le bouton <b>FORMATION</b> lance une amélioration payante qui prend plusieurs jours.
        Un seul membre du staff peut être formé à la fois. Le niveau 5 est le maximum.</p>
        <div class="tip">Le salaire du staff compte dans le plafond de masse salariale : un employé
        très bien payé peut bloquer un recrutement de joueur.</div>
        <p class="see">Voir aussi : <a href="topic:finances">Finances</a> ·
        <a href="topic:entrainement">Entraînement</a></p>
        """,
    },
    {
        "id": "formation",
        "theme": "entrainement",
        "title": "Centre de formation et prêts",
        "keywords": "formation jeune centre academie note composante investir pepite pret progresser",
        "html": """
        <h2>Le centre de formation</h2>
        <p>Le centre produit des jeunes chaque saison. Sa note dépend des installations, du staff,
        du recruteur et des investissements.</p>
        <h3>Écran Centre de formation</h3>
        <ul>
          <li><b>Note du centre</b> : synthèse des composantes.</li>
          <li><b>Investir 50 000 €</b> : améliore le centre et la qualité des promotions futures.</li>
          <li><b>Jeunes du club</b> : liste des joueurs formés, avec âge, potentiel et progression.</li>
        </ul>
        <h3>Faire jouer un jeune</h3>
        <p>Un jeune progresse en jouant et en s'entraînant. Il peut être prêté pour gagner du temps
        de jeu ; le prêt peut inclure une option d'achat ou un retour programmé.</p>
        <div class="tip">Les pépites sont rares. Un jeune très bien noté mais sans temps de jeu
        stagne : prête-le plutôt que de le laisser sur le banc.</div>
        <p class="see">Voir aussi : <a href="topic:prets">Prêts</a> ·
        <a href="topic:entrainement">Entraînement</a></p>
        """,
    },
    {
        "id": "mercato",
        "theme": "mercato",
        "title": "Le marché des transferts",
        "keywords": "transfert marche recherche filtre shortlist scouting offre valeur salaire fenetre mercato",
        "html": """
        <h2>Le marché</h2>
        <p>L'écran Transferts regroupe la recherche de joueurs, les rapports de scouting, la shortlist,
        les offres envoyées et reçues, les prêts et l'historique.</p>
        <h3>Chercher un joueur</h3>
        <ul>
          <li>Filtre par nom, club, poste, âge, niveau ou valeur.</li>
          <li>Ouvre une fiche pour voir le détail et les rapports disponibles.</li>
          <li><b>SHORTLIST</b> épingle un joueur et suit sa valeur.</li>
        </ul>
        <h3>Scouting</h3>
        <p><b>EXPRESS</b> est rapide et moins fiable ; <b>APPROFONDIE</b> coûte plus cher mais donne
        une meilleure connaissance. Le recruteur et le directeur sportif accélèrent le travail.</p>
        <h3>Fenêtres de transfert</h3>
        <p>Les transferts payants se concentrent sur les périodes de marché. Les joueurs libres
        peuvent être signés plus librement, sous réserve du plafond salarial et de l'accord du joueur.</p>
        <div class="tip">Un joueur épinglé n'est pas réservé : un club IA peut le recruter avant toi.</div>
        <p class="see">Voir aussi : <a href="topic:negociation">Négociation</a> ·
        <a href="topic:prets">Prêts</a> · <a href="topic:clubs-ia">Clubs IA</a></p>
        """,
    },
    {
        "id": "negociation",
        "theme": "mercato",
        "title": "Négocier et conclure un transfert",
        "keywords": "offre negociation contre-offre salaire duree prime accepte refuse offre recue envoyer",
        "html": """
        <h2>Négocier</h2>
        <p>Une offre se compose généralement d'une indemnité de transfert, d'un salaire et d'une durée
        de contrat. Le club vendeur et le joueur peuvent réagir séparément.</p>
        <h3>Envoyer une offre</h3>
        <ol>
          <li>Ouvre la fiche du joueur puis <b>ENVOYER L'OFFRE</b>.</li>
          <li>Renseigne l'indemnité, le salaire et la durée.</li>
          <li>Suis la réponse dans la messagerie ou l'onglet <b>OFFRES</b>.</li>
        </ol>
        <h3>Répondre à une offre</h3>
        <ul>
          <li><b>ACCEPTER</b> : valide la vente ou la signature.</li>
          <li><b>REFUSER</b> : clôt le dossier.</li>
          <li><b>CONTRE-OFFRE</b> : demande un montant ou un salaire plus élevé.</li>
        </ul>
        <div class="warn">Une offre acceptée peut être refusée par le joueur si le salaire ou le projet
        ne lui convient pas. Vérifie le coût total et le plafond avant de confirmer.</div>
        <p class="see">Voir aussi : <a href="topic:mercato">Marché</a> ·
        <a href="topic:contrats">Contrats</a> · <a href="topic:messages">Messagerie</a></p>
        """,
    },
    {
        "id": "prets",
        "theme": "mercato",
        "title": "Prêts entrants et sortants",
        "keywords": "pret preter rappeler fin de pret option achat jeune salaire retour",
        "html": """
        <h2>Les prêts</h2>
        <p>Un prêt permet de faire venir un joueur sans transfert définitif, ou d'envoyer un jeune
        gagner du temps de jeu ailleurs.</p>
        <h3>Prêt entrant</h3>
        <ul>
          <li>Le club d'origine reste propriétaire du joueur.</li>
          <li>Le salaire peut être partagé selon l'accord.</li>
          <li>Le joueur revient automatiquement à la fin du prêt.</li>
        </ul>
        <h3>Prêt sortant</h3>
        <p>Depuis l'onglet <b>PRÊTS</b>, sélectionne un jeune puis <b>PRÊTER UN JEUNE</b>. Tu peux
        suivre son temps de jeu, le rappeler ou mettre fin au prêt.</p>
        <div class="tip">Un prêt réussi fait progresser le jeune et peut augmenter sa valeur.
        Un prêt sans temps de jeu ne sert à rien.</div>
        <p class="see">Voir aussi : <a href="topic:formation">Formation</a> ·
        <a href="topic:mercato">Marché</a></p>
        """,
    },
    {
        "id": "clubs-ia",
        "theme": "mercato",
        "title": "Clubs IA : projets, besoins et rumeurs",
        "keywords": "club ia projet ambition objectif entraineur patience besoin rumeur offre cible identite anime prudent",
        "html": """
        <h2>Les clubs IA</h2>
        <p>Chaque club adversaire possède une identité stable (Formateur, Riche, Spectacle, Économe,
        Bâtisseur, Opportuniste, Guerrier) et un projet de saison.</p>
        <h3>Le projet</h3>
        <ul>
          <li><b>Ambition</b> : Titre, Montée, Haut de tableau, Milieu de tableau ou Maintien.</li>
          <li><b>Objectif</b> : un rang cible dans sa division.</li>
          <li><b>Entraîneur</b> : un nom et un style ; il peut être remplacé si l'objectif est manqué.</li>
          <li><b>Dynamique</b> : Animé, Équilibré ou Prudent.</li>
          <li><b>Besoins</b> : postes à renforcer, âge, niveau, fins de contrat.</li>
        </ul>
        <p>La fiche d'un club IA affiche ce projet. Un club Animé prospecte plus vite et dépense plus
        qu'un club Prudent, qui attend une bonne affaire.</p>
        <h3>Offres et rumeurs</h3>
        <p>Les offres reçues pour tes joueurs sont pondérées par le besoin réel du club. Le message
        indique le projet de l'acheteur. Des rumeurs peuvent aussi signaler qu'un club surveille un
        joueur à un poste précis, sans offre immédiate.</p>
        <div class="tip">Si un club a un besoin Haute à un poste, son offre sera plus probable et
        souvent plus généreuse.</div>
        <p class="see">Voir aussi : <a href="topic:direction">Direction sportive</a> ·
        <a href="topic:negociation">Négociation</a></p>
        """,
    },
    {
        "id": "finances",
        "theme": "finances",
        "title": "Finances du club",
        "keywords": "finance tresorerie budget revenu charge salaire sponsor pret bancaire prime plafond",
        "html": """
        <h2>Finances</h2>
        <p>L'écran Finances suit la trésorerie, les revenus, les charges et la santé du club.</p>
        <h3>Revenus</h3>
        <ul>
          <li>Billetterie et recettes du match (selon affluence et tarif).</li>
          <li>Sponsors et contrats commerciaux.</li>
          <li>Dotations de championnat et primes de classement.</li>
          <li>Services du complexe : bar, loge VIP, boutique, locations, événements.</li>
        </ul>
        <h3>Charges</h3>
        <ul>
          <li>Salaires des joueurs et du staff.</li>
          <li>Entretien des installations.</li>
          <li>Remboursement du prêt bancaire.</li>
        </ul>
        <h3>Prêt et sponsors</h3>
        <p>L'onglet <b>PRÊT BANCAIRE</b> permet d'emprunter ou de rembourser par anticipation.
        L'onglet <b>SPONSORS</b> permet de négocier un contrat. Un endettement excessif inquiète
        le board et peut bloquer des recrutements.</p>
        <div class="warn">Le plafond de masse salariale additionne joueurs et staff. Une signature
        peut être refusée même si la trésorerie semble suffisante.</div>
        <p class="see">Voir aussi : <a href="topic:contrats">Contrats</a> ·
        <a href="topic:infrastructure">Infrastructure</a> · <a href="topic:staff">Staff</a></p>
        """,
    },
    {
        "id": "infrastructure",
        "theme": "finances",
        "title": "Infrastructure et exploitation",
        "keywords": "infrastructure complexe tribune eclairage parking medical formation marketing chantier architecte tarif affluence bar vip boutique",
        "html": """
        <h2>Le complexe</h2>
        <p>L'écran Infrastructure se divise en trois onglets : <b>VUE D'ENSEMBLE</b>,
        <b>GESTION</b> et <b>EXPLOITATION</b>.</p>
        <h3>Vue d'ensemble</h3>
        <p>Vue intérieure ou extérieure du complexe, capacité, affluence estimée, recette du match
        et niveau des tribunes.</p>
        <h3>Gestion</h3>
        <p>Chaque carte est un chantier : tribunes, éclairage, parking, médical, formation,
        marketing, bar, loge VIP, boutique, terrains, événements, fan zone.</p>
        <ul>
          <li>Paie le coût, attends la durée, l'effet s'applique à la livraison.</li>
          <li>Un chantier par bâtiment ; l'architecte ajoute des places simultanées.</li>
          <li>Les niveaux augmentent la capacité, le confort ou les revenus.</li>
        </ul>
        <h3>Exploitation</h3>
        <p>Règle le <b>prix du match</b> et la stratégie (affluence, équilibré, recettes). Un tarif
        trop élevé vide les tribunes ; un tarif trop bas remplit la salle mais rapporte moins.
        Le bouton <b>CONSEIL</b> propose un tarif adapté.</p>
        <div class="tip">Les services (bar, VIP, boutique) rapportent même sans match : ils lissent
        les finances du club.</div>
        <p class="see">Voir aussi : <a href="topic:finances">Finances</a> ·
        <a href="topic:staff">Architecte</a></p>
        """,
    },
    {
        "id": "calendrier",
        "theme": "competitions",
        "title": "Calendrier et avancement",
        "keywords": "calendrier journee date match amical programmer rapport recent avancer continuer",
        "html": """
        <h2>Le calendrier</h2>
        <p>Le calendrier affiche les journées de championnat, les amicaux, la coupe et les rapports
        de match.</p>
        <h3>Avancer</h3>
        <p>Le bouton principal avance jusqu'au prochain événement : match, message, fin de chantier
        ou décision. Tu peux aussi consulter une journée et ouvrir son rapport.</p>
        <h3>Amicaux</h3>
        <p>En pré-saison, <b>PROGRAMMER L'AMICAL</b> ajoute une rencontre de préparation. Les amicaux
        font progresser la familiarité tactique et la forme, sans points de championnat.</p>
        <h3>Rapports</h3>
        <p>Chaque match joué conserve un compte-rendu : score, statistiques, notes et homme du match.
        Le bouton <b>RAPPORT RÉCENT</b> rouvre le dernier.</p>
        <div class="tip">Un match en direct verrouille la navigation : termine-le avant de changer
        d'écran.</div>
        <p class="see">Voir aussi : <a href="topic:match">Centre de match</a> ·
        <a href="topic:competitions">Compétitions</a></p>
        """,
    },
    {
        "id": "competitions",
        "theme": "competitions",
        "title": "Compétitions, coupe et archives",
        "keywords": "competition classement championnat coupe statistique historique palmares archive champion montee descente",
        "html": """
        <h2>Compétitions</h2>
        <p>L'écran Compétitions regroupe cinq onglets : <b>CHAMPIONNAT</b>, <b>COUPE</b>,
        <b>STATISTIQUES</b>, <b>HISTORIQUE</b> et <b>PALMARÈS</b>.</p>
        <h3>Championnat</h3>
        <p>Classement complet de la division, forme récente, différence de buts et points. Clique
        un club pour ouvrir sa fiche.</p>
        <h3>Coupe</h3>
        <p>Tableau à élimination directe. Les confrontations se jouent aux dates prévues ; un clic
        sur une affiche ouvre la fiche du club concerné.</p>
        <h3>Statistiques et archives</h3>
        <p>Meilleurs buteurs, passeurs, gardiens et notes. L'historique conserve les classements
        finaux saison par saison ; le palmarès grave les titres, montées et descentes.</p>
        <div class="tip">Les clubs IA ont aussi un palmarès : une fiche club permet de voir leur
        histoire et leur projet actuel.</div>
        <p class="see">Voir aussi : <a href="topic:calendrier">Calendrier</a> ·
        <a href="topic:clubs-ia">Clubs IA</a></p>
        """,
    },
    {
        "id": "options",
        "theme": "interface",
        "title": "Options et confort de jeu",
        "keywords": "option theme taille texte fenetre plein ecran difficulte messagerie maillot triche aide",
        "html": """
        <h2>Options</h2>
        <p>La fenêtre Options se compose de quatre onglets : <b>APPARENCE</b>, <b>MESSAGERIE</b>,
        <b>TRICHE</b> et <b>AIDE</b>.</p>
        <h3>Apparence</h3>
        <ul>
          <li><b>Thème</b> : Nuit violette, Vert futsal ou Noir & or.</li>
          <li><b>Taille du texte</b> : de 9 à 16 points, appliquée immédiatement.</li>
          <li><b>Mode de fenêtre</b> : fenêtré, maximisé ou plein écran.</li>
          <li><b>Difficulté</b> : Normale ou Difficile.</li>
          <li><b>Maillot du club</b> : rayures, bandes, écharpe, damier ou dégradé.</li>
        </ul>
        <h3>Messagerie</h3>
        <p>Choisis la cadence du brief et les catégories de messages reçus : anniversaires,
        performances, blessures, staff, rappels d'offres, fins de contrat et presse.</p>
        <p>Les <b>familles de messages</b> permettent de masquer ou d'afficher les dossiers,
        le scouting, les matchs, la vie du club, les bilans de saison et le système. L'option
        <b>Marquer comme lu à l'ouverture</b> laisse un message non lu si elle est décochée.</p>
        <h3>Triche</h3>
        <p>Des coups de pouce immédiats : argent, condition ou moral. Ils s'appliquent sans sanction
        du board et sans limite.</p>
        <div class="tip">Cette page AIDE est interactive : utilise la recherche ou le sommaire à gauche
        pour trouver une action précise.</div>
        <p class="see">Voir aussi : <a href="topic:navigation">Navigation</a> ·
        <a href="topic:depannage">Dépannage</a></p>
        """,
    },
    {
        "id": "navigation",
        "theme": "interface",
        "title": "Navigation, recherche et raccourcis",
        "keywords": "navigation menu sidebar recherche globale page retour fiche double clic glisser filtre",
        "html": """
        <h2>Se déplacer dans le jeu</h2>
        <p>Le menu de gauche donne accès aux grands écrans :</p>
        <ol>
          <li>Direction sportive</li>
          <li>Messagerie</li>
          <li>Effectif</li>
          <li>Tactiques</li>
          <li>Centre de match</li>
          <li>Entraînement</li>
          <li>Infrastructure</li>
          <li>Centre de formation</li>
          <li>Transferts</li>
          <li>Calendrier</li>
          <li>Compétitions</li>
          <li>Finances</li>
          <li>Staff</li>
        </ol>
        <h3>Recherche globale</h3>
        <p>La barre en haut du menu cherche un joueur ou un club. Appuie sur Entrée pour ouvrir la
        page Recherche avec les filtres. Un clic sur une carte ouvre la fiche complète.</p>
        <h3>Gestes utiles</h3>
        <ul>
          <li>Double-clic sur un joueur : fiche joueur.</li>
          <li>Glisser-déposer : composition tactique et banc.</li>
          <li>Molette ou ascenseur : écrans longs (effectif, infrastructure, aide).</li>
          <li>Clique un club dans un classement : fiche club.</li>
        </ul>
        <div class="tip">Si une fenêtre semble trop grande, réduis la taille du texte dans Options
        ou passe en mode maximisé.</div>
        <p class="see">Voir aussi : <a href="topic:options">Options</a> ·
        <a href="topic:effectif">Effectif</a></p>
        """,
    },
    {
        "id": "depannage",
        "theme": "interface",
        "title": "Dépannage et questions fréquentes",
        "keywords": "probleme bug erreur lancer exe bat sauvegarde perte ecran texte fenetre performance",
        "html": """
        <h2>Questions fréquentes</h2>
        <h3>Le jeu ne se lance pas</h3>
        <p>Lance toujours le jeu avec <b>LANCER.bat</b>. Il ne faut pas recompiler ni modifier les
        exécutables. Si une fenêtre noire apparaît puis disparaît, vérifie que Python et PySide6 sont
        installés.</p>
        <h3>Ma sauvegarde a disparu</h3>
        <p>Vérifie la liste <b>CHARGER</b> : une sauvegarde peut avoir été renommée ou déplacée.
        Le jeu ne supprime pas une carrière sans action explicite.</p>
        <h3>Le texte est trop petit ou trop grand</h3>
        <p>Ouvre <b>Options &gt; APPARENCE &gt; TAILLE DU TEXTE</b>. Le changement s'applique
        immédiatement. Le mode maximisé aide sur les petits écrans.</p>
        <h3>Un écran semble vide</h3>
        <p>Certaines pages dépendent de la carrière ouverte. Reviens à la Direction sportive, puis
        rouvre l'écran. Un match en direct peut aussi verrouiller la navigation.</p>
        <h3>Où sont les erreurs ?</h3>
        <p>Le jeu écrit un journal local. Les sauvegardes de secours et les versions saines sont
        conservées dans le dossier de sauvegardes du projet. Ne modifie pas les fichiers à la main
        pendant que le jeu tourne.</p>
        <div class="tip">En cas de doute, exporte une copie de la sauvegarde avant de tester un
        changement.</div>
        <p class="see">Voir aussi : <a href="topic:sauvegardes">Sauvegardes</a> ·
        <a href="topic:options">Options</a></p>
        """,
    },
    {
        "id": "glossaire",
        "theme": "interface",
        "title": "Glossaire du manager",
        "keywords": "glossaire niveau potentiel forme moral reputation masse salariale plafond shortlist precontrat pret v n d",
        "html": """
        <h2>Glossaire</h2>
        <table class="grid">
          <tr><td><b>V / N / D</b></td><td>Victoires, matchs nuls, défaites.</td></tr>
          <tr><td><b>J</b></td><td>Journée de championnat.</td></tr>
          <tr><td><b>Niveau /20</b></td><td>Synthèse pondérée des attributs selon le poste.</td></tr>
          <tr><td><b>Potentiel</b></td><td>Plafond de progression fixé à la création du joueur.</td></tr>
          <tr><td><b>Forme</b></td><td>Condition physique ; basse, elle pénalise et expose aux blessures.</td></tr>
          <tr><td><b>Moral</b></td><td>État mental ; influe sur la constance et les contrats.</td></tr>
          <tr><td><b>Réputation</b></td><td>Prestige du club, de local à mondial.</td></tr>
          <tr><td><b>Masse salariale</b></td><td>Somme des salaires des joueurs et du staff.</td></tr>
          <tr><td><b>Plafond</b></td><td>Limite de masse salariale imposée par le board.</td></tr>
          <tr><td><b>Shortlist</b></td><td>Liste de joueurs suivis, avec évolution de valeur.</td></tr>
          <tr><td><b>Pré-contrat</b></td><td>Accord pour rejoindre un club à la fin du contrat.</td></tr>
          <tr><td><b>Prêt</b></td><td>Joueur mis à disposition sans transfert définitif.</td></tr>
          <tr><td><b>Familiarité</b></td><td>Niveau d'automatisme d'une tactique ou d'un plan.</td></tr>
          <tr><td><b>Projet IA</b></td><td>Ambition, objectif, entraîneur et besoins d'un club adverse.</td></tr>
        </table>
        <p class="see">Voir aussi : <a href="topic:effectif">Effectif</a> ·
        <a href="topic:finances">Finances</a> · <a href="topic:clubs-ia">Clubs IA</a></p>
        """,
    },
    {
        "id": "mentalites",
        "theme": "tactiques",
        "title": "Mentalités : doser le risque",
        "keywords": "mentalite offensive prudente equilibree risque pressing bloc tempo conversion momentum fin de match",
        "html": """
        <h2>Trois mentalités, trois arbitrages</h2>
        <p>La mentalité ne change pas seulement l'intention : elle modifie l'attaque, la défense et la
        qualité des occasions. Choisir, c'est renoncer à quelque chose.</p>
        <table>
          <tr><th>Mentalité</th><th>Attaque</th><th>Défense</th><th>Conversion</th><th>Quand l'utiliser</th></tr>
          <tr><td><b>Prudente</b></td><td>−5,5 %</td><td><b>+7,5 %</b></td><td>−4 %</td>
              <td>Protéger un avantage, subir un pressing haut, jouer un gros adversaire.</td></tr>
          <tr><td><b>Équilibrée</b></td><td>—</td><td>—</td><td>—</td>
              <td>Référence : lisibilité et contrôle du rythme.</td></tr>
          <tr><td><b>Offensive</b></td><td><b>+7,5 %</b></td><td>−6 %</td><td>+5 %</td>
              <td>Il faut marquer, l'adversaire est faible ou fatigué.</td></tr>
        </table>
        <h3>Ce qui se combine</h3>
        <ul>
          <li><b>Pressing</b> : plus de récupérations et de pertes forcées, mais de la fatigue et des fautes.</li>
          <li><b>Hauteur de bloc</b> : un bloc haut réduit les occasions adverses mais expose la profondeur.</li>
          <li><b>Tempo</b> : rapide = plus de séquences, patient = meilleures passes et moins de déchet.</li>
          <li><b>Mentalité</b> : elle module le comportement des 8 dernières minutes (pousser ou sécuriser).</li>
        </ul>
        <h3>Le momentum</h3>
        <p>Un but ou une grosse occasion fait basculer le momentum. Une équipe offensive le ressent plus
        fort (positif comme négatif), une équipe prudente l'amortit : elle encaisse le coup sans s'effondrer.</p>
        <div class="tip">Une mi-temps ne se joue pas comme l'autre : commence équilibré, puis durcis ou
        lâche les chevaux selon le score et la fatigue adverse.</div>
        <p class="see">Voir aussi : <a href="topic:tactiques">Tactiques</a> ·
        <a href="topic:match">Match en direct</a> · <a href="topic:terrain-2d">Terrain 2D</a></p>
        """,
    },
    {
        "id": "terrain-2d",
        "theme": "tactiques",
        "title": "Lire le terrain 2D",
        "keywords": "terrain 2d animation fluide vitesse ralenti passe tir but pastille ballon trail",
        "html": """
        <h2>Ce que raconte le terrain</h2>
        <p>Le terrain 2D est un <b>mouchard</b> : il lit le moteur, il ne décide rien. Tout ce qui bouge
        correspond à une action réelle du match.</p>
        <h3>Les repères</h3>
        <ul>
          <li><b>Pions/maillots</b> : ton cinq à gauche en 1re période, à droite en 2e (changement de côté).</li>
          <li><b>Ballon + traînée</b> : la traînée marque les passes et les frappes rapides.</li>
          <li><b>Pilule d'action</b> en haut : le dernier événement et son détail (« Cissé → Roussel »).</li>
          <li><b>Popup BUT</b> : club et buteur, avec un court ralenti.</li>
        </ul>
        <h3>Vitesse et lisibilité</h3>
        <p>Le sélecteur <b>1× à 5×</b> accélère la simulation. Les animations d'action se raccourcissent
        automatiquement pour rester synchronisées : à 5×, le match est dense, à 1× tu vois chaque course.</p>
        <table>
          <tr><th>Contrôle</th><th>Effet</th></tr>
          <tr><td>PAUSE / REPRENDRE</td><td>Arrête ou relance le direct (la mi-temps lance la 2e période).</td></tr>
          <tr><td>+ 20 SECONDES</td><td>Avance d'une séquence sans changer la vitesse.</td></tr>
          <tr><td>Rapport du match</td><td>Ouvre le détail complet après le coup de sifflet.</td></tr>
        </table>
        <div class="tip">Si le terrain te semble figé, vérifie que le match n'est pas en pause ou en
        mi-temps : le chrono reste bloqué tant que tu n'as pas repris.</div>
        <p class="see">Voir aussi : <a href="topic:match">Match en direct</a> ·
        <a href="topic:mentalites">Mentalités</a></p>
        """,
    },
    {
        "id": "offres-secretes",
        "theme": "mercato",
        "title": "Offres de club et messages SECRET",
        "keywords": "offre club secret confidentiel changement de club carriere recruter manager accepter refuser",
        "html": """
        <h2>Quand un club veut te recruter</h2>
        <p>En fin de saison, si tes résultats et la confiance du board le justifient, des clubs peuvent
        te proposer leur banc. L'intérêt arrive sous deux formes :</p>
        <ul>
          <li>une <b>news publique</b> (« X club(s) pensent à toi ») ;</li>
          <li>un <b>message SECRET</b> dans la messagerie, dossier <b>Carrière</b>.</li>
        </ul>
        <h3>Le message confidentiel</h3>
        <p>Il précise le club, sa division et son projet. Il est marqué <b>CONFIDENTIEL</b> : aucune
        annonce officielle n'a été faite. Le bouton <b>VOIR LES OFFRES DE CLUB</b> ouvre la Direction
        sportive, où tu acceptes ou refuses.</p>
        <table>
          <tr><th>Choix</th><th>Conséquence</th></tr>
          <tr><td><b>Accepter</b></td><td>Tu prends le club : effectif, installations, budget et sponsors
              deviennent les tiens. Tu emmènes ton staff et tes méthodes, pas l'ancien effectif.</td></tr>
          <tr><td><b>Refuser</b></td><td>Le message est clos, l'offre disparaît, ton contrat actuel
              reste valable.</td></tr>
        </table>
        <div class="tip">Une seule vague d'offres par saison : si tu refuses tout, il faudra convaincre
        à nouveau la saison prochaine.</div>
        <p class="see">Voir aussi : <a href="topic:clubs-ia">Clubs IA</a> ·
        <a href="topic:messages">Messagerie</a> · <a href="topic:direction">Direction sportive</a></p>
        """,
    },
    {
        "id": "redressement",
        "theme": "finances",
        "title": "Trésorerie négative : embargo et redressement",
        "keywords": "tresorerie negative deficit embargo redressement vente forcee budget banqueroute board",
        "html": """
        <h2>Passer dans le rouge</h2>
        <p>Dès que la trésorerie passe sous zéro, le board réagit :</p>
        <ol>
          <li><b>Alerte immédiate</b> : news « Trésorerie négative » et <b>embargo implicite</b> —
              plus de recrutement, de prêt ni de chantier tant que le budget est négatif.</li>
          <li><b>60 jours rouges</b> : <b>plan de redressement</b> — le board met en vente le joueur
              le plus cher. Puis tous les 60 jours si le rouge persiste.</li>
          <li><b>Retour au vert</b> : l'embargo est levé et le compteur de jours rouges remis à zéro.</li>
        </ol>
        <h3>Le garde-fou</h3>
        <p>Le board ne descendra jamais sous un noyau de <b>8 joueurs</b> : une vente forcée protège
        l'effectif minimum. À la clôture, la réputation du club est aussi pénalisée.</p>
        <h3>Comment sortir du rouge</h3>
        <ul>
          <li>vendre un salaire lourd plutôt qu'un jeune à fort potentiel ;</li>
          <li>baisser les prix de billetterie pour remplir la salle ;</li>
          <li>attendre les recettes de match, les sponsors et les primes de classement ;</li>
          <li>éviter les chantiers tant que la trésorerie n'est pas assainie.</li>
        </ul>
        <div class="tip">Une prime de montée ou de parachute peut suffire à repasser au vert : le
        compteur repart alors de zéro, mais la confiance du board, elle, garde la trace.</div>
        <p class="see">Voir aussi : <a href="topic:finances">Finances</a> ·
        <a href="topic:infrastructure">Infrastructure</a></p>
        """,
    },
    {
        "id": "objectifs-board",
        "theme": "direction",
        "title": "Objectifs du board : comment c'est calculé",
        "keywords": "board objectif classement finances jeunes u21 confiance chip top maintien",
        "html": """
        <h2>Trois objectifs, une confiance</h2>
        <p>Le bandeau <b>OBJECTIFS DU BOARD</b> (Direction sportive) résume la saison en trois
        pastilles, puis la confiance globale.</p>
        <table>
          <tr><th>Pastille</th><th>Ce qui est mesuré</th><th>Réussi si…</th></tr>
          <tr><td><b>CLASSEMENT</b></td><td>Ta position réelle dans ta division, comparée à la
              place fixée par l'ambition du board (top N).</td><td>position ≤ top N</td></tr>
          <tr><td><b>FINANCES</b></td><td>La trésorerie du club.</td><td>budget ≥ 0</td></tr>
          <tr><td><b>JEUNES (U21)</b></td><td>Le nombre de joueurs de <b>21 ans ou moins</b> de ton
              effectif ayant joué <b>au moins 3 matchs</b> cette saison.</td><td>compteur ≥ objectif</td></tr>
        </table>
        <h3>Exemple : « JEUNES (U21) • 0/2 »</h3>
        <p>Cela veut dire : <b>aucun</b> joueur de 21 ans ou moins n'a encore atteint 3 matchs,
        alors que le board en attend <b>2</b>. Un jeune avec 1 ou 2 matchs ne compte pas encore :
        il faut le faire entrer régulièrement.</p>
        <p>L'infobulle de la pastille donne le détail : nombre d'U21 dans l'effectif et meilleur
        jeune (matches joués). La ligne sous les pastilles rappelle la règle et la confiance.</p>
        <h3>La confiance</h3>
        <p>Elle part de 50 et bouge avec le classement (gros bonus dans le top, malus si tu es loin),
        la trésorerie (±10), les jeunes (±10), le bilan victoires/défaites (±8). En dessous de 22 %,
        le board gèle les transferts ; sous 30 %, il adresse un avertissement.</p>
        <div class="tip">Pour valider l'objectif jeunes, donne du temps de jeu : un U21 titulaire
        atteint 3 matchs en trois journées. Les prêts de jeunes ne comptent pas pour ton club.</div>
        <p class="see">Voir aussi : <a href="topic:direction">Direction sportive</a> ·
        <a href="topic:formation">Centre de formation</a> ·
        <a href="topic:effectif">Effectif</a></p>
        """,
    },
]

THEME_INDEX = {key: (label, desc) for key, label, desc in HELP_THEMES}
TOPIC_INDEX = {topic["id"]: topic for topic in HELP_TOPICS}
