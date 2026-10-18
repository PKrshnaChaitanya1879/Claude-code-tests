# Rocks of the sea floor (M4, and M5 with a basalt material): low-poly faceted boulders, slabs and outcrops,
# replacing the greybox boxes. After the engravings im034 / im036 (Crespo: rounded rocks along the sandy path,
# "rocks carpeted with zoophytes", I.XVI) and im078 (holes in the rock for the crustaceans).
# Upward-facing faces take an encrusting material (coralline weed, sponges): colour lives where the light lands.
# Each rock sits at the origin, Z up, its base slightly below 0 so it never floats on uneven sand.
# Run: python3 seabed_rocks.py <outdir>   →  Seabed_Rocks.fbx (+ .blend for previews)
import sys, os, math, random
sys.path.insert(0, os.path.dirname(__file__))
import bpy, bmesh
from mathutils import Vector, noise
from blib import *

OUT = sys.argv[-1] if len(sys.argv) > 1 and not sys.argv[-1].endswith('.py') else '/tmp/rocks'
os.makedirs(OUT, exist_ok=True)
reset()
MATS = [mat('M_seabed_rock', (0.40, 0.38, 0.35), rough=0.95),
        mat('M_rock_encrust', (0.62, 0.36, 0.30), rough=0.9),      # coralline pink-ochre: red algae and sponges
        mat('M_rock_weed', (0.30, 0.34, 0.14), rough=0.9)]         # a green-brown film of weed
ROCKS = []

def rock(name, seed, size, squash=(1, 1, 0.7), subdiv=3, rough=0.35, sharp=1.0, holes=0):
    rnd = random.Random(seed)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
    off = Vector((rnd.uniform(-50, 50), rnd.uniform(-50, 50), rnd.uniform(-50, 50)))
    for v in bm.verts:
        p = v.co.copy()
        n = noise.noise(p * 1.3 + off) * rough + noise.noise(p * 3.1 + off) * rough * 0.35
        # planar facets: snap a few directions flat (cleaved granite), so the rock reads as stone, not a potato
        q = p * (1.0 + n)
        q = Vector((q.x * squash[0], q.y * squash[1], q.z * squash[2])) * size
        v.co = q
    # cleave: a few random planes cut the top and sides flat
    for _ in range(int(3 * sharp)):
        nrm = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-0.2, 1))).normalized()
        d = max((v.co.dot(nrm) for v in bm.verts)) * rnd.uniform(0.72, 0.85)
        for v in bm.verts:
            e = v.co.dot(nrm) - d
            if e > 0: v.co -= nrm * e
    # flatten the underside a little below the ground line
    zmin = min(v.co.z for v in bm.verts)
    for v in bm.verts:
        v.co.z -= zmin
        if v.co.z < size * squash[2] * 0.25: v.co.z = v.co.z * 0.4
        v.co.z -= size * 0.08
    # holes for the crustaceans: push a few side faces inward (II.IX "crouched in their holes")
    bm.faces.ensure_lookup_table()
    for _ in range(holes):
        f = rnd.choice([f for f in bm.faces if abs(f.normal.z) < 0.4 and f.calc_center_median().z > size * 0.2])
        c = f.calc_center_median()
        for v in f.verts: v.co = c + (v.co - c) * 1.3 - f.normal * size * 0.35
    bm.normal_update()
    # coherent patches (noise over the face centres), never a per-face checkerboard
    for f in bm.faces:
        up = f.normal.z
        c = f.calc_center_median() / size
        k = noise.noise(c * 1.4 + off * 0.5)
        if up > 0.45 and k > -0.15: f.material_index = 1 if noise.noise(c * 0.9 - off) > 0.0 else 2
        elif up > 0.1 and k > 0.35: f.material_index = 2
        else: f.material_index = 0
    o = new_obj(name, bm, MATS)
    world_uv(o, 1.0)
    ROCKS.append(o)
    return o

rock('rock_boulder_a', 1, 1.0, (1.0, 0.9, 0.75))
rock('rock_boulder_b', 2, 1.2, (1.2, 0.8, 0.6), rough=0.4)
rock('rock_boulder_c', 3, 0.7, (1.0, 1.0, 0.85), subdiv=2)
rock('rock_slab_a', 4, 1.4, (1.3, 1.0, 0.32), sharp=1.5)
rock('rock_slab_b', 5, 1.1, (1.0, 1.4, 0.28), sharp=1.5)
rock('rock_outcrop_a', 6, 1.3, (0.8, 0.7, 1.5), rough=0.45, sharp=1.3, holes=2)
rock('rock_outcrop_b', 7, 1.6, (1.1, 0.8, 1.2), rough=0.4, sharp=1.2, holes=3)
rock('rock_pebbles', 8, 0.35, (1.0, 1.0, 0.6), subdiv=2)

# lay them out in a row for the preview .blend (export resets locations via bake of each object's own transform)
bpy.ops.object.select_all(action='DESELECT')
for o in ROCKS: o.select_set(True)
bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, 'Seabed_Rocks.fbx'), use_selection=True, apply_unit_scale=True,
                         apply_scale_options='FBX_SCALE_UNITS', axis_forward='-Z', axis_up='Y', bake_space_transform=True,
                         object_types={'MESH'}, mesh_smooth_type='FACE', add_leaf_bones=False, path_mode='STRIP')
for i, o in enumerate(ROCKS): o.location.x = (i - len(ROCKS) / 2) * 3.4
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'rocks.blend'))
print('EXPORTED', [(o.name, sum(len(p.vertices) - 2 for p in o.data.polygons)) for o in ROCKS])
