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
    'coral_bubble': mat('M_coral_bubble', (0.78, 0.26, 0.30), rough=0.65),     # bubblegum coral (NOAA photographs)
    'coral_bubble_knob': mat('M_coral_bubble_knob', (0.92, 0.48, 0.50), rough=0.6),
    'black_coral': mat('M_black_coral', (0.78, 0.80, 0.62), rough=0.6),        # living black coral: pale cream-green
    'isis_white': mat('M_isis_white', (0.92, 0.88, 0.78), rough=0.5),
    'isis_gold': mat('M_isis_gold', (0.75, 0.55, 0.22), metal=0.2, rough=0.45),
    'polyp': mat('M_polyp', (0.97, 0.95, 0.9), rough=0.5),
    'kelp': mat('M_kelp', (0.46, 0.38, 0.11), rough=0.7),            # gold-olive (giant kelp photographs)
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
def prop(name, build, smooth=None, recalc=True):
    bm = bmesh.new(); build(bm)
    if recalc: bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
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
def ribbon(bm, base, a, w, h, n, mi, ruffle=0.05, lean=0.0, seed=0, out=None):
    """A long crinkled ribbon rising straight up (im035): the edges ruffle in and out of the blade's plane."""
    r = random.Random(seed)
    nrm = Vector((math.cos(a), math.sin(a), 0)); side0 = Vector((-math.sin(a), math.cos(a), 0))
    ph = r.uniform(0, 6.28)
    L, R_ = [], []
    for i in range(n + 1):
        t = i / n
        o = Vector((base[0], base[1], 0)).normalized() if out is None and (base[0] or base[1]) else (out or nrm)
        c = Vector(base) + o * lean * t * t + nrm * 0.05 * math.sin(t * 5 + ph) + Vector((0, 0, t * h))
        ww = w * (0.35 + 0.65 * math.sin(min(1.0, t * 1.08) * math.pi) ** 0.6)
        crinkle = ruffle * math.sin(i * 2.2 + ph)
        L.append(c - side0 * ww + nrm * crinkle); R_.append(c + side0 * ww - nrm * crinkle * 0.6)
    for i in range(n):
        q = [L[i], R_[i], R_[i + 1], L[i + 1]]
        f = bm.faces.new([bm.verts.new(v) for v in q]); f.material_index = mi
        f = bm.faces.new([bm.verts.new(v) for v in q[::-1]]); f.material_index = mi

def laminaria(bm, h=4.4, seed=1):
    """Laminaries after im035 and I.XVI: broad crinkled ribbons rising from a holdfast straight to the light,
    'kept as straight as a rod of iron' (the region of perpendicularity), fawn, olive and brown.
    These are the forest's trunks."""
    r = random.Random(seed)
    lathe(bm, [(0.0, 0.0), (0.3, 0.0), (0.16, 0.14), (0.09, 0.24)], 7, (0, 0, 0), MI['kelp_dark'])     # holdfast
    tube(bm, [(0, 0, 0.1), (0, 0, 0.5)], [0.09, 0.07], 6, MI['kelp_dark'])                               # short stipe
    for k in range(4):
        a = k * 1.57 + r.uniform(-0.4, 0.4)
        hh = h * r.uniform(0.75, 1.0)
        ribbon(bm, (math.cos(a) * 0.15, math.sin(a) * 0.15, 0.45), a + math.pi / 2 + r.uniform(-0.5, 0.5), r.uniform(0.22, 0.32), hh, 16,
               (MI['kelp'], MI['algae_brown'], MI['kelp_dark'])[k % 3], ruffle=0.11, lean=0.7, seed=seed * 10 + k)
