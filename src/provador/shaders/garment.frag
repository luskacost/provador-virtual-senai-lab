#version 330
// Peca: difuso por SH estimado na pele (lighting.py) + brilho especular suave + sheen de tecido + grao.
// Contas em espaco linear; a saida volta para sRGB. Ver docs/luz.md.
uniform vec4 base_color;        // sRGB
uniform float sh[9];            // forma da irradiancia (media ~1); direcao dominante = (sh[3], sh[1], sh[2])
uniform float exposure;
uniform vec3 tint;              // balanco de branco
uniform float grain;            // amplitude do grao (0 = sem)
uniform float grain_seed;
uniform sampler2D mask;         // segmentacao: R pele do corpo, G cabelo, B rosto, A pessoa
uniform vec4 viewport;          // x, y, w, h do video (letterbox) em pixels do framebuffer
uniform bool mirror;
uniform bool use_mask;

in vec3 v_view;
in vec3 v_normal;
in vec2 v_uv;
out vec4 color;


// @SH_EVAL@

float hash(vec2 p) {
    return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
}

void main() {
    vec3 n = normalize(v_normal);
    vec3 to_eye = normalize(-v_view);
    // Lado de dentro da casca (visto pela gola, mangas, barra): quem o ocupa e o corpo da pessoa,
    // entao descarta e deixa o video (pescoco, bracos) aparecer. Independe do espelho.
    if (dot(n, to_eye) < 0.0) discard;

    vec3 albedo = pow(base_color.rgb, vec3(2.2));
    float irradiance = max(sh_eval(n), 0.06) * exposure;
    vec3 rgb = albedo * irradiance * 0.85 * tint;

    // Brilho especular largo (tecido) na direcao dominante da luz, mais o sheen de borda
    vec3 ld = vec3(sh[3], sh[1], sh[2]);
    float strength = length(ld) * 0.488603 / max(sh[0] * 0.282095, 1e-4);      // 0 = difusa
    ld = length(ld) > 1e-5 ? normalize(ld) : vec3(0.0, 0.0, 1.0);
    vec3 h = normalize(ld + to_eye);
    float spec = pow(max(dot(n, h), 0.0), 18.0) * 0.06 * clamp(strength * 2.0, 0.0, 1.0);
    float sheen = pow(1.0 - max(dot(n, to_eye), 0.0), 3.0) * 0.07;
    rgb += (spec + sheen * irradiance) * exposure * tint;

    vec3 srgb = pow(clamp(rgb, 0.0, 1.0), vec3(1.0 / 2.2));
    srgb += (hash(gl_FragCoord.xy + grain_seed) - 0.5) * grain;                  // grao da webcam

    float alpha = base_color.a;
    if (use_mask) {                 // cabelo e queixo ficam sempre por cima da peca
        vec2 t = (gl_FragCoord.xy - viewport.xy) / viewport.zw;
        vec4 m = texture(mask, vec2(mirror ? 1.0 - t.x : t.x, 1.0 - t.y));
        alpha *= 1.0 - smoothstep(0.35, 0.75, max(m.g, m.b));
    }
    color = vec4(srgb, alpha);
}
