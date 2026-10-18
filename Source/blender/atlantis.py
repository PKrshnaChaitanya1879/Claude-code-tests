# Mission II (M5) kit: the night walk to the volcano and the drowned city, after Part II ch. IX and the plates
# im077 (the dead copse), im078 (crustaceans in their holes) and im079 (the summit, the volcano, the ruins).
# Ported and extended from the prototype's reference/blender/build_props.py. Each piece at the origin, base at
# Z = 0 (Blender Z up; exported Y up for Unity). Low-poly, faceted. Materials named for Unity's remap:
#   stone and its seaweed mantle ("sea-weed and fucus threw a thick vegetable mantle"), blossoming zoophytes,
#   black basalt, lava (emissive: "lava, but no flames"), scoriae, dead wood, chalk.
# Run: python3 atlantis.py <outdir>  ->  Atlantis.fbx (+ atlantis.blend)
import sys, os, math, random
sys.path.insert(0, os.path.dirname(__file__))
import bpy, bmesh
from mathutils import Vector, Matrix, noise
from blib import *

OUT = sys.argv[-1] if len(sys.argv) > 1 and not sys.argv[-1].endswith('.py') else '/tmp/atlantis'
os.makedirs(OUT, exist_ok=True)
reset()
M = {
    'stone': mat('M_atl_stone', (0.46, 0.43, 0.38), rough=0.9),          # Tuscan masonry
    'stone_dark': mat('M_atl_stone_dark', (0.30, 0.28, 0.26), rough=0.9),
    'weed': mat('M_atl_weed', (0.16, 0.20, 0.09), rough=0.9),            # the vegetable mantle
    'zoo': mat('M_atl_zoophyte', (0.62, 0.30, 0.32), rough=0.8),         # "a world of blossoming zoophytes"
    'basalt': mat('M_basalt', (0.07, 0.07, 0.08), rough=0.7),
    'scoria': mat('M_scoria', (0.13, 0.10, 0.09), rough=0.95),
    'lava': mat('M_lava', (1.0, 0.35, 0.06), rough=0.6, emit=(1.0, 0.38, 0.08)),
    'lava_crust': mat('M_lava_crust', (0.20, 0.06, 0.03), rough=0.8, emit=(0.3, 0.06, 0.01)),
    'wood': mat('M_deadwood', (0.06, 0.05, 0.05), rough=0.9),
    'chalk': mat('M_chalk', (0.92, 0.92, 0.88), rough=0.9),
    'pennatule': mat('M_pennatule', (0.5, 0.7, 0.8), rough=0.5, emit=(0.35, 0.8, 1.0)),
}
ML = list(M.values()); MI = {k: ML.index(v) for k, v in M.items()}
PROPS = []
def prop(name, build, smooth=None):
    bm = bmesh.new(); build(bm)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = new_obj(name, bm, ML, 'ATL', None, smooth)
    PROPS.append(o)
    return o

def jitter(bm, amt, seed=0):
    r = random.Random(seed)
    for v in bm.verts: v.co += Vector((r.uniform(-amt, amt), r.uniform(-amt, amt), r.uniform(-amt, amt)))

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
        f = bm.faces.new(rings[-1]); f.material_index = mi

def sub(fn, M_=Matrix.Identity(4)):
    t = bmesh.new(); fn(t)
    bmesh.ops.transform(t, matrix=M_, verts=t.verts)
    return t

def mantle(bm, seed=0, up=0.55, mi_w='weed', mi_z='zoo', amount=0.7):
    """The vegetable mantle: upward faces take seaweed in coherent patches, a few zoophytes blossoming among them."""
    off = Vector((seed * 3.1, seed * 1.7, seed * 2.3))
    bm.normal_update()
    for f in bm.faces:
        if f.material_index not in (MI['stone'], MI['stone_dark']): continue
        c = f.calc_center_median()
        k = noise.noise(c * 0.35 + off)
        if f.normal.z > up and k > -amount * 0.6: f.material_index = MI[mi_z] if noise.noise(c * 0.9 - off) > 0.45 else MI[mi_w]
        elif f.normal.z > 0.1 and k > 0.4: f.material_index = MI[mi_w]

