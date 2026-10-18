# The Nautilus, aft block (Part I, ch. XI "All by Electricity" and XV "A Walk on the Bottom of the Sea"):
# the central well with the iron ladder to the platform, the corridor, the cabin of Ned and Conseil
# ("six feet long"), the kitchen between the store-rooms with its electric furnaces and distilling
# apparatus, the bath-room "with hot and cold water taps", the crew's berth-room (door shut), the
# robing-room ("the arsenal and wardrobe ... A dozen diving apparatuses hung from the partition"),
# and the flooding cell with its water-tight door "furnished with stopper-plates".
# Blender axes as in nautilus_interior_fore.py: X toward the bow, Y to port, Z up; Unity (x, y, z) = (-Y, Z, X).
# The shells match the Unity greybox (SceneBuilders.Nautilus) exactly, so its boxes stay as invisible colliders.
# Objects named *__col get MeshColliders in Unity. Objects named kit_* are the player's own kit in the
# robing-room: Unity hides each one as it is put on (SuitStation).
import sys, os, math, random, json
sys.path.insert(0, os.path.dirname(__file__))
import bpy, bmesh
from mathutils import Vector, Matrix
from blib import *

OUT = sys.argv[-1] if len(sys.argv) > 1 and not sys.argv[-1].endswith('.py') else '/tmp/nautilus_aft'
os.makedirs(OUT, exist_ok=True)
random.seed(7)
reset()

M = {
    'ebony': mat('M_ebony', (0.06, 0.04, 0.035), rough=0.45),
    'oak': mat('M_oak', (0.35, 0.22, 0.12), rough=0.6),
    'carpet': mat('M_carpet', (0.32, 0.07, 0.06), rough=1.0),
    'leather': mat('M_leather', (0.28, 0.14, 0.07), rough=0.55),
    'brass': mat('M_brass', (0.75, 0.55, 0.25), metal=1.0, rough=0.35),
    'copper': mat('M_copper', (0.7, 0.38, 0.22), metal=1.0, rough=0.4),
    'iron': mat('M_iron', (0.22, 0.22, 0.22), metal=0.8, rough=0.6),
    'ironpaint': mat('M_ironpaint', (0.36, 0.37, 0.35), metal=0.2, rough=0.7),
    'grate': mat('M_grate', (0.15, 0.15, 0.15), metal=0.9, rough=0.55),
    'plaster': mat('M_plaster', (0.55, 0.52, 0.46), rough=0.9),
    'marble': mat('M_marble', (0.82, 0.8, 0.76), rough=0.4),
    'linen': mat('M_linen', (0.8, 0.78, 0.72), rough=0.95),
    'rubber': mat('M_rubber', (0.12, 0.1, 0.08), rough=0.7),
    'lead': mat('M_lead', (0.18, 0.18, 0.2), metal=0.6, rough=0.6),
    'glass': mat('M_glass', (0.8, 0.9, 0.9), rough=0.05),
    'bulb': mat('M_bulb', (1, 0.95, 0.85), emit=(1, 1, 1)),
    'coal': mat('M_coal', (0.9, 0.3, 0.05), emit=(1, 0.3, 0.05)),
    'sea': mat('M_seadoor', (0.05, 0.25, 0.28), emit=(0.05, 0.25, 0.28)),
    'pipe': mat('M_pipe', (0.7, 0.7, 0.68), metal=1.0, rough=0.3),
    'dial': mat('M_dial', (0.88, 0.85, 0.76), rough=0.6),
    'black': mat('M_black', (0.02, 0.02, 0.02), rough=0.6),
    'wool': mat('M_wool', (0.36, 0.33, 0.28), rough=1.0),
    'china': mat('M_china', (0.93, 0.91, 0.87), rough=0.2),
    'chinablue': mat('M_chinablue', (0.18, 0.28, 0.55), rough=0.2),
    'tilew': mat('M_tile_white', (0.86, 0.85, 0.8), rough=0.15),
    'tileb': mat('M_tile_black', (0.05, 0.05, 0.06), rough=0.15),
    'mahogany': mat('M_mahogany', (0.22, 0.07, 0.04), rough=0.35),
    'stoneware': mat('M_stoneware', (0.55, 0.45, 0.32), rough=0.6),
    'silver': mat('M_silver', (0.86, 0.86, 0.88), metal=1.0, rough=0.18),
    'enamelred': mat('M_enamel_red', (0.6, 0.05, 0.04), rough=0.15),
    'enamelblue': mat('M_enamel_blue', (0.05, 0.12, 0.5), rough=0.15),
}
MAT_LIST = list(M.values())
MI = {k: MAT_LIST.index(v) for k, v in M.items()}

def obj_from(name, build, props=None, smooth=None):
    bm = bmesh.new()
    build(bm)
    return new_obj(name, bm, MAT_LIST, 'INT', props, smooth)

def wall(bm, P0, du, dv, A, Z, openings, mi, step=0.6):
    As = sorted(set([0, A] + [o[0] for o in openings] + [o[1] for o in openings]))
    Zs = sorted(set([0, Z] + [o[2] for o in openings] + [o[3] for o in openings]))
    for i in range(len(As) - 1):
        for j in range(len(Zs) - 1):
            a0, a1, z0, z1 = As[i], As[i + 1], Zs[j], Zs[j + 1]
            if a1 - a0 < 1e-4 or z1 - z0 < 1e-4: continue
            cm, cz = (a0 + a1) / 2, (z0 + z1) / 2
            if any(o[0] < cm < o[1] and o[2] < cz < o[3] for o in openings): continue
            grid_quad(bm, P0 + du * a0 + dv * z0, du * (a1 - a0), dv * (z1 - z0), max(1, math.ceil((a1 - a0) / step)), max(1, math.ceil((z1 - z0) / step)), mi)

def room(name, x0, x1, y0, y1, h, ops=None, floor='iron', walls='ironpaint', ceil='plaster', wallmat=None):
    """Inward-facing shell. Wall codes: 'x0' (aft, along +Y from y0), 'x1' (fore, along -Y from y1),
    'y0' (starboard, along -X from x1), 'y1' (port, along +X from x0). wallmat overrides per wall."""
    ops = ops or {}; wallmat = wallmat or {}
    def b(bm):
        V = Vector
        grid_quad(bm, V((x0, y0, 0)), V((x1 - x0, 0, 0)), V((0, y1 - y0, 0)), math.ceil((x1 - x0) / 0.6), math.ceil((y1 - y0) / 0.6), MI[floor])
        grid_quad(bm, V((x0, y0, h)), V((0, y1 - y0, 0)), V((x1 - x0, 0, 0)), math.ceil((y1 - y0) / 0.6), math.ceil((x1 - x0) / 0.6), MI[ceil])
        wall(bm, V((x0, y0, 0)), V((0, 1, 0)), V((0, 0, 1)), y1 - y0, h, ops.get('x0', []), MI[wallmat.get('x0', walls)])
        wall(bm, V((x1, y1, 0)), V((0, -1, 0)), V((0, 0, 1)), y1 - y0, h, ops.get('x1', []), MI[wallmat.get('x1', walls)])
        wall(bm, V((x1, y0, 0)), V((-1, 0, 0)), V((0, 0, 1)), x1 - x0, h, ops.get('y0', []), MI[wallmat.get('y0', walls)])
        wall(bm, V((x0, y1, 0)), V((1, 0, 0)), V((0, 0, 1)), x1 - x0, h, ops.get('y1', []), MI[wallmat.get('y1', walls)])
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    return obj_from(name, b, props={'col': 1})

