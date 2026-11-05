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

def ico(bm, c, r, sub=1, mi=0, scale=(1, 1, 1)):
    t = bmesh.new()
    bmesh.ops.create_icosphere(t, subdivisions=sub, radius=r)
    for v in t.verts: v.co = Vector((v.co.x * scale[0], v.co.y * scale[1], v.co.z * scale[2])) + Vector(c)
    for f in t.faces: f.material_index = mi
    merge_into(bm, t)

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
    # 5 Nov 2026: broken, stepped wall-tops (blocks fallen out of the courses), not clean boxes
    for v in bm.verts:
        if v.co.z > 1.4:
            k = noise.noise(Vector((v.co.x * 0.7, v.co.y * 0.7, seed * 0.37)))
            v.co.z = max(1.2, v.co.z - max(0.0, k + 0.15) * 2.2)
    jitter(bm, 0.05, seed)
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

# GUM 4 Nov: "the volcano looks like an ice-cream inverted". Rebuilt from the NOAA footage of West Mata erupting
# (reference/underwater/a_real_submarine_eruption_0.jpg) and Verne's words: no smooth cone, no flames. A heap of black
# scoria and broken blocks, a ragged crater with several vents, lava glowing only in fissures and in tongues that break
# into blocks as they cool ("torrents of lava ... slid to the bottom of the mountain"), boulders thrown out and lying on
# the flanks ("a rain of stones and scoriae"). The vapour is a particle plume in Unity. Real size: radius 48 m, the
# crater rim about 110 m up, placed at scale 1.
VR, VH, CR = 110.0, 110.0, 17.0         # base radius, rim height, crater radius: ~30° scoria flanks
def v_height(x, y):
    """A scoria cone as it really is: lumpy outline, a shallow bowl crater with a sharp rim, the rim breached toward
    the city (+X) where the lava pours out, a collapse scar on one flank, gullies, and no point on top."""
    r = math.hypot(x, y); a = math.atan2(y, x)
    vr = VR * (1.0 + 0.22 * noise.noise(Vector((math.cos(a) * 1.3, math.sin(a) * 1.3, 4.2))))   # lobed outline
    if r >= vr: return -2.0
    breach = math.exp(-((a - (-0.35)) / 0.32) ** 2)                 # the notch the lava pours through
    rim = VH - 10.0 * breach
    if r < CR:
        h = rim - 16.0 * (1.0 - (r / CR) ** 2) * (1.0 - 0.45 * breach)   # the bowl
    else:
        t = (r - CR) / (vr - CR)
        h = rim * (1.0 - t) ** 1.1
        scar = math.exp(-((a - 2.3) / 0.35) ** 2) * math.exp(-((t - 0.4) / 0.22) ** 2) * 14.0   # an old collapse
        h -= scar
        h += abs(noise.noise(Vector((a * 3.1, t * 2.0, 6.6)))) * -9.0 * t * (1 - t) * 3        # gullies
    n = noise.noise(Vector((x * 0.05, y * 0.05, 3.1))) * 5.0 + noise.noise(Vector((x * 0.17, y * 0.17, 8.7))) * 2.0
    return h + n * min(1.0, r / CR)
def v_fissure(x, y):
    """How hot the ground is: high in the crater and along a few fissures running down the flank toward the city (+X)."""
    r = math.hypot(x, y); a = math.atan2(y, x)
    hot = max(0.0, 1.0 - r / (CR * 0.65)) * 0.8                 # only the crater floor glows; its walls are black
    for k, a0 in enumerate((-0.35, 0.05, 0.5, 2.6)):
        da = (a - a0 + math.pi) % (2 * math.pi) - math.pi
        wob = noise.noise(Vector((r * 0.06, k * 3.3, 0.5))) * 0.22
        width = 0.035 + 0.02 * noise.noise(Vector((r * 0.15, k, 2.0)))
        reach = (VR * 0.95) if k < 3 else VR * 0.45
        if r < reach: hot = max(hot, max(0.0, 1.0 - abs(da - wob) / width) * (1.0 - r / reach) ** 0.5)
    return hot
