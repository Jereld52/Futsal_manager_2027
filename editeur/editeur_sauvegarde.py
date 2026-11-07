# -*- coding: utf-8 -*-
"""Éditeur de sauvegarde FM2027 — outil autonome, hors du jeu.

Ouvre directement un fichier de sauvegarde SQLite et permet de modifier :
- les clubs (budget, réputation, division, salle) ;
- les joueurs (identité, club, attributs, potentiel, valeur, salaire, contrat,
  condition, moral, blessures, suspension, statut) ;
- le staff (embauche, niveau, nom, nationalité) ;
- les infrastructures et les tarifs.

Sécurité :
- aucune écriture sans validation ;
- sauvegarde de secours automatique avant la première modification ;
- détection d'une sauvegarde verrouillée (jeu ouvert) ;
- l'éditeur ne crée ni ne supprime aucune table.

Lancement : EDITEUR.bat ou `python editeur_sauvegarde.py`.
"""
from __future__ import annotations

import os
import csv
import re
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QLocale, Qt
from PySide6.QtGui import QColor, QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QFrame, QGridLayout,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QPushButton, QScrollArea, QSpinBox, QSplitter, QTabWidget, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget, QAbstractItemView, QSizePolicy,
)

if getattr(sys, "frozen", False):
    BASE_DIR = Path(os.environ.get("APPDATA") or os.path.expanduser("~")) / "FM2027V2"
    DATA_DIR = BASE_DIR / "data"
else:
    HERE = Path(__file__).resolve().parent
    ROOT = HERE.parent
    DATA_DIR = ROOT / "data"
SAVE_DIR = DATA_DIR / "saves"
ACTIVE_SAVE = DATA_DIR / "active_save.txt"

QLocale.setDefault(QLocale("fr_FR"))

REQUIRED_TABLES = {"club", "player", "career", "facility", "meta"}

STAFF_ROLES = (
    ("adjoint_hired", "Adjoint"),
    ("architecte_hired", "Architecte"),
    ("comptable_hired", "Comptable"),
    ("directeur_sportif_hired", "Directeur sportif"),
    ("marketing_hired", "Responsable marketing"),
    ("physio_hired", "Kiné"),
    ("preparateur_physique_hired", "Préparateur physique"),
    ("scout_staff_hired", "Recruteur"),
)

FACILITY_LEVELS = (
    ("arena_level", "Tribunes & capacité", 1, 8),
    ("medical_level", "Pôle médical", 1, 8),
    ("youth_level", "Centre de formation", 1, 8),
    ("marketing_level", "Marketing", 1, 8),
    ("lighting_level", "Éclairage & diffusion", 1, 8),
    ("parking_level", "Parking & accès", 1, 8),
    ("video_level", "Laboratoire vidéo", 0, 3),
    ("volunteer_level", "Bénévoles", 0, 3),
    ("restaurant_level", "Restaurant", 0, 3),
)

FACILITY_FLAGS = (
    ("has_bar", "Bar"),
    ("has_vip", "Loges VIP"),
    ("has_shop", "Boutique"),
    ("has_rental_courts", "Courts en location"),
    ("has_events_hall", "Salle événements"),
    ("has_fan_zone", "Fan zone"),
)

ATTRS = (
    ("technique", "Technique"), ("passing", "Passe"), ("finishing", "Finition"),
    ("defense", "Défense"), ("stamina", "Endurance"), ("speed", "Vitesse"),
    ("dribble", "Dribble"), ("positioning", "Placement"), ("goalkeeper", "Arrêts"),
)

POSITIONS = ("Gardien", "Défenseur", "Universel", "Pivot", "Ailier")

# Même barème que le jeu pour la valeur marchande (app.compute_market_value).
MARKET_POSITION_FACTOR = {"Gardien": 0.85, "Défenseur": 0.95, "Universel": 1.0,
                          "Pivot": 1.08, "Ailier": 1.12}


class SaveError(Exception):
    """Erreur lisible destinée à l'utilisateur."""


def rating20(value) -> int:
    return max(1, min(20, int(round(float(value or 0)))))