# ---- layout (Unity greybox -> Blender: X = z, Y = -x)
YC = 2.0             # corridor wall (Unity x = -2)
YS, YP = -3.2, 3.2   # starboard / port hull lining
H_AFT = 2.4
DOOR_W, DOOR_H = 0.85, 2.05
ROOMS = [  # name, x0, x1 (Blender X = Unity z), floor, walls, ceiling
    ('ned_conseil', -4.0, -2.0, 'oak', 'oak', 'plaster'),
    ('kitchen', -7.0, -4.0, 'iron', 'ironpaint', 'plaster'),
    ('bathroom', -8.5, -7.0, 'marble', 'marble', 'plaster'),
    ('crew', -12.5, -8.5, 'iron', 'ironpaint', 'plaster'),
    ('robing', -15.0, -12.5, 'iron', 'ironpaint', 'plaster'),
]
CELL = dict(x0=-17.5, x1=-15.0, y0=-1.2, y1=YC, h=2.3)
INNER_DOOR = (0.55, 1.45)     # Blender Y of the cell's inner door (Unity x -1.45 .. -0.55)
OUTER_DOOR = (-16.7, -15.8)   # Blender X of the outer door in the hull side (Unity z)
ENGINE_DOOR = (-3.05, -2.3)   # Blender Y of the passage to the engine-room, beside the cell (Unity x 2.3 .. 3.05)
ENG = dict(x0=-37.5, x1=-17.5, y0=YS, y1=YP, h=4.4)

def a_y1(xlo, xhi, x0): return (xlo - x0, xhi - x0)       # port wall measured along +X from x0
def a_x0(ylo, yhi, y0): return (ylo - y0, yhi - y0)       # aft wall measured along +Y from y0
def a_x1(ylo, yhi, y1): return (y1 - yhi, y1 - ylo)       # fore wall measured along -Y from y1

# ---------------------------------------------------------------- the central well and its iron ladder
room('hall_shell', -2.0, 0.0, YS, YP, 3.2, ops={
    'x1': [(*a_x1(-0.6, 0.6, YP), 0, 2.2)],
    'x0': [(*a_x0(2.1, 3.1, YS), 0, 2.1)],
}, floor='grate', walls='ironpaint', ceil='ironpaint')
LAD = (-1.6, -2.4)   # Unity (2.4, 0, -1.6)
def hall(bm):
    # ribs every half metre and riveted panels: the well reads as the inside of the hull
    for x in (-1.5, -0.5):
        for y in (YS + 0.04, YP - 0.04):
            box(bm, x - 0.05, x + 0.05, min(y, y + (0.06 if y < 0 else -0.06)), max(y, y + (0.06 if y < 0 else -0.06)), 0, 3.2, MI['iron'])
        box(bm, x - 0.05, x + 0.05, YS, YP, 3.1, 3.2, MI['iron'])
    # the iron ladder to the platform (rungs and rails; the Unity Ladder trigger climbs it)
    lx, ly = LAD
    for dy in (-0.22, 0.22):
        box(bm, lx - 0.02, lx + 0.02, ly + dy - 0.02, ly + dy + 0.02, 0, 3.2, MI['iron'])
    for k in range(1, 11):
        z = 0.3 * k
        cylinder(bm, (lx, ly - 0.22, z), 0.012, 0.44, 6, MI['iron'], axis='Y')
    # the hatch collar in the ceiling and its closed panel
    lathe(bm, [(0.4, 3.2), (0.4, 3.12), (0.33, 3.12), (0.33, 3.2)], 14, (lx, ly, 0), MI['iron'])
    # pressure piping along the ceiling to the aft
    for y in (2.4, 2.6):
        cylinder(bm, (-2.0, y, 2.95), 0.04, 2.0, 8, MI['pipe'], axis='X')
obj_from('hall', hall, props={'col': 1}, smooth=50)

# ---------------------------------------------------------------- the corridor (port side)
room('corridor_shell', -15.0, -2.0, YC, YP, H_AFT, ops={
    'x1': [(*a_x1(2.1, 3.1, YP), 0, 2.1)],
    'y0': [(*((-2.0) - (r[2] + r[1]) / 2 - DOOR_W / 2, (-2.0) - (r[2] + r[1]) / 2 + DOOR_W / 2), 0, DOOR_H) for r in ROOMS],
}, floor='grate', walls='ironpaint', ceil='ironpaint', wallmat={'y1': 'iron'})
LAMPS = []
def corridor(bm):
    for x in [-14.5 + i * 1.0 for i in range(13)]:
        # hull frames on the port side and across the ceiling
        box(bm, x - 0.04, x + 0.04, YP - 0.08, YP, 0, H_AFT, MI['iron'])
        box(bm, x - 0.04, x + 0.04, YC, YP, H_AFT - 0.08, H_AFT, MI['iron'])
    for y, r in ((3.0, 0.05), (2.85, 0.035), (2.72, 0.035)):
        cylinder(bm, (-15.0, y, 2.2), r, 13.0, 8, MI['pipe'] if r > 0.04 else MI['copper'], axis='X')
    # caged bulbs, "the electric light" everywhere
    for x in (-3.5, -7.5, -11.5, -14.3):
        lathe(bm, [(0.08, H_AFT), (0.09, H_AFT - 0.05), (0.07, H_AFT - 0.16), (0.0, H_AFT - 0.2)], 8, (x, 2.35, 0), MI['brass'])
        LAMPS.append([x, 2.35, H_AFT - 0.2])
obj_from('corridor', corridor, props={'col': 1}, smooth=40)
def corridor_bulbs(bm):
    for (x, y, z) in LAMPS:
        lathe(bm, [(0.0, z - 0.02), (0.06, z + 0.02), (0.06, z + 0.1)], 8, (x, y, 0), MI['bulb'])
obj_from('corridor_bulbs', corridor_bulbs)

# ---------------------------------------------------------------- the rooms to starboard
for (nm, x0, x1, fl, wl, cl) in ROOMS:
    mid = (x0 + x1) / 2
    ops = {'y1': [(*a_y1(mid - DOOR_W / 2, mid + DOOR_W / 2, x0), 0, DOOR_H)]}
    if nm == 'robing':
        ops['x0'] = [(*a_x0(*INNER_DOOR, YS), 0, 2.0), (*a_x0(*ENGINE_DOOR, YS), 0, 2.0)]
    room(nm + '_shell', x0, x1, YS, YC, H_AFT, ops=ops, floor=fl, walls=wl, ceil=cl, wallmat={'y0': 'iron' if nm != 'bathroom' else 'marble'})

