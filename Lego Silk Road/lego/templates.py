"""Reusable procedural part meshes and ABS materials (requires bpy).

Each catalogue part gets one template mesh, built once in millimetres and
scaled to metres (1 BU = 1 m).  Every placed brick links that shared mesh, so
Cycles instances the geometry instead of duplicating it.

The 0.2 mm micro-bevel is a real Bevel modifier, evaluated once on the template
and baked into the shared mesh (a live modifier on every instance would defeat
instancing and multiply memory by the part count).
"""

import math

import bmesh
import bpy
from mathutils import Matrix

from .catalog import BEVEL, BRICK, COLORS, INSET, PARTS, PLATE, STUD, STUD_D, STUD_H

MM = 0.001
SEGS = 20            # stud / tube facets
WALL_T = 1.2         # underside wall thickness (mm)
TOP_T = 1.0          # top thickness above the cavity (mm)
TUBE_OD = 6.51       # 2 x N anti-stud tube outer diameter (mm)
TUBE_ID = 4.8
POST_D = 3.2         # 1 x N underside post diameter (mm)


# -- low-level bmesh helpers (all coordinates in mm) -------------------------

def _quad(bm, vs):
    return bm.faces.new(vs)


def box_solid(bm, x0, x1, y0, y1, z0, z1):
    v = [bm.verts.new(p) for p in ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                                     (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))]
    for f in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        _quad(bm, [v[i] for i in f])


def box_hollow(bm, x0, x1, y0, y1, h):
    """Closed shell: outer box with an open-bottom cavity (walls WALL_T, roof TOP_T)."""
    ix0, ix1, iy0, iy1 = x0 + WALL_T, x1 - WALL_T, y0 + WALL_T, y1 - WALL_T
    ch = h - TOP_T
    if ix1 - ix0 < 0.5 or iy1 - iy0 < 0.5 or ch < 0.5:
        box_solid(bm, x0, x1, y0, y1, 0, h)
        return ch
    o = [bm.verts.new(p) for p in ((x0, y0, 0), (x1, y0, 0), (x1, y1, 0), (x0, y1, 0),
                                     (x0, y0, h), (x1, y0, h), (x1, y1, h), (x0, y1, h))]
    i = [bm.verts.new(p) for p in ((ix0, iy0, 0), (ix1, iy0, 0), (ix1, iy1, 0), (ix0, iy1, 0),
                                     (ix0, iy0, ch), (ix1, iy0, ch), (ix1, iy1, ch), (ix0, iy1, ch))]
    _quad(bm, [o[4], o[5], o[6], o[7]])                       # top
    for a, b in ((0, 1), (1, 2), (2, 3), (3, 0)):
        _quad(bm, [o[a], o[b], o[b + 4], o[a + 4]])            # outer walls
        _quad(bm, [o[b], o[a], i[a], i[b]])                    # bottom rim
        _quad(bm, [i[b], i[a], i[a + 4], i[b + 4]])            # cavity walls
    _quad(bm, [i[7], i[6], i[5], i[4]])                       # cavity ceiling
    return ch


def cylinder(bm, cx, cy, z0, z1, r, cap_top=True, cap_bottom=False, axis="z"):
    """Cylinder along +Z (or along -Y for side studs, with cy as the start plane
    and z0/z1 reinterpreted as the y-range)."""
    ring0, ring1 = [], []
    for k in range(SEGS):
        a = 2 * math.pi * k / SEGS
        dx, dy = r * math.cos(a), r * math.sin(a)
        if axis == "z":
            ring0.append(bm.verts.new((cx + dx, cy + dy, z0)))
            ring1.append(bm.verts.new((cx + dx, cy + dy, z1)))
        else:  # axis -Y: circle in the XZ plane centred at (cx, *, cy)
            ring0.append(bm.verts.new((cx + dx, z0, cy + dy)))
            ring1.append(bm.verts.new((cx + dx, z1, cy + dy)))
    for k in range(SEGS):
        n = (k + 1) % SEGS
        _quad(bm, [ring0[k], ring0[n], ring1[n], ring1[k]])
    if cap_top:
        bm.faces.new(ring1)
    if cap_bottom:
        bm.faces.new(list(reversed(ring0)))


