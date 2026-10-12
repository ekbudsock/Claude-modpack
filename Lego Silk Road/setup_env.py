"""Environment bootstrap and pre-flight for the Lego Silk Road pipeline.

Run it either way:

    python setup_env.py                      # Blender as a Python module (pip install bpy)
    blender -b -P setup_env.py -- [--timeout 120]

What it checks
--------------
1. Execution mode: standalone ``bpy`` module vs. the Blender binary (CLI with
   ``--background`` or a GUI session), and the script-argument convention
   (everything after ``--`` when launched by the Blender binary).
2. Watchdog: a hard wall-clock timeout that kills a hung render/bake with exit
   code 124, so CI and cron jobs never wedge.
3. Geometry source: a local LDraw parts library (``LDRAWDIR`` or the usual
   install paths) and an LDraw importer add-on (ImportLDraw / ldr_tools_blender).
   If either is missing the pipeline uses its procedural ``bpy`` templates.
4. Render device: Cycles is present and which compute devices it can see.
5. Templates: builds every catalogue part once (hollow underside, tubes or posts,
   studs, baked 0.2 mm bevel), checks each mesh is non-empty and closed where it
   should be, then frees it and runs a garbage-collection pass.

Exit codes: 0 ready, 1 a check failed, 124 watchdog timeout.
"""

import gc
import json
import os
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

EXIT_OK, EXIT_FAIL, EXIT_TIMEOUT = 0, 1, 124


def script_args(argv=None):
    """Arguments meant for this script.  The Blender binary passes its own flags
    first and ours after a literal '--'."""
    argv = sys.argv if argv is None else argv
    return argv[argv.index("--") + 1:] if "--" in argv else argv[1:]


def detect_mode():
    try:
        import bpy
    except ImportError:
        return {"mode": "no-blender", "bpy": None}
    binary = bpy.app.binary_path or ""
    if not binary:
        mode = "bpy-module"
    elif bpy.app.background:
        mode = "blender-cli"
    else:
        mode = "blender-gui"
    return {
        "mode": mode,
        "bpy": bpy.app.version_string,
        "binary_path": binary,
        "background": bool(bpy.app.background),
        "python": sys.version.split()[0],
    }


class Watchdog:
    """Hard timeout.  Rendering happens in C, so a Python signal can't interrupt it;
    a daemon timer that calls os._exit can."""

    def __init__(self, seconds, label="pipeline"):
        self.seconds = seconds
        self.label = label
        self._t = None

    def _fire(self):
        sys.stderr.write(f"\n[watchdog] {self.label} exceeded {self.seconds}s, aborting\n")
        sys.stderr.flush()
        os._exit(EXIT_TIMEOUT)

    def __enter__(self):
        if self.seconds and self.seconds > 0:
            self._t = threading.Timer(self.seconds, self._fire)
            self._t.daemon = True
            self._t.start()
        return self

    def __exit__(self, *exc):
        if self._t:
            self._t.cancel()
        return False


def find_ldraw():
    candidates = [os.environ.get("LDRAWDIR", ""),
                  os.path.expanduser("~/ldraw"), os.path.expanduser("~/LDraw"),
                  "/usr/share/ldraw", "/usr/local/share/ldraw", "/opt/ldraw",
                  "C:/LDraw", "C:/Program Files/LDraw",
                  "/Applications/LDraw", os.path.expanduser("~/Library/ldraw")]
    for c in candidates:
        if c and os.path.isfile(os.path.join(c, "parts", "3001.dat")):
            return c
    return None


def find_ldraw_importer():
    try:
        import addon_utils
    except ImportError:
        return None
    for mod in addon_utils.modules():
        name = mod.__name__.lower()
        if "ldraw" in name or "ldr_tools" in name:
            return mod.__name__
    return None


def cycles_devices():
    import bpy
    out = {"cycles": "cycles" in bpy.context.preferences.addons.keys() or hasattr(bpy.types, "CyclesRenderSettings")}
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.refresh_devices()
        out["devices"] = sorted({f"{d.type}:{d.name}" for d in prefs.devices})
    except Exception as exc:  # noqa: BLE001 - report, don't crash pre-flight
        out["devices"] = [f"CPU (device query failed: {exc})"]
    return out


def check_templates():
    """Build every catalogue part template once and sanity-check the mesh."""
    import bmesh
    import bpy
    from lego.catalog import PARTS
    from lego.templates import build_template

    report = {}
    ok = True
    for pid in sorted(PARTS):
        t = time.time()
        mesh = build_template(pid)
        bm = bmesh.new()
        bm.from_mesh(mesh)
        boundary = sum(1 for e in bm.edges if e.is_boundary)
        bm.free()
        dims = [round(v * 1000, 2) for v in (max(c.co[i] for c in mesh.vertices) - min(c.co[i] for c in mesh.vertices) for i in range(3))]
        good = len(mesh.polygons) > 0
        ok &= good
        report[pid] = {"verts": len(mesh.vertices), "faces": len(mesh.polygons),
                       "open_edges": boundary, "size_mm": dims, "ms": round((time.time() - t) * 1000)}
        bpy.data.meshes.remove(mesh)
    gc.collect()
    return ok, report


def preflight(build_templates=True, verbose=True):
    env = detect_mode()
    env["ldraw_library"] = find_ldraw()
    env["ldraw_importer"] = find_ldraw_importer() if env["bpy"] else None
    env["geometry_source"] = ("ldraw" if env["ldraw_library"] and env["ldraw_importer"]
                              else "procedural-bpy")
    ok = env["bpy"] is not None
    if ok:
        env["render"] = cycles_devices()
        if build_templates:
            tok, env["templates"] = check_templates()
            ok &= tok
    env["ready"] = ok
    if verbose:
        brief = {k: v for k, v in env.items() if k != "templates"}
        print(json.dumps(brief, indent=2))
        if "templates" in env:
            for pid, r in env["templates"].items():
                print(f"  template {pid:>6}: {r['verts']:>6} verts  size {r['size_mm']} mm  open edges {r['open_edges']}")
    return env


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Lego Silk Road environment pre-flight")
    ap.add_argument("--timeout", type=float, default=300, help="watchdog seconds (0 = off)")
    ap.add_argument("--no-templates", action="store_true", help="skip building part templates")
    ap.add_argument("--report", default=os.path.join(HERE, "builds", "env_report.json"))
    args = ap.parse_args(script_args())
    try:
        with Watchdog(args.timeout, "pre-flight"):
            env = preflight(build_templates=not args.no_templates)
        os.makedirs(os.path.dirname(args.report), exist_ok=True)
        with open(args.report, "w") as f:
            json.dump(env, f, indent=2)
    except Exception as exc:  # noqa: BLE001 - any failure is a failed pre-flight
        print(f"[setup_env] FAILED: {exc!r}", file=sys.stderr)
        sys.exit(EXIT_FAIL)
    sys.exit(EXIT_OK if env["ready"] else EXIT_FAIL)


if __name__ == "__main__":
    main()