def ceiling_lamp(bm, x, y, h=H_AFT):
    lathe(bm, [(0.16, h), (0.14, h - 0.04), (0.1, h - 0.1)], 10, (x, y, 0), MI['brass'])

# Ned and Conseil: "a cabin six feet long" with two berths, Ned's harpoon on its hooks
def ned(bm):
    for z in (0.35, 1.3):                                   # two berths, one above the other, to starboard
        box(bm, -3.95, -2.05, YS + 0.02, YS + 0.85, z, z + 0.12, MI['oak'])
        box(bm, -3.9, -2.1, YS + 0.05, YS + 0.8, z + 0.12, z + 0.22, MI['wool'])
        box(bm, -3.85, -3.55, YS + 0.1, YS + 0.7, z + 0.22, z + 0.3, MI['linen'])
    for x in (-3.95, -2.05):
        box(bm, x - 0.03, x + 0.03, YS + 0.8, YS + 0.86, 0, 1.75, MI['oak'])
    box(bm, -3.95, -2.05, YS + 0.82, YS + 0.86, 1.52, 1.6, MI['oak'])     # berth rail
    # Ned's harpoon on two hooks on the fore partition
    for y in (-0.4, 1.4):
        box(bm, -2.08, -2.02, y - 0.02, y + 0.02, 1.85, 1.92, MI['iron'])
    cylinder(bm, (-2.1, -0.9, 1.9), 0.018, 2.6, 6, MI['oak'], axis='Y')
    cylinder(bm, (-2.1, 1.7, 1.9), 0.025, 0.25, 6, MI['iron'], axis='Y', r2=0.0)
    # a folding table, a stool and a sea chest
    box(bm, -3.95, -3.4, -1.6, -0.7, 0.7, 0.74, MI['oak'])
    box(bm, -3.72, -3.62, -1.2, -1.1, 0, 0.7, MI['oak'])
    cylinder(bm, (-3.15, -1.15, 0), 0.18, 0.45, 8, MI['oak'])
    box(bm, -2.6, -2.1, -2.25, -1.6, 0, 0.45, MI['leather'])
    box(bm, -2.62, -2.08, -2.27, -1.58, 0.4, 0.47, MI['iron'])
    ceiling_lamp(bm, -3.0, -0.5)
obj_from('ned_conseil', ned, props={'col': 1}, smooth=40)

def checker(bm, x0, x1, y0, y1, z=0.002, n=0.3):
    """A black-and-white marble-tile floor laid over the iron deck."""
    i = 0
    xs = [x0 + k * n for k in range(int((x1 - x0) / n) + 1)] + [x1]
    ys = [y0 + k * n for k in range(int((y1 - y0) / n) + 1)] + [y1]
    for a in range(len(xs) - 1):
        for b in range(len(ys) - 1):
            if xs[a + 1] - xs[a] < 0.01 or ys[b + 1] - ys[b] < 0.01: continue
            grid_quad(bm, Vector((xs[a], ys[b], z)), Vector((xs[a + 1] - xs[a], 0, 0)), Vector((0, ys[b + 1] - ys[b], 0)), 1, 1, MI['tilew'] if (a + b) % 2 == 0 else MI['tileb'])
def jar(bm, x, y, z, h=0.22, r=0.08, mi=None):
    mi = MI['stoneware'] if mi is None else mi
    lathe(bm, [(0.0, 0), (r * 0.8, 0), (r, h * 0.2), (r, h * 0.75), (r * 0.7, h * 0.88), (r * 0.72, h), (0.0, h)], 12, (x, y, z), mi)

