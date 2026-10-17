# The diving apparatus as a puppet (M4), after Neuville's engraving (im033 / ill-003) and I.XIV:
# round copper helmet with three glass ports, india-rubber dress, copper bands across the chest, lead
# soles, the Rouquayrol reservoir on the back, the Ruhmkorff lamp at the belt; plus the iron-pointed stick,
# the pickaxe, the air-gun and the shroud of white linen for the burial. Ported from the prototype's
# reference/blender/build_props.py. Each part's origin is its joint (Blender Z up, front = -Y), so Unity
# assembles and animates the diver procedurally (DiverPuppet.cs): rigid parts, as a stiff dress moves.
import sys, os, math, random
sys.path.insert(0, os.path.dirname(__file__))
import bpy, bmesh
from mathutils import Vector, Matrix
from blib import *

OUT = sys.argv[-1] if len(sys.argv) > 1 and not sys.argv[-1].endswith('.py') else '/tmp/diver'
os.makedirs(OUT, exist_ok=True)
reset()
M = {
    'rubber': mat('M_suit', (0.16, 0.13, 0.1), rough=0.75),
    'copper': mat('M_copper', (0.7, 0.38, 0.22), metal=1.0, rough=0.4),
    'brass': mat('M_brass', (0.75, 0.55, 0.25), metal=1.0, rough=0.35),
    'port': mat('M_port', (0.05, 0.07, 0.08), rough=0.05),
    'lead': mat('M_lead', (0.25, 0.25, 0.26), metal=0.6, rough=0.6),
    'iron': mat('M_iron', (0.22, 0.22, 0.22), metal=0.8, rough=0.6),
    'wood': mat('M_oak', (0.35, 0.22, 0.12), rough=0.6),
    'lampglass': mat('M_lampglass', (0.9, 0.95, 1.0), emit=(1, 1, 1)),
    'linen': mat('M_linen', (0.8, 0.78, 0.72), rough=0.95),
}
ML = list(M.values()); MI = {k: ML.index(v) for k, v in M.items()}
PROPS = []
def prop(name, build, smooth=None, props=None):
    bm = bmesh.new(); build(bm)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = new_obj(name, bm, ML, 'DIVER', props, smooth)
    PROPS.append(o)
    return o

def jitter(bm, amt, seed=0):
    r = random.Random(seed)
    for v in bm.verts: v.co += Vector((r.uniform(-amt, amt), r.uniform(-amt, amt), r.uniform(-amt, amt)))

def ico(bm, c, r, sub=1, mi=0, scale=(1, 1, 1)):
    t = bmesh.new()
    bmesh.ops.create_icosphere(t, subdivisions=sub, radius=r)
    for v in t.verts: v.co = Vector((v.co.x * scale[0], v.co.y * scale[1], v.co.z * scale[2])) + Vector(c)
    for f in t.faces: f.material_index = mi
    merge_into(bm, t)

def tube(bm, pts, radii, seg=6, mi=0, cap=True):
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
    if cap:
        f = bm.faces.new(rings[0][::-1]); f.material_index = mi

# ------------------------------------------------------------ diving apparatus (parts, pivots at joints)
def helmet(bm):
    ico(bm, (0, 0, 0), 0.19, 2, MI['copper'])
    for (ax, ay) in [(0, -1), (-0.95, -0.3), (0.95, -0.3)]:
        d = Vector((ax, ay, 0.05)).normalized()
        c = d * 0.17
        rot = d.to_track_quat('Z', 'Y').to_matrix().to_4x4()
        t = bmesh.new()
        lathe(t, [(0.085, 0.0), (0.085, 0.035), (0.07, 0.04), (0.0, 0.035)], 14, (0, 0, 0), MI['brass'])
        merge_into(bm, t, Matrix.Translation(c) @ rot)
        t = bmesh.new()
        lathe(t, [(0.065, 0.041), (0.0, 0.046)], 14, (0, 0, 0), MI['port'])
        merge_into(bm, t, Matrix.Translation(c) @ rot)
        # guard bars on the front port
        if ay < -0.9:
            for k in (-0.03, 0.03):
                box(bm, k - 0.006, k + 0.006, -0.235, -0.225, -0.07, 0.07, MI['brass'])
    lathe(bm, [(0.2, -0.2), (0.2, -0.16), (0.17, -0.13)], 16, (0, 0, 0), MI['brass'])   # collar
    for k in range(6):
        a = k * math.pi / 3
        cylinder(bm, (math.cos(a) * 0.19, math.sin(a) * 0.19, -0.2), 0.012, 0.05, 6, MI['brass'])
    cylinder(bm, (0, 0.12, 0.12), 0.025, 0.08, 8, MI['brass'], axis='Y')   # air inlets at the back
