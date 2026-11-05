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
    'lampglass': mat('M_lampglass', (1.0, 0.85, 0.6), emit=(1.0, 0.72, 0.42)),   # warm filament, never white (GUM's 1860s rule)
    'linen': mat('M_linen', (0.8, 0.78, 0.72), rough=0.95),
    'leather': mat('M_leather', (0.2, 0.12, 0.07), rough=0.7),
    'skin': mat('M_skin', (0.62, 0.45, 0.36), rough=0.6),
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
# ---------------------------------------------------------------- the dress (GUM Prompt_3: "more realistic")
# After Neuville's im033 and the real Rouquayrol-Denayrouze apparatus (1864-67): a big spherical copper bonnet
# bolted by three bolts to a copper corselet on the shoulders, the india-rubber dress clamped between them; the
# dress baggy and creased at the joints, a full belly, a leather belt with the lamp; lead weights hung under the
# arms; laced boots on thick lead soles with a brass toe-cap; the iron reservoir worn like a knapsack, with a lead
# weight on it and the air hose to the helmet. Low-poly, faceted, but each piece where it really is.
def folds(profile, amp, n, z0, z1):
    """Add creases to a lathe profile between heights z0..z1 (alternating swell and pinch)."""
    out = []
    for (r, z) in profile:
        if z0 < z < z1 and r > 0:
            k = (z - z0) / (z1 - z0)
            r *= 1 + amp * math.sin(k * n * math.pi * 2)
        out.append((r, z))
    return out

def helmet(bm):
    R = 0.25   # 5 Nov: the big bonnet of im033, as wide as the shoulders
    ico(bm, (0, 0, 0.02), R, 3, MI['copper'], scale=(1, 1.02, 0.98))
    # three ports (I.XIV: "three windows of thick glass"): two side by side in front, like eyes (im033), one on the right
    for (ax, ay, az, rr) in [(-0.42, -1, 0.05, 0.068), (0.42, -1, 0.05, 0.068), (1, -0.15, 0.08, 0.058)]:
        d = Vector((ax, ay, az)).normalized()
        c = Vector((0, 0, 0.02)) + d * (R - 0.012)
        rot = d.to_track_quat('Z', 'Y').to_matrix().to_4x4()
        t = bmesh.new()
        lathe(t, [(rr + 0.02, 0.0), (rr + 0.022, 0.022), (rr + 0.01, 0.03), (rr, 0.024)], 12, (0, 0, 0), MI['brass'])
        merge_into(bm, t, Matrix.Translation(c) @ rot)
        t = bmesh.new()
        lathe(t, [(rr, 0.022), (0.0, 0.026)], 12, (0, 0, 0), MI['port'])
        merge_into(bm, t, Matrix.Translation(c) @ rot)
        for k in range(6):                                   # the screws of the port rim
            a = k * math.pi / 3
            p = Vector((math.cos(a) * (rr + 0.014), math.sin(a) * (rr + 0.014), 0.031))
            t = bmesh.new(); ico(t, (0, 0, 0), 0.006, 1, MI['brass'])
            merge_into(bm, t, Matrix.Translation(c) @ rot @ Matrix.Translation(p))
    # the neck: a brass ring and the three-bolt flange that clamps the dress to the corselet
    lathe(bm, [(0.17, -0.17), (0.185, -0.19), (0.19, -0.23), (0.17, -0.24)], 16, (0, 0, 0), MI['brass'])
    for k in range(3):
        a = math.pi / 2 + k * 2 * math.pi / 3
        cylinder(bm, (math.cos(a) * 0.2, math.sin(a) * 0.2, -0.235), 0.014, 0.05, 6, MI['brass'])
        cylinder(bm, (math.cos(a) * 0.2, math.sin(a) * 0.2, -0.19), 0.022, 0.012, 6, MI['brass'])   # wing nut
    # a seam of rivets around the crown, the air inlet and the exhaust at the back, and a small lead weight each side
    for k in range(16):
        a = k * math.pi / 8
        t = bmesh.new(); ico(t, (math.cos(a) * 0.205, math.sin(a) * 0.205, 0.11), 0.007, 1, MI['brass']); merge_into(bm, t)
    cylinder(bm, (-0.05, 0.19, 0.06), 0.022, 0.07, 8, MI['brass'], axis='Y')
    cylinder(bm, (0.06, 0.2, -0.04), 0.016, 0.06, 8, MI['brass'], axis='Y')
    for s in (-1, 1):
        box(bm, s * 0.2 - 0.03, s * 0.2 + 0.03, -0.06, 0.06, -0.16, -0.08, MI['lead'])
