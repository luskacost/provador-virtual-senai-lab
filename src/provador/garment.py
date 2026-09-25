"""Peça de roupa rigada: leitura de GLB e skinning (LBS) de referência em numpy.

O renderer (T5) faz o mesmo cálculo no vertex shader; esta versão em CPU serve de referência e de teste.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from pygltflib import GLTF2

from . import skeleton

_COMPONENT_DTYPE = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
_TYPE_SIZE = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


@dataclass
class Garment:
    positions: np.ndarray        # (V, 3) float32, pose de repouso
    normals: np.ndarray          # (V, 3) float32
    uvs: np.ndarray              # (V, 2) float32 (origem no canto superior esquerdo, como no glTF)
    joints: np.ndarray           # (V, 4) uint16, índices do esqueleto padrão (skeleton.INDEX)
    weights: np.ndarray          # (V, 4) float32, somam 1
    indices: np.ndarray          # (F*3,) uint32
    base_color: tuple[float, float, float, float]
    name: str = ""


def _read_accessor(gltf: GLTF2, blob: bytes, index: int) -> np.ndarray:
    acc = gltf.accessors[index]
    view = gltf.bufferViews[acc.bufferView]
    dtype = np.dtype(_COMPONENT_DTYPE[acc.componentType])
    n_comp = _TYPE_SIZE[acc.type]
    offset = (view.byteOffset or 0) + (acc.byteOffset or 0)
    stride = view.byteStride or dtype.itemsize * n_comp
    if stride == dtype.itemsize * n_comp:
        data = np.frombuffer(blob, dtype, acc.count * n_comp, offset)
    else:  # dados intercalados
        raw = np.frombuffer(blob, np.uint8, acc.count * stride, offset).reshape(acc.count, stride)
        data = raw[:, : dtype.itemsize * n_comp].copy().view(dtype).ravel()
    return data.reshape(acc.count, n_comp) if n_comp > 1 else data.copy()


def load_glb(path: str | Path) -> Garment:
    """Lê a primeira primitiva da primeira malha rigada. Os ossos são remapeados pelo NOME do nó para o
    esqueleto padrão; nomes fora do padrão geram erro claro (melhor que uma peça deformada errado)."""
    gltf = GLTF2().load(str(path))
    blob = gltf.binary_blob()
    if not gltf.skins:
        raise ValueError(f"{path}: GLB sem skin (peça não rigada)")
    prim = gltf.meshes[0].primitives[0]
    attr = prim.attributes
    if attr.JOINTS_0 is None or attr.WEIGHTS_0 is None:
        raise ValueError(f"{path}: malha sem JOINTS_0/WEIGHTS_0")

    names = [gltf.nodes[j].name for j in gltf.skins[0].joints]
    unknown = [n for n in names if n not in skeleton.INDEX]
    if unknown:
        raise ValueError(f"{path}: ossos fora do esqueleto padrão: {unknown}")
    remap = np.array([skeleton.INDEX[n] for n in names], np.uint16)

    raw_w = _read_accessor(gltf, blob, attr.WEIGHTS_0)
    weights = raw_w.astype(np.float32)
    if raw_w.dtype != np.float32:           # pesos normalizados em uint8/uint16
        weights /= np.iinfo(raw_w.dtype).max
    weights /= np.maximum(weights.sum(axis=1, keepdims=True), 1e-8)

    mat = gltf.materials[prim.material] if prim.material is not None and gltf.materials else None
    color = tuple(mat.pbrMetallicRoughness.baseColorFactor) if mat and mat.pbrMetallicRoughness else (1, 1, 1, 1)

    return Garment(
        positions=_read_accessor(gltf, blob, attr.POSITION).astype(np.float32),
        normals=_read_accessor(gltf, blob, attr.NORMAL).astype(np.float32),
        uvs=_read_accessor(gltf, blob, attr.TEXCOORD_0).astype(np.float32),
        joints=remap[_read_accessor(gltf, blob, attr.JOINTS_0).astype(np.int64)],
        weights=weights,
        indices=_read_accessor(gltf, blob, prim.indices).astype(np.uint32),
        base_color=color,
        name=gltf.meshes[0].name or Path(path).stem,
    )


def skin(garment: Garment, skin_mats: np.ndarray) -> np.ndarray:
    """LBS: posição deformada de cada vértice = Σ peso × (matriz de skinning do osso × posição). (V, 3)."""
    p = np.concatenate([garment.positions, np.ones((len(garment.positions), 1), np.float32)], axis=1)  # (V,4)
    out = np.zeros((len(p), 3))
    for k in range(4):
        m = skin_mats[garment.joints[:, k]]                       # (V, 4, 4)
        out += garment.weights[:, k, None] * np.einsum("vij,vj->vi", m, p)[:, :3]
    return out
