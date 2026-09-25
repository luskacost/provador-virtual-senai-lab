"""Camiseta procedural rigada no esqueleto padrão (o "template" das peças) e exportação para GLB.

A malha é dividida em meia-frente e meia-costas, com vértices duplicados na costura lateral, para que
o UV seja um atlas planar simples: frente na metade esquerda da textura, costas na direita.
Isso é o que a T9 usa para projetar as fotos reais sobre o template.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from pygltflib import (
    ARRAY_BUFFER,
    ELEMENT_ARRAY_BUFFER,
    FLOAT,
    GLTF2,
    UNSIGNED_INT,
    UNSIGNED_SHORT,
    Accessor,
    Asset,
    Attributes,
    Buffer,
    BufferView,
    Material,
    Mesh,
    Node,
    PbrMetallicRoughness,
    Primitive,
    Scene,
    Skin,
)

from . import skeleton as sk

# Torso: (y, meia-largura em x, meia-profundidade em z). Do barrado até a gola.
TORSO_RINGS = [
    (0.950, 0.205, 0.115),
    (1.050, 0.192, 0.106),
    (1.200, 0.205, 0.115),
    (1.320, 0.215, 0.120),
    (1.400, 0.212, 0.114),
    (1.455, 0.185, 0.100),
    (1.485, 0.125, 0.082),
    (1.505, 0.088, 0.076),
]
SLEEVE_X = (0.15, 0.33)         # da raiz à barra da manga (a partir do centro do corpo)
SLEEVE_RADIUS = (0.062, 0.070)  # raiz → barra
SLEEVE_CENTER_Y = 1.43
SEG_TORSO, SEG_SLEEVE, RINGS_SLEEVE = 20, 8, 6
BASE_COLOR = (0.82, 0.86, 0.95, 1.0)


@dataclass
class Mesh3D:
    positions: np.ndarray
    normals: np.ndarray
    uvs: np.ndarray
    joints: np.ndarray
    weights: np.ndarray
    indices: np.ndarray


def _smoothstep(a: float, b: float, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _grid(points: np.ndarray, centers: np.ndarray, base: int) -> tuple[np.ndarray, np.ndarray]:
    """Triângulos de uma grade (anéis × pontos do arco). Enrola para o lado de fora (afastando de `centers`)."""
    n_r, n_p = points.shape[:2]
    idx = base + np.arange(n_r * n_p).reshape(n_r, n_p)
    a, b, c, d = idx[:-1, :-1], idx[:-1, 1:], idx[1:, :-1], idx[1:, 1:]
    tris = np.concatenate([np.stack([a, b, c], -1).reshape(-1, 3), np.stack([b, d, c], -1).reshape(-1, 3)])
    flat = points.reshape(-1, 3)
    ctr = np.repeat(centers, n_p, axis=0)
    p0, p1, p2 = (flat[tris[:, k] - base] for k in range(3))
    normal = np.cross(p1 - p0, p2 - p0)
    outward = (p0 + p1 + p2) / 3 - (ctr[tris[:, 0] - base] + ctr[tris[:, 1] - base] + ctr[tris[:, 2] - base]) / 3
    flip = (normal * outward).sum(axis=1) < 0
    tris[flip] = tris[flip][:, [0, 2, 1]]
    return flat, tris


def _torso_points(front: bool, hem: float) -> tuple[np.ndarray, np.ndarray]:
    ys = np.array([r[0] for r in TORSO_RINGS])
    ys[0] = hem
    a = np.array([r[1] for r in TORSO_RINGS])[:, None]
    b = np.array([r[2] for r in TORSO_RINGS])[:, None]
    phi = np.radians(np.linspace(-90, 90, SEG_TORSO + 1) + (0 if front else 180))
    pts = np.stack([a * np.sin(phi)[None], np.repeat(ys[:, None], len(phi), 1), b * np.cos(phi)[None]], -1)
    centers = np.stack([np.zeros_like(ys), ys, np.zeros_like(ys)], -1)
    return pts, centers


def _sleeve_points(side: float, front: bool, sleeve_end: float) -> tuple[np.ndarray, np.ndarray]:
    xs = np.linspace(SLEEVE_X[0], sleeve_end, RINGS_SLEEVE) * side
    r = np.linspace(*SLEEVE_RADIUS, RINGS_SLEEVE)[:, None]
    theta = np.radians(np.linspace(-90, 90, SEG_SLEEVE + 1) + (0 if front else 180))
    pts = np.stack([
        np.repeat(xs[:, None], len(theta), 1),
        SLEEVE_CENTER_Y + r * np.sin(theta)[None],
        0.95 * r * np.cos(theta)[None],
    ], -1)
    centers = np.stack([xs, np.full_like(xs, SLEEVE_CENTER_Y), np.zeros_like(xs)], -1)
    return pts, centers


def _weights(pos: np.ndarray, sleeve: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Pesos por vértice (máx. 4 influências): (V,4) índices de osso e (V,4) pesos, somando 1."""
    x, y = pos[:, 0], pos[:, 1]
    ax = np.abs(x)
    left = x >= 0
    n = len(pos)
    w = np.zeros((n, sk.N_JOINTS))

    # Tronco: corrente quadril → coluna → peito pela altura
    s_hips = 1 - _smoothstep(1.00, 1.12, y)
    s_chest = _smoothstep(1.10, 1.30, y)
    w[:, sk.INDEX["hips"]] = s_hips
    w[:, sk.INDEX["chest"]] = s_chest * (1 - s_hips)
    w[:, sk.INDEX["spine"]] = np.clip(1 - s_hips - s_chest * (1 - s_hips), 0, 1)

    # Pescoço: só a gola, e só perto do centro
    neck = _smoothstep(1.47, 1.505, y) * (1 - _smoothstep(0.06, 0.12, ax))
    w *= (1 - neck)[:, None]
    w[:, sk.INDEX["neck"]] = neck

    # Ombro do torso: acompanha a clavícula (encolher/levantar ombros) sem seguir o giro do braço
    for side, is_side in (("L", left), ("R", ~left)):
        sh = np.where(is_side & ~sleeve, 0.5 * _smoothstep(0.10, 0.19, ax) * _smoothstep(1.40, 1.46, y), 0.0)
        w[:] *= (1 - sh)[:, None]
        w[:, sk.INDEX[f"{side}_clavicle"]] += sh

    # Manga: do peito/clavícula para o braço conforme se afasta do centro
    arm = _smoothstep(0.13, 0.24, ax)
    for side, is_side in (("L", left), ("R", ~left)):
        m = is_side & sleeve
        clav = np.minimum((1 - arm) * 0.6, 0.5) * _smoothstep(1.36, 1.44, y)
        w[m] *= (1 - arm[m])[:, None]                       # o que sobra vem do tronco
        w[m] *= (1 - clav[m])[:, None]
        w[m, sk.INDEX[f"{side}_clavicle"]] += clav[m]
        w[m, sk.INDEX[f"{side}_upper_arm"]] += arm[m]

    order = np.argsort(-w, axis=1)[:, :4]
    top = np.take_along_axis(w, order, axis=1)
    top /= np.maximum(top.sum(axis=1, keepdims=True), 1e-8)
    return order.astype(np.uint16), top.astype(np.float32)


