"""Простой однопроходный low-poly diffuse shader с линейной дымкой."""

from __future__ import annotations

from ursina import Shader, Vec3, Vec4, camera, color


WORLD_SHADER = Shader(
    name="stillwater_world_lit_fog",
    language=Shader.GLSL,
    vertex="""
#version 130
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelMatrix;
uniform mat3 p3d_NormalMatrix;
in vec4 p3d_Vertex;
in vec3 p3d_Normal;
in vec2 p3d_MultiTexCoord0;
in vec4 p3d_Color;
out vec3 world_position;
out vec3 world_normal;
out vec2 uv;
out vec4 vertex_color;
void main() {
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    world_position = (p3d_ModelMatrix * p3d_Vertex).xyz;
    world_normal = normalize(p3d_NormalMatrix * p3d_Normal);
    uv = p3d_MultiTexCoord0;
    vertex_color = p3d_Color;
}
""",
    fragment="""
#version 130
uniform sampler2D p3d_Texture0;
uniform vec4 p3d_ColorScale;
uniform vec3 camera_world_position;
uniform vec3 ambient_color;
uniform vec4 lamp0_position_range;
uniform vec4 lamp0_color_enabled;
uniform vec4 lamp1_position_range;
uniform vec4 lamp1_color_enabled;
uniform vec4 lamp2_position_range;
uniform vec4 lamp2_color_enabled;
uniform vec4 fog_color;
uniform float fog_start;
uniform float fog_end;
in vec3 world_position;
in vec3 world_normal;
in vec2 uv;
in vec4 vertex_color;
out vec4 fragColor;

vec3 shade_lamp(vec4 position_range, vec4 color_enabled, vec3 normal) {
    vec3 to_light = position_range.xyz - world_position;
    float distance_to_light = length(to_light);
    float radius = max(position_range.w, 0.001);
    float falloff = max(0.0, 1.0 - distance_to_light / radius);
    falloff *= falloff;
    float diffuse = 0.28 + 0.72 * max(dot(normal, normalize(to_light)), 0.0);
    return color_enabled.rgb * color_enabled.a * falloff * diffuse;
}

void main() {
    vec4 base = texture(p3d_Texture0, uv) * p3d_ColorScale * vertex_color;
    vec3 normal = normalize(world_normal);
    vec3 illumination = ambient_color;
    illumination += shade_lamp(lamp0_position_range, lamp0_color_enabled, normal);
    illumination += shade_lamp(lamp1_position_range, lamp1_color_enabled, normal);
    illumination += shade_lamp(lamp2_position_range, lamp2_color_enabled, normal);
    vec3 lit_color = base.rgb * clamp(illumination, vec3(0.12), vec3(1.4));
    float distance_to_camera = length(world_position - camera_world_position);
    float fog_amount = clamp((distance_to_camera - fog_start) / max(0.001, fog_end - fog_start), 0.0, 1.0);
    lit_color = mix(lit_color, fog_color.rgb, fog_amount * fog_color.a);
    fragColor = vec4(lit_color, base.a);
}
""",
    default_input={
        "camera_world_position": lambda: Vec3(camera.world_position),
        "ambient_color": Vec3(0.16, 0.17, 0.16),
        "lamp0_position_range": Vec4(-1.5, 3.0, -3.8, 6.4),
        "lamp0_color_enabled": Vec4(0.0, 0.0, 0.0, 0.0),
        "lamp1_position_range": Vec4(0.0, 3.0, 3.7, 6.4),
        "lamp1_color_enabled": Vec4(0.0, 0.0, 0.0, 0.0),
        "lamp2_position_range": Vec4(0.0, 3.0, 11.1, 6.4),
        "lamp2_color_enabled": Vec4(0.0, 0.0, 0.0, 0.0),
        "fog_color": color.rgba32(24, 31, 32, 225),
        "fog_start": 11.0,
        "fog_end": 34.0,
    },
)


def set_global_light_state(power_on: bool) -> None:
    """Обновить три лампы для уже созданных объектов сцены."""
    for index, x_position in enumerate((-1.5, 0.0, 1.5)):
        WORLD_SHADER.default_input[f"lamp{index}_position_range"] = Vec4(
            x_position, 3.0, (-3.8, 3.7, 11.1)[index], 6.8
        )
        strength = 1.0 if power_on else 0.0
        warmth = 1.0 if index != 1 else 0.67
        WORLD_SHADER.default_input[f"lamp{index}_color_enabled"] = Vec4(
            0.66 * warmth * strength,
            0.46 * warmth * strength,
            0.27 * warmth * strength,
            1.0,
        )