# The kitchen (I.XI): "There electricity, better than gas itself, did all the cooking. The streams under the
# furnaces gave out to the sponges of platina a heat which was regularly kept up and distributed. They also
# heated a distilling apparatus, which, by evaporation, furnished excellent drinkable water."
def kitchen(bm):
    checker(bm, -7.0, -4.0, YS, YC)
    # the electric range: a long cast-iron body with brass rails, oven doors with cast panels, three platina hobs
    box(bm, -6.95, -4.95, YS + 0.02, YS + 0.72, 0.06, 0.86, MI['iron'])
    box(bm, -6.97, -4.93, YS, YS + 0.74, 0.0, 0.06, MI['black'])
    box(bm, -6.97, -4.93, YS, YS + 0.76, 0.86, 0.92, MI['ironpaint'])
    cylinder(bm, (-6.97, YS + 0.84, 0.82), 0.016, 2.04, 8, MI['brass'], axis='X')           # towel rail along the front
    for x in (-6.5, -5.9, -5.3):
        box(bm, x - 0.25, x + 0.25, YS + 0.72, YS + 0.735, 0.2, 0.68, MI['black'])           # oven door
        box(bm, x - 0.2, x + 0.2, YS + 0.735, YS + 0.745, 0.26, 0.62, MI['iron'])           # cast panel
        lathe(bm, [(0.0, 0), (0.05, 0), (0.05, 0.004), (0.0, 0.004)], 12, (x, YS + 0.745, 0.44), MI['brass'], axis='Y')
        cylinder(bm, (x - 0.08, YS + 0.745, 0.6), 0.012, 0.16, 8, MI['brass'], axis='X')   # handle
    # the hood over it, copper, on brass brackets (the vapour is carried off along the hull)
    box(bm, -6.98, -4.92, YS, YS + 0.6, 1.75, 1.78, MI['copper'])
    for k in range(6):
        z = 1.78 + k * 0.08
        box(bm, -6.98 + k * 0.06, -4.92 - k * 0.06, YS, YS + 0.6 - k * 0.07, z, z + 0.08, MI['copper'])
    # pans on the hobs: a stock-pot and a sauté pan
    lathe(bm, [(0.0, 0.92), (0.16, 0.92), (0.17, 1.2), (0.18, 1.22), (0.0, 1.22)], 14, (-6.5, YS + 0.38, 0), MI['copper'])
    lathe(bm, [(0.0, 0.92), (0.14, 0.92), (0.15, 0.98), (0.0, 0.97)], 14, (-5.3, YS + 0.38, 0), MI['iron'])
    cylinder(bm, (-5.3, YS + 0.52, 0.96), 0.012, 0.3, 6, MI['iron'], axis='Y')
    # the distilling apparatus: copper boiler, dome, swan-neck, a glass condenser into a tank with a brass tap
    lathe(bm, [(0.0, 0.0), (0.3, 0.0), (0.32, 0.6), (0.3, 0.9), (0.18, 1.05), (0.06, 1.12), (0.0, 1.14)], 16, (-4.45, YS + 0.45, 0), MI['copper'], cap0=True)
    for zb in (0.15, 0.45, 0.75):
        lathe(bm, [(0.325, zb), (0.335, zb + 0.01), (0.325, zb + 0.03)], 16, (-4.45, YS + 0.45, 0), MI['brass'])
    cylinder(bm, (-4.45, YS + 0.45, 1.12), 0.035, 0.45, 8, MI['copper'])
    cylinder(bm, (-4.45, YS + 0.45, 1.55), 0.035, 0.9, 8, MI['copper'], axis='Y')
    cylinder(bm, (-4.45, YS + 1.35, 0.8), 0.13, 0.75, 14, MI['glass'])                   # condenser glass
    for k in range(7):
        lathe(bm, [(0.09, 1.5 - k * 0.1), (0.11, 1.48 - k * 0.1), (0.09, 1.46 - k * 0.1)], 10, (-4.45, YS + 1.35, 0), MI['copper'])
    cylinder(bm, (-4.45, YS + 1.35, 0), 0.24, 0.8, 14, MI['ironpaint'])                   # the tank of drinking water
    cylinder(bm, (-4.45, YS + 1.62, 0.25), 0.02, 0.08, 6, MI['brass'], axis='Y')
    lathe(bm, [(0.0, 0.8), (0.25, 0.8), (0.25, 0.82), (0.0, 0.82)], 14, (-4.45, YS + 1.35, 0), MI['brass'])
    # a dresser on the aft partition: plate rack with china, hooks with copper pans and ladles
    box(bm, -6.98, -6.6, -2.9, -0.4, 0.0, 0.85, MI['oak'])
    box(bm, -7.0, -6.55, -2.95, -0.35, 0.85, 0.9, MI['oak'])
    box(bm, -6.98, -6.95, -2.9, -0.4, 0.9, 2.0, MI['oak'])
    for z in (1.25, 1.62):
        box(bm, -6.95, -6.75, -2.9, -0.4, z, z + 0.025, MI['oak'])
        box(bm, -6.77, -6.75, -2.9, -0.4, z + 0.025, z + 0.06, MI['oak'])
        for q in range(9):
            yy = -2.75 + q * 0.27
            cylinder(bm, (-6.93, yy, z + 0.025 + 0.1), 0.095, 0.012, 14, MI['chinablue'] if q % 3 == 1 else MI['china'], axis='X')
    cylinder(bm, (-6.96, -2.9, 2.08), 0.012, 2.5, 6, MI['brass'], axis='Y')                # pan rail
    for q in range(6):
        yy = -2.75 + q * 0.42; r = 0.07 + 0.015 * q
        cylinder(bm, (-6.93, yy, 2.0), 0.006, 0.08, 4, MI['iron'])
        lathe(bm, [(0.0, 0), (r, 0.005), (r, 0.03 + 0.01 * q), (0.0, 0.02)], 12, (-6.9, yy, 1.98 - r * 2.2), MI['copper'], axis='X')
    for (x0, y0, z0) in [(-6.6, -2.6, 0.9), (-6.6, -2.2, 0.9), (-6.6, -1.8, 0.9)]:
        jar(bm, x0, y0, z0, 0.24, 0.08)                                                       # preserved sea-anemones, fucus sugar
    # the work table: marble top on oak, a board with a fish from the morning's net, bowls
    box(bm, -6.1, -4.9, -1.1, 0.1, 0.84, 0.9, MI['marble'])
    box(bm, -6.08, -4.92, -1.08, 0.08, 0.74, 0.84, MI['oak'])
    for (x, y) in [(-6.04, -1.04), (-4.96, -1.04), (-6.04, 0.04), (-4.96, 0.04)]:
        lathe(bm, [(0.04, 0), (0.03, 0.3), (0.04, 0.5), (0.03, 0.74)], 8, (x, y, 0), MI['oak'])
    box(bm, -5.8, -5.35, -0.7, -0.35, 0.9, 0.925, MI['oak'])
    lathe(bm, [(0.0, 0), (0.02, 0.03), (0.05, 0.12), (0.045, 0.22), (0.02, 0.3), (0.0, 0.32)], 8, (-5.58, -0.52, 0.925), MI['pipe'], axis='Y')  # a silver fish
    for (x, y) in ((-5.2, -0.2), (-5.05, -0.85)):
        lathe(bm, [(0.0, 0.9), (0.06, 0.9), (0.12, 0.98), (0.125, 1.0)], 12, (x, y, 0), MI['china'])
    ceiling_lamp(bm, -5.5, -0.5)
obj_from('kitchen', kitchen, props={'col': 1}, smooth=40)
def kitchen_glow(bm):
    for x in (-5.9,):
        box(bm, x - 0.18, x + 0.18, YS + 0.2, YS + 0.58, 0.921, 0.925, MI['coal'])    # a free hob: the platina sponge glows
obj_from('kitchen_glow', kitchen_glow)