# ------------------------------------------------------------ the Tuscan order ("the massive character of Tuscan architecture")
def column(bm, h=5.0, broken=False, seed=0, mi='stone'):
    r = random.Random(seed)
    lathe(bm, [(0.0, 0.0), (0.62, 0.0), (0.62, 0.25), (0.55, 0.32), (0.5, 0.42)], 12, (0, 0, 0), MI[mi])
    top = h if not broken else h * r.uniform(0.35, 0.7)
    lathe(bm, [(0.5, 0.42), (0.47, top * 0.6), (0.42, top)], 12, (0, 0, 0), MI[mi])
    if not broken:
        lathe(bm, [(0.42, top), (0.48, top + 0.1), (0.6, top + 0.25), (0.0, top + 0.25)], 12, (0, 0, 0), MI[mi])
        box(bm, -0.68, 0.68, -0.68, 0.68, top + 0.25, top + 0.45, MI[mi])
    else:
        lathe(bm, [(0.42, top), (0.0, top)], 12, (0, 0, 0), MI[mi])
        for v in bm.verts:
            if abs(v.co.z - top) < 1e-3 and v.co.length > 0.1: v.co.z += r.uniform(-0.3, 0.12)
prop('col_tuscan', lambda bm: (column(bm, 5.0), mantle(bm, 1, amount=0.3)), smooth=30)
prop('col_broken_a', lambda bm: (column(bm, 5.0, True, 2), mantle(bm, 2)), smooth=30)
prop('col_broken_b', lambda bm: (column(bm, 5.0, True, 5), mantle(bm, 3)), smooth=30)
def drum(bm):
    lathe(bm, [(0.0, 0.0), (0.47, 0.0), (0.45, 0.9), (0.0, 0.9)], 12, (0, 0, 0), MI['stone'], axis='X')
    for v in bm.verts: v.co.z += 0.46
    mantle(bm, 4)
prop('col_drum', drum, smooth=30)

def temple(bm, w=16.0, d=9.0, cols=(6, 11), h=5.0, seed=7, ruin=0.45):
    """A peristyle temple, fallen: stylobate of three steps, columns standing or broken, a piece of entablature."""
    r = random.Random(seed)
    for k in range(3):
        box(bm, -w / 2 + k * 0.4, w / 2 - k * 0.4, -d / 2 + k * 0.4, d / 2 - k * 0.4, k * 0.35, (k + 1) * 0.35, MI['stone'], step=2.0)
    base = 1.05
    nx, ny = cols
    standing = []
    for i in range(nx):
        for j in range(ny):
            if 0 < i < nx - 1 and 0 < j < ny - 1: continue            # the peristyle only
            x = -w / 2 + 1.4 + i * (w - 2.8) / (nx - 1); y = -d / 2 + 1.4 + j * (d - 2.8) / (ny - 1)
            roll = r.random()
            if roll < ruin * 0.35: continue                             # gone
            brk = roll < ruin
            t = sub(lambda t: column(t, h, brk, seed * 31 + i * 7 + j), Matrix.Translation((x, y, base)))
            merge_into(bm, t)
            if not brk: standing.append((x, y))
    # a run of entablature still riding the front columns
    front = sorted([s for s in standing if s[1] < -d / 2 + 2.0])
    if len(front) >= 2:
        x0, x1 = front[0][0] - 0.7, front[-1][0] + 0.7
        box(bm, x0, x1, -d / 2 + 0.7, -d / 2 + 2.1, base + h + 0.45, base + h + 1.25, MI['stone'], step=2.0)
    # the cella's walls, broken to different heights
    for (xa, xb, ya, yb) in ((-w / 2 + 3, w / 2 - 3, -d / 2 + 2.6, -d / 2 + 3.2), (-w / 2 + 3, w / 2 - 3, d / 2 - 3.2, d / 2 - 2.6),
                             (-w / 2 + 3, -w / 2 + 3.6, -d / 2 + 2.6, d / 2 - 2.6)):
        top = base + r.uniform(1.2, 3.2)
        box(bm, xa, xb, ya, yb, base, top, MI['stone_dark'], step=1.0)
    jitter(bm, 0.03, seed)
    mantle(bm, seed)
