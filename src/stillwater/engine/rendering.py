"""Единый низкоразрешённый конвейер ретро-постобработки."""

from __future__ import annotations

from direct.filter.FilterManager import FilterManager
from panda3d.core import Camera as PandaCamera
from panda3d.core import CardMaker, Texture as PandaTexture
from ursina import Shader, application, camera, window


VHS_SHADER = Shader(
    name="stillwater_vhs",
    vertex="""
#version 130
uniform mat4 p3d_ModelViewProjectionMatrix;
in vec4 p3d_Vertex;
in vec2 p3d_MultiTexCoord0;
out vec2 uv;
void main() {
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    uv = p3d_MultiTexCoord0;
}
""",
    fragment="""
#version 130
uniform sampler2D tex;
uniform float clock_time;
uniform float grain_strength;
uniform float glitch_strength;
in vec2 uv;
out vec4 fragColor;

float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

void main() {
    vec2 sample_uv = uv;
    float band = step(0.996, hash(vec2(floor(uv.y * 54.0), floor(clock_time * 5.0))));
    sample_uv.x += (hash(vec2(floor(uv.y * 115.0), floor(clock_time * 9.0))) - 0.5)
                   * glitch_strength * band;

    float offset = 0.0012 * glitch_strength;
    vec3 image;
    image.r = texture(tex, sample_uv + vec2(offset, 0.0)).r;
    image.g = texture(tex, sample_uv).g;
    image.b = texture(tex, sample_uv - vec2(offset, 0.0)).b;

    float noise = hash(gl_FragCoord.xy + floor(clock_time * 30.0)) - 0.5;
    image += noise * grain_strength;

    float vignette = smoothstep(1.15, 0.2, length((uv - 0.5) * vec2(1.0, 0.82)));
    image *= mix(0.72, 1.0, vignette);
    fragColor = vec4(clamp(image, 0.0, 1.0), 1.0);
}
""",
    default_input={
        "clock_time": 0.0,
        "grain_strength": 0.018,
        "glitch_strength": 0.0,
    },
)


class RetroPipeline:
    """Render target пониженного разрешения и один VHS-финальный проход."""

    PROFILES = ("clean", "retro", "vhs")

    def __init__(self, base: object, scale: float = 0.5) -> None:
        self.base = base
        self.scale = scale
        self.profile_index = 1
        self._clock = 0.0
        self._manager: FilterManager | None = None
        self._buffer = None
        self._camera_quad = None
        self._final_quad = None
        self._render_texture: PandaTexture | None = None
        self._rebuild()
        self.set_profile("retro")

    @property
    def profile(self) -> str:
        return self.PROFILES[self.profile_index]

    def cycle_profile(self) -> str:
        self.profile_index = (self.profile_index + 1) % len(self.PROFILES)
        self._apply_profile()
        return self.profile

    def set_profile(self, profile: str) -> None:
        if profile not in self.PROFILES:
            raise ValueError(f"Неизвестный графический профиль: {profile}")
        self.profile_index = self.PROFILES.index(profile)
        self._apply_profile()

    def update(self, dt: float) -> None:
        self._clock += dt
        if self._final_quad:
            self._final_quad.setShaderInput("clock_time", self._clock)

    def _rebuild(self) -> None:
        """Построить low-res сцену и full-res композиционный проход."""
        if self._manager:
            self._manager.cleanup()
            self._manager = None
        if self._final_quad:
            self._final_quad.removeNode()
            self._final_quad = None
        if self._camera_quad:
            self._camera_quad.removeNode()
            self._camera_quad = None

        win_x = max(1, int(window.size.x * self.scale))
        win_y = max(1, int(window.size.y * self.scale))
        self._manager = FilterManager(
            application.base.win, application.base.cam, forcex=win_x, forcey=win_y
        )
        self._render_texture = PandaTexture("stillwater-low-resolution")
        self._final_quad = self._manager.renderSceneInto(
            depthtex=None,
            colortex=self._render_texture,
        )
        if self._final_quad is None:
            raise RuntimeError("Panda3D не удалось создать low-resolution render target")
        self._final_quad.setDepthTest(False)
        self._final_quad.setDepthWrite(False)
        self._final_quad.setTexture(self._render_texture)
        self._final_quad.setColor(1, 1, 1, 1)

    def _apply_profile(self) -> None:
        if not self._final_quad:
            return
        if self.profile == "clean":
            self._final_quad.setShaderOff()
        else:
            self._final_quad.setShader(VHS_SHADER._shader if VHS_SHADER.compiled else self._compile_shader())
            self._final_quad.setShaderInput(
                "grain_strength", 0.0 if self.profile == "clean" else 0.018
            )
            self._final_quad.setShaderInput(
                "glitch_strength", 0.035 if self.profile == "vhs" else 0.0
            )

    @staticmethod
    def _compile_shader():
        VHS_SHADER.compile()
        return VHS_SHADER._shader
