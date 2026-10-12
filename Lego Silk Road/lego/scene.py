"""Blender scene assembly, studio rig and renders (requires bpy)."""

import gc
import math
import os

import bpy
from mathutils import Euler, Vector

from .catalog import PLATE, STUD
from .layout import COLLECTIONS
from .templates import MM, abs_material, build_template


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    return sc


def _collection(name, parent=None):
    col = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if col.name not in (parent or bpy.context.scene.collection).children:
        (parent or bpy.context.scene.collection).children.link(col)
    return col


def build_model(model, gc_every=200):
    """Instance every placement as a linked duplicate of its part template."""
    cols = {name: _collection(name) for name in COLLECTIONS}
    root = bpy.data.objects.new(model.name, None)
    bpy.context.scene.collection.objects.link(root)
    meshes = {}
    templates = {}
    for k, pl in enumerate(model.parts):
        key = (pl.part, pl.color)
        if key not in meshes:
            if pl.part not in templates:
                templates[pl.part] = build_template(pl.part)
            mesh = templates[pl.part].copy()
            mesh.name = f"{pl.part}_{pl.color.replace(' ', '')}"
            mesh.materials.append(abs_material(pl.color))
            meshes[key] = mesh
        ob = bpy.data.objects.new(f"{pl.group}_{pl.part}_{k:04d}", meshes[key])
        p = pl.p
        if pl.sideways:
            cx, yb, cz = pl.mm
            ob.location = Vector((cx, yb, cz)) * MM
            ob.rotation_euler = Euler((math.pi / 2, 0, 0))
        else:
            w, d = pl.dims()
            ob.location = Vector(((pl.x + w / 2) * STUD, (pl.y + d / 2) * STUD, pl.z * PLATE)) * MM
            ob.rotation_euler = Euler((0, 0, math.radians(pl.rot)))
        ob["part_id"] = pl.part
        ob["color"] = pl.color
        ob.parent = root
        cols[pl.collection].objects.link(ob)
        if (k + 1) % gc_every == 0:
            gc.collect()   # keep Python-side wrappers from piling up during batch instancing
    for m in templates.values():
        if m.users == 0:
            bpy.data.meshes.remove(m)
    gc.collect()
    return root


def model_bounds(model):
    xs, ys, zs = [], [], []
    for pl in model.parts:
        if pl.sideways:
            cx, yb, cz = pl.mm
            xs += [cx]
            ys += [yb - PLATE * 2]
            zs += [cz + 8]
            continue
        w, d = pl.dims()
        xs += [pl.x * STUD, (pl.x + w) * STUD]
        ys += [pl.y * STUD, (pl.y + d) * STUD]
        zs += [(pl.z + pl.p.h) * PLATE + 1.7]
    lo = Vector((min(xs), min(ys), 0.0)) * MM
    hi = Vector((max(xs), max(ys), max(zs))) * MM
    return lo, hi


def _sweep(size, lo, hi, color=(0.42, 0.40, 0.37)):
    """Infinite-cove backdrop: floor running into a curved back wall behind the model."""
    import bmesh
    cx, cy = (lo.x + hi.x) / 2, (lo.y + hi.y) / 2
    span = max(hi.x - lo.x, hi.y - lo.y)
    W, front, back, R, H = span * 40, span * 12, span * 1.2, span * 0.8, span * 12
    prof = [(cy - front, 0.0), (cy + back, 0.0)]
    for k in range(1, 13):
        a = math.pi / 2 * k / 12
        prof.append((cy + back + R * math.sin(a), R - R * math.cos(a)))
    prof.append((cy + back + R, H))
    bm = bmesh.new()
    left = [bm.verts.new((cx - W / 2, y, z - 0.0002)) for y, z in prof]
    right = [bm.verts.new((cx + W / 2, y, z - 0.0002)) for y, z in prof]
    for k in range(len(prof) - 1):
        bm.faces.new([left[k], right[k], right[k + 1], left[k + 1]])
    me = bpy.data.meshes.new("Backdrop")
    bm.to_mesh(me)
    bm.free()
    for f in me.polygons:
        f.use_smooth = True
    ob = bpy.data.objects.new("Backdrop_Sweep", me)
    mat = bpy.data.materials.new("Backdrop_Matte")
    mat.use_nodes = True
    b = mat.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = 0.8
    me.materials.append(mat)
    return ob


def _area_light(name, color, power, size, loc, target, shape="RECTANGLE", ratio=1.0):
    ld = bpy.data.lights.new(name, "AREA")
    ld.shape = shape
    ld.size = size
    ld.size_y = size * ratio
    ld.energy = power
    ld.color = color
    ob = bpy.data.objects.new(name, ld)
    ob.visible_camera = False   # softboxes light the set but never appear in frame
    ob.location = loc
    ob.rotation_euler = (target - loc).to_track_quat("-Z", "Y").to_euler()
    return ob