def giant_kelp(bm, h=10.0, seed=1, stipes=4):
    """GUM 4 Nov, from the photographs (reference/underwater/giant_kelp_*): Macrocystis, the trees of Verne's forest
    ("their stems rose perpendicularly"). A tangled holdfast; a few thin stipes rising straight to the surface; along each,
    every half metre or so, a long ruffled blade on a small gas bladder, alternating sides and angled up; the last metre and
    a half bends over and lies along the surface as the canopy the sun comes through. Low-poly: blades are 3-segment
    two-sided strips, bladders tetrahedra."""
    r = random.Random(seed)
    # holdfast: a squat tangle of root-like haptera
    for k in range(9):
        a = k * 0.7 + r.uniform(-0.2, 0.2); L = r.uniform(0.25, 0.45)
        tube(bm, [(0, 0, 0.18), (math.cos(a) * L * 0.6, math.sin(a) * L * 0.6, 0.1), (math.cos(a) * L, math.sin(a) * L, -0.02)], [0.05, 0.04, 0.025], 4, MI['kelp_dark'])
    lathe(bm, [(0.0, 0.0), (0.2, 0.0), (0.12, 0.2), (0.05, 0.3)], 6, (0, 0, 0), MI['kelp_dark'])
    for sidx in range(stipes):
        a0 = sidx * 2 * math.pi / stipes + r.uniform(-0.4, 0.4)
        hh = h * r.uniform(0.82, 1.0)
        lean = Vector((math.cos(a0), math.sin(a0), 0)) * r.uniform(0.8, 1.8)
        canopy_dir = Vector((math.cos(a0 + r.uniform(-0.6, 0.6)), math.sin(a0 + r.uniform(-0.6, 0.6)), 0)).normalized()
        cl = r.uniform(2.0, 3.2)                               # canopy length along the surface
        def at(t):                                             # the stipe as a curve: straight up, then laid over at the top
            if t <= 1.0: return Vector((0, 0, 0.25)) + lean * t * t + Vector((0, 0, t * (hh - 0.25))) + Vector((math.sin(t * 9 + sidx) * 0.06, math.cos(t * 7 + sidx) * 0.06, 0))
            u = t - 1.0
            return at(1.0) + canopy_dir * u * cl + Vector((0, 0, -0.15 * u))
        pts = [at(i / 14) for i in range(15)] + [at(1.0 + i / 4) for i in range(1, 5)]
        tube(bm, [tuple(p) for p in pts], [0.035] * len(pts), 4, MI['kelp_dark'], cap=False)
        nblades = int(hh / 0.42)
        for b in range(nblades + 6):
            t = (b + 0.6) / nblades if b < nblades else 1.0 + (b - nblades + 0.5) / 6
            p0 = at(t); side = 1 if b % 2 == 0 else -1
            up = (at(min(t + 0.02, 2.0)) - at(max(t - 0.02, 0.0))).normalized()
            ax = up.cross(Vector((0, 0, 1)) if abs(up.z) < 0.9 else Vector((1, 0, 0))).normalized()
            ang = a0 + side * 1.4 + r.uniform(-0.4, 0.4)
            out = Vector((math.cos(ang), math.sin(ang), 0))
            # the gas bladder
            bl = p0 + out * 0.06
            tv = [bm.verts.new(bl + Vector(d) * 0.05) for d in ((1, 0, -0.4), (-0.5, 0.87, -0.4), (-0.5, -0.87, -0.4), (0, 0, 1.1))]
            for fv in ((0, 1, 2), (0, 3, 1), (1, 3, 2), (2, 3, 0)):
                f = bm.faces.new([tv[i] for i in fv]); f.material_index = MI['algae_brown']
            # the blade: long, narrow, ruffled, angled up from the bladder (in the canopy it trails along the surface)
            L = r.uniform(1.0, 1.6); W = r.uniform(0.09, 0.15)
            dirv = (out * 0.55 + up * 0.85).normalized() if t <= 1.0 else (canopy_dir * 0.8 + out * 0.4).normalized()
            wv = dirv.cross(out).normalized() if abs(dirv.dot(out)) < 0.95 else ax
            prev = None
            sway = Vector((0.55 + r.uniform(-0.2, 0.2), r.uniform(-0.25, 0.25), -0.15 if t > 1.0 else 0.0))   # a gentle current toward +X
            for i in range(5):
                tt = i / 4
                c = bl + dirv * L * tt + (sway - dirv * 0.35 * (1 if t <= 1.0 else 0)) * tt * tt * L   # blades bend and flow
                ww = W * (math.sin(min(1.0, tt * 1.1 + 0.15) * math.pi) * 0.9 + 0.1)
                ruf = out * 0.025 * math.sin(i * 2.5 + b)
                cur = (c - wv * ww + ruf, c + wv * ww - ruf)
                if prev:
                    q = [prev[0], prev[1], cur[1], cur[0]]
                    mi = MI['kelp'] if (b + sidx) % 3 else MI['algae_brown']
                    f = bm.faces.new([bm.verts.new(v) for v in q]); f.material_index = mi
                    f = bm.faces.new([bm.verts.new(v) for v in q[::-1]]); f.material_index = mi
                prev = cur
