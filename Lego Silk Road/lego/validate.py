"""Physical-build checks for a generated Model (no Blender needed)."""

from collections import defaultdict

from .catalog import (BRICK, GAP, INSET, OBSOLETE, PARTS, PLATE, STUD, STUD_D, STUD_H,
                      is_available)
from .layout import span_ok

BASEPLATE_BOTTOM = 1.6  # mm; a 3811 baseplate is a thin sheet under the first plate level


def part_boxes(pl):
    """Axis-aligned body boxes in mm (studs excluded: they sit inside the part above)."""
    p = pl.p
    if pl.sideways:
        cx, yb, cz = pl.mm
        hw, hd = p.w * STUD / 2 - INSET, p.d * STUD / 2 - INSET
        return [(cx - hw, cx + hw, yb - p.h * PLATE, yb, cz - hd, cz + hd)]
    w, d = pl.dims()
    x0, x1 = pl.x * STUD + INSET, (pl.x + w) * STUD - INSET
    y0, y1 = pl.y * STUD + INSET, (pl.y + d) * STUD - INSET
    z0, z1 = pl.z * PLATE, (pl.z + p.h) * PLATE
    if p.kind == "baseplate":
        z0 = BASEPLATE_BOTTOM
    boxes = [(x0, x1, y0, y1, z0, z1)]
    if p.kind == "bracket":
        # Vertical 1 x 2 plate hanging off the -Y edge, bottom flush with the base.
        assert pl.rot == 0, "brackets are only modelled facing -Y"
        boxes.append((x0, x1, pl.y * STUD - PLATE, y0, z0, z0 + STUD))
    return boxes


def _overlap(a, b, eps=1e-6):
    return all(min(a[i + 1], b[i + 1]) - max(a[i], b[i]) > eps for i in (0, 2, 4))


