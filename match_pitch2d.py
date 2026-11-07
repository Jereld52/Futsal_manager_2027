# -*- coding: utf-8 -*-
"""match_pitch2d.py — Terrain de futsal 2D sur le centre de match (niveau 1).

PRINCPE : mouchard, pas acteur. Ce module n'ecrit JAMAIS dans match_state ni
dans la base : il lit l'etat du moteur a chaque tick et dessine. Les
resultats (seed, stats, timeline) restent la propriete exclusive du moteur
app.py. La classe LiveMatchBanner remplace MatchActionBanner a la creation
du bandeau : elle retransmet chaque action (passe, tir, but, arret, faute,
corner, turnover, remplacement) au terrain via note_event().

Robustesse :
  - update/paint defensifs : une donnee inattendue est ignoree (jamais de
    KeyError remonte), une exception est avale localement (le moteur
    continue), log_error reste cote appelant (app._pitch_sync).
  - rendu en pure paintEvent (aucun QGraphicsScene item cree en boucle) :
    cout CPU negligeable, pas d'accumulation d'objets (fuite Qt).
  - timer de rendu demarre SEULEMENT quand une animation est en cours
    (entite non arrivee a sa cible / flash actif), arrete sinon.
"""
import math
import sys
import time
from PySide6.QtCore import QTimer, Qt, QPointF, QRectF
from PySide6.QtGui import (QColor, QFont, QPainter, QPen, QBrush, QFontMetrics,
                           QPainterPath, QPolygonF, QPixmap)
from PySide6.QtWidgets import QWidget, QSizePolicy, QPushButton, QButtonGroup, QToolButton

from ui_components import MatchActionBanner


def display_team_colors(home_color, away_color):
    """Couleurs RÉELLES des deux clubs.

    On ne change PLUS la teinte du club adverse (retour : « les pions sont en
    vert, pas aux couleurs du club affronté »). Si les deux maillots sont
    vraiment trop proches, on se contente d'éclaircir/assombrir l'extérieur ;
    la forme (cercle / losange) et le maillot dessiné dessus suffisent."""
    h=QColor(home_color); a=QColor(away_color)
    if not h.isValid(): h=QColor("#35c98a")
    if not a.isValid(): a=QColor("#f0a34e")
    dist=abs(h.red()-a.red())+abs(h.green()-a.green())+abs(h.blue()-a.blue())
    if dist<55:
        a=a.darker(155) if a.lightness()>110 else a.lighter(160)
    return h,a


# ------------------------------------------------------------------ repertoires
# Slots normalises (x,y) pour l'equipe "h" qui joue vers x=1. l'equipe "a"
# joue vers x=0 (miroir). 2-2 classique futsal.
SLOTS_H = [(0.055, 0.50),                 # gardien
           (0.27, 0.24), (0.27, 0.76),    # deux defenseurs (ecart elargi)
           (0.52, 0.30), (0.52, 0.70)]    # deux attaquants (couloirs larges)
MARKER_MS = 1600      # duree d'affichage du dernier libelle d'action
FLASH_MS = 2200       # duree du flash "BUT"
FPS_MS = 33
STEPS = ("1RE", "2E")
MAX_STEP = 0.0150      # vitesse de course max par frame
BALL_STEP = 0.038     # (heritage) vitesse max du ballon
BALL_KICK_STEP = 0.060  # vitesse d'une frappe
BALL_DRIBBLE_STEP = 0.020  # vitesse de conduite de balle
PLAYER_ACCEL = 0.26   # lissage de la vitesse des joueurs (0..1)
BALL_ACCEL = 0.34     # lissage de la vitesse du ballon
WANDER_A = 0.039      # amplitude du balancement naturel des joueurs

ACTION_TEXT = {
    "kickoff": "COUP D'ENVOI",
    "build": "CONSTRUCTION",
    "pass": "PASSE",
    "shot": "TIR",
    "target": "TIR CADRÉ",
    "save": "ARRÊT",
    "goal": "BUT",
    "foul": "FAUTE",
    "corner": "CORNER",
    "turnover": "RÉCUPÉRATION",
    "interception": "INTERCEPTION",
    "substitution": "REMPLACEMENT",
    "yellow_card": "CARTON JAUNE",
    "red": "CARTON ROUGE",
    "ten_metre": "10 M",
    "timeout": "TEMPS MORT",
    "instruction": "CONSIGNE",
    "halftime": "MI-TEMPS",
    "fulltime": "FIN DU MATCH",
}


def _clamp01(v):
    return 0.0 if v < 0.0 else (1.0 if v > 1.0 else float(v))


def _mirror(slot):
    return (1.0 - slot[0], 1.0 - slot[1])


