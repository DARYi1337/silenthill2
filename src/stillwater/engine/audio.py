"""Процедурный звук-прототип без внешних игровых ассетов."""

from __future__ import annotations

from array import array
import math
from pathlib import Path
import random
import struct
import wave

from ursina import Audio, Entity


def ensure_ambient_asset(asset_path: Path) -> None:
    """Создать короткий тихий моно-луп, если ещё нет авторского ассета."""
    if asset_path.exists():
        return
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = 16000
    duration_seconds = 4
    sample_count = sample_rate * duration_seconds
    rng = random.Random(2202)
    frame_data = array("h")
    phase = 0.0
    phase_step = 2 * math.pi * 47.0 / sample_rate
    previous_noise = 0.0
    for index in range(sample_count):
        sample = index / sample_rate
        phase += phase_step
        noise = previous_noise * 0.98 + rng.uniform(-1.0, 1.0) * 0.02
        previous_noise = noise
        loop_envelope = min(1.0, sample / 0.12, (duration_seconds - sample) / 0.12)
        value = (math.sin(phase) * 0.12 + noise * 0.42) * max(0.0, loop_envelope)
        frame_data.append(int(max(-1.0, min(1.0, value)) * 32767 * 0.2))
    if struct.pack("=h", 1) != struct.pack("<h", 1):
        frame_data.byteswap()
    with wave.open(str(asset_path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(frame_data.tobytes())


def ensure_stinger_asset(asset_path: Path) -> None:
    """Создать короткий металлический импульс для перехода состояния."""
    if asset_path.exists():
        return
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = 16000
    duration_seconds = 0.65
    sample_count = int(sample_rate * duration_seconds)
    frame_data = array("h")
    for index in range(sample_count):
        sample = index / sample_rate
        envelope = max(0.0, 1.0 - sample / duration_seconds) ** 2
        value = (
            math.sin(2 * math.pi * 96 * sample)
            + 0.45 * math.sin(2 * math.pi * 181 * sample)
            + 0.2 * math.sin(2 * math.pi * 410 * sample)
        ) * envelope * 0.18
        frame_data.append(int(value * 32767))
    with wave.open(str(asset_path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(frame_data.tobytes())


class AmbientSound:
    """Пространственный гул станции и короткие атмосферные удары."""

    def __init__(self, asset_path: Path, stinger_path: Path) -> None:
        ensure_ambient_asset(asset_path)
        ensure_stinger_asset(stinger_path)
        self.loop = Audio(
            asset_path, loop=True, autoplay=True, volume=0.19, auto_destroy=False
        )
        self.listener_anchor = Entity(position=(0, 1.0, 0), add_to_scene_entities=False)
        self.stinger_path = stinger_path
        self.one_shots: list[Audio] = []

    def play_stinger(self) -> None:
        """Короткий тихий пространственный удар при восстановлении питания."""
        if self.one_shots:
            return
        stinger = Audio(
            self.stinger_path,
            loop=False,
            autoplay=True,
            volume=0.22,
            auto_destroy=False,
        )
        if not stinger.clip:
            stinger.stop()
            return
        self.one_shots.append(stinger)

    def update(self, player_position: tuple[float, float, float]) -> None:
        self.listener_anchor.position = player_position

    def dispose(self) -> None:
        self.loop.stop()
        for sound in self.one_shots:
            sound.stop()
        self.listener_anchor.disable()