prop('diver_helmet', helmet, smooth=30)

def torso(bm):
    # waist z=0 to the corselet (z~0.55): a full chest and belly in loose india-rubber, creased at the waist
    # 5 Nov: bulkier and rounder, as Neuville draws it: the dress blown out by the air inside, a barrel of a chest
    prof = [(0.0, -0.02), (0.18, -0.02), (0.205, 0.06), (0.225, 0.16), (0.24, 0.27), (0.24, 0.36), (0.228, 0.44), (0.19, 0.5), (0.13, 0.53), (0.0, 0.54)]
    prof = folds(prof, 0.045, 3.0, 0.0, 0.24)
    lathe(bm, prof, 16, (0, 0, 0), MI['rubber'])
    for v in bm.verts:
        v.co.y *= 0.86
        if v.co.y < 0 and 0.08 < v.co.z < 0.3: v.co.y *= 1.12          # the belly (im033)
    # the copper corselet over the shoulders, its flange bolts, and the brails clamping the dress
    t = bmesh.new()
    lathe(t, [(0.26, 0.44), (0.25, 0.49), (0.21, 0.54), (0.18, 0.56), (0.17, 0.58)], 16, (0, 0, 0), MI['copper'])
    for v in t.verts: v.co.y *= 0.8
    merge_into(bm, t)
    for k in range(12):
        a = k * math.pi / 6
        t = bmesh.new(); ico(t, (math.cos(a) * 0.245, math.sin(a) * 0.245 * 0.8, 0.455), 0.009, 1, MI['brass']); merge_into(bm, t)
    # lead weights hung under the arms, front and back
    for s in (-1, 1):
        for yy in (-1, 1):
            box(bm, s * 0.11 - 0.06, s * 0.11 + 0.06, yy * 0.15 - 0.022, yy * 0.15 + 0.022, 0.24, 0.36, MI['lead'])
            box(bm, s * 0.11 - 0.008, s * 0.11 + 0.008, yy * 0.15 - 0.024, yy * 0.15 + 0.024, 0.36, 0.44, MI['iron'])   # the strap
    # the leather belt with its buckle (the lamp hangs from it)
    lathe(bm, [(0.178, 0.02), (0.182, 0.05), (0.178, 0.08)], 14, (0, 0, 0), MI['leather'])
    box(bm, -0.035, 0.035, -0.16, -0.135, 0.02, 0.08, MI['brass'])
    # the hose from the reservoir over the right shoulder to the helmet
    tube(bm, [(0.08, 0.14, 0.36), (0.12, 0.12, 0.5), (0.1, 0.06, 0.6), (0.06, 0.02, 0.66)], 0.022, 6, MI['rubber'], cap=False)
prop('diver_torso', torso, smooth=38)

def hips(bm):
    prof = [(0.0, 0.02), (0.182, 0.02), (0.198, -0.06), (0.19, -0.13), (0.155, -0.18), (0.0, -0.19)]
    lathe(bm, prof, 16, (0, 0, 0), MI['rubber'])
    for v in bm.verts: v.co.y *= 0.86
prop('diver_hips', hips, smooth=38)

