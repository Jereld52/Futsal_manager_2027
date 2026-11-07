"""Rapport de bug auto-suffisant pour la bêta de Futsal Manager 2027."""
from __future__ import annotations

import json
import os
import platform
import shutil
import sqlite3
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path


def _safe_text(value, limit=8000):
    text = str(value or "")
    return text[:limit]


def _copy_if_exists(source, zf, arcname, limit=2_000_000):
    try:
        path = Path(source)
        if not path.is_file():
            return False
        with path.open("rb") as handle:
            data = handle.read(limit)
        zf.writestr(arcname, data)
        return True
    except OSError:
        return False


def _save_snapshot(save_path, destination):
    source = sqlite3.connect(str(save_path), timeout=5)
    target = sqlite3.connect(str(destination))
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()


def create_bug_report(dest_dir, description, data_dir=None, save_path=None,
                      include_save=False, app_version="2027.2", extra=None):
    """Crée un ZIP de diagnostic et retourne son chemin.

    Le fichier de sauvegarde n'est jamais modifié : une copie est faite via
    l'API backup de SQLite dans un fichier temporaire.
    """
    data_dir = Path(data_dir or ".")
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = dest_dir / f"rapport_bug_{stamp}.zip"
    description = _safe_text(description, 8000)
    temp_save = None
    try:
        with zipfile.ZipFile(report_path, "w", zipfile.ZIP_DEFLATED) as zf:
            lines = [
                "FUTSAL MANAGER 2027 — RAPPORT DE BUG",
                "====================================",
                f"Date : {datetime.now().isoformat(timespec='seconds')}",
                f"Version : {app_version}",
                f"Système : {platform.platform()}",
                f"Python : {sys.version.split()[0]}",
            ]
            try:
                import PySide6
                lines.append(f"PySide6 : {PySide6.__version__}")
            except Exception:
                pass
            if save_path:
                lines.append(f"Sauvegarde active : {save_path}")
                try:
                    conn = sqlite3.connect(str(save_path), timeout=5)
                    club = conn.execute("SELECT name,division,season FROM club WHERE id=1").fetchone()
                    career = conn.execute("SELECT current_date,matchday FROM career WHERE id=1").fetchone()
                    players = conn.execute("SELECT COUNT(*) FROM player").fetchone()[0]
                    conn.close()
                    if club:
                        lines.append(f"Club : {club[0]} • Ligue {club[1]} • saison {club[2]}")
                    if career:
                        lines.append(f"Date de carrière : {career[0]} • journée {career[1]}")
                    lines.append(f"Joueurs dans la base : {players}")
                except (sqlite3.Error, OSError):
                    pass
            if extra:
                lines.append("")
                lines.append("Contexte :")
                for key, value in dict(extra).items():
                    lines.append(f"- {key} : {_safe_text(value, 1000)}")
            lines.extend(["", "DESCRIPTION", "-----------", description or "(non renseignée)", ""])
            zf.writestr("rapport.txt", "\n".join(lines).encode("utf-8"))

            _copy_if_exists(data_dir / "error.log", zf, "error.log")
            _copy_if_exists(data_dir / "fault.log", zf, "fault.log")
            _copy_if_exists(data_dir / "game_options.json", zf, "game_options.txt")
            _copy_if_exists(data_dir / "ui_trace.log", zf, "ui_trace.log", limit=500_000)

            if include_save and save_path and Path(save_path).is_file():
                temp_save = Path(tempfile.mkdtemp(prefix="fm_bug_")) / "sauvegarde_active.db"
                try:
                    _save_snapshot(save_path, temp_save)
                    zf.write(temp_save, "sauvegarde_active.db")
                except (sqlite3.Error, OSError):
                    pass
        return str(report_path)
    finally:
        if temp_save is not None:
            try:
                shutil.rmtree(temp_save.parent, ignore_errors=True)
            except OSError:
                pass


__all__ = ["create_bug_report"]