def tube(bm, cx, cy, h, ro, ri):
    outer0 = [bm.verts.new((cx + ro * math.cos(2 * math.pi * k / SEGS), cy + ro * math.sin(2 * math.pi * k / SEGS), 0)) for k in range(SEGS)]
    outer1 = [bm.verts.new((v.co.x, v.co.y, h)) for v in outer0]
    inner0 = [bm.verts.new((cx + ri * math.cos(2 * math.pi * k / SEGS), cy + ri * math.sin(2 * math.pi * k / SEGS), 0)) for k in range(SEGS)]
    inner1 = [bm.verts.new((v.co.x, v.co.y, h)) for v in inner0]
    for k in range(SEGS):
        n = (k + 1) % SEGS
        _quad(bm, [outer0[k], outer0[n], outer1[n], outer1[k]])
        _quad(bm, [inner0[n], inner0[k], inner1[k], inner1[n]])
        _quad(bm, [outer0[n], outer0[k], inner0[k], inner0[n]])


def prism(bm, poly, a0, a1, plane):
    """Extrude a 2D polygon. plane 'xz': poly in (x, z), extruded along y;
    plane 'yz': poly in (y, z), extruded along x."""
    def P(u, v, a):
        return (u, a, v) if plane == "xz" else (a, u, v)
    f0 = [bm.verts.new(P(u, v, a0)) for u, v in poly]
    f1 = [bm.verts.new(P(u, v, a1)) for u, v in poly]
    bm.faces.new(f0)
    bm.faces.new(list(reversed(f1)))
    n = len(poly)
    for k in range(n):
        m = (k + 1) % n
        _quad(bm, [f0[m], f0[k], f1[k], f1[m]])


def studs_top(bm, cells, w, d, z):
    for lx, ly in cells:
        cx = (lx + 0.5) * STUD - w * STUD / 2
        cy = (ly + 0.5) * STUD - d * STUD / 2
        cylinder(bm, cx, cy, z, z + STUD_H, STUD_D / 2)


def underside(bm, w, d, cavity):
    if cavity <= 0:
        return
    if w >= 2 and d >= 2:
        for i in range(1, w):
            for j in range(1, d):
                tube(bm, i * STUD - w * STUD / 2, j * STUD - d * STUD / 2, cavity, TUBE_OD / 2, TUBE_ID / 2)
    elif w >= 2 or d >= 2:
        n, along_x = (w, True) if w >= 2 else (d, False)
        for i in range(1, n):
            c = i * STUD - n * STUD / 2
            cylinder(bm, c if along_x else 0, 0 if along_x else c, 0, cavity, POST_D / 2, cap_top=False, cap_bottom=True)


# -- part builders ------------------------------------------------------------