def tank(bm):
    # the Rouquayrol reservoir: a box of thick iron plate on the back (im033), regulator chamber and its brass ring on top,
    # shoulder straps, a lead weight on the bottom
    box(bm, -0.17, 0.17, 0.0, 0.17, -0.22, 0.2, MI['iron'])
    for zz in (-0.2, -0.05, 0.1):
        box(bm, -0.175, 0.175, -0.005, 0.175, zz, zz + 0.02, MI['iron'])                 # the plate seams
    cylinder(bm, (0, 0.085, 0.2), 0.09, 0.08, 12, MI['brass'])                            # the air chamber
    lathe(bm, [(0.1, 0.27), (0.1, 0.29), (0.0, 0.3)], 12, (0, 0.085, 0), MI['brass'])
    cylinder(bm, (0.12, 0.09, 0.24), 0.018, 0.08, 6, MI['brass'], axis='X')              # the hose union
    box(bm, -0.16, 0.16, 0.0, 0.16, -0.3, -0.22, MI['lead'])
    for s in (-1, 1):
        tube(bm, [(s * 0.11, 0.0, 0.18), (s * 0.12, -0.08, 0.28), (s * 0.12, -0.18, 0.2), (s * 0.11, -0.2, 0.0)], 0.012, 4, MI['leather'], cap=False)
prop('diver_tank', tank)

def upperarm(bm):
    prof = folds([(0.0, 0.05), (0.098, 0.03), (0.096, -0.08), (0.09, -0.18), (0.084, -0.27), (0.0, -0.31)], 0.09, 2.5, -0.16, -0.3)   # baggy, creased at the elbow
    lathe(bm, prof, 12, (0, 0, 0), MI['rubber'])
prop('diver_upperarm', upperarm, smooth=38)

def forearm(bm):
    prof = folds([(0.0, 0.02), (0.084, 0.0), (0.082, -0.1), (0.074, -0.2), (0.058, -0.25), (0.0, -0.26)], 0.09, 2.0, -0.02, -0.14)
    lathe(bm, prof, 12, (0, 0, 0), MI['rubber'])
    lathe(bm, [(0.052, -0.235), (0.056, -0.255), (0.05, -0.27)], 9, (0, 0, 0), MI['brass'])   # the cuff ring
    # the bare hand (im033): palm and the fingers together, the thumb apart
    t = bmesh.new()
    box(t, -0.045, 0.045, -0.022, 0.022, -0.36, -0.27, MI['skin'])
    box(t, -0.04, 0.04, -0.018, 0.018, -0.42, -0.36, MI['skin'])
    box(t, 0.04, 0.065, -0.016, 0.016, -0.34, -0.29, MI['skin'])
    merge_into(bm, t)
prop('diver_forearm', forearm, smooth=38)

def thigh(bm):
    prof = folds([(0.0, 0.03), (0.122, 0.0), (0.12, -0.12), (0.108, -0.26), (0.096, -0.38), (0.0, -0.42)], 0.08, 2.5, -0.26, -0.41)   # baggy breeches, folds over the knee
    lathe(bm, prof, 12, (0, 0, 0), MI['rubber'])
prop('diver_thigh', thigh, smooth=38)

def shin(bm):
    prof = folds([(0.0, 0.03), (0.1, 0.0), (0.096, -0.12), (0.086, -0.26), (0.078, -0.34), (0.0, -0.36)], 0.09, 2.0, -0.01, -0.14)
    lathe(bm, prof, 12, (0, 0, 0), MI['rubber'])
    lathe(bm, [(0.088, -0.3), (0.092, -0.34), (0.086, -0.38)], 12, (0, 0, 0), MI['leather'])   # the boot's laced top
prop('diver_shin', shin, smooth=38)

def boot(bm):
    # a laced canvas-and-leather boot on a thick lead sole, brass toe-cap, straps over the instep (im033)
    # rounder upper over a broad lead sole; the toe swells as Neuville's heavy boots do
    lathe(bm, [(0.0, -0.07), (0.085, -0.07), (0.09, 0.0), (0.085, 0.06), (0.0, 0.07)], 12, (0, 0, 0), MI['leather'])
    t = bmesh.new(); ico(t, (0, -0.15, -0.05), 0.085, 2, MI['leather'], scale=(1.0, 1.25, 0.7)); merge_into(bm, t)
    box(bm, -0.092, 0.092, -0.27, 0.1, -0.14, -0.07, MI['lead'])
    t = bmesh.new(); ico(t, (0, -0.24, -0.075), 0.06, 1, MI['brass'], scale=(1.4, 0.8, 0.7)); merge_into(bm, t)
    for yy in (-0.12, -0.04):
        box(bm, -0.074, 0.074, yy - 0.012, yy + 0.012, -0.075, 0.065, MI['iron'])
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
