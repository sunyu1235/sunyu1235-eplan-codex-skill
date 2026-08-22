#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse, json, re
from pathlib import Path
import cadquery as cq


def safe(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._+-]+", "_", s.strip()).strip("_")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", default="cad-libraries/dimension-proxies.json")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    index = []

    for p in spec["parts"]:
        model = p["model"]
        w, h, d = float(p["w"]), float(p["h"]), float(p["d"])
        # X=width, Y=depth, Z=height, origin at mounting-plate lower-left/back corner.
        shape = cq.Workplane("XY").box(w, d, h, centered=(False, False, False))
        fn = safe(model) + "_DIMENSION_PROXY.step"
        target = out / fn
        cq.exporters.export(shape, str(target))
        sidecar = {
            "model": model,
            "width_mm": w,
            "height_mm": h,
            "depth_mm": d,
            "axis": "X=W, Y=D, Z=H",
            "status": p["status"],
            "source": p["source"],
            "file": fn,
            "purpose": "cabinet placement/envelope only; not visual-detail replacement"
        }
        (out / (safe(model) + ".json")).write_text(json.dumps(sidecar, ensure_ascii=False, indent=2), encoding="utf-8")
        index.append(sidecar)
        print(f"generated {model}: {w}x{h}x{d} mm -> {fn}")

    (out / "proxy-index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"DONE: {len(index)} STEP dimension proxies")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
