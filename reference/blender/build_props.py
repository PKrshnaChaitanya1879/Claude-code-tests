# Props for the two excursions: the diving apparatus (after Neuville's engraving: round copper
# helmet with three glass ports, india-rubber dress, copper bands across the chest, lead soles,
# Rouquayrol reservoir on the back, Ruhmkorff lamp at the belt), corals and the coral cemetery,
# petrified trees, rocks, the ruins of Atlantis, and the creatures.
# Each prop sits at the origin (Blender Z up, front = -Y unless noted) so the engine can instance it.
import sys, os, math, random
sys.path.insert(0, os.path.dirname(__file__))
import bpy, bmesh
from mathutils import Vector, Matrix
from blib import *

OUT = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else '/tmp/props.glb'
reset()
R = random.Random(12)
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
    'coral_red': mat('M_coral_red', (0.62, 0.08, 0.06), rough=0.7),
    'coral_orange': mat('M_coral_orange', (0.85, 0.42, 0.12), rough=0.7),
    'coral_purple': mat('M_coral_purple', (0.45, 0.18, 0.55), rough=0.7),
    'coral_yellow': mat('M_coral_yellow', (0.86, 0.72, 0.3), rough=0.7),
    'coral_pink': mat('M_coral_pink', (0.88, 0.5, 0.55), rough=0.7),
    'coral_white': mat('M_coral_white', (0.85, 0.83, 0.78), rough=0.7),
    'coral_teal': mat('M_coral_teal', (0.2, 0.55, 0.55), rough=0.7),
    'coral_stone': mat('M_coral_stone', (0.55, 0.5, 0.45), rough=0.9),
    'polyp': mat('M_polyp', (0.95, 0.92, 0.85), rough=0.5),
    'kelp': mat('M_kelp', (0.38, 0.42, 0.14), rough=0.8),
    'kelp_red': mat('M_kelp_red', (0.42, 0.12, 0.1), rough=0.8),
    'rock': mat('M_rock', (0.36, 0.36, 0.34), rough=0.95),
    'basalt': mat('M_basalt', (0.12, 0.12, 0.12), rough=0.85),
    'stone': mat('M_ruinstone', (0.62, 0.58, 0.5), rough=0.9),
    'deadwood': mat('M_deadwood', (0.1, 0.09, 0.08), rough=0.95),
    'fish_a': mat('M_fish_a', (0.85, 0.75, 0.25), rough=0.4),
    'fish_b': mat('M_fish_b', (0.3, 0.45, 0.7), rough=0.4),
    'fish_c': mat('M_fish_c', (0.75, 0.75, 0.78), rough=0.3),
    'jelly': mat('M_jelly', (0.8, 0.85, 0.95), rough=0.2),
    'crab': mat('M_crab', (0.5, 0.18, 0.1), rough=0.6),
    'eye': mat('M_eye', (0.3, 0.9, 0.7), emit=(1, 1, 1)),
}
ML = list(M.values()); MI = {k: ML.index(v) for k, v in M.items()}

def prop(name, build, smooth=None, props=None):
    bm = bmesh.new(); build(bm)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_obj(name, bm, ML, 'EXT', props, smooth)

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
    """Sweep a circle along a polyline."""
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
        if radii[-1] if isinstance(radii, (list, tuple)) else radii:
            f = bm.faces.new(rings[-1]); f.material_index = mi

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

# ------------------------------------------------------------ corals ("the coral kingdom")
def branching(bm, mi, depth=4, base=0.05, length=0.35, spread=0.6, seed=0, root=(0, 0, 0), up=(0, 0, 1)):
    r = random.Random(seed)
    def grow(p, d, rad, L, k):
        q = p + d * L
        if k > 1: tube(bm, [p, q], [rad, rad * 0.75], 4, mi, cap=False)
        else: tube(bm, [p, p + d * L * 0.5 + Vector((r.uniform(-1, 1), r.uniform(-1, 1), 0)) * L * 0.08, q], [rad, rad * 0.85, rad * 0.7], 6, mi, cap=(k == depth))
        if k >= depth:
            if rad > 0.012: ico(bm, q, rad * 0.9, 0, mi)
            return
        n = 2 if k < 2 else r.choice((2, 2, 3))
        for i in range(n):
            ang = r.uniform(0, 2 * math.pi)
            nd = (d + Vector((math.cos(ang), math.sin(ang), 0)) * spread * r.uniform(0.6, 1.2)).normalized()
            grow(q, nd, rad * 0.72, L * r.uniform(0.7, 0.9), k + 1)
    grow(Vector(root), Vector(up).normalized(), base, length, 0)
