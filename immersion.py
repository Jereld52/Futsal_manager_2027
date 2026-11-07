"""Ambiance sonore et commentaire live de Futsal Manager 2027.

Aucun asset externe : les sons de salle sont de petits WAV synthétisés une
seule fois dans `data/audio`. En mode hors écran ou avec `FM2027_NO_AUDIO=1`,
tout est silencieux et aucun fichier n'est créé.
"""
from __future__ import annotations

import math
import os
import random
import re
import struct
import wave
from pathlib import Path

SAMPLE_RATE = 22050

SOUND_FOR_CATEGORY = {
    "goal": "goal",
    "shot": "shot",
    "save": "save",
    "yellow_card": "whistle",
    "red": "whistle",
    "kickoff": "whistle",
    "halftime": "buzzer",
    "fulltime": "buzzer",
    "timeout": "buzzer",
    "substitution": "crowd",
    "injury": "crowd",
    "corner": "crowd",
}

COMMENTARY_PREFIX = {
    "goal": "La salle explose !",
    "shot": "Ça chauffe devant le but.",
    "save": "Quel arrêt !",
    "yellow_card": "Le carton tombe.",
    "red": "Le match bascule.",
    "kickoff": "Coup d'envoi.",
    "halftime": "C'est la pause.",
    "fulltime": "Coup de sifflet final.",
    "timeout": "Temps mort.",
    "substitution": "Changement sur le banc.",
    "injury": "Inquiétude sur le terrain.",
    "corner": "Corner à suivre.",
    "interception": "Récupération.",
    "pass": "Le ballon circule.",
    "turnover": "Ballon rendu.",
    "coach": "Sur le banc.",
    "ten_metre": "Coup franc à 10 mètres.",
    "instruction": "Consigne du coach.",
    "lineup": "Composition.",
}


def _clean_event(text):
    text = re.sub(r"<br\s*/?>", " ", str(text or ""), flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"^\s*\d{1,2}:\d{2}\s*[—–-]\s*", "", text)
    return re.sub(r"\s+", " ", text).strip()


def commentary_line(category, text):
    """Ligne de commentaire courte et vivante à partir d'un événement."""
    clean = _clean_event(text)
    if not clean:
        return ""
    prefix = COMMENTARY_PREFIX.get(str(category or "").lower(), "")
    if not prefix:
        return clean
    if clean.lower().startswith(prefix.lower()[:12]):
        return clean
    return f"{prefix} {clean}"