prop('temple_ruin', lambda bm: temple(bm))
prop('temple_ruin_small', lambda bm: temple(bm, 11.0, 7.0, (4, 7), 4.2, 11, 0.6))

def acropolis(bm):
    """'the high base of an Acropolis, with the floating outline of a Parthenon': a cut-rock platform with a ramp,
    and the Parthenon's peristyle (8 x 17) still standing in outline, its roof long gone."""
    r = random.Random(21)
    # the rock base: a stepped mass, faceted
    t = bmesh.new()
    bmesh.ops.create_cube(t, size=1.0)
    for v in t.verts: v.co = Vector((v.co.x * 64, v.co.y * 44, (v.co.z + 0.5) * 12))
    bmesh.ops.subdivide_edges(t, edges=t.edges, cuts=3, use_grid_fill=True)
    for v in t.verts:
        if v.co.z < 11.9: v.co += Vector((noise.noise(v.co * 0.08) * 2.0, noise.noise(v.co * 0.08 + Vector((5, 5, 5))) * 2.0, 0))
    for f in t.faces: f.material_index = MI['stone_dark']
    merge_into(bm, t)
    for k in range(10):     # the ramp up the west face
        box(bm, -36 + k * 1.2, -34.8 + k * 1.2, -4, 4, 0, (k + 1) * 1.2, MI['stone'], step=2.0)
    # the Parthenon's stylobate and peristyle
    W, D, base = 30.0, 14.0, 12.0
    for k in range(3):
        box(bm, -W / 2 + k * 0.5, W / 2 - k * 0.5, -D / 2 + k * 0.5, D / 2 - k * 0.5, base + k * 0.4, base + (k + 1) * 0.4, MI['stone'], step=3.0)
    b2 = base + 1.2
    for i in range(17):
        for j in range(8):
            if 0 < i < 16 and 0 < j < 7: continue
            x = -W / 2 + 1.5 + i * (W - 3) / 16; y = -D / 2 + 1.5 + j * (D - 3) / 7
            roll = r.random()
            if roll < 0.12: continue
            merge_into(bm, sub(lambda t: column(t, 9.0, roll < 0.32, i * 13 + j), Matrix.Translation((x, y, b2))))
    # pediment on the east front, the architrave along one flank
    box(bm, -W / 2 + 0.8, -W / 2 + 2.2, -D / 2 + 0.8, D / 2 - 0.8, b2 + 9.45, b2 + 10.4, MI['stone'], step=3.0)
    box(bm, -W / 2 + 0.8, W / 2 - 6, D / 2 - 2.2, D / 2 - 0.8, b2 + 9.45, b2 + 10.4, MI['stone'], step=3.0)
    tri = [Vector((-W / 2 + 1.5, -D / 2 + 0.8, b2 + 10.4)), Vector((-W / 2 + 1.5, D / 2 - 0.8, b2 + 10.4)), Vector((-W / 2 + 1.5, 0, b2 + 12.6))]
    for dx in (0, 0.8):
        vv = [bm.verts.new(p + Vector((dx, 0, 0))) for p in tri]
        f = bm.faces.new(vv if dx else vv[::-1]); f.material_index = MI['stone']
    mantle(bm, 21, amount=0.5)
prop('acropolis', acropolis)