prop('coral_branch', lambda bm: branching(bm, MI['coral_orange'], 3, 0.05, 0.34, 0.7, 1), smooth=45)
prop('coral_branch2', lambda bm: branching(bm, MI['coral_purple'], 3, 0.045, 0.3, 0.9, 2), smooth=45)
prop('coral_blood', lambda bm: branching(bm, MI['coral_red'], 4, 0.034, 0.25, 0.8, 3), smooth=45)
prop('coral_white', lambda bm: branching(bm, MI['coral_white'], 3, 0.045, 0.32, 0.6, 9), smooth=45)
def fan(bm, mi=MI['coral_purple'], seed=4, size=1.0):
    r = random.Random(seed)
    # a gorgonian fan: flat lattice of thin branches in the XZ plane
    pts = []
    for i in range(14):
        a = math.radians(-70 + 140 * i / 13)
        L = size * (0.7 + 0.3 * r.random())
        p0 = Vector((0, 0, 0.05)); p1 = Vector((math.sin(a) * L * 0.45, 0, 0.05 + math.cos(a) * L * 0.5)); p2 = Vector((math.sin(a) * L, r.uniform(-0.02, 0.02), math.cos(a) * L))
        tube(bm, [p0, p1, p2], [0.02 * size, 0.012 * size, 0.006 * size], 4, mi, cap=False)
        pts.append((p1, p2))
    for i in range(len(pts) - 1):
        for t in (0.35, 0.6, 0.85):
            a = pts[i][1] * t; b = pts[i + 1][1] * t
            tube(bm, [a, b], [0.005 * size, 0.005 * size], 3, mi, cap=False)
    cylinder(bm, (0, 0, -0.05), 0.04 * size, 0.12, 6, mi)
prop('coral_fan', fan, smooth=45)
prop('coral_fan2', lambda bm: fan(bm, MI['coral_yellow'], 7, 0.8), smooth=45)
def brain(bm, mi=MI['coral_yellow']):
    t = bmesh.new()
    bmesh.ops.create_icosphere(t, subdivisions=3, radius=0.5)
    for v in t.verts:
        n = v.co.normalized()
        groove = 0.035 * math.sin(n.x * 22 + math.sin(n.y * 9) * 3) * math.sin(n.y * 19)
        v.co = n * (0.5 + groove)
        v.co.z = max(v.co.z * 0.7, -0.05)
    for f in t.faces: f.material_index = mi
    merge_into(bm, t)
prop('coral_brain', brain, smooth=60)
prop('coral_brain2', lambda bm: brain(bm, MI['coral_teal']), smooth=60)
def table(bm):
    lathe(bm, [(0.0, 0.0), (0.08, 0.0), (0.06, 0.25), (0.3, 0.38), (0.7, 0.42), (0.75, 0.47), (0.0, 0.5)], 14, (0, 0, 0), MI['coral_stone'])
    jitter(bm, 0.03, 5)
prop('coral_table', table, smooth=45)
def tubes(bm):
    r = random.Random(6)
    for i in range(7):
        a = r.uniform(0, 6.28); d = r.uniform(0, 0.18)
        h = r.uniform(0.3, 0.8); rr = r.uniform(0.04, 0.08)
        lathe(bm, [(rr * 0.8, 0), (rr, h * 0.5), (rr * 1.1, h), (rr * 0.8, h - 0.02), (rr * 0.6, h * 0.4)], 8, (math.cos(a) * d, math.sin(a) * d, 0), MI['coral_pink'])
