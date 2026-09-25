#version 330
// Repinta o pixel do video onde o braco (capsula) esta a frente da peca, recortado pela mascara.
uniform sampler2D video;
uniform sampler2D mask;      // R pele do corpo, G cabelo, B rosto, A pessoa
uniform vec4 viewport;       // x, y, w, h do video (letterbox) em pixels do framebuffer
uniform bool mirror;
uniform bool debug;
in vec3 v_view;
in vec3 v_normal;
out vec4 color;

void main() {
    vec2 t = (gl_FragCoord.xy - viewport.xy) / viewport.zw;
    vec2 uv = vec2(mirror ? 1.0 - t.x : t.x, 1.0 - t.y);
    vec4 m = texture(mask, uv);
    // Miolo da capsula (onde a normal encara a camera): basta ser pessoa (manga comprida, luva...).
    // Borda da capsula: so pele, para o contorno vir da mascara e nao da geometria aproximada.
    float facing = abs(dot(normalize(v_normal), normalize(-v_view)));
    float core = smoothstep(0.45, 0.7, facing);
    float skin = smoothstep(0.3, 0.7, m.r);
    float a = max(skin, smoothstep(0.4, 0.8, m.a) * core);
    vec3 rgb = texture(video, uv).rgb;
    if (debug) {
        rgb = mix(rgb, vec3(1.0, 0.2, 0.6), 0.45);
        a = max(a, 0.25);
    }
    color = vec4(rgb, a);
}
