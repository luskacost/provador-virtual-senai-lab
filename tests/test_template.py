import numpy as np
import pytest

from provador import garment
from provador import skeleton as sk
from provador.template import build_tshirt, write_glb


@pytest.fixture(scope="module")
def shirt(tmp_path_factory):
    path = write_glb(build_tshirt(), tmp_path_factory.mktemp("glb") / "tshirt.glb")
    return garment.load_glb(path)


def _pose(**deg_z):
    """Rotações locais em torno de Z (graus) por nome de osso."""
    rots = np.broadcast_to(np.eye(3), (sk.N_JOINTS, 3, 3)).copy()
    for name, deg in deg_z.items():
        rots[sk.INDEX[name]] = sk.rotation_axis_angle((0, 0, 1), deg)
    return sk.skin_matrices(sk.world_matrices(rots))


def test_esqueleto_topologico_e_repouso_e_identidade():
    assert sk.N_JOINTS == 13          # 5 do tronco/cabeça + 4 por braço
    assert (sk.PARENT < np.arange(sk.N_JOINTS)).all()
    assert np.allclose(sk.skin_matrices(sk.world_matrices()), np.eye(4), atol=1e-12)
    assert np.allclose(sk.world_matrices()[:, :3, 3], sk.REST_WORLD)


def test_glb_carrega_com_atributos_consistentes(shirt):
    v = len(shirt.positions)
    assert v > 100 and shirt.indices.max() < v and len(shirt.indices) % 3 == 0
    assert shirt.normals.shape == shirt.uvs.shape[:1] + (3,) == (v, 3)
    assert shirt.joints.max() < sk.N_JOINTS
    assert np.allclose(shirt.weights.sum(axis=1), 1.0, atol=1e-5)
    assert (shirt.weights >= 0).all()
    assert np.allclose(np.linalg.norm(shirt.normals, axis=1), 1.0, atol=1e-4)


def test_normais_apontam_para_fora(shirt):
    radial = shirt.positions.copy()
    radial[:, 1] = 0                                     # do eixo vertical para o vértice (torso)
    torso = np.abs(shirt.positions[:, 0]) < 0.14
    torso &= shirt.positions[:, 1] < 1.45                # exclui a gola (normais quase horizontais)
    dots = (shirt.normals[torso] * radial[torso]).sum(axis=1)
    assert (dots > 0).mean() > 0.95


def test_uv_atlas_frente_e_costas(shirt):
    assert shirt.uvs.min() >= 0.0 and shirt.uvs.max() <= 1.0
    front = shirt.normals[:, 2] > 0.3
    back = shirt.normals[:, 2] < -0.3
    assert (shirt.uvs[front, 0] <= 0.5 + 1e-6).all()
    assert (shirt.uvs[back, 0] >= 0.5 - 1e-6).all()


def test_pose_de_repouso_nao_deforma(shirt):
    posed = garment.skin(shirt, sk.skin_matrices(sk.world_matrices()))
    assert np.abs(posed - shirt.positions).max() < 1e-5


def test_girar_o_braco_esquerdo_deforma_so_a_manga_esquerda(shirt):
    posed = garment.skin(shirt, _pose(L_upper_arm=60))
    moved = np.linalg.norm(posed - shirt.positions, axis=1)
    x, y = shirt.positions[:, 0], shirt.positions[:, 1]
    left_sleeve = (x > 0.25) & (y > 1.36)
    assert moved[left_sleeve].mean() > 0.05              # a manga sobe
    assert moved[x < -0.05].max() < 1e-6                 # lado direito intacto
    assert moved[y < 1.25].max() < 1e-6                  # da cintura para baixo intacto


def test_girar_a_coluna_move_o_peito_e_nao_o_quadril(shirt):
    rots = np.broadcast_to(np.eye(3), (sk.N_JOINTS, 3, 3)).copy()
    rots[sk.INDEX["spine"]] = sk.rotation_axis_angle((0, 1, 0), 30)
    posed = garment.skin(shirt, sk.skin_matrices(sk.world_matrices(rots)))
    moved = np.linalg.norm(posed - shirt.positions, axis=1)
    assert moved[shirt.positions[:, 1] > 1.35].mean() > 0.02
    assert moved[shirt.positions[:, 1] < 1.0].max() < 1e-6


def test_deslocar_a_raiz_move_tudo_igual(shirt):
    posed = garment.skin(shirt, sk.skin_matrices(sk.world_matrices(root_offset=(0.1, 0.0, -0.2))))
    assert np.allclose(posed - shirt.positions, [0.1, 0.0, -0.2], atol=1e-5)


def test_load_glb_rejeita_glb_sem_skin(tmp_path):
    from pygltflib import GLTF2, Mesh, Node, Primitive, Scene

    path = tmp_path / "sem_skin.glb"
    GLTF2(scene=0, scenes=[Scene(nodes=[0])], nodes=[Node(mesh=0)],
          meshes=[Mesh(primitives=[Primitive()])]).save_binary(str(path))
    with pytest.raises(ValueError, match="sem skin"):
        garment.load_glb(path)
