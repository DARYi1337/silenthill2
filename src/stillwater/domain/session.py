"""Модель игрового прогресса и идемпотентные правила прохождения."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import json
from pathlib import Path
import shutil
from typing import Any


class InteractionResult(StrEnum):
    """Стабильные результаты, которые игровой слой отображает игроку."""

    NO_TARGET = "no_target"
    FUSE_PICKED_UP = "fuse_picked_up"
    FUSE_ALREADY_CARRIED = "fuse_already_carried"
    POWER_RESTORED = "power_restored"
    FUSE_REQUIRED = "fuse_required"
    NOTE_READ = "note_read"
    DOOR_OPENED = "door_opened"
    DOOR_CLOSED = "door_closed"
    DOOR_LOCKED = "door_locked"
    ALREADY_DONE = "already_done"
    UNKNOWN_TARGET = "unknown_target"


@dataclass(slots=True)
class GameSession:
    """Единственный источник истины о прогрессе эпизода."""

    scene_id: str = "station"
    spawn_id: str = "station_entry"
    inventory: set[str] = field(default_factory=set)
    read_notes: set[str] = field(default_factory=set)
    fusebox_solved: bool = False
    door_open: bool = False
    played_sequences: set[str] = field(default_factory=set)

    def interact(self, target_id: str) -> InteractionResult:
        """Выполнить одно предметное действие без побочных эффектов движка."""
        if target_id == "fuse_pickup":
            if "fuse" in self.inventory:
                return InteractionResult.FUSE_ALREADY_CARRIED
            self.inventory.add("fuse")
            return InteractionResult.FUSE_PICKED_UP

        if target_id == "fusebox":
            if self.fusebox_solved:
                return InteractionResult.ALREADY_DONE
            if "fuse" not in self.inventory:
                return InteractionResult.FUSE_REQUIRED
            self.inventory.remove("fuse")
            self.fusebox_solved = True
            return InteractionResult.POWER_RESTORED

        if target_id == "note":
            self.read_notes.add("maintenance_note")
            return InteractionResult.NOTE_READ

        if target_id == "exit_door":
            if not self.fusebox_solved:
                return InteractionResult.DOOR_LOCKED
            self.door_open = not self.door_open
            return (
                InteractionResult.DOOR_OPENED
                if self.door_open
                else InteractionResult.DOOR_CLOSED
            )

        return InteractionResult.UNKNOWN_TARGET

    def to_dict(self) -> dict[str, Any]:
        """Преобразовать прогресс к стабильному JSON-формату."""
        return {
            "schema_version": 1,
            "scene_id": self.scene_id,
            "spawn_id": self.spawn_id,
            "inventory": sorted(self.inventory),
            "read_notes": sorted(self.read_notes),
            "fusebox_solved": self.fusebox_solved,
            "door_open": self.door_open,
            "played_sequences": sorted(self.played_sequences),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GameSession:
        """Проверить версию и восстановить только устойчивый прогресс."""
        if data.get("schema_version") != 1:
            raise ValueError("Неподдерживаемая версия сохранения")
        return cls(
            scene_id=str(data.get("scene_id", "station")),
            spawn_id=str(data.get("spawn_id", "station_entry")),
            inventory={str(value) for value in data.get("inventory", [])},
            read_notes={str(value) for value in data.get("read_notes", [])},
            fusebox_solved=bool(data.get("fusebox_solved", False)),
            door_open=bool(data.get("door_open", False)),
            played_sequences={
                str(value) for value in data.get("played_sequences", [])
            },
        )


class SaveService:
    """Атомарное JSON-сохранение с резервной копией последнего состояния."""

    def __init__(self, save_path: Path) -> None:
        self.save_path = save_path
        self.backup_path = save_path.with_suffix(".bak.json")

    def load(self) -> GameSession:
        """Загрузить основное сохранение или его резервную копию."""
        for candidate in (self.save_path, self.backup_path):
            if not candidate.exists():
                continue
            try:
                payload = json.loads(candidate.read_text(encoding="utf-8"))
                return GameSession.from_dict(payload)
            except (OSError, json.JSONDecodeError, TypeError, ValueError):
                continue
        return GameSession()

    def save(self, session: GameSession) -> None:
        """Сначала записать временный файл, затем атомарно заменить слот."""
        self.save_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.save_path.with_suffix(".tmp")
        serialized = json.dumps(
            session.to_dict(), ensure_ascii=False, indent=2
        )
        temporary_path.write_text(serialized + "\n", encoding="utf-8")
        if self.save_path.exists():
            shutil.copy2(self.save_path, self.backup_path)
        temporary_path.replace(self.save_path)