prop('laminaria_a', lambda bm: giant_kelp(bm, 10.5, 1, 7), smooth=40, recalc=False)   # the names Unity places stay; the plants are giant kelp
prop('laminaria_b', lambda bm: giant_kelp(bm, 8.0, 2, 5), smooth=40, recalc=False)
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
def branching(bm, mi, depth=4, base=0.05, length=0.35, spread=0.6, seed=0, root=(0, 0, 0), up=(0, 0, 1), tips=None, knobs=0.0, planar=0.0):
    """5 Nov 2026: real coral growth (after photographs of Corallium rubrum and the gorgonians): a short thick trunk,
    dichotomous branching that keeps a crown (branches bend back toward the vertical), tapering to blunt tips with
    polyps; optional knobs (budding polyp warts along the branches) and a planar bias (sea-fan-like colonies grow in
    one plane across the current)."""
    r = random.Random(seed)
    def grow(p, d, rad, L, k):
        mid = p + d * L * 0.5 + Vector((r.uniform(-1, 1), r.uniform(-1, 1) * (1 - planar), 0)) * L * 0.1
        q = p + d * L
        tube(bm, [p, mid, q], [rad, rad * 0.88, rad * 0.76], 6 if k < 2 else 5, mi, cap=False)
        ico(bm, q, rad * 0.8, 1, mi)                                   # the fork's swelling: no seams between pieces
        if knobs > 0 and k >= 1:
            for j in range(r.randint(0, 2)):
                t = r.uniform(0.25, 0.8); kp = p + (q - p) * t
                kd = Vector((r.uniform(-1, 1), r.uniform(-1, 1) * (1 - planar), r.uniform(0, 0.5))).normalized()
                ico(bm, kp + kd * rad * 0.7, rad * knobs, 0, tips if tips is not None else mi)
        if k >= depth:
            ico(bm, q + d * rad * 0.4, rad * 1.05, 1, tips if tips is not None else mi)
            return
        n = 2 if k < depth - 1 else r.choice((2, 3, 3))
        base_ang = r.uniform(0, 2 * math.pi)
        for i in range(n):
            ang = base_ang + i * 2 * math.pi / n + r.uniform(-0.4, 0.4)
            side = Vector((math.cos(ang), math.sin(ang) * (1 - planar), 0))
            nd = (d * (1.0 + 0.25 * k) + side * spread * r.uniform(0.7, 1.15)).normalized()   # bends back toward the vertical: a crown
            grow(q, nd, rad * 0.74, L * r.uniform(0.72, 0.9), k + 1)
    grow(Vector(root), Vector(up).normalized(), base, length, 0)

def coral_colony(bm, mi, tips, seed, heads=3, depth=4, base=0.04, length=0.22, spread=0.85, knobs=0.35, planar=0.0):
    """Several colonies from one rock: what a reef wall actually looks like (never a lone twig)."""
    r = random.Random(seed)
    ico(bm, (0, 0, 0.02), 0.12, 1, MI['coral_stone'], scale=(1.4, 1.1, 0.5))      # the encrusted holdfast rock
    for h in range(heads):
        a = r.uniform(0, 2 * math.pi); d = r.uniform(0.0, 0.1)
        up = Vector((r.uniform(-0.25, 0.25), r.uniform(-0.25, 0.25) * (1 - planar), 1))
        branching(bm, mi, depth, base * r.uniform(0.75, 1.1), length * r.uniform(0.8, 1.15), spread, seed * 7 + h,
                  root=(math.cos(a) * d, math.sin(a) * d, 0.04), up=up, tips=tips, knobs=knobs, planar=planar)