prop('coral_tubes', tubes, smooth=45)
def anemone(bm):
    r = random.Random(8)
    lathe(bm, [(0.0, 0.0), (0.1, 0.0), (0.09, 0.08), (0.11, 0.12), (0.0, 0.13)], 10, (0, 0, 0), MI['coral_red'])
    for i in range(22):
        a = i * 2 * math.pi / 22; rr = 0.07 + 0.03 * (i % 2)
        p0 = Vector((math.cos(a) * rr, math.sin(a) * rr, 0.12))
        p1 = p0 + Vector((math.cos(a) * 0.06, math.sin(a) * 0.06, 0.12 + r.uniform(0, 0.06)))
        tube(bm, [p0, p1], [0.012, 0.004], 4, MI['coral_pink'])
prop('anemone', anemone, smooth=45)
def polyp(bm):
    # a living flower of the coral: white petals that retreat into their red case when a hand comes near
    lathe(bm, [(0.0, 0.0), (0.02, 0.0), (0.018, 0.04), (0.0, 0.045)], 6, (0, 0, 0), MI['coral_red'])
    for i in range(8):
        a = i * math.pi / 4
        tube(bm, [(0, 0, 0.04), (math.cos(a) * 0.035, math.sin(a) * 0.035, 0.07)], [0.006, 0.002], 3, MI['polyp'])
prop('polyp', polyp, smooth=45)
def fucus(bm, mi=MI['kelp'], h=4.0, seed=10):
    # rigid perpendicular blades ("the region of perpendicularity")
    r = random.Random(seed)
    n = 9
    for b in range(3):
        a = b * 2.1 + r.uniform(-0.3, 0.3)
        w = 0.12 + r.uniform(0, 0.08)
        hh = h * (0.7 + 0.3 * r.random())
        L, Rr = [], []
        for i in range(n + 1):
            t = i / n
            c = Vector((math.cos(a) * 0.05 * t, math.sin(a) * 0.05 * t, t * hh))
            side = Vector((-math.sin(a), math.cos(a), 0)) * w * (math.sin(t * math.pi) * 0.9 + 0.1)
            L.append(bm.verts.new(c - side)); Rr.append(bm.verts.new(c + side))
        for i in range(n):
            f = bm.faces.new([L[i], Rr[i], Rr[i + 1], L[i + 1]]); f.material_index = mi
    cylinder(bm, (0, 0, 0), 0.02, h * 0.95, 4, mi, r2=0.008)
prop('fucus', fucus)
prop('fucus_red', lambda bm: fucus(bm, MI['kelp_red'], 2.4, 11))
def coral_tree(bm):
    # an enormous petrified tree of the coral forest, joined by garlands of sea-bindweed
    branching(bm, MI['coral_stone'], 4, 0.35, 2.2, 0.75, 31)
    jitter(bm, 0.02, 31)
prop('coral_tree', coral_tree, smooth=40)
def coral_tree2(bm):
    branching(bm, MI['coral_stone'], 4, 0.28, 1.8, 0.95, 37)
prop('coral_tree2', coral_tree2, smooth=40)
def pendant(bm):
    # pendants disposed like lustres, hanging from the gallery arches
    r = random.Random(14)
    for i in range(5):
        a = r.uniform(0, 6.28); d = r.uniform(0, 0.4)
        lathe(bm, [(0.08 + r.uniform(0, 0.05), 0.0), (0.05, -0.4), (0.0, -0.7 - r.uniform(0, 0.6))], 6, (math.cos(a) * d, math.sin(a) * d, 0), MI['coral_stone'])
prop('pendant', pendant, smooth=40)
def arch(bm):
    # a natural arch of coral for the dark gallery
    pts = [(-2.6, 0, 0), (-2.5, 0, 1.6), (-2.0, 0, 3.0), (-1.0, 0, 3.8), (0, 0, 4.0), (1.0, 0, 3.8), (2.0, 0, 3.0), (2.5, 0, 1.6), (2.6, 0, 0)]
    tube(bm, pts, [0.7, 0.55, 0.45, 0.4, 0.42, 0.4, 0.45, 0.55, 0.7], 8, MI['coral_stone'])
    jitter(bm, 0.08, 15)