class Pitch2DWidget(QWidget):
    """Terrain 40x20 m (ratio 2:1 impose, contrairement au viewport) centre.

    Les positions restent normalisees (0..1)*2D : le rendu met a l'echelle a
    chaque paintEvent — le terrain ne s'etire jamais, il se recentre (lecon
    ClubIdentityPreview : ratio fixe + recentrage).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Pitch2D")
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setMinimumSize(420, 250)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._state = None
        self._phase = "prematch"                 # prematch | live | halft | fullt
        self._second_half = False                # changement de cotes a la mi-temps
        self._teams = self._empty_teams()
        self._ball = {"pos": [0.5, 0.5], "target": [0.5, 0.5], "vx": 0.0, "vy": 0.0}
        self._ball_trail = []
        self._possession = None                   # "h"/"a"/None
        self._carriers = {"h": 1, "a": 1}         # index rotatif du porteur
        self._last_event = None                   # (label, side, until_mono)
        self._last_event_detail = ""              # court detail (buteur, passeur…)
        self._goal_flash = None                   # (side, until_mono)
        self._goal_info = None                    # (buteur, side, until)
        self._ball_lock_until = 0.0               # cible evenement prioritaire
        self._celebrate = None                    # {"side","until"} celebration but
        self._pulse_until = 0.0
        self._players_on = {"h": 5, "a": 5}
        self._sent_off_slot = {"h": None, "a": None}
        self._clock = "00:00"
        self._score = (0, 0)
        # consignes tactiques du match (photo app : pressing/mentalite/preset)
        self._tactics = {"h": {}, "a": {}}
        # TRANSITION BURST (retour « fluide et conforme aux tactiques ») :
        # a chaque changement de possession, les attaquants de l'equipe qui
        # recupere accelerent 1,7 s ; preset "contre" = sprint encore plus net.
        self._burst = None                        # (side, until_mono)
        self._names = ("DOMICILE", "EXTÉRIEUR")
        self._colors = {"h": QColor("#72dfbd"), "a": QColor("#ffbd73")}
        self._kits = {"h": None, "a": None}   # maillots dessinés sur les pions
        self._kit_scaled = {}
        self._seen = dict(hg=0, ag=0, passes_h=0, passes_a=0, shots_h=0,
                          shots_a=0, target_h=0, target_a=0, corners_h=0,
                          corners_a=0, fouls_h=0, fouls_a=0, red_h=0, red_a=0)
        self._timer = QTimer(self)
        self._timer.setInterval(FPS_MS)
        self._timer.timeout.connect(self._step)
        # Cadence du moteur (ms par tick) : les verrous d'action sont raccourcis
        # quand la simulation accelere, pour que le ballon suive toujours l'action.
        self._pace_k = 1.0
        # Cache du terrain : les lignes, buts et zones ne changent pas a chaque frame.
        self._court_cache = None
        self._court_cache_key = None
        self._has_been_visible = False

    # ------------------------------------------------------------ construction
    @staticmethod
    def _empty_teams():
        def mk():
            return [{"slot": None, "number": 0, "name": "",
                     "pos": [0.5, 0.5], "target": [0.5, 0.5], "vx": 0.0, "vy": 0.0,
                     "gk": False, "shown": True, "alpha": 1.0} for _ in range(5)]
        return {"h": mk(), "a": mk()}

    def set_team_kits(self, home_pix=None, away_pix=None):
        """Maillots (QPixmap) dessinés à la place des pions : couleurs ET motif
        du club, comme sur les vignettes."""
        self._kits = {"h": home_pix, "a": away_pix}
        self._kit_scaled = {}

    def set_pace(self, interval_ms):
        """Adapte la durée des animations à la vitesse de simulation (1x..5x)."""
        try:
            k = float(interval_ms) / 600.0
        except (TypeError, ValueError):
            k = 1.0
        self._pace_k = max(0.35, min(1.5, k))

    def _scaled_kit(self, side, px):
        src=self._kits.get(side)
        if src is None or src.isNull(): return None
        key=(side,int(px))
        hit=self._kit_scaled.get(key)
        if hit is None:
            hit=src.scaled(int(px),int(px),Qt.KeepAspectRatio,Qt.SmoothTransformation)
            if len(self._kit_scaled)>120: self._kit_scaled={}
            self._kit_scaled[key]=hit
        return hit

    def reset_teams(self, home_name, away_name, home_color, away_color):
        # nouvelle rencontre : on repart des consignes neutres en attente de la photo
        self._timer.stop()
        self._tactics = {"h": {}, "a": {}}
        try:
            self._teams = self._empty_teams()
            self._names = (str(home_name or "DOMICILE"), str(away_name or "EXTÉRIEUR"))
            hc,ac = display_team_colors(home_color, away_color)
            self._colors = {"h": hc, "a": ac}
            self._seen = dict(hg=0, ag=0, passes_h=0, passes_a=0, shots_h=0,
                              shots_a=0, target_h=0, target_a=0, corners_h=0,
                              corners_a=0, fouls_h=0, fouls_a=0, red_h=0, red_a=0)
            self._phase = "prematch"
            self._second_half = False
            self._ball = {"pos": [0.5, 0.5], "target": [0.5, 0.5], "vx": 0.0, "vy": 0.0}
            self._ball_trail = []
            self._possession = None
            self._last_event = None; self._goal_flash = None
            # FENETRE CLEAN : purge aussi la popup but / la celebration —
            # re-ouvrir le centre de match ne doit rien ressusciter.
            self._goal_info = None; self._celebrate = None
            self._last_event_detail = ""
            self._players_on = {"h": 5, "a": 5}
            self._sent_off_slot = {"h": None, "a": None}
        except Exception:
            pass

    # ------------------------------------------------------------------ hooks
    def note_state(self, state, animate=True):
        """Appelé à chaque tick moteur (20 s simulées) : lit l'état, déduit
        les cibles de placement. AUCUNE ECRIТURE dans state."""
        try:
            if not state:
                return
            elapsed = int(state.get("elapsed_seconds", 0) or 0)
            self._clock = f"{elapsed // 60:02d}:{elapsed % 60:02d}"
            hg, ag = int(state.get("hg", 0) or 0), int(state.get("ag", 0) or 0)
            # CHANGEMENT DE COTES : des que la seconde periode commence
            # (>= 1200 s), chaque equipe defend l'autre moitie du terrain.
            self._second_half = elapsed >= 1200
            if state.get("finished"):
                self._phase = "fullt"
            elif state.get("half_time_break"):
                self._phase = "halft"
            elif elapsed >= 1200:
                self._phase = "live"
            else:
                self._phase = "live"
            # un score qui bouge => but : le ballon file au fond des filets
            # COULEURS EXTÉRIEUR (retour « buteur/couleur inversés à l'extérieur ») :
            # l'état moteur raconte le match en cotes RÉELLES (h = domicile),
            # les slots 2D sont en cotes COACH (h = club du joueur). Tout ce
            # qui sort du state est remappé avant usage, sinon à l'extérieur
            # les buts/celebrations/porteurs adverses apparaissent sur les
            # pions du club du joueur.
            is_home = bool(state.get("is_home", True))
            def _co(st):
                if st not in ("h", "a"): return None
                return st if is_home else ("a" if st == "h" else "h")
            side = None
            if hg > self._seen["hg"]:
                side = _co("h")
            elif ag > self._seen["ag"]:
                side = _co("a")
            self._seen["hg"], self._seen["ag"] = hg, ag
            self._score = (hg, ag)
            if side:
                self._score_goal(side, elapsed)
            _pon = state.get("players_on", {}) or {}
            self._players_on = {"h": int(_pon.get("h" if is_home else "a", 5) or 5),
                                "a": int(_pon.get("a" if is_home else "h", 5) or 5)}
            # PHOTO TACTIQUE : le terrain aligne le bloc sur les consignes du jour.
            tac2 = state.get("tactics_2d")
            if isinstance(tac2, dict):
                try:
                    self._tactics = {"h": dict(tac2.get("h") or {}), "a": dict(tac2.get("a") or {})}
                except Exception:
                    pass
            self._integrate_lineups(state)
            # possession : l'aim du porteur respecte la PRIORITE des evenements
            # (tirs/buts/arrêts "verrouillent" la cible du ballon quelques secondes)
            now = time.monotonic()
            poss = _co(state.get("possession_side"))
            if poss in ("h", "a") and now >= self._ball_lock_until:
                passes = state.get("passes", None) or {}
                # compteurs de passes LUS en cotes moteurs, stockés en cotes coach
                ph, pa = int(passes.get("h" if is_home else "a", 0) or 0), int(passes.get("a" if is_home else "h", 0) or 0)
                side_changed = (poss != self._possession)
                if side_changed or ph != self._seen["passes_h"] or pa != self._seen["passes_a"]:
                    self._carriers[poss] = int(passes.get("h" if is_home else "a", 0) or 0) if poss == "h" else int(passes.get("a" if is_home else "h", 0) or 0)
                    self._seen["passes_h"], self._seen["passes_a"] = ph, pa
                self._possession = poss
                self._aim_carrier(poss)
            # EXCLUSION (retour « affecte les 2 equipes ») : le moteur retire
            # DEJA l'expulse de son lineup ; _integrate_lineups masque ensuite
            # le slot libere (None en fin d'ordre). L'ancien calcul
            # _sent_off_slot *re-masquait* un second slot (index d'avant le
            # pop, decorre de l'ordre gardien-d'abord) : une equipe se
            # retrouvait deux pions en moins. On ne masque plus ici.
            self._sent_off_slot = {"h": None, "a": None}
            self._wake()
        except Exception:
            pass

    def note_event(self, side, kind, detail=""):
        """Relais LiveMatchBanner : anime le ballon selon le type d'action.

        Chaque evenement pose un VERROU sur la cible du ballon : le tick
        suivant ne l'ecrase pas tant que l'action n'est pas purgee. Hiarchie :
        but (2,2 s) > tir/arrêt (1,4/1,0 s) > corner (0,9 s) > reprise (0,6 s)
        > passe (0,45 s)."""
        try:
            if side not in ("h", "a"):
                side = "h"
            label = ACTION_TEXT.get(kind, "ACTION")
            now = time.monotonic()
            self._last_event = (label, side, now + MARKER_MS / 1000.0, now)
            self._last_event_detail = str(detail or "")
            # TRANSITION BURST : le changement de possession lance un sprint
            # court de la nouvelle equipe attaquante (jubile "contre").
            if side != self._possession and self._possession is not None:
                self._burst = (side, now + 1.7)
            attacking = self._side_attacks_right(side)
            if kind == "goal":
                self._score_goal(side, None)
                self._goal_info = (str(detail or "BUT"), side, now + FLASH_MS / 1000.0 * self._pace_k)
                self._ball["target"] = (1.004 if attacking else -0.004, 0.5)
                self._kick_ball(self._ball["target"], BALL_KICK_STEP)
                self._ball_lock_until = now + FLASH_MS / 1000.0 * self._pace_k
                self._start_celebration(side, now + FLASH_MS / 1000.0 * self._pace_k)
            elif kind == "kickoff":
                self._ball["target"] = (0.5, 0.5)
                self._ball["vx"] = self._ball["vy"] = 0.0
                self._possession = side
                self._ball_lock_until = now + 0.8 * self._pace_k
            elif kind == "shot":
                self._ball["target"] = (1.0 if attacking else 0.0,
                                        0.36 + 0.28 * ((self._carriers.get(side, 1) * 37) % 100) / 100.0)
                self._kick_ball(self._ball["target"], BALL_KICK_STEP)
                self._ball_lock_until = now + 1.4 * self._pace_k
                self._wake()
            elif kind == "save":
                other = "a" if side == "h" else "h"
                keeper = self._keeper_x(other)
                self._ball["target"] = (keeper, 0.5)
                self._kick_ball(self._ball["target"], BALL_KICK_STEP * 0.7)
                self._ball_lock_until = now + 1.0 * self._pace_k
                self._wake()
            elif kind == "corner":
                attacking_corner = self._side_attacks_right(side)
                y = 0.06 if self._carriers.get(side, 1) % 2 else 0.94
                self._ball["target"] = (1.0 if attacking_corner else 0.0, y)
                self._kick_ball(self._ball["target"], BALL_KICK_STEP * 0.55)
                self._ball_lock_until = now + 0.9 * self._pace_k
                self._wake()
            elif kind == "turnover":
                other = "a" if side == "h" else "h"
                self._possession = other
                self._carriers[other] = self._carriers.get(other, 1) + 1
                self._aim_carrier(other)
                self._kick_ball(self._ball["target"], BALL_DRIBBLE_STEP)
                self._ball_lock_until = now + 0.6 * self._pace_k
                self._wake()
            elif kind in ("pass", "build"):
                self._possession = side
                receiver = None
                if kind == "pass" and "→" in str(detail):
                    receiver = self._entity_by_name(side, str(detail).split("→", 1)[1].strip())
                self._aim_carrier(side, advance=(kind == "pass"), target_ent=receiver)
                self._kick_ball(self._ball["target"], BALL_DRIBBLE_STEP * 1.15)
                self._ball_lock_until = now + (0.45 if kind == "pass" else 0.3) * self._pace_k
                self._wake()
            else:  # carton, 10 m, temps mort, consigne, remplacement…
                self._wake()
        except Exception:
            pass

    def _keeper_x(self, side):
        team = self._teams.get(side) or []
        for ent in team:
            if ent.get("gk") and ent.get("shown"):
                return _clamp01(ent["pos"][0])
        return 0.05 if side == "h" else 0.95

    def _start_celebration(self, side, until):
        """Le cinq qui marque file celebrer au coin de la zone adverse."""
        try:
            attacking_right = self._side_attacks_right(side)
            corner_x = 0.94 if attacking_right else 0.06
            team = self._teams.get(side) or []
            spread = 0.14
            for i, ent in enumerate(team):
                if not ent.get("shown") or ent.get("gk"):
                    continue
                ent["target"] = [corner_x - 0.02 * (i - 1), _clamp01(0.18 + spread * (i - 1))]
            self._celebrate = {"side": side, "until": until}
            self._wake()
        except Exception:
            pass

    # ---------------------------------------------------------------intérieur
    def _side_attacks_right(self, side):
        # "h" (club du joueur) attaque a droite en 1RE mi-temps, a GAUCHE en
        # 2E (changement de cotes). Toutes les animations (buts, corners,
        # celebrations) suivent automatiquement ce pivot.
        attacks_right_h = (side == "h")
        return attacks_right_h if not self._second_half else (side == "a")

    def _score_goal(self, side, _elapsed):
        now = time.monotonic()
        self._goal_flash = (side, now + FLASH_MS / 1000.0 * self._pace_k)
        attacks_right = self._side_attacks_right(side)
        self._ball["target"] = (1.004 if attacks_right else -0.004, 0.5)
        self._possession = "a" if side == "h" else "h"

    def _lineup_slots(self, players):
        """5 slots stables : gardien d'abord, puis le reste dans l'ordre."""
        gk = [p for p in players if str(p.get("position", "")).strip() == "Gardien"]
        rest = [p for p in players if str(p.get("position", "")).strip() != "Gardien"]
        while len(gk) < 1 and rest:
            gk.append(rest.pop(0))
        while len(gk) > 1 and gk:
            rest.insert(0, gk.pop())
        ordered = (gk[:1] + rest)[:5]
        while len(ordered) < 5:
            ordered.append(None)
        return ordered

    def _integrate_lineups(self, state):
        for side, key in (("h", "lineup"), ("a", "opponent_lineup")):
            players = state.get(key) or []
            ordered = self._lineup_slots(players)
            conds = state.get("conditions" if key == "lineup" else "opponent_conditions", {}) or {}
            team = self._teams[side]
            for i, player in enumerate(ordered):
                # Placement : 1RE = h a gauche / a a droite. En 2E les deux
                # equipes PIVOTENT (h a droite, a a gauche) : changement de
                # cotes fidele a la mi-temps (retour utilisateur).
                base = _mirror(SLOTS_H[i]) if self._second_half else SLOTS_H[i]
                slot = base if side == "h" else _mirror(base)
                ent = team[i]
                if player is None:
                    ent["shown"] = False
                    continue
                condition = float(conds.get(player.get("id"), player.get("condition", 75)) or 75)
                swap = (ent["slot"] != slot) or (ent["name"] != f"{player.get('first_name','')} {player.get('last_name','')}") or not ent["slot"]
                ent["slot"] = slot
                ent["name"] = f"{player.get('first_name','')} {player.get('last_name','')}"
                ent["number"] = int(player.get("shirt_number") or 0)
                ent["gk"] = (i == 0)
                ent["shown"] = True
                ent["alpha"] = 0.55 + 0.45 * max(0.0, min(1.0, condition / 100.0))
                if swap:
                    # changement de joueur dans le slot : reprise nette depuis
                    # une position legerement decalee (pas de glissade fantome)
                    jitter = 0.04 if ent["shown"] else 0.0
                    dx = 1.0 if player.get("id", i) % 2 else -1.0
                    ent["pos"] = [slot[0] + dx * jitter, slot[1]]
                    ent["vx"] = 0.0
                    ent["vy"] = 0.0
                # pendant la celebration, la cible (coin du terrain) ne bouge pas
                celebrating = bool(self._celebrate and self._celebrate["side"] == side
                                   and time.monotonic() < self._celebrate["until"])
                if not celebrating:
                    self._aim_slot(side, i, ent)

    def _aim_slot(self, side, i, ent):
        slot = ent["slot"] or (SLOTS_H[i] if side == "h" else _mirror(SLOTS_H[i]))
        push = 1.0 if self._possession == side else 0.0
        # TACTIQUE EN 2D (retour « plus de deplacement en fonction de la tactique ») :
        # la hauteur du bloc depend du preset (possession > equilibre > contre),
        # de la mentalite (offensive pousse, prudente tient) et du pressing
        # (Haut = bloc haut meme sans ballon, Bas = bloc bas patent).
        tac = (self._tactics.get(side) or {}) if getattr(self,"_tactics",None) else {}
        preset = str(tac.get("preset","equilibre"))
        mentality = tac.get("mentality",0) or 0
        press = tac.get("pressing",1) if tac.get("pressing") is not None else 1
        preset_gain = {"possession":0.100,"powerplay":0.110,"equilibre":0.065,
                       "pressing":0.085,"contre":0.040}.get(preset,0.065)
        mentality_f = (0.66,1.0,1.28)[mentality if 0<=mentality<=2 else 1]
        # sans ballon le bloc reste haut si pressing Haut, s'assoit si Bas
        deep_gain = preset_gain + (0.040 if press==2 else -0.020 if press==0 else 0.0)
        shift_x = deep_gain * mentality_f * push if i >= 3 else deep_gain*0.55 * mentality_f * push
        block_seed = (press-1)*0.030 + (mentality-1)*0.035*push
        base_x = slot[0] + block_seed*(1.0 if side=="h" else -1.0)
        shift_x = shift_x if side=="h" else -shift_x
        sway = ((i % 2) * 0.065) * (1 if self._possession == side else -1)
        tx, ty = _clamp01(base_x + shift_x), _clamp01(slot[1] + sway)
        ent["target"] = [_clamp01(tx), _clamp01(ty)]

    def _aim_carrier(self, side, advance=False, target_ent=None):
        holder = target_ent if target_ent is not None else self._carrier_entity(side)
        if holder is None:
            self._ball["target"] = (0.5, 0.5)
            return
        attacking_right = self._side_attacks_right(side)
        lead = 0.045 if attacking_right else -0.045
        if advance:
            lead *= 1.5
        self._ball["target"] = (_clamp01(holder["pos"][0] + lead),
                                _clamp01(holder["pos"][1] + 0.02))

    def _kick_ball(self, target, speed):
        """Impulsion : le ballon part vraiment vers sa cible (passe, tir, but)."""
        try:
            bx, by = self._ball["pos"]
            dx = float(target[0]) - bx
            dy = float(target[1]) - by
            dist = math.hypot(dx, dy)
            if dist < 1e-6:
                return
            self._ball["vx"] = dx / dist * float(speed)
            self._ball["vy"] = dy / dist * float(speed)
        except Exception:
            pass

    # ------------------------------------------------------------------ rendu
    def reset_all(self):
        self.reset_teams(*self._names, self._colors["h"].name(), self._colors["a"].name())

    def showEvent(self, event):
        self._has_been_visible = True
        super().showEvent(event)

    def _wake(self):
        if not self.isVisible():
            self.update()
            return
        if not self._timer.isActive():
            self._timer.start()
        self.repaint_soon()

    def repaint_soon(self):
        self.update()

    def _step(self):
        """Boucle d'animation (33 fps quand actif) : MOUVEMENT CONTINU.

        Chaque joueur combine : sa cible tactique lente (note_state/aim_slot),
        un balancement naturel perpetuel (wander sinusoidal), l'attirance vers
        le ballon, le pressing du defenseur le plus proche, le repli quand le
        ballon s'invite dans la moitie adverse et les courses de soutien de la
        possession. Vitesse de course PLAFONNEE (MAX_STEP/frame) : plus de
        teleports, des deplacements reels et visibles."""
        if not self.isVisible() and getattr(self, "_has_been_visible", False):
            self._timer.stop()
            return
        now = time.monotonic()
        ball = self._ball
        # --- ballon : conduite sur le porteur, ou trajectoire verrouillee (tir/but/passe)
        locked = now < self._ball_lock_until
        if not locked and self._possession in ("h", "a"):
            holder = self._carrier_entity(self._possession)
            if holder:
                attacking = self._side_attacks_right(self._possession)
                ball["target"] = [_clamp01(holder["pos"][0] + (0.045 if attacking else -0.045)),
                                  _clamp01(holder["pos"][1] + 0.03)]
        bx, by = ball["pos"]
        all_settled = True
        dx = ball["target"][0] - bx
        dy = ball["target"][1] - by
        dist = math.hypot(dx, dy)
        bvx = float(ball.get("vx", 0.0) or 0.0)
        bvy = float(ball.get("vy", 0.0) or 0.0)
        if dist > 0.001:
            max_speed = BALL_KICK_STEP if locked else BALL_DRIBBLE_STEP
            want = min(max_speed, dist * 5.0)
            tvx, tvy = dx / dist * want, dy / dist * want
        else:
            tvx = tvy = 0.0
        bvx += (tvx - bvx) * BALL_ACCEL
        bvy += (tvy - bvy) * BALL_ACCEL
        if abs(bvx) < 1e-5:
            bvx = 0.0
        if abs(bvy) < 1e-5:
            bvy = 0.0
        if bvx or bvy:
            bx = _clamp01(bx + bvx)
            by = _clamp01(by + bvy)
            ball["pos"] = [bx, by]
            ball["vx"], ball["vy"] = bvx, bvy
            all_settled = False
            if math.hypot(bvx, bvy) > 0.018:
                self._ball_trail.append((bx, by, now))
                self._ball_trail = [t for t in self._ball_trail if now - t[2] < 0.45][-10:]
        if dist > 0.002:
            all_settled = False
        # --- pressing : le defenseur adverse le plus proche du ballon presse
        presser_side = "a" if self._possession == "h" else ("h" if self._possession == "a" else None)
        # PRESSING TACTIQUE (retour « moteur selon les options de jeu ») :
        # Haut => 2 presseurs en continue ; Bas => on reggenado puis sursaut
        # quand le ballon envahit le camp ; Mediane => 1 presseur.
        pressers = []
        if presser_side and not locked:
            _side_tac = (self._tactics.get(presser_side) or {}) if getattr(self,"_tactics",None) else {}
            try: _press=int(_side_tac.get("pressing",1) or 1)
            except (TypeError,ValueError): _press=1
            n_press = 2 if _press>=2 else (1 if _press==1 else 0)
            if _press<=0:
                own_deep = max(0.0,(0.5-bx)) if presser_side=="h" else max(0.0,(bx-0.5))
                n_press = 2 if own_deep>0.10 else 0
            if n_press:
                _cand=[]
                for i, ent in enumerate(self._teams[presser_side]):
                    if not ent.get("shown") or ent.get("gk") or i == self._sent_off_slot.get(presser_side):
                        continue
                    d = math.hypot(ent["pos"][0] - bx, ent["pos"][1] - by)
                    _cand.append((d, ent))
                _cand.sort(key=lambda t: t[0])
                pressers = [ent for _, ent in _cand[:n_press]]
        celebrating = self._celebrate and self._celebrate["until"] > now
        for side in ("h", "a"):
            is_celebrating = bool(celebrating and self._celebrate["side"] == side)
            has_poss = (self._possession == side) and not locked
            burst = bool(self._burst and self._burst[0] == side and self._burst[1] > now)
            deep = max(0.0, (0.5 - bx)) if side == "h" else max(0.0, (bx - 0.5))
            ball_in_own_half = (bx < 0.5) if side == "h" else (bx >= 0.5)
            _side_tac = (self._tactics.get(side) or {}) if getattr(self,"_tactics",None) else {}
            try: _m=int(_side_tac.get("mentality",0) or 0)
            except (TypeError,ValueError): _m=0
            # gains pedagogiques par consigne : offense mentale +28 % / prudente -30 %
            attack_gain = 0.055*(1.28 if _m==2 else (0.7 if _m==1 else 1.0))
            _pt=_side_tac.get("pressing",1)
            try: _p=int(_pt or 1)
            except (TypeError,ValueError): _p=1
            retreat_gain = (0.17 if _p>=2 else 0.13 if _p==1 else 0.085)
            for i, ent in enumerate(self._teams[side]):
                if not ent.get("shown"):
                    continue
                base = ent.get("target") or ent["pos"]
                if is_celebrating:
                    gx, gy = base[0], base[1]
                elif ent in pressers:
                    # pressing continu : il colle au ballon (legerement cote terrain)
                    gx, gy = bx - (0.03 if side == "h" else -0.03), by
                else:
                    phase = i * 1.73 + (0.0 if side == "h" else 0.9)
                    gx, gy = base[0], base[1]
                    if has_poss and i >= 3:
                        # ATTAQUE : appels en largeur amples + course de soutien
                        # vers la profondeur du ballon (les attaquants
                        # s'invitent dans la moitie adverse quand l'action monte)
                        # amplitude modulee par la MENTALITE (offensive ++)
                        deep_atk = max(0.0, (bx - 0.5)) if side == "h" else max(0.0, (0.5 - bx))
                        gx = _clamp01(gx + attack_gain + 0.048 * math.sin(now * 0.55 + phase) + 0.62 * deep_atk)
                        gy = _clamp01(base[1] + 0.23 * math.sin(now * 0.95 + phase))
                    elif not has_poss and i >= 1 and not ent.get("gk") and ball_in_own_half and deep > 0.02:
                        # repli defensif proportionnel a la profondeur du ballon
                        # (+ amplifie si pressing Haut : on défense en avancé et on
                        # décroche vite ; pressing Bas : bloc bas patient)
                        gx = _clamp01(gx + ((-retreat_gain * deep) if side == "h" else (retreat_gain * deep)))
                    if has_poss and 1 <= i <= 2:
                        # construction dans son camp : le bloc "respire", il monte et
                        # redescend en continu au lieu d'attendre sur ses slots
                        gx = _clamp01(gx + 0.068 * math.sin(now * 0.5 + phase))
                    if not ent.get("gk"):
                        # BLOC GLISSANT : chaque ligne suit lateralement le ballon
                        # (le propre camp ne se fige plus : la defense glisse,
                        # les milieux glissent, tout le monde s'ajuste en continu)
                        gy = _clamp01(gy + (by - base[1]) * (0.20 if i >= 3 else 0.26))
                        if abs(bx - base[0]) < 0.55:
                            gx = _clamp01(gx + (bx - base[0]) * (0.09 if i >= 3 else 0.13))
                    # balancement naturel perpetuel (jamais statique)
                    gx = _clamp01(gx + WANDER_A * math.sin(now * (0.7 + 0.11 * i) + phase))
                    gy = _clamp01(gy + WANDER_A * math.cos(now * (0.63 + 0.09 * i) + phase * 1.7))
                pos = ent["pos"]
                ddx = gx - pos[0]; ddy = gy - pos[1]
                dist_run = math.hypot(ddx, ddy)
                vx = float(ent.get("vx", 0.0) or 0.0)
                vy = float(ent.get("vy", 0.0) or 0.0)
                # VITESSE DE COURSE : plafond de base + burst de transition
                # (presseurs et attaquants en possession) ; le preset
                # "contre" sprinte encore plus fort sur la reprise de balle.
                mstep = MAX_STEP
                if burst and (ent in pressers or (has_poss and i >= 3)):
                    _tac = self._tactics.get(side) or {}
                    mstep = MAX_STEP * (1.65 if _tac.get("preset") == "contre" else 1.5)
                # Steering : accélération et freinage lissés (plus de saut de
                # direction, la course décrit une courbe naturelle).
                if dist_run > 0.0015:
                    want = min(mstep, dist_run * 5.0)
                    tvx, tvy = ddx / dist_run * want, ddy / dist_run * want
                else:
                    tvx = tvy = 0.0
                vx += (tvx - vx) * PLAYER_ACCEL
                vy += (tvy - vy) * PLAYER_ACCEL
                if abs(vx) < 1e-4:
                    vx = 0.0
                if abs(vy) < 1e-4:
                    vy = 0.0
                if vx or vy:
                    pos[0] = _clamp01(pos[0] + vx)
                    pos[1] = _clamp01(pos[1] + vy)
                    ent["vx"], ent["vy"] = vx, vy
                    all_settled = False
                elif dist_run > 0.002:
                    all_settled = False
        if self._celebrate and self._celebrate["until"] <= now:
            self._celebrate = None
        if self._burst and not self._burst[1] > now:
            self._burst = None
        flash_active = (self._goal_flash and self._goal_flash[1] > now) or \
                       (self._last_event and self._last_event[2] > now)
        if all_settled and not flash_active:
            self._timer.stop()
        self.update()

    def _carrier_entity(self, side):
        """Porteur = joueur de champ le plus proche du ballon (jeu continu)."""
        team = self._teams.get(side) or []
        shown = [e for e in team if e.get("shown") and not e.get("gk")]
        order = shown or [e for e in team if e.get("shown")]
        if not order:
            return None
        bx, by = self._ball["pos"]
        return min(order, key=lambda e: (e["pos"][0] - bx) ** 2 + (e["pos"][1] - by) ** 2)

    def _entity_by_name(self, side, text):
        """Retrouve le pion nommé dans un détail de passe (« X → Y »)."""
        text = str(text or "").strip()
        if not text:
            return None
        for ent in self._teams.get(side) or []:
            name = str(ent.get("name") or "").strip()
            if not name or not ent.get("shown"):
                continue
            compact_name = name.replace(" ", "").casefold()
            compact_text = text.replace(" ", "").casefold()
            if name in text or text in name or (compact_name and compact_name in compact_text):
                return ent
            last = name.split()[-1] if name.split() else ""
            if len(last) >= 3 and last.casefold() in text.casefold():
                return ent
        return None

    # ------------------------------------------------------------------ paint
    def paintEvent(self, event):
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing, True)
            w, h = float(self.width()), float(self.height())
            court = self._court_rect(w, h)
            painter.fillRect(QRectF(0, 0, w, h), QColor("#10131f"))
            self._paint_court(painter, court)
            self._paint_power_play(painter, court)
            self._paint_players(painter, court)
            self._paint_ball(painter, court)
            self._paint_action_chip(painter, court)
            self._paint_overlays(painter, court)
            painter.end()
        except Exception as exc:
            # un visuel ne doit jamais casser le match : on trace et on renonce
            import traceback
            print("[pitch2d] paint:", exc, file=sys.stderr)
            print(traceback.format_exc(), file=sys.stderr)

    def _court_rect(self, w, h):
        ratio = 40.0 / 20.0
        usable_w = w - 28; usable_h = h - 26
        cw = usable_w; ch = cw / ratio
        if ch > usable_h:
            ch = usable_h; cw = ch * ratio
        x0 = (w - cw) / 2.0; y0 = (h - ch) / 2.0
        return QRectF(x0, y0, cw, ch)

    def _paint_court(self, painter, rect):
        key=(int(rect.x()),int(rect.y()),int(rect.width()),int(rect.height()),self.devicePixelRatioF())
        if self._court_cache is None or self._court_cache_key != key:
            pm=QPixmap(max(1,self.width()),max(1,self.height()))
            pm.fill(Qt.transparent)
            cp=QPainter(pm)
            cp.setRenderHint(QPainter.Antialiasing, True)
            self._draw_court(cp, rect)
            cp.end()
            self._court_cache=pm; self._court_cache_key=key
        painter.drawPixmap(0,0,self._court_cache)

    def _draw_court(self, painter, rect):
        court = QColor("#0f241b")
        painter.setPen(QPen(QColor("#3b5d4d"), max(1.0, rect.height() / 90.0)))
        painter.setBrush(QBrush(court))
        painter.drawRoundedRect(rect, rect.height() / 14.0, rect.height() / 14.0)
        line = QPen(QColor("#4e7a63"), max(1.0, rect.height() / 160.0))
        painter.setPen(line); painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QRectF(rect.center().x() - rect.width() / 8.0,
                                   rect.center().y() - rect.height() / 8.0,
                                   rect.width() / 4.0, rect.height() / 4.0))
        painter.drawLine(QPointF(rect.center().x(), rect.top()),
                         QPointF(rect.center().x(), rect.bottom()))
        zone_w = rect.width() * 0.10; zone_h = rect.height() * 0.55
        painter.drawRoundedRect(QRectF(rect.left(), rect.center().y() - zone_h / 2, zone_w, zone_h),
                                zone_w / 3.0, zone_w / 3.0)
        painter.drawRoundedRect(QRectF(rect.right() - zone_w, rect.center().y() - zone_h / 2, zone_w, zone_h),
                                zone_w / 3.0, zone_w / 3.0)
        goal_h = rect.height() * 0.22
        painter.setBrush(QBrush(QColor("#dfe7f2")))
        painter.setPen(QPen(QColor("#c8d2e0"), 1.0))
        painter.drawRect(QRectF(rect.left() - rect.width() * 0.008, rect.center().y() - goal_h / 2,
                                rect.width() * 0.012, goal_h))
        painter.drawRect(QRectF(rect.right() - rect.width() * 0.004, rect.center().y() - goal_h / 2,
                                rect.width() * 0.012, goal_h))

    def _paint_power_play(self, painter, rect):
        for side in ("h", "a"):
            if self._players_on.get(side, 5) < 5 and self._phase == "live":
                # la moitie coloree est la moitie D'ATTAQUE de l'equipe en
                # inferiorite numerique (suit le changement de cotes de la 2E)
                on_right = self._side_attacks_right(side)
                x0 = rect.center().x() if on_right else rect.left()
                zone = QRectF(x0, rect.top(), rect.width() * 0.5, rect.height())
                painter.fillRect(zone, QColor(255, 179, 71, 26))

    def _dot_radius(self, rect):
        return max(6.0, rect.height() / 22.0)

    def _paint_players(self, painter, rect):
        radius = self._dot_radius(rect)
        font = QFont(self.font())
        font.setPixelSize(int(radius * 1.25))
        font.setBold(True)
        painter.setFont(font)
        for side in ("h", "a"):
            color = QColor(self._colors[side])
            for i, ent in enumerate(self._teams[side]):
                if not ent.get("shown"):
                    continue
                off_slot = self._sent_off_slot.get(side)
                if off_slot is not None and i == off_slot:
                    continue
                x = rect.left() + ent["pos"][0] * rect.width()
                y = rect.top() + ent["pos"][1] * rect.height()
                alpha = int(255 * (0.35 + 0.65 * ent.get("alpha", 1.0)))
                fill = QColor(color)
                fill.setAlpha(alpha)
                ring = QColor("#e8ecf6"); ring.setAlpha(150)
                kit = self._scaled_kit(side, radius * 3.1)
                if kit is not None:
                    # MAILLOT DU CLUB : couleurs + motif, comme les vignettes.
                    painter.setOpacity(alpha / 255.0)
                    painter.drawPixmap(QPointF(x - kit.width() / 2.0, y - kit.height() / 2.0), kit)
                    painter.setOpacity(1.0)
                    # anneau discret pour détacher le maillot du terrain
                    painter.setBrush(Qt.NoBrush)
                    rq=QColor("#ffffff"); rq.setAlpha(70 if not ent.get("gk") else 160)
                    painter.setPen(QPen(rq, max(1.0, radius / 10.0)))
                    painter.drawEllipse(QPointF(x, y), radius * 1.32, radius * 1.32)
                    if ent.get("gk"):
                        painter.setPen(QPen(QColor("#ffd36e"), max(1.6, radius / 7.0)))
                        painter.drawEllipse(QPointF(x, y), radius * 1.5, radius * 1.5)
                    if radius >= 8.0:
                        num=str(ent.get("number") or "•")
                        fnum=QFont(self.font()); fnum.setPixelSize(max(7, int(radius * 0.95))); fnum.setBold(True)
                        painter.setFont(fnum)
                        nrect=QRectF(x-radius*0.9, y-radius*0.55, radius*1.8, radius*1.1)
                        painter.setPen(QPen(QColor(0,0,0,190), max(1.0, radius*0.16)))
                        painter.setBrush(Qt.NoBrush)
                        tpath=QPainterPath(); fmn=painter.fontMetrics()
                        tw=fmn.horizontalAdvance(num)
                        tpath.addText(QPointF(x-tw/2.0, y+fmn.ascent()/2.0-fmn.descent()/2.0), fnum, num)
                        painter.drawPath(tpath)
                        painter.setPen(Qt.NoPen); painter.setBrush(QColor("#ffffff")); painter.drawPath(tpath)
                else:
                    painter.setPen(QPen(ring, max(1.0, radius / 9.0)))
                    painter.setBrush(QBrush(fill))
                    if ent.get("gk"):
                        painter.drawEllipse(QPointF(x, y), radius * 1.25, radius * 1.25)
                    elif side == "a":
                        # Forme géométrique différente : même deux couleurs
                        # proches restent immédiatement identifiables.
                        painter.drawPolygon(QPolygonF([
                            QPointF(x, y-radius), QPointF(x+radius, y),
                            QPointF(x, y+radius), QPointF(x-radius, y)]))
                    else:
                        painter.drawEllipse(QPointF(x, y), radius, radius)
                    if radius >= 9.0:
                        painter.setPen(QPen(QColor("#10131f")))
                        painter.drawText(QRectF(x - radius, y - radius, radius * 2, radius * 2),
                                         Qt.AlignCenter, str(ent.get("number") or "•"))

    def _paint_ball(self, painter, rect):
        now = time.monotonic()
        radius = max(3.0, rect.height() / 40.0)
        # Traînée : le ballon laisse une trace sur les frappes et les passes vives.
        for tx, ty, stamp in list(getattr(self, "_ball_trail", [])):
            age = now - stamp
            if age >= 0.45:
                continue
            life = 1.0 - age / 0.45
            px = rect.left() + tx * rect.width()
            py = rect.top() + ty * rect.height()
            trail_color = QColor("#dfe9f7")
            trail_color.setAlpha(int(80 * life))
            painter.setPen(Qt.NoPen)
            painter.setBrush(trail_color)
            tr = radius * (0.30 + 0.55 * life)
            painter.drawEllipse(QPointF(px, py), tr, tr)
        x = rect.left() + self._ball["pos"][0] * rect.width()
        y = rect.top() + self._ball["pos"][1] * rect.height()
        # Ombre portée : le ballon se détache du parquet.
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 95))
        painter.drawEllipse(QPointF(x + radius * 0.40, y + radius * 0.60), radius, radius * 0.85)
        painter.setPen(QPen(QColor("#20232b"), max(1.0, radius * 0.22)))
        painter.setBrush(QBrush(QColor("#f8fbff")))
        painter.drawEllipse(QPointF(x, y), radius, radius)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 255, 190))
        painter.drawEllipse(QPointF(x - radius * 0.30, y - radius * 0.36), radius * 0.34, radius * 0.28)

    def _paint_action_chip(self, painter, rect):
        if not self._last_event:
            return
        now = time.monotonic()
        label, side, until = self._last_event[:3]
        remaining = until - now
        if remaining <= 0:
            self._last_event = None
            self._last_event_detail = ""
            return
        started = self._last_event[3] if len(self._last_event) > 3 else (until - MARKER_MS / 1000.0)
        detail = (self._last_event_detail or "").strip()
        if len(detail) > 54:
            detail = detail[:52] + "…"
        color = QColor(self._colors[side])
        fade_in = min(1.0, max(0.0, (now - started) / 0.12))
        fade_out = min(1.0, max(0.0, remaining / 0.35))
        alpha = int(255 * fade_in * fade_out)
        label_px = max(10, int(rect.height() / 15.0))
        detail_px = max(8, int(rect.height() / 24.0))
        f_label = QFont(self.font()); f_label.setPixelSize(label_px); f_label.setBold(True)
        f_detail = QFont(self.font()); f_detail.setPixelSize(detail_px)
        pad = max(8, int(rect.height() / 48.0))
        fm_label = QFontMetrics(f_label)
        fm_detail = QFontMetrics(f_detail)
        text_w = max(fm_label.horizontalAdvance(label),
                     fm_detail.horizontalAdvance(detail) if detail else 0)
        box_w = min(rect.width() * 0.92, text_w + pad * 4 + 12)
        box_h = pad * 2 + label_px + (detail_px + 3 if detail else 0)
        box = QRectF(rect.center().x() - box_w / 2, rect.top() + 7, box_w, box_h)
        bg = QColor(9, 14, 24); bg.setAlpha(int(205 * alpha / 255))
        painter.setPen(Qt.NoPen); painter.setBrush(bg)
        painter.drawRoundedRect(box, box_h / 2.6, box_h / 2.6)
        border = QColor(color); border.setAlpha(int(200 * alpha / 255))
        painter.setPen(QPen(border, 1.4)); painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(box.adjusted(1, 1, -1, -1), box_h / 2.6, box_h / 2.6)
        dot = QColor(color); dot.setAlpha(int(235 * alpha / 255))
        painter.setPen(Qt.NoPen); painter.setBrush(dot)
        painter.drawEllipse(QPointF(box.left() + pad * 1.6, box.center().y()), 3.2, 3.2)
        painter.setFont(f_label)
        painter.setPen(QPen(QColor(255, 255, 255, int(240 * alpha / 255))))
        painter.drawText(QRectF(box.left() + pad * 3, box.top() + pad * 0.7,
                                box.width() - pad * 4, label_px + 2),
                         Qt.AlignHCenter | Qt.AlignVCenter, label)
        if detail:
            painter.setFont(f_detail)
            painter.setPen(QPen(QColor(color).lighter(135), int(230 * alpha / 255)))
            painter.drawText(QRectF(box.left() + pad * 2, box.top() + pad * 0.7 + label_px + 1,
                                    box.width() - pad * 3, detail_px + 4),
                             Qt.AlignHCenter | Qt.AlignVCenter, detail)

    def _paint_overlays(self, painter, rect):
        now = time.monotonic()
        if self._goal_flash and self._goal_flash[1] > now:
            side = self._goal_flash[0]
            until = self._goal_flash[1]
            prog = 1.0 - max(0.0, min(1.0, (until - now) * 1000.0 / FLASH_MS))
            color = QColor(self._colors[side])
            color.setAlpha(int(84 * (1.0 - prog) + 26))
            goal_h = rect.height() * 0.5
            if self._side_attacks_right(side):
                zone = QRectF(rect.right() - rect.width() * 0.18, rect.center().y() - goal_h / 2,
                              rect.width() * 0.18, goal_h)
            else:
                zone = QRectF(rect.left(), rect.center().y() - goal_h / 2,
                              rect.width() * 0.18, goal_h)
            painter.fillRect(zone, color)
            # ondes concentriques au point de but (impact visible franchement)
            mouth = QPointF(zone.center().x() - (0.0 if self._side_attacks_right(side) else zone.width()),
                            rect.center().y())
            painter.setBrush(Qt.NoBrush)
            pen = QPen(QColor(self._colors[side])); pen.setWidthF(max(2.0, rect.height() / 55.0))
            painter.setPen(pen)
            for k in range(3):
                r = rect.height() * (0.10 + 0.32 * prog + 0.10 * k)
                painter.drawEllipse(mouth, r, r)
            # POPUP BUT 2D : carte agrandie, club sur DEUX lignes si besoin,
            # buteur en dessous, encre clignotante blanc <> couleur du club.
            hm_colors = self._names or ("DOMICILE", "EXTÉRIEUR")
            club = str(hm_colors[0] if side == "h" else hm_colors[1])
            scorer, _side, _until = (self._goal_info or ("", side, until))
            who = str(scorer) if scorer and scorer != "BUT" else ""
            club_color = QColor(self._colors[side]).lighter(135)
            blink_on = (int(now * 3.0) % 2) == 0
            head_txt = "BUT !   " + club
            # Le nom du club reste sur UNE ligne : on réduit légèrement la
            # police au lieu de couper le nom en deux.
            head_px = int(max(15, rect.height() / 9.5))
            while head_px > 12:
                _f = QFont(self.font()); _f.setPixelSize(head_px); _f.setBold(True)
                if QFontMetrics(_f).horizontalAdvance(head_txt) <= rect.width() * 0.84:
                    break
                head_px -= 2
            head_font = QFont(self.font()); head_font.setPixelSize(head_px); head_font.setBold(True)
            hair_painter = QFontMetrics(head_font)
            text_w = rect.width() * 0.92
            head_rect = hair_painter.boundingRect(QRectF(0, 0, text_w, 1000).toRect(),
                                                  int(Qt.AlignHCenter | Qt.AlignTop | Qt.TextSingleLine), head_txt)
            sub_font = QFont(self.font()); sub_font.setPixelSize(int(max(13, rect.height() / 11.0))); sub_font.setBold(True)
            sub_metrics = QFontMetrics(sub_font)
            who_rect = sub_metrics.boundingRect(QRectF(0, 0, text_w * 0.95, 400).toRect(),
                                                int(Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap), who) if who else None
            pad = max(12, int(rect.height() * 0.035))
            box_w = min(rect.width() * 0.82, max(head_rect.width(), who_rect.width() if who_rect else 0) + pad * 2)
            box_h = head_rect.height() + (who_rect.height() + 4 if who_rect else 0) + pad * 2
            box = QRectF(rect.center().x() - box_w / 2,
                         rect.center().y() - box_h / 2 + rect.height() * 0.14, box_w, box_h)
            # Fond sombre translucide + liseré club : le texte reste lisible
            # sur n'importe quel maillot ou zone du terrain.
            alpha_bg = 215
            bg = QColor(9, 14, 24); bg.setAlpha(alpha_bg)
            painter.setPen(Qt.NoPen); painter.setBrush(bg)
            painter.drawRoundedRect(box, 10, 10)
            border = QColor(club_color); border.setAlpha(170 if blink_on else 90)
            painter.setPen(QPen(border, 2)); painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(box.adjusted(1, 1, -1, -1), 9, 9)
            # LIGNE 1 — club (peut occuper deux lignes, jamais tronqué en plein mot)
            painter.setFont(head_font)
            pen1 = QColor(club_color) if blink_on else QColor("#ffffff")
            pen1.setAlpha(238 if blink_on else 210)
            painter.setPen(QPen(pen1))
            painter.drawText(QRectF(box.left() + pad, box.top() + pad, box.width() - pad * 2, head_rect.height()),
                             Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap, head_txt)
            # LIGNE 2 — buteur
            if who:
                painter.setFont(sub_font)
                pen2 = QColor("#ffffff") if blink_on else QColor(club_color)
                pen2.setAlpha(235 if blink_on else 205)
                painter.setPen(QPen(pen2))
                painter.drawText(QRectF(box.left() + pad, box.top() + pad + head_rect.height() + 4,
                                        box.width() - pad * 2, who_rect.height()),
                                 Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap, who)
        if self._goal_flash and self._goal_flash[1] <= now:
            self._goal_flash = None; self._goal_info = None
        text = None
        if self._phase == "prematch":
            text = "AVANT-MATCH  •  coup d'envoi en attente"
        elif self._phase == "halft":
            text = "MI-TEMPS  •  chrono bloqué"
        elif self._phase == "fullt":
            text = "FIN DU MATCH"
        if not text:
            return
        font = QFont(self.font())
        font.setPixelSize(max(9, int(rect.height() / 22.0)))
        font.setBold(True)
        painter.setFont(font)
        metrics = QFontMetrics(font)
        tw = metrics.horizontalAdvance(text)
        pad_x, pad_y = max(12, int(rect.height() / 34.0)), max(5, int(rect.height() / 90.0))
        box = QRectF(rect.center().x() - (tw + pad_x * 2) / 2.0,
                     rect.center().y() - (metrics.height() + pad_y * 2) / 2.0,
                     tw + pad_x * 2, metrics.height() + pad_y * 2)
        bg = QColor(9, 14, 24, 190)
        painter.setPen(Qt.NoPen); painter.setBrush(bg)
        painter.drawRoundedRect(box, box.height() / 2.4, box.height() / 2.4)
        border = QColor("#8fa2b8"); border.setAlpha(110)
        painter.setPen(QPen(border, 1.2)); painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(box.adjusted(1, 1, -1, -1), box.height() / 2.4, box.height() / 2.4)
        painter.setPen(QPen(QColor("#c9d8ea")))
        painter.drawText(box, Qt.AlignHCenter | Qt.AlignVCenter, text)


class LiveMatchBanner(MatchActionBanner):
    """Bandeau du moteur + retransmission des actions au terrain."""

    def __init__(self, pitch=None, parent=None):
        super().__init__(parent)
        self._pitch = pitch
        # Côté MOTEUR du club du joueur ("h" quand nous sommes domicile) :
        # les événements arrivent en cotes moteurs ; ce remappage évite
        # l'inversion nom/couleur des buts à l'EXTÉRIEUR.
        self._engine_user_side = "h"

    def bind_pitch(self, pitch):
        self._pitch = pitch

    def set_colors(self, home_color, away_color):
        """Applique le même contraste que le terrain 2D au bandeau/popup."""
        hc,ac=display_team_colors(home_color, away_color)
        super().set_colors(hc.name(),ac.name())

    def _coach_side(self, side):
        """Côté moteur (h = domicile réel) -> slot coach (h = club du joueur)."""
        return "h" if str(side) == str(self._engine_user_side) else "a"

    def animate_action(self, side="h", kind="build", detail=""):
        super().animate_action(self._coach_side(side), kind, detail)
        if self._pitch is not None:
            try:
                self._pitch.note_event(self._coach_side(side), kind, detail)
            except Exception:
                pass


# ------------------------------------------------------------------ possession live
class PossessionBar(QWidget):
    """Barre de possession home/away (mouchard lecture-seule).

    Deux moities colorees selon le % de possession du club du joueur ; mise
    a jour a chaque minute depuis les stats du moteur (advance_minute)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(9)
        self._share_h = 50
        self._colors = ("#66ff88", "#ff6688")

    def set_values(self, share_home):
        try:
            self._share_h = max(0, min(100, int(share_home)))
            self.update()
        except Exception:
            pass

    def set_colors(self, home, away):
        self._colors = (str(home or "#66ff88"), str(away or "#ff6688"))
        self.update()

    def paintEvent(self, event):
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing, False)
            rect = self.rect()
            painter.fillRect(rect, QColor("#12182a"))
            split = int(rect.width() * self._share_h / 100.0)
            painter.fillRect(QRectF(rect.x(), rect.y(), split, rect.height()),
                             QColor(self._colors[0]))
            painter.fillRect(QRectF(rect.x() + split, rect.y(),
                                    rect.width() - split, rect.height()),
                             QColor(self._colors[1]))
            painter.setPen(QPen(QColor("#8fa2b8")))
            painter.setFont(QFont(self.font()))
            painter.drawText(rect, Qt.AlignCenter,
                             "%d%% — %d%%" % (self._share_h, 100 - self._share_h))
            painter.end()
        except Exception:
            pass


