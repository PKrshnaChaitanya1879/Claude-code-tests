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
M = {'crab': mat('M_crab', (0.72, 0.16, 0.06), rough=0.55),                 # deep-sea red crab (NOAA): vivid orange-red
     'spider': mat('M_spidercrab', (0.78, 0.36, 0.16), rough=0.7),           # Japanese spider crab: orange
     'eye': mat('M_eye', (0.4, 1.0, 0.75), emit=(0.4, 1.0, 0.75)),
     'spot': mat('M_spot', (0.93, 0.9, 0.82), rough=0.7),                    # white spots
     'lobster': mat('M_lobster', (0.42, 0.18, 0.1), rough=0.6),              # spiny lobster: red-brown
     'lobster_band': mat('M_lobster_band', (0.95, 0.62, 0.18), rough=0.6)}
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

def leg(bm, p0, dirxy, lengths, lift, drop, rad, mi, joints_mi=None):
    """A jointed leg: up and out to the knee, then down to the tip; little knuckles at the joints."""
    p1 = p0 + dirxy * lengths[0] + Vector((0, 0, lift))
    p2 = p1 + dirxy * lengths[1] + Vector((0, 0, lift * 0.2))
    p3 = p2 + dirxy * lengths[2] * 0.5 + Vector((0, 0, -drop))
    band = joints_mi if joints_mi is not None else mi
    for k, (a, b, ra, rb) in enumerate(((p0, p1, rad, rad * 0.85), (p1, p2, rad * 0.85, rad * 0.6), (p2, p3, rad * 0.6, rad * 0.25))):
        m_ = (a + b) * 0.5
        tube(bm, [a, a.lerp(b, 0.42)], [ra, ra * 0.95], 5, mi); tube(bm, [a.lerp(b, 0.42), a.lerp(b, 0.58)], [ra * 0.95, ra * 0.93], 5, band)
        tube(bm, [a.lerp(b, 0.58), b], [ra * 0.93, rb], 5, mi)
    for p in (p1, p2): ico(bm, p, rad * 1.15, 0, band)

def sea_spider(bm):
    """The Japanese spider crab (reference/underwater/japanese_spider_crab_*), Verne's "monstrous sea-spider": a small
    rounded, knobbly body low on enormously long jointed legs (span about 3 m), slender arms with small claws, orange
    with white spots."""
    ico(bm, (0, 0, 0.52), 0.3, 1, MI['spider'], (1.0, 1.15, 0.62))
    ico(bm, (0, -0.2, 0.52), 0.08, 1, MI['spider'], (0.8, 1.2, 0.7))                  # the rostrum
    r = random.Random(4)
    for k in range(14):                                                            # knobs and white spots on the carapace
        a = r.uniform(0, 6.28); z = r.uniform(0.5, 0.6)
        ico(bm, (math.cos(a) * 0.22, math.sin(a) * 0.25, z + 0.04), 0.04, 0, MI['spot'] if k % 2 else MI['spider'])
    for s_ in (-1, 1):
        for k in range(4):
            a = math.radians(-55 + k * 32)
            d = Vector((math.sin(a) * s_, math.cos(a), 0)).normalized()
            leg(bm, Vector((0.22 * s_, math.cos(a) * 0.12, 0.5)), d, (0.6, 0.65, 0.6), 0.3, 0.8, 0.04, MI['spider'], MI['spot'])
        d = Vector((0.45 * s_, -1, 0)).normalized()
        leg(bm, Vector((0.08 * s_, -0.22, 0.52)), d, (0.3, 0.3, 0.2), 0.12, 0.2, 0.025, MI['spider'], MI['spot'])   # the arms
        tube(bm, [(0.04 * s_, -0.25, 0.56), (0.05 * s_, -0.27, 0.62)], [0.01, 0.008], 4, MI['spider'])
        ico(bm, (0.05 * s_, -0.27, 0.63), 0.02, 0, MI['eye'])
prop('sea_spider', sea_spider, smooth=40)

