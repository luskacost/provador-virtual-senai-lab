"""Gera a camiseta procedural rigada (template das peças) em assets/templates/tshirt.glb.

Uso:  python tools/make_template.py [--out caminho.glb] [--preview preview.png]
--preview desenha frente, lado e uma pose de teste (braço levantado) com matplotlib, para conferir a olho.
"""

import argparse

from provador import paths
from provador.template import build_tshirt, write_demo_catalog, write_glb


def preview(glb, png) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    from provador import garment
    from provador import skeleton as sk

    g = garment.load_glb(glb)
    tris = g.indices.reshape(-1, 3)
    rots = np.broadcast_to(np.eye(3), (sk.N_JOINTS, 3, 3)).copy()
    rots[sk.INDEX["L_upper_arm"]] = sk.rotation_axis_angle((0, 0, 1), 60)     # braço esquerdo sobe
    rots[sk.INDEX["R_upper_arm"]] = sk.rotation_axis_angle((0, 0, 1), 70)     # braço direito desce
    rots[sk.INDEX["spine"]] = sk.rotation_axis_angle((0, 1, 0), 25)           # torce o tronco
    posed = garment.skin(g, sk.skin_matrices(sk.world_matrices(rots)))

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    views = [("Frente (repouso)", g.positions, (0, 1)), ("Lado (repouso)", g.positions, (2, 1)),
             ("Frente (pose de teste)", posed, (0, 1))]
    for ax, (title, pts, (i, j)) in zip(axes, views, strict=True):
        ax.triplot(pts[:, i], pts[:, j], tris, lw=0.3, color="steelblue")
        ax.scatter(sk.REST_WORLD[:, i], sk.REST_WORLD[:, j], s=8, c="crimson", zorder=3)
        ax.set_aspect("equal")
        ax.set_title(title)
    fig.savefig(png, dpi=110, bbox_inches="tight")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(paths.TEMPLATES / "tshirt.glb"))
    ap.add_argument("--catalog", action="store_true", help="gera também as 5 peças de demonstração em assets/garments/")
    ap.add_argument("--preview", help="salva um PNG de conferência (requer matplotlib)")
    args = ap.parse_args()
    if args.catalog:
        for path in write_demo_catalog(paths.GARMENTS):
            print(path)
    mesh = build_tshirt()
    out = write_glb(mesh, args.out)
    print(f"{out} | {len(mesh.positions)} vertices, {len(mesh.indices) // 3} triangulos")
    if args.preview:
        preview(out, args.preview)
        print(f"preview: {args.preview}")


if __name__ == "__main__":
    main()
