# Handoff: Lego Silk Road caravanserai

This is a briefing for a local Claude Code session on a faster machine,
picking up from a cloud session that ran on a 4-core CPU with no GPU.
The goal is **faster renders while refining the design**.

## Where things stand

- **Repo:** `ekbudsock/Claude-modpack`, branch `claude/new-project-folder-jmphwz`, project folder `Lego Silk Road/`.
- **Status:** a complete pipeline for a Silk Road caravanserai MOC in three sizes. Every size passes all validation checks; renders, BOMs and the sourcing analysis are committed.
- **Docs:** `README.md` covers architecture and usage. `SOURCING.md` is the generated cost analysis.

| | Small 12×12 | Medium 16×16 | Large 32×32 |
|---|---:|---:|---:|
| Parts / lots | 124 / 26 | 281 / 45 | 676 / 57 |
| BrickLink, parts only | $10.95 | $26.92 | $76.36 |
| Incl. est. shipping | $16.95 | $38.92 | $88.36 |
| Joints staggered | 100% | 99.6% | 100% |
| Layout time (CPU) | <1 s | ~25 s | ~130 s |
| Render time, 3 views (4-core CPU) | ~18 min | ~18 min | ~16 min |

Rendering is the bottleneck. Layout, validation, BOM and cost together take
about 3 minutes for all sizes.

## Local setup

```bash
git clone https://github.com/ekbudsock/Claude-modpack.git
cd Claude-modpack && git checkout claude/new-project-folder-jmphwz
cd "Lego Silk Road"            # note the spaces: always quote this path
python3.13 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt # bpy==5.2.2, which needs Python 3.13
python setup_env.py             # pre-flight; exit 0 means ready
```

If you have a Blender 5.2 binary instead, run
`blender -b -P setup_env.py -- --timeout 120` and
`blender -b -P pipeline.py -- --size medium`.

## Turning on the GPU (needs a code change)

`lego/scene.py`, `studio()`, hard-codes `sc.cycles.device = "CPU"` (around
line 162). The cloud box had no GPU, so it was never parameterised. Suggested
change: add a `--device` flag to `pipeline.py` (`CPU|GPU|auto`), pass it
through to `studio()`, and enable the GPU like this:

```python
prefs = bpy.context.preferences.addons["cycles"].preferences
for backend in ("OPTIX", "CUDA", "HIP", "METAL", "ONEAPI"):   # first one that works
    try:
        prefs.compute_device_type = backend
        prefs.refresh_devices()
        gpus = [d for d in prefs.devices if d.type == backend]
        if gpus:
            for d in prefs.devices:
                d.use = d.type == backend
            sc.cycles.device = "GPU"
            break
    except TypeError:
        continue
```

`setup_env.py` already reports the Cycles devices it can see, so use it to
confirm the GPU is detected. OptiX also supports the OpenImageDenoise path the
pipeline uses.

## Fast iteration loop

- **Checks, BOM and cost only (no Blender):** `python pipeline.py --size medium --skip-render`
- **Quick preview:** `python pipeline.py --size medium --samples 16 --resolution 640x480 --out /tmp/preview`
- **Final quality:** `python pipeline.py --size all` (128 samples, 1600×1200, adaptive 0.02, OIDN). On a GPU, consider `--samples 256 --resolution 3200x2400`.
- **Re-render without regenerating the layout:** each `builds/<size>/caravanserai_<size>.blend` contains the model, the studio and three cameras (`CAM_Hero`, `CAM_Profile`, `CAM_TopDown`). Open it in the Blender GUI to tweak lighting interactively, or render a camera headless:
  ```bash
  blender -b "builds/medium/caravanserai_medium.blend" --python-expr \
    "import bpy; s=bpy.context.scene; s.camera=bpy.data.objects['CAM_Profile']; s.render.filepath='/abs/path/out.png'; bpy.ops.render.render(write_still=True)"
  ```
- **Exit codes:** 0 success, 1 runtime error, 2 a validation check failed, 124 watchdog timeout (default 4 h; `--timeout`).

Use **absolute** output paths with `bpy`. A relative `filepath` fails to save.

## Code map