prop('coral_arch', arch, smooth=35)
def cross(bm):
    # a cross of coral that extended its long arms, made of petrified blood; on a pedestal of rocks roughly piled
    tube(bm, [(0, 0, 0.7), (0.02, 0, 1.4), (0, 0, 2.3)], [0.13, 0.11, 0.1], 7, MI['coral_red'])
    tube(bm, [(-0.55, 0, 1.75), (0, 0, 1.8), (0.55, 0, 1.75)], [0.08, 0.11, 0.08], 7, MI['coral_red'])
    jitter(bm, 0.015, 16)
    for i in range(7):
        a = i * 0.9; d = 0.25 + (i % 3) * 0.12
        ico(bm, (math.cos(a) * d, math.sin(a) * d, 0.25 + (i % 2) * 0.25), 0.28 + (i % 3) * 0.05, 1, MI['rock'], (1.0, 0.9, 0.7))
prop('coral_cross', cross, smooth=40)
def mound(bm):
    t = bmesh.new()
    bmesh.ops.create_icosphere(t, subdivisions=2, radius=1.0)
    for v in t.verts: v.co = Vector((v.co.x * 0.55, v.co.y * 1.05, max(-0.02, v.co.z * 0.22)))
    for f in t.faces: f.material_index = MI['coral_white']
    merge_into(bm, t); jitter(bm, 0.02, 17)
prop('grave_mound', mound, smooth=50)

# ------------------------------------------------------------ rocks
for i in range(6):
    def rock(bm, i=i):
        t = bmesh.new(); bmesh.ops.create_icosphere(t, subdivisions=1 if i % 2 else 2, radius=1.0)
        rr = random.Random(40 + i)
        for v in t.verts:
            v.co *= 1 + rr.uniform(-0.18, 0.18)
            v.co.z *= 0.55 + 0.3 * rr.random()
        for f in t.faces: f.material_index = MI['basalt' if i == 5 else 'rock']
        merge_into(bm, t)
    prop('rock_%d' % i, rock)
def slab(bm):
    # a rock of black basalt with a flat face, where the captain writes with chalk
    box(bm, -1.1, 1.1, -0.35, 0.35, 0, 2.0, MI['basalt'])
    jitter(bm, 0.05, 50)
prop('basalt_slab', slab)

# ------------------------------------------------------------ Atlantis: Tuscan order, temples, aqueduct, quay
def column(bm, h=5.0, broken=False, seed=0):
    r = random.Random(seed)
    lathe(bm, [(0.0, 0.0), (0.62, 0.0), (0.62, 0.25), (0.55, 0.32), (0.5, 0.42)], 14, (0, 0, 0), MI['stone'])
    top = h if not broken else h * r.uniform(0.35, 0.7)
    lathe(bm, [(0.5, 0.42), (0.47, top * 0.6), (0.42, top)], 14, (0, 0, 0), MI['stone'])
    if not broken:
        lathe(bm, [(0.42, top), (0.48, top + 0.1), (0.6, top + 0.25), (0.0, top + 0.25)], 14, (0, 0, 0), MI['stone'])
        box(bm, -0.68, 0.68, -0.68, 0.68, top + 0.25, top + 0.45, MI['stone'])
    else:
        # jagged break
        for v in bm.verts:
            if abs(v.co.z - top) < 1e-3: v.co.z += r.uniform(-0.25, 0.15)
prop('col_tuscan', lambda bm: column(bm, 5.0), smooth=30)
prop('col_broken', lambda bm: column(bm, 5.0, True, 2), smooth=30)
prop('col_broken2', lambda bm: column(bm, 5.0, True, 5), smooth=30)
def drum(bm):
    lathe(bm, [(0.0, 0.0), (0.47, 0.0), (0.45, 0.9), (0.0, 0.9)], 14, (0, 0, 0), MI['stone'], axis='X')
