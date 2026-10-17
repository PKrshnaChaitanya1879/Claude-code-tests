# Mission I flora (M4), after Part I ch. XV-XVI (the forest of Crespo) and XXIII (the coral kingdom),
# ported and extended from the prototype's reference/blender/build_props.py. Every prop sits at the
# origin, base at Z = 0, so Unity can instance it along the route. Names are the species Verne gives
# (Design Bible species table, priority A first). Low-poly, faceted; colour is in the material, vivid,
# because the lamps and the shallows bring it out (the water model takes it away with distance).
import sys, os, math, random
sys.path.insert(0, os.path.dirname(__file__))
import bpy, bmesh
from mathutils import Vector, Matrix
from blib import *

OUT = sys.argv[-1] if len(sys.argv) > 1 and not sys.argv[-1].endswith('.py') else '/tmp/crespo_flora'
os.makedirs(OUT, exist_ok=True)
reset()
M = {
    'coral_red': mat('M_coral_red', (0.70, 0.07, 0.05), rough=0.6),        # "the Flower of Blood"
    'coral_pink': mat('M_coral_pink', (0.90, 0.45, 0.50), rough=0.6),
    'coral_orange': mat('M_coral_orange', (0.92, 0.42, 0.10), rough=0.6),
    'coral_purple': mat('M_coral_purple', (0.48, 0.16, 0.60), rough=0.6),
    'coral_yellow': mat('M_coral_yellow', (0.92, 0.74, 0.22), rough=0.6),
    'coral_white': mat('M_coral_white', (0.88, 0.86, 0.80), rough=0.7),
    'coral_teal': mat('M_coral_teal', (0.16, 0.56, 0.54), rough=0.6),
    'coral_stone': mat('M_coral_stone', (0.58, 0.52, 0.46), rough=0.9),
    'isis_white': mat('M_isis_white', (0.92, 0.88, 0.78), rough=0.5),
    'isis_gold': mat('M_isis_gold', (0.75, 0.55, 0.22), metal=0.2, rough=0.45),
    'polyp': mat('M_polyp', (0.97, 0.95, 0.9), rough=0.5),
    'kelp': mat('M_kelp', (0.36, 0.40, 0.12), rough=0.7),
    'kelp_dark': mat('M_kelp_dark', (0.20, 0.22, 0.08), rough=0.7),
    'algae_red': mat('M_algae_red', (0.62, 0.10, 0.12), rough=0.7),
    'algae_brown': mat('M_algae_brown', (0.45, 0.30, 0.10), rough=0.7),
    'star_red': mat('M_star_red', (0.80, 0.16, 0.08), rough=0.7),
    'star_orange': mat('M_star_orange', (0.95, 0.52, 0.12), rough=0.7),
    'star_violet': mat('M_star_violet', (0.45, 0.20, 0.62), rough=0.7),
    'shell': mat('M_shell', (0.88, 0.78, 0.66), rough=0.5),
    'rock': mat('M_rock', (0.36, 0.36, 0.34), rough=0.95),
    'anemone': mat('M_anemone', (0.95, 0.40, 0.55), rough=0.5),
    'sponge': mat('M_sponge', (0.85, 0.62, 0.20), rough=0.9),
}
ML = list(M.values()); MI = {k: ML.index(v) for k, v in M.items()}
PROPS = []
def prop(name, build, smooth=None):
    bm = bmesh.new(); build(bm)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = new_obj(name, bm, ML, 'FLORA', None, smooth)
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

def blade(bm, base, a, w, h, n, mi, bend=0.0, twist=0.0):
    """A flat vertical frond, both faces (seen from either side under water)."""
    L, R_ = [], []
    for i in range(n + 1):
        t = i / n
        ang = a + twist * t
        c = Vector(base) + Vector((math.cos(a) * bend * t * t, math.sin(a) * bend * t * t, t * h))
        side = Vector((-math.sin(ang), math.cos(ang), 0)) * w * (math.sin(min(1.0, t * 1.15) * math.pi) * 0.85 + 0.15)
        L.append(c - side); R_.append(c + side)
    for i in range(n):
        q = [L[i], R_[i], R_[i + 1], L[i + 1]]
        f = bm.faces.new([bm.verts.new(v) for v in q]); f.material_index = mi
        f = bm.faces.new([bm.verts.new(v) for v in q[::-1]]); f.material_index = mi

