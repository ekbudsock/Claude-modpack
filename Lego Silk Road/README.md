# Lego Silk Road

A Silk Road caravanserai (a fortified roadside inn for caravans) designed as a
buildable LEGO MOC in three sizes. The pipeline generates the layout from real
catalogue parts, checks it is physically buildable, builds it in Blender,
renders studio shots, and exports a bill of materials plus a sourcing plan.

| Size | Footprint | Features |
|---|---|---|
| Small | 12 × 12 studs | Single-thick walls, arched gate, 2 × 2 corner towers, covered well |
| Medium | 16 × 16 studs | Rooms behind one centred iwan arch per side, roof deck, raised gateway (pishtaq) with a sideways tile panel, 3 × 3 towers |
| Large | 32 × 32 baseplate | Double-thick outer walls, 18 × 18 sand courtyard, 3 arches per side, hollow 6 × 6 bastions, wider SNOT tile panel |

The results are in `builds/<size>/`: renders, `bom.csv`, `parts.xml`
(a BrickLink wanted list), `validation.json`, `cost.json`, `layout.json` and a
`.blend` file. The sourcing analysis is in [SOURCING.md](SOURCING.md).

## Running it

```bash
pip install -r requirements.txt          # bpy 5.2.2 (Blender as a Python module, Python 3.13)
python setup_env.py                      # pre-flight: mode, LDraw, Cycles, part templates
python pipeline.py --size all            # layout + validation + BOM + cost + renders
```

Or with a Blender binary, headless:

```bash
blender -b -P setup_env.py -- --timeout 120
blender -b -P pipeline.py -- --size medium --samples 128 --resolution 1600x1200
```

Useful flags: `--skip-render` (layout, checks, BOM and cost only; doesn't need
Blender), `--samples`, `--resolution WxH`, `--timeout SECONDS`, `--out DIR`.

Exit codes: `0` success, `1` runtime error, `2` a validation check failed,
`124` the watchdog timeout fired.

## How it works

| File | Role |
|---|---|
| `setup_env.py` | Detects how it was launched (bpy module, Blender CLI, or GUI) and reads script arguments after `--`. Provides a watchdog that hard-exits a hung render with code 124. Looks for an LDraw library and importer, falling back to procedural geometry. Lists Cycles devices, and builds and checks every part template, garbage-collecting afterwards. |
| `lego/catalog.py` | Part catalogue (BrickLink IDs, which match the LDraw file names), BrickLink colour IDs and LEGO hex values, active-mold and colour-availability tables, price tables. |
| `lego/layout.py` | Procedural caravanserai on the integer LEGO grid, plus the course tiler (see below). |
| `lego/validate.py` | Physical-build checks (see below). |
| `lego/templates.py` | `bpy` part meshes with hollow undersides, anti-stud tubes or posts, 4.8 × 1.7 mm studs, 0.1 mm sidewall clearance, and a 0.2 mm Bevel modifier baked into each shared template. Also the ABS plastic materials. |
| `lego/scene.py` | Instancing into the four build-phase collections, the three-point softbox rig, the infinite sweep, cameras and the Cycles renders. |
| `lego/bom.py`, `lego/cost.py` | `bom.csv`, BrickLink XML, and the cost and sourcing split. |
| `pipeline.py` | Orchestrates all of the above for each size. |

### Course tiler (running bond)

Each wall course is filled by an exact depth-first search with
conflict-directed backjumping. It takes the largest available element first.
A placement is rejected if:

* a vertical joint would sit directly on a joint in the course below or above,
* it would stack exactly on an identical part (a "column"),
* any stud would be left unsupported beyond a 4-stud span or a 1-stud cantilever, or
* it would strand a cell that no part can still reach.

A one-course lookahead keeps T- and L-junctions bridgeable by the next course.
Afterwards, a repair pass re-solves small windows around any leftover aligned
joint, either in its own course or jointly with the course below or above.

### Validation (`builds/<size>/validation.json`)

* System dimensions: 8.0 mm stud pitch, 3.2 mm plate, 9.6 mm brick, 4.8 × 1.7 mm studs, 0.1 mm sidewall gap.
* 5:2 SNOT rule: 2 studs sideways = 5 plates (16.0 mm); each sideways panel spans exactly 5 plates, starting on the plate grid.
* Every part is an active mold in a stocked colour; known retired molds are blocked.
* No body collisions, checked on millimetre bounding boxes with the clearance gap.
* Every part connects to the baseplate through real stud-in-tube joints or bracket studs.
* No unsupported spans over 4 studs, and cantilevers of at most 1 stud.
* No untied single-column stacks. The well posts are tied in by the canopy plate.
* Running bond: no vertical joint continues through 3 or more courses, and at
  least 98% of in-course joints are staggered. Every remaining aligned joint is
  listed by location. Joints against a fixed feature, such as the side of a
  two-course arch or a tower rising past the wall, are boundaries rather than
  in-course joints.

### Scene

The outliner collections are `01_Baseplate_Foundation`, `02_Structural_Core`,
`03_Exterior_Facade`, `04_Roof_Details` and `05_Studio`. Materials use a
Principled BSDF with LEGO sRGB colours, roughness 0.18 (0.15 for transparent
parts), IOR 1.46 and subsurface 0.03. Renders use Cycles on the CPU with
adaptive sampling and OpenImageDenoise. The key light is warm, the fill cool
and the rim crisp, against a roughness-0.8 sweep, with subtle depth of field on
the perspective views.

## Assumptions and limits

* No reference image was supplied. The design follows the standard Persian
  caravanserai plan: a square walled court, a raised gateway, iwan arcades,
  corner towers and a central well.
* There was no LDraw library or network access to one in the build
  environment, so all geometry is procedural. `setup_env.py` reports when
  LDraw is available.
* The geometry of the arches, slopes and the 99781 bracket is modelled from
  published dimensions, with solid undersides.
* Prices, mold status and colour availability are curated catalogue data, not
  live BrickLink or Pick a Brick queries. Re-price `parts.xml` on BrickLink
  before ordering.