prop('col_drum', drum, smooth=30)
def temple_base(bm):
    for k in range(3):
        box(bm, -6 + k * 0.4, 6 - k * 0.4, -3.5 + k * 0.4, 3.5 - k * 0.4, k * 0.35, (k + 1) * 0.35, MI['stone'], step=1.5)
prop('temple_base', temple_base)
def entablature(bm):
    box(bm, -5.6, 5.6, -0.6, 0.6, 0.0, 0.7, MI['stone'], step=1.0)
    box(bm, -5.7, 5.7, -0.7, 0.7, 0.7, 0.9, MI['stone'], step=1.0)
prop('entablature', entablature)
def pediment(bm):
    vs = [(-5.8, 0), (5.8, 0), (0, 1.8)]
    for y in (-0.4, 0.4):
        f = bm.faces.new([bm.verts.new(Vector((x, y, z))) for (x, z) in (vs if y < 0 else vs[::-1])]); f.material_index = MI['stone']
    a = [bm.verts.new(Vector((x, -0.4, z))) for (x, z) in vs]; b = [bm.verts.new(Vector((x, 0.4, z))) for (x, z) in vs]
    for i in range(3):
        f = bm.faces.new([a[i], a[(i + 1) % 3], b[(i + 1) % 3], b[i]]); f.material_index = MI['stone']
prop('pediment', pediment)
def wall_block(bm):
    box(bm, -2.0, 2.0, -0.4, 0.4, 0, 2.2, MI['stone'], step=1.0)
    jitter(bm, 0.04, 60)
prop('wall_block', wall_block)
def aqueduct(bm):
    # one bay of a gigantic aqueduct: two piers and a round arch
    for x in (-2.4, 1.6):
        box(bm, x, x + 0.8, -0.6, 0.6, 0, 6.0, MI['stone'], step=1.0)
    pts = []
    for i in range(9):
        a = math.pi * i / 8
        pts.append((math.cos(a) * -2.0, 0, 6.0 + math.sin(a) * 2.0))
    tube(bm, pts, 0.42, 6, MI['stone'])
    box(bm, -2.4, 2.4, -0.7, 0.7, 8.0, 9.0, MI['stone'], step=1.0)
prop('aqueduct', aqueduct, smooth=30)
def stairs(bm):
    for k in range(6):
        box(bm, -2.5, 2.5, -k * 0.45, 0.45 - k * 0.45, 0, (6 - k) * 0.25, MI['stone'], step=1.2)
prop('stairs', stairs)

# ------------------------------------------------------------ petrified trees of the Atlantic copse
def deadtree(bm, seed=1, h=9.0):
    r = random.Random(seed)
    pts = [(0, 0, -0.5)]
    x = y = 0
    for i in range(1, 7):
        x += r.uniform(-0.15, 0.15); y += r.uniform(-0.15, 0.15)
        pts.append((x, y, h * i / 6))
    tube(bm, pts, [0.32, 0.28, 0.24, 0.2, 0.14, 0.09, 0.03], 6, MI['deadwood'])
    for k in range(r.randint(3, 6)):
        z = r.uniform(h * 0.35, h * 0.9)
        a = r.uniform(0, 6.28); L = r.uniform(0.6, 2.0) * (1.2 - z / h)
        p0 = Vector((x * z / h, y * z / h, z))
        tube(bm, [p0, p0 + Vector((math.cos(a) * L, math.sin(a) * L, r.uniform(-0.2, 0.6)))], [0.07, 0.015], 4, MI['deadwood'])
    jitter(bm, 0.02, seed)
for i in range(4):
    prop('deadtree_%d' % i, lambda bm, i=i: deadtree(bm, i + 3, 7.0 + i * 1.5), smooth=None)
def log(bm):
    tube(bm, [(-3.5, 0, 0), (-1.0, 0.05, 0.05), (1.0, -0.05, 0.02), (3.5, 0, 0)], [0.28, 0.3, 0.28, 0.24], 7, MI['deadwood'])
    jitter(bm, 0.015, 70)