# ------------------------------------------------------------ the forest of Crespo ("the region of perpendicularity")
def laminaria(bm, h=4.4, seed=1):
    """Laminaries: a rigid stipe rising straight to the surface's light, a crown of long blades at the top
    (I.XVI: 'the stems ... rose perpendicularly'). These are the forest's trunks."""
    r = random.Random(seed)
    tube(bm, [(0, 0, 0), (0.03, 0, h * 0.5), (0, 0.03, h)], [0.11, 0.08, 0.05], 6, MI['kelp_dark'])
    lathe(bm, [(0.0, 0.0), (0.3, 0.0), (0.16, 0.14), (0.09, 0.24)], 7, (0, 0, 0), MI['kelp_dark'])     # holdfast
    for k in range(8):
        a = k * 2.4 + r.uniform(-0.3, 0.3)
        blade(bm, (0, 0, h * (0.5 + 0.06 * k)), a, 0.26, h * 0.42, 7, MI['kelp'], bend=0.6, twist=0.5)
prop('laminaria_a', lambda bm: laminaria(bm, 4.4, 1), smooth=40)
prop('laminaria_b', lambda bm: laminaria(bm, 3.4, 2), smooth=40)
def alaria(bm, seed=3):
    """Alariae: 'blades ... like arrows', tall straight leaves in a sheaf."""
    r = random.Random(seed)
    for k in range(6):
        a = k * 1.05 + r.uniform(-0.2, 0.2)
        blade(bm, (math.cos(a) * 0.06, math.sin(a) * 0.06, 0), a, 0.16, r.uniform(2.2, 3.0), 7, MI['kelp'], bend=0.2)
prop('alaria', alaria)
def fucus(bm, seed=10):
    """Fucus: olive ribbons with air-bladders, swaying (im034 hangs them in the trees' light)."""
    r = random.Random(seed)
    for k in range(5):
        a = k * 1.25 + r.uniform(-0.3, 0.3)
        hh = r.uniform(1.0, 1.7)
        blade(bm, (0, 0, 0), a, 0.05, hh, 6, MI['algae_brown'], bend=0.4, twist=1.0)
        for j in range(3):
            t = 0.3 + 0.22 * j
            ico(bm, (math.cos(a) * 0.4 * t * t, math.sin(a) * 0.4 * t * t, hh * t), 0.035, 0, MI['algae_brown'], (1, 1, 1.4))
prop('fucus', fucus)
def red_algae(bm, seed=12):
    """Laurenciae and scarlet ceramies: fine red fronds in tufts."""
    r = random.Random(seed)
    for k in range(9):
        a = r.uniform(0, 2 * math.pi); h = r.uniform(0.25, 0.55)
        tube(bm, [(0, 0, 0), (math.cos(a) * 0.06, math.sin(a) * 0.06, h * 0.5), (math.cos(a) * 0.14, math.sin(a) * 0.14, h)], [0.012, 0.008, 0.003], 3, MI['algae_red'], cap=False)
        for j in range(3):
            t = 0.45 + 0.2 * j; b = a + r.uniform(-1, 1)
            p = Vector((math.cos(a) * 0.1 * t, math.sin(a) * 0.1 * t, h * t))
            tube(bm, [p, p + Vector((math.cos(b) * 0.08, math.sin(b) * 0.08, 0.07))], [0.006, 0.002], 3, MI['algae_red'], cap=False)
prop('red_algae', red_algae)
def padina(bm, seed=13):
    """Pavonari, 'spread like a fan': banded peacock's-tail fans on short stalks."""
    r = random.Random(seed)
    for k in range(5):
        a = r.uniform(0, 2 * math.pi); rr = r.uniform(0.08, 0.15); h = r.uniform(0.08, 0.2)
        c = Vector((math.cos(a) * 0.08, math.sin(a) * 0.08, h))
        for s in range(6):
            t0, t1 = -1.0 + s / 3, -1.0 + (s + 1) / 3
            vs = [c, c + Vector((math.cos(a + t0) * rr, math.sin(a + t0) * rr, rr * 0.9)), c + Vector((math.cos(a + t1) * rr, math.sin(a + t1) * rr, rr * 0.9))]
            mi = MI['algae_brown'] if s % 2 else MI['coral_yellow']
            f = bm.faces.new([bm.verts.new(v) for v in vs]); f.material_index = mi
            f = bm.faces.new([bm.verts.new(v) for v in vs[::-1]]); f.material_index = mi
        tube(bm, [(c.x, c.y, 0), c], [0.008, 0.006], 3, MI['algae_brown'], cap=False)
