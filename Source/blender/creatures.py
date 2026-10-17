# Crustaceans for both excursions (M4/M5), from the prototype's build_props.py and the book:
#  - the sea-spider of the forest of Crespo, "about thirty-eight inches high ... watching me with squinting eyes" (I.XVI);
#  - the titanic crabs "pointed like a gun on its carriage" and giant lobsters "setting themselves up like halberdiers",
#    whose eyes shine in the holes on the way to Atlantis (II.IX). Eyes are emissive: in the dark they are what you see.
# Each creature at the origin, Z up, front = -Y.
import sys, os, math, random
sys.path.insert(0, os.path.dirname(__file__))
import bpy, bmesh
from mathutils import Vector, Matrix
from blib import *

OUT = sys.argv[-1] if len(sys.argv) > 1 and not sys.argv[-1].endswith('.py') else '/tmp/creatures'
os.makedirs(OUT, exist_ok=True)
reset()
M = {'crab': mat('M_crab', (0.5, 0.16, 0.08), rough=0.6), 'spider': mat('M_spidercrab', (0.55, 0.32, 0.2), rough=0.8),
     'eye': mat('M_eye', (0.4, 1.0, 0.75), emit=(0.4, 1.0, 0.75))}
ML = list(M.values()); MI = {k: ML.index(v) for k, v in M.items()}
PROPS = []
def prop(name, build, smooth=None):
    bm = bmesh.new(); build(bm); bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = new_obj(name, bm, ML, 'CRE', None, smooth); PROPS.append(o); return o
def ico(bm, c, r, sub=1, mi=0, scale=(1, 1, 1)):
    t = bmesh.new(); bmesh.ops.create_icosphere(t, subdivisions=sub, radius=r)
    for v in t.verts: v.co = Vector((v.co.x * scale[0], v.co.y * scale[1], v.co.z * scale[2])) + Vector(c)
    for f in t.faces: f.material_index = mi
    merge_into(bm, t)
def tube(bm, pts, radii, seg=6, mi=0):
    rings = []
    for i, p in enumerate(pts):
        p = Vector(p)
        d = (Vector(pts[min(i + 1, len(pts) - 1)]) - Vector(pts[max(i - 1, 0)])).normalized()
        up = Vector((0, 0, 1)) if abs(d.z) < 0.95 else Vector((1, 0, 0))
        a = d.cross(up).normalized(); b = d.cross(a).normalized()
        r = radii[i] if isinstance(radii, (list, tuple)) else radii
        rings.append([bm.verts.new(p + (a * math.cos(2 * math.pi * k / seg) + b * math.sin(2 * math.pi * k / seg)) * r) for k in range(seg)])
    for i in range(len(rings) - 1):
        for k in range(seg):
            f = bm.faces.new([rings[i][k], rings[i][(k + 1) % seg], rings[i + 1][(k + 1) % seg], rings[i + 1][k]]); f.material_index = mi

def sea_spider(bm):
    """Spider crab: a small pear-shaped carapace held high on eight long, jointed legs; two slender claws; stalked eyes."""
    ico(bm, (0, 0, 0.82), 0.22, 1, MI['spider'], (0.9, 1.15, 0.6))
    ico(bm, (0, -0.25, 0.86), 0.09, 1, MI['spider'], (0.8, 1.2, 0.7))
    for s in (-1, 1):
        for k in range(4):
            a = math.radians(-40 + k * 30)
            p0 = Vector((math.sin(a) * 0.18 * s + 0.02 * s, math.cos(a) * 0.12, 0.8))
            p1 = p0 + Vector((math.sin(a) * 0.45 * s, math.cos(a) * 0.35, 0.3))       # knees high, spider-like
            p2 = p1 + Vector((math.sin(a) * 0.35 * s, math.cos(a) * 0.3, -1.12))
            tube(bm, [p0, p1, p2], [0.03, 0.025, 0.008], 4, MI['spider'])
        tube(bm, [(0.08 * s, -0.3, 0.84), (0.3 * s, -0.62, 0.95), (0.18 * s, -0.9, 0.86)], [0.03, 0.025, 0.012], 4, MI['spider'])
        tube(bm, [(0.04 * s, -0.33, 0.9), (0.06 * s, -0.36, 0.98)], [0.01, 0.008], 4, MI['spider'])
        ico(bm, (0.06 * s, -0.37, 0.99), 0.022, 0, MI['eye'])
prop('sea_spider', sea_spider, smooth=40)
def crab(bm):
    ico(bm, (0, 0, 0.35), 0.6, 1, MI['crab'], (1.0, 0.8, 0.45))
    for s in (-1, 1):
        for k in range(4):
            a = math.radians(-50 + k * 30)
            p0 = Vector((math.sin(a) * 0.45 * s, math.cos(a) * 0.45, 0.35))
            p1 = p0 + Vector((math.sin(a) * 0.5 * s, math.cos(a) * 0.5, 0.25))
            p2 = p1 + Vector((math.sin(a) * 0.25 * s, math.cos(a) * 0.25, -0.6))
            tube(bm, [p0, p1, p2], [0.05, 0.04, 0.015], 4, MI['crab'])
        tube(bm, [(0.3 * s, -0.45, 0.4), (0.5 * s, -0.9, 0.5), (0.35 * s, -1.25, 0.45)], [0.08, 0.1, 0.07], 5, MI['crab'])
        ico(bm, (0.35 * s, -1.35, 0.45), 0.13, 1, MI['crab'], (0.8, 1.3, 0.6))
        ico(bm, (0.15 * s, -0.55, 0.6), 0.04, 1, MI['eye'])
prop('crab_giant', crab, smooth=40)
def lobster(bm):
    tube(bm, [(0, 1.2, 0.3), (0, 0.6, 0.35), (0, 0.0, 0.4), (0, -0.5, 0.42)], [0.1, 0.2, 0.26, 0.22], 7, MI['crab'])
    for s in (-1, 1):
        tube(bm, [(0.15 * s, -0.5, 0.45), (0.4 * s, -1.0, 0.6), (0.3 * s, -1.6, 0.7)], [0.06, 0.08, 0.05], 5, MI['crab'])
        ico(bm, (0.3 * s, -1.75, 0.7), 0.15, 1, MI['crab'], (0.7, 1.4, 0.5))
        tube(bm, [(0.08 * s, -0.55, 0.55), (0.6 * s, -1.6, 1.4), (1.0 * s, -2.4, 1.6)], [0.015, 0.01, 0.004], 3, MI['crab'])
        ico(bm, (0.1 * s, -0.6, 0.6), 0.035, 1, MI['eye'])
prop('lobster_giant', lobster, smooth=40)

for o in PROPS: world_uv(o, 1.0)
bpy.ops.object.select_all(action='DESELECT')
for o in PROPS: o.select_set(True)
bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, 'Creatures.fbx'), use_selection=True, apply_unit_scale=True,
                         apply_scale_options='FBX_SCALE_UNITS', axis_forward='-Z', axis_up='Y', bake_space_transform=True,
                         object_types={'MESH'}, mesh_smooth_type='FACE', add_leaf_bones=False, path_mode='STRIP')
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'creatures.blend'))
print('EXPORTED', [(o.name, sum(len(p.vertices) - 2 for p in o.data.polygons)) for o in PROPS])
