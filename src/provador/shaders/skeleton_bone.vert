#version 330
// Osso = quad instanciado com espessura em pixels (o core profile so garante linhas de 1 px).
in vec3 a;                // x, y normalizados na imagem (0..1, y para baixo), visibilidade
in vec3 b;
uniform vec2 viewport_px; // tamanho em pixels da area do video (com letterbox)
uniform bool mirror;
uniform float thickness;  // em pixels
out float vis;

vec2 to_px(vec2 p) {
    if (mirror) p.x = 1.0 - p.x;
    return p * viewport_px;
}

void main() {
    vec2 pa = to_px(a.xy), pb = to_px(b.xy);
    vec2 d = pb - pa;
    float len = length(d);
    vec2 dir = len > 1e-4 ? d / len : vec2(1.0, 0.0);
    vec2 n = vec2(-dir.y, dir.x) * thickness * 0.5;
    // 4 vertices: (A-n) (A+n) (B-n) (B+n)
    vec2 base = (gl_VertexID >> 1) == 0 ? pa : pb;
    vec2 p = base + ((gl_VertexID & 1) == 0 ? -n : n);
    gl_Position = vec4(p.x / viewport_px.x * 2.0 - 1.0, 1.0 - p.y / viewport_px.y * 2.0, 0.0, 1.0);
    vis = min(a.z, b.z);
}