# ------------------------------------------------------------------ boutons immersifs
class MatchPlayButton(QPushButton):
    """Bouton play/pause du direct : grand, code couleur selon l'etat.

    Le moteur change le texte du bouton a divers endroits (lancement,
    pause, reprise 2e mi-temps, fin) : la couleur suit AUTOMATIQUEMENT le
    libelle via setText() surcharge — aucun appel moteur a modifier.
      ▶ (reprendre / 2e mi-temps)  -> vert lisible "on peut lancer"
      Ⅱ (pause)                    -> ambre "le direct file"
      autre (MATCH TERMINE…)       -> gris neutre
    """

    STYLES = {
        "play": "QPushButton{background:#123526;color:#7de0aa;border:1.5px solid #2f7a52;"
                "border-radius:9px;font-weight:900;font-size:11.5pt;padding:6px 16px;}"
                "QPushButton:hover{background:#1a4a33;border-color:#43b07a;}"
                "QPushButton:disabled{background:#131722;color:#5d6a80;border-color:#2a3148;}",
        "pause": "QPushButton{background:#3d2c0e;color:#f0c469;border:1.5px solid #8a6a2a;"
                 "border-radius:9px;font-weight:900;font-size:11.5pt;padding:6px 16px;}"
                 "QPushButton:hover{background:#553c12;border-color:#c59b41;}"
                 "QPushButton:disabled{background:#131722;color:#5d6a80;border-color:#2a3148;}",
        "neutral": "",
    }

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._restyle(text)

    def setText(self, text):  # noqa: N802 - surcharge Qt volontaire
        super().setText(text)
        self._restyle(str(text))

    def _restyle(self, text):
        try:
            if "\u25b6" in text:          # ▶
                self.setStyleSheet(self.STYLES["play"])
            elif "\u2161" in text:        # Ⅱ
                self.setStyleSheet(self.STYLES["pause"])
            elif "PAUSE" in text:
                self.setStyleSheet(self.STYLES["pause"])
            elif ("REPRENDRE" in text) or ("LANCER" in text):
                self.setStyleSheet(self.STYLES["play"])
            else:
                self.setStyleSheet(self.STYLES["neutral"])
        except Exception:
            pass
