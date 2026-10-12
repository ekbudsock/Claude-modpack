"""Procedural caravanserai layout on the LEGO grid.

All positions are integers: x/y in studs, z in plates.  A part's (x, y) is the
minimum-corner cell of its footprint after rotation.  Nothing in this module
imports Blender.

Every course is filled by ``Model.fill``: an exact depth-first search with
conflict-directed backjumping that tries the largest element first and rejects
any placement that

* puts a vertical joint directly on a joint in the course below or above,
* repeats the part below exactly (a "column"),
* leaves a stud unsupported beyond a 4-stud span or a 1-stud cantilever,
* or leaves the next course a junction it cannot bridge (lookahead).

If a course has no perfect tiling, a scored greedy fallback minimises the same
faults, and ``repair_seams`` then re-solves small windows, alone or jointly
with the course below and/or above, until the bond is clean.
"""

import random
import time
from dataclasses import dataclass, field

from .catalog import PARTS, PLATE, STUD, sizes_for

C1 = "01_Baseplate_Foundation"
C2 = "02_Structural_Core"
C3 = "03_Exterior_Facade"
C4 = "04_Roof_Details"
COLLECTIONS = (C1, C2, C3, C4)

MAX_SPAN = 4  # studs of unsupported plate allowed between two supports


@dataclass
class Placement:
    part: str
    color: str
    x: int
    y: int
    z: int
    rot: int = 0
    collection: str = C2
    group: str = ""
    spec: int = None              # index of the tiled layer this part came from
    # Sideways (SNOT) parts are positioned in millimetres instead of on the grid.
    sideways: bool = False
    mm: tuple = None              # (x_center, y_back_face, z_center) for sideways parts
    cells: frozenset = field(default=frozenset(), repr=False)

    @property
    def p(self):
        return PARTS[self.part]

    def dims(self):
        p = self.p
        return (p.w, p.d) if self.rot in (0, 180) else (p.d, p.w)


def local_to_world(p, x, y, rot, lx, ly):
    if rot == 0:
        return x + lx, y + ly
    if rot == 90:
        return x + (p.d - 1 - ly), y + lx
    if rot == 180:
        return x + (p.w - 1 - lx), y + (p.d - 1 - ly)
    if rot == 270:
        return x + ly, y + (p.w - 1 - lx)
    raise ValueError(rot)


def _nbrs(c):
    x, y = c
    return ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))


def _edge(a, b):
    return (a, b) if a < b else (b, a)


def _components(cells):
    """4-connected components of a cell set."""
    out, seen = [], set()
    for c0 in sorted(cells):
        if c0 in seen:
            continue
        comp, stack = set(), [c0]
        seen.add(c0)
        while stack:
            c = stack.pop()
            comp.add(c)
            for n in _nbrs(c):
                if n in cells and n not in seen:
                    seen.add(n)
                    stack.append(n)
        out.append(comp)
    return out


def _axis_ok(v, supports):
    """v lies on a support line, within a <=MAX_SPAN gap between two support lines,
    or one stud past the outermost one (cantilever)."""
    if v in supports:
        return True
    lo = max((s for s in supports if s < v), default=None)
    hi = min((s for s in supports if s > v), default=None)
    if lo is not None and hi is not None and hi - lo - 1 <= MAX_SPAN:
        return True
    return (lo is not None and v - lo == 1) or (hi is not None and hi - v == 1)


def span_ok(cells, sup):
    """A plate or brick is stiff in both directions, so each unsupported cell must be
    bridged (or cantilevered by one stud) between support lines along X *and* Y."""
    if not sup:
        return False
    xs = {q[0] for q in sup}
    ys = {q[1] for q in sup}
    return all(_axis_ok(q[0], xs) and _axis_ok(q[1], ys) for q in cells if q not in sup)


class LayoutError(RuntimeError):
    pass