def studio(model, samples=128, resolution=(1600, 1200)):
    sc = bpy.context.scene
    lo, hi = model_bounds(model)
    center = (lo + hi) / 2
    radius = (hi - lo).length / 2
    studio_col = _collection("05_Studio")
    studio_col.objects.link(_sweep(radius, lo, hi))

    # Three-point softbox rig, scaled to the model.
    aim = Vector((center.x, center.y, hi.z * 0.35))
    d = radius * 3.2
    # Power scales with distance squared so every size gets the same exposure.
    k = d * d
    rigs = [
        ("Key_Warm", (1.0, 0.86, 0.72), 20 * k, radius * 1.6, -55, 45),
        ("Fill_Cool", (0.72, 0.84, 1.0), 6 * k, radius * 2.4, 75, 30),
        ("Rim_Crisp", (1.0, 1.0, 1.0), 24 * k, radius * 0.6, 155, 40),
    ]
    for name, col, pw, size, az, el in rigs:
        a, e = math.radians(az), math.radians(el)
        loc = aim + Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))) * d
        studio_col.objects.link(_area_light(name, col, pw, size, loc, aim))

    world = bpy.data.worlds.new("Studio")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.42, 0.40, 0.37, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.15
    sc.world = world

    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.02
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 8
    sc.cycles.transmission_bounces = 8
    sc.render.resolution_x, sc.render.resolution_y = resolution
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.render.film_transparent = False
    try:
        sc.view_settings.view_transform = "AgX"
        sc.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    return lo, hi, center, radius, studio_col


def _camera(name, col):
    cd = bpy.data.cameras.new(name)
    ob = bpy.data.objects.new(name, cd)
    col.objects.link(ob)
    return ob


def _look(ob, loc, target):
    ob.location = loc
    ob.rotation_euler = (target - loc).to_track_quat("-Z", "Y").to_euler()


def render_views(model, outdir, lo, hi, center, radius, col):
    os.makedirs(outdir, exist_ok=True)
    sc = bpy.context.scene
    aspect = sc.render.resolution_x / sc.render.resolution_y
    hero_target = Vector((center.x, center.y, hi.z * 0.38))
    out = {}

    # 1. Hero: front three-quarter, low angle, subtle depth of field on the gateway.
    cam = _camera("CAM_Hero", col)
    cam.data.lens = 70
    cam.data.sensor_width = 36
    half_v = math.atan(cam.data.sensor_width / aspect / 2 / cam.data.lens)
    dist = radius / math.sin(half_v) * 1.02
    az, el = math.radians(-35), math.radians(16)
    loc = hero_target + Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el))) * dist
    _look(cam, loc, hero_target)
    gate = Vector((center.x, lo.y, hi.z * 0.3))
    cam.data.dof.use_dof = True
    cam.data.dof.focus_distance = (gate - loc).length
    cam.data.dof.aperture_fstop = max(5.6, min(64.0, 3.5 / max(radius, 0.01)))
    out["hero_perspective.png"] = cam

    # 2. Profile: orthographic front elevation (the gateway facade).
    cam = _camera("CAM_Profile", col)
    cam.data.type = "ORTHO"
    w, h = hi.x - lo.x, hi.z - lo.z
    cam.data.ortho_scale = max(w, h * aspect) * 1.18
    frame_h = cam.data.ortho_scale / aspect
    cz = frame_h / 2                           # frame bottom sits exactly on the floor line
    _look(cam, Vector((center.x, lo.y - radius * 6, cz)), Vector((center.x, center.y, cz)))
    cam.data.clip_end = radius * 20
    out["profile_elevation.png"] = cam

    # 3. Detail: steep overhead view that rakes light across the studs.
    cam = _camera("CAM_TopDown", col)
    cam.data.lens = 50
    half_v = math.atan(cam.data.sensor_width / aspect / 2 / cam.data.lens)
    dist = radius / math.sin(half_v) * 0.98
    az, el = math.radians(-12), math.radians(72)
    tgt = Vector((center.x, center.y, hi.z * 0.4))
    loc = tgt + Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el))) * dist
    _look(cam, loc, tgt)
    cam.data.dof.use_dof = True
    cam.data.dof.focus_distance = (tgt - loc).length
    cam.data.dof.aperture_fstop = max(8.0, min(64.0, 5.0 / max(radius, 0.01)))
    out["detail_topdown.png"] = cam

    written = []
    for fname, cam in out.items():
        sc.camera = cam
        sc.render.filepath = os.path.abspath(os.path.join(outdir, fname))
        bpy.ops.render.render(write_still=True)
        written.append(sc.render.filepath)
        gc.collect()
    return written