def aqueduct(bm, bays=6, seed=31):
    """'some remains of a gigantic aqueduct': piers and round arches, two bays fallen."""
    r = random.Random(seed)
    span, H = 6.0, 14.0
    fallen = {2, 4}
    for b in range(bays + 1):
        x = -bays * span / 2 + b * span
        top = H if b not in (3,) else H * 0.55
        box(bm, x - 0.8, x + 0.8, -1.0, 1.0, 0, top, MI['stone'], step=2.0)
    for b in range(bays):
        if b in fallen: continue
        x0 = -bays * span / 2 + b * span
        pts = [(x0 + 0.8 + (span - 1.6) * (0.5 - 0.5 * math.cos(math.pi * i / 8)), 0, H - 2.4 + math.sin(math.pi * i / 8) * (span - 1.6) / 2) for i in range(9)]
        tube(bm, pts, 0.7, 6, MI['stone'])
        box(bm, x0 - 0.8, x0 + span + 0.8, -1.1, 1.1, H, H + 1.6, MI['stone'], step=2.0)    # the channel
    jitter(bm, 0.05, seed)
    mantle(bm, seed)
prop('aqueduct', aqueduct)

def house(bm, w=7.0, d=6.0, seed=41):
    """Roofless walls, doorways and a dislocated arch: 'its roofs open to the sky ... its arches dislocated'."""
    r = random.Random(seed)
    th = 0.5
    for (xa, xb, ya, yb, door) in ((-w / 2, w / 2, -d / 2, -d / 2 + th, True), (-w / 2, w / 2, d / 2 - th, d / 2, False),
                                   (-w / 2, -w / 2 + th, -d / 2, d / 2, False), (w / 2 - th, w / 2, -d / 2, d / 2, r.random() < 0.5)):
        top = r.uniform(1.6, 4.2)
        if door:
            mid = (xa + xb) / 2 if xb - xa > 1 else (ya + yb) / 2
            if xb - xa > 1:
                box(bm, xa, mid - 0.7, ya, yb, 0, top, MI['stone'], step=1.0); box(bm, mid + 0.7, xb, ya, yb, 0, top * r.uniform(0.6, 1.0), MI['stone'], step=1.0)
                if top > 2.6: box(bm, mid - 0.7, mid + 0.7, ya, yb, 2.2, top, MI['stone'])
            else:
                box(bm, xa, xb, ya, mid - 0.7, 0, top, MI['stone'], step=1.0); box(bm, xa, xb, mid + 0.7, yb, 0, top * 0.8, MI['stone'], step=1.0)
        else:
            box(bm, xa, xb, ya, yb, 0, top, MI['stone'], step=1.0)
    for k in range(5):     # rubble inside
        x, y = r.uniform(-w / 3, w / 3), r.uniform(-d / 3, d / 3)
        box(bm, x - 0.4, x + 0.4, y - 0.3, y + 0.3, 0, r.uniform(0.3, 0.6), MI['stone_dark'])
    jitter(bm, 0.04, seed)
    mantle(bm, seed)
prop('house_ruin_a', lambda bm: house(bm))
prop('house_ruin_b', lambda bm: house(bm, 9.0, 5.0, 43))
prop('house_ruin_c', lambda bm: house(bm, 5.5, 5.5, 47))

def quay(bm, L=40.0):
    """'there traces of a quay, as if an ancient port': a long dressed wall with landing steps and bollards."""
    box(bm, -L / 2, L / 2, -2.0, 2.0, 0, 3.0, MI['stone'], step=2.0)
    for x in (-12, 6):
        for k in range(6):
            box(bm, x - 1.5, x + 1.5, -2.0 - (k + 1) * 0.5, -2.0 - k * 0.5, 0, 3.0 - (k + 1) * 0.5, MI['stone'], step=1.5)
    for x in range(-18, 19, 6):
        merge_into(bm, sub(lambda t: lathe(t, [(0, 0), (0.3, 0), (0.25, 0.6), (0.35, 0.8), (0, 0.8)], 8, (0, 0, 0), MI['stone_dark']), Matrix.Translation((x, 1.2, 3.0))))
    jitter(bm, 0.03, 51)
    mantle(bm, 51)
prop('quay', quay)