prop('log_bridge', log)

# ------------------------------------------------------------ creatures
def fish(bm, mi, L=0.25, tall=0.35):
    # front = +X; vertex shader wiggles by x
    prof = [(0.0, -0.5), (0.35, -0.35), (0.5, 0.0), (0.42, 0.25), (0.25, 0.45), (0.08, 0.5)]
    for v in []: pass
    lathe(bm, [(0.0, L * 0.5), (L * 0.12, L * 0.38), (L * 0.18, L * 0.1), (L * 0.15, -L * 0.2), (L * 0.06, -L * 0.42), (0.0, -L * 0.45)], 8, (0, 0, 0), mi, axis='X')
    for v in bm.verts: v.co.z *= tall / 0.18 * 0.18 / max(0.18, 0.18); v.co.y *= 0.45; v.co.z *= 1.6
    # tail
    tv = [Vector((-L * 0.42, 0, 0)), Vector((-L * 0.75, 0, L * 0.22)), Vector((-L * 0.68, 0, 0)), Vector((-L * 0.75, 0, -L * 0.22))]
    vv = [bm.verts.new(v) for v in tv]
    f = bm.faces.new([vv[0], vv[1], vv[2]]); f.material_index = mi
    f = bm.faces.new([vv[0], vv[2], vv[3]]); f.material_index = mi
prop('fish_a', lambda bm: fish(bm, MI['fish_a'], 0.24), smooth=45)
prop('fish_b', lambda bm: fish(bm, MI['fish_b'], 0.3), smooth=45)
prop('fish_c', lambda bm: fish(bm, MI['fish_c'], 0.16), smooth=45)
def jelly(bm):
    lathe(bm, [(0.0, 0.18), (0.12, 0.15), (0.2, 0.06), (0.22, 0.0), (0.16, 0.02), (0.0, 0.05)], 12, (0, 0, 0), MI['jelly'])
    for i in range(8):
        a = i * math.pi / 4
        tube(bm, [(math.cos(a) * 0.15, math.sin(a) * 0.15, 0.0), (math.cos(a) * 0.17, math.sin(a) * 0.17, -0.3), (math.cos(a) * 0.12, math.sin(a) * 0.12, -0.7)], [0.008, 0.005, 0.002], 3, MI['jelly'])
prop('jelly', jelly, smooth=45)
def crab(bm):
    # titanic crab "pointed like a gun on its carriage"
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
    # giant lobsters setting themselves up like halberdiers
    tube(bm, [(0, 1.2, 0.3), (0, 0.6, 0.35), (0, 0.0, 0.4), (0, -0.5, 0.42)], [0.1, 0.2, 0.26, 0.22], 7, MI['crab'])
    for s in (-1, 1):
        tube(bm, [(0.15 * s, -0.5, 0.45), (0.4 * s, -1.0, 0.6), (0.3 * s, -1.6, 0.7)], [0.06, 0.08, 0.05], 5, MI['crab'])
        ico(bm, (0.3 * s, -1.75, 0.7), 0.15, 1, MI['crab'], (0.7, 1.4, 0.5))
        tube(bm, [(0.08 * s, -0.55, 0.55), (0.6 * s, -1.6, 1.4), (1.0 * s, -2.4, 1.6)], [0.015, 0.01, 0.004], 3, MI['crab'])
        ico(bm, (0.1 * s, -0.6, 0.6), 0.035, 1, MI['eye'])
prop('lobster_giant', lobster, smooth=40)

objs = [o for o in coll('EXT').objects if o.type == 'MESH' and len(o.data.vertices)]
for o in objs: world_uv(o, 1.0)
for i, o in enumerate(objs): o.location = ((i % 8) * 16.0, (i // 8) * 16.0, 0)
bake_ao([o for o in coll('EXT').objects if o.type == 'MESH' and len(o.data.vertices)], distance=0.6, samples=int(os.environ.get('AO_SAMPLES', '16')))
for o in objs: o.location = (0, 0, 0)
export(OUT)
print('EXPORTED', OUT, len(coll('EXT').objects))