def _welded_normals(pos: np.ndarray, tris: np.ndarray) -> np.ndarray:
    """Normais suaves; vértices coincidentes (costura frente/costas) recebem a mesma normal."""
    p0, p1, p2 = (pos[tris[:, k]] for k in range(3))
    fn = np.cross(p1 - p0, p2 - p0)
    acc = np.zeros_like(pos)
    for k in range(3):
        np.add.at(acc, tris[:, k], fn)
    key = np.round(pos, 5)
    _, inv = np.unique(key, axis=0, return_inverse=True)
    inv = inv.ravel()
    summed = np.zeros((inv.max() + 1, 3))
    np.add.at(summed, inv, acc)
    n = summed[inv]
    return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)


def build_tshirt(sleeve_end: float = SLEEVE_X[1], hem: float = TORSO_RINGS[0][0]) -> Mesh3D:
    """Camiseta (torso + mangas curtas) na pose de repouso em T. sleeve_end: x da barra da manga (m);
    hem: y do barrado (m)."""
    positions, tris_all = [], []
    base = 0
    parts = [(_torso_points(f, hem), f, False) for f in (True, False)]
    parts += [(_sleeve_points(s, f, sleeve_end), f, True) for s in (+1.0, -1.0) for f in (True, False)]
    for (pts, ctr), _front, _sleeve in parts:
        flat, tris = _grid(pts, ctr, base)
        positions.append(flat)
        tris_all.append(tris)
        base += len(flat)
    pos = np.concatenate(positions)
    tris = np.concatenate(tris_all)

    # A borda de um arco (costura) é compartilhada no espaço; o "front" de cada vértice vem do índice
    front_mask = np.concatenate([np.full(len(p), f) for p, (_, f, _) in zip(positions, parts, strict=True)])
    sleeve_mask = np.concatenate([np.full(len(p), sl) for p, (_, _, sl) in zip(positions, parts, strict=True)])

    # UV: atlas planar. Frente em [0, .5] (u cresce com +x), costas em [.5, 1] (espelhado, visto por trás).
    xmin, xmax = pos[:, 0].min(), pos[:, 0].max()
    ymin, ymax = pos[:, 1].min(), pos[:, 1].max()
    u = (pos[:, 0] - xmin) / (xmax - xmin)
    uvs = np.stack([
        np.where(front_mask, 0.5 * u, 0.5 + 0.5 * (1 - u)),
        1 - (pos[:, 1] - ymin) / (ymax - ymin),
    ], 1)

    joints, weights = _weights(pos, sleeve_mask)
    return Mesh3D(
        positions=pos.astype(np.float32),
        normals=_welded_normals(pos, tris).astype(np.float32),
        uvs=uvs.astype(np.float32),
        joints=joints,
        weights=weights,
        indices=tris.astype(np.uint32).ravel(),
    )