def street(bm, L=24.0, W=6.0):
    """A broad, deserted street: paving slabs, some lifted."""
    r = random.Random(61)
    for i in range(int(L / 1.5)):
        for j in range(int(W / 1.5)):
            x = -L / 2 + i * 1.5; y = -W / 2 + j * 1.5
            z = r.uniform(0.05, 0.18) if r.random() > 0.08 else 0.35
            box(bm, x + 0.04, x + 1.46, y + 0.04, y + 1.46, -0.1, z, MI['stone'])
    mantle(bm, 61, amount=0.8)
prop('street', street)

# ------------------------------------------------------------ the mountain, the summit, the volcano
def summit(bm):
    """The peak where Nemo stands (im079): a pinnacle with a platform 'a circle of ten yards', falling sheer on the city side."""
    t = bmesh.new()
    bmesh.ops.create_cone(t, cap_ends=True, segments=16, radius1=16.0, radius2=4.6, depth=22.0)
    for v in t.verts:
        v.co.z += 11.0
        n = noise.noise(v.co * 0.12) * 2.5
        if v.co.z < 21.5: v.co.x += n; v.co.y += noise.noise(v.co * 0.12 + Vector((9, 9, 9))) * 2.5
        if v.co.y > 0 and v.co.z < 21.5: v.co.y *= 0.55        # the sheer face toward the city (+Y)
    bmesh.ops.subdivide_edges(t, edges=[e for e in t.edges if e.calc_length() > 3], cuts=3, use_grid_fill=True)
    bmesh.ops.triangulate(t, faces=t.faces)
    for v in t.verts:
        if v.co.z < 21.0: v.co += Vector((noise.noise(v.co * 0.3) * 0.8, noise.noise(v.co * 0.3 + Vector((3, 1, 2))) * 0.8, 0))
    for f in t.faces: f.material_index = MI['basalt']
    merge_into(bm, t)
prop('summit', summit)

def volcano(bm):
    """'At fifty feet above the peak ... a large crater was vomiting forth torrents of lava which fell in a cascade
    of fire': a broad cone with a broken crater rim; the lava runs are a separate piece (emissive)."""
    t = bmesh.new()
    prof = [(0, 0), (90, 0), (70, 18), (45, 42), (24, 64), (18, 70), (14, 66), (6, 58), (0, 58)]
    lathe(t, [(r_, z) for r_, z in prof], 28, (0, 0, 0), MI['scoria'])
    bmesh.ops.subdivide_edges(t, edges=[e for e in t.edges if e.calc_length() > 12], cuts=1)
    for v in t.verts:
        rr = Vector((v.co.x, v.co.y, 0)).length
        if rr > 1: v.co += Vector((v.co.x / rr, v.co.y / rr, 0)) * noise.noise(v.co * 0.05) * 6.0 + Vector((0, 0, noise.noise(v.co * 0.08) * 2.0))
    bm2 = t
    for f in bm2.faces:
        if f.calc_center_median().z > 56: f.material_index = MI['lava_crust']
    merge_into(bm, bm2)
prop('volcano', volcano)

def lava_runs(bm):
    """Torrents of lava down the cone toward the city: glowing ribbons, a crust darkening at their edges."""
    r = random.Random(71)
    for k in range(5):
        a = math.radians(-60 + k * 30 + r.uniform(-8, 8))
        pts = []
        for i in range(10):
            t = i / 9
            rr = 16 + t * 72; z = 66 - 60 * (t ** 0.8)
            pts.append(Vector((math.cos(a) * rr + math.sin(t * 7 + k) * 2.0, math.sin(a) * rr, z + 0.6)))
        w0 = r.uniform(1.6, 3.0)
        for i in range(9):
            p0, p1 = pts[i], pts[i + 1]
            d = (p1 - p0).normalized(); s = Vector((-d.y, d.x, 0)).normalized()
            w = w0 * (1 - 0.5 * i / 9)
            q = [p0 - s * w, p0 + s * w, p1 + s * w * 0.9, p1 - s * w * 0.9]
            f = bm.faces.new([bm.verts.new(v) for v in q]); f.material_index = MI['lava']
            q2 = [p0 - s * w * 1.5 - Vector((0, 0, 0.2)), p0 - s * w, p1 - s * w * 0.9, p1 - s * w * 1.4 - Vector((0, 0, 0.2))]
            f = bm.faces.new([bm.verts.new(v) for v in q2]); f.material_index = MI['lava_crust']
            q3 = [p0 + s * w, p0 + s * w * 1.5 - Vector((0, 0, 0.2)), p1 + s * w * 1.4 - Vector((0, 0, 0.2)), p1 + s * w * 0.9]
            f = bm.faces.new([bm.verts.new(v) for v in q3]); f.material_index = MI['lava_crust']
