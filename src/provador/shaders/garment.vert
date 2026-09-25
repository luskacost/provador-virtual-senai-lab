#version 330
// Peca rigada: skinning linear (LBS) na GPU. N_JOINTS e injetado pelo Python (#define).
in vec3 in_pos;
in vec3 in_normal;
in vec2 in_uv;
in uvec4 in_joints;
in vec4 in_weights;

uniform mat4 bones[N_JOINTS];   // matrizes de skinning (mundo do osso x inversa do bind)
uniform mat4 model;             // espaco da peca -> espaco da camera
uniform mat4 proj;              // projecao alinhada a webcam
uniform bool mirror;

out vec3 v_view;                // posicao no espaco da camera (tambem capturada no teste)
out vec3 v_normal;
out vec2 v_uv;

void main() {
    mat4 skin = in_weights.x * bones[in_joints.x]
              + in_weights.y * bones[in_joints.y]
              + in_weights.z * bones[in_joints.z]
              + in_weights.w * bones[in_joints.w];
    vec4 p = model * (skin * vec4(in_pos, 1.0));
    v_view = p.xyz;
    v_normal = mat3(model) * (mat3(skin) * in_normal);   // sem escala nao uniforme: nao precisa da inversa
    v_uv = in_uv;
    gl_Position = proj * p;
    if (mirror) gl_Position.x = -gl_Position.x;
}