def write_glb(mesh: Mesh3D, path: str | Path, name: str = "camiseta_template",
              color: tuple[float, ...] = BASE_COLOR) -> Path:
    """Grava o GLB: malha + skin + nós dos ossos (hierarquia do esqueleto padrão)."""
    path = Path(path)
    blob = bytearray()
    views, accessors = [], []

    def add(data: np.ndarray, comp_type: int, kind: str, target: int, minmax: bool = False) -> int:
        while len(blob) % 4:
            blob.append(0)
        raw = np.ascontiguousarray(data).tobytes()
        views.append(BufferView(buffer=0, byteOffset=len(blob), byteLength=len(raw), target=target))
        blob.extend(raw)
        count = len(data) if data.ndim == 1 else data.shape[0]
        acc = Accessor(bufferView=len(views) - 1, componentType=comp_type, count=count, type=kind)
        if minmax:
            acc.min, acc.max = data.min(axis=0).tolist(), data.max(axis=0).tolist()
        accessors.append(acc)
        return len(accessors) - 1

    a_pos = add(mesh.positions, FLOAT, "VEC3", ARRAY_BUFFER, minmax=True)
    a_nor = add(mesh.normals, FLOAT, "VEC3", ARRAY_BUFFER)
    a_uv = add(mesh.uvs, FLOAT, "VEC2", ARRAY_BUFFER)
    a_jnt = add(mesh.joints, UNSIGNED_SHORT, "VEC4", ARRAY_BUFFER)
    a_wgt = add(mesh.weights, FLOAT, "VEC4", ARRAY_BUFFER)
    a_idx = add(mesh.indices, UNSIGNED_INT, "SCALAR", ELEMENT_ARRAY_BUFFER)

    # inverseBindMatrices: glTF é column-major → transpor antes de gravar
    ibm = sk.inverse_bind().astype(np.float32).transpose(0, 2, 1)
    a_ibm = add(ibm, FLOAT, "MAT4", 0)
    views[-1].target = None

    # Nós: 0..n-1 = ossos (mesma ordem do esqueleto), n = malha
    nodes = [Node(name=j.name, translation=sk.REST_LOCAL[i].tolist()) for i, j in enumerate(sk.JOINTS)]
    for i, j in enumerate(sk.JOINTS):
        if j.parent >= 0:
            nodes[j.parent].children = (nodes[j.parent].children or []) + [i]
    mesh_node = sk.N_JOINTS
    nodes.append(Node(name=name, mesh=0, skin=0))

    gltf = GLTF2(
        asset=Asset(version="2.0", generator="provador.template"),
        scene=0,
        scenes=[Scene(nodes=[sk.INDEX["hips"], mesh_node])],
        nodes=nodes,
        meshes=[Mesh(name=name, primitives=[Primitive(
            attributes=Attributes(POSITION=a_pos, NORMAL=a_nor, TEXCOORD_0=a_uv, JOINTS_0=a_jnt, WEIGHTS_0=a_wgt),
            indices=a_idx, material=0)])],
        skins=[Skin(name="esqueleto", joints=list(range(sk.N_JOINTS)), inverseBindMatrices=a_ibm,
                    skeleton=sk.INDEX["hips"])],
        materials=[Material(name="tecido", doubleSided=True, pbrMetallicRoughness=PbrMetallicRoughness(
            baseColorFactor=list(color), metallicFactor=0.0, roughnessFactor=0.9))],
        accessors=accessors,
        bufferViews=views,
        buffers=[Buffer(byteLength=len(blob))],
    )
    gltf.set_binary_blob(bytes(blob))
    path.parent.mkdir(parents=True, exist_ok=True)
    gltf.save_binary(str(path))
    return path


# Catálogo procedural de demonstração: (arquivo, nome, cor RGBA, fim da manga, barrado). Nomes em ASCII (o HUD
# usa a fonte do OpenCV, sem acentos). O prefixo numérico define a ordem no app.
DEMO_CATALOG = [
    ("01_branca.glb", "Camiseta Branca", (0.93, 0.93, 0.95, 1.0), 0.33, 0.95),
    ("02_azul.glb", "Camiseta Azul Marinho", (0.12, 0.20, 0.42, 1.0), 0.33, 0.95),
    ("03_vermelha.glb", "Camiseta Vermelha Longa", (0.75, 0.13, 0.15, 1.0), 0.36, 0.88),
    ("04_verde.glb", "Camiseta Verde Curta", (0.20, 0.55, 0.32, 1.0), 0.26, 1.02),
    ("05_preta.glb", "Camiseta Preta", (0.10, 0.10, 0.12, 1.0), 0.31, 0.93),
]


def write_demo_catalog(folder: str | Path) -> list[Path]:
    """Gera as peças de demonstração em `folder` (sobrescreve as de mesmo nome)."""
    out = []
    for filename, name, color, sleeve_end, hem in DEMO_CATALOG:
        mesh = build_tshirt(sleeve_end=sleeve_end, hem=hem)
        out.append(write_glb(mesh, Path(folder) / filename, name=name, color=color))
    return out
