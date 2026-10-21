"""Кинематическое управление и камера третьего лица."""

from __future__ import annotations

from math import atan2, cos, degrees, radians, sin

from ursina import Entity, Vec3, camera, color, held_keys, lerp, mouse, raycast, time
from ursina.collider import BoxCollider


class PlayerController(Entity):
    """Коллайдер персонажа и базовое движение относительно камеры."""

    WALK_SPEED = 1.65
    RUN_SPEED = 3.1
    RADIUS = 0.34
    HEIGHT = 1.72

    def __init__(self, spawn=(0, 0, -4)) -> None:
        super().__init__(
            name="player_controller",
            position=spawn,
            add_to_scene_entities=True,
        )
        self.model = None
        self.collider = BoxCollider(
            self,
            center=(0, self.HEIGHT / 2, 0),
            size=(self.RADIUS * 2, self.HEIGHT, self.RADIUS * 2),
        )
        self.last_safe_position = self.position
        self.visual = self._create_low_poly_character()
        self.walk_phase = 0.0
        self.camera_yaw = 0.0
        self.camera_pitch = 10.0
        self.camera_distance = 4.2
        self.camera_height = 2.55
        self._setup_camera()

    def _create_low_poly_character(self) -> Entity:
        silhouette = Entity(parent=self, position=(0, 0.05, 0))
        Entity(
            parent=silhouette,
            model="cube",
            color=color.rgb(38, 42, 42),
            position=(0, 0.93, 0),
            scale=(0.48, 0.83, 0.30),
        )
        Entity(
            parent=silhouette,
            model="sphere",
            color=color.rgb(155, 137, 113),
            position=(0, 1.48, 0),
            scale=(0.37, 0.39, 0.34),
            subdivision=1,
        )
        for side in (-1, 1):
            Entity(
                parent=silhouette,
                model="cube",
                color=color.rgb(35, 37, 37),
                position=(side * 0.14, 0.33, 0.02),
                scale=(0.18, 0.58, 0.22),
            )
            Entity(
                parent=silhouette,
                model="cube",
                color=color.rgb(28, 29, 29),
                position=(side * 0.29, 0.90, 0),
                scale=(0.17, 0.67, 0.22),
            )
        return silhouette

    def _setup_camera(self) -> None:
        camera.parent = None
        camera.fov = 62
        camera.clip_plane_far = 90
        camera.rotation = (0, 0, 0)

    def update(self) -> None:
        dt = min(time.dt, 0.05)
        self.camera_yaw += float(mouse.velocity[0]) * 110.0
        self.camera_pitch = max(
            -3.0,
            min(34.0, self.camera_pitch - float(mouse.velocity[1]) * 90.0),
        )
        self._move(dt)
        self._update_animation(dt)
        self._update_camera(dt)

    def _move(self, dt: float) -> None:
        input_x = held_keys["d"] - held_keys["a"]
        input_z = held_keys["w"] - held_keys["s"]
        direction_length = (input_x * input_x + input_z * input_z) ** 0.5
        if direction_length <= 0:
            return
        input_x /= direction_length
        input_z /= direction_length

        yaw = radians(self.camera_yaw)
        direction = Vec3(
            input_x * cos(yaw) + input_z * sin(yaw),
            0,
            -input_x * sin(yaw) + input_z * cos(yaw),
        )
        running = bool(held_keys["shift"])
        speed = self.RUN_SPEED if running else self.WALK_SPEED
        distance = min(speed * dt, 0.15)
        origin = self.position + Vec3(0, 0.8, 0)
        moved = False
        for axis in ("x", "z"):
            axis_amount = getattr(direction, axis) * distance
            if abs(axis_amount) < 0.0001:
                continue
            axis_direction = Vec3(1 if axis_amount > 0 else -1, 0, 0) if axis == "x" else Vec3(0, 0, 1 if axis_amount > 0 else -1)
            hit = raycast(
                origin=origin,
                direction=axis_direction,
                distance=abs(axis_amount) + self.RADIUS + 0.06,
                ignore=[self],
            )
            if not hit.hit:
                setattr(self, axis, getattr(self, axis) + axis_amount)
                moved = True

        if moved:
            self.rotation_y = lerp_angle(
                self.rotation_y,
                self.camera_yaw + degrees(atan2(direction.x, direction.z)),
                min(1.0, dt * 11.0),
            )
            self.last_safe_position = self.position

    def _update_animation(self, dt: float) -> None:
        moving = abs(held_keys["w"]) + abs(held_keys["a"]) + abs(held_keys["s"]) + abs(held_keys["d"]) > 0
        self.walk_phase += dt * (10.0 if held_keys["shift"] else 6.5) if moving else 0.0
        swing = sin(self.walk_phase) * (0.045 if moving else 0.0)
        for child in self.visual.children:
            if child.model:
                child.rotation_x = swing if abs(child.x) > 0.2 else -swing

    def _update_camera(self, dt: float) -> None:
        yaw = radians(self.camera_yaw)
        pitch = radians(self.camera_pitch)
        horizontal = self.camera_distance * cos(pitch)
        desired = self.position + Vec3(
            -sin(yaw) * horizontal,
            self.camera_height + sin(pitch) * self.camera_distance,
            -cos(yaw) * horizontal,
        )
        focus = self.position + Vec3(0, 1.25, 0)
        segment = desired - focus
        hit = raycast(
            origin=focus,
            direction=segment.normalized(),
            distance=segment.length(),
            ignore=[self],
        )
        if hit.hit:
            desired = hit.world_point + hit.world_normal * 0.18
        blend = 1.0 - pow(0.001, dt)
        camera.position = lerp(camera.position, desired, blend)
        camera.look_at(focus)


def lerp_angle(start: float, end: float, amount: float) -> float:
    """Интерполировать угол по кратчайшему пути."""
    difference = (end - start + 180.0) % 360.0 - 180.0
    return start + difference * amount