prop('lava_runs', lava_runs)

def scoria(bm, seed=81):
    t = bmesh.new(); bmesh.ops.create_icosphere(t, subdivisions=1, radius=0.35)
    jitter(t, 0.1, seed)
    for f in t.faces: f.material_index = MI['scoria']
    merge_into(bm, t)
prop('scoria', scoria)

def basalt_slab(bm):
    """The rock of black basalt on which Nemo traced ATLANTIS: a leaning block with one smooth face toward the visitor (-Y)."""
    box(bm, -1.6, 1.6, -0.5, 0.5, 0, 2.4, MI['basalt'], step=0.8)
    for v in bm.verts:
        edge = abs(v.co.x) > 1.5 or v.co.z > 2.3 or v.co.z < 0.1
        if v.co.y > 0: v.co += Vector((noise.noise(v.co * 1.5) * 0.15, noise.noise(v.co * 1.5 + Vector((2, 2, 2))) * 0.2, 0))
        if edge: v.co += Vector((noise.noise(v.co * 2.1 + Vector((7, 1, 3))) * 0.25, 0, noise.noise(v.co * 2.1 + Vector((1, 7, 3))) * 0.2))   # a broken outline, the face kept flat
        v.co.y += v.co.z * 0.12      # leaning back
prop('basalt_slab', basalt_slab)

def cromlech(bm, seed=91):
    """'monumental rocks, leaning on their regularly-cut bases ... like cromlechs of prehistoric times'."""
    r = random.Random(seed)
    box(bm, -1.0, 1.0, -0.8, 0.8, 0, 0.6, MI['stone_dark'])
    t = bmesh.new()
    box(t, -0.8, 0.8, -0.5, 0.5, 0, 4.0, MI['basalt'], step=1.0)
    jitter(t, 0.12, seed)
    bmesh.ops.transform(t, matrix=Matrix.Translation((0, 0, 0.55)) @ Matrix.Rotation(math.radians(r.uniform(8, 16)), 4, 'X'), verts=t.verts)
    merge_into(bm, t)
    mantle(bm, seed)
prop('cromlech', cromlech)

# ------------------------------------------------------------ the petrified copse (im077) and the log bridge
def deadtree(bm, seed=1, h=9.0, pine=False):
    r = random.Random(seed)
    pts = [(0, 0, -0.5)]; x = y = 0
    for i in range(1, 7):
        x += r.uniform(-0.18, 0.18); y += r.uniform(-0.18, 0.18)
        pts.append((x, y, h * i / 6))
    tube(bm, pts, [0.36, 0.3, 0.26, 0.2, 0.14, 0.09, 0.03], 6, MI['wood'])
    nb = 9 if pine else r.randint(4, 7)
    for k in range(nb):
        z = (h * (0.3 + 0.65 * k / nb)) if pine else r.uniform(h * 0.35, h * 0.9)
        a = r.uniform(0, 6.28) if not pine else k * 2.4
        L = (r.uniform(1.4, 2.6) * (1.15 - z / h)) if pine else r.uniform(0.8, 2.4) * (1.2 - z / h)
        p0 = Vector((x * z / h, y * z / h, z))
        p1 = p0 + Vector((math.cos(a) * L, math.sin(a) * L, (-0.3 if pine else r.uniform(-0.1, 0.7))))
        tube(bm, [p0, p1], [0.08, 0.02], 4, MI['wood'])
        if not pine and r.random() < 0.6:     # twigs: "like fine black paper cuttings"
            p2 = p1 + Vector((math.cos(a + 0.7) * L * 0.4, math.sin(a + 0.7) * L * 0.4, L * 0.3))
            tube(bm, [p1, p2], [0.02, 0.006], 3, MI['wood'])
    jitter(bm, 0.02, seed)
