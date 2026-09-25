#version 330
// Capsulas dos bracos (cilindros/esferas unitarios instanciados), no espaco da camera.
in vec3 in_pos;
in vec3 in_normal;
in mat4 inst;
uniform mat4 proj;
uniform bool mirror;
out vec3 v_view;
out vec3 v_normal;

void main() {
    vec4 p = inst * vec4(in_pos, 1.0);
    v_view = p.xyz;
    v_normal = mat3(inst) * in_normal;
    gl_Position = proj * p;
    if (mirror) gl_Position.x = -gl_Position.x;
}