# The bath-room (I.XI): "comfortably furnished, with hot and cold water taps"
def bathroom(bm):
    checker(bm, -8.5, -7.0, YS, YC, n=0.25)
    # white tiles to dado height, a black border, painted above
    for (x0, x1, y0, y1) in [(-8.5, -8.49, YS, YC), (-7.01, -7.0, YS, YC - 0.0)]:
        box(bm, x0, x1, y0, y1, 0.0, 1.2, MI['tilew'])
        box(bm, x0 - 0.002, x1 + 0.002, y0, y1, 1.2, 1.25, MI['tileb'])
    box(bm, -8.5, -7.0, YS, YS + 0.01, 0.0, 1.2, MI['tilew'])
    box(bm, -8.5, -7.0, YS, YS + 0.012, 1.2, 1.25, MI['tileb'])
    # the bath: an enamelled roll-top on four lion's-paw feet, across the hull end
    bx0, bx1, by0, by1 = -8.42, -7.08, YS + 0.08, YS + 0.78
    yc = (by0 + by1) / 2; xc = (bx0 + bx1) / 2
    lathe(bm, [(0.0, 0.18), (0.25, 0.18), (0.31, 0.3), (0.33, 0.55), (0.35, 0.62), (0.33, 0.64), (0.28, 0.6), (0.0, 0.3)], 24, (0, 0, 0), MI['china'])
    o_bath = None
    # (the lathe made a round tub at the origin; stretch it into an oval and move it into place)
    vs = [v for v in bm.verts if abs(v.co.x) < 0.4 and abs(v.co.y) < 0.4 and 0.17 < v.co.z < 0.66 and v.index >= 0]
    for v in bm.verts[-len(vs):] if False else []: pass
    bm.verts.ensure_lookup_table()
    n_new = 24 * 8
    for v in bm.verts[len(bm.verts) - n_new:]:
        v.co.x = xc + v.co.x * 1.95; v.co.y = yc + v.co.y * 1.05
    for (fx, fy) in [(bx0 + 0.15, by0 + 0.12), (bx1 - 0.15, by0 + 0.12), (bx0 + 0.15, by1 - 0.12), (bx1 - 0.15, by1 - 0.12)]:
        lathe(bm, [(0.0, 0.0), (0.05, 0.0), (0.04, 0.06), (0.03, 0.12), (0.045, 0.2), (0.0, 0.2)], 8, (fx, fy, 0), MI['brass'])
    # the hot and cold taps (red and blue enamel discs), a brass spout, pipes up the hull
    for (y, disc) in ((yc - 0.12, 'enamelred'), (yc + 0.12, 'enamelblue')):
        cylinder(bm, (-8.49, y, 0.75), 0.018, 1.6, 8, MI['copper'])
        cylinder(bm, (-8.49, y, 0.75), 0.02, 0.1, 8, MI['brass'], axis='X')
        lathe(bm, [(0.0, 0), (0.035, 0), (0.035, 0.012), (0.0, 0.012)], 12, (-8.39, y, 0.75), MI[disc], axis='X')
    cylinder(bm, (-8.49, yc, 0.68), 0.02, 0.22, 8, MI['brass'], axis='X')
    cylinder(bm, (-8.28, yc, 0.6), 0.02, 0.08, 8, MI['brass'])
    # a duckboard mat before it
    for k in range(6):
        box(bm, -8.2 + k * 0.17, -8.08 + k * 0.17, YS + 0.85, YS + 1.45, 0.0, 0.03, MI['oak'])
    # the wash-stand: mahogany with a marble top, a porcelain basin and ewer, a gilt-framed glass above
    box(bm, -8.48, -7.95, -1.6, -0.55, 0.0, 0.78, MI['mahogany'])
    box(bm, -8.5, -7.92, -1.63, -0.52, 0.78, 0.81, MI['marble'])
    lathe(bm, [(0.0, 0.81), (0.06, 0.81), (0.17, 0.88), (0.19, 0.92), (0.0, 0.86)], 16, (-8.2, -1.08, 0), MI['china'])
    lathe(bm, [(0.0, 0.81), (0.06, 0.81), (0.08, 0.9), (0.05, 1.02), (0.06, 1.1), (0.0, 1.1)], 12, (-8.35, -0.72, 0), MI['china'])
    for (y, disc) in ((-1.2, 'enamelred'), (-0.96, 'enamelblue')):
        cylinder(bm, (-8.49, y, 0.95), 0.016, 0.12, 8, MI['brass'], axis='X')
        lathe(bm, [(0.0, 0), (0.025, 0), (0.025, 0.01), (0.0, 0.01)], 10, (-8.37, y, 0.95), MI[disc], axis='X')
    box(bm, -8.49, -8.47, -1.5, -0.65, 1.25, 1.95, MI['glass'])                               # the looking-glass
    for (y0, y1, z0, z1) in [(-1.54, -0.61, 1.95, 1.99), (-1.54, -0.61, 1.21, 1.25), (-1.54, -1.5, 1.21, 1.99), (-0.65, -0.61, 1.21, 1.99)]:
        box(bm, -8.49, -8.45, y0, y1, z0, z1, MI['brass'])
    # towel rail with linen, soap dish, a shelf of bottles
    for z in (0.9, 1.15):
        cylinder(bm, (-8.45, 0.0, z), 0.012, 0.9, 8, MI['brass'], axis='Y')
    box(bm, -8.46, -8.38, 0.08, 0.8, 0.55, 1.16, MI['linen'])
    box(bm, -8.48, -8.3, -0.3, -0.1, 1.35, 1.37, MI['marble'])
    for k in range(4):
        lathe(bm, [(0.0, 1.37), (0.025, 1.37), (0.025, 1.47), (0.01, 1.5), (0.0, 1.5)], 8, (-8.39, -0.27 + k * 0.05, 0), MI['glass'])
    ceiling_lamp(bm, -7.75, -0.5)
obj_from('bathroom', bathroom, props={'col': 1}, smooth=40)

# The crew's berth-room: the door stays shut (I.XI); behind it only hammocks hooked under the frames
def crew(bm):
    for k in range(4):
        x = -12.0 + k * 0.95
        box(bm, x - 0.02, x + 0.02, YS, YC, 2.1, 2.14, MI['iron'])
        box(bm, x - 0.35, x + 0.35, -2.6, 1.2, 1.0, 1.08, MI['wool'])
    ceiling_lamp(bm, -10.5, -0.5)
obj_from('crew', crew, props={'col': 1})

# ---------------------------------------------------------------- the robing-room: arsenal and wardrobe
R = dict(x0=-15.0, x1=-12.5, y0=YS, y1=YC)

def hanging_dress(bm, x, y, face, mi_suit='rubber', with_reservoir=False, with_helmet=False, stand=False):
    """One diving apparatus hanging from its hook (or on its stand). face = unit vector (x, y) the front looks along.
    About 1.55 m from boot to collar: india-rubber without seam, copper bands crossing the chest, leaden soles."""
    fx, fy = face
    sx, sy = -fy, fx            # the dress's right-to-left axis
    V = Vector
    def P(u, v, z):              # u along the shoulders, v along the face
        return (x + sx * u + fx * v, y + sy * u + fy * v, z)
    zb = 0.05 if stand else 0.2
    # legs: tapered, slightly apart; leaden boots
    for u in (-0.1, 0.1):
        c = P(u, 0, zb)
        cylinder(bm, (c[0], c[1], zb + 0.14), 0.085, 0.72, 8, MI[mi_suit], r2=0.1)
        box(bm, c[0] - 0.07 + fx * 0.04, c[0] + 0.07 + fx * 0.04, c[1] - 0.07 + fy * 0.04, c[1] + 0.07 + fy * 0.04, zb, zb + 0.14, MI['lead']) if abs(fx) > 0.5 else \
            box(bm, c[0] - 0.07, c[0] + 0.07, c[1] - 0.07 + fy * 0.04, c[1] + 0.07 + fy * 0.04, zb, zb + 0.14, MI['lead'])
    # body: a barrel of india-rubber
    c = P(0, 0, 0)
    lathe(bm, [(0.17, zb + 0.84), (0.2, zb + 1.0), (0.21, zb + 1.2), (0.19, zb + 1.38), (0.12, zb + 1.46)], 10, (c[0], c[1], 0), MI[mi_suit])
    # copper bands across the chest, the collar
    lathe(bm, [(0.215, zb + 1.18), (0.215, zb + 1.22)], 10, (c[0], c[1], 0), MI['copper'])
    lathe(bm, [(0.205, zb + 1.04), (0.205, zb + 1.08)], 10, (c[0], c[1], 0), MI['copper'])
    lathe(bm, [(0.16, zb + 1.44), (0.17, zb + 1.5), (0.13, zb + 1.53)], 10, (c[0], c[1], 0), MI['copper'])
    # arms hanging, gloves
    for u in (-0.25, 0.25):
        a = P(u, 0, 0)
        cylinder(bm, (a[0], a[1], zb + 0.72), 0.06, 0.66, 6, MI[mi_suit], r2=0.075)
        lathe(bm, [(0.0, zb + 0.6), (0.06, zb + 0.64), (0.06, zb + 0.72)], 6, (a[0], a[1], 0), MI[mi_suit])
    if with_reservoir:
        b = P(0, -0.27, 0)
        box(bm, b[0] - 0.13, b[0] + 0.13, b[1] - 0.13, b[1] + 0.13, zb + 0.95, zb + 1.45, MI['iron']) if abs(fx) < 0.5 else \
            box(bm, b[0] - 0.08, b[0] + 0.08, b[1] - 0.15, b[1] + 0.15, zb + 0.95, zb + 1.45, MI['iron'])
    if with_helmet:
        helmet(bm, c[0], c[1], zb + 1.53, face)
    return zb + 1.55