for i in range(4):
    prop('deadtree_%d' % i, lambda bm, i=i: deadtree(bm, i + 3, 7.0 + i * 1.5))
prop('dead_pine', lambda bm: deadtree(bm, 17, 16.0, True))      # "here and there overtopped by gigantic pines"
def log(bm):
    tube(bm, [(-4.0, 0, 0), (-1.2, 0.05, 0.05), (1.2, -0.05, 0.02), (4.0, 0, 0)], [0.3, 0.32, 0.3, 0.25], 7, MI['wood'])
    tube(bm, [(2.4, 0, 0.1), (3.0, 0.6, 0.9)], [0.08, 0.02], 4, MI['wood'])
    jitter(bm, 0.015, 70)
prop('log_bridge', log)

def pennatule(bm, seed=101):
    """Sea-pens on the stony plain, 'lit slightly with their phosphorescent gleam'."""
    r = random.Random(seed)
    tube(bm, [(0, 0, 0), (0, 0, 0.35)], [0.015, 0.01], 4, MI['pennatule'])
    for k in range(7):
        z = 0.12 + k * 0.035
        for s in (-1, 1):
            q = [Vector((0, 0, z)), Vector((s * 0.09, 0, z + 0.03)), Vector((s * 0.08, 0, z + 0.06)), Vector((0, 0, z + 0.03))]
            f = bm.faces.new([bm.verts.new(v) for v in q]); f.material_index = MI['pennatule']
            f = bm.faces.new([bm.verts.new(v) for v in q[::-1]]); f.material_index = MI['pennatule']
prop('pennatule', pennatule)

# ------------------------------------------------------------ the word, in chalk: one piece per letter, for Nemo's hand to reveal
def letters():
    x = -1.25
    for i, ch in enumerate('ATLANTIS'):
        cu = bpy.data.curves.new('chalk_%d' % i, 'FONT'); cu.body = ch; cu.size = 0.42; cu.extrude = 0.004
        o = bpy.data.objects.new('chalk_%d' % i, cu); bpy.context.scene.collection.objects.link(o)
        bpy.context.view_layer.objects.active = o
        for oo in bpy.context.selected_objects: oo.select_set(False)
        o.select_set(True)
        bpy.ops.object.convert(target='MESH')
        o = bpy.context.view_layer.objects.active
        o.name = 'chalk_%d' % i
        o.data.materials.clear(); o.data.materials.append(M['chalk'])
        # lay it on the slab's face: Blender text is in XY; stand it up in XZ, facing -Y
        o.data.transform(Matrix.Rotation(math.radians(90), 4, 'X'))
        # in place on basalt_slab's smooth face (-Y, leaning back 1:0.12), about the same origin
        o.data.transform(Matrix.Translation((x, -0.385, 1.05)) @ Matrix.Rotation(-math.atan(0.12), 4, 'X'))
        x += 0.36 if ch != 'I' else 0.2
        PROPS.append(o)
letters()

for o in PROPS:
    if o.type == 'MESH' and not o.name.startswith('chalk'): world_uv(o, 1.0)
bpy.ops.object.select_all(action='DESELECT')
for o in PROPS: o.select_set(True)
bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, 'Atlantis.fbx'), use_selection=True, apply_unit_scale=True,
                         apply_scale_options='FBX_SCALE_UNITS', axis_forward='-Z', axis_up='Y', bake_space_transform=True,
                         object_types={'MESH'}, mesh_smooth_type='FACE', add_leaf_bones=False, path_mode='STRIP')
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'atlantis.blend'))
print('EXPORTED', [(o.name, sum(len(p.vertices) - 2 for p in o.data.polygons)) for o in PROPS])
