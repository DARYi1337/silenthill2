"""Сборка первой тестовой локации из процедурных low-poly форм."""

from __future__ import annotations

from dataclasses import dataclass

from ursina import Entity, color
from ursina.shaders import unlit_with_fog_shader


PALETTE = {
    "floor": color.rgb(61, 64, 58),
    "wall": color.rgb(72, 78, 75),
    "dark_wall": color.rgb(45, 51, 49),
    "metal": color.rgb(85, 93, 92),
    "rust": color.rgb(102, 69, 49),
    "warm_light": color.rgb(207, 157, 87),
    "cold_light": color.rgb(134, 163, 165),
}


@dataclass(slots=True)
class Interactable:
    """Визуальный объект, связанный с постоянным предметным ID."""

    instance: Entity
    target_id: str
    prompt: str
    interaction_point_offset: tuple[float, float, float] = (0, 0.35, 0)

    @property
    def interaction_point(self) -> tuple[float, float, float]:
        return (
            self.instance.x + self.interaction_point_offset[0],
            self.instance.y + self.interaction_point_offset[1],
            self.instance.z + self.interaction_point_offset[2],
        )


class StationScene:
    """Первая локация с тремя точками интереса и итоговым выходом."""

    def __init__(self) -> None:
        self.root = Entity(name="station_scene_root")
        self.interactables: list[Interactable] = []
        self.switch_visuals: list[Entity] = []
        self.light_entities: list[Entity] = []
        self._build_room()
        self._build_objects()
        self.apply_progress(fusebox_solved=False, door_open=False)

    def _part(
        self,
        name: str,
        position: tuple[float, float, float],
        scale: tuple[float, float, float],
        tint,
        collider: str | None = None,
        model: str = "cube",
        **kwargs,
    ) -> Entity:
        return Entity(
            parent=self.root,
            name=name,
            model=model,
            position=position,
            scale=scale,
            color=tint,
            collider=collider,
            **kwargs,
        )

    def _build_room(self) -> None:
        floor_tint = PALETTE["floor"]
        wall = PALETTE["wall"]
        self._part("floor", (0, -0.12, 4), (14, 0.24, 22), floor_tint, "box")
        self._part("ceiling", (0, 3.7, 4), (14, 0.25, 22), color.rgb(38, 43, 43), "box")
        self._part("left_wall", (-7, 1.8, 4), (0.3, 3.6, 22), wall, "box")
        self._part("right_wall", (7, 1.8, 4), (0.3, 3.6, 22), wall, "box")
        self._part("back_wall", (0, 1.8, 15), (14, 3.6, 0.3), wall, "box")

        # Передняя стена с широким центральным проходом и непрозрачными стойками.
        self._part("entry_left", (-5.2, 1.8, -7), (3.6, 3.6, 0.3), PALETTE["dark_wall"], "box")
        self._part("entry_right", (5.2, 1.8, -7), (3.6, 3.6, 0.3), PALETTE["dark_wall"], "box")
        self._part("entry_header", (0, 3.28, -7), (6.8, 0.55, 0.3), PALETTE["dark_wall"], "box")

        # Опоры и балки визуально дробят пустую комнату на читаемые зоны.
        for z_pos in (-2, 4.5, 10.7):
            for x_pos in (-3.0, 3.0):
                self._part(
                    "support_pillar",
                    (x_pos, 1.75, z_pos),
                    (0.42, 3.5, 0.55),
                    color.rgb(63, 68, 65),
                    "box",
                )
        for x_pos in (-4.7, 0, 4.7):
            self._part("ceiling_beam", (x_pos, 3.42, 4), (0.25, 0.34, 21.8), color.rgb(42, 46, 44))

        # Сырость, масляные следы и дорожка сделаны плоскими цветными формами.
        for x_pos, z_pos, sx, sz in (
            (-4.2, 1.0, 2.2, 4.0),
            (4.1, 8.5, 2.4, 3.4),
            (-1.7, 11.0, 3.0, 1.4),
            (1.3, -2.0, 1.8, 2.2),
        ):
            self._part(
                "oil_stain",
                (x_pos, 0.011, z_pos),
                (sx, 0.012, sz),
                color.rgba(30, 37, 35, 170),
            )

        # Вешала и трубы создают дополнительный масштаб, не блокируя путь.
        self._part("overhead_pipe", (0, 3.05, 5), (0.19, 0.19, 17), PALETTE["rust"])
        self._part("overhead_pipe_west", (-6.35, 2.87, 4), (0.15, 0.15, 17), PALETTE["metal"])

        # Лёгкая рамка дальнего выходного проёма.
        for x_pos in (-1.35, 1.35):
            self._part("exit_jamb", (x_pos, 1.25, 15), (0.25, 2.5, 0.3), PALETTE["rust"], "box")
        self._part("exit_header", (0, 2.55, 15), (2.8, 0.28, 0.3), PALETTE["rust"], "box")

        # Тонкая однотонная дымка оставляет силуэты читаемыми.
        Entity.default_shader = unlit_with_fog_shader

    def _build_objects(self) -> None:
        pickup = self._part(
            "fuse_pickup",
            (-4.55, 0.18, 2.0),
            (0.28, 0.48, 0.24),
            color.rgb(202, 157, 84),
            model="cube",
            rotation=(8, 0, 14),
        )
        self._register(pickup, "fuse_pickup", "Взять предохранитель")

        note = self._part(
            "maintenance_note",
            (-4.05, 0.23, 2.0),
            (0.44, 0.06, 0.32),
            color.rgb(172, 163, 135),
            model="cube",
            rotation=(0, 12, -8),
        )
        self._register(note, "note", "Прочитать записку")

        panel = self._part(
            "fusebox_visual",
            (5.62, 1.38, 10.2),
            (0.52, 1.75, 1.0),
            color.rgb(61, 70, 69),
            "box",
        )
        panel.rotation_y = -90
        self._register(panel, "fusebox", "Осмотреть электрощит")
        for index in range(3):
            switch = Entity(
                parent=self.root,
                model="cube",
                position=(5.30, 1.48 + index * 0.24, 10.2),
                scale=(0.13, 0.11, 0.3),
                color=color.rgb(128, 90, 63),
            )
            switch.rotation_z = -30
            self.switch_visuals.append(switch)
        self._part("warning_label", (5.30, 0.96, 10.18), (0.05, 0.16, 0.4), color.rgb(166, 112, 65))

        door = self._part(
            "exit_door_visual",
            (0, 1.18, 15),
            (2.35, 2.28, 0.14),
            color.rgb(70, 78, 74),
            "box",
        )
        self._register(door, "exit_door", "Проверить выход")
        handle = self._part("door_handle", (0.78, 1.14, 14.88), (0.13, 0.13, 0.12), PALETTE["warm_light"])
        self._door_handle = handle

        self._build_light_fixtures()

    def _build_light_fixtures(self) -> None:
        from ursina.lights import PointLight

        for index, z_pos in enumerate((-3.8, 3.7, 11.1)):
            self._part(
                f"lamp_fixture_{index}",
                (0, 3.33, z_pos),
                (1.15, 0.12, 0.48),
                color.rgb(62, 68, 67),
            )
            bulb = self._part(
                f"lamp_bulb_{index}",
                (0, 3.20, z_pos),
                (0.65, 0.08, 0.20),
                color.rgb(117, 111, 92),
            )
            lamp = PointLight(position=(0, 3.03, z_pos), color=color.rgb(54, 61, 58))
            lamp._bulb = bulb
            self.light_entities.append(lamp)

    def _register(self, instance: Entity, target_id: str, prompt: str) -> None:
        self.interactables.append(Interactable(instance, target_id, prompt))

    def apply_progress(self, fusebox_solved: bool, door_open: bool) -> None:
        """Отобразить устойчивое состояние без повторного проигрывания события."""
        for lamp in self.light_entities:
            if fusebox_solved:
                lamp.color = PALETTE["warm_light"]
                lamp._light.setColor((0.74, 0.55, 0.31, 1.0))
                lamp._bulb.color = color.rgb(226, 189, 129)
            else:
                lamp.color = color.rgb(54, 61, 58)
                lamp._light.setColor((0.12, 0.14, 0.14, 1.0))
                lamp._bulb.color = color.rgb(117, 111, 92)

        for switch in self.switch_visuals:
            switch.rotation_z = 28 if fusebox_solved else -30
            switch.color = color.rgb(178, 133, 75) if fusebox_solved else color.rgb(128, 90, 63)

        door = next(item.instance for item in self.interactables if item.target_id == "exit_door")
        door.color = color.rgb(111, 116, 101) if fusebox_solved else color.rgb(70, 78, 74)
        if door_open:
            door.rotation_y = -88
            door.x = -1.13
            self._door_handle.x = -1.87
        else:
            door.rotation_y = 0
            door.x = 0
            self._door_handle.x = 0.78

    def set_light_flicker(self, enabled: bool) -> None:
        if not enabled:
            return
        for lamp in self.light_entities:
            lamp._light.setColor((0.9, 0.62, 0.29, 1.0))

    def dispose(self) -> None:
        self.root.disable()
        for light in self.light_entities:
            light.disable()