def round_money(value) -> int:
    try:
        v = int(float(value))
    except (TypeError, ValueError):
        return 0
    sign = 1 if v >= 0 else -1
    v = abs(v)
    if v < 2000:
        step = 100
    elif v < 20000:
        step = 500
    elif v < 100000:
        step = 2500
    elif v < 500000:
        step = 10000
    elif v < 2000000:
        step = 50000
    elif v < 10000000:
        step = 250000
    else:
        step = 1000000
    return sign * ((v + step // 2) // step * step)


def player_level(row) -> int:
    keys = ["technique", "passing", "finishing", "defense", "stamina"]
    if row["position"] == "Gardien":
        keys.append("goalkeeper")
    return rating20(sum(int(row[k] or 0) for k in keys) / len(keys))


def player_potential(row) -> int:
    stored = row["potential_fixed"] if "potential_fixed" in row.keys() else None
    if stored is not None:
        return max(1, min(20, int(round(float(stored)))))
    age = int(row["age"] or 25)
    growth = 4 if age < 19 else 3 if age < 23 else 2 if age < 27 else 1 if age < 31 else 0
    return min(20, player_level(row) + growth)


def money(value) -> str:
    return f"{int(value or 0):,}".replace(",", " ") + " €"


SORT_ROLE = Qt.UserRole + 20


class SortableItem(QTableWidgetItem):
    """Cellule triable : affiche un texte lisible, trie sur une valeur typée."""

    def __init__(self, text, sort_value=None):
        super().__init__(str(text))
        if sort_value is not None:
            self.setData(SORT_ROLE, sort_value)

    def __lt__(self, other):
        left = self.data(SORT_ROLE)
        right = other.data(SORT_ROLE) if isinstance(other, QTableWidgetItem) else None
        if left is not None and right is not None:
            try:
                return left < right
            except TypeError:
                pass
        return super().__lt__(other)


STATUS_LABELS = ("DISPONIBLE", "BLESSÉ", "SUSPENDU", "SUR LA LISTE",
                 "PRÊT", "LIBRE", "RETRAITÉ")
STATUS_COLORS = {
    "DISPONIBLE": "#8fe0a3", "BLESSÉ": "#ff8d97", "SUSPENDU": "#f1a34f",
    "SUR LA LISTE": "#ffd98a", "PRÊT": "#6fc8ff", "LIBRE": "#c89aff",
    "RETRAITÉ": "#8a97ab",
}


def player_status(row) -> str:
    """Statut lisible d'un joueur (même logique que la colonne STATUT)."""
    if int(row["retired"] or 0) if "retired" in row.keys() else 0:
        return "RETRAITÉ"
    if int(row["is_free_agent"] or 0):
        return "LIBRE"
    if int(row["loan_from_club"] or 0):
        return "PRÊT"
    if int(row["suspension_matches"] or 0) or int(row["suspension_days"] or 0):
        return "SUSPENDU"
    if int(row["injury_matches"] or 0) or int(row["injury_days"] or 0):
        return "BLESSÉ"
    if int(row["transfer_listed"] or 0):
        return "SUR LA LISTE"
    return "DISPONIBLE"


def filter_players(rows, filters):
    """Filtres avancés, appliqués côté éditeur (la base reste en lecture simple).

    filters attendu : position, age_min, age_max, level_min, potential_min,
    value_min, value_max, contract_max, status. Les valeurs 0 / "" / -1
    désactivent le filtre correspondant.
    """
    position = str(filters.get("position") or "")
    status = str(filters.get("status") or "")
    age_min = int(filters.get("age_min") or 0)
    age_max = int(filters.get("age_max") or 0)
    level_min = int(filters.get("level_min") or 0)
    potential_min = int(filters.get("potential_min") or 0)
    value_min = int(filters.get("value_min") or 0)
    value_max = int(filters.get("value_max") or 0)
    contract_max = int(filters.get("contract_max", -1))
    result = []
    for row in rows:
        age = int(row["age"] or 0)
        if position and row["position"] != position:
            continue
        if age_min and age < age_min:
            continue
        if age_max and age > age_max:
            continue
        if level_min and player_level(row) < level_min:
            continue
        if potential_min and player_potential(row) < potential_min:
            continue
        value = int(row["market_value"] or 0)
        if value_min and value < value_min:
            continue
        if value_max and value > value_max:
            continue
        if contract_max >= 0 and int(row["contract_years"] or 0) > contract_max:
            continue
        if status and player_status(row) != status:
            continue
        result.append(row)
    return result


CSV_COLUMNS = ("ID", "Prénom", "Nom", "Club", "Division", "Poste", "Âge",
               "Nationalité", "Niveau", "Potentiel", "Technique", "Passe",
               "Finition", "Défense", "Endurance", "Vitesse", "Dribble",
               "Placement", "Arrêts", "Valeur", "Salaire", "Contrat",
               "Condition", "Moral", "Statut")


def export_players_csv(path, rows):
    """Exporte la liste filtrée en CSV lisible (séparateur point-virgule)."""
    with open(path, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle, delimiter=";")
        writer.writerow(CSV_COLUMNS)
        for row in rows:
            writer.writerow([
                row["id"], row["first_name"], row["last_name"],
                row["club_name"] or "Libre", row["club_division"] or "",
                row["position"], row["age"], row["nationality"] or "",
                player_level(row), player_potential(row),
                rating20(row["technique"]), rating20(row["passing"]),
                rating20(row["finishing"]), rating20(row["defense"]),
                rating20(row["stamina"]), rating20(row["speed"]),
                rating20(row["dribble"]), rating20(row["positioning"]),
                rating20(row["goalkeeper"]),
                int(row["market_value"] or 0), int(row["salary"] or 0),
                int(row["contract_years"] or 0), int(row["condition"] or 0),
                int(row["morale"] or 0), player_status(row),
            ])
    return path


def select_save_files():
    files = []
    if SAVE_DIR.is_dir():
        files = [str(p) for p in SAVE_DIR.glob("*.db") if p.is_file()]
    return sorted(files, key=lambda p: os.path.getmtime(p), reverse=True)


def active_save_file():
    try:
        path = ACTIVE_SAVE.read_text(encoding="utf-8").strip()
        if path and os.path.isfile(path):
            return os.path.abspath(path)
    except OSError:
        pass
    files = select_save_files()
    return files[0] if files else ""


class SaveStore:
    """Accès contrôlé à une sauvegarde FM2027 (aucune migration de schéma)."""

    def __init__(self, path):
        self.path = os.path.abspath(path)
        if not os.path.isfile(self.path):
            raise SaveError(f"Fichier introuvable : {self.path}")
        self.conn = sqlite3.connect(self.path, timeout=3, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA busy_timeout=2500")
        try:
            tables = {r["name"] for r in self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            missing = REQUIRED_TABLES - tables
            if missing:
                self.close()
                raise SaveError("Ce fichier n'est pas une sauvegarde FM2027 "
                                f"(tables manquantes : {', '.join(sorted(missing))}).")
            self.columns_cache = {}
            self.read_only = False
            self.lock_message = ""
            self.sidecar = any(os.path.exists(self.path + suffix)
                               for suffix in ("-wal", "-shm"))
            try:
                self.conn.execute("BEGIN IMMEDIATE")
                self.conn.execute("ROLLBACK")
            except sqlite3.OperationalError as exc:
                self.read_only = True
                self.lock_message = str(exc)
        except SaveError:
            raise
        except sqlite3.Error as exc:
            self.close()
            raise SaveError(f"Sauvegarde illisible : {exc}") from exc

    def close(self):
        try:
            if getattr(self, "conn", None) is not None:
                self.conn.close()
        except sqlite3.Error:
            pass
        self.conn = None

    # ---------- lecture ----------
    def columns(self, table):
        if table not in self.columns_cache:
            self.columns_cache[table] = {r[1] for r in self.conn.execute(f"PRAGMA table_info({table})")}
        return self.columns_cache[table]

    def career(self):
        return self.conn.execute("SELECT * FROM career WHERE id=1").fetchone()

    def clubs(self):
        return self.conn.execute(
            "SELECT id,name,division,budget,reputation,season,arena_name "
            "FROM club ORDER BY division,name COLLATE NOCASE").fetchall()

    def club(self, club_id):
        return self.conn.execute("SELECT * FROM club WHERE id=?", (int(club_id),)).fetchone()

    def players(self, search="", club_filter=0, include_retired=False):
        sql = ("SELECT p.*, c.name club_name, c.division club_division "
               "FROM player p LEFT JOIN club c ON c.id=p.club_id WHERE 1=1")
        args = []
        if search.strip():
            sql += " AND (p.first_name LIKE ? OR p.last_name LIKE ?)"
            term = f"%{search.strip()}%"
            args += [term, term]
        if club_filter > 0:
            sql += " AND p.club_id=?"
            args.append(int(club_filter))
        elif club_filter < 0:
            sql += " AND COALESCE(p.is_free_agent,0)=1"
        if not include_retired:
            sql += " AND COALESCE(p.retired,0)=0"
        sql += " ORDER BY c.division, c.name, p.last_name, p.first_name"
        return self.conn.execute(sql, args).fetchall()

    def player(self, player_id):
        return self.conn.execute("SELECT * FROM player WHERE id=?", (int(player_id),)).fetchone()

    def facility(self):
        return self.conn.execute("SELECT * FROM facility WHERE id=1").fetchone()

    def staff(self):
        rows = self.conn.execute("SELECT key,value FROM meta").fetchall()
        meta = {r["key"]: (r["value"] or "") for r in rows}
        result = []
        for key, label in STAFF_ROLES:
            level_key = self.staff_level_key(key)
            result.append({
                "key": key,
                "label": label,
                "hired": meta.get(key, "0") == "1",
                "level": int(meta.get(level_key, "1") or 1),
                "name": meta.get(f"staff_name_{key}", ""),
                "nat": meta.get(f"staff_nat_{key}", ""),
                "level_key": level_key,
            })
        return result

    @staticmethod
    def staff_level_key(hired_key):
        if hired_key == "scout_staff_hired":
            return "scout_level"
        if hired_key == "architecte_hired":
            return "architecte_level"
        return hired_key + "_level"

    def quick_check(self):
        try:
            return str(self.conn.execute("PRAGMA quick_check").fetchone()[0])
        except sqlite3.Error as exc:
            return f"erreur : {exc}"

    # ---------- écritures ----------
    def _begin(self):
        if self.read_only:
            raise SaveError("Sauvegarde verrouillée : ferme le jeu avant de modifier "
                            f"({self.lock_message or 'base ouverte ailleurs'}).")
        self.conn.execute("BEGIN IMMEDIATE")

    def _commit(self):
        self.conn.execute("COMMIT")

    def _rollback(self):
        try:
            self.conn.execute("ROLLBACK")
        except sqlite3.Error:
            pass

    @staticmethod
    def _check_int(value, label, low, high):
        try:
            number = int(value)
        except (TypeError, ValueError):
            raise SaveError(f"{label} : valeur entière attendue.")
        if number < low or number > high:
            raise SaveError(f"{label} doit être compris entre {low} et {high} (reçu {number}).")
        return number

    def update_club(self, club_id, budget, reputation, division, arena_name):
        club_id = self._check_int(club_id, "Club", 1, 10 ** 6)
        budget = self._check_int(budget, "Budget", 0, 2_000_000_000)
        reputation = self._check_int(reputation, "Réputation", 1, 100)
        division = self._check_int(division, "Division", 1, 6)
        arena_name = str(arena_name or "").strip()[:60]
        if not self.club(club_id):
            raise SaveError("Club inconnu.")
        self._begin()
        try:
            self.conn.execute(
                "UPDATE club SET budget=?,reputation=?,division=?,arena_name=? WHERE id=?",
                (budget, reputation, division, arena_name, club_id))
            self._commit()
        except Exception:
            self._rollback()
            raise

    def update_facility(self, levels, flags, ticket_price):
        values = {}
        for key, _label, low, high in FACILITY_LEVELS:
            values[key] = self._check_int(levels.get(key, low), _label, low, high)
        price = self._check_int(ticket_price, "Prix du billet", 1, 60)
        columns = self.columns("facility")
        assignments = [f"{k}=?" for k in values if k in columns]
        args = [v for k, v in values.items() if k in columns]
        for key, _label in FACILITY_FLAGS:
            if key in columns:
                assignments.append(f"{key}=?")
                args.append(1 if flags.get(key) else 0)
        if "ticket_price" in columns:
            assignments.append("ticket_price=?")
            args.append(price)
        if not assignments:
            raise SaveError("Table facility sans colonnes modifiables.")
        old_row = self.conn.execute("SELECT * FROM facility WHERE id=1").fetchone()
        self._begin()
        try:
            self.conn.execute("UPDATE facility SET " + ", ".join(assignments) + " WHERE id=1", args)
            # Plafond manuel : le jeu ne doit pas restaurer un niveau historique
            # supérieur (bâtiment volontairement baissé dans l'éditeur).
            for key, value in values.items():
                if old_row is not None and key in old_row.keys() and int(old_row[key] or 0) == value:
                    continue
                self.conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)",
                                  ("facility_editor_cap_" + key, str(value)))
                self.conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)",
                                  ("facility_max_" + key, str(value)))
                self.conn.execute(
                    "UPDATE facility_project SET target_level=? "
                    "WHERE facility_key=? AND status='completed' AND target_level>?",
                    (value, key, value))
                self.conn.execute(
                    "DELETE FROM facility_project WHERE facility_key=? "
                    "AND status='in_progress' AND target_level>?", (key, value))
            for key, flag in flags.items():
                if old_row is not None and key in old_row.keys() and int(old_row[key] or 0) == (1 if flag else 0):
                    continue
                self.conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)",
                                  ("facility_editor_cap_" + key, "1" if flag else "0"))
                if not flag:
                    self.conn.execute(
                        "DELETE FROM facility_project WHERE facility_key=? AND status='in_progress'",
                        (key,))
            self._commit()
        except Exception:
            self._rollback()
            raise

    def update_staff(self, entries):
        """entries : liste de dicts key/hired/level/name/nat."""
        clean = []
        for entry in entries:
            key = entry["key"]
            if key not in {k for k, _ in STAFF_ROLES}:
                raise SaveError(f"Rôle de staff inconnu : {key}")
            level = self._check_int(entry.get("level", 1), "Niveau du staff", 1, 5)
            name = str(entry.get("name") or "").strip()[:60]
            nat = str(entry.get("nat") or "").strip()[:40]
            clean.append((key, 1 if entry.get("hired") else 0, level, name, nat))
        self._begin()
        try:
            for key, hired, level, name, nat in clean:
                self.conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)",
                                  (key, str(hired)))
                self.conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)",
                                  (self.staff_level_key(key), str(level if hired else level)))
                if name:
                    self.conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)",
                                      (f"staff_name_{key}", name))
                if nat:
                    self.conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)",
                                      (f"staff_nat_{key}", nat))
            self._commit()
        except Exception:
            self._rollback()
            raise

    def apply_player(self, player_id, data):
        row = self.player(player_id)
        if not row:
            raise SaveError("Joueur introuvable.")
        first = str(data.get("first_name") or "").strip()[:40]
        last = str(data.get("last_name") or "").strip()[:40]
        if not first or not last:
            raise SaveError("Le prénom et le nom sont obligatoires.")
        age = self._check_int(data.get("age"), "Âge", 15, 60)
        position = str(data.get("position") or "")
        if position not in POSITIONS:
            raise SaveError("Poste invalide.")
        nationality = str(data.get("nationality") or "").strip()[:40] or "Inconnue"
        shirt = self._check_int(data.get("shirt_number", 0), "Numéro de maillot", 0, 99)
        potential = self._check_int(data.get("potential", 1), "Potentiel", 1, 20)
        salary = self._check_int(data.get("salary", 0), "Salaire", 0, 10_000_000)
        value = self._check_int(data.get("market_value", 0), "Valeur", 0, 100_000_000)
        years = self._check_int(data.get("contract_years", 0), "Contrat", 0, 10)
        condition = self._check_int(data.get("condition", 100), "Condition", 0, 100)
        morale = self._check_int(data.get("morale", 70), "Moral", 0, 100)
        injury_matches = self._check_int(data.get("injury_matches", 0), "Blessure (matchs)", 0, 365)
        injury_days = self._check_int(data.get("injury_days", 0), "Blessure (jours)", 0, 365)
        suspension_matches = self._check_int(data.get("suspension_matches", 0), "Suspension (matchs)", 0, 365)
        suspension_days = self._check_int(data.get("suspension_days", 0), "Suspension (jours)", 0, 365)
        yellow = self._check_int(data.get("yellow_cards", 0), "Cartons jaunes", 0, 99)
        target_club = self._check_int(data.get("club_id", 0), "Club", 0, 10 ** 6)
        free_agent = target_club == 0
        if target_club > 0 and not self.club(target_club):
            raise SaveError("Club de destination inconnu.")
        attrs_ui = {key: self._check_int(data.get(key, 10), label, 1, 20)
                    for key, label in ATTRS}
        attrs = {key: value * 5 for key, value in attrs_ui.items()}
        keys = ["technique", "passing", "finishing", "defense", "stamina"]
        if position == "Gardien":
            keys.append("goalkeeper")
        level = max(1, min(20, int(round(sum(attrs_ui[k] for k in keys) / len(keys)))))
        notice = ""
        if potential < level:
            potential = level
            notice = f"Potentiel relevé à {level} pour rester ≥ niveau."

        old_club = int(row["club_id"] or 0)
        club_changed = target_club > 0 and target_club != old_club
        new_club = target_club if target_club > 0 else old_club

        if shirt > 0 and new_club:
            clash = self.conn.execute(
                "SELECT id FROM player WHERE club_id=? AND shirt_number=? AND id<>? "
                "AND COALESCE(retired,0)=0", (new_club, shirt, int(player_id))).fetchone()
            if clash:
                shirt = 0
                notice = (notice + " " if notice else "") + "Numéro déjà pris : libéré."

        columns = self.columns("player")
        values = {
            "first_name": first, "last_name": last, "age": age, "position": position,
            "nationality": nationality, "shirt_number": shirt, "potential_fixed": potential,
            "salary": salary, "market_value": value, "contract_years": years,
            "condition": condition, "morale": morale,
            "injury_matches": injury_matches, "injury_days": injury_days,
            "suspension_matches": suspension_matches, "suspension_days": suspension_days,
            "yellow_cards": yellow,
            "transfer_listed": 1 if data.get("transfer_listed") else 0,
            "is_free_agent": 1 if free_agent else 0,
        }
        values.update(attrs)
        if club_changed:
            values.update({
                "club_id": new_club,
                "loan_from_club": 0, "loan_until_season": 0, "loan_promise": "",
                "loan_start_matches": 0, "loan_start_date": "",
                "precontract_club": 0, "precontract_from": 0, "precontract_salary": 0,
                "precontract_years": 0,
            })
        elif free_agent and "club_id" not in values:
            # Joueur libre : on conserve son ancien club comme origine.
            values["loan_from_club"] = 0
            values["loan_until_season"] = 0
            values["loan_promise"] = ""
            values["loan_start_matches"] = 0
            values["loan_start_date"] = ""
            values["precontract_club"] = 0
            values["precontract_from"] = 0
            values["precontract_salary"] = 0
            values["precontract_years"] = 0

        assignments = [f"{k}=?" for k in values if k in columns]
        args = [v for k, v in values.items() if k in columns]
        if not assignments:
            raise SaveError("Aucune colonne joueur modifiable.")
        self._begin()
        try:
            self.conn.execute("UPDATE player SET " + ", ".join(assignments) + " WHERE id=?",
                              args + [int(player_id)])
            # La progression de saison repart des nouvelles valeurs.
            if "player_attr_baseline" in {
                    r["name"] for r in self.conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'")}:
                season_row = self.conn.execute("SELECT season FROM club WHERE id=1").fetchone()
                season = int(season_row["season"] or 1) if season_row else 1
                base_cols = self.columns("player_attr_baseline")
                payload = {"technique": attrs["technique"], "passing": attrs["passing"],
                           "finishing": attrs["finishing"], "defense": attrs["defense"],
                           "stamina": attrs["stamina"], "speed": attrs["speed"],
                           "dribble": attrs["dribble"], "positioning": attrs["positioning"],
                           "goalkeeper": attrs["goalkeeper"]}
                keys = [k for k in payload if k in base_cols]
                if keys:
                    self.conn.execute(
                        "INSERT OR REPLACE INTO player_attr_baseline(player_id,season,"
                        + ",".join(keys) + ") VALUES(?,?," + ",".join("?" for _ in keys) + ")",
                        [int(player_id), season] + [payload[k] for k in keys])
            self._commit()
        except Exception:
            self._rollback()
            raise
        return {"notice": notice, "level": level, "potential": potential, "shirt": shirt}

    def recompute_value(self, player_id):
        row = self.player(player_id)
        if not row:
            raise SaveError("Joueur introuvable.")
        club = self.club(row["club_id"]) if int(row["club_id"] or 0) else None
        division = int(club["division"] or 3) if club else 3
        reputation = int(club["reputation"] or 20) if club else 20
        level = player_level(row)
        potential = player_potential(row)
        count = int(row["season_rating_count"] or 0)
        rating_avg = (float(row["season_rating_sum"] or 0) / count) if count else 0.0
        try:
            futsal_avg = (float(row["dribble"]) + float(row["speed"]) + float(row["positioning"])) / 3
        except (KeyError, TypeError, ValueError):
            futsal_avg = 55.0
        value = compute_market_value(
            level, int(row["age"] or 25), potential, row["position"], division, reputation,
            int(row["season_goals"] or 0), int(row["season_assists"] or 0),
            int(row["season_saves"] or 0), rating_avg, count, int(row["contract_years"] or 2),
            int(row["injury_days"] or 0), int(row["is_free_agent"] or 0), futsal_avg,
            int(row["morale"] or 70))
        return int(value)

    # ---------- sauvegardes ----------
    def backup_dir(self):
        """Sous-dossier ignoré par le catalogue du jeu (glob non récursif)."""
        return os.path.join(os.path.dirname(self.path), "editeur_backups")

    def backup(self, tag="manuel"):
        folder = self.backup_dir()
        os.makedirs(folder, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem = os.path.splitext(os.path.basename(self.path))[0]
        dest = os.path.join(folder, f"{stem}_{stamp}_{tag}.db")
        target = sqlite3.connect(dest)
        try:
            self.conn.backup(target)
        finally:
            target.close()
        self.prune_backups()
        return dest

    def list_backups(self):
        folder = self.backup_dir()
        if not os.path.isdir(folder):
            return []
        stem = os.path.splitext(os.path.basename(self.path))[0]
        names = [n for n in os.listdir(folder)
                 if n.startswith(stem + "_") and n.endswith(".db")]
        paths = [os.path.join(folder, n) for n in names]
        return sorted(paths, key=os.path.getmtime, reverse=True)

    def prune_backups(self, keep=10):
        for path in self.list_backups()[keep:]:
            try:
                os.remove(path)
            except OSError:
                pass

    def duplicate(self, destination):
        """Copie la sauvegarde ouverte vers un nouveau fichier .db."""
        destination = os.path.abspath(destination)
        if destination == self.path:
            raise SaveError("Choisis un autre nom : c'est déjà la sauvegarde ouverte.")
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        temp = destination + ".copie.tmp"
        target = sqlite3.connect(temp)
        try:
            self.conn.backup(target)
        finally:
            target.close()
        try:
            os.replace(temp, destination)
        except OSError as exc:
            try:
                os.remove(temp)
            except OSError:
                pass
            raise SaveError(f"Copie impossible : {exc}") from exc
        return destination


def compute_market_value(level, age, potential, position, division, reputation,
                         season_goals=0, season_assists=0, season_saves=0,
                         rating_avg=0.0, rating_count=0, contract_years=2,
                         injury_days=0, is_free_agent=0, futsal_avg=55.0, morale=70):
    """Copie du barème de app.py (aucune dépendance au jeu)."""
    division = max(1, min(6, int(division)))
    base = (float(level) ** 3.55) * 3.4
    growth = max(0, int(potential) - int(level))
    age = int(age)
    if age <= 20:
        age_mult = 1.05 + growth * 0.045
    elif age <= 23:
        age_mult = 1.08 + growth * 0.035
    elif age <= 27:
        age_mult = 1.0 + growth * 0.015
    elif age <= 30:
        age_mult = 0.94
    elif age <= 33:
        age_mult = 0.80
    else:
        age_mult = max(0.45, 0.68 - (age - 33) * 0.05)
    pot_prem = 1.0
    if age <= 22 and int(potential or 0) >= 15:
        pot_prem = 1.0 + (int(potential) - 14) * 0.05
    pos_mult = MARKET_POSITION_FACTOR.get(str(position), 1.0)
    perf_mult = 1.0
    if rating_count > 0:
        perf_mult = 1.0 + (float(rating_avg) - 6.5) * 0.06
        perf_mult += min(0.35, int(season_goals) * 0.02 + int(season_assists) * 0.012
                         + int(season_saves) * 0.01)
        perf_mult = max(0.85, min(1.30, perf_mult))
    contract_mult = 1.0
    if not is_free_agent:
        years = max(0, int(contract_years or 0))
        contract_mult = 0.62 if years <= 0 else 0.85 if years == 1 else 1.0 if years == 2 else 1.05 if years == 3 else 1.08
    injury_days = int(injury_days or 0)
    injury_mult = 0.88 if injury_days > 60 else 0.94 if injury_days > 30 else 0.97 if injury_days > 14 else 1.0
    rep_mult = max(0.75, min(1.45, 0.7 + int(reputation or 0) * 0.009))
    league_mult = 1.0 + (6 - division) * 0.18
    futsal_mult = max(0.90, min(1.18, 1.0 + (float(futsal_avg) - 55.0) * 0.0045))
    morale_mult = 0.96 if int(morale or 0) < 40 else 1.02 if int(morale or 0) > 85 else 1.0
    value = base * age_mult * pot_prem * pos_mult * perf_mult * contract_mult * injury_mult * rep_mult * league_mult * futsal_mult * morale_mult
    floor = 2500 if is_free_agent else 4000
    return round_money(max(floor, min(5_000_000, int(value))))


STYLE = """
QWidget { background:#0b111b; color:#e8eef7; font-family:'Segoe UI'; font-size:10pt; }
QFrame#Panel { background:#101a26; border:1px solid #25384c; border-radius:10px; }
QLabel#Title { font-size:16pt; font-weight:1000; color:#f2f6ff; }
QLabel#Hint { color:#9fb0c6; }
QLabel#Warn { color:#ffd98a; font-weight:800; }
QLabel#Section { color:#9fd2b6; font-size:8.5pt; font-weight:900; letter-spacing:1px; }
QLabel#FieldLabel { color:#9fb0c6; font-size:8.5pt; font-weight:700; }
QLabel#Chip { border-radius:8px; padding:5px 10px; font-size:8.5pt; font-weight:900; }
QPushButton { background:#17243a; color:#e8f2fb; border:1px solid #2a3b58; border-radius:6px; padding:7px 11px; }
QPushButton:hover { background:#203450; border-color:#3fb6e8; }
QPushButton:disabled { color:#61718a; background:#101827; }
QPushButton#Primary { background:#2f6fed; border:0; font-weight:900; }
QPushButton#Primary:hover { background:#4a84f5; }
QPushButton#Danger { background:#3a1720; border-color:#7a2c3d; color:#ffb3c0; }
QLineEdit, QComboBox, QSpinBox { background:#0e1826; border:1px solid #2a3b58; border-radius:6px; padding:5px 7px; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border-color:#3fb6e8; }
QTableWidget { background:#0d1623; alternate-background-color:#111c2c; gridline-color:#1f3048; border:1px solid #24354f; border-radius:8px; }
QHeaderView::section { background:#142033; color:#9fb0c6; border:0; padding:6px; font-weight:800; }
QTableWidget::item:selected { background:#1d3a5c; color:#ffffff; }
QTabWidget::pane { border:1px solid #24354f; border-radius:8px; top:-1px; }
QTabBar::tab { background:#111a29; color:#9fb0c6; padding:8px 15px; border:1px solid #24354f; border-bottom:0; }
QTabBar::tab:selected { background:#182740; color:#ffffff; font-weight:800; }
QCheckBox { spacing:7px; }
QScrollArea { border:0; }
QStatusBar { color:#9fb0c6; }
"""


class EditorWindow(QMainWindow):
    def __init__(self, auto_open=True):
        super().__init__()
        self.store = None
        self._loading = False
        self._current_pid = 0
        self.setWindowTitle("Éditeur de sauvegarde — Futsal Manager 2027")
        self.resize(1520, 940)
        self.setStyleSheet(STYLE)
        self._build_ui()
        self._reload_save_list()
        if auto_open:
            path = active_save_file()
            if path:
                self.open_path(path)

    # ---------- construction ----------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 10, 12, 8)
        root.setSpacing(8)

        bar = QFrame(); bar.setObjectName("Panel")
        bl = QGridLayout(bar); bl.setContentsMargins(12, 9, 12, 9)
        bl.setHorizontalSpacing(8); bl.setVerticalSpacing(6)
        title = QLabel("ÉDITEUR DE SAUVEGARDE"); title.setObjectName("Title")
        bl.addWidget(title, 0, 0)
        self.save_combo = QComboBox(); self.save_combo.setMinimumWidth(420)
        bl.addWidget(self.save_combo, 0, 1)
        open_btn = QPushButton("OUVRIR"); open_btn.setObjectName("Primary")
        open_btn.clicked.connect(self._open_selected)
        browse = QPushButton("PARCOURIR…"); browse.clicked.connect(self._browse)
        self.duplicate_btn = QPushButton("DUPLIQUER POUR TESTER")
        self.duplicate_btn.clicked.connect(self._duplicate_for_test)
        bl.addWidget(open_btn, 0, 2); bl.addWidget(browse, 0, 3)
        bl.addWidget(self.duplicate_btn, 0, 4)
        self.save_chip = QLabel("AUCUNE SAUVEGARDE")
        self.save_chip.setObjectName("Chip")
        self.save_chip.setAlignment(Qt.AlignCenter)
        self.save_chip.setMinimumWidth(150)
        bl.addWidget(self.save_chip, 1, 0)
        self.save_meta = QLabel("Choisis une sauvegarde puis clique sur OUVRIR.")
        self.save_meta.setObjectName("Hint"); self.save_meta.setWordWrap(True)
        bl.addWidget(self.save_meta, 1, 1, 1, 3)
        backup = QPushButton("SAUVEGARDE DE SECOURS"); backup.clicked.connect(self._manual_backup)
        folder = QPushButton("DOSSIER"); folder.clicked.connect(self._open_folder)
        bl.addWidget(backup, 1, 4)
        bl.setColumnStretch(1, 1)
        root.addWidget(bar)

        self.banner = QLabel("Les modifications sont écrites immédiatement dans la sauvegarde ouverte. "
                             "Utilise DUPLIQUER POUR TESTER pour expérimenter sur une copie, "
                             "sans toucher à ta carrière.")
        self.banner.setObjectName("Warn"); self.banner.setWordWrap(True)
        root.addWidget(self.banner)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_clubs_tab(), "CLUBS")
        self.tabs.addTab(self._build_players_tab(), "JOUEURS")
        self.tabs.addTab(self._build_staff_tab(), "STAFF")
        self.tabs.addTab(self._build_facility_tab(), "INFRASTRUCTURES")
        self.tabs.addTab(self._build_backups_tab(), "SAUVEGARDES")
        root.addWidget(self.tabs, 1)

        self.status = self.statusBar()
        self.status.showMessage("Aucune sauvegarde ouverte.")
        self._set_enabled(False)
        QShortcut(QKeySequence("Ctrl+F"), self).activated.connect(
            lambda: (self.tabs.setCurrentIndex(1), self.player_search.setFocus()))
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self._manual_backup)
        QShortcut(QKeySequence("Ctrl+D"), self).activated.connect(self._duplicate_for_test)

    def _set_enabled(self, enabled):
        for i in range(self.tabs.count()):
            self.tabs.setTabEnabled(i, enabled)

    def _panel(self):
        frame = QFrame(); frame.setObjectName("Panel")
        return frame

    def _section(self, text):
        label = QLabel(text); label.setObjectName("Section")
        return label

    def _build_clubs_tab(self):
        page = QWidget(); lay = QVBoxLayout(page); lay.setContentsMargins(10, 10, 10, 10); lay.setSpacing(8)
        filters = QHBoxLayout(); filters.setSpacing(8)
        self.club_search = QLineEdit(); self.club_search.setPlaceholderText("Rechercher un club…")
        self.club_search.setClearButtonEnabled(True)
        self.club_search.textChanged.connect(lambda *_: self._refresh_clubs())
        filters.addWidget(self.club_search, 2)
        self.club_div_filter = QComboBox()
        self.club_div_filter.addItem("Toutes les divisions", 0)
        for d in range(1, 7):
            self.club_div_filter.addItem(f"Ligue {d}", d)
        self.club_div_filter.currentIndexChanged.connect(lambda *_: self._refresh_clubs())
        filters.addWidget(self.club_div_filter, 1)
        self.club_sort = QComboBox()
        for label, key in (("Tri : division", "division"), ("Tri : nom", "name"),
                           ("Tri : budget", "budget"), ("Tri : réputation", "reputation")):
            self.club_sort.addItem(label, key)
        self.club_sort.currentIndexChanged.connect(lambda *_: self._refresh_clubs())
        filters.addWidget(self.club_sort)
        self.club_count = QLabel("—"); self.club_count.setObjectName("Hint")
        filters.addWidget(self.club_count)
        lay.addLayout(filters)

        self.clubs_table = QTableWidget(0, 7)
        self.clubs_table.setHorizontalHeaderLabels(
            ["ID", "CLUB", "DIV.", "RÉPUTATION", "BUDGET", "SAISON", "SALLE"])
        self.clubs_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.clubs_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.clubs_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.clubs_table.verticalHeader().setVisible(False)
        self.clubs_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.clubs_table.horizontalHeader().setSortIndicatorShown(True)
        self.clubs_table.setSortingEnabled(True)
        self.clubs_table.horizontalHeader().setSortIndicator(-1, Qt.AscendingOrder)
        self.clubs_table.setToolTip("Clique un en-tête de colonne pour trier.")
        self.clubs_table.itemSelectionChanged.connect(self._club_selected)
        lay.addWidget(self.clubs_table, 1)

        form = self._panel(); fl = QGridLayout(form); fl.setContentsMargins(12, 10, 12, 10); fl.setSpacing(8)
        fl.addWidget(self._section("MODIFIER LE CLUB SÉLECTIONNÉ"), 0, 0, 1, 6)
        self.club_name = QLabel("—"); self.club_name.setObjectName("Title")
        fl.addWidget(self.club_name, 1, 0, 1, 6)
        fl.addWidget(QLabel("Budget"), 2, 0)
        self.club_budget = QSpinBox(); self.club_budget.setRange(0, 2_000_000_000)
        self.club_budget.setSingleStep(50_000); self.club_budget.setGroupSeparatorShown(True)
        self.club_budget.setLocale(QLocale("fr_FR"))
        fl.addWidget(self.club_budget, 2, 1)
        fl.addWidget(QLabel("Réputation"), 2, 2)
        self.club_reputation = QSpinBox(); self.club_reputation.setRange(1, 100)
        fl.addWidget(self.club_reputation, 2, 3)
        fl.addWidget(QLabel("Division"), 2, 4)
        self.club_division = QComboBox()
        for d in range(1, 7):
            self.club_division.addItem(f"Ligue {d}", d)
        fl.addWidget(self.club_division, 2, 5)
        fl.addWidget(QLabel("Salle"), 3, 0)
        self.club_arena = QLineEdit(); self.club_arena.setMaxLength(60)
        fl.addWidget(self.club_arena, 3, 1, 1, 3)
        self.club_apply = QPushButton("APPLIQUER AU CLUB"); self.club_apply.setObjectName("Primary")
        self.club_apply.clicked.connect(self._apply_club)
        fl.addWidget(self.club_apply, 3, 4, 1, 2)
        hint = QLabel("Changer la division ne régénère pas le calendrier déjà en cours. "
                      "Les infrastructures se règlent dans l'onglet INFRASTRUCTURES (ton club).")
        hint.setObjectName("Hint"); hint.setWordWrap(True)
        fl.addWidget(hint, 4, 0, 1, 6)
        lay.addWidget(form)
        return page

    def _field(self, text, widget):
        box = QWidget(); box.setMinimumWidth(0)
        lay = QVBoxLayout(box); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(2)
        label = QLabel(text); label.setObjectName("FieldLabel")
        lay.addWidget(label); lay.addWidget(widget)
        return box

    def _build_players_tab(self):
        page = QWidget(); lay = QVBoxLayout(page); lay.setContentsMargins(10, 10, 10, 10); lay.setSpacing(8)
        filters = QHBoxLayout(); filters.setSpacing(8)
        self.player_search = QLineEdit(); self.player_search.setPlaceholderText("Rechercher un joueur…")
        self.player_search.setClearButtonEnabled(True)
        self.player_search.textChanged.connect(lambda *_: self._refresh_players())
        filters.addWidget(self.player_search, 2)
        self.player_club_filter = QComboBox(); self.player_club_filter.setMinimumWidth(240)
        self.player_club_filter.currentIndexChanged.connect(lambda *_: self._refresh_players())
        filters.addWidget(self.player_club_filter, 1)
        self.player_free_only = QCheckBox("Joueurs libres")
        self.player_free_only.stateChanged.connect(lambda *_: self._refresh_players())
        filters.addWidget(self.player_free_only)
        self.player_retired = QCheckBox("Retraités")
        self.player_retired.stateChanged.connect(lambda *_: self._refresh_players())
        filters.addWidget(self.player_retired)
        self.player_sort = QComboBox(); self.player_sort.setMinimumWidth(150)
        for label, key in (("Tri : club", "club"), ("Tri : nom", "name"),
                           ("Tri : niveau", "level"), ("Tri : potentiel", "potential"),
                           ("Tri : valeur", "value"), ("Tri : âge", "age")):
            self.player_sort.addItem(label, key)
        self.player_sort.currentIndexChanged.connect(lambda *_: self._refresh_players())
        filters.addWidget(self.player_sort)
        refresh = QPushButton("ACTUALISER"); refresh.clicked.connect(self._refresh_players)
        filters.addWidget(refresh)
        export = QPushButton("EXPORTER CSV"); export.clicked.connect(self._export_players)
        filters.addWidget(export)
        lay.addLayout(filters)

        adv = QFrame(); adv.setObjectName("Panel")
        al = QGridLayout(adv); al.setContentsMargins(10, 8, 10, 8)
        al.setHorizontalSpacing(10); al.setVerticalSpacing(6)
        self.f_position = QComboBox(); self.f_position.addItem("Tous les postes", "")
        for position in POSITIONS:
            self.f_position.addItem(position, position)
        self.f_position.currentIndexChanged.connect(lambda *_: self._refresh_players())
        al.addWidget(self._field("Poste", self.f_position), 0, 0)

        self.f_age_min = QSpinBox(); self.f_age_min.setRange(0, 60)
        self.f_age_min.setSpecialValueText("Tous")
        self.f_age_min.valueChanged.connect(lambda *_: self._refresh_players())
        al.addWidget(self._field("Âge minimum", self.f_age_min), 0, 1)
        self.f_age_max = QSpinBox(); self.f_age_max.setRange(0, 60)
        self.f_age_max.setSpecialValueText("Tous")
        self.f_age_max.valueChanged.connect(lambda *_: self._refresh_players())
        al.addWidget(self._field("Âge maximum", self.f_age_max), 0, 2)

        self.f_level_min = QSpinBox(); self.f_level_min.setRange(0, 20)
        self.f_level_min.setSpecialValueText("Tous")
        self.f_level_min.valueChanged.connect(lambda *_: self._refresh_players())
        al.addWidget(self._field("Niveau minimum", self.f_level_min), 0, 3)
        self.f_potential_min = QSpinBox(); self.f_potential_min.setRange(0, 20)
        self.f_potential_min.setSpecialValueText("Tous")
        self.f_potential_min.valueChanged.connect(lambda *_: self._refresh_players())
        al.addWidget(self._field("Potentiel minimum", self.f_potential_min), 0, 4)

        self.f_value_min = QSpinBox(); self.f_value_min.setRange(0, 100_000_000)
        self.f_value_min.setSingleStep(250_000); self.f_value_min.setSpecialValueText("Toutes")
        self.f_value_min.setGroupSeparatorShown(True); self.f_value_min.setLocale(QLocale("fr_FR"))
        self.f_value_min.valueChanged.connect(lambda *_: self._refresh_players())
        al.addWidget(self._field("Valeur minimum", self.f_value_min), 1, 0)

        self.f_contract = QComboBox()
        for label, value in (("Contrat : tous", -1), ("≤ 1 an", 1), ("≤ 2 ans", 2),
                             ("≤ 3 ans", 3), ("Expiré (0 an)", 0)):
            self.f_contract.addItem(label, value)
        self.f_contract.currentIndexChanged.connect(lambda *_: self._refresh_players())
        al.addWidget(self._field("Contrat", self.f_contract), 1, 1)

        self.f_status = QComboBox(); self.f_status.addItem("Statut : tous", "")
        for label in STATUS_LABELS:
            self.f_status.addItem(label, label)
        self.f_status.currentIndexChanged.connect(lambda *_: self._refresh_players())
        al.addWidget(self._field("Statut", self.f_status), 1, 2)

        self.player_reset = QPushButton("RÉINITIALISER LES FILTRES")
        self.player_reset.clicked.connect(self._reset_filters)
        al.addWidget(self.player_reset, 1, 3)
        self.player_count = QLabel("—")
        self.player_count.setObjectName("Hint")
        al.addWidget(self.player_count, 1, 4)
        for column in range(5):
            al.setColumnStretch(column, 1)
        lay.addWidget(adv)

        split = QSplitter(Qt.Horizontal)
        self.players_table = QTableWidget(0, 11)
        self.players_table.setHorizontalHeaderLabels(
            ["ID", "JOUEUR", "CLUB", "POSTE", "ÂGE", "NIV.", "POT.", "VALEUR", "SALAIRE", "CONTRAT", "STATUT"])
        self.players_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.players_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.players_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.players_table.verticalHeader().setVisible(False)
        self.players_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.players_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.players_table.setSortingEnabled(True)
        self.players_table.horizontalHeader().setSortIndicator(-1, Qt.AscendingOrder)
        self.players_table.setToolTip("Clique un en-tête de colonne pour trier.")
        self.players_table.itemSelectionChanged.connect(self._player_selected)
        split.addWidget(self.players_table)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        form_holder = QWidget(); form_holder.setMinimumWidth(0)
        self.player_form = QVBoxLayout(form_holder)
        self.player_form.setContentsMargins(8, 4, 10, 4); self.player_form.setSpacing(8)
        scroll.setWidget(form_holder)
        split.addWidget(scroll)
        split.setStretchFactor(0, 1); split.setStretchFactor(1, 1)
        split.setSizes([900, 620])
        scroll.setMinimumWidth(420)
        self.players_table.setMinimumWidth(640)
        self.players_split = split
        lay.addWidget(split, 1)

        self.player_form.addWidget(self._section("IDENTITÉ"))
        ident = QGridLayout(); ident.setHorizontalSpacing(8); ident.setVerticalSpacing(6)
        self.p_first = QLineEdit(); self.p_last = QLineEdit()
        self.p_age = QSpinBox(); self.p_age.setRange(15, 60)
        self.p_pos = QComboBox(); [self.p_pos.addItem(p) for p in POSITIONS]
        self.p_pos.currentIndexChanged.connect(lambda *_: self._update_level_hint())
        self.p_nat = QLineEdit(); self.p_nat.setMaxLength(40)
        self.p_shirt = QSpinBox(); self.p_shirt.setRange(0, 99)
        ident.addWidget(self._field("Prénom", self.p_first), 0, 0)
        ident.addWidget(self._field("Nom", self.p_last), 0, 1)
        ident.addWidget(self._field("Âge", self.p_age), 1, 0)
        ident.addWidget(self._field("Poste", self.p_pos), 1, 1)
        ident.addWidget(self._field("Nationalité", self.p_nat), 2, 0)
        ident.addWidget(self._field("N° maillot", self.p_shirt), 2, 1)
        ident.setColumnStretch(0, 1); ident.setColumnStretch(1, 1)
        self.player_form.addLayout(ident)

        self.player_form.addWidget(self._section("CLUB"))
        self.p_club = QComboBox(); self.p_club.setMinimumWidth(240)
        self.player_form.addWidget(self.p_club)
        self.p_free_hint = QLabel("Un joueur libre conserve son club d'origine.")
        self.p_free_hint.setObjectName("Hint")
        self.p_free_hint.setWordWrap(True)
        self.p_free_hint.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.p_free_hint.setMinimumWidth(0)
        self.player_form.addWidget(self.p_free_hint)

        self.player_form.addWidget(self._section("ATTRIBUTS /20"))
        attrs = QGridLayout(); attrs.setHorizontalSpacing(8); attrs.setVerticalSpacing(6)
        self.p_attrs = {}
        for i, (key, label) in enumerate(ATTRS):
            spin = QSpinBox(); spin.setRange(1, 20)
            spin.valueChanged.connect(self._update_level_hint)
            self.p_attrs[key] = spin
            attrs.addWidget(self._field(label, spin), i // 3, i % 3)
        for column in range(3):
            attrs.setColumnStretch(column, 1)
        self.player_form.addLayout(attrs)
        self.p_hint = QLabel("Niveau calculé : —   •   Potentiel : —")
        self.p_hint.setObjectName("Hint")
        self.p_hint.setWordWrap(True)
        self.p_hint.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.p_hint.setMinimumWidth(0)
        self.player_form.addWidget(self.p_hint)

        self.player_form.addWidget(self._section("CARRIÈRE"))
        career = QGridLayout(); career.setHorizontalSpacing(8); career.setVerticalSpacing(6)
        self.p_potential = QSpinBox(); self.p_potential.setRange(1, 20)
        self.p_value = QSpinBox(); self.p_value.setRange(0, 100_000_000); self.p_value.setSingleStep(25_000)
        self.p_value.setGroupSeparatorShown(True)
        self.p_value.setLocale(QLocale("fr_FR"))
        self.p_salary = QSpinBox(); self.p_salary.setRange(0, 10_000_000); self.p_salary.setSingleStep(500)
        self.p_salary.setGroupSeparatorShown(True)
        self.p_salary.setLocale(QLocale("fr_FR"))
        self.p_contract = QSpinBox(); self.p_contract.setRange(0, 10)
        self.p_condition = QSpinBox(); self.p_condition.setRange(0, 100)
        self.p_morale = QSpinBox(); self.p_morale.setRange(0, 100)
        for i, (label, widget) in enumerate((
                ("Potentiel", self.p_potential), ("Valeur", self.p_value),
                ("Salaire / mois", self.p_salary), ("Contrat (ans)", self.p_contract),
                ("Condition", self.p_condition), ("Moral", self.p_morale))):
            career.addWidget(self._field(label, widget), i // 2, i % 2)
        career.setColumnStretch(0, 1); career.setColumnStretch(1, 1)
        self.player_form.addLayout(career)

        self.player_form.addWidget(self._section("DISPONIBILITÉ"))
        avail = QGridLayout(); avail.setHorizontalSpacing(8); avail.setVerticalSpacing(6)
        self.p_inj_m = QSpinBox(); self.p_inj_m.setRange(0, 365)
        self.p_inj_d = QSpinBox(); self.p_inj_d.setRange(0, 365)
        self.p_susp_m = QSpinBox(); self.p_susp_m.setRange(0, 365)
        self.p_susp_d = QSpinBox(); self.p_susp_d.setRange(0, 365)
        self.p_yellow = QSpinBox(); self.p_yellow.setRange(0, 99)
        for i, (label, widget) in enumerate((
                ("Blessure (matchs)", self.p_inj_m), ("Blessure (jours)", self.p_inj_d),
                ("Suspension (matchs)", self.p_susp_m), ("Suspension (jours)", self.p_susp_d),
                ("Cartons jaunes", self.p_yellow))):
            avail.addWidget(self._field(label, widget), i // 2, i % 2)
        avail.setColumnStretch(0, 1); avail.setColumnStretch(1, 1)
        self.player_form.addLayout(avail)

        self.p_listed = QCheckBox("Liste des transferts")
        self.p_listed.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.player_form.addWidget(self.p_listed)
        buttons = QHBoxLayout()
        self.player_apply = QPushButton("APPLIQUER AU JOUEUR"); self.player_apply.setObjectName("Primary")
        self.player_apply.clicked.connect(self._apply_player)
        self.player_reload = QPushButton("RECHARGER"); self.player_reload.clicked.connect(self._reload_player)
        self.player_value = QPushButton("RECALCULER LA VALEUR"); self.player_value.clicked.connect(self._recalc_value)
        buttons.addWidget(self.player_apply); buttons.addWidget(self.player_reload); buttons.addWidget(self.player_value)
        lay.addLayout(buttons)
        self.player_form.addStretch(1)
        self._set_player_form_enabled(False)
        return page

    def _build_staff_tab(self):
        page = QWidget(); lay = QVBoxLayout(page); lay.setContentsMargins(10, 10, 10, 10); lay.setSpacing(8)
        hint = QLabel("Le staff appartient à la carrière ouverte. Niveau 1 à 5 ; "
                      "un poste non pourvu conserve son niveau pour une réembauche.")
        hint.setObjectName("Hint"); hint.setWordWrap(True)
        lay.addWidget(hint)
        self.staff_table = QTableWidget(len(STAFF_ROLES), 5)
        self.staff_table.setHorizontalHeaderLabels(["POSTE", "EMBAUCHÉ", "NIVEAU", "NOM", "NATIONALITÉ"])
        self.staff_table.verticalHeader().setVisible(False)
        self.staff_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.staff_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.staff_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.staff_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.staff_checks = []
        self.staff_levels = []
        self.staff_names = []
        self.staff_nats = []
        for row in range(len(STAFF_ROLES)):
            item = QTableWidgetItem(STAFF_ROLES[row][1])
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.staff_table.setItem(row, 0, item)
            check = QCheckBox(); self.staff_table.setCellWidget(row, 1, self._centered(check))
            spin = QSpinBox(); spin.setRange(1, 5)
            self.staff_table.setCellWidget(row, 2, spin)
            name = QLineEdit(); name.setMaxLength(60)
            name.setPlaceholderText("(généré par le jeu)")
            self.staff_table.setCellWidget(row, 3, name)
            nat = QLineEdit(); nat.setMaxLength(40)
            nat.setPlaceholderText("—")
            self.staff_table.setCellWidget(row, 4, nat)
            self.staff_checks.append(check); self.staff_levels.append(spin)
            self.staff_names.append(name); self.staff_nats.append(nat)
            self.staff_table.setRowHeight(row, 42)
        lay.addWidget(self.staff_table, 1)
        buttons = QHBoxLayout()
        apply = QPushButton("APPLIQUER TOUT LE STAFF"); apply.setObjectName("Primary")
        apply.clicked.connect(self._apply_staff)
        reload = QPushButton("RECHARGER"); reload.clicked.connect(self._refresh_staff)
        buttons.addWidget(apply); buttons.addWidget(reload); buttons.addStretch(1)
        lay.addLayout(buttons)
        return page

    def _centered(self, widget):
        holder = QWidget(); lay = QHBoxLayout(holder)
        lay.setContentsMargins(0, 0, 0, 0); lay.addWidget(widget, 0, Qt.AlignCenter)
        return holder

    def _build_facility_tab(self):
        page = QWidget(); lay = QVBoxLayout(page); lay.setContentsMargins(10, 10, 10, 10); lay.setSpacing(8)
        self.fac_club_label = QLabel("Infrastructures du club : —")
        self.fac_club_label.setObjectName("Title")
        lay.addWidget(self.fac_club_label)
        fac_hint = QLabel("Cet onglet modifie le campus du club du joueur (club 1). "
                          "Les autres clubs n'ont pas d'infrastructures séparées.")
        fac_hint.setObjectName("Hint"); fac_hint.setWordWrap(True)
        lay.addWidget(fac_hint)
        grid = QGridLayout(); grid.setHorizontalSpacing(12); grid.setVerticalSpacing(7)
        self.fac_spins = {}
        for i, (key, label, low, high) in enumerate(FACILITY_LEVELS):
            spin = QSpinBox(); spin.setRange(low, high)
            self.fac_spins[key] = spin
            grid.addWidget(QLabel(label), i // 3, (i % 3) * 2)
            grid.addWidget(spin, i // 3, (i % 3) * 2 + 1)
        lay.addLayout(grid)
        lay.addWidget(self._section("ÉQUIPEMENTS"))
        flags = QGridLayout(); flags.setHorizontalSpacing(18); flags.setVerticalSpacing(6)
        self.fac_flags = {}
        for i, (key, label) in enumerate(FACILITY_FLAGS):
            check = QCheckBox(label); self.fac_flags[key] = check
            flags.addWidget(check, i // 3, i % 3)
        lay.addLayout(flags)
        price_row = QHBoxLayout()
        price_row.addWidget(QLabel("Prix du billet"))
        self.fac_price = QSpinBox(); self.fac_price.setRange(1, 60)
        price_row.addWidget(self.fac_price)
        price_row.addStretch(1)
        apply = QPushButton("APPLIQUER AUX INFRASTRUCTURES"); apply.setObjectName("Primary")
        apply.clicked.connect(self._apply_facility)
        price_row.addWidget(apply)
        lay.addLayout(price_row)
        lay.addStretch(1)
        return page

    def _build_backups_tab(self):
        page = QWidget(); lay = QVBoxLayout(page); lay.setContentsMargins(10, 10, 10, 10); lay.setSpacing(8)
        card = self._panel(); cl = QVBoxLayout(card); cl.setContentsMargins(12, 10, 12, 10); cl.setSpacing(6)
        cl.addWidget(self._section("SAUVEGARDE OUVERTE"))
        self.backup_open_path = QLabel("Aucune sauvegarde ouverte.")
        self.backup_open_path.setObjectName("Hint"); self.backup_open_path.setWordWrap(True)
        self.backup_open_path.setTextInteractionFlags(Qt.TextSelectableByMouse)
        cl.addWidget(self.backup_open_path)
        self.backup_open_meta = QLabel("—"); self.backup_open_meta.setObjectName("Hint")
        self.backup_open_meta.setWordWrap(True)
        cl.addWidget(self.backup_open_meta)
        row = QHBoxLayout()
        duplicate = QPushButton("DUPLIQUER POUR TESTER")
        duplicate.clicked.connect(self._duplicate_for_test)
        copy_path = QPushButton("COPIER LE CHEMIN")
        copy_path.clicked.connect(self._copy_save_path)
        folder = QPushButton("OUVRIR LE DOSSIER")
        folder.clicked.connect(self._open_folder)
        row.addWidget(duplicate); row.addWidget(copy_path); row.addWidget(folder); row.addStretch(1)
        cl.addLayout(row)
        lay.addWidget(card)

        lay.addWidget(self._section("COPIES DE SECOURS"))
        self.backup_hint = QLabel("—"); self.backup_hint.setObjectName("Hint")
        self.backup_hint.setWordWrap(True)
        lay.addWidget(self.backup_hint)
        self.backups_table = QTableWidget(0, 3)
        self.backups_table.setHorizontalHeaderLabels(["FICHIER", "DATE", "TAILLE"])
        self.backups_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.backups_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.backups_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.backups_table.verticalHeader().setVisible(False)
        self.backups_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.backups_table.setSortingEnabled(True)
        self.backups_table.horizontalHeader().setSortIndicator(-1, Qt.AscendingOrder)
        self.backups_table.setToolTip("Clique un en-tête de colonne pour trier.")
        lay.addWidget(self.backups_table, 1)
        row2 = QHBoxLayout()
        create = QPushButton("CRÉER UNE SAUVEGARDE"); create.clicked.connect(self._manual_backup)
        restore = QPushButton("RESTAURER LA SÉLECTION"); restore.setObjectName("Danger")
        restore.clicked.connect(self._restore_selected)
        open_backups = QPushButton("OUVRIR LE DOSSIER DES COPIES")
        open_backups.clicked.connect(self._open_backup_folder)
        row2.addWidget(create); row2.addWidget(restore); row2.addWidget(open_backups); row2.addStretch(1)
        lay.addLayout(row2)
        return page

    def _copy_save_path(self):
        if self.store:
            QApplication.clipboard().setText(self.store.path)
            self.status.showMessage("Chemin copié.")
        else:
            QMessageBox.information(self, "Chemin", "Aucune sauvegarde ouverte.")

    # ---------- ouverture ----------
    def _reload_save_list(self):
        self.save_combo.clear()
        active = active_save_file()
        for path in select_save_files():
            label = os.path.basename(path)
            try:
                c = sqlite3.connect(path, timeout=1)
                c.row_factory = sqlite3.Row
                row = c.execute("SELECT name,division,season FROM club WHERE id=1").fetchone()
                c.close()
                if row:
                    label = f"{os.path.basename(path)} — {row['name']} (L{row['division']}, saison {row['season']})"
            except sqlite3.Error:
                pass
            self.save_combo.addItem(label, path)
            if os.path.abspath(path) == active:
                self.save_combo.setCurrentIndex(self.save_combo.count() - 1)

    def _open_selected(self):
        path = self.save_combo.currentData()
        if path:
            self.open_path(path)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Ouvrir une sauvegarde", str(SAVE_DIR),
                                             "Sauvegardes FM2027 (*.db)")
        if path:
            self.open_path(path)

    def open_path(self, path):
        try:
            if self.store:
                self.store.close()
            self.store = SaveStore(path)
        except SaveError as exc:
            QMessageBox.critical(self, "Ouverture impossible", str(exc))
            return False
        self._reload_combos()
        self._refresh_clubs()
        self._refresh_players()
        self._refresh_staff()
        self._refresh_facility()
        self._refresh_backups()
        self._set_enabled(True)
        writable = not self.store.read_only
        for widget in (self.club_apply, self.player_apply, self.player_value):
            widget.setEnabled(writable)
        if not writable:
            self.banner.setText(
                "⚠ Sauvegarde verrouillée : ferme le jeu avant de modifier. "
                f"({self.store.lock_message or 'base ouverte ailleurs'})")
        elif self.store.sidecar:
            self.banner.setText(
                "⚠ Le jeu semble encore ouvert (fichiers -wal/-shm présents). "
                "Ferme-le pour éviter que le jeu n'écrase tes modifications.")
        else:
            self.banner.setText(
                "Écriture immédiate activée. Pour expérimenter sans risque, utilise "
                "DUPLIQUER POUR TESTER : l'éditeur basculera sur une copie, et ta "
                "carrière d'origine restera intacte.")
        career = self.store.career()
        info = "—"
        if career:
            info = (f"{os.path.basename(self.store.path)} • {career['current_date']} • "
                    f"journée {career['matchday']} • {len(self.store.clubs())} clubs")
        self.status.showMessage(info)
        self._update_save_header()
        return True

    def _ensure_backup_once(self):
        if not hasattr(self, "_backup_done") or self._backup_done != self.store.path:
            self.store.backup("auto")
            self._backup_done = self.store.path
            self._refresh_backups()

    def _guard(self, fn):
        try:
            self._ensure_backup_once()
            fn()
            self._update_save_header()
            self._refresh_backups()
            self.status.showMessage("Modification enregistrée.")
        except SaveError as exc:
            QMessageBox.warning(self, "Valeur refusée", str(exc))
        except sqlite3.Error as exc:
            QMessageBox.critical(self, "Erreur SQLite", str(exc))

    # ---------- clubs ----------
    def _refresh_clubs(self):
        current = None
        row = self.clubs_table.currentRow()
        if row >= 0 and self.clubs_table.item(row, 0):
            current = int(self.clubs_table.item(row, 0).data(Qt.UserRole) or 0)
        header = self.clubs_table.horizontalHeader()
        sort_col = header.sortIndicatorSection()
        sort_order = header.sortIndicatorOrder()
        self.clubs_table.setSortingEnabled(False)
        self.clubs_table.setRowCount(0)
        if not self.store:
            return
        rows = list(self.store.clubs())
        search = self.club_search.text().strip().casefold()
        division = int(self.club_div_filter.currentData() or 0)
        if search:
            rows = [club for club in rows if search in str(club["name"]).casefold()]
        if division:
            rows = [club for club in rows if int(club["division"] or 0) == division]
        mode = self.club_sort.currentData() if hasattr(self, "club_sort") else "division"
        if mode == "name":
            rows.sort(key=lambda club: str(club["name"]).casefold())
        elif mode == "budget":
            rows.sort(key=lambda club: int(club["budget"] or 0), reverse=True)
        elif mode == "reputation":
            rows.sort(key=lambda club: int(club["reputation"] or 0), reverse=True)
        if hasattr(self, "club_count"):
            self.club_count.setText(f"{len(rows)} club(s)")
        self.clubs_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            values = [row["id"], row["name"], f"L{row['division']}", row["reputation"],
                      money(row["budget"]), row["season"], row["arena_name"] or "—"]
            sorts = [int(row["id"]), str(row["name"]).casefold(), int(row["division"] or 0),
                     int(row["reputation"] or 0), int(row["budget"] or 0),
                     int(row["season"] or 0), str(row["arena_name"] or "").casefold()]
            for c, value in enumerate(values):
                item = SortableItem(value, sorts[c])
                if c == 0:
                    item.setData(Qt.UserRole, int(row["id"]))
                if c in (2, 3, 5):
                    item.setTextAlignment(Qt.AlignCenter)
                self.clubs_table.setItem(i, c, item)
        self.clubs_table.resizeColumnsToContents()
        self.clubs_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.clubs_table.setSortingEnabled(True)
        if sort_col >= 0:
            self.clubs_table.sortItems(sort_col, sort_order)
        if rows:
            selected_row = 0
            if current:
                for i in range(self.clubs_table.rowCount()):
                    item = self.clubs_table.item(i, 0)
                    if item and int(item.data(Qt.UserRole) or 0) == current:
                        selected_row = i; break
            self.clubs_table.selectRow(selected_row)

    def _club_selected(self):
        if self._loading or not self.store:
            return
        row = self.clubs_table.currentRow()
        if row < 0:
            return
        club_id = self.clubs_table.item(row, 0).data(Qt.UserRole)
        club = self.store.club(club_id)
        if not club:
            return
        self._loading = True
        self.club_name.setText(f"{club['name']}  •  Ligue {club['division']}")
        self.club_budget.setValue(int(club["budget"] or 0))
        self.club_reputation.setValue(int(club["reputation"] or 1))
        self.club_division.setCurrentIndex(max(0, min(5, int(club["division"] or 1) - 1)))
        self.club_arena.setText(str(club["arena_name"] or ""))
        self._loading = False

    def _apply_club(self):
        row = self.clubs_table.currentRow()
        if row < 0 or not self.store:
            QMessageBox.information(self, "Club", "Sélectionne d'abord un club.")
            return
        club_id = self.clubs_table.item(row, 0).data(Qt.UserRole)

        def run():
            self.store.update_club(club_id, self.club_budget.value(), self.club_reputation.value(),
                                   self.club_division.currentData(), self.club_arena.text())
            self._refresh_clubs()
        self._guard(run)

    # ---------- joueurs ----------
    def _reload_combos(self):
        self.player_club_filter.blockSignals(True)
        self.player_club_filter.clear()
        self.player_club_filter.addItem("Tous les clubs", 0)
        self.player_club_filter.addItem("Joueurs libres", -1)
        for club in self.store.clubs():
            self.player_club_filter.addItem(f"L{club['division']} · {club['name']}", int(club["id"]))
        self.player_club_filter.blockSignals(False)
        self.p_club.clear()
        self.p_club.addItem("— Joueur libre —", 0)
        for club in self.store.clubs():
            self.p_club.addItem(f"L{club['division']} · {club['name']}", int(club["id"]))

    def _refresh_players(self, select_pid=None):
        if not self.store:
            return
        if select_pid is None:
            select_pid = self._current_pid
        club_filter = self.player_club_filter.currentData() if self.player_club_filter.count() else 0
        if self.player_free_only.isChecked():
            club_filter = -1
        rows = self.store.players(self.player_search.text(), int(club_filter or 0),
                                  self.player_retired.isChecked())
        mode = self.player_sort.currentData() if hasattr(self, "player_sort") else "club"
        if mode == "name":
            rows = sorted(rows, key=lambda r: (str(r["last_name"]).casefold(),
                                               str(r["first_name"]).casefold()))
        elif mode == "level":
            rows = sorted(rows, key=player_level, reverse=True)
        elif mode == "potential":
            rows = sorted(rows, key=lambda r: (player_potential(r), player_level(r)), reverse=True)
        elif mode == "value":
            rows = sorted(rows, key=lambda r: int(r["market_value"] or 0), reverse=True)
        elif mode == "age":
            rows = sorted(rows, key=lambda r: int(r["age"] or 99))
        total = len(rows)
        rows = filter_players(rows, self._current_filters())
        self._visible_rows = rows
        if hasattr(self, "player_count"):
            self.player_count.setText(f"{len(rows)} / {total} joueur(s)")
        header = self.players_table.horizontalHeader()
        sort_col = header.sortIndicatorSection()
        sort_order = header.sortIndicatorOrder()
        self.players_table.setSortingEnabled(False)
        self.players_table.blockSignals(True)
        self.players_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            level = player_level(row)
            potential = player_potential(row)
            status = player_status(row)
            values = [row["id"], f"{row['first_name']} {row['last_name']}",
                      row["club_name"] or "Libre", row["position"], row["age"],
                      level, potential, money(row["market_value"]), money(row["salary"]),
                      f"{int(row['contract_years'] or 0)} an(s)", status]
            sorts = [int(row["id"]), f"{row['first_name']} {row['last_name']}".casefold(),
                     str(row["club_name"] or "Libre").casefold(), str(row["position"]),
                     int(row["age"] or 0), level, potential, int(row["market_value"] or 0),
                     int(row["salary"] or 0), int(row["contract_years"] or 0), status]
            for c, value in enumerate(values):
                item = SortableItem(value, sorts[c])
                if c == 0:
                    item.setData(Qt.UserRole, int(row["id"]))
                if c in (0, 3, 4, 5, 6, 9):
                    item.setTextAlignment(Qt.AlignCenter)
                if c in (5, 6) and potential - level >= 4:
                    item.setForeground(QColor("#8fe0a3"))
                if c == 10:
                    item.setForeground(QColor(STATUS_COLORS.get(status, "#e8eef7")))
                self.players_table.setItem(i, c, item)
        self.players_table.blockSignals(False)
        for column, width in {0: 45, 3: 75, 4: 45, 5: 45, 6: 45,
                              7: 95, 8: 85, 9: 85, 10: 100}.items():
            self.players_table.setColumnWidth(column, width)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        self.players_table.setSortingEnabled(True)
        if sort_col >= 0:
            self.players_table.sortItems(sort_col, sort_order)
        if rows:
            target_row = 0
            if select_pid:
                for i in range(self.players_table.rowCount()):
                    item = self.players_table.item(i, 0)
                    if item and int(item.data(Qt.UserRole) or 0) == int(select_pid):
                        target_row = i; break
            self.players_table.selectRow(target_row)
            item = self.players_table.item(target_row, 0)
            if item:
                self._current_pid = int(item.data(Qt.UserRole) or 0)
                if self._current_pid:
                    self._load_player(self._current_pid)
        else:
            self._set_player_form_enabled(False)
            self._current_pid = 0

    @staticmethod
    def _player_status(row):
        return player_status(row)

    def _current_filters(self):
        return {
            "position": self.f_position.currentData() or "",
            "age_min": self.f_age_min.value(),
            "age_max": self.f_age_max.value(),
            "level_min": self.f_level_min.value(),
            "potential_min": self.f_potential_min.value(),
            "value_min": self.f_value_min.value(),
            "contract_max": int(self.f_contract.currentData()),
            "status": self.f_status.currentData() or "",
        }

    def _reset_filters(self):
        widgets = (self.player_search, self.player_club_filter, self.player_free_only,
                   self.player_retired, self.player_sort, self.f_position,
                   self.f_age_min, self.f_age_max, self.f_level_min,
                   self.f_potential_min, self.f_value_min, self.f_contract, self.f_status)
        for widget in widgets:
            widget.blockSignals(True)
        self.player_search.clear()
        self.player_club_filter.setCurrentIndex(0)
        self.player_free_only.setChecked(False)
        self.player_retired.setChecked(False)
        self.player_sort.setCurrentIndex(0)
        self.f_position.setCurrentIndex(0)
        for spin in (self.f_age_min, self.f_age_max, self.f_level_min,
                     self.f_potential_min, self.f_value_min):
            spin.setValue(0)
        self.f_contract.setCurrentIndex(0)
        self.f_status.setCurrentIndex(0)
        for widget in widgets:
            widget.blockSignals(False)
        self._refresh_players()

    def _export_players(self):
        rows = getattr(self, "_visible_rows", [])
        if not rows:
            QMessageBox.information(self, "Export CSV",
                                    "Aucun joueur à exporter avec les filtres actuels.")
            return
        default = os.path.join(os.path.expanduser("~"), "joueurs_fm2027.csv")
        path, _ = QFileDialog.getSaveFileName(self, "Exporter les joueurs",
                                             default, "CSV (*.csv)")
        if not path:
            return
        if not path.lower().endswith(".csv"):
            path += ".csv"
        try:
            export_players_csv(path, rows)
        except OSError as exc:
            QMessageBox.critical(self, "Export impossible", str(exc)); return
        self.status.showMessage(f"{len(rows)} joueur(s) exporté(s) vers {os.path.basename(path)}")

    def _player_selected(self):
        if self._loading:
            return
        row = self.players_table.currentRow()
        if row < 0 or not self.players_table.item(row, 0):
            return
        pid = int(self.players_table.item(row, 0).data(Qt.UserRole) or 0)
        if pid:
            self._current_pid = pid
            self._load_player(pid)

    def _load_player(self, pid):
        player = self.store.player(pid)
        if not player:
            return
        self._loading = True
        try:
            self._set_player_form_enabled(True)
            self.p_first.setText(player["first_name"] or "")
            self.p_last.setText(player["last_name"] or "")
            self.p_age.setValue(int(player["age"] or 18))
            self.p_pos.setCurrentText(player["position"] if player["position"] in POSITIONS else "Universel")
            self.p_nat.setText(player["nationality"] or "")
            self.p_shirt.setValue(int(player["shirt_number"] or 0))
            club_id = int(player["club_id"] or 0)
            if int(player["is_free_agent"] or 0):
                self.p_club.setCurrentIndex(0)
            else:
                index = self.p_club.findData(club_id)
                self.p_club.setCurrentIndex(index if index >= 0 else 0)
            for key, _label in ATTRS:
                self.p_attrs[key].setValue(rating20(player[key]))
            self.p_potential.setValue(player_potential(player))
            self.p_value.setValue(int(player["market_value"] or 0))
            self.p_salary.setValue(int(player["salary"] or 0))
            self.p_contract.setValue(int(player["contract_years"] or 0))
            self.p_condition.setValue(int(player["condition"] or 100))
            self.p_morale.setValue(int(player["morale"] or 70))
            self.p_inj_m.setValue(int(player["injury_matches"] or 0))
            self.p_inj_d.setValue(int(player["injury_days"] or 0))
            self.p_susp_m.setValue(int(player["suspension_matches"] or 0))
            self.p_susp_d.setValue(int(player["suspension_days"] or 0))
            self.p_yellow.setValue(int(player["yellow_cards"] or 0))
            self.p_listed.setChecked(bool(int(player["transfer_listed"] or 0)))
            self._update_level_hint()
        finally:
            self._loading = False

    def _set_player_form_enabled(self, enabled):
        for widget in (self.p_first, self.p_last, self.p_age, self.p_pos, self.p_nat,
                       self.p_shirt, self.p_club, self.p_potential, self.p_value,
                       self.p_salary, self.p_contract, self.p_condition, self.p_morale,
                       self.p_inj_m, self.p_inj_d, self.p_susp_m, self.p_susp_d,
                       self.p_yellow, self.p_listed, self.player_apply,
                       self.player_reload, self.player_value, *self.p_attrs.values()):
            widget.setEnabled(enabled)

    def _update_level_hint(self, *_):
        if not hasattr(self, "p_attrs") or not self.p_attrs:
            return
        keys = ["technique", "passing", "finishing", "defense", "stamina"]
        if self.p_pos.currentText() == "Gardien":
            keys.append("goalkeeper")
        level = max(1, min(20, int(round(
            sum(self.p_attrs[k].value() for k in keys) / len(keys)))))
        self.p_hint.setText(f"Niveau calculé : {level}/20   •   Potentiel saisi : {self.p_potential.value()}/20")

    def _player_form_data(self):
        return {
            "first_name": self.p_first.text(), "last_name": self.p_last.text(),
            "age": self.p_age.value(), "position": self.p_pos.currentText(),
            "nationality": self.p_nat.text(), "shirt_number": self.p_shirt.value(),
            "club_id": int(self.p_club.currentData() or 0),
            "potential": self.p_potential.value(), "market_value": self.p_value.value(),
            "salary": self.p_salary.value(), "contract_years": self.p_contract.value(),
            "condition": self.p_condition.value(), "morale": self.p_morale.value(),
            "injury_matches": self.p_inj_m.value(), "injury_days": self.p_inj_d.value(),
            "suspension_matches": self.p_susp_m.value(), "suspension_days": self.p_susp_d.value(),
            "yellow_cards": self.p_yellow.value(),
            "transfer_listed": self.p_listed.isChecked(),
            **{key: self.p_attrs[key].value() for key, _ in ATTRS},
        }

    def _apply_player(self):
        if not self._current_pid:
            return

        def run():
            result = self.store.apply_player(self._current_pid, self._player_form_data())
            notice = result.get("notice") or ""
            self._refresh_players(select_pid=self._current_pid)
            self.status.showMessage(
                f"Joueur enregistré. Niveau {result['level']}/20, potentiel {result['potential']}/20. "
                + notice)
        self._guard(run)

    def _reload_player(self):
        if self._current_pid:
            self._load_player(self._current_pid)

    def _recalc_value(self):
        if not self._current_pid:
            return
        try:
            value = self.store.recompute_value(self._current_pid)
        except SaveError as exc:
            QMessageBox.warning(self, "Valeur", str(exc)); return
        self.p_value.setValue(value)
        self.status.showMessage(f"Valeur recalculée : {money(value)}. Clique sur APPLIQUER pour enregistrer.")

    # ---------- staff ----------
    def _refresh_staff(self):
        if not self.store:
            return
        rows = self.store.staff()
        for i, entry in enumerate(rows):
            self._loading = True
            self.staff_checks[i].setChecked(entry["hired"])
            self.staff_levels[i].setValue(max(1, min(5, entry["level"])))
            self.staff_names[i].setText(entry["name"])
            self.staff_nats[i].setText(entry["nat"])
            self._loading = False

    def _apply_staff(self):
        if not self.store:
            return
        entries = []
        for i, (key, label) in enumerate(STAFF_ROLES):
            entries.append({"key": key, "hired": self.staff_checks[i].isChecked(),
                            "level": self.staff_levels[i].value(),
                            "name": self.staff_names[i].text(),
                            "nat": self.staff_nats[i].text()})
        self._guard(lambda: (self.store.update_staff(entries), self._refresh_staff()))

    # ---------- infrastructures ----------
    def _refresh_facility(self):
        if not self.store:
            return
        row = self.store.facility()
        if not row:
            return
        club = self.store.club(1)
        if hasattr(self, "fac_club_label"):
            self.fac_club_label.setText(
                f"Infrastructures de {club['name'] if club else 'ton club'} (ton club)")
        self._loading = True
        for key, _label, low, high in FACILITY_LEVELS:
            if key in row.keys():
                self.fac_spins[key].setValue(max(low, min(high, int(row[key] or low))))
        for key, _label in FACILITY_FLAGS:
            if key in row.keys():
                self.fac_flags[key].setChecked(bool(int(row[key] or 0)))
        self.fac_price.setValue(int(row["ticket_price"] or 12))
        self._loading = False

    def _apply_facility(self):
        if not self.store:
            return
        levels = {k: s.value() for k, s in self.fac_spins.items()}
        flags = {k: c.isChecked() for k, c in self.fac_flags.items()}
        self._guard(lambda: (self.store.update_facility(levels, flags, self.fac_price.value()),
                             self._refresh_facility()))

    # ---------- sauvegardes ----------
    def _refresh_backups(self):
        if not self.store:
            return
        size = os.path.getsize(self.store.path) / (1024 * 1024)
        when = datetime.fromtimestamp(os.path.getmtime(self.store.path)).strftime("%d/%m/%Y %H:%M")
        self.backup_open_path.setText(self.store.path)
        self.backup_open_meta.setText(
            f"{size:.1f} Mo  •  modifié le {when}  •  intégrité : {self.store.quick_check()}  •  "
            f"{self.store.conn.execute('SELECT COUNT(*) FROM player').fetchone()[0]} joueurs  •  "
            f"{self.store.conn.execute('SELECT COUNT(*) FROM club').fetchone()[0]} clubs")
        backup_dir = self.store.backup_dir()
        self.backup_hint.setText(
            f"Les modifications sont écrites immédiatement dans la sauvegarde ouverte. "
            f"Les copies de secours sont rangées dans : {backup_dir} "
            f"(10 plus récentes conservées, invisibles dans CHARGER UNE PARTIE).")
        paths = self.store.list_backups()
        header = self.backups_table.horizontalHeader()
        sort_col = header.sortIndicatorSection()
        sort_order = header.sortIndicatorOrder()
        self.backups_table.setSortingEnabled(False)
        self.backups_table.setRowCount(len(paths))
        for i, path in enumerate(paths):
            name = os.path.basename(path)
            stamp = os.path.getmtime(path)
            when = datetime.fromtimestamp(stamp).strftime("%d/%m/%Y %H:%M:%S")
            bytes_size = os.path.getsize(path)
            size = f"{bytes_size / 1024:.0f} Ko"
            for c, value in enumerate((name, when, size)):
                sorts = (name.casefold(), stamp, bytes_size)
                item = SortableItem(value, sorts[c])
                if c == 0:
                    item.setData(Qt.UserRole, path)
                self.backups_table.setItem(i, c, item)
        self.backups_table.resizeColumnsToContents()
        self.backups_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.backups_table.setSortingEnabled(True)
        if sort_col >= 0:
            self.backups_table.sortItems(sort_col, sort_order)

    def _manual_backup(self):
        if not self.store:
            QMessageBox.information(self, "Sauvegarde", "Ouvre d'abord une sauvegarde.")
            return
        try:
            path = self.store.backup("manuel")
        except (sqlite3.Error, OSError) as exc:
            QMessageBox.critical(self, "Sauvegarde impossible", str(exc)); return
        self._refresh_backups()
        self.status.showMessage(f"Sauvegarde créée : {os.path.basename(path)}")

    def _restore_selected(self):
        if not self.store:
            return
        row = self.backups_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Restauration", "Sélectionne une sauvegarde dans la liste.")
            return
        path = self.backups_table.item(row, 0).data(Qt.UserRole)
        if QMessageBox.question(self, "Restaurer cette sauvegarde ?",
                                f"{os.path.basename(path)}\n\nLa sauvegarde actuelle sera d'abord "
                                "copiée de secours.") != QMessageBox.Yes:
            return
        try:
            safety = self.store.backup("avant_restauration")
            self.store.close()
            temp = self.store.path + ".restauration.tmp"
            shutil.copy2(path, temp)
            os.replace(temp, self.store.path)
            self.store = SaveStore(self.store.path)
        except (sqlite3.Error, OSError, SaveError) as exc:
            QMessageBox.critical(self, "Restauration impossible", str(exc))
            try:
                self.store = SaveStore(self.store.path)
            except SaveError:
                pass
            return
        self._backup_done = None
        self.open_path(self.store.path)
        self.status.showMessage(f"Restauré depuis {os.path.basename(path)} (secours : {os.path.basename(safety)}).")

    def _open_folder(self):
        folder = os.path.dirname(self.store.path) if self.store else str(SAVE_DIR)
        try:
            if sys.platform.startswith("win"):
                os.startfile(folder)  # noqa: S606
            else:
                QMessageBox.information(self, "Dossier", folder)
        except OSError:
            QMessageBox.information(self, "Dossier", folder)

    def _open_backup_folder(self):
        folder = self.store.backup_dir() if self.store else str(SAVE_DIR / "editeur_backups")
        try:
            os.makedirs(folder, exist_ok=True)
            if sys.platform.startswith("win"):
                os.startfile(folder)  # noqa: S606
            else:
                QMessageBox.information(self, "Dossier des copies", folder)
        except OSError:
            QMessageBox.information(self, "Dossier des copies", folder)

    def _update_save_header(self):
        if not self.store:
            self.save_chip.setText("AUCUNE SAUVEGARDE")
            self.save_chip.setStyleSheet("background:#1a2230;color:#8a97ab;border:1px solid #2b3953;")
            self.save_meta.setText("Choisis une sauvegarde puis clique sur OUVRIR.")
            return
        if self.store.read_only:
            text = "VERROUILLÉE"
            style = "background:#3a1720;color:#ffb3c0;border:1px solid #7a2c3d;"
        elif self.store.sidecar:
            text = "JEU OUVERT ?"
            style = "background:#3a2c12;color:#ffd98a;border:1px solid #7a5c24;"
        else:
            text = "PRÊTE · ÉCRITURE"
            style = "background:#173a2b;color:#8fe0a3;border:1px solid #2f6b4a;"
        self.save_chip.setText(text)
        self.save_chip.setStyleSheet(style)
        club = self.store.club(1)
        count = self.store.conn.execute("SELECT COUNT(*) FROM player").fetchone()[0]
        size = os.path.getsize(self.store.path) / (1024 * 1024)
        when = datetime.fromtimestamp(os.path.getmtime(self.store.path)).strftime("%d/%m %H:%M")
        club_text = f"{club['name']} · L{club['division']} · saison {club['season']}" if club else "—"
        self.save_meta.setText(
            f"{os.path.basename(self.store.path)}  •  {size:.1f} Mo  •  modifié {when}  •  "
            f"{club_text}  •  {count} joueurs")
        self.save_meta.setToolTip(self.store.path)

    def _duplicate_for_test(self):
        if not self.store:
            QMessageBox.information(self, "Copie de travail",
                                    "Ouvre d'abord une sauvegarde.")
            return
        stem = os.path.splitext(os.path.basename(self.store.path))[0]
        default = os.path.join(os.path.dirname(self.store.path), f"{stem}_test.db")
        destination, _ = QFileDialog.getSaveFileName(
            self, "Dupliquer la sauvegarde pour tester", default,
            "Sauvegardes FM2027 (*.db)")
        if not destination:
            return
        if not destination.lower().endswith(".db"):
            destination += ".db"
        try:
            new_path = self.store.duplicate(destination)
        except SaveError as exc:
            QMessageBox.warning(self, "Copie impossible", str(exc)); return
        self._reload_save_list()
        self.open_path(new_path)
        self.status.showMessage(
            f"Copie de travail créée : {os.path.basename(new_path)}. "
            "Ouvre-la dans CHARGER UNE PARTIE pour jouer avec.")
        QMessageBox.information(
            self, "Copie de travail créée",
            f"{os.path.basename(new_path)}\n\n"
            "L'éditeur travaille désormais sur cette copie. Elle apparaît aussi "
            "dans CHARGER UNE PARTIE du jeu : c'est elle que tu peux utiliser "
            "pour tester sans toucher à la carrière d'origine.")

    def closeEvent(self, event):
        if self.store:
            self.store.close()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    try:
        window = EditorWindow(auto_open=True)
        window.show()
    except Exception as exc:  # message lisible plutôt qu'un crash muet
        QMessageBox.critical(None, "Éditeur de sauvegarde", str(exc))
        return 1
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