class Model:
    def __init__(self, name, base_size, seed=7):
        self.name = name
        self.base_size = base_size
        self.parts = []
        self.occ = {}      # (x, y, z) -> part index
        self.studs = {}    # (x, y, z) -> part index; stud whose base is at level z
        self.snot_links = []  # (holder index, held index) for sideways connections
        self.rng = random.Random(seed)
        self.specs = []    # tiled layers: dict(z, h, kind, color, collection, group, region)
        self.fill_stats = []

    # -- placement -----------------------------------------------------------
    def add(self, pl):
        p = pl.p
        idx = len(self.parts)
        if pl.sideways:
            self.parts.append(pl)
            return idx
        cells = frozenset(local_to_world(p, pl.x, pl.y, pl.rot, lx, ly) for lx, ly in p.cells())
        for (cx, cy) in cells:
            for k in range(p.h):
                key = (cx, cy, pl.z + k)
                if key in self.occ:
                    other = self.parts[self.occ[key]]
                    raise LayoutError(f"collision at {key}: {pl.part} vs {other.part} ({other.group})")
        pl.cells = cells
        self.parts.append(pl)
        for (cx, cy) in cells:
            for k in range(p.h):
                self.occ[(cx, cy, pl.z + k)] = idx
        for lx, ly in p.top_cells():
            cx, cy = local_to_world(p, pl.x, pl.y, pl.rot, lx, ly)
            self.studs[(cx, cy, pl.z + p.h)] = idx
        return idx

    def remove(self, idx):
        pl = self.parts[idx]
        p = pl.p
        for (cx, cy) in pl.cells:
            for k in range(p.h):
                del self.occ[(cx, cy, pl.z + k)]
        for lx, ly in p.top_cells():
            cx, cy = local_to_world(p, pl.x, pl.y, pl.rot, lx, ly)
            del self.studs[(cx, cy, pl.z + p.h)]
        self.parts[idx] = None
        return pl

    def place(self, part, color, x, y, z, rot=0, collection=C2, group="", spec=None):
        pl = Placement(part, color, x, y, z, rot, collection, group)
        pl.spec = spec
        return self.add(pl)

    def compact(self):
        """Drop parts removed during seam repair and renumber references."""
        remap, kept = {}, []
        for i, pl in enumerate(self.parts):
            if pl is not None:
                remap[i] = len(kept)
                kept.append(pl)
        self.parts = kept
        self.occ = {k: remap[v] for k, v in self.occ.items()}
        self.studs = {k: remap[v] for k, v in self.studs.items()}
        self.snot_links = [(remap[a], remap[b]) for a, b in self.snot_links]

    def bottom_cells(self, pl):
        p = pl.p
        return [local_to_world(p, pl.x, pl.y, pl.rot, lx, ly) for lx, ly in p.base_cells()]

    # -- seams ---------------------------------------------------------------
    def seam(self, a, b, level):
        """True if cells a and b are covered by two different parts at this level."""
        pa = self.occ.get((a[0], a[1], level))
        pb = self.occ.get((b[0], b[1], level))
        return pa is not None and pb is not None and pa != pb

    def aligned_seams(self, spec_id):
        """Seam edges inside a tiled course that sit directly on a seam one level down.

        Only joints *within* the course count; where a course butts against a
        different feature (a tower rising past the wall cap, an arch, a merlon)
        the joint is a boundary and no single course could bridge it."""
        s = self.specs[spec_id]
        z = s["z"]
        reg = s["region"]
        out = set()
        for c in reg:
            for n in ((c[0] + 1, c[1]), (c[0], c[1] + 1)):
                if n in reg and self.seam(c, n, z) and self.seam(c, n, z - 1):
                    out.add(_edge(c, n))
        return out

    # -- tiler ---------------------------------------------------------------
    def _solver(self, z, h, kind, color, need_support, next_cells=None, next_spec=None):
        """Build the constraint helpers for tiling cells at level z..z+h-1."""
        cands, seen = [], set()
        for p in sizes_for(kind, color):
            for (w, d, rot) in ((p.w, p.d, 0), (p.d, p.w, 90)):
                if (w, d) not in seen:
                    seen.add((w, d))
                    cands.append((p.id, w, d, rot))
        model = self

        def forbidden(a, b):
            # A new seam may not sit on a seam directly below or directly above.
            return model.seam(a, b, z - 1) or model.seam(a, b, z + h)

        def supported(c):
            return (c[0], c[1], z) in model.studs

        def span_ok_(csset):
            return span_ok(csset, {q for q in csset if supported(q)})

        small_first = sorted(cands, key=lambda c: c[1] * c[2])

        def coverable(n, region, taken):
            # Smallest parts first: a short strip reaching a support is the usual witness.
            for _, w, d, _ in small_first:
                for ox in range(w):
                    for oy in range(d):
                        x0, y0 = n[0] - ox, n[1] - oy
                        ok = True
                        for i in range(w):
                            for j in range(d):
                                q = (x0 + i, y0 + j)
                                if q not in region or q in taken:
                                    ok = False
                                    break
                            if not ok:
                                break
                        if ok and span_ok_({(x0 + i, y0 + j) for i in range(w) for j in range(d)}):
                            return True
            return False

        def column(csset):
            for level in (z - 1, z + h):
                ids = {model.occ.get((q[0], q[1], level)) for q in csset}
                if len(ids) == 1 and None not in ids:
                    other = model.parts[next(iter(ids))]
                    if other.cells == csset:
                        return True
            return False

        def evaluate(c, w, d, covered, region):
            """None if the part can't go here, else (cells, aligned seams, column)."""
            cs = frozenset((c[0] + i, c[1] + j) for i in range(w) for j in range(d))
            if any(q not in region or q in covered for q in cs):
                return None
            if need_support:
                if not span_ok_(cs):
                    return None
                taken = covered | cs
                for q in cs:
                    for n in _nbrs(q):
                        if n in region and n not in taken and not supported(n) and not coverable(n, region, taken):
                            return None  # would strand an unsupported cell
            hits = 0
            for q in cs:
                for n in _nbrs(q):
                    if n in cs:
                        continue
                    if n not in region:
                        continue  # boundary with an opening or a fixed feature (arch side,
                                  # tower face): no single course can bridge those
                    if n in covered:
                        continue  # counted when that neighbour was placed
                    if forbidden(q, n):
                        hits += 1
            return cs, hits, 1 if column(cs) else 0

        def scan(region, colmajor):
            return sorted(region, key=(lambda c: (c[0], c[1])) if colmajor else (lambda c: (c[1], c[0])))

        nk, ncol = next_spec or (kind, color)
        next_dims = sorted({(p.w, p.d) for p in sizes_for(nk, ncol)} | {(p.d, p.w) for p in sizes_for(nk, ncol)},
                           key=lambda wd: wd[0] * wd[1])
        top = z + h - 1

        def joint(a, b, owner, cur):
            """Is there a joint between a and b in the course being tiled?  A placed
            cell next to a still-empty cell of the course is a certain joint: that
            neighbour will belong to another part."""
            ia = owner.get(a, model.occ.get((a[0], a[1], top)))
            ib = owner.get(b, model.occ.get((b[0], b[1], top)))
            if ia is None and ib is None:
                return False
            if ia is None:
                return a in cur
            if ib is None:
                return b in cur
            return ia != ib

        def bridgeable(q, owner, region, cur):
            """Exact local lookahead: can the next course still cover q with one part
            that sits on no joint of this course and doesn't repeat a part exactly?
            Cells not yet tiled count as joint-free (optimistic)."""
            if q not in region:
                return True   # the next course has an opening here
            if sum(1 for n in _nbrs(q) if n in region and joint(q, n, owner, cur)) < 2:
                return True   # a straight part through q always exists
            for w, d in next_dims:
                for ox in range(w):
                    for oy in range(d):
                        cs = [(q[0] - ox + i, q[1] - oy + j) for i in range(w) for j in range(d)]
                        if any(c not in region for c in cs):
                            continue
                        css = set(cs)
                        if any(joint(c, n, owner, cur) for c in cs for n in _nbrs(c) if n in region and n not in css):
                            continue
                        ids = {owner.get(c) for c in cs}
                        if len(ids) == 1 and None not in ids and len(css) > 1 and \
                                css == {c for c, k in owner.items() if k == next(iter(ids))}:
                            continue  # would repeat the part below exactly (a column)
                        return True
            return False

        def exact(region, colmajor, limit, lookahead=True):
            nxt = region if next_cells is None else next_cells
            order = scan(region, colmajor)
            covered, chosen, owner = set(), [], {}
            budget = [limit]

            BUDGET = "budget"

            def near(c, k):
                """Earlier decisions whose parts lie within three studs of c."""
                out = set()
                for dx in range(-3, 4):
                    for dy in range(-3, 4):
                        j = owner.get((c[0] + dx, c[1] + dy))
                        if j is not None and j < k:
                            out.add(j)
                return out

            def rec(i):
                # Conflict-directed backjumping: returns True on success, BUDGET when out
                # of nodes, else the set of earlier decisions the dead end depends on.
                while i < len(order) and order[i] in covered:
                    i += 1
                if i == len(order):
                    return True
                budget[0] -= 1
                if budget[0] < 0:
                    return BUDGET
                c = order[i]
                k = len(chosen)
                conflicts = near(c, k)
                for pid, w, d, rot in cands:
                    ev = evaluate(c, w, d, covered, region)
                    # A 2-stud stub (e.g. a corner cell pinned by an arch leg) may repeat the
                    # part below; the course above ties it in, which validation verifies.
                    if ev is None or ev[1] or (ev[2] and len(region) > 2):
                        continue
                    for q in ev[0]:
                        owner[q] = k
                    ok = True
                    if lookahead:
                        touched = set(ev[0]) | {n for q in ev[0] for n in _nbrs(q) if n in owner}
                        ok = all(bridgeable(q, owner, nxt, region) for q in touched)
                    r = None
                    if ok:
                        covered.update(ev[0])
                        chosen.append((pid, c, rot))
                        r = rec(i + 1)
                        if r is True:
                            return True
                        covered.difference_update(ev[0])
                        chosen.pop()
                    for q in ev[0]:
                        del owner[q]
                    if r is BUDGET:
                        return BUDGET
                    if r is not None:
                        if k not in r:
                            return r      # the dead end below doesn't depend on this choice
                        conflicts |= r - {k}
                return conflicts

            return list(chosen) if rec(0) is True else None

        def greedy(region, n_restarts):
            """Fallback when no perfect tiling exists: minimise aligned joints, columns
            and joints the next course can't bridge, preferring large parts."""
            nxt = region if next_cells is None else next_cells
            best = None
            for r in range(n_restarts):
                covered, chosen, owner = set(), [], {}
                hits_total = cols_total = 0
                noise = 0.0 if r == 0 else (1.5 if r % 2 else 4.0)
                ok = True
                for c in scan(region, (z + r) % 2 == 1):
                    if c in covered:
                        continue
                    pick = None
                    k = len(chosen)
                    for pid, w, d, rot in cands:
                        ev = evaluate(c, w, d, covered, region)
                        if ev is None:
                            continue
                        for q in ev[0]:
                            owner[q] = k
                        touched = set(ev[0]) | {n for q in ev[0] for n in _nbrs(q) if n in owner}
                        stuck = sum(1 for q in touched if not bridgeable(q, owner, nxt, region))
                        for q in ev[0]:
                            del owner[q]
                        score = (w * d - 9.0 * (ev[1] + stuck) - 6.0 * ev[2]
                                 + model.rng.random() * noise)
                        if pick is None or score > pick[0]:
                            pick = (score, pid, rot, ev)
                    if pick is None:
                        ok = False
                        break
                    _, pid, rot, (cs, hits, col) = pick
                    covered.update(cs)
                    for q in cs:
                        owner[q] = k
                    chosen.append((pid, c, rot))
                    hits_total += hits
                    cols_total += col
                if not ok:
                    continue
                n_small = sum(1 for pid, _, _ in chosen if PARTS[pid].w * PARTS[pid].d == 1)
                cost = hits_total * 10 + cols_total * 8 + len(chosen) + 2 * n_small
                if best is None or cost < best[0]:
                    best = (cost, chosen)
            return best[1] if best else None

        return exact, greedy

    def fill(self, cells, z, kind, color, collection, group, need_support=True, next_cells=None, next_spec=None):
        h = 3 if kind == "brick" else 1
        free = {c for c in cells if all((c[0], c[1], z + k) not in self.occ for k in range(h))}
        if not free:
            return []
        spec_id = len(self.specs)
        self.specs.append(dict(z=z, h=h, kind=kind, color=color, collection=collection,
                               group=group, region=frozenset(free), need_support=need_support))
        exact, greedy = self._solver(z, h, kind, color, need_support,
                                     None if next_cells is None else set(next_cells), next_spec)
        out, method = [], "exact"
        for region in _components(free):
            sol = exact(region, z % 2 == 1, 300 + 8 * len(region))
            if sol is None:
                sol = exact(region, z % 2 == 1, 300 + 4 * len(region), lookahead=False)
            if sol is None:
                sol = greedy(region, 16 if len(region) < 120 else 6)
                method = "greedy"
            if sol is None:
                raise LayoutError(f"cannot fill {group} layer z={z} ({len(region)} cells, {color} {kind})")
            for pid, c, rot in sol:
                out.append(self.place(pid, color, c[0], c[1], z, rot, collection, group, spec_id))
        self.fill_stats.append({"group": group, "z": z, "parts": len(out), "method": method})
        return out

    def _retile(self, spec_ids, window):
        """Remove the parts of the given stacked layers that touch `window` and
        re-solve the patch bottom-up with exact search, holding everything else
        fixed.  Rolls back completely if any layer has no seam-free solution."""
        # Grow the window until it covers every part it touches in every layer of
        # the stack, so the patch boundary never inherits a joint from outside.
        window = set(window)
        victims = {}
        for _ in range(6):
            grown = set(window)
            for sid in spec_ids:
                z = self.specs[sid]["z"]
                ids = {self.occ.get((c[0], c[1], z)) for c in window}
                victims[sid] = sorted(i for i in ids if i is not None
                                      and getattr(self.parts[i], "spec", None) == sid)
                for i in victims[sid]:
                    grown |= self.parts[i].cells
            if grown == window or len(grown) > 400:
                break
            window = grown
        removed = {sid: [(i, self.remove(i)) for i in victims[sid]] for sid in spec_ids}
        if not any(removed.values()):
            return False
        placed = []
        ok = True
        for k, sid in enumerate(spec_ids):
            s = self.specs[sid]
            if not removed[sid]:
                continue
            patch = set().union(*(pl.cells for _, pl in removed[sid]))
            nxt = self.specs[spec_ids[k + 1]]["region"] if k + 1 < len(spec_ids) else None
            nspec = self.specs[spec_ids[k + 1]] if k + 1 < len(spec_ids) else None
            exact, _ = self._solver(s["z"], s["h"], s["kind"], s["color"], s["need_support"],
                                    None if nxt is None else set(nxt),
                                    None if nspec is None else (nspec["kind"], nspec["color"]))
            for region in _components(patch):
                sol = None
                for colmajor in (True, False):
                    # Lower layers of a joint repair look ahead so the next one can bridge.
                    sol = exact(region, colmajor, 400 + 25 * len(region), lookahead=k < len(spec_ids) - 1)
                    if sol is not None:
                        break
                if sol is None:
                    ok = False
                    break
                for pid, c, rot in sol:
                    placed.append(self.place(pid, s["color"], c[0], c[1], s["z"], rot,
                                             s["collection"], s["group"], sid))
            if not ok:
                break
        if ok:
            return True
        for i in placed:
            self.remove(i)
        for sid in spec_ids:
            for i, pl in removed[sid]:
                self.parts[i] = pl
                self._reinsert(i)
        return False

    def _reinsert(self, idx):
        pl = self.parts[idx]
        p = pl.p
        for (cx, cy) in pl.cells:
            for k in range(p.h):
                self.occ[(cx, cy, pl.z + k)] = idx
        for lx, ly in p.top_cells():
            cx, cy = local_to_world(p, pl.x, pl.y, pl.rot, lx, ly)
            self.studs[(cx, cy, pl.z + p.h)] = idx

    def _neighbour_spec(self, edge, level):
        out = set()
        for c in edge:
            i = self.occ.get((c[0], c[1], level))
            if i is not None and getattr(self.parts[i], "spec", None) is not None:
                out.add(self.parts[i].spec)
        return out

    def repair_seams(self, spec_ids, rounds=3, time_limit=240):
        """Large-neighbourhood search: clear every aligned seam by re-tiling a small
        window of its own course, or jointly with the course below and/or above."""
        spec_set = set(spec_ids)
        t_end = time.time() + time_limit
        for _ in range(rounds):
            todo = [(sid, e) for sid in spec_ids for e in sorted(self.aligned_seams(sid))]
            if not todo:
                break
            progress = False
            for sid, e in todo:
                if time.time() > t_end:
                    break
                if e not in self.aligned_seams(sid):
                    continue
                s = self.specs[sid]
                lower = sorted(self._neighbour_spec(e, s["z"] - 1) & spec_set)
                upper = sorted(self._neighbour_spec(e, s["z"] + s["h"]) & spec_set)
                plans = [([sid], 1), ([sid], 2), ([sid], 3)]
                plans += [([lo, sid], r) for lo in lower for r in (2, 3)]
                plans += [([sid, up], r) for up in upper for r in (2, 3)]
                plans += [([lo, sid, up], 3) for lo in lower for up in upper]
                if s["kind"] == "plate":
                    # Plate decks are a handful of big parts: re-solve the whole layer.
                    plans += [([sid], 6), ([sid], 64)]
                    plans += [([lo, sid], r) for lo in lower for r in (5, 8)]
                for stack, radius in plans:
                    reg = set().union(*(self.specs[t]["region"] for t in stack))
                    window = {c for c in reg if min(abs(c[0] - q[0]) + abs(c[1] - q[1]) for q in e) <= radius}
                    # A successful re-solve has zero aligned seams inside the patch.
                    if self._retile(stack, window):
                        progress = True
                        break
            if not progress:
                break
        return sum(len(self.aligned_seams(sid)) for sid in spec_ids)

    def merlons(self, path, z, color, collection, group):
        """Crenellation: two-stud merlon, one-stud gap, along an ordered path.
        A one-stud stub gets no merlon: a 1 x 1 on a 1 x 1 would be an untied column."""
        if len(path) < 2:
            return
        i = 0
        while i < len(path):
            a = path[i]
            b = path[i + 1] if i + 1 < len(path) else None
            if b is not None and abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1:
                x, y = min(a[0], b[0]), min(a[1], b[1])
                rot = 0 if a[1] == b[1] else 90
                self.place("3004", color, x, y, z, rot, collection, group)
            else:
                self.place("3005", color, a[0], a[1], z, 0, collection, group)
            i += 3