prop('padina', padina)
def acetabularia(bm, seed=14):
    """Acetabuli, 'stems increase in size upwards': mermaid's wineglasses, a thin stalk and a pale disc."""
    r = random.Random(seed)
    for k in range(9):
        a = r.uniform(0, 2 * math.pi); d = r.uniform(0, 0.12); h = r.uniform(0.08, 0.16)
        x, y = math.cos(a) * d, math.sin(a) * d
        tube(bm, [(x, y, 0), (x, y, h)], [0.003, 0.004], 3, MI['coral_teal'], cap=False)
        lathe(bm, [(0.0, h), (0.03, h + 0.006), (0.0, h + 0.008)], 8, (x, y, 0), MI['coral_teal'])
prop('acetabularia', acetabularia)

# ------------------------------------------------------------ corals and their kin (the coral kingdom)
def branching(bm, mi, depth=4, base=0.05, length=0.35, spread=0.6, seed=0, root=(0, 0, 0), up=(0, 0, 1), tips=None):
    r = random.Random(seed)
    def grow(p, d, rad, L, k):
        q = p + d * L
        tube(bm, [p, p + d * L * 0.5 + Vector((r.uniform(-1, 1), r.uniform(-1, 1), 0)) * L * 0.08, q], [rad, rad * 0.85, rad * 0.7], 5 if k < 2 else 4, mi, cap=False)
        if k >= depth:
            ico(bm, q, rad * 0.9, 0, tips if tips is not None else mi)
            return
        n = 2 if k < 2 else r.choice((2, 2, 3))
        for i in range(n):
            ang = r.uniform(0, 2 * math.pi)
            nd = (d + Vector((math.cos(ang), math.sin(ang), 0)) * spread * r.uniform(0.6, 1.2)).normalized()
            grow(q, nd, rad * 0.72, L * r.uniform(0.7, 0.9), k + 1)
    grow(Vector(root), Vector(up).normalized(), base, length, 0)
prop('red_coral', lambda bm: branching(bm, MI['coral_red'], 4, 0.035, 0.26, 0.8, 3, tips=MI['polyp']), smooth=45)   # white polyps on the blood-red
prop('tuft_coral', lambda bm: branching(bm, MI['coral_orange'], 3, 0.05, 0.3, 0.7, 1), smooth=45)
prop('pink_coral', lambda bm: branching(bm, MI['coral_pink'], 3, 0.045, 0.3, 0.9, 2), smooth=45)
def isis(bm, seed=5):
    """Isis: jointed stems, white segments with gold nodes, in a fan."""
    r = random.Random(seed)
    for k in range(7):
        a = math.radians(-55 + 110 * k / 6); L = r.uniform(0.5, 0.8)
        p = Vector((0, 0, 0))
        d = Vector((math.sin(a), 0, math.cos(a)))
        for s in range(5):
            q = p + d * (L / 5)
            tube(bm, [p, q], [0.012, 0.01], 4, MI['isis_white'], cap=False)
            ico(bm, q, 0.016, 0, MI['isis_gold'])
            d = (d + Vector((r.uniform(-0.15, 0.15), r.uniform(-0.05, 0.05), 0.05))).normalized()
            p = q
prop('isis', isis, smooth=45)
def fan(bm, mi=MI['coral_purple'], seed=4, size=1.0):
    r = random.Random(seed)
    pts = []
    for i in range(14):
        a = math.radians(-70 + 140 * i / 13)
        L = size * (0.7 + 0.3 * r.random())
        p0 = Vector((0, 0, 0.05)); p1 = Vector((math.sin(a) * L * 0.45, 0, 0.05 + math.cos(a) * L * 0.5)); p2 = Vector((math.sin(a) * L, r.uniform(-0.02, 0.02), math.cos(a) * L))
        tube(bm, [p0, p1, p2], [0.02 * size, 0.012 * size, 0.006 * size], 4, mi, cap=False)
        pts.append((p1, p2))
    for i in range(len(pts) - 1):
        for t in (0.35, 0.6, 0.85):
            tube(bm, [pts[i][1] * t, pts[i + 1][1] * t], [0.005 * size, 0.005 * size], 3, mi, cap=False)
    cylinder(bm, (0, 0, -0.05), 0.04 * size, 0.12, 6, mi)
prop('gorgonian_fan', fan, smooth=45)
prop('gorgonian_fan_yellow', lambda bm: fan(bm, MI['coral_yellow'], 7, 0.8), smooth=45)
def brain(bm, mi=MI['coral_yellow']):
    """Zebra-meandrines: grooved domes."""
    t = bmesh.new()
    bmesh.ops.create_icosphere(t, subdivisions=3, radius=0.5)
    for v in t.verts:
        n = v.co.normalized()
        groove = 0.035 * math.sin(n.x * 22 + math.sin(n.y * 9) * 3) * math.sin(n.y * 19)
        v.co = n * (0.5 + groove)
        v.co.z = max(v.co.z * 0.7, -0.05)
    for f in t.faces: f.material_index = mi
    merge_into(bm, t)
