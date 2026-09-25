"""Transforma fotos de uma peça (frente e costas) em um GLB rigado com a textura projetada no UV do template.

Uso:
  python tools/garment_from_photos.py --sheet assets/photos/sesi/folha.jpg --name "Camiseta SESI"
  python tools/garment_from_photos.py --front frente.jpg --back costas.jpg --name "Camiseta X"

Fotos: peça estendida sem ninguém vestindo, luz uniforme, fundo liso, o maior possível (≥ 1024 px).
A folha pode trazer várias vistas lado a lado (frente, costas, mangas de lado...): elas são separadas
automaticamente, da esquerda para a direita. As vistas laterais ainda não são usadas.

Saída em assets/garments/: <slug>.glb (com o atlas embutido) e <slug>.meta.json. O prefixo "photo_" no slug
faz a peça aparecer depois das procedurais no app. Use --debug-dir para salvar recortes, análise e atlas.
"""

import argparse
import datetime
import json
import re
import sys
import unicodedata
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from provador import garment, paths, photos
from provador import template as tpl


def slugify(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", ascii_name.lower()).strip("_") or "peca"


def load_views(args) -> tuple[photos.View, photos.View, list[photos.View]]:
    """Devolve (frente, costas, todas as vistas encontradas)."""
    if args.sheet:
        img = cv2.imread(args.sheet)
        if img is None:
            raise SystemExit(f"não foi possível ler {args.sheet}")
        views = photos.split_views(img)
        if len(views) < 2:
            raise SystemExit(f"a folha tem {len(views)} vista(s); preciso de ao menos frente e costas")
        return views[0], views[1], views
    if not (args.front and args.back):
        raise SystemExit("informe --sheet, ou --front e --back")
    pair = []
    for name, path in (("frente", args.front), ("costas", args.back)):
        img = cv2.imread(path)
        if img is None:
            raise SystemExit(f"não foi possível ler {path}")
        found = photos.split_views(img, names=(name,))
        pair.append(max(found, key=lambda v: v.mask.sum()))            # se houver mais de uma, fica a maior
    return pair[0], pair[1], pair


def save_debug(out: Path, front: photos.View, back: photos.View, atlas) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for v in (front, back):
        cv2.imwrite(str(out / f"recorte_{v.name}.png"), v.rgb)
        cv2.imwrite(str(out / f"mascara_{v.name}.png"), (v.mask * 255).astype("uint8"))
    cv2.imwrite(str(out / "atlas.png"), atlas)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sheet", help="folha com as vistas lado a lado")
    ap.add_argument("--front", help="foto da frente")
    ap.add_argument("--back", help="foto das costas")
    ap.add_argument("--name", required=True, help="nome exibido no app (ASCII: a fonte do HUD não tem acentos)")
    ap.add_argument("--slug", help="nome do arquivo (padrão: photo_<nome>)")
    ap.add_argument("--out", default=str(paths.GARMENTS), help="pasta de saída (padrão: assets/garments)")
    ap.add_argument("--atlas", type=int, default=1024, help="largura do atlas em px (frente + costas)")
    ap.add_argument("--sleeve-end", type=float, default=tpl.SLEEVE_X[1], help="fim da manga do template (m)")
    ap.add_argument("--hem", type=float, default=tpl.TORSO_RINGS[0][0], help="altura do barrado do template (m)")
    ap.add_argument("--debug-dir", help="salva recortes, máscaras e o atlas nesta pasta")
    args = ap.parse_args()

    front, back, views = load_views(args)
    print(f"Vistas encontradas: {', '.join(f'{v.name} {v.bbox[2]}x{v.bbox[3]}' for v in views)}")
    for v in (front, back):
        if v.bbox[2] < 400:
            print(f"[AVISO] a vista '{v.name}' tem só {v.bbox[2]} px de largura; a textura vai ficar borrada "
                  "(o ideal é ≥ 1024 px).")

    mesh = tpl.build_tshirt(sleeve_end=args.sleeve_end, hem=args.hem)
    atlas, info = photos.build_atlas(front, back, mesh, args.sleeve_end, args.hem, size=args.atlas)
    for view, key in ((front, "front_sleeves"), (back, "back_sleeves")):
        if len(info[key]) < 2:
            print(f"[AVISO] só achei {len(info[key])} manga(s) na vista '{view.name}': "
                  "confira o recorte com --debug-dir (fundo liso? mangas separadas do tronco?).")

    ok, png = cv2.imencode(".png", atlas)
    assert ok
    slug = args.slug or f"photo_{slugify(args.name)}"
    out = Path(args.out)
    glb = tpl.write_glb(mesh, out / f"{slug}.glb", name=args.name, color=(1.0, 1.0, 1.0, 1.0),
                        texture_png=png.tobytes())
    meta = {
        "name": args.name,
        "slug": slug,
        "created": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": {"sheet": args.sheet, "front": args.front, "back": args.back},
        "views": [{"name": v.name, "bbox": list(v.bbox)} for v in views],
        "used_views": {"front": front.name, "back": back.name},
        "template": {"sleeve_end_m": args.sleeve_end, "hem_y_m": args.hem},
        "atlas": info,
        "notes": ("Textura projetada por linhas no tronco e por retângulo nas mangas; vistas laterais ainda não "
                  "usadas. As fotos e este GLB podem conter marcas: veja .gitignore antes de publicar."),
    }
    (out / f"{slug}.meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    if args.debug_dir:
        save_debug(Path(args.debug_dir), front, back, atlas)

    check = garment.load_glb(glb)                                           # confere que o app consegue ler
    assert check.texture is not None and check.texture.shape[:2] == atlas.shape[:2]
    print(f"OK: {glb} ({glb.stat().st_size / 1e3:.0f} kB, atlas {atlas.shape[1]}x{atlas.shape[0]}) + {slug}.meta.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
