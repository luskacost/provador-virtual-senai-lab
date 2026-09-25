// Base de SH ate l=2, na ordem [1, y, z, x, xy, yz, 3z^2-1, xz, x^2-y^2]. Espelha lighting.sh_basis (numpy).
// Incluido por concatenacao no Python (garment_render.sh_glsl), depois de "uniform float sh[9];".
float sh_eval(vec3 n) {
    return sh[0] * 0.282095
         + sh[1] * 0.488603 * n.y
         + sh[2] * 0.488603 * n.z
         + sh[3] * 0.488603 * n.x
         + sh[4] * 1.092548 * n.x * n.y
         + sh[5] * 1.092548 * n.y * n.z
         + sh[6] * 0.315392 * (3.0 * n.z * n.z - 1.0)
         + sh[7] * 1.092548 * n.x * n.z
         + sh[8] * 0.546274 * (n.x * n.x - n.y * n.y);
}