# --------------------------------------------------------------------------
# Caravanserai
# --------------------------------------------------------------------------

SIZES = {
    "small": dict(base=12, N=12, t=1, rd=0, T=2, gate=2, pishtaq=6, pishtaq_depth=1,
                  schedule="PBBB", tower_extra=2, snot=0, label="Small (12 x 12)"),
    "medium": dict(base=16, N=16, t=1, rd=2, T=3, gate=4, pishtaq=8, pishtaq_depth=2,
                   schedule="PBBPBB", tower_extra=2, snot=4, label="Medium (16 x 16)"),
    "large": dict(base=32, N=30, t=2, rd=3, T=6, gate=4, pishtaq=10, pishtaq_depth=2,
                  schedule="PBBPBBB", tower_extra=2, snot=8, label="Large (32 x 32)"),
}

WALL = "Tan"
TRIM = "Dark Tan"


def _layers(schedule):
    z = 1
    out = []
    for ch in schedule:
        out.append((z, "brick" if ch == "B" else "plate"))
        z += 3 if ch == "B" else 1
    return out, z


def _pack_arches(a, b, pier, mirror=False):
    L = b - a + 1
    n = 0
    while 4 * (n + 1) + pier * n <= L:
        n += 1
    if n == 0:
        return []
    total = 4 * n + pier * (n - 1)
    start = a + (L - total) // 2 if not mirror else b - total + 1 - (L - total) // 2
    return [start + k * (4 + pier) for k in range(n)]


