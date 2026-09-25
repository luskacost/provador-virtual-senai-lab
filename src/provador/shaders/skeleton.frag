#version 330
uniform vec3 rgb;
uniform bool round_point;
in float vis;
out vec4 color;

void main() {
    if (round_point) {
        vec2 c = gl_PointCoord * 2.0 - 1.0;
        if (dot(c, c) > 1.0) discard;
    }
    color = vec4(rgb, clamp(vis * 1.5, 0.0, 1.0) * 0.9);   // pontos pouco visiveis somem
}