def helmet(bm, x, y, z, face, mi='copper'):
    """The copper ball: three thick glass ports (front and both sides), brass rims, the breast plate."""
    lathe(bm, [(0.0, 0.0), (0.12, 0.01), (0.17, 0.09), (0.18, 0.18), (0.15, 0.3), (0.08, 0.36), (0.0, 0.37)], 10, (x, y, z), MI[mi])
    fx, fy = face
    for (dx, dy) in ((fx, fy), (-fy, fx), (fy, -fx)):
        cx_, cy_ = x + dx * 0.17, y + dy * 0.17
        ax = 'X' if abs(dx) > 0.5 else 'Y'
        cylinder(bm, (cx_ - (0.02 if ax == 'X' and dx < 0 else 0), cy_ - (0.02 if ax == 'Y' and dy < 0 else 0), z + 0.19), 0.06, 0.02, 10, MI['brass'], axis=ax)
        cylinder(bm, (cx_ + dx * 0.012, cy_ + dy * 0.012, z + 0.19), 0.045, 0.005, 10, MI['glass'], axis=ax)

def reservoir(bm, x, y, z, along='Y'):
    """The Rouquayrol reservoir: a box of thick iron plates, the bellows box on top, two india-rubber pipes."""
    box(bm, x - 0.09, x + 0.09, y - 0.15, y + 0.15, z, z + 0.48, MI['iron'])
    box(bm, x - 0.095, x + 0.095, y - 0.155, y + 0.155, z + 0.48, z + 0.58, MI['brass'])
    for dy in (-0.07, 0.07):
        cylinder(bm, (x, y + dy, z + 0.58), 0.018, 0.2, 6, MI['rubber'])
    for zz in (z + 0.12, z + 0.36):
        box(bm, x - 0.1, x + 0.1, y - 0.16, y + 0.16, zz, zz + 0.025, MI['ironpaint'])

def lamp(bm, x, y, z):
    """The Ruhmkorff lamp: the Bunsen pile in a box, the lantern with its spiral glass on top, a belt hook."""
    box(bm, x - 0.07, x + 0.07, y - 0.05, y + 0.05, z, z + 0.16, MI['iron'])
    lathe(bm, [(0.0, z + 0.16), (0.05, z + 0.16), (0.055, z + 0.2), (0.05, z + 0.32), (0.035, z + 0.36), (0.0, z + 0.37)], 10, (x, y, 0), MI['brass'])
    cylinder(bm, (x, y, z + 0.2), 0.04, 0.11, 8, MI['glass'])
    cylinder(bm, (x, y + 0.05, z + 0.08), 0.03, 0.02, 6, MI['brass'], axis='Y')     # "by turning a screw"

def air_gun(bm, x, y, z):
    """The air-gun: steel butt hollowed for the compressed air, a long barrel, standing upright in the rack."""
    box(bm, x - 0.03, x + 0.03, y - 0.05, y + 0.05, z, z + 0.32, MI['pipe'])
    cylinder(bm, (x, y, z + 0.32), 0.016, 0.85, 6, MI['iron'])
    box(bm, x - 0.025, x + 0.025, y - 0.03, y + 0.03, z + 0.3, z + 0.42, MI['oak'])

def stick(bm, x, y, z, lean=0.0):
    cylinder(bm, (x, y, z), 0.016, 1.45, 6, MI['oak'])
    cylinder(bm, (x, y, z - 0.08), 0.02, 0.08, 6, MI['iron'], r2=0.003)

def robing(bm):
    # the dresses hang along their rails like coats, shoulders square to the partition:
    # three on the starboard partition (helmets on the shelf above), eight on the fore partition
    box(bm, -14.15, -12.8, YS + 0.27, YS + 0.31, 1.92, 1.96, MI['brass'])
    for k in range(3):
        x = -13.9 + k * 0.44
        box(bm, x - 0.01, x + 0.01, YS + 0.02, YS + 0.3, 1.9, 1.94, MI['brass'])
        hanging_dress(bm, x, YS + 0.3, (1, 0))
    box(bm, -12.89, -12.85, -2.7, 0.8, 1.92, 1.96, MI['brass'])
    for k in range(8):
        y = -2.4 + k * 0.43
        hanging_dress(bm, -12.87, y, (0, 1))
    box(bm, -14.15, -12.8, YS + 0.02, YS + 0.36, 1.97, 2.0, MI['oak'])
    for k in range(3):
        helmet(bm, -13.9 + k * 0.44, YS + 0.2, 2.0, (0, 1))
    # the rack of reservoirs, lamps and air-guns on the fore partition, by the corridor door
    for z in (0.0, 0.9, 1.4):
        box(bm, -12.95, -12.52, 0.85, 1.95, z, z + (0.05 if z == 0 else 0.03), MI['oak'])
    for k in range(3):
        reservoir(bm, -12.7, 1.0 + k * 0.36, 0.05)
    for k in range(5):
        lamp(bm, -12.7, 0.98 + k * 0.22, 0.93)
    for k in range(4):
        air_gun(bm, -12.62, 1.0 + k * 0.28, 1.43)
    # bench along the aft partition where the visitors are dressed
    box(bm, -14.98, -14.6, -1.5, -0.2, 0.42, 0.47, MI['oak'])
    for y in (-1.4, -0.85, -0.3):
        box(bm, -14.95, -14.63, y - 0.03, y + 0.03, 0, 0.42, MI['oak'])
    # stopper-plate frame round the cell's inner door: heavy iron jambs and the dogs
    y0, y1 = INNER_DOOR
    box(bm, -14.98, -14.88, y0 - 0.14, y0, 0, 2.12, MI['iron'])
    box(bm, -14.98, -14.88, y1, y1 + 0.14, 0, 2.12, MI['iron'])
    box(bm, -14.98, -14.88, y0 - 0.14, y1 + 0.14, 2.0, 2.14, MI['iron'])
    for z in (0.3, 1.0, 1.7):
        box(bm, -14.88, -14.84, y1 + 0.03, y1 + 0.11, z - 0.05, z + 0.05, MI['brass'])
    ceiling_lamp(bm, -13.75, -0.6)
obj_from('robing_room', robing, props={'col': 1}, smooth=40)

# the player's own kit, laid ready on the bench and its stand: hidden in Unity as each piece is put on
KIT = {}
def kit(name, fn):
    o = obj_from('kit_' + name, fn, smooth=40)
    KIT[name] = o
kit('dress', lambda bm: hanging_dress(bm, -14.7, -1.9, (1, 0), stand=True))
kit('reservoir', lambda bm: reservoir(bm, -14.8, -1.3, 0.47))
kit('lamp', lambda bm: lamp(bm, -14.8, -0.98, 0.47))
kit('gun', lambda bm: air_gun(bm, -14.92, -0.8, 0.47))
kit('stick', lambda bm: stick(bm, -14.93, 0.1, 0.08))
kit('helmet', lambda bm: helmet(bm, -14.78, -0.45, 0.47, (1, 0)))
def dress_stand(bm):
    box(bm, -14.95, -14.45, -2.15, -1.65, 0, 0.05, MI['oak'])
