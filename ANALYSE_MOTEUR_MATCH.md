# ANALYSE — Moteur de match FM2027

> Analyse du 30/10/2026. Deux moteurs cohabitent : le moteur **entre équipes IA**
> (`match_engine.py`) et le moteur **live du manager** (`MainWindow.simulate_event`,
> rendu par `match_pitch2d.py`).

## 1. Architecture actuelle

| Élément | Moteur IA (`match_engine.py`) | Moteur manager (app.py) |
|---|---|---|
| Cadence | 120 ticks de 20 s (2 × 20 min) | 1 événement toutes les 20 s, 2400 s |
| Force des équipes | moyenne des 5 alignés (`match_team_profile`) | idem + consignes individuelles |
| Tactique | style, formation, pressing, tempo | + mentalité, bloc, largeur, axe, relance, familiarité, coups de pied arrêtés, powerplay |
| Aléatoire | RNG semé par `fixture_id` (déterministe) | RNG propre au match |
| Cartons | tirage **après** le match (0-2 jaunes, 8 % rouge) | par faute, avec jaune/rouge et 2 min à 4 |
| Fatigue | forfait fin de match (2-4 pts selon pressing/tempo) | à la mi-temps et en fin de match |
| Momentum | absent | présent (±20) |
| Score / temps | absent | relance offensive des dernières minutes |
| Blessures | absentes | présentes (hors simulation d'événement) |

## 2. Ce que le moteur « entre équipes » utilise vraiment

- `attack` = finition 32 % + technique 24 % + dribble 14 % + vitesse 8 % + passe 14 % + endurance 8 %
- `defense` = défense 42 % + placement 17 % + endurance 19 % + technique 12 % + passe 10 %
- `passing` = passe 54 % + technique 30 % + placement 16 %
- `finishing`, `keeper` (gardien 70 % + condition 12 % + endurance 8 % + placement 10 %), `stamina`
- Identité : `style` (possession / contre / pressing / équilibre), `formation` (4-0, 2-2, 3-1),
  `pressing` (Haut / Médian / Bas), `tempo` (Patient / Normal / Rapide)
- Avantage du terrain : **+0,018** fixe sur l'attaque
- Réputation : seulement pour l'éligibilité des offres et le tirage au sort de la coupe

Effets codés en dur aujourd'hui :

| Réglage | Effet |
|---|---|
| 4-0 | +0,025 attaque |
| 2-2 | +0,015 attaque |
| pressing haut | +0,020 attaque adverse autorisée, +0,035 pertes de balle forcées |
| contre | +0,012 attaque |
| possession | +0,035 réussite de passe |
| tempo patient | +0,025 réussite de passe |
| domicile | +0,018 attaque |

## 3. Ce qui manque (et qui explique le manque de réalisme)

1. **La mentalité n'existe pas côté IA.** Aucun club ne joue « prudent » ou
   « offensif » : seuls 4 styles génériques existent, sans coût ni bénéfice
   défensif. Résultat : toutes les équipes se ressemblent.
2. **Aucune dynamique de match.** Pas de momentum, pas d'effet du score, pas de
   fin de match à gérer. Un 2-0 à la 30e ne change rien.
3. **Le rouge est décoratif.** Les cartons sont tirés après coup : une équipe à
   4 ne défend pas moins bien.
4. **La fatigue ne pèse pas.** Elle est appliquée après le match, jamais pendant :
   un pressing haut ne coûte rien en fin de rencontre.
5. **Le gardien n'a pas de « jour sans ».** Seule sa note moyenne compte.
6. **Les individualités s'effacent.** Seuls les buteurs sont pondérés ; un
   défenseur ou un passeur d'exception ne change presque rien.
7. **Pas de coups de pied arrêtés** hors 6e faute (et encore : le moteur IA ne
   gère pas les 6 fautes).
8. **Pas de blessures en match**, pas de but contre son camp (le paramètre
   existe mais n'est jamais utilisé), pas de frappe déviée.
9. **Peu de surprise.** La variance vient uniquement du tirage des séquences :
   l'écart de niveau est écrasé (`0,0012` par point, soit 0,048 pour 40 points).
10. **Tempo/tactique ne changent pas le nombre de possessions**, seulement la
    réussite des passes.

## 4. Le plan v2 (implémenté)

### 4.1 Identité tactique complète (`club_profiles.py`)

Chaque profil de club reçoit une identité lisible par le moteur :

| Profil | Mentalité | Bloc | Largeur | Axe | Discipline |
|---|---|---|---|---|---|
| Formateur | Équilibrée | Médian | Normale | Ailes | 0,85 |
| Riche | Offensive | Haut | Large | Axe | 0,60 |
| Spectacle | Offensive | Haut | Large | Ailes | 0,50 |
| Économe | Prudente | Bas | Étroite | Axe | 0,85 |
| Bâtisseur | Équilibrée | Médian | Normale | Axe | 0,70 |
| Opportuniste | Prudente | Médian | Étroite | Ailes | 0,65 |
| Guerrier | Offensive | Haut | Normale | Axe | 0,35 |

### 4.2 Moteur v2 (`match_engine.py`)

- **Forme du jour** par équipe (moral + condition + tirage semé, ±3 %) : une
  grosse équipe peut être méconnaissable un soir.
- **Arbitre** tiré par match (sévérité 0,7-1,3) : plus ou moins de cartons.
- **Possession** pondérée par passe, style, pressing, tempo, fatigue, momentum.
- **Duel individuel** à chaque séquence : porteur et défenseur choisis par
  attributs, donc les stars pèsent.
- **Qualité de frappe** : occasion nette / frappe normale / frappe spéculative,
  avec conversion distincte.
- **Erreur de gardien** (~1,5-2,5 %), **but contre son camp** (rare),
  **frappe déviée** (devient corner ou but).
- **Fautes par tick** liées à la discipline et au pressing, cartons liés à
  l'arbitre ; **rouge = 2 minutes à 4** (le moteur IA ne le faisait pas).
- **6e faute cumulée** → 10 m sans mur.
- **Momentum** qui monte/descend (buts, grosses occasions) et se dissipe.
- **Effet du score et du temps** : une équipe menée pousse (surtout si
  offensive), une équipe devant sécurise (surtout si prudente).
- **Fatigue en direct** : le pressing et le tempo haut coûtent cher après la
  30e ; l'endurance et la condition amortissent.
- **Blessures en match** (rares, aggravées par la fatigue), **cartons** et
  **notes** cohérents avec le déroulé.

### 4.3 Moteur manager : la mentalité devient symétrique

Aujourd'hui « Offensive » donne +4 % d'attaque sans risque et « Prudente »
-2,5 % d'attaque sans bonus défensif. La v2 applique un vrai arbitrage :

| Mentalité | Attaque | Défense | Conversion | Comportement |
|---|---|---|---|---|
| Prudente | −5,5 % | **+7,5 %** | −4 % | Bloc bas, temporise, sécurise un avantage |
| Équilibrée | 0 | 0 | 0 | Référence |
| Offensive | **+7,5 %** | **−6 %** | +5 % | Bloc haut, pousse tôt, s'expose aux contres |

Et le momentum devient plus sensible pour les mentalités extrêmes (une
offensive « vit » plus fort un but marqué ou encaissé).

## 5. Garde-fous

- Déterminisme conservé (même `fixture_id` → même score).
- Buts/match surveillés : cible **4,0-6,5** (réel futsal ≈ 5-7).
- Avantage du terrain **55-60 %** de points à domicile.
- Une équipe 15 points au-dessus gagne **> 60 %** de ses matchs.
- Rouges < 0,15/match, blessures < 0,3/match, buts CSC < 0,03/match.
- `tests/test_match_engine_v2.py` + soak complet.

## 6. Résultats mesurés après implémentation

Banc de 400 matchs par scénario (`tests/test_match_engine_v2.py`) :

| Scénario | Buts/match | Domicile | Nul | Extérieur | Tirs | Cartons |
|---|---|---|---|---|---|---|
| Équipes égales | 4,69 | 48,0 % | 15,2 % | 36,8 % | 32 | 2,5 |
| Fort (72) vs faible (52) | 5,17 | 74,8 % | 9,9 % | 11,5 % | 33 | 2,6 |
| Offensive vs équilibrée | 5,19 | — | — | — | — | 3,4 |
| Prudente vs équilibrée | 4,68 | — | — | — | — | 2,3 |
| Offensive vs offensive | ≈ 5,5 | — | — | — | 35 | 5,1 |

- **Mentalités** : à niveau égal, l'offensive marque **2,75** et encaisse **2,44** ;
  la prudente marque **2,60** et encaisse **2,08**. L'arbitrage est réel, aucune
  mentalité n'est dominante.
- **Hiérarchie** : +20 points de niveau → **75 %** de victoires, mais **11,5 %**
  d'exploits adverses (la surprise reste possible).
- **Dynamique** : un but fait basculer le momentum, une équipe menée pousse dans
  les 12 dernières minutes (8 si prudente), un rouge coûte 2 minutes à 4.
- **Intégration saison** (soak 599 matchs) : **4,82 buts/match**, 0 erreur,
  `data/error.log` à 0 octet.