prop('red_coral', lambda bm: coral_colony(bm, MI['coral_red'], MI['polyp'], 3, heads=3, depth=4, base=0.035, length=0.21, spread=0.9, knobs=0.45), smooth=45)   # Corallium: blood-red, white polyps
prop('tuft_coral', lambda bm: coral_colony(bm, MI['coral_orange'], MI['coral_yellow'], 1, heads=5, depth=3, base=0.03, length=0.2, spread=0.6, knobs=0.0), smooth=45)
prop('pink_coral', lambda bm: coral_colony(bm, MI['coral_pink'], MI['polyp'], 2, heads=2, depth=4, base=0.04, length=0.24, spread=1.0, knobs=0.3), smooth=45)
def isis(bm, seed=5):
    """Isis (bamboo coral): jointed stems, white chalky segments and dark-gold horny nodes, branching in a loose fan."""
    r = random.Random(seed)
    def stem(p, d, L, n, rad, k):
        for s in range(n):
            q = p + d * (L / n)
            tube(bm, [p, q], [rad, rad * 0.95], 5, MI['isis_white'], cap=False)
            ico(bm, q, rad * 1.35, 1, MI['isis_gold'])
            d = (d + Vector((r.uniform(-0.12, 0.12), r.uniform(-0.04, 0.04), 0.06))).normalized()
            if k < 2 and s in (1, 3) and r.random() < 0.7:
                side = Vector((r.choice((-1, 1)) * 0.6, 0, 0.4))
                stem(q, (d + side).normalized(), L * 0.6, max(2, n - 2), rad * 0.75, k + 1)
            p = q
    for k in range(5):
        a = math.radians(-40 + 80 * k / 4)
        stem(Vector((0, 0, 0)), Vector((math.sin(a), 0, math.cos(a))), r.uniform(0.55, 0.85), 6, 0.014, 0)
prop('isis', isis, smooth=45)
def fan(bm, mi=MI['coral_purple'], seed=4, size=1.0):
    """Gorgonian sea fan: a flat, dense net in one plane across the current. Main branches fan out from a short stalk and
    fork; every neighbouring pair is laced by fine anastomosing cross-links, so the colony reads as a lattice, not spokes."""
    r = random.Random(seed)
    cylinder(bm, (0, 0, -0.04), 0.035 * size, 0.14, 6, mi)
    lines = []                                             # each branch as a polyline in the fan's plane (x, z)
    def branch(p, ang, L, rad, k):
        pts = [p]
        for s in range(4):
            ang += r.uniform(-0.12, 0.12)
            p = p + Vector((math.sin(ang), r.uniform(-0.01, 0.01), math.cos(ang))) * (L / 4)
            pts.append(p)
        tube(bm, pts, [rad * (1 - 0.15 * i) for i in range(len(pts))], 4, mi, cap=False)
        lines.append(pts)
        if k < 2:
            for da in (-0.28, 0.28):
                branch(p, ang + da, L * 0.62, rad * 0.7, k + 1)
    for i in range(6):
        branch(Vector((0, 0, 0.08)), math.radians(-55 + 110 * i / 5), size * r.uniform(0.32, 0.42), 0.014 * size, 0)
    # the net: points scattered evenly over the fan's area (in its plane), each laced to its nearest neighbours
    pts = [q for ln in lines for q in ln[1:]]
    R = size * 0.78
    tries = 0; target = len(pts) + 150
    while len(pts) < target and tries < 6000:
        tries += 1
        a = r.uniform(-1.0, 1.0); rr = R * math.sqrt(r.uniform(0.04, 1.0))
        q = Vector((math.sin(a) * rr, r.uniform(-0.008, 0.008), 0.08 + math.cos(a) * rr * 0.95))
        if all((q - p).length > 0.05 * size for p in pts): pts.append(q)
    done = set()
    for i, a in enumerate(pts):
        near = sorted(((b - a).length, j) for j, b in enumerate(pts) if j != i)
        for dist, j in near[:3]:
            key = (min(i, j), max(i, j))
            if key in done or dist > 0.16 * size: continue
            done.add(key)
            tube(bm, [a, pts[j]], 0.0045 * size, 3, mi, cap=False)