def volcano(bm):
    rnd = random.Random(1869)
    step = 3.0; n = int(VR * 2 / step) + 1
    vs = {}
    for i in range(n):
        for j in range(n):
            x = -VR + i * step + rnd.uniform(-0.45, 0.45); y = -VR + j * step + rnd.uniform(-0.45, 0.45)
            vs[i, j] = bm.verts.new((x, y, v_height(x, y)))
    for i in range(n - 1):
        for j in range(n - 1):
            q = [vs[i, j], vs[i + 1, j], vs[i + 1, j + 1], vs[i, j + 1]]
            c = sum((v.co for v in q), Vector()) / 4
            if math.hypot(c.x, c.y) > VR + 1: continue
            for tri in ((q[0], q[1], q[2]), (q[0], q[2], q[3])):
                f = bm.faces.new(tri); cc = f.calc_center_median()
                heat = v_fissure(cc.x, cc.y)
                f.material_index = MI['lava'] if heat > 0.55 else (MI['lava_crust'] if heat > 0.2 else MI['scoria'])
    # blocks and bombs on the flanks, thicker near the top ("a rain of stones and scoriae")
    for k in range(420):
        r = CR * 0.8 + (VR - CR) * (rnd.random() ** 1.8) * 0.9; a = rnd.uniform(0, 2 * math.pi)
        x, y = math.cos(a) * r, math.sin(a) * r
        s = rnd.uniform(0.8, 3.2) * (1.4 - r / VR)
        t = bmesh.new(); bmesh.ops.create_icosphere(t, subdivisions=1, radius=s)
        for v in t.verts: v.co.x *= rnd.uniform(0.8, 1.4); v.co.z *= rnd.uniform(0.5, 0.9)
        jitter(t, s * 0.25, k)
        hot = v_fissure(x, y) > 0.3
        for f in t.faces: f.material_index = MI['lava_crust'] if hot else MI['scoria']
        merge_into(bm, t, Matrix.Translation((x, y, v_height(x, y) + s * 0.3)) @ Matrix.Rotation(rnd.uniform(0, 6.28), 4, 'Z'))
prop('volcano', volcano)

