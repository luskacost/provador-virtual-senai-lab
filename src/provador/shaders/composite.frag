#version 330
// Composicao do passo 1-2 da T7b: cenario atras + pessoa recortada pela mascara da segmentacao.
// A mascara e 256x256 e cobre o quadro inteiro; a borda e refinada em resolucao total por
// "joint bilateral upsampling": cada pixel do video pondera os texels vizinhos da mascara pela semelhanca de cor
// entre ele e o quadro reduzido (guia), entao a borda da pessoa segue a borda REAL da imagem.
uniform sampler2D video;        // 0: quadro da webcam (resolucao total)
uniform sampler2D mask;         // 1: R pele do corpo, G cabelo, B rosto, A pessoa
uniform sampler2D background;   // 3: cenario
uniform sampler2D guide;        // 4: quadro reduzido 256x256 (mesmo do modelo)
uniform vec2 bg_scale;          // "cobrir": escala do uv da tela para o uv do cenario
uniform vec3 person_gain;       // casamento de cor da pessoa com o cenario (linear)
uniform float range_sigma;      // sigma de cor do refinamento
uniform float edge_lo;          // corte da mascara: abaixo disso e fundo (erosao leve do halo)
uniform float edge_hi;

in vec2 uv;                     // uv do video (espelhado se o modo espelho estiver ligado)
in vec2 screen_uv;              // uv da tela, sem espelho (o cenario nao e espelhado: texto legivel)
out vec4 color;

vec3 apply_gain(vec3 srgb, vec3 g) {
    return pow(pow(srgb, vec3(2.2)) * g, vec3(1.0 / 2.2));
}

float person_alpha(vec2 p, vec3 c) {
    ivec2 size = textureSize(mask, 0);
    vec2 pos = p * vec2(size);
    ivec2 base = ivec2(floor(pos));
    float acc = 0.0, wsum = 0.0;
    for (int dy = -1; dy <= 1; dy++) {
        for (int dx = -1; dx <= 1; dx++) {
            ivec2 t = clamp(base + ivec2(dx, dy), ivec2(0), size - 1);
            vec2 d = pos - (vec2(t) + 0.5);
            float ws = exp(-dot(d, d) / (2.0 * 0.8 * 0.8));
            vec3 dc = c - texelFetch(guide, t, 0).rgb;
            float wr = exp(-dot(dc, dc) / (2.0 * range_sigma * range_sigma));
            float w = ws * wr + 1e-5;
            acc += w * texelFetch(mask, t, 0).a;
            wsum += w;
        }
    }
    return acc / wsum;
}

void main() {
    vec3 c = texture(video, uv).rgb;
    float a = smoothstep(edge_lo, edge_hi, person_alpha(uv, c));
    vec3 person = apply_gain(c, person_gain);
    vec3 bg = texture(background, (screen_uv - 0.5) * bg_scale + 0.5).rgb;
    color = vec4(mix(bg, person, a), 1.0);
}
