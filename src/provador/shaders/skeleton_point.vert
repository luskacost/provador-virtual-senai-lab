#version 330
in vec3 p;                // x, y normalizados na imagem, visibilidade
uniform bool mirror;
uniform float point_size;
out float vis;

void main() {
    float x = mirror ? 1.0 - p.x : p.x;
    gl_Position = vec4(x * 2.0 - 1.0, 1.0 - p.y * 2.0, 0.0, 1.0);
    gl_PointSize = point_size;
    vis = p.z;
}