prop('brain_coral', brain, smooth=60)
prop('brain_coral_teal', lambda bm: brain(bm, MI['coral_teal']), smooth=60)
def cup_corals(bm, seed=6):
    """Yellow caryophylliae: cup corals in clusters."""
    r = random.Random(seed)
    for k in range(11):
        a = r.uniform(0, 2 * math.pi); d = r.uniform(0, 0.16); h = r.uniform(0.06, 0.16); rr = r.uniform(0.025, 0.04)
        lathe(bm, [(rr * 0.7, 0.0), (rr * 0.8, h * 0.7), (rr * 1.2, h), (rr * 0.9, h - 0.01), (rr * 0.5, h * 0.6)], 7, (math.cos(a) * d, math.sin(a) * d, 0), MI['coral_yellow'])
prop('cup_corals', cup_corals, smooth=45)
def fungia(bm, seed=7):
    """Prickly fungi: mushroom-coral discs with radial ridges, lying on the sand."""
    r = random.Random(seed)
    for k in range(3):
        cx, cy, rr = r.uniform(-0.25, 0.25), r.uniform(-0.25, 0.25), r.uniform(0.09, 0.15)
        n = 18
        ctr = bm.verts.new((cx, cy, rr * 0.35))
        rim = [bm.verts.new((cx + math.cos(2 * math.pi * i / n) * rr * (1.0 if i % 2 else 0.93), cy + math.sin(2 * math.pi * i / n) * rr * (1.0 if i % 2 else 0.93), 0.01 + (0.015 if i % 2 else 0))) for i in range(n)]
        for i in range(n):
            f = bm.faces.new([ctr, rim[i], rim[(i + 1) % n]][::-1]); f.material_index = MI['coral_white']
prop('fungia', fungia, smooth=20)
def anemone(bm, seed=8):
    r = random.Random(seed)
    lathe(bm, [(0.0, 0.0), (0.1, 0.0), (0.09, 0.08), (0.11, 0.12), (0.0, 0.13)], 10, (0, 0, 0), MI['coral_red'])
    for i in range(22):
        a = i * 2 * math.pi / 22; rr = 0.07 + 0.03 * (i % 2)
        p0 = Vector((math.cos(a) * rr, math.sin(a) * rr, 0.12))
        p1 = p0 + Vector((math.cos(a) * 0.06, math.sin(a) * 0.06, 0.12 + r.uniform(0, 0.06)))
        tube(bm, [p0, p1], [0.012, 0.004], 4, MI['anemone'], cap=False)
prop('anemone', anemone, smooth=45)
def sponge(bm, seed=9):
    """Sponges: tubes with open mouths."""
    r = random.Random(seed)
    for k in range(4):
        a = r.uniform(0, 6.28); d = r.uniform(0, 0.12); h = r.uniform(0.25, 0.55); rr = r.uniform(0.05, 0.09)
        lathe(bm, [(rr * 0.8, 0), (rr, h * 0.5), (rr * 1.1, h), (rr * 0.8, h - 0.02), (rr * 0.6, h * 0.4)], 8, (math.cos(a) * d, math.sin(a) * d, 0), MI['sponge'])
prop('sponge', sponge, smooth=45)
def sea_star(bm, mi, seed=0, arms=5, r_arm=0.13):
    """Sea-stars, red, orange or violet, flat on the sand."""
    r = random.Random(seed)
    c = bm.verts.new((0, 0, 0.025))
    ring = []
    for k in range(arms * 2):
        a = k * math.pi / arms
        rr = r_arm if k % 2 == 0 else r_arm * 0.32
        ring.append(bm.verts.new((math.cos(a) * rr, math.sin(a) * rr, 0.008 if k % 2 == 0 else 0.018)))
    for k in range(arms * 2):
        f = bm.faces.new([c, ring[k], ring[(k + 1) % (arms * 2)]]); f.material_index = mi