| File | What it does |
|---|---|
| `lego/catalog.py` | Parts (BrickLink IDs, which match LDraw), colours (BL IDs plus LEGO hex), the `AVAILABLE` part×colour whitelist, `OBSOLETE` molds, price tables. Change palettes or parts here. |
| `lego/layout.py` | `SIZES` config (footprint, wall thickness, room depth, tower size, layer schedule `PBBPBB`, SNOT width) and `build_caravanserai()`. Also the course tiler `Model.fill` and the seam repair `Model.repair_seams`. |
| `lego/validate.py` | All physical checks, reported in `validation.json`. |
| `lego/templates.py` | Procedural part meshes (mm → m), baked 0.2 mm bevel, ABS materials. |
| `lego/scene.py` | Collections, instancing, the three-point area-light rig, the cove sweep, cameras, and the Cycles settings. |
| `lego/bom.py`, `cost.py`, `report.py` | `bom.csv`, BrickLink `parts.xml`, cost model, `SOURCING.md`. The pipeline regenerates `SOURCING.md` when all three sizes exist. |
| `setup_env.py`, `pipeline.py` | Pre-flight and orchestration. |

## Hard-won lessons (don't undo these)

1. **The tiler is exact search, not greedy.** It uses depth-first search with conflict-directed backjumping and an exact next-course lookahead. That lookahead treats untiled neighbours of placed cells as certain joints, and counts joints against fixed parts such as arch legs. Greedy is only a fallback, followed by multi-course window repair. Early greedy versions left a joint running up all seven courses of the large build.
2. **Seam rule consistency.** The solver and the validator count only *in-course* joints, where both cells are in the same tiled region. A joint against an arch side or a tower face is a boundary, because no course can bridge it. When the solver was stricter than the validator, whole courses became infeasible.
3. **Columns:** only 2-stud stubs may repeat the part below (`len(region) > 2` in `exact`). At 4 studs this let the small model's 2×2 towers become untied columns.
4. **Arcades need a corner pier.** An arch leg on both sides of a ring corner creates an unbridgeable joint. That's why medium has one centred iwan per side.
5. **The plinth stops at openings**, and the path tiles run through the gate. A plinth under the opening produced a joint pattern the next course couldn't match.
6. **Merlons:** they're placed *before* the course they sit on is tiled, and 1-stud stubs get none (a 1×1 on a 1×1 is a column).
7. **Studio:** lights are `visible_camera = False`, the sweep is 40× the model span (a narrower one showed its edge as a dark disc), and the ortho elevation's frame bottom sits on the floor line. Light power scales with distance², so every size gets the same exposure.
8. **Determinism:** `Model(seed=7)`. Same code, same layout.

## Known limitations and refinement backlog

- **Medium has 1 aligned joint:** a roof-deck plate over the back arcade arch leg, at (9,12)–(10,12). The deck, the wall below, the parapet and the trim constrain it all at once. It's listed in `validation.json`.
- **Running-bond pass criterion:** no joint through 3 or more courses, and at least 98% staggered. That is a deliberate relaxation of "every joint staggered", and it's documented.
- **Geometry approximations:** arches, slopes and the 99781 bracket have solid undersides and use published dimensions. There are no LEGO logos on the studs. The gap is 0.1 mm as specified; real LEGO is about 0.2 mm.
- **LDraw** is detected by `setup_env.py` but there is **no import path**. If you have a local LDraw library plus ImportLDraw or ldr_tools_blender, swapping in real part geometry is a natural upgrade, and it's much more practical with a GPU.
- **Prices are curated estimates, not live data.** Pick a Brick and bulk generic lots were never cheaper under this model. Re-price by uploading `builds/<size>/parts.xml` to BrickLink.
- **`profile_elevation.png` is the front facade.** For a true side view, change the `CAM_Profile` position in `scene.render_views`.
- `builds/summary.json` and `env_report.json` contain absolute paths from the cloud box.
- **Render ideas** once a GPU is available: 256–512 samples at 4K, a slight bevel-weight increase for crisper highlights, a turntable animation (the camera rig is already parametric), and a construction-step render per collection (`01_` to `04_`).

## Owner preferences

The owner wants clarifying questions when context is missing, a brief plan
before multi-step work, and **confirmation before deleting, editing or
overwriting existing code or documents**. Commit to the branch above; don't
open a PR unless asked.