prop('diver_helmet', helmet, smooth=40)
def torso(bm):
    # waist at z=0 up to the collar (z=0.55); chest broad, impervious dress
    lathe(bm, [(0.0, -0.02), (0.15, -0.02), (0.17, 0.1), (0.19, 0.28), (0.21, 0.42), (0.18, 0.52), (0.12, 0.56), (0.0, 0.57)], 12, (0, 0, 0), MI['rubber'])
    for v in bm.verts: v.co.y *= 0.72
    # copper bands crossing the chest and the belt
    for s in (-1, 1):
        tube(bm, [(s * 0.17, -0.11, 0.48), (0, -0.155, 0.3), (-s * 0.17, -0.11, 0.12)], 0.016, 6, MI['copper'], cap=False)
    lathe(bm, [(0.172, 0.04), (0.176, 0.07), (0.172, 0.1)], 14, (0, 0, 0), MI['copper'])
    for v in bm.verts[-50:]:
        pass
prop('diver_torso', torso, smooth=50)
def hips(bm):
    lathe(bm, [(0.0, 0.02), (0.16, 0.02), (0.17, -0.08), (0.15, -0.16), (0.0, -0.18)], 12, (0, 0, 0), MI['rubber'])
    for v in bm.verts: v.co.y *= 0.75
prop('diver_hips', hips, smooth=50)
def tank(bm):
    # Rouquayrol reservoir of thick iron plates, worn like a soldier's knapsack, and the regulator box on top
    box(bm, -0.17, 0.17, 0.0, 0.18, -0.25, 0.22, MI['iron'])
    box(bm, -0.12, 0.12, 0.02, 0.16, 0.22, 0.33, MI['brass'])
    for s in (-1, 1):
        tube(bm, [(s * 0.06, 0.08, 0.33), (s * 0.06, 0.02, 0.45), (s * 0.05, -0.02, 0.56)], 0.014, 6, MI['rubber'], cap=False)
    for zz in (-0.15, 0.1):
        box(bm, -0.175, 0.175, -0.01, 0.19, zz, zz + 0.025, MI['copper'])
prop('diver_tank', tank, smooth=None)
def upperarm(bm):
    lathe(bm, [(0.0, 0.03), (0.07, 0.02), (0.065, -0.14), (0.055, -0.28), (0.0, -0.3)], 8, (0, 0, 0), MI['rubber'])
prop('diver_upperarm', upperarm, smooth=50)
def forearm(bm):
    lathe(bm, [(0.0, 0.02), (0.055, 0.0), (0.05, -0.15), (0.042, -0.26), (0.0, -0.27)], 8, (0, 0, 0), MI['rubber'])
    lathe(bm, [(0.0, -0.25), (0.05, -0.26), (0.048, -0.33), (0.03, -0.38), (0.0, -0.39)], 8, (0, 0, 0), MI['rubber'])
    for v in bm.verts:
        if v.co.z < -0.27: v.co.x *= 1.25; v.co.y *= 0.65