obj_from('robing_stand', dress_stand)

# ---------------------------------------------------------------- the flooding cell
C = CELL
room('cell_shell', C['x0'], C['x1'], C['y0'], C['y1'], C['h'], ops={
    'x1': [(*a_x1(*INNER_DOOR, C['y1']), 0, 2.0)],
    'y1': [(*a_y1(*OUTER_DOOR, C['x0']), 0, 2.0)],
}, floor='grate', walls='iron', ceil='iron')
def cell(bm):
    # riveted ribs; the sea comes in through a grating in the floor
    for x in (-17.0, -15.6):
        box(bm, x - 0.04, x + 0.04, C['y0'], C['y0'] + 0.08, 0, C['h'], MI['iron'])
        box(bm, x - 0.04, x + 0.04, C['y0'], C['y1'], C['h'] - 0.08, C['h'], MI['iron'])
    box(bm, -16.9, -16.3, -0.6, 0.6, 0.0, 0.01, MI['black'])                  # the flooding grate
    # the sea tap's housing and its pipe down to the grate (the wheel itself is the Unity Valve)
    box(bm, -16.4, -16.1, -1.15, -0.95, 1.05, 1.35, MI['brass'])
    cylinder(bm, (-16.25, C['y0'] + 0.12, 0.0), 0.05, 1.05, 8, MI['copper'])
    # the gauge's brass case behind the Unity needle
    lathe(bm, [(0.0, 0.0), (0.17, 0.0), (0.17, 0.05), (0.0, 0.05)], 14, (-16.25, C['y0'] + 0.01, 1.75), MI['brass'], axis='Y')
    lathe(bm, [(0.0, 0.051), (0.15, 0.051)], 14, (-16.25, C['y0'] + 0.01, 1.75), MI['dial'], axis='Y')
    # the pump knob's plate
    box(bm, -15.47, -15.23, C['y0'] + 0.02, C['y0'] + 0.04, 1.08, 1.32, MI['brass'])
    # the outer door's heavy frame in the hull side
    x0, x1 = OUTER_DOOR
    box(bm, x0 - 0.14, x0, C['y1'] - 0.1, C['y1'], 0, 2.12, MI['iron'])
    box(bm, x1, x1 + 0.14, C['y1'] - 0.1, C['y1'], 0, 2.12, MI['iron'])
    box(bm, x0 - 0.14, x1 + 0.14, C['y1'] - 0.1, C['y1'], 2.0, 2.14, MI['iron'])
    # the inner door's frame and stopper-plates on the cell side
    y0, y1 = INNER_DOOR
    box(bm, -15.12, -15.02, y0 - 0.14, y0, 0, 2.12, MI['iron'])
    box(bm, -15.12, -15.02, y1, y1 + 0.14, 0, 2.12, MI['iron'])
    box(bm, -15.12, -15.02, y0 - 0.14, y1 + 0.14, 2.0, 2.14, MI['iron'])
    lathe(bm, [(0.12, C['h']), (0.1, C['h'] - 0.08), (0.0, C['h'] - 0.12)], 8, (-16.25, 0.4, 0), MI['iron'])
obj_from('flooding_cell', cell, props={'col': 1}, smooth=40)

# the hull-side lobby beyond the outer door: the sea door stands open on "a faint light"
room('sea_lobby_shell', C['x0'], C['x1'], C['y1'], YP, C['h'], ops={
    'y0': [(*((C['x1']) - OUTER_DOOR[1], (C['x1']) - OUTER_DOOR[0]), 0, 2.0)],
}, floor='iron', walls='iron', ceil='iron', wallmat={'y1': 'sea'})

# ---------------------------------------------------------------- the engine-room (I.XI, plate im024)
# "This engine-room, clearly lighted, did not measure less than sixty-five feet in length. It was divided
#  into two parts; the first contained the materials for producing electricity, and the second the
#  machinery that connected it with the screw." Bunsen's piles: "fewer in number, but strong and large";
# "electro-magnets of great size, on a system of levers and cog-wheels that transmit the movement to the
#  axle of the screw." A passage beside the flooding cell leads aft from the robing-room.
E = ENG
room('engine_passage_shell', -17.5, -15.0, YS, -1.2, 2.3, ops={
    'x1': [(*a_x1(*ENGINE_DOOR, -1.2), 0, 2.0)],
    'x0': [(*a_x0(*ENGINE_DOOR, YS), 0, 2.0)],
}, floor='grate', walls='iron', ceil='iron')
room('engine_room_shell', E['x0'], E['x1'], E['y0'], E['y1'], E['h'], ops={
    'x1': [(*a_x1(*ENGINE_DOOR, E['y1']), 0, 2.0)],
}, floor='grate', walls='iron', ceil='ironpaint')
PILE_X = [-19.6, -21.1, -22.6, -24.1, -25.6, -27.1]
ENG_LAMPS = []
def engine(bm):
    h = E['h']
    # hull frames and ceiling girders, riveted plates (the engraving's ribbed vault)
    for x in [E['x0'] + 0.5 + i * 1.5 for i in range(14)]:
        for y in (YS, YP - 0.1):
            box(bm, x - 0.06, x + 0.06, y, y + 0.1, 0, h, MI['iron'])
        box(bm, x - 0.06, x + 0.06, YS, YP, h - 0.22, h, MI['iron'])
    for y in (-1.6, 0.0, 1.6):
        box(bm, E['x0'], E['x1'], y - 0.05, y + 0.05, h - 0.3, h - 0.22, MI['iron'])
    # ---- first part: Bunsen's piles, strong and large, two rows with a gangway between
    for side in (-1, 1):
        yc = side * 2.45
        for x in PILE_X:
            lathe(bm, [(0.52, 0.0), (0.52, 0.12), (0.46, 0.14), (0.46, 3.3), (0.5, 3.32), (0.5, 3.42), (0.3, 3.5), (0.0, 3.52)], 12, (x, yc, 0), MI['ironpaint'])
            for z in (0.6, 1.5, 2.4):    # riveted bands
                lathe(bm, [(0.485, z), (0.485, z + 0.1)], 12, (x, yc, 0), MI['iron'])
            # the lion-headed taps and brass cocks of the engraving
            fx = x; fy = yc - side * 0.5
            box(bm, fx - 0.09, fx + 0.09, min(fy, fy - side * 0.12), max(fy, fy - side * 0.12), 1.2, 1.38, MI['bronze'] if 'bronze' in MI else MI['brass'])
            cylinder(bm, (fx, fy - side * 0.12, 1.26), 0.025, 0.18, 6, MI['brass'], axis='Y' if side < 0 else 'Y')
            # elbow pipe from the cap into the header
            cylinder(bm, (x, yc, 3.5), 0.12, 0.5, 8, MI['iron'])
        cylinder(bm, (PILE_X[-1] - 0.3, yc, 4.0), 0.16, PILE_X[0] - PILE_X[-1] + 0.8, 10, MI['iron'], axis='X')
    # ---- second part: electro-magnets, levers and cog-wheels on the axle of the screw
    for side in (-1, 1):
        for x in (-29.2, -31.0):
            yc = side * 2.3
            cylinder(bm, (x - 0.75, yc, 1.1), 0.62, 1.5, 14, MI['copper'], axis='X')        # the coil
            for xx in (x - 0.8, x + 0.8):
                cylinder(bm, (xx - 0.04, yc, 1.1), 0.7, 0.08, 14, MI['iron'], axis='X')     # cheeks
            box(bm, x - 0.85, x + 0.85, yc - 0.55, yc + 0.55, 0.0, 0.42, MI['ironpaint'])   # bed
            # the lever from the armature toward the shaft
            box(bm, x - 0.05, x + 0.05, min(yc, side * 0.5), max(yc, side * 0.5), 1.95, 2.05, MI['pipe'])
    # shaft bearings (the axle itself turns in Unity)
    for x in (-28.0, -31.9, -35.2, -37.3):
        box(bm, x - 0.2, x + 0.2, -0.45, 0.45, 0.0, 0.85, MI['ironpaint'])
        lathe(bm, [(0.32, 0.0), (0.32, 0.4)], 12, (x - 0.2, 0, 1.0), MI['brass'], axis='X')
    # the pit under the great wheel
    box(bm, -33.8, -33.2, -1.7, 1.7, -0.75, 0.0, MI['black'], inside=True, skip=('z1',))
    # lights along the vault ("clearly lighted")
    for x in (-19.5, -23.0, -26.5, -30.0, -33.5, -36.5):
        lathe(bm, [(0.14, h - 0.3), (0.14, h - 0.36), (0.1, h - 0.45)], 10, (x, 0.0, 0), MI['brass'])
        ENG_LAMPS.append([x, 0.0, h - 0.47])