def build_caravanserai(size, seed=7):
    cfg = SIZES[size]
    B, N, t, rd, T = cfg["base"], cfg["N"], cfg["t"], cfg["rd"], cfg["T"]
    m = (B - N) // 2
    gw = cfg["gate"]
    g0 = N // 2 - gw // 2
    model = Model(f"caravanserai_{size}", B, seed)
    model.cfg = cfg

    def W(c):  # relative building cell -> world cell
        return (c[0] + m, c[1] + m)

    def depth(c):
        x, y = c
        return min(x, y, N - 1 - x, N - 1 - y)

    allc = [(x, y) for x in range(N) for y in range(N)]
    in_tower = lambda c: (c[0] < T or c[0] >= N - T) and (c[1] < T or c[1] >= N - T)

    def tower_hollow(c):
        if not in_tower(c) or T - 2 * t < 2:
            return False
        lx = c[0] if c[0] < T else N - 1 - c[0]
        ly = c[1] if c[1] < T else N - 1 - c[1]
        return t <= lx < T - t and t <= ly < T - t

    outer = {c for c in allc if depth(c) < t}
    towers = {c for c in allc if in_tower(c) and not tower_hollow(c)}
    inner_idx = t + rd
    inner = {c for c in allc if rd > 0 and depth(c) == inner_idx}
    court_min = inner_idx + 1 if rd > 0 else t

    # Sides map (s, d) -> cell: front, back, left, right.
    sides = {
        "front": lambda s, d: (s, d),
        "back": lambda s, d: (s, N - 1 - d),
        "left": lambda s, d: (d, s),
        "right": lambda s, d: (N - 1 - d, s),
    }

    layers, z_top = _layers(cfg["schedule"])
    brick_z = [z for z, k in layers if k == "brick"]
    big_arch = gw == 4
    gate_arch_part = "15254" if big_arch else "3659"
    gate_arch_z = brick_z[-2] if big_arch else brick_z[-1]
    arcade_z = brick_z[-1]

    # ---- openings and fixed parts ------------------------------------------
    openings = {}    # cell -> top z (exclusive) of the void
    fixed = []       # (Placement) placed before the tiler runs
    partitions = set()

    # Gate: through the outer wall, the room passage and the inner wall.
    gate_rows = list(range(0, t)) + ([inner_idx] if rd > 0 else [])
    for y in range(0, inner_idx + (1 if rd > 0 else 0)):
        for x in range(g0, g0 + gw):
            openings[(x, y)] = gate_arch_z
    for y in gate_rows:
        fixed.append(Placement(gate_arch_part, WALL, g0 - 1 + m, y + m, gate_arch_z, 0, C3, "gate_arch"))
    if rd > 0:
        for y in range(t, inner_idx):
            partitions.add((g0 - 1, y))
            partitions.add((g0 + gw, y))

    # Arcades (iwans) on the inner wall, with a partition behind each pier.
    if rd > 0:
        a, b = inner_idx + 1, N - 2 - inner_idx
        pier = 1 if (b - a + 1) >= 14 else 0
        for side, f in sides.items():
            # Keep a solid pier of at least one stud at each corner of the inner ring:
            # an arch leg on both sides of a corner cell leaves a joint nothing can bridge.
            if side == "front":
                starts = _pack_arches(a + 1, g0 - 2, pier) + _pack_arches(g0 + gw + 1, b - 1, pier, mirror=True)
            else:
                starts = _pack_arches(a + 1, b - 1, pier)
            for k, s0 in enumerate(starts):
                cells = [f(s0 + i, inner_idx) for i in range(4)]
                x0, y0 = min(c[0] for c in cells), min(c[1] for c in cells)
                rot = 0 if side in ("front", "back") else 90
                fixed.append(Placement("3659", WALL, x0 + m, y0 + m, arcade_z, rot, C3, "arcade_arch"))
                for i in (1, 2):
                    openings[f(s0 + i, inner_idx)] = arcade_z
                if side != "front" and k < len(starts) - 1:
                    ps = s0 + 4 if pier else s0 + 3
                    for d in range(t, inner_idx):
                        partitions.add(f(ps, d))

    wall_cells = (outer | towers | inner | partitions)

    # ---- 01 foundation -------------------------------------------------------
    if B == 12:
        model.place("3028", "Tan", 0, 0, 0, 90, C1, "foundation")
        model.place("3028", "Tan", 6, 0, 0, 90, C1, "foundation")
    elif B == 16:
        model.place("91405", "Tan", 0, 0, 0, 0, C1, "foundation")
    else:
        model.place("3811", "Tan", 0, 0, 0, 0, C1, "foundation")

    for pl in fixed:
        model.add(pl)

    # ---- walls, layer by layer -------------------------------------------------
    masks = []
    for (z, kind) in layers:
        mask = set()
        for c in wall_cells:
            top = openings.get(c)
            if top is not None and z < top:
                continue
            mask.add(W(c))
        masks.append(mask)
    p0 = N // 2 - cfg["pishtaq"] // 2
    pish = {(x, y) for x in range(p0, p0 + cfg["pishtaq"]) for y in range(cfg["pishtaq_depth"])}
    if rd > 0:
        top_mask = {W(c) for c in allc if depth(c) <= inner_idx}
    else:
        top_mask = {W(c) for c in outer if c not in towers}
    spec_of = {"plate": ("plate", TRIM), "brick": ("brick", WALL)}
    top_spec = ("plate", WALL) if rd > 0 else ("plate", TRIM)
    for k, (z, kind) in enumerate(layers):
        nxt = masks[k + 1] if k + 1 < len(masks) else top_mask
        nspec = spec_of[layers[k + 1][1]] if k + 1 < len(layers) else top_spec
        if kind == "plate":
            model.fill(masks[k], z, "plate", TRIM, C3, "plinth" if z == 1 else "band",
                       next_cells=nxt, next_spec=nspec)
        else:
            model.fill(masks[k], z, "brick", WALL, C2, "wall", next_cells=nxt, next_spec=nspec)

    # ---- courtyard paving + well (01 / 03) -----------------------------------
    wc = N // 2 - 2
    well = {(wc + i, wc + j) for i in range(4) for j in range(4)}
    water = {(wc + i, wc + j) for i in (1, 2) for j in (1, 2)}
    apron = {(wc + i, wc + j) for i in range(-1, 5) for j in range(-1, 5)} - well
    # Paved path from the threshold of the gate, through the passage, to the well.
    path = set()
    for y in range(0, wc):
        for x in range(g0, g0 + gw):
            if (x, y) not in wall_cells or (x, y) in openings:
                path.add((x, y))
    paving = {W(c) for c in (path | apron) if c not in well}
    model.fill(paving, 1, "tile", "Light Bluish Gray", C1, "paving", need_support=True)

    for c in water:
        model.place("98138", "Trans-Light Blue", *W(c), 1, 0, C3, "well_water")
    ring = {W(c) for c in well - water}
    model.fill(ring, 1, "brick", "Dark Bluish Gray", C3, "well")
    model.fill(ring, 4, "brick", "Dark Bluish Gray", C3, "well")
    corners = [W((wc, wc)), W((wc + 3, wc)), W((wc, wc + 3)), W((wc + 3, wc + 3))]
    for z in (7, 10):
        for c in corners:
            model.place("3062b", "Reddish Brown", c[0], c[1], z, 0, C3, "well_post")
    wx, wy = W((wc, wc))
    model.place("3031", "Reddish Brown", wx, wy, 13, 0, C3, "well_roof")
    # Gable roof: front pair rises toward +Y, back pair toward -Y; studs meet on the ridge.
    model.place("3039", "Reddish Brown", wx, wy, 14, 0, C3, "well_roof")
    model.place("3039", "Reddish Brown", wx + 2, wy, 14, 0, C3, "well_roof")
    model.place("3039", "Reddish Brown", wx, wy + 2, 14, 180, C3, "well_roof")
    model.place("3039", "Reddish Brown", wx + 2, wy + 2, 14, 180, C3, "well_roof")

    # ---- roof / wall-walk -------------------------------------------------------
    # Merlons are placed before the layer they stand on is tiled, so the tiler can
    # see them and never puts a merlon on an identical part (a column).
    crest_z = z_top + 4 if rd > 0 else z_top + 1
    for side, f in sides.items():
        run = []
        for s in range(N):
            c = f(s, 0)
            if c in towers or c in pish:
                if run:
                    model.merlons([W(q) for q in run], crest_z, WALL, C4, "merlon")
                run = []
            else:
                run.append(c)
        if run:
            model.merlons([W(q) for q in run], crest_z, WALL, C4, "merlon")
    if rd > 0:
        deck = {W(c) for c in allc if depth(c) <= inner_idx}
        model.fill(deck, z_top, "plate", WALL, C4, "roof_deck")
        trim = {W(c) for c in inner}
        model.fill(trim, z_top + 1, "tile", TRIM, C4, "roof_trim")
        parapet = {W(c) for c in allc if depth(c) == 0 and c not in towers and c not in pish}
        model.fill(parapet, z_top + 1, "brick", WALL, C4, "parapet")
    else:
        cap = {W(c) for c in outer if c not in towers}
        model.fill(cap, z_top, "plate", TRIM, C4, "wall_cap")

    # ---- corner towers above the wall-walk ------------------------------------
    tz = z_top + (1 if rd > 0 else 0)
    tower_cells = {W(c) for c in towers}
    cap_z = tz + 3 * cfg["tower_extra"]
    for cx, cy in ((0, 0), (N - T, 0), (0, N - T), (N - T, N - T)):
        loop = ([(cx + i, cy) for i in range(T)] + [(cx + T - 1, cy + j) for j in range(1, T)] +
                [(cx + T - 1 - i, cy + T - 1) for i in range(1, T)] + [(cx, cy + T - 1 - j) for j in range(1, T - 1)])
        model.merlons([W(q) for q in loop], cap_z + 1, WALL, C4, "tower_merlon")
    for k in range(cfg["tower_extra"]):
        model.fill(tower_cells, tz + 3 * k, "brick", WALL, C4, "tower")
    solid = {W(c) for c in allc if in_tower(c)}
    model.fill(solid, cap_z, "plate", TRIM, C4, "tower_cap")

    # ---- gateway (pishtaq) with SNOT tile panel --------------------------------
    pz = z_top + 1
    pish_w = {W(c) for c in pish}
    top = pz + (5 + (3 if size == "large" else 0) if cfg["snot"] else 3)
    front = sorted((c for c in pish_w if c[1] == m), key=lambda c: c[0])
    model.merlons(front, top + 1, WALL, C3, "pishtaq_merlon")
    if cfg["snot"]:
        sw = cfg["snot"]
        sx0 = N // 2 - sw // 2
        brackets = []
        for i in range(0, sw, 2):
            brackets.append(model.place("99781", WALL, sx0 + i + m, m, pz, 0, C3, "snot_bracket"))
        model.fill(pish_w, pz, "plate", WALL, C3, "pishtaq")
        model.fill(pish_w, pz + 1, "plate", WALL, C3, "pishtaq")
        model.fill(pish_w, pz + 2, "brick", WALL, C3, "pishtaq")
        _snot_panel(model, sx0 + m, m, pz, sw, brackets)
        if size == "large":
            model.fill(pish_w, pz + 5, "brick", WALL, C3, "pishtaq")
    else:
        model.fill(pish_w, pz, "brick", WALL, C3, "pishtaq")
    model.fill(pish_w, top, "plate", TRIM, C3, "pishtaq_cap")

    # ---- running-bond repair across every tiled layer ---------------------------
    model.residual_aligned = model.repair_seams(list(range(len(model.specs))))
    model.compact()
    model.z_top = z_top
    return model