def crab(bm):
    """Atlantis's "titanic crabs" at 150 fathoms: the deep-sea red crab (NOAA, reference/underwater/deep_sea_red_crab_*).
    A broad smooth shell wider than long with a few teeth at the front corners, strong long walking legs, claws held
    forward; vivid orange-red under a light, black in the dark; eyes that catch the glow."""
    ico(bm, (0, 0, 0.42), 0.6, 2, MI['crab'], (1.25, 0.9, 0.42))
    for s_ in (-1, 1):
        for k in range(3):                                                         # front-corner teeth
            ico(bm, (s_ * (0.55 + k * 0.1), -0.32 + k * 0.08, 0.45), 0.05, 0, MI['crab'], (1.0, 1.6, 0.6))
        ico(bm, (0.12 * s_, -0.55, 0.62), 0.05, 0, MI['crab'])   # eye stalk
        for k in range(4):
            a = math.radians(-35 + k * 28)
            d = Vector((math.sin(math.radians(70)) * s_, math.cos(math.radians(70)) * 0.3 + (k - 1.5) * 0.35, 0)).normalized()
            leg(bm, Vector((0.62 * s_, (k - 1.5) * 0.2, 0.38)), d, (0.5, 0.55, 0.6), 0.12, 0.5, 0.1, MI['crab'])
        # the claws: arm forward, a heavy hand
        tube(bm, [(0.42 * s_, -0.45, 0.42), (0.62 * s_, -0.85, 0.45), (0.45 * s_, -1.12, 0.42)], [0.08, 0.09, 0.07], 5, MI['crab'])
        ico(bm, (0.38 * s_, -1.25, 0.42), 0.2, 1, MI['crab'], (0.85, 1.4, 0.7))
        tube(bm, [(0.42 * s_, -1.42, 0.42), (0.36 * s_, -1.68, 0.4)], [0.07, 0.02], 4, MI['crab']); tube(bm, [(0.3 * s_, -1.42, 0.38), (0.27 * s_, -1.62, 0.36)], [0.05, 0.015], 4, MI['crab'])   # the pincers
        ico(bm, (0.12 * s_, -0.58, 0.58), 0.04, 1, MI['eye'])
prop('crab_giant', crab, smooth=40)

def lobster(bm):
    """Verne's lobsters "setting themselves up like halberdiers": the spiny lobster (reference/underwater/european_spiny_lobster_*).
    No big claws. A spiny cylindrical carapace, a segmented tail ending in a fan, five pairs of walking legs, and two very
    long, thick, spiny antennae raised forward like pikes; red-brown, paler bands and spots."""
    # carapace and tail, head toward -Y
    tube(bm, [(0, -0.55, 0.32), (0, -0.2, 0.36), (0, 0.15, 0.36)], [0.16, 0.2, 0.19], 8, MI['lobster'])
    r = random.Random(7)
    for k in range(18):                                                            # spines on the carapace
        a = r.uniform(0.2, 2.9); y = r.uniform(-0.5, 0.1)
        ico(bm, (math.cos(a) * 0.19, y, 0.36 + math.sin(a) * 0.17), 0.025, 0, MI['lobster_band'], (0.7, 0.7, 1.5))
    for k in range(6):                                                             # the tail segments, banded
        y = 0.18 + k * 0.11; rr = 0.17 - k * 0.018
        tube(bm, [(0, y, 0.34 - k * 0.02), (0, y + 0.1, 0.33 - k * 0.022)], [rr, rr * 0.95], 8, MI['lobster_band'] if k % 2 else MI['lobster'])
    for k, a in enumerate((-0.6, -0.2, 0.2, 0.6, 1.0)):                            # the tail fan
        tube(bm, [(0, 0.85, 0.22), (math.sin(a) * 0.14, 0.85 + math.cos(a) * 0.2, 0.2)], [0.03, 0.06], 4, MI['lobster'])
    for s_ in (-1, 1):
        for k in range(5):
            d = Vector((s_, (k - 2) * 0.25, 0)).normalized()
            leg(bm, Vector((0.12 * s_, -0.45 + k * 0.12, 0.25)), d, (0.2, 0.22, 0.3), 0.1, 0.3, 0.028, MI['lobster_band'], MI['lobster'])
        # the halberds: long thick spiny antennae, raised forward
        base = Vector((0.07 * s_, -0.6, 0.42))
        pts = [base + Vector((0.08 * s_ * t * 4, -1.2 * t, 0.55 * t - 0.25 * t * t)) for t in (0, 0.25, 0.5, 0.75, 1.0)]
        tube(bm, [tuple(p) for p in pts], [0.04, 0.035, 0.025, 0.015, 0.006], 5, MI['lobster'])
        for t in (0.1, 0.2, 0.3, 0.4, 0.55):
            p = base + Vector((0.08 * s_ * t * 4, -1.2 * t, 0.55 * t - 0.25 * t * t))
            ico(bm, p + Vector((0, 0, 0.03)), 0.016, 0, MI['lobster_band'], (0.6, 0.6, 1.6))
        tube(bm, [(0.03 * s_, -0.62, 0.38), (0.12 * s_, -0.9, 0.42), (0.2 * s_, -1.05, 0.38)], [0.01, 0.008, 0.004], 3, MI['lobster_band'])   # the small antennules
        ico(bm, (0.06 * s_, -0.6, 0.47), 0.03, 1, MI['eye'])
prop('lobster_giant', lobster, smooth=40)

for o in PROPS: world_uv(o, 1.0)
bpy.ops.object.select_all(action='DESELECT')
for o in PROPS: o.select_set(True)
bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, 'Creatures.fbx'), use_selection=True, apply_unit_scale=True,
                         apply_scale_options='FBX_SCALE_UNITS', axis_forward='-Z', axis_up='Y', bake_space_transform=True,
                         object_types={'MESH'}, mesh_smooth_type='FACE', add_leaf_bones=False, path_mode='STRIP')
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'creatures.blend'))
print('EXPORTED', [(o.name, sum(len(p.vertices) - 2 for p in o.data.polygons)) for o in PROPS])