class ArenaSound:
    """Petits effets de salle synthétisés, sans dépendance à des fichiers."""

    def __init__(self, data_dir, enabled=True, volume=0.55):
        self.audio_dir = Path(data_dir) / "audio"
        self.volume = max(0.0, min(1.0, float(volume or 0.0)))
        silent = (os.environ.get("QT_QPA_PLATFORM", "") == "offscreen"
                  or os.environ.get("FM2027_NO_AUDIO", "") == "1")
        self.silent = silent
        self.enabled = bool(enabled) and not silent
        self._effects = {}
        self._ambience = None
        self._qt = False
        try:
            from PySide6.QtMultimedia import QSoundEffect  # noqa: F401
            self._qt = True
        except Exception:
            self._qt = False
        if self.enabled:
            try:
                self._ensure_assets()
            except Exception:
                self.enabled = False

    # --- Synthèse des WAV -----------------------------------------------------
    def _write(self, name, samples):
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        path = self.audio_dir / f"{name}.wav"
        if path.exists():
            return path
        with wave.open(str(path), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(SAMPLE_RATE)
            handle.writeframes(b"".join(
                struct.pack("<h", max(-32767, min(32767, int(value * 32767))))
                for value in samples))
        return path

    @staticmethod
    def _envelope(index, total, attack=0.02, release=0.25):
        if total <= 0:
            return 0.0
        pos = index / total
        if pos < attack:
            return pos / max(1e-6, attack)
        if pos > 1.0 - release:
            return max(0.0, (1.0 - pos) / max(1e-6, release))
        return 1.0

    def _ensure_assets(self):
        import random as _random
        rng = _random.Random(2027)

        def tone(freq, duration, gain=0.5, wobble=0.0, noise=0.0):
            count = int(SAMPLE_RATE * duration)
            data = []
            for i in range(count):
                t = i / SAMPLE_RATE
                value = math.sin(2 * math.pi * freq * t)
                if wobble:
                    value = 0.7 * value + 0.3 * math.sin(
                        2 * math.pi * (freq + wobble * math.sin(2 * math.pi * 7 * t)) * t)
                value *= gain * self._envelope(i, count, 0.01, 0.4)
                if noise:
                    value += (rng.random() * 2 - 1) * noise * self._envelope(i, count, 0.01, 0.5)
                data.append(value)
            return data

        whistle = tone(2050, 0.55, 0.42, wobble=90, noise=0.05)
        self._write("whistle", whistle)
        self._write("buzzer", tone(155, 0.8, 0.42, wobble=3, noise=0.02))
        self._write("shot", tone(95, 0.16, 0.5, noise=0.45))
        self._write("save", tone(180, 0.22, 0.4, noise=0.35))
        self._write("goal", self._crowd(duration=2.0, gain=0.55, burst=True))
        self._write("crowd", self._crowd(duration=5.0, gain=0.30, burst=False))
        self._write("applause", self._crowd(duration=1.4, gain=0.40, burst=True))

    @staticmethod
    def _crowd(duration, gain, burst=False):
        rng = random.Random(2027 if not burst else 2028)
        count = int(SAMPLE_RATE * duration)
        data = []
        smoothed = 0.0
        for i in range(count):
            noise = rng.random() * 2 - 1
            smoothed = 0.92 * smoothed + 0.08 * noise
            pos = i / max(1, count)
            env = (0.5 - 0.5 * math.cos(2 * math.pi * min(1.0, pos * 1.6))) if burst else (
                0.75 + 0.25 * math.sin(2 * math.pi * 0.35 * pos))
            if pos > 0.75:
                env *= max(0.0, (1.0 - pos) / 0.25)
            data.append((smoothed * 1.7 + noise * 0.12) * gain * env)
        return data

    # --- Lecture ---------------------------------------------------------------
    def _effect(self, name):
        if not self.enabled:
            return None
        path = self.audio_dir / f"{name}.wav"
        if not path.exists():
            return None
        if self._qt:
            if name in self._effects:
                return self._effects[name]
            try:
                from PySide6.QtCore import QUrl
                from PySide6.QtMultimedia import QSoundEffect
                effect = QSoundEffect()
                effect.setSource(QUrl.fromLocalFile(str(path)))
                effect.setVolume(self.volume)
                self._effects[name] = effect
                return effect
            except Exception:
                self._qt = False
        return None

    def play(self, name, volume=None):
        if not self.enabled:
            return
        effect = self._effect(name)
        if effect is not None:
            try:
                effect.setVolume(self.volume if volume is None else max(0.0, min(1.0, volume)))
                effect.play()
                return
            except Exception:
                pass
        try:
            import winsound
            winsound.PlaySound(str(self.audio_dir / f"{name}.wav"),
                               winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception:
            pass

    def start_ambience(self):
        if not self.enabled:
            return
        if self._ambience is None:
            self._ambience = self._effect("crowd")
            if self._ambience is not None:
                try:
                    from PySide6.QtMultimedia import QSoundEffect
                    self._ambience.setLoopCount(QSoundEffect.Infinite)
                    self._ambience.setVolume(self.volume * 0.45)
                except Exception:
                    pass
        if self._ambience is not None:
            try:
                self._ambience.play()
            except Exception:
                pass

    def stop_ambience(self):
        if self._ambience is not None:
            try:
                self._ambience.stop()
            except Exception:
                pass

    def set_enabled(self, enabled):
        self.enabled = bool(enabled) and not getattr(self, "silent", False)
        if not self.enabled:
            self.stop_ambience()

    def close(self):
        self.stop_ambience()
        self._effects.clear()
        self._ambience = None