prop('diver_forearm', forearm, smooth=50)
def thigh(bm):
    lathe(bm, [(0.0, 0.02), (0.09, 0.0), (0.085, -0.2), (0.07, -0.4), (0.0, -0.42)], 8, (0, 0, 0), MI['rubber'])
prop('diver_thigh', thigh, smooth=50)
def shin(bm):
    lathe(bm, [(0.0, 0.02), (0.07, 0.0), (0.065, -0.2), (0.055, -0.38), (0.0, -0.4)], 8, (0, 0, 0), MI['rubber'])
prop('diver_shin', shin, smooth=50)
def boot(bm):
    # thick boots weighted with heavy leaden soles
    box(bm, -0.065, 0.065, -0.17, 0.06, -0.06, 0.08, MI['rubber'])
    box(bm, -0.075, 0.075, -0.19, 0.075, -0.1, -0.06, MI['lead'])
    cylinder(bm, (0, 0, 0.02), 0.065, 0.1, 8, MI['rubber'])
prop('diver_boot', boot)
def lamp(bm):
    # Ruhmkorff lamp: a Bunsen pile in a box and a lantern with a spiral glass of carbonic gas
    box(bm, -0.06, 0.06, -0.05, 0.05, -0.22, -0.02, MI['brass'])
    cylinder(bm, (0, 0, -0.02), 0.012, 0.04, 6, MI['brass'])
    box(bm, -0.045, 0.045, -0.06, 0.03, -0.2, -0.04, MI['lampglass'])
    tube(bm, [(0, 0, 0.02), (0, 0.02, 0.06)], 0.006, 4, MI['iron'])
prop('diver_lamp', lamp)
def stick(bm):
    cylinder(bm, (0, 0, -0.75), 0.016, 1.45, 6, MI['wood'])
    cylinder(bm, (0, 0, -0.95), 0.0, 0.2, 6, MI['iron'], r2=0.018)
    for v in bm.verts:
        pass
prop('diver_stick', stick, smooth=40)
def pickaxe(bm):
    cylinder(bm, (0, 0, -0.45), 0.018, 0.8, 6, MI['wood'])
    tube(bm, [(-0.28, 0, 0.33), (-0.1, 0, 0.36), (0, 0, 0.37), (0.1, 0, 0.36), (0.25, 0, 0.32)], [0.008, 0.025, 0.03, 0.025, 0.012], 6, MI['iron'])
prop('pickaxe', pickaxe, smooth=40)
def gun(bm):
    # air gun: steel butt hollowed as a reservoir, metal tube
    box(bm, -0.035, 0.035, -0.04, 0.04, -0.35, -0.05, MI['iron'])
    cylinder(bm, (0, 0, -0.05), 0.014, 0.75, 8, MI['iron'])
    box(bm, -0.02, 0.02, -0.02, 0.06, -0.12, -0.08, MI['brass'])
prop('diver_gun', gun)
def shroud(bm):
    # the body, enveloped in a tissue of white linen, carried on shoulders
    lathe(bm, [(0.0, -0.9), (0.15, -0.88), (0.2, -0.6), (0.24, -0.1), (0.22, 0.4), (0.18, 0.7), (0.12, 0.88), (0.0, 0.92)], 10, (0, 0, 0), MI['linen'], axis='Y')
    for v in bm.verts: v.co.z *= 0.75
    jitter(bm, 0.012, 3)
prop('shroud', shroud, smooth=60)


for o in PROPS: world_uv(o, 1.0)
bpy.ops.object.select_all(action='DESELECT')
for o in PROPS: o.select_set(True)
bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, 'Diver_Parts.fbx'), use_selection=True, apply_unit_scale=True,
                         apply_scale_options='FBX_SCALE_UNITS', axis_forward='-Z', axis_up='Y', bake_space_transform=True,
                         object_types={'MESH'}, mesh_smooth_type='FACE', add_leaf_bones=False, path_mode='STRIP')
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'diver_parts.blend'))
print('EXPORTED', [o.name for o in PROPS], sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in PROPS))
