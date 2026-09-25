# Luz da peça (T10)

A peça é iluminada com uma estimativa da luz do ambiente feita **a partir da própria pessoa**, a 10 Hz
(~3 ms por estimativa). Código: `src/provador/lighting.py` (estimativa) e `shaders/garment.frag` + `sh.glsl` (uso).

## Como a luz é estimada

1. **Amostras de pele com normal conhecida.** A máscara da segmentação (T7) diz quais pixels são pele.
   - Rosto = esfera (centro e raio pelos landmarks de olhos e orelhas); cabelo fica de fora.
   - Braços = cilindros ao longo de ombro→cotovelo→pulso; a normal vem da posição perpendicular ao eixo.
2. **Forma (SH ordem 2).** Ajuste por mínimos quadrados da luminância linear da pele em 9 harmônicos esféricos
   (`[1, y, z, x, xy, yz, 3z²-1, xz, x²-y²]`), regularizado em direção a uma luz padrão. Só o hemisfério voltado
   à câmera é observado, então os termos de ordem 2 ficam contidos e os de ordem 0–1 (ambiente e direção) mandam.
3. **Exposição.** Luminância média do quadro (não da pele, para não depender do tom de pele), elevada a 0,6 e
   limitada a 0,45–1,8; a câmera já compensa parte da variação.
4. **Balanço de branco.** Cromaticidade da pele contra uma pele nominal, com força `--wb-strength` (padrão 0,35).
   É uma **heurística**: o tom de pele varia entre pessoas. `--wb-strength 0` desliga.
5. **Suavização temporal** (EMA, ~0,5 s) para a peça não cintilar.

Sem amostras suficientes (< 150 pixels), a luz anterior é mantida.

## Como a luz é usada

Difuso por SH (`albedo × E(n) × exposição × tinta`), brilho especular largo na direção dominante da luz, *sheen*
de borda (tecido) e grão leve (`--grain`, padrão 0,02) para combinar com o ruído da webcam. Contas em espaço
linear; a saída volta para sRGB. A tecla **L** alterna entre a luz adaptativa e uma luz fixa.

Convenção da direção no HUD: espaço da câmera, imagem **crua** (sem espelho): x > 0 = lado esquerdo da pessoa,
y > 0 = para cima, z > 0 = vindo da câmera.

## Limitações conhecidas

- Sem sombras projetadas (do rosto ou dos braços sobre a peça) e sem oclusão ambiente.
- Rosto e braços são só aproximados por esfera e cilindros; cabelo cobrindo a testa reduz as amostras altas.
- Com luz muito lateral e pele escura, a estimativa da direção é mais ruidosa.
- O grão é fixo, não é medido da câmera.
