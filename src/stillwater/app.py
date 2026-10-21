"""Оркестрация игрового концепта, ввода, интерфейса и игровых систем."""

from __future__ import annotations

from pathlib import Path
import sys

from ursina import (
    Audio,
    Entity,
    Text,
    application,
    camera,
    color,
    held_keys,
    mouse,
    raycast,
    time,
    window,
)
from ursina.collider import BoxCollider

from stillwater.domain.session import GameSession, InteractionResult, SaveService
from stillwater.engine.audio import AmbientSound
from stillwater.engine.player import PlayerController
from stillwater.engine.rendering import RetroPipeline
from stillwater.engine.scene import Interactable, StationScene
from stillwater.engine.shaders import WORLD_SHADER, set_global_light_state


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ASSET_ROOT = PROJECT_ROOT / "assets"
SAVE_ROOT = Path.home() / "AppData" / "Local" / "StillwaterPrototype"
FOG_COLOR = color.rgb32(24, 31, 32)

RESULT_MESSAGES = {
    InteractionResult.FUSE_PICKED_UP: "Предохранитель убран в карман.",
    InteractionResult.FUSE_ALREADY_CARRIED: "Предохранитель уже у тебя.",
    InteractionResult.POWER_RESTORED: "Тумблер щёлкает. Где-то в глубине загорается свет.",
    InteractionResult.FUSE_REQUIRED: "В щитке не хватает предохранителя.",
    InteractionResult.NOTE_READ: "Записка прочитана.",
    InteractionResult.DOOR_OPENED: "Дверь со скрипом подалась.",
    InteractionResult.DOOR_CLOSED: "Дверь закрыта.",
    InteractionResult.DOOR_LOCKED: "Замок не реагирует. Сначала нужно дать питание.",
    InteractionResult.ALREADY_DONE: "Механизм уже работает.",
    InteractionResult.UNKNOWN_TARGET: "Здесь больше нечего сделать.",
}


class PlayerControllerEntity(Entity):
    """Прозрачная обёртка для создания PlayerController в сцене."""


