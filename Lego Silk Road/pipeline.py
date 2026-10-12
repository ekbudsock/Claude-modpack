"""Lego Silk Road: model, validate, catalogue and render the caravanserai.

    python pipeline.py --size all                      # bpy module (pip install bpy)
    blender -b -P pipeline.py -- --size medium         # Blender binary, headless

Per size it writes builds/<size>/:
    layout.json         every placement (part, colour, grid position, rotation)
    validation.json     physical-build checks
    bom.csv, parts.xml  bill of materials / BrickLink wanted list
    cost.json           sourcing split and price-per-part
    caravanserai_<size>.blend
    renders/hero_perspective.png, profile_elevation.png, detail_topdown.png

Exit codes: 0 success, 1 runtime error, 2 validation failed, 124 timeout.
"""

import argparse
import gc
import json
import os
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from setup_env import EXIT_FAIL, EXIT_OK, Watchdog, detect_mode, script_args  # noqa: E402

EXIT_INVALID = 2


def layout_json(model):
    return {
        "name": model.name,
        "base_size_studs": model.base_size,
        "units": {"x_y": "studs (8.0 mm)", "z": "plates (3.2 mm)", "sideways_mm": "x_center, y_back_face, z_center"},
        "parts": [
            {"part": pl.part, "color": pl.color, "x": pl.x, "y": pl.y, "z": pl.z, "rot": pl.rot,
             "collection": pl.collection, "group": pl.group,
             **({"sideways": True, "mm": [round(v, 3) for v in pl.mm]} if pl.sideways else {})}
            for pl in model.parts
        ],
    }


def run_size(size, args, can_render):
    from lego.bom import bom_rows, write_bricklink_xml, write_csv
    from lego.cost import analyze
    from lego.layout import build_caravanserai
    from lego.validate import validate, visibility

    out = os.path.join(args.out, size)
    os.makedirs(out, exist_ok=True)
    t0 = time.time()
    model = build_caravanserai(size)
    t_layout = time.time() - t0
    report = validate(model)
    report["layout_seconds"] = round(t_layout, 1)
    with open(os.path.join(out, "layout.json"), "w") as f:
        json.dump(layout_json(model), f, indent=1)
    with open(os.path.join(out, "validation.json"), "w") as f:
        json.dump(report, f, indent=2)
    rows = bom_rows(model)
    write_csv(rows, os.path.join(out, "bom.csv"))
    write_bricklink_xml(rows, os.path.join(out, "parts.xml"))
    cost = analyze(model, visibility(model))
    with open(os.path.join(out, "cost.json"), "w") as f:
        json.dump(cost, f, indent=2)
    print(f"[{size}] {report['parts']} parts, {cost['lots']} lots, layout {t_layout:.0f}s, "
          f"checks: " + ", ".join(f"{k}={'ok' if v else 'FAIL'}" for k, v in report["checks"].items()))
    print(f"[{size}] est. ${cost['optimised_total']:.2f} optimised "
          f"(${cost['ppp_optimised']:.3f}/part), all-BrickLink ${cost['all_bricklink']:.2f}")

    rendered = []
    if can_render and not args.skip_render:
        from lego import scene
        scene.reset_scene()
        scene.build_model(model)
        gc.collect()
        lo, hi, center, radius, col = scene.studio(model, samples=args.samples, resolution=args.resolution)
        t1 = time.time()
        rendered = scene.render_views(model, os.path.join(out, "renders"), lo, hi, center, radius, col)
        print(f"[{size}] rendered {len(rendered)} views in {time.time() - t1:.0f}s")
        import bpy
        bpy.context.scene.camera = bpy.data.objects["CAM_Hero"]
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(os.path.join(out, f"caravanserai_{size}.blend")),
                                    compress=True)
    return report["passed"], report, cost, rendered


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--size", default="all", choices=["small", "medium", "large", "all"])
    ap.add_argument("--samples", type=int, default=128)
    ap.add_argument("--resolution", default="1600x1200")
    ap.add_argument("--skip-render", action="store_true")
    ap.add_argument("--timeout", type=float, default=4 * 3600, help="watchdog seconds (0 = off)")
    ap.add_argument("--out", default=os.path.join(HERE, "builds"))
    args = ap.parse_args(script_args())
    args.resolution = tuple(int(v) for v in args.resolution.lower().split("x"))

    env = detect_mode()
    print(f"[pipeline] mode={env['mode']} blender={env.get('bpy')} python={sys.version.split()[0]}")
    can_render = env["bpy"] is not None
    if not can_render and not args.skip_render:
        print("[pipeline] bpy not available: layout, validation, BOM and cost only")
    sizes = ["small", "medium", "large"] if args.size == "all" else [args.size]
    summary, all_ok = {}, True
    try:
        with Watchdog(args.timeout, "pipeline"):
            for size in sizes:
                ok, report, cost, rendered = run_size(size, args, can_render)
                all_ok &= ok
                summary[size] = {"passed": ok, "parts": report["parts"], "lots": cost["lots"],
                                 "optimised_total": cost["optimised_total"], "renders": rendered}
                gc.collect()
    except Exception:  # noqa: BLE001 - surface any failure as a non-zero exit
        traceback.print_exc()
        sys.exit(EXIT_FAIL)
    with open(os.path.join(args.out, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    if all(os.path.exists(os.path.join(args.out, s, "cost.json")) for s in ("small", "medium", "large")):
        from lego.report import write_sourcing
        write_sourcing(args.out, os.path.join(HERE, "SOURCING.md"))
        print("[pipeline] wrote SOURCING.md")
    sys.exit(EXIT_OK if all_ok else EXIT_INVALID)


if __name__ == "__main__":
    main()
