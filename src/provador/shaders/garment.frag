#version 330
// Iluminacao provisoria (ambiente + difusa). A T10 troca por SH estimado na pele.
uniform vec4 base_color;
uniform vec3 light_dir;         // no espaco da camera, apontando PARA a luz
uniform sampler2D mask;         // segmentacao: R pele do corpo, G cabelo, B rosto, A pessoa
uniform vec4 viewport;          // x, y, w, h do video (letterbox) em pixels do framebuffer
uniform bool mirror;
uniform bool use_mask;

in vec3 v_view;
in vec3 v_normal;
in vec2 v_uv;
out vec4 color;

void main() {
    vec3 n = normalize(v_normal);
    vec3 to_eye = normalize(-v_view);
    // Lado de dentro da casca (visto pela gola, mangas, barra): quem o ocupa e o corpo da pessoa,
    // entao descarta e deixa o video (pescoco, bracos) aparecer. Independe do espelho.
    if (dot(n, to_eye) < 0.0) discard;
    float diff = max(dot(n, normalize(light_dir)), 0.0);
    vec3 rgb = base_color.rgb * (0.42 + 0.65 * diff);
    float alpha = base_color.a;
    if (use_mask) {                 // cabelo e queixo ficam sempre por cima da peca
        vec2 t = (gl_FragCoord.xy - viewport.xy) / viewport.zw;
        vec4 m = texture(mask, vec2(mirror ? 1.0 - t.x : t.x, 1.0 - t.y));
        alpha *= 1.0 - smoothstep(0.35, 0.75, max(m.g, m.b));
    }
    color = vec4(rgb, alpha);
}