class GameApplication(Entity):
    """Главный контроллер прототипа и владелец режимов взаимодействия."""

    def __init__(self) -> None:
        super().__init__(name="game_application", ignore_paused=True)
        self.mode = "exploration"
        self.debug_visible = False
        self._hovered_id: str | None = None
        self._look_note_open = False
        self._escape_was_down = False
        self.save_service = SaveService(SAVE_ROOT / "episode_01.json")
        self.session = self.save_service.load()
        self.scene = StationScene()
        self.player = PlayerController(spawn=(-0.2, 0, -2.7))
        self.player.camera_distance = 3.7
        self.player.camera_height = 2.05
        self.player.camera_pitch = 8.0
        self.render_pipeline = RetroPipeline(application.base, scale=0.52)
        self.ambient = AmbientSound(
            ASSET_ROOT / "audio" / "station_hum.wav",
            ASSET_ROOT / "audio" / "power_stinger.wav",
        )
        self._create_hud()
        self._restore_presentation()
        self._update_object_visibility()
        self._show_toast("Техстанция «Север». Исследуй помещение.", duration=4.0)

    def _create_hud(self) -> None:
        self.crosshair = Text(
            text="+",
            parent=camera.ui,
            position=(0, 0, -2),
            origin=(0, 0),
            scale=1.25,
            color=color.rgba32(214, 217, 207, 195),
            font="C:/Windows/Fonts/consola.ttf",
        )
        self.prompt = Text(
            text="",
            parent=camera.ui,
            position=(0, -0.34),
            origin=(0, 0),
            scale=0.76,
            color=color.rgba32(218, 218, 202),
            font="C:/Windows/Fonts/consola.ttf",
        )
        self.status = Text(
            text="STILLWATER   //   СМЕНА 02:17",
            parent=camera.ui,
            position=(-0.48, 0.455),
            origin=(-0.5, 0.5),
            scale=0.62,
            color=color.rgba32(161, 170, 160),
            font="C:/Windows/Fonts/consola.ttf",
        )
        self.hint = Text(
            text="WASD — ходьба   SHIFT — бег   E — действие   TAB — записи   ESC — пауза",
            parent=camera.ui,
            position=(0, -0.465),
            origin=(0, 0),
            scale=0.54,
            color=color.rgba32(136, 145, 139),
            font="C:/Windows/Fonts/consola.ttf",
        )
        self.toast = Text(
            text="",
            parent=camera.ui,
            position=(0, 0.34),
            origin=(0, 0),
            scale=0.68,
            color=color.rgba32(223, 213, 182),
            font="C:/Windows/Fonts/consola.ttf",
        )
        self.debug_text = Text(
            text="",
            parent=camera.ui,
            position=(0.48, 0.455),
            origin=(0.5, 0.5),
            scale=0.54,
            color=color.rgba32(158, 192, 169),
            font="C:/Windows/Fonts/consola.ttf",
            enabled=False,
        )
        self.modal = Entity(
            parent=camera.ui,
            model="quad",
            position=(0, 0, -3),
            scale=(0.92, 0.54),
            color=color.rgba32(13, 17, 18, 245),
            enabled=False,
            ignore_paused=True,
        )
        self.modal_title = Text(
            text="ЗАПИСНАЯ КНИЖКА",
            parent=self.modal,
            position=(-0.42, 0.20, -0.02),
            origin=(-0.5, 0.5),
            scale=0.8,
            color=color.rgba32(189, 164, 119),
            font="C:/Windows/Fonts/consola.ttf",
            ignore_paused=True,
        )
        self.modal_body = Text(
            text="",
            parent=self.modal,
            position=(-0.42, 0.10, -0.02),
            origin=(-0.5, 0.5),
            scale=0.69,
            line_height=1.45,
            color=color.rgba32(211, 210, 194),
            font="C:/Windows/Fonts/consola.ttf",
            ignore_paused=True,
        )
        self.modal_footer = Text(
            text="E / TAB / ESC — закрыть",
            parent=self.modal,
            position=(0.42, -0.22, -0.02),
            origin=(0.5, 0.5),
            scale=0.52,
            color=color.rgba32(140, 151, 145),
            font="C:/Windows/Fonts/consola.ttf",
            ignore_paused=True,
        )
        self.pause_overlay = Entity(
            parent=camera.ui,
            model="quad",
            position=(0, 0, -4),
            scale=(2, 1.2),
            color=color.rgba32(7, 9, 10, 215),
            enabled=False,
            ignore_paused=True,
        )
        self.pause_label = Text(
            text="ПАУЗА\n\nESC — вернуться\nF5 — профиль изображения",
            parent=self.pause_overlay,
            position=(0, 0, -0.03),
            origin=(0, 0),
            scale=0.82,
            line_height=1.4,
            color=color.rgba32(209, 211, 198),
            font="C:/Windows/Fonts/consola.ttf",
            ignore_paused=True,
        )

    def _restore_presentation(self) -> None:
        self.scene.apply_progress(
            self.session.fusebox_solved,
            self.session.door_open,
        )
        set_global_light_state(self.session.fusebox_solved)
        self._update_fog()

    def _update_fog(self) -> None:
        shader = WORLD_SHADER
        fog_tint = color.rgba32(24, 31, 32, 225)
        fog_end = 32.0 if self.session.fusebox_solved else 27.0
        shader.default_input["fog_color"] = fog_tint
        shader.default_input["fog_end"] = fog_end
        for entity in tuple(__import__("ursina").scene.entities):
            if entity.shader is shader:
                entity.set_shader_input("fog_color", fog_tint)
                entity.set_shader_input("fog_end", fog_end)

    def _update_object_visibility(self) -> None:
        for interactable in self.scene.interactables:
            if interactable.target_id == "fuse_pickup":
                interactable.instance.enabled = "fuse" in self.session.inventory
                # Installed fuse has left the inventory, but the pickup remains gone.
                if self.session.fusebox_solved:
                    interactable.instance.enabled = False

    def update(self) -> None:
        dt = min(time.dt, 0.05)
        self.render_pipeline.update(dt)
        if self.mode != "exploration":
            return

        self.player.tick(dt)
        self.ambient.update(tuple(self.player.position))
        self._refresh_interaction_target()
        if self.debug_visible:
            self.debug_text.text = (
                f"XYZ {self.player.x:05.1f} {self.player.y:04.1f} {self.player.z:05.1f}\n"
                f"MODE {self.mode.upper()}\n"
                f"TARGET {self._hovered_id or '-'}\n"
                f"POWER {'ON' if self.session.fusebox_solved else 'OFF'}\n"
                f"PROFILE {self.render_pipeline.profile.upper()}"
            )

    def _refresh_interaction_target(self) -> None:
        self._hovered_id = None
        self.prompt.text = ""
        camera_forward = camera.forward.normalized()
        player_eye = self.player.position + (0, 1.25, 0)
        candidates: list[tuple[float, Interactable]] = []

        for interactable in self.scene.interactables:
            if not interactable.instance.enabled:
                continue
            point = interactable.interaction_point
            delta = (
                point[0] - player_eye.x,
                point[1] - player_eye.y,
                point[2] - player_eye.z,
            )
            distance = (delta[0] ** 2 + delta[1] ** 2 + delta[2] ** 2) ** 0.5
            if distance > 2.25 or distance <= 0.001:
                continue
            direction = (delta[0] / distance, delta[1] / distance, delta[2] / distance)
            dot = (
                camera_forward.x * direction[0]
                + camera_forward.y * direction[1]
                + camera_forward.z * direction[2]
            )
            if dot < 0.52:
                continue
            obstruction = raycast(
                origin=player_eye,
                direction=direction,
                distance=max(0.0, distance - 0.22),
                ignore=[self.player, interactable.instance],
            )
            if obstruction.hit:
                continue
            candidates.append((distance - dot * 0.45, interactable))

        if candidates:
            _, target = min(candidates, key=lambda candidate: candidate[0])
            self._hovered_id = target.target_id
            self.prompt.text = f"[ E ]  {target.prompt}"

    def input(self, key: str) -> None:
        if key == "escape":
            if self.mode == "note":
                self._close_note()
            elif self.mode == "pause":
                self._close_pause()
            else:
                self._open_pause()
            return

        if self.mode == "note":
            if key in ("tab", "e", "enter"):
                self._close_note()
            return

        if self.mode == "pause":
            if key == "f5":
                self._cycle_render_profile()
            return

        if key == "e":
            self._interact()
        elif key == "tab":
            self._open_note()
        elif key == "f3":
            self.debug_visible = not self.debug_visible
            self.debug_text.enabled = self.debug_visible
        elif key == "f5":
            self._cycle_render_profile()
        elif key == "window minimized":
            self._open_pause()

    def _interact(self) -> None:
        target_id = self._hovered_id
        if target_id is None:
            return

        result = self.session.interact(target_id)
        self._update_object_visibility()
        self.scene.apply_progress(
            self.session.fusebox_solved,
            self.session.door_open,
        )
        if result == InteractionResult.POWER_RESTORED:
            set_global_light_state(True)
            self._update_fog()
            self.ambient.play_stinger()
            self.scene.set_light_flicker(enabled=True)
        if result != InteractionResult.UNKNOWN_TARGET:
            self.save_service.save(self.session)
        self._show_toast(RESULT_MESSAGES.get(result, ""), duration=3.4)
        if result == InteractionResult.NOTE_READ:
            self._open_note()

    def _open_note(self) -> None:
        self.mode = "note"
        self.modal_title.text = "ЗАПИСКА МЕХАНИКА"
        self.modal_body.text = (
            "\"Три рычага снова выбило.\n"
            "Северный щит пустой — поставь целый\n"
            "предохранитель, потом подними все\n"
            "тумблеры. Не стой у двери, когда\n"
            "станция проснётся.\"\n\n"
            "На обороте: СМЕНА 02:17"
        )
        self.modal.enabled = True
        self.pause_overlay.enabled = False
        application.pause()
        mouse.locked = False
        self._look_note_open = True

    def _close_note(self) -> None:
        self.modal.enabled = False
        application.resume()
        self.mode = "exploration"
        mouse.locked = True
        self._look_note_open = False

    def _open_pause(self) -> None:
        if self.mode in ("pause", "note"):
            return
        self.mode = "pause"
        self.pause_overlay.enabled = True
        application.pause()
        mouse.locked = False

    def _close_pause(self) -> None:
        self.pause_overlay.enabled = False
        self.mode = "exploration"
        application.resume()
        mouse.locked = True

    def _cycle_render_profile(self) -> None:
        profile = self.render_pipeline.cycle_profile()
        self._show_toast(f"Изображение: {profile.upper()}", duration=2.0)

    def _show_toast(self, message: str, duration: float = 2.4) -> None:
        self.toast.text = message
        self.toast.enabled = bool(message)
        self._toast_remaining = duration

    def shutdown(self) -> None:
        self.ambient.dispose()
        self.scene.dispose()


def main() -> None:
    """Создать окно Ursina и построить концепт эпизода."""
    # Content always receives the same world shader, while UI keeps its own fonts and materials.
    Entity.default_shader = WORLD_SHADER
    WORLD_SHADER.compile()
    from ursina import Ursina, scene

    scene.fog_color = FOG_COLOR
    application_instance = Ursina(
        title="Stillwater — Retro Horror Prototype",
        fullscreen=False,
        borderless=False,
        size=(1280, 720),
        vsync=True,
        editor_ui_enabled=False,
        development_mode=False,
        show_ursina_splash=False,
    )
    window.color = FOG_COLOR
    window.exit_button.enabled = False
    mouse.locked = True
    game = GameApplication()

    original_exit = application.quit

    def graceful_exit() -> None:
        game.shutdown()
        original_exit()

    application.quit = graceful_exit
    application_instance.run()


if __name__ == "__main__":
    main()
