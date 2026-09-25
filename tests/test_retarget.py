import numpy as np
import pytest

from provador import garment, retarget
from provador import skeleton as sk
from provador.camera import perspective, project
from provador.retarget import L_EL, L_HIP, L_SH, L_WR, R_EL, R_HIP, R_SH, R_WR
from provador.template import build_tshirt, write_glb

W, H, HFOV = 1280, 720, 70.0
HIP_HALF = 0.10


def synthetic(depth=1.8, scale=1.0, yaw=0.0, twist=0.0, l_arm=0.0, r_arm=0.0, x_off=0.0):
    """Pessoa sintética = esqueleto padrão posado e colocado à frente da câmera.

    yaw gira o corpo todo; twist gira o peito em relação ao quadril; *_arm gira os braços em Z (graus).
    Devolve (px, world, vis, pontos no espaço da câmera, matriz do modelo).
    """
    rots = np.broadcast_to(np.eye(3), (sk.N_JOINTS, 3, 3)).copy()
    rots[sk.INDEX["hips"]] = sk.rotation_axis_angle((0, 1, 0), yaw)
    rots[sk.INDEX["spine"]] = sk.rotation_axis_angle((0, 1, 0), twist)
    rots[sk.INDEX["L_upper_arm"]] = sk.rotation_axis_angle((0, 0, 1), l_arm)
    rots[sk.INDEX["R_upper_arm"]] = sk.rotation_axis_angle((0, 0, 1), r_arm)
    world = sk.world_matrices(rots)
    model = sk.translation((x_off, -1.0 * scale, -depth)) @ np.diag([scale, scale, scale, 1.0])

    def cam(p):
        return (model @ np.append(p, 1.0))[:3]

    pts = np.zeros((33, 3))
    hips = world[sk.INDEX["hips"]]
    pts[L_HIP] = cam((hips @ [HIP_HALF, 0, 0, 1])[:3])
    pts[R_HIP] = cam((hips @ [-HIP_HALF, 0, 0, 1])[:3])
    for lm, name in ((L_SH, "L_upper_arm"), (R_SH, "R_upper_arm"), (L_EL, "L_forearm"), (R_EL, "R_forearm"),
                     (L_WR, "L_hand"), (R_WR, "R_hand")):
        pts[lm] = cam(world[sk.INDEX[name], :3, 3])
    used = [L_SH, R_SH, L_EL, R_EL, L_WR, R_WR, L_HIP, R_HIP]
    for i in range(33):                                  # demais landmarks: no quadril (não são usados)
        if i not in used:
            pts[i] = (pts[L_HIP] + pts[R_HIP]) / 2
    px = project(pts, perspective(HFOV, W / H), W, H)
    hip_mid = (pts[L_HIP] + pts[R_HIP]) / 2
    mp_world = (pts - hip_mid) * np.array([1.0, -1.0, -1.0])
    return px, mp_world, np.ones(33), pts, model


def run(**kw):
    px, world, vis, pts, model = synthetic(**kw)
    return retarget.retarget(px, world, vis, (W, H), HFOV), px, pts, model


@pytest.mark.parametrize("depth", [0.9, 1.6, 2.8])
def test_profundidade_estimada(depth):
    res, *_ = run(depth=depth)
    assert res.depth == pytest.approx(depth, rel=0.02)


def test_articulacoes_caem_sobre_os_landmarks():
    res, px, *_ = run(depth=1.5, yaw=20, l_arm=50, r_arm=-30, x_off=0.2)
    assert retarget.joint_error_px(res, px, HFOV, (W, H)) < 0.5


@pytest.mark.parametrize("scale", [0.85, 1.0, 1.2])
def test_escala_pelos_ombros_e_tronco(scale):
    res, *_ = run(scale=scale)
    assert res.scale[0] == pytest.approx(scale, rel=0.02)
    assert res.scale[1] == pytest.approx(scale, rel=0.02)


@pytest.mark.parametrize(("yaw", "twist"), [(0, 0), (25, 0), (-30, 0), (10, 30), (0, -30)])
def test_giro_e_torcao(yaw, twist):
    res, *_ = run(yaw=yaw, twist=twist)
    assert res.yaw_deg == pytest.approx(yaw + twist, abs=1.0)
    assert res.twist_deg == pytest.approx(twist, abs=1.0)


def test_pose_t_reproduz_a_peca_rigida(tmp_path):
    """De frente e em T, a peça deformada é só o template escalado e transladado."""
    g = garment.load_glb(write_glb(build_tshirt(), tmp_path / "t.glb"))
    res, _, _, model = run(depth=1.7, scale=1.1)
    got = garment.skin(g, res.skin)
    expected = (np.c_[g.positions, np.ones(len(g.positions))] @ model.T)[:, :3]
    assert np.abs(got - expected).max() < 0.005                # < 5 mm


def test_braco_levantado_leva_a_manga_junto(tmp_path):
    g = garment.load_glb(write_glb(build_tshirt(), tmp_path / "t.glb"))
    res, _, pts, _ = run(l_arm=60)
    got = garment.skin(g, res.skin)
    sleeve = (g.positions[:, 0] > 0.28) & (g.positions[:, 1] > 1.36)
    sleeve_dir = got[sleeve].mean(0) - pts[L_SH]
    arm_dir = pts[L_EL] - pts[L_SH]
    cos = sleeve_dir @ arm_dir / np.linalg.norm(sleeve_dir) / np.linalg.norm(arm_dir)
    assert cos > 0.97


def test_quadril_fora_do_quadro_ainda_estima_profundidade():
    px, world, vis, *_ = synthetic(depth=1.2)
    vis[[L_HIP, R_HIP]] = 0.1
    res = retarget.retarget(px, world, vis, (W, H), HFOV)
    assert res.depth == pytest.approx(1.2, rel=0.05)


def test_rotation_between():
    for a, b in [((1, 0, 0), (0, 1, 0)), ((1, 0, 0), (-1, 0, 0)), ((0.3, 0.2, 0.9), (0.3, 0.2, 0.9))]:
        r = retarget.rotation_between(np.array(a, float), np.array(b, float))
        assert np.allclose(r @ r.T, np.eye(3), atol=1e-9)
        assert np.allclose(r @ (np.array(a) / np.linalg.norm(a)), np.array(b) / np.linalg.norm(b), atol=1e-9)
