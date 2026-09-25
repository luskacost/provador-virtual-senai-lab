import numpy as np
import pytest

from provador import camera, garment
from provador import skeleton as sk
from provador.template import build_tshirt, write_glb


def test_projecao_centro_e_bordas():
    w, h, hfov = 1280, 720, 70.0
    proj = camera.perspective(hfov, w / h)
    edge_x = 2.0 * np.tan(np.radians(hfov / 2))              # na borda direita a 2 m
    px = camera.project(np.array([[0, 0, -2.0], [edge_x, 0, -2.0]]), proj, w, h)
    assert np.allclose(px[0], [640, 360], atol=1e-6)
    assert np.allclose(px[1], [1280, 360], atol=1e-6)


def test_projecao_bate_com_pinhole_e_unproject():
    w, h, hfov = 1280, 720, 65.0
    f = camera.focal_px(hfov, w)
    pts = np.array([[0.3, 0.2, -1.5], [-0.4, -0.1, -2.2]])
    px = camera.project(pts, camera.perspective(hfov, w / h), w, h)
    expected_x = w / 2 + f * pts[:, 0] / -pts[:, 2]
    expected_y = h / 2 - f * pts[:, 1] / -pts[:, 2]         # y da imagem cresce para baixo
    assert np.allclose(px[:, 0], expected_x) and np.allclose(px[:, 1], expected_y)
    back = camera.unproject(px, -pts[:, 2], hfov, w, h)
    assert np.allclose(back, pts)


def test_gl_bytes_e_column_major():
    m = np.arange(16, dtype=float).reshape(4, 4)
    got = np.frombuffer(camera.gl_bytes(m), np.float32).reshape(4, 4)
    assert np.allclose(got, m.T)


@pytest.fixture(scope="module")
def gl():
    moderngl = pytest.importorskip("moderngl")
    try:
        ctx = moderngl.create_standalone_context(require=330)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"sem contexto OpenGL: {exc}")
    yield ctx
    ctx.release()


def test_lbs_na_gpu_igual_a_referencia_numpy(gl, tmp_path):
    """O vertex shader do app, capturado por transform feedback, tem de bater com garment.skin()."""
    from provador.garment_render import vertex_source

    g = garment.load_glb(write_glb(build_tshirt(), tmp_path / "t.glb"))
    rots = np.broadcast_to(np.eye(3), (sk.N_JOINTS, 3, 3)).copy()
    rots[sk.INDEX["L_upper_arm"]] = sk.rotation_axis_angle((0, 0, 1), 55)
    rots[sk.INDEX["R_upper_arm"]] = sk.rotation_axis_angle((1, 0, 1), -40)
    rots[sk.INDEX["spine"]] = sk.rotation_axis_angle((0, 1, 0), 25)
    skin = sk.skin_matrices(sk.world_matrices(rots, root_offset=(0.05, -0.02, 0.1)))
    model = sk.translation((0.1, -1.25, -1.8))

    prog = gl.program(vertex_shader=vertex_source(), varyings=["v_view"])
    prog["bones"].write(camera.gl_bytes(skin))
    prog["model"].write(camera.gl_bytes(model))
    prog["proj"].write(camera.gl_bytes(np.eye(4)))
    layout = [(g.positions, "3f", "in_pos"), (g.normals, "3f", "in_normal"), (g.joints.astype("u4"), "4u4",
              "in_joints"), (g.weights, "4f", "in_weights")]
    content = [(gl.buffer(np.ascontiguousarray(a, a.dtype if a.dtype == np.uint32 else "f4").tobytes()), f, n)
               for a, f, n in layout if n in prog]
    vao = gl.vertex_array(prog, content)
    out = gl.buffer(reserve=len(g.positions) * 12)
    vao.transform(out, 0, vertices=len(g.positions))   # 0 = GL_POINTS
    gpu = np.frombuffer(out.read(), np.float32).reshape(-1, 3)

    ref = garment.skin(g, skin) + model[:3, 3]
    assert np.abs(gpu - ref).max() < 1e-4

