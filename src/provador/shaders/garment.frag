#version 330
// Iluminacao provisoria (ambiente + difusa). A T10 troca por SH estimado na pele.
uniform vec4 base_color;
uniform vec3 light_dir;         // no espaco da camera, apontando PARA a luz

in vec3 v_view;
in vec3 v_normal;
in vec2 v_uv;
out vec4 color;

void main() {
    vec3 n = normalize(v_normal);
    vec3 to_eye = normalize(-v_view);
    float inside = 0.0;
    if (dot(n, to_eye) < 0.0) {     // lado de dentro da casca (gola, barra): independe do espelho
        n = -n;
        inside = 1.0;
    }
    float diff = max(dot(n, normalize(light_dir)), 0.0);
    vec3 rgb = base_color.rgb * (0.42 + 0.65 * diff);
    rgb *= mix(1.0, 0.55, inside);
    color = vec4(rgb, base_color.a);
}