def lava_runs(bm):
    """The fire itself, so the light comes from lava and not from a glowing ball (GUM 4 Nov): a lava lake in the crater
    bowl broken into dark crust plates with molten seams between them, molten rock spattering up from the vents, and a
    lip of lava spilling through the breach toward the city (+X), breaking into glowing blocks as it falls."""
    rnd = random.Random(71)
    # the lake: a disc just under the rim's inner floor, molten
    lake_z = VH - 16.0 * 0.95 + 1.2
    t = bmesh.new(); bmesh.ops.create_circle(t, cap_ends=True, segments=24, radius=CR * 0.82)
    bmesh.ops.triangulate(t, faces=t.faces)
    for f in t.faces: f.material_index = MI['lava']
    merge_into(bm, t, Matrix.Translation((0, 0, lake_z)))
    # crust plates floating on it, with molten seams showing between them
    for k in range(26):
        rr = CR * 0.75 * math.sqrt(rnd.random()); aa = rnd.uniform(0, 2 * math.pi)
        px, py = math.cos(aa) * rr, math.sin(aa) * rr
        t = bmesh.new(); bmesh.ops.create_circle(t, cap_ends=True, segments=rnd.choice((5, 6, 7)), radius=rnd.uniform(1.4, 3.2))
        for v in t.verts: v.co.x *= rnd.uniform(0.7, 1.3); v.co += Vector((0, 0, rnd.uniform(0.0, 0.25)))
        ext = bmesh.ops.extrude_face_region(t, geom=t.faces[:])
        for v in [e for e in ext['geom'] if isinstance(e, bmesh.types.BMVert)]: v.co.z += 0.35
        for f in t.faces: f.material_index = MI['lava_crust']
        merge_into(bm, t, Matrix.Translation((px, py, lake_z + 0.05)) @ Matrix.Rotation(rnd.uniform(0, 6.28), 4, 'Z'))
    # spatter: molten clots thrown up from three vents, hanging in the water in arcs
    for vx, vy, n in ((0.0, 0.0, 22), (5.5, -3.0, 12), (-4.5, 4.0, 10)):
        for k in range(n):
            h = rnd.uniform(1.0, 16.0); spread = 0.25 * h
            x = vx + rnd.uniform(-spread, spread); y = vy + rnd.uniform(-spread, spread)
            sz = rnd.uniform(0.25, 0.9) * (1.2 - h / 20)
            t = bmesh.new(); bmesh.ops.create_icosphere(t, subdivisions=1, radius=sz); jitter(t, sz * 0.35, 500 + k)
            for f in t.faces: f.material_index = MI['lava'] if h < 9 or rnd.random() < 0.5 else MI['lava_crust']
            merge_into(bm, t, Matrix.Translation((x, y, lake_z + h)))
    # GUM 4 Nov, from the West Mata accounts: "huge, glowing lava bubbles several feet across" rising from the vent
    # (seawater flashing to steam inside a skin of lava), and "low-level, nearly continuous fire fountains"
    for k in range(9):
        h = rnd.uniform(2.0, 14.0); rad = rnd.uniform(0.35, 1.0) * (1.1 - h / 20)
        t = bmesh.new(); bmesh.ops.create_icosphere(t, subdivisions=2, radius=rad); jitter(t, rad * 0.08, 300 + k)
        for f in t.faces: f.material_index = MI['lava'] if h < 7 else MI['lava_crust']
        merge_into(bm, t, Matrix.Translation((rnd.uniform(-1.5, 1.5), rnd.uniform(-1.5, 1.5), lake_z + h)))
    for vx, vy, n in ((0.0, 0.0, 5), (5.5, -3.0, 4), (-4.5, 4.0, 3)):           # fountains: arcs of molten clots
        for f_ in range(n):
            az = rnd.uniform(0, 2 * math.pi); v0 = rnd.uniform(6, 11); el = math.radians(rnd.uniform(55, 80))
            for i in range(1, 9):
                tt = i * 0.16
                x = vx + math.cos(az) * v0 * math.cos(el) * tt; y = vy + math.sin(az) * v0 * math.cos(el) * tt
                z = lake_z + v0 * math.sin(el) * tt - 0.5 * 9.0 * tt * tt * 0.6          # slowed by the water
                if z < lake_z: break
                sz = 0.32 - i * 0.025
                t = bmesh.new(); bmesh.ops.create_icosphere(t, subdivisions=1, radius=max(sz, 0.08)); jitter(t, sz * 0.3, 700 + f_ * 10 + i)
                for f in t.faces: f.material_index = MI['lava'] if i < 6 else MI['lava_crust']
                merge_into(bm, t, Matrix.Translation((x, y, z)))
    # "bands of superheated pillow lava flowing down the volcano's slope": glowing lobes, each crusting as it cools
    for k, a0 in enumerate((-0.35, 0.05, 0.5)):
        r = CR * 1.2
        while r < VR * 0.85:
            a = a0 + noise.noise(Vector((r * 0.06, k * 3.3, 0.5))) * 0.22
            x, y = math.cos(a) * r, math.sin(a) * r
            L = rnd.uniform(2.2, 3.6); rad = rnd.uniform(0.7, 1.2) * (1.15 - r / VR)
            d = Vector((math.cos(a), math.sin(a), 0))
            p0 = Vector((x, y, v_height(x, y) + rad * 0.6)); p1 = p0 + d * L
            p1.z = v_height(p1.x, p1.y) + rad * 0.6
            t = bmesh.new()
            tube(t, [tuple(p0), tuple(p0.lerp(p1, 0.5) + Vector((0, 0, rad * 0.15))), tuple(p1)], [rad * 0.7, rad, rad * 0.7], 7, MI['lava'] if r < VR * 0.55 else MI['lava_crust'])
            merge_into(bm, t)
            r += L * 0.9
    for k in range(70):   # molten blocks tumbling down the main fissure
        r = CR + rnd.random() ** 0.7 * VR * 0.8; a = -0.35 + noise.noise(Vector((r * 0.06, 0, 0.5))) * 0.22 + rnd.uniform(-0.04, 0.04)
        x, y = math.cos(a) * r, math.sin(a) * r
        s = rnd.uniform(0.4, 1.5) * (1.2 - r / VR)
        t = bmesh.new(); bmesh.ops.create_icosphere(t, subdivisions=1, radius=s); jitter(t, s * 0.3, 900 + k)
        for f in t.faces: f.material_index = MI['lava'] if rnd.random() < 0.55 else MI['lava_crust']
        merge_into(bm, t, Matrix.Translation((x, y, v_height(x, y) + s * 0.5)))
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
    """5 Nov 2026: 'trees petrified by the action of the water': gnarled, leafless, mineral. A flared root plate gripping the
    rock, a twisting trunk that splits into heavy limbs, each limb forking into broken, thinning branches ending in blunt
    stubs (no twigs survive), knots and burls along the way. The pines: one tall shaft with whorls of short, drooping,
    snapped-off branches ('here and there overtopped by gigantic pines')."""
    r = random.Random(seed)
    # the root plate: buttress roots spreading out and down into the floor
    for k in range(5 if not pine else 4):
        a = k * 2 * math.pi / (5 if not pine else 4) + r.uniform(-0.3, 0.3)
        L = r.uniform(0.9, 1.6) * h / 9
        tube(bm, [(0, 0, 0.6), (math.cos(a) * L * 0.4, math.sin(a) * L * 0.4, 0.15), (math.cos(a) * L, math.sin(a) * L, -0.25)], [0.3, 0.18, 0.05], 5, MI['wood'])
    # the trunk: a slow twist
    pts = [Vector((0, 0, -0.4))]; x = y = 0.0
    n = 8
    for i in range(1, n + 1):
        x += r.uniform(-0.22, 0.22) * (0.4 if pine else 1); y += r.uniform(-0.22, 0.22) * (0.4 if pine else 1)
        pts.append(Vector((x, y, h * i / n * (1.0 if pine else 0.62))))
    base_r = 0.42 * h / 9
    tube(bm, pts, [base_r * (1 - 0.75 * i / n) for i in range(n + 1)], 7, MI['wood'])
    for i in range(2, n, 2):                                 # burls and knots
        if r.random() < 0.6: ico(bm, pts[i] + Vector((r.uniform(-1, 1), r.uniform(-1, 1), 0)).normalized() * base_r * 0.6, base_r * r.uniform(0.35, 0.55), 1, MI['wood'])
    def limb(p, d, L, rad, k):
        q = p + d * L
        mid = p + d * L * 0.5 + Vector((r.uniform(-1, 1), r.uniform(-1, 1), r.uniform(-0.3, 0.3))) * L * 0.15
        tube(bm, [p, mid, q], [rad, rad * 0.8, rad * 0.62], 5 if k < 2 else 4, MI['wood'], cap=True)
        if k >= 3 or rad < 0.025: return
        for j in range(r.choice((1, 2, 2, 3))):
            if r.random() < 0.18 * k: continue              # snapped off: a blunt stub
            a = r.uniform(0, 2 * math.pi)
            nd = (d + Vector((math.cos(a), math.sin(a), r.uniform(-0.1, 0.5))) * 0.8).normalized()
            limb(q, nd, L * r.uniform(0.55, 0.75), rad * 0.6, k + 1)
    if pine:
        top = pts[-1]
        for w in range(6):                                   # whorls of short drooping branches
            z = h * (0.45 + 0.09 * w); c = Vector((x * z / h, y * z / h, z))
            for k in range(4):
                if r.random() < 0.35: continue
                a = k * math.pi / 2 + w * 0.7 + r.uniform(-0.3, 0.3)
                L = r.uniform(0.9, 2.0) * (1.2 - w * 0.12)
                limb(c, Vector((math.cos(a), math.sin(a), -0.35)).normalized(), L, 0.09, 2)
    else:
        top = pts[-1]
        for j in range(r.randint(3, 4)):                     # the crown: three or four heavy limbs
            a = j * 2 * math.pi / 4 + r.uniform(-0.4, 0.4)
            d = Vector((math.cos(a) * 0.75, math.sin(a) * 0.75, 1.0)).normalized()
            start = pts[r.randint(n - 3, n)]
            limb(start, d, h * r.uniform(0.22, 0.32), base_r * 0.45, 0)
    jitter(bm, 0.015, seed)
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