def _build(bm, p):
    hw, hd = p.w * STUD / 2 - INSET, p.d * STUD / 2 - INSET
    H = p.h * PLATE
    if p.kind == "box":
        cavity = box_hollow(bm, -hw, hw, -hd, hd, H)
        underside(bm, p.w, p.d, cavity)
        if p.studs:
            studs_top(bm, p.top_cells(), p.w, p.d, H)
    elif p.kind == "baseplate":
        box_solid(bm, -hw, hw, -hd, hd, 1.6, H)
        studs_top(bm, p.top_cells(), p.w, p.d, H)
    elif p.kind == "round":
        r = STUD / 2 - INSET
        cylinder(bm, 0, 0, 0, H, r, cap_top=True, cap_bottom=True)
        if p.studs:
            studs_top(bm, p.top_cells(), p.w, p.d, H)
    elif p.kind == "slope":
        # Profile in (y, z): low lip at -Y, flat top over the rear stud row.
        lip = H - STUD   # 45 degrees: the slope drops one stud depth over one stud
        poly = [(-hd, 0), (hd, 0), (hd, H), (hd - STUD + INSET, H), (-hd, lip)]
        prism(bm, poly, -hw, hw, "yz")
        studs_top(bm, p.top_cells(), p.w, p.d, H)
    elif p.kind == "arch":
        a = p.extra["span"] * STUD / 2 - INSET
        spring = p.extra["spring"]
        poly = [(-hw, 0), (-a, 0), (-a, spring)]
        for k in range(1, 24):
            t = math.pi - math.pi * k / 24
            poly.append((a * math.cos(t), spring + a * math.sin(t)))
        poly += [(a, spring), (a, 0), (hw, 0), (hw, H), (-hw, H)]
        prism(bm, poly, -hd, hd, "xz")
        studs_top(bm, p.top_cells(), p.w, p.d, H)
    elif p.kind == "bracket":
        box_solid(bm, -hw, hw, -hd, hd, 0, H)
        studs_top(bm, p.top_cells(), p.w, p.d, H)
        y_face = -p.d * STUD / 2
        box_solid(bm, -hw, hw, y_face - PLATE, y_face + INSET, 0, STUD)
        for i in range(p.w):
            cx = (i + 0.5) * STUD - p.w * STUD / 2
            cylinder(bm, cx, STUD / 2, y_face - PLATE, y_face - PLATE - STUD_H, STUD_D / 2, axis="y")
    else:
        raise ValueError(p.kind)


def _smooth_by_angle(mesh, degrees=35.0):
    bm = bmesh.new()
    bm.from_mesh(mesh)
    limit = math.radians(degrees)
    for f in bm.faces:
        f.smooth = True
    for e in bm.edges:
        e.smooth = e.is_manifold and e.calc_face_angle(math.pi) < limit
    bm.to_mesh(mesh)
    bm.free()


def build_template(part_id):
    p = PARTS[part_id]
    bm = bmesh.new()
    _build(bm, p)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    raw = bpy.data.meshes.new(f"_raw_{part_id}")
    bm.to_mesh(raw)
    bm.free()
    raw.transform(Matrix.Scale(MM, 4))

    # Bevel modifier, evaluated once and baked into the shared template mesh.
    tmp = bpy.data.objects.new(f"_tmp_{part_id}", raw)
    bpy.context.scene.collection.objects.link(tmp)
    mod = tmp.modifiers.new("MicroBevel", "BEVEL")
    mod.width = BEVEL * MM
    mod.segments = 2
    mod.limit_method = "ANGLE"
    mod.angle_limit = math.radians(30)
    mod.use_clamp_overlap = True
    dg = bpy.context.evaluated_depsgraph_get()
    mesh = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    mesh.name = f"part_{part_id}"
    bpy.data.objects.remove(tmp)
    bpy.data.meshes.remove(raw)
    _smooth_by_angle(mesh)
    return mesh


def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def abs_material(color_name):
    c = COLORS[color_name]
    mat = bpy.data.materials.get(f"ABS_{c.name}")
    if mat:
        return mat
    mat = bpy.data.materials.new(f"ABS_{c.name}")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    rgb = [srgb_to_linear(int(c.hex[i:i + 2], 16) / 255) for i in (1, 3, 5)]
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.15 if c.transparent else 0.18
    bsdf.inputs["IOR"].default_value = 1.46
    if c.transparent:
        bsdf.inputs["Transmission Weight"].default_value = 1.0
    else:
        bsdf.inputs["Subsurface Weight"].default_value = 0.03
        bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.6, 0.4)
        bsdf.inputs["Subsurface Scale"].default_value = 1.0 * MM
    mat["bricklink_color_id"] = c.bl_id
    return mat