prop('gorgonian_fan', fan, smooth=45)
prop('gorgonian_fan_yellow', lambda bm: fan(bm, MI['coral_yellow'], 7, 0.8), smooth=45)
def brain(bm, mi=MI['coral_yellow']):
    """Zebra-meandrines (brain coral): a low dome covered in long winding valleys and ridges. The meander comes from a
    domain-warped stripe pattern on the sphere; the base flares out where it grows over the rock."""
    t = bmesh.new()
    bmesh.ops.create_icosphere(t, subdivisions=5, radius=0.5)
    def warp(n):
        x, y, z = n.x * 7.0, n.y * 7.0, n.z * 7.0
        for _ in range(2):
            x, y, z = x + 0.9 * math.sin(y * 1.3 + z * 0.7), y + 0.9 * math.sin(z * 1.1 + x * 0.9), z + 0.9 * math.sin(x * 1.2 + y * 0.8)
        return x, y, z
    for v in t.verts:
        n = v.co.normalized()
        x, y, z = warp(n)
        stripe = math.sin(x * 1.7 + y * 1.1 + z * 0.6)
        ridge = (1 - abs(stripe)) ** 1.6                      # thin sharp ridges, rounded valleys between
        v.co = n * (0.5 + 0.04 * ridge - 0.015)
        if v.co.z < 0: v.co.z *= 0.25                       # flat underside
        v.co.z = v.co.z * 0.62
        v.co.x *= 1.0 + 0.08 * max(0.0, 0.1 - v.co.z) * 10; v.co.y *= 1.0 + 0.08 * max(0.0, 0.1 - v.co.z) * 10   # flaring over the rock
    for f in t.faces: f.material_index = mi
    merge_into(bm, t)
prop('brain_coral', brain, smooth=55)
prop('brain_coral_teal', lambda bm: brain(bm, MI['coral_teal']), smooth=55)
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
def paragorgia(bm, seed=31, h=3.0, mi=None, knob=None):
    """GUM 4 Nov, from the NOAA photographs (reference/underwater/bubblegum_coral_*): Verne's "enormous petrified trees" at
    300 yards are bubblegum coral, the one coral that grows into real trees deep down. A thick short trunk; stout branches
    that divide again and again but stay mostly in one plane (a fan-shaped tree facing the current); every tip, and
    knots along the branches, swollen into round knobs ("bubblegum"); thick to the end, never twiggy."""
    mi = MI['coral_bubble'] if mi is None else mi; knob = MI['coral_bubble_knob'] if knob is None else knob
    r = random.Random(seed)
    def grow(p, d, rad, L, k):
        q = p + d * L
        mid = p + d * L * 0.5 + Vector((r.uniform(-1, 1), r.uniform(-0.25, 0.25), r.uniform(-0.4, 0.4))) * L * 0.1
        tube(bm, [p, mid, q], [rad, rad * 0.95, rad * 0.9], 5 if k < 3 else (4 if k < 5 else 3), mi, cap=False)
        if k >= 3 and r.random() < 0.35: ico(bm, mid, rad * 1.5, 0, knob)              # knots along the branch
        if k >= 7 or (k >= 5 and r.random() < 0.18):
            ico(bm, q, max(rad * 1.9, 0.022), 0, knob, scale=(1, 1, 1.2))               # the bubblegum knob
            return
        n = 2 if k < 5 else r.choice((1, 2, 2))
        for i in range(n):
            side = (-1 if i == 0 else 1) * r.uniform(0.22, 0.5) * (1.0 if k < 4 else 0.75)
            nd = (d + Vector((side, r.uniform(-0.1, 0.1), 0))).normalized()           # in the X-Z plane: a fan
            nd = (nd + Vector((0, 0, 0.35 if k < 4 else 0.45))).normalized()
            grow(q, nd, max(rad * 0.74, 0.008), L * r.uniform(0.74, 0.86), k + 1)
    trunk = h * 0.2
    tube(bm, [(0, 0, -0.1), (0, 0, trunk * 0.5), (r.uniform(-0.05, 0.05), 0, trunk)], [0.075 * h / 3, 0.062 * h / 3, 0.055 * h / 3], 6, mi)
    lathe(bm, [(0.0, -0.05), (0.2 * h / 3, -0.05), (0.08 * h / 3, 0.12)], 6, (0, 0, 0), mi)            # its foot on the rock
    for i, side in enumerate((-0.55, -0.18, 0.18, 0.55)):
        grow(Vector((0, 0, trunk)), Vector((side, r.uniform(-0.08, 0.08), 1)).normalized(), 0.042 * h / 3, h * 0.2, 1)
    jitter(bm, 0.006, seed)