prop('sea_star_red', lambda bm: sea_star(bm, MI['star_red'], 1), smooth=10)
prop('sea_star_orange', lambda bm: sea_star(bm, MI['star_orange'], 2, 5, 0.1), smooth=10)
prop('sea_star_violet', lambda bm: sea_star(bm, MI['star_violet'], 3, 6, 0.11), smooth=10)
def basket_star(bm, seed=4):
    """Asterophytons, 'like fine lace': basket stars with forking arms, raised like a hand."""
    r = random.Random(seed)
    for k in range(5):
        a = k * 2 * math.pi / 5
        branching(bm, MI['coral_orange'], 2, 0.012, 0.11, 0.9, seed + k, root=(0, 0, 0.03), up=(math.cos(a), math.sin(a), 0.6))
    ico(bm, (0, 0, 0.03), 0.04, 1, MI['coral_orange'], (1, 1, 0.5))
prop('basket_star', basket_star, smooth=45)
def shells(bm, seed=21):
    """Hammer-heads, staircases, red helmet-shells: a scatter of shells on the sand."""
    r = random.Random(seed)
    for k in range(6):
        x, y = r.uniform(-0.3, 0.3), r.uniform(-0.3, 0.3)
        if k % 2 == 0:
            for w in range(4):
                rr = 0.03 * (1 - w * 0.2); hz = w * 0.014
                lathe(bm, [(0.0, hz), (rr, hz + 0.004), (rr * 0.85, hz + 0.014)], 7, (x, y, 0), MI['shell'])
        else:
            ico(bm, (x, y, 0.01), 0.035, 1, MI['shell'], (1.0, 0.8, 0.35))
prop('shells', shells, smooth=40)

# ------------------------------------------------------------ the coral cemetery (I.XXIII)
def coral_tree(bm, seed=31, base=0.35, length=2.2, spread=0.75):
    """'Enormous petrified trees ... joined by garlands of elegant sea-bindweed', red coral at the tips."""
    branching(bm, MI['coral_stone'], 4, base, length, spread, seed, tips=MI['coral_red'])
    jitter(bm, 0.02, seed)
prop('coral_tree', coral_tree, smooth=40)
prop('coral_tree2', lambda bm: coral_tree(bm, 37, 0.28, 1.8, 0.95), smooth=40)
def garland(bm, seed=15):
    """Sea-bindweed garlands hanging between the coral trees (a sagging rope of fronds, 4 m)."""
    r = random.Random(seed)
    pts = [(-2.0 + 4.0 * i / 8, 0, -0.9 * math.sin(math.pi * i / 8)) for i in range(9)]
    tube(bm, pts, 0.025, 4, MI['algae_brown'], cap=False)
    for (x, _, z) in pts[1:-1]:
        blade(bm, (x, 0, z - 0.25), r.uniform(0, 6.28), 0.04, 0.3, 3, MI['kelp'])
prop('bindweed_garland', garland)
def pendant(bm, seed=14):
    """Pendants 'disposed like lustres', hanging from the gallery's vault."""
    r = random.Random(seed)
    for i in range(5):
        a = r.uniform(0, 6.28); d = r.uniform(0, 0.4)
        lathe(bm, [(0.08 + r.uniform(0, 0.05), 0.0), (0.05, -0.4), (0.0, -0.7 - r.uniform(0, 0.6))], 6, (math.cos(a) * d, math.sin(a) * d, 0), MI['coral_stone'])
prop('coral_pendant', pendant, smooth=40)
def arch(bm):
    """A natural arch of coral for the dark gallery."""
    pts = [(-2.6, 0, 0), (-2.5, 0, 1.6), (-2.0, 0, 3.0), (-1.0, 0, 3.8), (0, 0, 4.0), (1.0, 0, 3.8), (2.0, 0, 3.0), (2.5, 0, 1.6), (2.6, 0, 0)]
    tube(bm, pts, [0.7, 0.55, 0.45, 0.4, 0.42, 0.4, 0.45, 0.55, 0.7], 8, MI['coral_stone'])
    jitter(bm, 0.08, 15)
prop('coral_arch', arch, smooth=35)
def cross(bm):
    """'A cross of coral that extended its long arms ... made of petrified blood', on rocks roughly piled."""
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

# ------------------------------------------------------------ export: one FBX, each prop a child at the origin
for o in PROPS: world_uv(o, 1.0)
bpy.ops.object.select_all(action='DESELECT')
for o in PROPS: o.select_set(True)
bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, 'Crespo_Flora.fbx'), use_selection=True, apply_unit_scale=True,
                         apply_scale_options='FBX_SCALE_UNITS', axis_forward='-Z', axis_up='Y', bake_space_transform=True,
                         object_types={'MESH'}, mesh_smooth_type='FACE', add_leaf_bones=False, path_mode='STRIP')
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'crespo_flora.blend'))
for o in PROPS:
    print('PROP', o.name, sum(len(p.vertices) - 2 for p in o.data.polygons))
print('EXPORTED', len(PROPS))