obj_from('engine_room', engine, props={'col': 1}, smooth=40)
def engine_bulbs(bm):
    for (x, y, z) in ENG_LAMPS:
        lathe(bm, [(0.0, z - 0.04), (0.09, z), (0.09, z + 0.05)], 10, (x, y, 0), MI['bulb'])
o = obj_from('engine_bulbs', engine_bulbs)
o['lights'] = json.dumps(ENG_LAMPS)

def rotating(name, center, build):
    """A part that turns about the screw's axis (Blender X): built around its own origin so Unity can spin it."""
    bm = bmesh.new()
    build(bm)
    ob = new_obj(name, bm, MAT_LIST, 'INT', None, 40)
    ob.location = center
    return ob
def shaft(bm):
    cylinder(bm, (-9.7, 0, 0), 0.22, 9.9, 12, MI['pipe'], axis='X')
    for x in (-6.0, -2.5, 0.0):
        cylinder(bm, (x - 0.05, 0, 0), 0.3, 0.1, 12, MI['iron'], axis='X')   # couplings
def great_wheel(bm):
    # the toothed wheel of plate im024: rim, spokes, hub, teeth
    n = 40; r0, r1 = 1.45, 1.62
    lathe(bm, [(1.32, -0.12), (1.45, -0.12), (1.45, 0.12), (1.32, 0.12), (1.32, -0.12)], n, (0, 0, 0), MI['iron'], axis='X')
    for k in range(n):
        a = 2 * math.pi * k / n
        c, s_ = math.cos(a), math.sin(a)
        p0 = Vector((0, c * r0, s_ * r0)); w = Vector((0, -s_, c)) * 0.06
        q = [p0 - w, p0 + w, Vector((0, c * r1, s_ * r1)) + w * 0.6, Vector((0, c * r1, s_ * r1)) - w * 0.6]
        for dx in (-0.1, 0.1):
            vs = [bm.verts.new(v + Vector((dx, 0, 0))) for v in q]
            f = bm.faces.new(vs if dx > 0 else vs[::-1]); f.material_index = MI['iron']
    for k in range(6):
        a = 2 * math.pi * k / 6
        d = Vector((0, math.cos(a), math.sin(a)))
        for t in range(1):
            p = d * 0.7
            M_ = Matrix.Rotation(a, 4, 'X')
            sub = bmesh.new()
            box(sub, -0.06, 0.06, 0.25, 1.35, -0.06, 0.06, 0)
            bmesh.ops.transform(sub, matrix=M_, verts=sub.verts)
            for f in sub.faces: f.material_index = MI['iron']
            tmp = bpy.data.meshes.new('tmp'); sub.to_mesh(tmp); sub.free(); bm.from_mesh(tmp); bpy.data.meshes.remove(tmp)
    cylinder(bm, (-0.2, 0, 0), 0.35, 0.4, 12, MI['iron'], axis='X')
def cog(bm):
    n = 16; r0, r1 = 0.55, 0.66
    cylinder(bm, (-0.08, 0, 0), r0, 0.16, n, MI['brass'], axis='X')
    for k in range(n):
        a = 2 * math.pi * (k + 0.5) / n
        c, s_ = math.cos(a), math.sin(a)
        sub = bmesh.new()
        box(sub, -0.08, 0.08, r0 - 0.02, r1, -0.05, 0.05, 0)
        bmesh.ops.transform(sub, matrix=Matrix.Rotation(a - math.pi / 2, 4, 'X'), verts=sub.verts)
        for f in sub.faces: f.material_index = MI['brass']
        tmp = bpy.data.meshes.new('tmp'); sub.to_mesh(tmp); sub.free(); bm.from_mesh(tmp); bpy.data.meshes.remove(tmp)
rotating('rot_shaft', (-27.6, 0, 1.0), shaft)
rotating('rot_great_wheel', (-33.5, 0, 1.0), great_wheel)
rotating('rot_cog', (-33.5, 0.9, 3.03), cog)

# ---------------------------------------------------------------- markers, UVs, export
for name, loc in (('BOW_TIP', (40.0, 0, 2.0)), ('STERN', (-40.0, 0, 2.0)), ('LANTERN', (0.0, 0, 9.0)), ('PORT_DOOR', (0.0, 3.9, 1.0))):
    e = bpy.data.objects.new(name, None); e.location = loc; coll('INT').objects.link(e)
for o in list(coll('INT').objects):
    if o.type == 'MESH' and len(o.data.polygons):
        world_uv(o, 1.0)
        if o.get('col'): o.name = o.name + '__col'
bpy.ops.object.select_all(action='DESELECT')
for o in coll('INT').objects: o.select_set(True)
bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, 'Nautilus_Interior_Aft.fbx'), use_selection=True, apply_unit_scale=True,
                         apply_scale_options='FBX_SCALE_UNITS', axis_forward='-Z', axis_up='Y', bake_space_transform=True,
                         object_types={'MESH', 'EMPTY'}, mesh_smooth_type='FACE', add_leaf_bones=False, path_mode='STRIP')
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'nautilus_interior_aft.blend'))
tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in coll('INT').objects if o.type == 'MESH')
print('EXPORTED', OUT, 'triangles', tris)