prop('coral_tree', lambda bm: paragorgia(bm, 31, 3.0), smooth=40)                                                  # pink-red
prop('coral_tree2', lambda bm: paragorgia(bm, 37, 2.4, MI['coral_white'], MI['polyp']), smooth=40)               # the white form
def garland(bm, seed=15):
    """"Garlands of elegant sea-bindweed" between the trees: black coral (reference/underwater/black_coral_*), a long
    thin whip sagging between two trees and twisting as it goes, with fine feathery side shoots; the living tissue pale
    cream-green (the skeleton that gives it its name is black inside). 4 m, stretched in Unity to the gap."""
    r = random.Random(seed)
    pts = []
    for i in range(17):
        t = i / 16
        pts.append(Vector((-2.0 + 4.0 * t, 0.12 * math.sin(t * 13), -0.9 * math.sin(math.pi * t) + 0.08 * math.cos(t * 11))))
    tube(bm, [tuple(p) for p in pts], 0.018, 4, MI['black_coral'], cap=False)
    for i in range(1, 16):
        p = pts[i]
        for k in range(2):
            a = r.uniform(0, 6.28); d = Vector((math.cos(a) * 0.4, math.sin(a), r.uniform(-0.6, 0.2))).normalized()
            L = r.uniform(0.15, 0.32)
            tube(bm, [tuple(p), tuple(p + d * L * 0.5 + Vector((0, 0, -0.03))), tuple(p + d * L)], [0.008, 0.006, 0.004], 3, MI['black_coral'], cap=False)
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

# ------------------------------------------------------------ the dark gallery's vault (I.XXIII: "a dark gallery ... natural arches")
def gallery_vault(bm, seed=19):
    """A lumpy half-tube of coral rock, 13 m long along Y, 8 m wide, with a few ragged skylights: the way goes dark
    under it (the lamps come on) and the sun falls through the holes in shafts. Two skins so it reads from both sides."""
    r = random.Random(seed)
    L, R0, T = 13.0, 4.1, 0.45
    nu, nv = 14, 18                        # around (0..pi), along
    holes = {(r.randrange(4, 11), r.randrange(2, nv - 2)) for _ in range(6)}
    def P(i, j, rad):
        a = math.pi * i / nu
        n = 1.0 + 0.09 * math.sin(i * 1.7 + j * 0.9) + 0.06 * math.sin(i * 3.1 - j * 1.3)
        return Vector((math.cos(a) * rad * n, -L / 2 + L * j / nv, math.sin(a) * rad * n * 0.95))
    inner = [[bm.verts.new(P(i, j, R0)) for j in range(nv + 1)] for i in range(nu + 1)]
    outer = [[bm.verts.new(P(i, j, R0 + T)) for j in range(nv + 1)] for i in range(nu + 1)]
    for i in range(nu):
        for j in range(nv):
            if (i, j) in holes or (i + 1, j) in holes and (i, j + 1) in holes: continue
            # winding chosen by hand (no normal recalculation): the inner skin faces the axis, the outer skin faces away
            f = bm.faces.new([inner[i][j], inner[i + 1][j], inner[i + 1][j + 1], inner[i][j + 1]]); f.material_index = MI['coral_stone']
            f = bm.faces.new([outer[i][j], outer[i][j + 1], outer[i + 1][j + 1], outer[i + 1][j]]); f.material_index = MI['rock']
    jitter(bm, 0.06, seed)
prop('gallery_vault', gallery_vault, smooth=35, recalc=False)

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