def _snot_panel(model, x0, y_face_cell, zb, width, brackets):
    """Sideways tile panel held by 99781 brackets.

    Bracket vertical plates hang 3.2 mm in front of the wall face with studs
    4.0 mm above the bracket base.  A 2 x 4 plate turned sideways hooks onto
    that stud row and spans 2 studs = 16.0 mm = exactly 5 plates (5:2 rule),
    so its top lands flush on the plate grid at zb + 5.
    """
    face = y_face_cell * STUD
    z0 = zb * PLATE
    plates = []
    for i in range(0, width, 4):
        pl = Placement("3020", "Medium Azure", 0, 0, zb, 0, C3, "snot_panel", sideways=True,
                       mm=((x0 + i + 2) * STUD, face - 3.2, z0 + 8.0))
        idx = model.add(pl)
        plates.append((idx, x0 + i, x0 + i + 4))
        for b in brackets:
            bx = model.parts[b].x
            if x0 + i <= bx < x0 + i + 4:
                model.snot_links.append((b, idx))
    # Two rows of tiles; on wide panels the top row bridges the plate seam.
    if width == 4:
        rows = [[(0, 2, "Medium Azure"), (2, 2, "White")], [(0, 2, "White"), (2, 2, "Medium Azure")]]
    else:
        rows = [[(0, 4, "Medium Azure"), (4, 4, "Medium Azure")],
                [(0, 2, "White"), (2, 4, "Medium Azure"), (6, 2, "White")]]
    for r, row in enumerate(rows):
        for (ox, w, color) in row:
            pid = "3069b" if w == 2 else "2431"
            pl = Placement(pid, color, 0, 0, zb, 0, C3, "snot_tile", sideways=True,
                           mm=((x0 + ox + w / 2) * STUD, face - 6.4, z0 + 4.0 + 8.0 * r))
            idx = model.add(pl)
            for (pidx, a, b) in plates:
                if x0 + ox < b and x0 + ox + w > a:
                    model.snot_links.append((pidx, idx))
