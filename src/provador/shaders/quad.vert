#version 330
// Quad em tela cheia (ou retangulo) sem VBO: 4 vertices em triangle strip via gl_VertexID.
uniform vec4 rect;      // x0, y0, x1, y1 em NDC (y para cima)
uniform bool mirror;    // espelha horizontalmente (visao de espelho)
out vec2 uv;
out vec2 screen_uv;     // uv sem espelho (usado pela composicao do cenario)

void main() {
    vec2 t = vec2(gl_VertexID & 1, gl_VertexID >> 1);   // (0,0) (1,0) (0,1) (1,1); t.y=1 e o topo
    gl_Position = vec4(mix(rect.xy, rect.zw, t), 0.0, 1.0);
    screen_uv = vec2(t.x, 1.0 - t.y);
    uv = vec2(mirror ? 1.0 - t.x : t.x, 1.0 - t.y);       // linha 0 da imagem = topo
}