def check_collisions(model):
    grid = defaultdict(list)
    boxes = []
    for i, pl in enumerate(model.parts):
        for bx in part_boxes(pl):
            boxes.append((i, bx))
    for k, (i, bx) in enumerate(boxes):
        for gx in range(int(bx[0] // STUD), int(bx[1] // STUD) + 1):
            for gy in range(int(bx[2] // STUD), int(bx[3] // STUD) + 1):
                grid[(gx, gy)].append(k)
    hits = set()
    for bucket in grid.values():
        for a in range(len(bucket)):
            for b in range(a + 1, len(bucket)):
                ia, ba = boxes[bucket[a]]
                ib, bb = boxes[bucket[b]]
                if ia != ib and _overlap(ba, bb):
                    hits.add((min(ia, ib), max(ia, ib)))
    return sorted(hits)


def connections(model):
    """Edges (lower, upper) of real stud-in-tube joints, plus SNOT stud joints."""
    edges = set()
    for i, pl in enumerate(model.parts):
        if pl.sideways or pl.z == 0:
            continue
        for c in model.bottom_cells(pl):
            j = model.studs.get((c[0], c[1], pl.z))
            if j is not None and j != i:
                edges.add((j, i))
    for a, b in model.snot_links:
        edges.add((a, b))
    return edges


def check_connectivity(model, edges):
    adj = defaultdict(set)
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    roots = [i for i, pl in enumerate(model.parts) if pl.group == "foundation"]
    seen, stack = set(roots), list(roots)
    while stack:
        n = stack.pop()
        for m in adj[n]:
            if m not in seen:
                seen.add(m)
                stack.append(m)
    floating = [i for i in range(len(model.parts)) if i not in seen]
    return floating


def check_spans(model):
    """Every unsupported cell must be a <=1 stud cantilever or sit in a gap of at
    most MAX_SPAN studs between two supported cells of the same part."""
    bad = []
    for i, pl in enumerate(model.parts):
        if pl.sideways or pl.z == 0:
            continue
        cells = set(pl.cells)
        legs = set(model.bottom_cells(pl))
        sup = {c for c in legs if (c[0], c[1], pl.z) in model.studs}
        if not sup:
            bad.append((i, "no support"))
            continue
        if pl.p.kind == "arch":
            continue  # only the legs are meant to bear
        if not span_ok(cells, sup):
            bad.append((i, "unsupported span or cantilever"))
    return bad


def check_columns(model, edges):
    """A part resting on exactly one part with the identical footprint is a column
    link.  Every column must be tied in at the top by a part that bears on two or
    more supports (e.g. the well canopy over its posts)."""
    below = defaultdict(set)
    above = defaultdict(set)
    for a, b in edges:
        below[b].add(a)
        above[a].add(b)

    def is_link(i):
        if len(below[i]) != 1:
            return False
        j = next(iter(below[i]))
        a, b = model.parts[i], model.parts[j]
        return not a.sideways and not b.sideways and a.cells == b.cells

    def tied(i, depth=0):
        if depth > 50:
            return False
        for k in above[i]:
            if len(below[k]) >= 2:
                return True
            if is_link(k) and tied(k, depth + 1):
                return True
        return False

    links = [i for i in range(len(model.parts)) if is_link(i)]
    untied = [i for i in links if not tied(i)]
    return links, untied


def check_snot(model):
    """5:2 rule: sideways panels must span whole studs across and exactly 5 plates
    (2 studs) vertically, starting on the plate grid."""
    out = []
    for i, pl in enumerate(model.parts):
        if not pl.sideways:
            continue
        p = pl.p
        cx, yb, cz = pl.mm
        height = p.d * STUD
        z0 = cz - height / 2
        rec = {"index": i, "part": pl.part, "group": pl.group, "height_mm": round(height, 3),
               "bottom_on_plate_grid": abs(z0 / PLATE - round(z0 / PLATE)) < 1e-6}
        base = pl.z * PLATE
        if pl.group == "snot_panel":
            rec["plates_spanned"] = round(height / PLATE, 6)
            rec["ok"] = abs(height - 5 * PLATE) < 1e-6 and rec["bottom_on_plate_grid"]
        else:
            # Tiles sit on the sideways plate's stud rows: whole studs above the panel base,
            # and inside the 5-plate panel.
            off = (z0 - base) / STUD
            rec["ok"] = abs(off - round(off)) < 1e-6 and z0 >= base - 1e-6 and z0 + height <= base + 5 * PLATE + 1e-6
        out.append(rec)
    return out


def check_catalog(model):
    problems = []
    for i, pl in enumerate(model.parts):
        if pl.part not in PARTS:
            problems.append((i, f"unknown part {pl.part}"))
            continue
        if pl.part in OBSOLETE or not PARTS[pl.part].active:
            problems.append((i, f"obsolete mold {pl.part}"))
        if not is_available(pl.part, pl.color):
            problems.append((i, f"{pl.part} not stocked in {pl.color}"))
    return problems


def running_bond(model):
    per = []
    total_seams = total_aligned = 0
    for sid, s in enumerate(model.specs):
        reg = s["region"]
        z = s["z"]
        seams = sum(1 for c in reg for n in ((c[0] + 1, c[1]), (c[0], c[1] + 1))
                    if n in reg and model.seam(c, n, z) and model.occ.get((c[0], c[1], z - 1)) is not None
                    and model.occ.get((n[0], n[1], z - 1)) is not None)
        aligned = sorted(model.aligned_seams(sid))
        total_seams += seams
        total_aligned += len(aligned)
        if aligned:
            per.append({"group": s["group"], "z": z, "aligned": [list(map(list, e)) for e in aligned]})
    # Longest continuous vertical joint: consecutive courses whose aligned joints sit
    # on the same cell edge (a "zipper" is the real structural weakness).
    by_edge = defaultdict(list)
    for sid, s in enumerate(model.specs):
        for e in model.aligned_seams(sid):
            by_edge[e].append(s["z"])
    zipper = max((len(v) + 1 for v in by_edge.values()), default=1)
    return {"seams_checked": total_seams, "aligned": total_aligned,
            "longest_vertical_joint_courses": zipper,
            "staggered_pct": round(100.0 * (1 - total_aligned / max(1, total_seams)), 2),
            "aligned_by_layer": per}


def visibility(model):
    """Flag parts that touch outside air (flood fill of empty voxels from the
    bounding box).  Parts that never touch it are concealed."""
    occ = model.occ
    xs = [k[0] for k in occ] + [0]
    ys = [k[1] for k in occ] + [0]
    zs = [k[2] for k in occ]
    x0, x1, y0, y1, z0, z1 = min(xs) - 1, max(xs) + 1, min(ys) - 1, max(ys) + 1, 0, max(zs) + 1
    air = set()
    stack = [(x0, y0, z1)]
    air.add(stack[0])
    while stack:
        x, y, z = stack.pop()
        for n in ((x + 1, y, z), (x - 1, y, z), (x, y + 1, z), (x, y - 1, z), (x, y, z + 1), (x, y, z - 1)):
            if x0 <= n[0] <= x1 and y0 <= n[1] <= y1 and z0 <= n[2] <= z1 and n not in air and n not in occ:
                air.add(n)
                stack.append(n)
    visible = set()
    for (x, y, z), i in occ.items():
        for n in ((x + 1, y, z), (x - 1, y, z), (x, y + 1, z), (x, y - 1, z), (x, y, z + 1)):
            if n in air:
                visible.add(i)
                break
    for i, pl in enumerate(model.parts):
        if pl.sideways or pl.p.kind in ("bracket", "baseplate"):
            visible.add(i)
    return visible


def validate(model):
    edges = connections(model)
    collisions = check_collisions(model)
    floating = check_connectivity(model, edges)
    spans = check_spans(model)
    links, untied = check_columns(model, edges)
    snot = check_snot(model)
    catalog = check_catalog(model)
    bond = running_bond(model)
    dims = {
        "stud_pitch_mm": STUD, "plate_mm": PLATE, "brick_mm": BRICK,
        "brick_equals_3_plates": abs(BRICK - 3 * PLATE) < 1e-9,
        "stud_diameter_mm": STUD_D, "stud_height_mm": STUD_H,
        "sidewall_gap_mm": GAP, "snot_2_studs_equals_5_plates": abs(2 * STUD - 5 * PLATE) < 1e-9,
    }
    name = lambda i: f"{model.parts[i].part}/{model.parts[i].color}/{model.parts[i].group}"
    checks = {
        "dimensions": all(v for k, v in dims.items() if isinstance(v, bool)),
        "catalog_active_molds_and_colors": not catalog,
        "no_collisions": not collisions,
        "all_parts_connected_to_baseplate": not floating,
        "spans_and_cantilevers": not spans,
        "no_untied_single_column_stacks": not untied,
        "snot_5_to_2_alignment": all(r["ok"] for r in snot),
        # Running bond: no vertical joint continues through 3+ courses, and at least
        # 98% of in-course joints are staggered.  Every exception is listed below.
        "running_bond_in_course": bond["longest_vertical_joint_courses"] < 3 and bond["staggered_pct"] >= 98.0,
    }
    report = {
        "model": model.name,
        "parts": len(model.parts),
        "checks": checks,
        "passed": all(checks.values()),
        "dimensions": dims,
        "catalog_problems": [(i, m) for i, m in catalog],
        "collisions": [(name(a), name(b)) for a, b in collisions],
        "floating_parts": [name(i) for i in floating],
        "span_problems": [(name(i), m) for i, m in spans],
        "column_links": len(links),
        "untied_columns": [name(i) for i in untied],
        "snot": snot,
        "running_bond": bond,
        "connections": len(edges),
    }
    return report
