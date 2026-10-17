# The Nautilus, built from the book's own figures (Part I, ch. X-XI, XV and XII):
# saloon 30 ft x 18 ft x 15 ft with a luminous ceiling, organ, tridacna fountain, thirty pictures,
# glass cases fixed with copper rivets and two crystal windows behind sliding iron panels;
# library of ebony inlaid with brass ending in leather divans, four globes in the ceiling;
# the captain's monkish room with its instruments; the waist; the wardrobe with a dozen diving
# apparatuses; and the little flooding cell with a second door cut in the side of the hull.
# Blender axes: X toward the bow, Y to port, Z up. Interior deck Z = 0, hull axis Z = 1.6, radius 4.
import sys, os, math, random
sys.path.insert(0, os.path.dirname(__file__))
import bpy, bmesh
from mathutils import Vector, Matrix, Euler
from blib import *

OUT = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else '/tmp/nautilus.glb'
random.seed(4)
reset()

M = {
    'ebony': mat('M_ebony', (0.06, 0.04, 0.035), rough=0.45),
    'oak': mat('M_oak', (0.35, 0.22, 0.12), rough=0.6),
    'tapestry': mat('M_tapestry', (0.18, 0.22, 0.2), rough=0.9),
    'carpet': mat('M_carpet', (0.32, 0.07, 0.06), rough=1.0),
    'velvet': mat('M_velvet', (0.3, 0.05, 0.05), rough=0.9),
    'leather': mat('M_leather', (0.28, 0.14, 0.07), rough=0.55),
    'brass': mat('M_brass', (0.75, 0.55, 0.25), metal=1.0, rough=0.35),
    'copper': mat('M_copper', (0.7, 0.38, 0.22), metal=1.0, rough=0.4),
    'gilt': mat('M_gilt', (0.6, 0.45, 0.2), metal=1.0, rough=0.4),
    'iron': mat('M_iron', (0.22, 0.22, 0.22), metal=0.8, rough=0.6),
    'ironpaint': mat('M_ironpaint', (0.36, 0.37, 0.35), metal=0.2, rough=0.7),
    'grate': mat('M_grate', (0.15, 0.15, 0.15), metal=0.9, rough=0.55),
    'ceiling': mat('M_ceiling', (0.9, 0.88, 0.8), emit=(1, 1, 1)),
    'plaster': mat('M_plaster', (0.55, 0.52, 0.46), rough=0.9),
    'marble': mat('M_marble', (0.82, 0.8, 0.76), rough=0.4),
    'bronze': mat('M_bronze', (0.35, 0.25, 0.14), metal=1.0, rough=0.45),
    'glass': mat('M_glass', (0.8, 0.9, 0.9), rough=0.05),
    'pipe': mat('M_pipe', (0.7, 0.7, 0.68), metal=1.0, rough=0.3),
    'linen': mat('M_linen', (0.8, 0.78, 0.72), rough=0.95),
    'paper': mat('M_paper', (0.78, 0.74, 0.62), rough=0.95),
    'rubber': mat('M_rubber', (0.12, 0.1, 0.08), rough=0.7),
    'bulb': mat('M_bulb', (1, 0.95, 0.85), emit=(1, 1, 1)),
    'globe': mat('M_globe', (1, 0.97, 0.9), emit=(1, 1, 1)),
    'coal': mat('M_coal', (0.9, 0.3, 0.05), emit=(1, 0.3, 0.05)),
    'water': mat('M_water', (0.5, 0.7, 0.75), rough=0.05),
    'shell': mat('M_shell', (0.85, 0.75, 0.65), rough=0.5),
    'coral': mat('M_coralspec', (0.75, 0.2, 0.15), rough=0.6),
    'pearl': mat('M_pearl', (0.92, 0.9, 0.86), rough=0.2),
    'dial': mat('M_dial', (0.88, 0.85, 0.76), rough=0.6),
    'black': mat('M_black', (0.02, 0.02, 0.02), rough=0.6),
    'hull': mat('M_hull', (0.18, 0.18, 0.17), metal=0.7, rough=0.55),
    'lens': mat('M_lens', (0.9, 0.95, 1.0), emit=(1, 1, 1)),
    'lensdark': mat('M_lensdark', (0.2, 0.25, 0.27), rough=0.1),
    'crystal': mat('M_crystal', (0.8, 0.9, 0.95), rough=0.05),
}
MAT_LIST = list(M.values())
MI = {k: MAT_LIST.index(v) for k, v in M.items()}

def obj_from(name, build, c='INT', props=None, smooth=None):
    bm = bmesh.new()
    build(bm)
    return new_obj(name, bm, MAT_LIST, c, props, smooth)

# ---------------------------------------------------------------- room shells
def wall(bm, P0, du, dv, A, Z, openings, mi, step=0.5):
    """Wall rectangle [0,A]x[0,Z] mapped by P0 + du*a + dv*z, with rectangular openings (a0,a1,z0,z1)."""
    As = sorted(set([0, A] + [o[0] for o in openings] + [o[1] for o in openings]))
    Zs = sorted(set([0, Z] + [o[2] for o in openings] + [o[3] for o in openings]))
    for i in range(len(As) - 1):
        for j in range(len(Zs) - 1):
            a0, a1, z0, z1 = As[i], As[i + 1], Zs[j], Zs[j + 1]
            if a1 - a0 < 1e-4 or z1 - z0 < 1e-4: continue
            cm, cz = (a0 + a1) / 2, (z0 + z1) / 2
            if any(o[0] < cm < o[1] and o[2] < cz < o[3] for o in openings): continue
            grid_quad(bm, P0 + du * a0 + dv * z0, du * (a1 - a0), dv * (z1 - z0), max(1, math.ceil((a1 - a0) / step)), max(1, math.ceil((z1 - z0) / step)), mi)

def room(name, x0, x1, y0, y1, h, ops=None, floor='carpet', walls='tapestry', ceil='plaster', ceiling=True, step=0.5, lower=None):
    """Inward-facing room. ops: dict wall-> list of (a0,a1,z0,z1); walls 'x0','x1','y0','y1'.
    a is measured: x0 wall along +Y from y0; x1 wall along -Y from y1; y0 wall along -X from x1; y1 wall along +X from x0."""
    ops = ops or {}
    def b(bm):
        V = Vector
        grid_quad(bm, V((x0, y0, 0)), V((x1 - x0, 0, 0)), V((0, y1 - y0, 0)), math.ceil((x1 - x0) / step), math.ceil((y1 - y0) / step), MI[floor])
        if ceiling:
            grid_quad(bm, V((x0, y0, h)), V((0, y1 - y0, 0)), V((x1 - x0, 0, 0)), math.ceil((y1 - y0) / step), math.ceil((x1 - x0) / step), MI[ceil])
        wl = MI[walls]
        wall(bm, V((x0, y0, 0)), V((0, 1, 0)), V((0, 0, 1)), y1 - y0, h, ops.get('x0', []), wl, step)
        wall(bm, V((x1, y1, 0)), V((0, -1, 0)), V((0, 0, 1)), y1 - y0, h, ops.get('x1', []), wl, step)
        wall(bm, V((x1, y0, 0)), V((-1, 0, 0)), V((0, 0, 1)), x1 - x0, h, ops.get('y0', []), wl, step)
        wall(bm, V((x0, y1, 0)), V((1, 0, 0)), V((0, 0, 1)), x1 - x0, h, ops.get('y1', []), wl, step)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    return obj_from(name, b, props={'col': 1})

def reveal_x(bm, xa, xb, ya, yb, z0, z1, mi):
    """Lining of an opening through a partition normal to X, from xa to xb (xa<xb)."""
    V = Vector
    grid_quad(bm, V((xa, ya, z0)), V((xb - xa, 0, 0)), V((0, 0, z1 - z0)), 1, 4, mi)          # side at ya, facing +Y
    grid_quad(bm, V((xb, yb, z0)), V((xa - xb, 0, 0)), V((0, 0, z1 - z0)), 1, 4, mi)          # side at yb, facing -Y
    grid_quad(bm, V((xa, ya, z1)), V((0, yb - ya, 0)), V((xb - xa, 0, 0)), 2, 1, mi)          # top facing -Z
    grid_quad(bm, V((xa, ya, z0)), V((xb - xa, 0, 0)), V((0, yb - ya, 0)), 1, 2, mi)          # threshold facing +Z

def reveal_y(bm, ya, yb, xa, xb, z0, z1, mi):
    V = Vector
    grid_quad(bm, V((xa, yb, z0)), V((0, ya - yb, 0)), V((0, 0, z1 - z0)), 1, 4, mi)          # side at xa facing +X
    grid_quad(bm, V((xb, ya, z0)), V((0, yb - ya, 0)), V((0, 0, z1 - z0)), 1, 4, mi)          # side at xb facing -X
    grid_quad(bm, V((xa, ya, z1)), V((xb - xa, 0, 0)), V((0, yb - ya, 0)), 2, 1, mi)          # top facing -Z
    grid_quad(bm, V((xa, ya, z0)), V((0, yb - ya, 0)), V((xb - xa, 0, 0)), 1, 2, mi)          # threshold

# ---- layout constants
SAL = dict(x0=5.0, x1=14.1, y0=-2.9, y1=2.9, h=4.0)
LIB = dict(x0=0.4, x1=4.85, y0=-2.9, y1=2.9, h=3.4)
NEMO = dict(x0=14.25, x1=18.6, y0=-1.85, y1=2.75, h=2.8)
ARON = dict(x0=18.75, x1=21.0, y0=-1.85, y1=2.6, h=2.7)
FPAS = dict(x0=14.25, x1=21.0, y0=-3.1, y1=-2.0, h=2.45)
WAIST = dict(x0=-17.0, x1=0.25, y0=-3.1, y1=-2.0, h=2.4)
WELL = dict(x0=-6.0, x1=-4.4, y0=-1.85, y1=-0.2, h=5.3)
WARD = dict(x0=-21.0, x1=-17.15, y0=-3.1, y1=2.0, h=2.6)
LOCK = dict(x0=-20.4, x1=-18.2, y0=2.15, y1=3.45, h=2.3)
DOOR_H = 2.05
WIN = dict(xc=9.55, w=3.0, z0=0.8, z1=2.9)

# Saloon. Openings: fore wall (x1, a from y1 downward): door to passage at y -2.85..-2.05, door to Nemo's room y 1.6..2.4
# aft wall (x0, a from y0 up): door to library at y -2.85..-2.05; side walls: windows.
def a_x1(y_lo, y_hi, y1): return (y1 - y_hi, y1 - y_lo)
def a_x0(y_lo, y_hi, y0): return (y_lo - y0, y_hi - y0)
def a_y0(x_lo, x_hi, x1): return (x1 - x_hi, x1 - x_lo)
def a_y1(x_lo, x_hi, x0): return (x_lo - x0, x_hi - x0)

S = SAL
wa = a_y1(WIN['xc'] - WIN['w'] / 2, WIN['xc'] + WIN['w'] / 2, S['x0'])
wb = a_y0(WIN['xc'] - WIN['w'] / 2, WIN['xc'] + WIN['w'] / 2, S['x1'])
room('saloon_shell', S['x0'], S['x1'], S['y0'], S['y1'], S['h'], ops={
    'x1': [(*a_x1(-2.85, -2.05, S['y1']), 0, DOOR_H), (*a_x1(1.6, 2.4, S['y1']), 0, DOOR_H)],
    'x0': [(*a_x0(-2.85, -2.05, S['y0']), 0, DOOR_H)],
    'y1': [(*wa, WIN['z0'], WIN['z1'])],
    'y0': [(*wb, WIN['z0'], WIN['z1'])],
}, ceiling=False)

# coved luminous ceiling: cove from wall top (h) up to a recessed panel
def sal_ceiling(bm):
    V = Vector
    x0, x1, y0, y1, h = S['x0'], S['x1'], S['y0'], S['y1'], S['h']
    ins, top = 0.85, 4.5
    corners_lo = [V((x0, y0, h)), V((x1, y0, h)), V((x1, y1, h)), V((x0, y1, h))]
    corners_hi = [V((x0 + ins, y0 + ins, top)), V((x1 - ins, y0 + ins, top)), V((x1 - ins, y1 - ins, top)), V((x0 + ins, y1 - ins, top))]
    for k in range(4):
        a, b2 = corners_lo[k], corners_lo[(k + 1) % 4]
        c, d = corners_hi[(k + 1) % 4], corners_hi[k]
        n = max(2, int((a - b2).length / 0.6))
        vs = []
        for i in range(n + 1):
            t = i / n
            lo = a.lerp(b2, t); hi = d.lerp(c, t)
            mid = lo.lerp(hi, 0.5) + V((0, 0, 0.12))  # curved cove
            vs.append((lo, mid, hi))
        for i in range(n):
            for r in range(2):
                q = [bm.verts.new(vs[i][r]), bm.verts.new(vs[i][r + 1]), bm.verts.new(vs[i + 1][r + 1]), bm.verts.new(vs[i + 1][r])]
                f = bm.faces.new(q); f.material_index = MI['plaster']
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
obj_from('saloon_cove', sal_ceiling)
def sal_panel(bm):
    V = Vector
    ins, top = 0.85, 4.5
    grid_quad(bm, V((S['x0'] + ins, S['y0'] + ins, top)), V((0, S['y1'] - S['y0'] - 2 * ins, 0)), V((S['x1'] - S['x0'] - 2 * ins, 0, 0)), 1, 1, MI['ceiling'])
o = obj_from('saloon_ceiling_light', sal_panel, props={'ia': 'ceiling'})
o.data.uv_layers.new(name='UVMap')
for li, l in enumerate(o.data.loops):
    co = o.data.vertices[l.vertex_index].co
    o.data.uv_layers.active.data[li].uv = ((co.x - S['x0'] - 0.85) / (S['x1'] - S['x0'] - 1.7), (co.y - S['y0'] - 0.85) / (S['y1'] - S['y0'] - 1.7))

# gilt moulding around the ceiling panel and cornice
def cornice(bm):
    x0, x1, y0, y1, h = S['x0'], S['x1'], S['y0'], S['y1'], S['h']
    for (a, b2, c0, c1) in [(x0, x1, y0, y0 + 0.12), (x0, x1, y1 - 0.12, y1)]:
        box(bm, a, b2, c0, c1, h - 0.18, h, MI['gilt'])
    for (a, b2) in [(x0, x0 + 0.12), (x1 - 0.12, x1)]:
        box(bm, a, b2, y0, y1, h - 0.18, h, MI['gilt'])
obj_from('saloon_cornice', cornice)

# window embrasures through the hull (to Y = +-3.75) and the crystal plates
def embrasure(bm, side):
    sgn = 1 if side == 'P' else -1
    ya, yb = (S['y1'], 3.75) if sgn > 0 else (-3.75, S['y0'])
    xa, xb = WIN['xc'] - WIN['w'] / 2, WIN['xc'] + WIN['w'] / 2
    V = Vector
    z0, z1 = WIN['z0'], WIN['z1']
    mi = MI['ebony']
    if sgn > 0:
        grid_quad(bm, V((xa, yb, z0)), V((0, ya - yb, 0)), V((0, 0, z1 - z0)), 2, 3, mi)
        grid_quad(bm, V((xb, ya, z0)), V((0, yb - ya, 0)), V((0, 0, z1 - z0)), 2, 3, mi)
        grid_quad(bm, V((xa, ya, z1)), V((xb - xa, 0, 0)), V((0, yb - ya, 0)), 4, 2, mi)
        grid_quad(bm, V((xa, ya, z0)), V((0, yb - ya, 0)), V((xb - xa, 0, 0)), 2, 4, MI['oak'])
    else:
        grid_quad(bm, V((xa, ya, z0)), V((0, yb - ya, 0)), V((0, 0, z1 - z0)), 2, 3, mi)
        grid_quad(bm, V((xb, yb, z0)), V((0, ya - yb, 0)), V((0, 0, z1 - z0)), 2, 3, mi)
        grid_quad(bm, V((xa, ya, z1)), V((xb - xa, 0, 0)), V((0, yb - ya, 0)), 4, 2, mi)
        grid_quad(bm, V((xa, ya, z0)), V((0, yb - ya, 0)), V((xb - xa, 0, 0)), 2, 4, MI['oak'])
    # brass frame on the room side with arched spandrels and copper bands across the crystal
    yf = S['y1'] + 0.001 if sgn > 0 else S['y0'] - 0.001
    yw = (S['y1'] - 0.04) if sgn > 0 else (S['y0'] + 0.04)
    t = 0.12
    box(bm, xa - t, xb + t, min(yf, yw), max(yf, yw), z1, z1 + t, MI['brass'])
    box(bm, xa - t, xb + t, min(yf, yw), max(yf, yw), z0 - t, z0, MI['brass'])
    box(bm, xa - t, xa, min(yf, yw), max(yf, yw), z0, z1, MI['brass'])
    box(bm, xb, xb + t, min(yf, yw), max(yf, yw), z0, z1, MI['brass'])
    # arched spandrels (ebony) fill the top corners so the opening reads as an arch
    n = 10; cx = (xa + xb) / 2; rx = (xb - xa) / 2; rz = 0.45; zb = z1 - rz
    for side_k in (0, 1):
        pts = []
        for i in range(n + 1):
            ang = math.pi / 2 * i / n
            if side_k == 0: px = cx - rx * math.cos(ang)
            else: px = cx + rx * math.cos(ang)
            pz = zb + rz * math.sin(ang)
            pts.append((px, pz))
        corner = (xa, z1) if side_k == 0 else (xb, z1)
        for i in range(n):
            vs = [V((corner[0], yw, corner[1])), V((pts[i][0], yw, pts[i][1])), V((pts[i + 1][0], yw, pts[i + 1][1]))]
            bv = [bm.verts.new(v) for v in vs]
            f = bm.faces.new(bv[::-1] if (sgn > 0) == (side_k == 1) else bv); f.material_index = MI['ebony']
    # copper bands on the crystal (outer face)
    yc = 3.72 if sgn > 0 else -3.72
    for k in range(1, 3):
        xx = xa + (xb - xa) * k / 3
        box(bm, xx - 0.03, xx + 0.03, min(yc, yc - 0.06 * sgn), max(yc, yc - 0.06 * sgn), z0, z1, MI['copper'])
    zz = (z0 + z1) / 2
    box(bm, xa, xb, min(yc, yc - 0.06 * sgn), max(yc, yc - 0.06 * sgn), zz - 0.03, zz + 0.03, MI['copper'])
for sd in ('P', 'S'):
    obj_from('saloon_window_' + sd, lambda bm, sd=sd: embrasure(bm, sd), props={'col': 1})

# ---------------------------------------------------------------- saloon furniture
def wainscot(bm, x0, x1, y0, y1, hgt=0.95, skip=()):
    t = 0.04
    segs = []
    if 'y0' not in skip: segs.append(('y', y0, x0, x1, +1))
    if 'y1' not in skip: segs.append(('y', y1, x0, x1, -1))
    if 'x0' not in skip: segs.append(('x', x0, y0, y1, +1))
    if 'x1' not in skip: segs.append(('x', x1, y0, y1, -1))
    for (ax, c, a0, a1, d) in segs:
        if ax == 'y':
            box(bm, a0, a1, min(c, c + t * d), max(c, c + t * d), 0, hgt, MI['ebony'], step=0.6)
            box(bm, a0, a1, min(c, c + (t + 0.03) * d), max(c, c + (t + 0.03) * d), hgt, hgt + 0.06, MI['brass'])
        else:
            box(bm, min(c, c + t * d), max(c, c + t * d), a0, a1, 0, hgt, MI['ebony'], step=0.6)
            box(bm, min(c, c + (t + 0.03) * d), max(c, c + (t + 0.03) * d), a0, a1, hgt, hgt + 0.06, MI['brass'])
def sal_wainscot(bm):
    xa, xb = WIN['xc'] - WIN['w'] / 2 - 0.12, WIN['xc'] + WIN['w'] / 2 + 0.12
    for (a, b2) in [(S['x0'], xa), (xb, S['x1'])]:
        box(bm, a, b2, S['y1'] - 0.04, S['y1'], 0, 0.95, MI['ebony'], step=0.6)
        box(bm, a, b2, S['y0'], S['y0'] + 0.04, 0, 0.95, MI['ebony'], step=0.6)
        box(bm, a, b2, S['y1'] - 0.07, S['y1'], 0.95, 1.01, MI['brass'])
        box(bm, a, b2, S['y0'], S['y0'] + 0.07, 0.95, 1.01, MI['brass'])
    box(bm, xa, xb, S['y1'] - 0.04, S['y1'], 0, WIN['z0'] - 0.12, MI['ebony'])
    box(bm, xa, xb, S['y0'], S['y0'] + 0.04, 0, WIN['z0'] - 0.12, MI['ebony'])
    # aft wall, leaving the library door
    box(bm, S['x0'], S['x0'] + 0.04, -2.05, S['y1'], 0, 0.95, MI['ebony'], step=0.6)
    box(bm, S['x0'], S['x0'] + 0.07, -2.05, S['y1'], 0.95, 1.01, MI['brass'])
obj_from('saloon_wainscot', sal_wainscot)

# door frames (brass architraves) around all saloon doors
def architrave_x(bm, x, ylo, yhi, d):
    t = 0.1
    xs = sorted([x, x + 0.05 * d])
    box(bm, xs[0], xs[1], ylo - t, ylo, 0, DOOR_H + t, MI['gilt'])
    box(bm, xs[0], xs[1], yhi, yhi + t, 0, DOOR_H + t, MI['gilt'])
    box(bm, xs[0], xs[1], ylo - t, yhi + t, DOOR_H, DOOR_H + t, MI['gilt'])
def sal_doors(bm):
    architrave_x(bm, S['x1'], -2.85, -2.05, -1)
    architrave_x(bm, S['x1'], 1.6, 2.4, -1)
    architrave_x(bm, S['x0'], -2.85, -2.05, 1)
    # reveals to adjoining rooms
    reveal_x(bm, S['x1'], NEMO['x0'], -2.85, -2.05, 0, DOOR_H, MI['ebony'])
    reveal_x(bm, S['x1'], NEMO['x0'], 1.6, 2.4, 0, DOOR_H, MI['ebony'])
    reveal_x(bm, LIB['x1'], S['x0'], -2.85, -2.05, 0, DOOR_H, MI['ebony'])
obj_from('saloon_doorframes', sal_doors, props={'col': 1})

# the organ (fore wall), after the engraving: gothic case, pipe flat, console and bench
def organ(bm):
    X = S['x1']; yc = 0.3
    # case
    box(bm, X - 0.75, X - 0.02, yc - 1.25, yc + 1.25, 0, 1.05, MI['ebony'], step=0.4)          # console base
    box(bm, X - 0.95, X - 0.6, yc - 1.0, yc + 1.0, 0.72, 0.78, MI['ebony'])                      # key bed
    box(bm, X - 0.92, X - 0.62, yc - 0.92, yc + 0.92, 0.78, 0.8, MI['linen'])                    # keys (ivory)
    box(bm, X - 0.85, X - 0.6, yc - 0.92, yc + 0.92, 0.86, 0.88, MI['linen'])                    # upper manual
    box(bm, X - 0.85, X - 0.62, yc - 1.0, yc + 1.0, 0.8, 0.86, MI['ebony'])
    box(bm, X - 0.4, X - 0.02, yc - 1.25, yc + 1.25, 1.05, 3.5, MI['ebony'], step=0.5)          # tower
    # pinnacles and gable
    for yy in (yc - 1.2, yc + 1.2, yc - 0.45, yc + 0.45):
        box(bm, X - 0.45, X - 0.05, yy - 0.06, yy + 0.06, 1.0, 3.75 if abs(yy - yc) > 1 else 3.6, MI['ebony'])
        cylinder(bm, (X - 0.25, yy, 3.75 if abs(yy - yc) > 1 else 3.6), 0.07, 0.35, 6, MI['brass'], r2=0.0)
    gv = [Vector((X - 0.42, yc - 1.25, 3.5)), Vector((X - 0.42, yc, 3.95)), Vector((X - 0.42, yc + 1.25, 3.5))]
    f = bm.faces.new([bm.verts.new(v) for v in gv]); f.material_index = MI['ebony']
    # stop knobs
    for i in range(6):
        for s in (-1, 1):
            cylinder(bm, (X - 0.62, yc + s * (1.05 + 0.0), 0.95 + i * 0.07), 0.018, 0.06, 6, MI['linen'], axis='X')
    # pipes in a gentle crown
    n = 21
    for i in range(n):
        t = (i - (n - 1) / 2) / ((n - 1) / 2)
        L = 1.2 + 1.0 * (1 - t * t) + 0.15 * (i % 2)
        y = yc + t * 1.0
        r = 0.045 + 0.02 * (1 - abs(t))
        cylinder(bm, (X - 0.47, y, 1.35), r, L, 8, MI['pipe'])
        cylinder(bm, (X - 0.47, y, 1.1), 0.0, 0.25, 8, MI['pipe'], r2=r)   # foot
        box(bm, X - 0.52 - r * 0.6, X - 0.47, y - r * 0.5, y + r * 0.5, 1.42, 1.48, MI['black'])  # mouth
obj_from('organ', organ, props={'col': 1, 'ia': 'organ'}, smooth=35)
def organ_bench(bm):
    X = S['x1']
    box(bm, X - 1.55, X - 1.15, -0.55, 1.15, 0.42, 0.48, MI['leather'])
    for (a, b2) in [(-0.5, -0.42), (1.02, 1.1)]:
        box(bm, X - 1.5, X - 1.2, a, b2, 0, 0.42, MI['ebony'])
obj_from('organ_bench', organ_bench, props={'col': 1})

# curtains framing the organ (tied back from the two doors)
def curtain(bm, X, ya, yb, folds=7, depth=0.12, mi=None, tie=None):
    n = folds * 4
    rows = []
    for zi in range(9):
        z = 0.02 + zi * (S['h'] - 0.25) / 8
        row = []
        for i in range(n + 1):
            t = i / n
            y = ya + (yb - ya) * t
            if tie is not None:
                pinch = math.exp(-((z - 1.1) ** 2) / 0.25)
                y = ya + (yb - ya) * (t * (1 - 0.55 * pinch)) if tie < 0 else yb - (yb - ya) * ((1 - t) * (1 - 0.55 * pinch))
            x = X - 0.08 - depth * (0.5 + 0.5 * math.sin(t * folds * 2 * math.pi))
            row.append(bm.verts.new(Vector((x, y, z))))
        rows.append(row)
    for zi in range(8):
        for i in range(n):
            f = bm.faces.new([rows[zi][i], rows[zi][i + 1], rows[zi + 1][i + 1], rows[zi + 1][i]][::-1]); f.material_index = mi
def curtains(bm):
    curtain(bm, S['x1'], -2.9, -1.0, folds=5, mi=MI['velvet'], tie=-1)
    curtain(bm, S['x1'], 1.55, 2.9, folds=4, mi=MI['velvet'], tie=1)
    box(bm, S['x1'] - 0.12, S['x1'] - 0.06, -2.9, 2.9, S['h'] - 0.28, S['h'] - 0.22, MI['brass'])
obj_from('organ_curtains', curtains, smooth=60)

# fountain table with the giant tridacna basin, and the glass-topped specimen table around it
def fountain(bm):
    xc, yc = 9.55, 0.0
    # long table
    box(bm, xc - 1.35, xc + 1.35, yc - 0.55, yc + 0.55, 0.68, 0.76, MI['ebony'], step=0.5)
    for sx in (-1, 1):
        for sy in (-1, 1):
            cylinder(bm, (xc + sx * 1.2, yc + sy * 0.42, 0), 0.05, 0.68, 8, MI['ebony'], r2=0.035)
    box(bm, xc - 1.25, xc + 1.25, yc - 0.48, yc + 0.48, 0.18, 0.22, MI['ebony'])
    # rolled display cylinders (glass bolsters) at both ends
    for sx in (-1, 1):
        cylinder(bm, (xc + sx * 1.0, yc - 0.5, 0.92), 0.16, 1.0, 12, MI['glass'], axis='Y')
        for e in (0, 1):
            cylinder(bm, (xc + sx * 1.0, yc - 0.52 + e * 1.02, 0.92), 0.18, 0.02, 12, MI['brass'], axis='Y')
    # pedestal and tridacna
    lathe(bm, [(0.0, 0.76), (0.22, 0.76), (0.14, 0.82), (0.1, 0.95), (0.16, 1.02), (0.0, 1.02)], 12, (xc, yc, 0), MI['bronze'])
obj_from('fountain_table', fountain, props={'col': 1}, smooth=40)
def tridacna(bm):
    xc, yc, z = 9.55, 0.0, 1.02
    # scalloped bivalve basin: lathe with a fluted rim
    seg = 24
    prof = [(0.0, 0.0), (0.25, 0.02), (0.45, 0.1), (0.58, 0.22), (0.62, 0.3)]
    rows = []
    for (r, h) in prof:
        row = []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            flute = 1 + (0.09 * (r / 0.62)) * math.cos(a * 6)
            ry = r * 0.72
            row.append(bm.verts.new(Vector((xc + math.cos(a) * r * flute, yc + math.sin(a) * ry * flute, z + h + 0.06 * (r / 0.62) * math.cos(a * 6)))))
        rows.append(row)
    for k in range(len(rows) - 1):
        for i in range(seg):
            f = bm.faces.new([rows[k][i], rows[k][(i + 1) % seg], rows[k + 1][(i + 1) % seg], rows[k + 1][i]]); f.material_index = MI['shell']
    # outside skin
    for k in range(len(rows) - 1):
        for i in range(seg):
            vs = [rows[k][i].co, rows[k + 1][i].co, rows[k + 1][(i + 1) % seg].co, rows[k][(i + 1) % seg].co]
            vv = [bm.verts.new(v - Vector((0, 0, 0.03))) for v in vs]
            f = bm.faces.new(vv); f.material_index = MI['shell']
    # water surface in the basin
    wv = [bm.verts.new(Vector((xc + math.cos(2 * math.pi * i / seg) * 0.5, yc + math.sin(2 * math.pi * i / seg) * 0.36, z + 0.2))) for i in range(seg)]
    f = bm.faces.new(wv); f.material_index = MI['water']
obj_from('tridacna', tridacna, smooth=50)

# divans (curved arms, buttoned leather), four in the saloon
def divan(bm, x0, x1, y_wall, d):
    """d=+1 if divan faces +Y (against y0 wall)."""
    yb = y_wall + 0.06 * d; yf = y_wall + 0.82 * d
    lo, hi = min(yb, yf), max(yb, yf)
    box(bm, x0, x1, lo, hi, 0.08, 0.42, MI['leather'], step=0.4)
    box(bm, x0 + 0.05, x1 - 0.05, lo + 0.02, hi - 0.02, 0.42, 0.5, MI['leather'], step=0.4)
    yback0 = yb; yback1 = yb + 0.22 * d
    box(bm, x0, x1, min(yback0, yback1), max(yback0, yback1), 0.42, 0.98, MI['leather'], step=0.4)
    for xx in (x0, x1 - 0.14):
        box(bm, xx, xx + 0.14, lo, hi, 0.42, 0.72, MI['leather'])
        cylinder(bm, (xx, (yb + yf) / 2 - 0.42, 0.72), 0.09, 0.84, 10, MI['leather'], axis='Y') if d > 0 else cylinder(bm, (xx, (yb + yf) / 2 - 0.42, 0.72), 0.09, 0.84, 10, MI['leather'], axis='Y')
    for xx in (x0 + 0.05, x1 - 0.1):
        for yy in (lo + 0.05, hi - 0.1):
            box(bm, xx, xx + 0.05, yy, yy + 0.05, 0, 0.08, MI['ebony'])
def divans(bm):
    xa, xb = WIN['xc'] - WIN['w'] / 2 - 0.3, WIN['xc'] + WIN['w'] / 2 + 0.3
    for (a, b2) in [(S['x0'] + 0.9, xa), (xb, S['x1'] - 1.7)]:
        divan(bm, a, b2, S['y1'], -1)
        divan(bm, a, b2, S['y0'], 1)
    # long window seat under each window
    for (yw, d) in [(S['y1'], -1), (S['y0'], 1)]:
        y0_, y1_ = sorted([yw + 0.04 * d, yw + 0.5 * d])
        box(bm, WIN['xc'] - 1.5, WIN['xc'] + 1.5, y0_, y1_, 0.0, 0.45, MI['leather'], step=0.5)
obj_from('saloon_divans', divans, props={'col': 1})

# glass cases fixed by copper rivets (specimens are added in-engine), mosaic table, busts
def case(bm, x0, x1, y0, y1, hgt=1.0):
    box(bm, x0, x1, y0, y1, 0.0, hgt - 0.25, MI['ebony'], step=0.4)
    box(bm, x0 - 0.02, x1 + 0.02, y0 - 0.02, y1 + 0.02, hgt - 0.25, hgt - 0.2, MI['brass'])
    # glass box on top
    gz0, gz1 = hgt - 0.2, hgt + 0.08
    box(bm, x0 + 0.01, x1 - 0.01, y0 + 0.01, y1 - 0.01, gz0, gz1, MI['glass'])
    # copper frame and rivets
    for (xx, yy) in [(x0, y0), (x1, y0), (x0, y1), (x1, y1)]:
        box(bm, xx - 0.015, xx + 0.015, yy - 0.015, yy + 0.015, gz0, gz1 + 0.01, MI['copper'])
    for t in range(6):
        xx = x0 + (x1 - x0) * (t + 0.5) / 6
        for yy in (y0, y1):
            cylinder(bm, (xx, yy, gz1 + 0.005), 0.008, 0.012, 5, MI['copper'])
CASES = [(5.15, 5.75, -1.65, -0.15), (5.15, 5.75, 0.45, 1.95), (12.0, 13.1, -2.85, -2.35), (5.9, 7.0, 2.35, 2.85)]
def cases(bm):
    for c in CASES: case(bm, *c)
obj_from('saloon_cases', cases, props={'col': 1, 'cases': str(CASES)})

def mosaic_table(bm):
    xc, yc = 7.0, -1.1
    lathe(bm, [(0.0, 0.74), (0.5, 0.74), (0.5, 0.78), (0.0, 0.78)], 16, (xc, yc, 0), MI['marble'])
    lathe(bm, [(0.0, 0.0), (0.28, 0.0), (0.25, 0.06), (0.07, 0.12), (0.05, 0.5), (0.1, 0.62), (0.14, 0.74), (0.0, 0.74)], 10, (xc, yc, 0), MI['bronze'])
obj_from('mosaic_table', mosaic_table, props={'col': 1}, smooth=40)

def bust(bm, xc, yc, mi):
    lathe(bm, [(0.0, 0.0), (0.24, 0.0), (0.24, 0.08), (0.18, 0.12), (0.15, 0.9), (0.2, 0.96), (0.22, 1.05), (0.0, 1.05)], 8, (xc, yc, 0), MI['ebony'])
    # shoulders and chest
    lathe(bm, [(0.0, 1.05), (0.17, 1.05), (0.24, 1.18), (0.22, 1.32), (0.12, 1.4), (0.06, 1.42), (0.0, 1.42)], 10, (xc, yc, 0), mi)
    # neck and head
    lathe(bm, [(0.0, 1.4), (0.055, 1.4), (0.06, 1.5), (0.1, 1.55), (0.11, 1.65), (0.1, 1.73), (0.06, 1.79), (0.0, 1.8)], 10, (xc, yc, 0), mi)
def busts(bm):
    bust(bm, 5.45, 2.45, MI['marble']); bust(bm, 5.45, -2.45, MI['bronze'])
    bust(bm, 13.75, 2.6, MI['marble']); bust(bm, 13.65, -1.7, MI['marble'])
obj_from('saloon_busts', busts, props={'col': 1}, smooth=50)

# controls on the aft wall: ceiling switch, panel lever, and the instruments
def controls_plate(bm):
    x = S['x0'] + 0.02
    box(bm, x, x + 0.03, -1.95, -1.25, 1.0, 1.6, MI['brass'])
    for yy in (-1.8, -1.4):
        box(bm, x + 0.03, x + 0.06, yy - 0.05, yy + 0.05, 1.05, 1.5, MI['ebony'])
obj_from('controls_plate', controls_plate)
def lever(name, yy, ia):
    def b(bm):
        cylinder(bm, (0, 0, 0), 0.025, 0.06, 8, MI['brass'], axis='X')
        box(bm, 0.03, 0.06, -0.015, 0.015, -0.02, 0.22, MI['brass'])
        cylinder(bm, (0.045, 0, 0.24), 0.03, 0.05, 8, MI['ebony'], axis='X')
    o = obj_from(name, b, props={'ia': ia})
    o.location = (S['x0'] + 0.06, yy, 1.27)
    return o
lever('IA_ceilingSwitch', -1.8, 'ceilingSwitch')
lever('IA_panelLever', -1.4, 'panelLever')

def dial(bm, c, r, axis_n, face='dial', rim='brass', depth=0.04):
    """Round instrument; axis_n: 'X+' etc gives facing direction."""
    ax = axis_n[0]; s = 1 if axis_n[1] == '+' else -1
    cx, cy, cz = c
    if ax == 'X':
        cylinder(bm, (cx, cy, cz), r, depth * s, 20, MI[rim], axis='X')
        cylinder(bm, (cx + depth * s + 0.001 * s, cy, cz), r * 0.86, 0.004 * s, 20, MI[face], axis='X')
    else:
        cylinder(bm, (cx, cy, cz), r, depth * s, 20, MI[rim], axis='Y')
        cylinder(bm, (cx, cy + depth * s + 0.001 * s, cz), r * 0.86, 0.004 * s, 20, MI[face], axis='Y')

INSTR_SAL = [('manometer', (S['x0'] + 0.01, -0.85, 1.95), 0.17), ('clock', (S['x0'] + 0.01, -0.85, 2.45), 0.2),
             ('speed', (S['x0'] + 0.01, -1.35, 2.2), 0.12)]
def sal_instruments(bm):
    for (nm, c, r) in INSTR_SAL: dial(bm, c, r, 'X+')
obj_from('saloon_instruments', sal_instruments)
def needle(name, c, r, axis='X+', ia=None):
    def b(bm):
        s = 1 if axis[1] == '+' else -1
        if axis[0] == 'X':
            box(bm, 0, 0.006, -0.006, 0.006, -r * 0.15, r * 0.78, MI['black'])
            cylinder(bm, (0, 0, 0), 0.012, 0.012, 8, MI['brass'], axis='X')
        else:
            box(bm, -0.006, 0.006, 0, 0.006, -r * 0.15, r * 0.78, MI['black'])
            cylinder(bm, (0, 0, 0), 0.012, 0.012, 8, MI['brass'], axis='Y')
    props = {'needle': name}
    if ia: props['ia'] = ia
    o = obj_from('NEEDLE_' + name + '_' + str(int(c[0] * 10)), b, props=props)
    s = 1 if axis[1] == '+' else -1
    o.location = (c[0] + 0.046 * s, c[1], c[2]) if axis[0] == 'X' else (c[0], c[1] + 0.046 * s, c[2])
    return o
for (nm, c, r) in INSTR_SAL: needle(nm, c, r, 'X+', ia='instr_' + nm)

# picture frames: the canvas faces get per-picture materials in-engine (named slots)
PICS = []
def frames(bm):
    rnd = random.Random(11)
    walls = []
    xa, xb = WIN['xc'] - WIN['w'] / 2 - 0.25, WIN['xc'] + WIN['w'] / 2 + 0.25
    # side walls: two rows over the divans, one column either side of the window
    for (yw, d, tag) in [(S['y1'], -1, 'P'), (S['y0'], 1, 'S')]:
        for (a, b2) in [(S['x0'] + 0.9, xa), (xb, S['x1'] - 1.7)]:
            span = b2 - a
            n = 2 if span > 2 else 1
            for k in range(n):
                xc = a + span * (k + 0.5) / n
                walls.append(('y', yw, d, xc, 1.95, 0.95 + rnd.random() * 0.25, 0.75 + rnd.random() * 0.2))
                walls.append(('y', yw, d, xc + rnd.uniform(-0.15, 0.15), 3.15, 0.7 + rnd.random() * 0.2, 0.55 + rnd.random() * 0.1))
        walls.append(('y', yw, d, WIN['xc'], 3.45, 1.0, 0.45))
    # aft wall pictures
    for (yc, zc, w, h) in [(0.0, 1.95, 0.8, 0.6), (1.2, 1.95, 0.7, 0.9), (2.2, 2.0, 0.6, 0.75), (0.6, 3.1, 1.3, 0.8), (-0.9, 3.15, 0.8, 0.6), (2.15, 3.15, 0.6, 0.6)]:
        walls.append(('x', S['x0'], 1, yc, zc, w, h))
    for i, (ax, c, d, u, zc, w, h) in enumerate(walls):
        t = 0.07
        if ax == 'y':
            y0, y1 = sorted([c, c + 0.05 * d])
            box(bm, u - w / 2 - t, u + w / 2 + t, y0, y1, zc - h / 2 - t, zc + h / 2 + t, MI['gilt'])
            PICS.append({'i': i, 'c': [u, c + 0.051 * d, zc], 'n': [0, d, 0], 'w': w, 'h': h})
        else:
            x0, x1 = sorted([c, c + 0.05 * d])
            box(bm, x0, x1, u - w / 2 - t, u + w / 2 + t, zc - h / 2 - t, zc + h / 2 + t, MI['gilt'])
            PICS.append({'i': i, 'c': [c + 0.051 * d, u, zc], 'n': [d, 0, 0], 'w': w, 'h': h})
o = obj_from('saloon_frames', frames)
import json
o['pictures'] = json.dumps(PICS)

# ---------------------------------------------------------------- library
L = LIB
room('library_shell', L['x0'], L['x1'], L['y0'], L['y1'], L['h'], ops={
    'x1': [(*a_x1(-2.85, -2.05, L['y1']), 0, DOOR_H)],
    'x0': [(*a_x0(-2.85, -2.05, L['y0']), 0, DOOR_H)],
}, walls='ebony', ceil='plaster')
SHELVES = []
def library(bm):
    dpt = 0.36
    runs = [  # (axis, wall coord, dir into room, a0, a1)
        ('y', L['y1'], -1, L['x0'] + 0.05, L['x1'] - 0.05),
        ('y', L['y0'], 1, L['x0'] + 0.05, L['x1'] - 0.05),
        ('x', L['x0'], 1, -1.95, L['y1'] - 0.4),
        ('x', L['x1'], -1, -1.95, L['y1'] - 0.4),
    ]
    for (ax, c, d, a0, a1) in runs:
        if ax == 'y':
            ylo, yhi = sorted([c, c + dpt * d])
            box(bm, a0, a1, ylo, yhi, 0.55, 0.6, MI['ebony'])
            for k in range(6):
                z = 0.6 + k * 0.47
                box(bm, a0, a1, ylo, yhi, z, z + 0.03, MI['ebony'])
                box(bm, a0, a1, min(c + dpt * d, c + (dpt + 0.01) * d), max(c + dpt * d, c + (dpt + 0.01) * d), z, z + 0.03, MI['brass'])
                if k < 5: SHELVES.append({'ax': 'y', 'c': c, 'd': d, 'a0': a0, 'a1': a1, 'z': z + 0.03, 'dpt': dpt})
            nv = max(2, int((a1 - a0) / 1.1))
            for i in range(nv + 1):
                aa = a0 + (a1 - a0) * i / nv
                box(bm, aa - 0.025, aa + 0.025, ylo, yhi, 0.55, 3.0, MI['ebony'])
            # divan at the base
            ylo2, yhi2 = sorted([c + 0.0 * d, c + 0.75 * d])
            box(bm, a0, a1, ylo2, yhi2, 0.0, 0.44, MI['leather'], step=0.5)
        else:
            xlo, xhi = sorted([c, c + dpt * d])
            box(bm, xlo, xhi, a0, a1, 0.55, 0.6, MI['ebony'])
            for k in range(6):
                z = 0.6 + k * 0.47
                box(bm, xlo, xhi, a0, a1, z, z + 0.03, MI['ebony'])
                if k < 5: SHELVES.append({'ax': 'x', 'c': c, 'd': d, 'a0': a0, 'a1': a1, 'z': z + 0.03, 'dpt': dpt})
            nv = max(2, int((a1 - a0) / 1.1))
            for i in range(nv + 1):
                aa = a0 + (a1 - a0) * i / nv
                box(bm, xlo, xhi, aa - 0.025, aa + 0.025, 0.55, 3.0, MI['ebony'])
            xlo2, xhi2 = sorted([c, c + 0.75 * d])
            box(bm, xlo2, xhi2, a0, a1, 0.0, 0.44, MI['leather'], step=0.5)
    # centre table with pamphlets and old newspapers
    xc = (L['x0'] + L['x1']) / 2
    box(bm, xc - 1.1, xc + 1.1, -0.75, 0.75, 0.72, 0.78, MI['ebony'], step=0.5)
    for sx in (-1, 1):
        box(bm, xc + sx * 0.95 - 0.08, xc + sx * 0.95 + 0.08, -0.65, 0.65, 0.0, 0.72, MI['ebony'])
    rnd = random.Random(5)
    for i in range(14):
        px, py = xc + rnd.uniform(-0.9, 0.9), rnd.uniform(-0.6, 0.6)
        w, hh = rnd.uniform(0.2, 0.42), rnd.uniform(0.28, 0.5)
        z = 0.78 + 0.003 * i
        a = rnd.uniform(-0.6, 0.6)
        vs = [Vector((px + math.cos(a) * u - math.sin(a) * v, py + math.sin(a) * u + math.cos(a) * v, z)) for (u, v) in [(-w / 2, -hh / 2), (w / 2, -hh / 2), (w / 2, hh / 2), (-w / 2, hh / 2)]]
        f = bm.faces.new([bm.verts.new(v) for v in vs]); f.material_index = MI['paper']
    # ceiling volutes for the four globes
    for gx in (L['x0'] + 1.2, L['x1'] - 1.2):
        for gy in (-1.3, 1.3):
            lathe(bm, [(0.42, L['h']), (0.36, L['h'] - 0.06), (0.28, L['h'] - 0.08)], 12, (gx, gy, 0), MI['gilt'])
    # brazier on a bronze stem
    lathe(bm, [(0.0, 0.0), (0.2, 0.0), (0.05, 0.08), (0.03, 0.9), (0.06, 0.95), (0.18, 1.0), (0.16, 1.08), (0.0, 1.04)], 10, (L['x1'] - 0.55, 2.05, 0), MI['bronze'])
obj_from('library', library, props={'col': 1}, smooth=40)
def library_glow(bm):
    for gx in (L['x0'] + 1.2, L['x1'] - 1.2):
        for gy in (-1.3, 1.3):
            lathe(bm, [(0.0, L['h'] - 0.42), (0.17, L['h'] - 0.33), (0.25, L['h'] - 0.18), (0.27, L['h'] - 0.05)], 12, (gx, gy, 0), MI['globe'])
    lathe(bm, [(0.0, 1.06), (0.13, 1.06), (0.0, 1.1)], 8, (L['x1'] - 0.55, 2.05, 0), MI['coal'])
o = obj_from('library_globes', library_glow, smooth=60)
o['lights'] = json.dumps([[gx, gy, L['h'] - 0.25] for gx in (L['x0'] + 1.2, L['x1'] - 1.2) for gy in (-1.3, 1.3)])
o2 = bpy.data.objects['library']
o2['shelves'] = json.dumps(SHELVES)
def lib_doors(bm):
    reveal_x(bm, WAIST['x1'], L['x0'], -2.85, -2.05, 0, DOOR_H, MI['ebony'])
obj_from('library_doorframes', lib_doors, props={'col': 1})

# ---------------------------------------------------------------- the captain's room
N = NEMO
room('nemo_shell', N['x0'], N['x1'], N['y0'], N['y1'], N['h'], ops={
    'y0': [(*a_y0(16.0, 16.8, N['x1']), 0, DOOR_H)],
    'x0': [(*a_x0(1.6, 2.4, N['y0']), 0, DOOR_H)],
}, floor='oak', walls='plaster', ceil='plaster')
INSTR_NEMO = [('manometer', (N['x1'] - 0.01, 0.2, 1.75), 0.2), ('clock', (N['x1'] - 0.01, 0.2, 2.25), 0.2),
              ('speed', (N['x1'] - 0.01, -0.45, 1.85), 0.13), ('barometer', (N['x1'] - 0.01, 0.85, 1.85), 0.14),
              ('hygrometer', (N['x1'] - 0.01, -0.45, 1.45), 0.09), ('compassdial', (N['x1'] - 0.01, 0.85, 1.42), 0.1),
              ('chrono1', (N['x1'] - 0.01, -1.0, 1.95), 0.07), ('chrono2', (N['x1'] - 0.01, -1.0, 1.7), 0.07), ('chrono3', (N['x1'] - 0.01, -1.0, 1.45), 0.07)]
def nemo_room(bm):
    # iron bedstead
    xb0, xb1 = N['x0'] + 0.4, N['x0'] + 2.4
    yb0, yb1 = N['y1'] - 0.95, N['y1'] - 0.05
    box(bm, xb0, xb1, yb0, yb1, 0.35, 0.5, MI['linen'])
    for (xx, top) in ((xb0, 0.95), (xb1, 0.75)):
        for yy in (yb0, yb1):
            cylinder(bm, (xx, yy, 0), 0.02, top, 6, MI['iron'])
        cylinder(bm, (xx, yb0, top - 0.04), 0.015, yb1 - yb0, 6, MI['iron'], axis='Y')
        for k in range(5):
            cylinder(bm, (xx, yb0 + (yb1 - yb0) * (k + 0.5) / 5, 0.5), 0.01, top - 0.5, 5, MI['iron'])
    box(bm, xb0, xb1, yb0, yb1, 0.28, 0.35, MI['iron'])
    # table, chair, toilet articles
    box(bm, N['x1'] - 1.0, N['x1'] - 0.15, -0.9, 0.9, 0.72, 0.76, MI['oak'])
    for (xx, yy) in [(N['x1'] - 0.95, -0.85), (N['x1'] - 0.2, -0.85), (N['x1'] - 0.95, 0.85), (N['x1'] - 0.2, 0.85)]:
        box(bm, xx - 0.03, xx + 0.03, yy - 0.03, yy + 0.03, 0, 0.72, MI['oak'])
    box(bm, N['x1'] - 1.6, N['x1'] - 1.2, -0.2, 0.2, 0.44, 0.48, MI['oak'])
    box(bm, N['x1'] - 1.6, N['x1'] - 1.56, -0.2, 0.2, 0.48, 0.95, MI['oak'])
    for (xx, yy) in [(N['x1'] - 1.58, -0.18), (N['x1'] - 1.22, -0.18), (N['x1'] - 1.58, 0.18), (N['x1'] - 1.22, 0.18)]:
        box(bm, xx - 0.02, xx + 0.02, yy - 0.02, yy + 0.02, 0, 0.44, MI['oak'])
    box(bm, N['x0'] + 0.1, N['x0'] + 0.6, N['y0'] + 0.1, N['y0'] + 0.6, 0, 0.85, MI['oak'])
    lathe(bm, [(0.0, 0.85), (0.16, 0.86), (0.18, 0.95), (0.0, 0.9)], 10, (N['x0'] + 0.35, N['y0'] + 0.35, 0), MI['pipe'])
    # instruments board
    box(bm, N['x1'] - 0.03, N['x1'], -1.25, 1.15, 1.2, 2.5, MI['oak'])
    for (nm, c, r) in INSTR_NEMO: dial(bm, (c[0] - 0.02, c[1], c[2]), r, 'X-')
    # thermometer and storm glass tubes
    box(bm, N['x1'] - 0.06, N['x1'] - 0.03, 1.12, 1.18, 1.3, 2.2, MI['dial'])
    cylinder(bm, (N['x1'] - 0.08, 1.15, 1.3), 0.012, 0.9, 6, MI['glass'])
    cylinder(bm, (N['x1'] - 0.1, -1.18, 2.1), 0.04, 0.3, 10, MI['glass'])
    # sextant and glasses on the table
    cylinder(bm, (N['x1'] - 0.55, 0.45, 0.78), 0.03, 0.4, 10, MI['brass'], axis='Y')
    cylinder(bm, (N['x1'] - 0.5, -0.4, 0.76), 0.12, 0.08, 14, MI['brass'])
    # ceiling light
    lathe(bm, [(0.3, N['h']), (0.22, N['h'] - 0.06)], 12, (16.4, 0.4, 0), MI['gilt'])
obj_from('nemo_room', nemo_room, props={'col': 1}, smooth=40)
for (nm, c, r) in INSTR_NEMO:
    if nm in ('manometer', 'clock', 'speed', 'barometer'):
        needle(nm, (c[0] - 0.02, c[1], c[2]), r, 'X-', ia='instr_' + nm)

# ---------------------------------------------------------------- Aronnax's room
A = ARON
room('aronnax_shell', A['x0'], A['x1'], A['y0'], A['y1'], A['h'], ops={
    'y0': [(*a_y0(19.45, 20.25, A['x1']), 0, DOOR_H)],
}, floor='carpet', walls='tapestry', ceil='plaster')
def aronnax(bm):
    # bed against the bow partition
    box(bm, A['x1'] - 0.95, A['x1'] - 0.05, 0.4, A['y1'] - 0.05, 0.0, 0.45, MI['ebony'], step=0.5)
    box(bm, A['x1'] - 0.92, A['x1'] - 0.08, 0.43, A['y1'] - 0.08, 0.45, 0.58, MI['linen'], step=0.5)
    box(bm, A['x1'] - 0.85, A['x1'] - 0.15, A['y1'] - 0.55, A['y1'] - 0.12, 0.58, 0.7, MI['linen'])
    box(bm, A['x1'] - 0.95, A['x1'] - 0.05, A['y1'] - 0.08, A['y1'] - 0.02, 0.0, 1.1, MI['ebony'])
    # writing table with papers, chair, dressing table, wardrobe
    box(bm, A['x0'] + 0.05, A['x0'] + 0.75, 0.2, 1.5, 0.72, 0.77, MI['ebony'])
    for (xx, yy) in [(A['x0'] + 0.1, 0.25), (A['x0'] + 0.7, 0.25), (A['x0'] + 0.1, 1.45), (A['x0'] + 0.7, 1.45)]:
        box(bm, xx - 0.03, xx + 0.03, yy - 0.03, yy + 0.03, 0, 0.72, MI['ebony'])
    box(bm, A['x0'] + 0.9, A['x0'] + 1.3, 0.65, 1.05, 0.44, 0.48, MI['leather'])
    box(bm, A['x0'] + 1.26, A['x0'] + 1.3, 0.65, 1.05, 0.48, 0.95, MI['ebony'])
    for (xx, yy) in [(A['x0'] + 0.92, 0.67), (A['x0'] + 1.28, 0.67), (A['x0'] + 0.92, 1.03), (A['x0'] + 1.28, 1.03)]:
        box(bm, xx - 0.02, xx + 0.02, yy - 0.02, yy + 0.02, 0, 0.44, MI['ebony'])
    box(bm, A['x0'] + 0.05, A['x0'] + 0.6, -1.8, -0.9, 0, 0.8, MI['ebony'])
    box(bm, A['x0'] + 0.05, A['x0'] + 0.08, -1.7, -1.0, 1.0, 1.7, MI['gilt'])
    box(bm, A['x1'] - 0.6, A['x1'] - 0.05, -1.8, -0.6, 0, 2.0, MI['ebony'], step=0.5)
    rnd = random.Random(9)
    for i in range(7):
        px, py = A['x0'] + 0.4 + rnd.uniform(-0.25, 0.25), 0.85 + rnd.uniform(-0.5, 0.5)
        a = rnd.uniform(-0.5, 0.5); w, hh = 0.21, 0.29
        vs = [Vector((px + math.cos(a) * u - math.sin(a) * v, py + math.sin(a) * u + math.cos(a) * v, 0.772 + 0.002 * i)) for (u, v) in [(-w / 2, -hh / 2), (w / 2, -hh / 2), (w / 2, hh / 2), (-w / 2, hh / 2)]]
        f = bm.faces.new([bm.verts.new(v) for v in vs]); f.material_index = MI['paper']
    lathe(bm, [(0.25, A['h']), (0.2, A['h'] - 0.05)], 10, (19.9, 0.4, 0), MI['gilt'])
obj_from('aronnax_room', aronnax, props={'col': 1})
def note(bm):
    vs = [Vector((-0.1, -0.13, 0)), Vector((0.1, -0.13, 0)), Vector((0.1, 0.13, 0)), Vector((-0.1, 0.13, 0))]
    f = bm.faces.new([bm.verts.new(v) for v in vs]); f.material_index = MI['paper']
o = obj_from('IA_note', note, props={'ia': 'note'})
o.location = (A['x0'] + 0.42, 0.55, 0.79); o.rotation_euler = (0, 0, 0.3)

# ---------------------------------------------------------------- passages, well, wardrobe, flooding cell
F = FPAS
room('fpassage_shell', F['x0'], F['x1'], F['y0'], F['y1'], F['h'], ops={
    'x0': [(*a_x0(-2.85, -2.05, F['y0']), 0, DOOR_H)],
    'y1': [(*a_y1(16.0, 16.8, F['x0']), 0, DOOR_H), (*a_y1(19.45, 20.25, F['x0']), 0, DOOR_H)],
}, floor='grate', walls='ironpaint', ceil='ironpaint')
def fpass_reveals(bm):
    reveal_y(bm, F['y1'], NEMO['y0'], 16.0, 16.8, 0, DOOR_H, MI['iron'])
    reveal_y(bm, F['y1'], ARON['y0'], 19.45, 20.25, 0, DOOR_H, MI['iron'])
obj_from('fpassage_reveals', fpass_reveals, props={'col': 1})

W = WAIST
room('waist_shell', W['x0'], W['x1'], W['y0'], W['y1'], W['h'], ops={
    'x1': [(*a_x1(-2.85, -2.05, W['y1']), 0, DOOR_H)],
    'x0': [(*a_x0(-2.85, -2.05, W['y0']), 0, DOOR_H)],
    'y1': [(*a_y1(WELL['x0'] + 0.1, WELL['x1'] - 0.1, W['x0']), 0, 2.2)],
}, floor='grate', walls='ironpaint', ceil='ironpaint')
WL = WELL
room('well_shell', WL['x0'], WL['x1'], WL['y0'], WL['y1'], WL['h'], ops={
    'y0': [(*a_y0(WL['x0'] + 0.1, WL['x1'] - 0.1, WL['x1']), 0, 2.2)],
}, floor='grate', walls='ironpaint', ceil='iron')
def well_bits(bm):
    reveal_y(bm, W['y1'], WL['y0'], WL['x0'] + 0.1, WL['x1'] - 0.1, 0, 2.2, MI['iron'])
    # iron ladder fastened with an iron hook to the partition
    for yy in (-0.95, -0.45):
        box(bm, WL['x0'] + 0.08, WL['x0'] + 0.13, yy - 0.02, yy + 0.02, 0, WL['h'], MI['iron'])
    for k in range(17):
        z = 0.3 + k * 0.3
        cylinder(bm, (WL['x0'] + 0.105, -0.95, z), 0.015, 0.5, 6, MI['iron'], axis='Y')
    # hatch to the boat
    lathe(bm, [(0.45, WL['h'] - 0.02), (0.4, WL['h'] - 0.08), (0.0, WL['h'] - 0.1)], 12, (WL['x0'] + 0.7, -1.0, 0), MI['iron'])
    for a in range(4):
        ang = a * math.pi / 2
        box(bm, WL['x0'] + 0.7 + math.cos(ang) * 0.32 - 0.03, WL['x0'] + 0.7 + math.cos(ang) * 0.32 + 0.03, -1.0 + math.sin(ang) * 0.32 - 0.03, -1.0 + math.sin(ang) * 0.32 + 0.03, WL['h'] - 0.16, WL['h'] - 0.08, MI['brass'])
obj_from('well_bits', well_bits, props={'col': 1})
def waist_bits(bm):
    # pipes and cables along the ceiling
    for (yy, zz, r) in [(-2.25, 2.25, 0.06), (-2.45, 2.28, 0.035), (-2.9, 2.2, 0.045), (-3.0, 2.0, 0.025)]:
        cylinder(bm, (W['x0'], yy, zz), r, W['x1'] - W['x0'], 8, MI['copper' if r < 0.04 else 'iron'], axis='X')
        cylinder(bm, (F['x0'], yy, zz), r, F['x1'] - F['x0'], 8, MI['copper' if r < 0.04 else 'iron'], axis='X')
    # riveted frames every 1.2 m
    for (x0, x1) in [(W['x0'], W['x1']), (F['x0'], F['x1'])]:
        n = int((x1 - x0) / 1.2)
        for i in range(1, n):
            xx = x0 + (x1 - x0) * i / n
            box(bm, xx - 0.05, xx + 0.05, -3.1, -3.04, 0, 2.4, MI['iron'])
            box(bm, xx - 0.05, xx + 0.05, -3.1, -2.0, 2.33, 2.4, MI['iron'])
    # locked doors along the waist: dining room, crew cabin, kitchen, berth room
    for xc in (-1.6, -7.3, -9.7, -13.2):
        box(bm, xc - 0.45, xc + 0.45, -2.04, -2.0, 0, 2.0, MI['iron'])
        box(bm, xc - 0.52, xc + 0.52, -2.06, -2.0, 1.98, 2.08, MI['iron'])
        box(bm, xc + 0.25, xc + 0.35, -2.12, -2.04, 0.95, 1.05, MI['brass'])
        for zz in (0.25, 1.75):
            box(bm, xc - 0.45, xc - 0.38, -2.08, -2.04, zz, zz + 0.12, MI['iron'])
obj_from('waist_bits', waist_bits, props={'col': 1}, smooth=40)
BULBS = [(x, -2.55, 2.3) for x in (-15.5, -11.5, -8.5, -3.0, 1.0 - 1.4)] + [(x, -2.55, 2.35) for x in (15.2, 18.2, 20.5)]
def bulbs(bm):
    for (x, y, z) in BULBS:
        lathe(bm, [(0.0, z - 0.14), (0.06, z - 0.12), (0.07, z - 0.06), (0.04, z)], 8, (x, y, 0), MI['bulb'])
        for a in range(4):
            ang = a * math.pi / 2 + 0.4
            box(bm, x + math.cos(ang) * 0.075 - 0.006, x + math.cos(ang) * 0.075 + 0.006, y + math.sin(ang) * 0.075 - 0.006, y + math.sin(ang) * 0.075 + 0.006, z - 0.16, z + 0.02, MI['brass'])
o = obj_from('bulbs', bulbs)
o['lights'] = json.dumps([list(b) for b in BULBS])

D = WARD
room('wardrobe_shell', D['x0'], D['x1'], D['y0'], D['y1'], D['h'], ops={
    'x1': [(*a_x1(-2.85, -2.05, D['y1']), 0, DOOR_H)],
    'y1': [(*a_y1(-19.7, -18.9, D['x0']), 0, DOOR_H)],
    'x0': [(*a_x0(-0.9, -0.1, D['y0']), 0, DOOR_H)],
}, floor='grate', walls='ironpaint', ceil='ironpaint')
def ward_bits(bm):
    reveal_x(bm, D['x1'], W['x0'], -2.85, -2.05, 0, DOOR_H, MI['iron'])
    reveal_y(bm, D['y1'], LOCK['y0'], -19.7, -18.9, 0, DOOR_H, MI['iron'])
    # rail with hooks for the dozen apparatuses along the starboard wall and the aft wall
    cylinder(bm, (D['x0'] + 0.2, -2.85, 2.1), 0.025, 3.4, 8, MI['iron'], axis='X')
    for i in range(8):
        cylinder(bm, (D['x0'] + 0.45 + i * 0.42, -2.85, 1.95), 0.01, 0.15, 5, MI['iron'])
    # shelf for helmets, high on the wall (as in the engraving)
    box(bm, D['x0'] + 0.15, D['x1'] - 0.3, D['y0'] + 0.02, D['y0'] + 0.38, 2.25, 2.29, MI['oak'])
    # bench
    box(bm, -19.9, -18.0, -0.7, -0.25, 0.42, 0.47, MI['oak'])
    for xx in (-19.8, -18.1):
        box(bm, xx - 0.04, xx + 0.04, -0.68, -0.27, 0, 0.42, MI['oak'])
    # rack for air guns and the lamp hooks by the flooding cell
    box(bm, D['x0'] + 0.02, D['x0'] + 0.08, 0.4, 1.8, 0.9, 1.7, MI['oak'])
    for k in range(5):
        cylinder(bm, (D['x0'] + 0.08, 0.6 + k * 0.28, 1.5), 0.012, 0.1, 5, MI['iron'], axis='X')
    # engine-room door (shut), heavy and riveted
    box(bm, D['x0'], D['x0'] + 0.06, -0.95, -0.05, 0, 2.05, MI['iron'])
    lathe(bm, [(0.0, 0.0), (0.2, 0.0), (0.18, 0.04), (0.0, 0.04)], 10, (0, 0, 0), MI['brass'])
obj_from('wardrobe_bits', ward_bits, props={'col': 1}, smooth=40)

K = LOCK
room('lock_shell', K['x0'], K['x1'], K['y0'], K['y1'], K['h'], ops={
    'y0': [(*a_y0(-19.7, -18.9, K['x1']), 0, DOOR_H)],
    'y1': [(*a_y1(-19.7, -18.9, K['x0']), 0, DOOR_H)],
}, floor='grate', walls='iron', ceil='iron', step=0.35)
def lock_bits(bm):
    # outer passage through the hull plating
    reveal_y(bm, K['y1'], 3.98, -19.7, -18.9, 0, DOOR_H, MI['iron'])
    # drain grate, cold-water inlet, pressure gauge plate
    box(bm, -19.6, -19.0, 2.5, 3.1, 0.0, 0.01, MI['black'])
    cylinder(bm, (K['x1'] - 0.02, 2.4, 0.25), 0.06, -0.12, 10, MI['brass'], axis='X')
    dial(bm, (K['x1'] - 0.01, 3.05, 1.65), 0.1, 'X-')
obj_from('lock_bits', lock_bits, props={'col': 1})
needle('lockgauge', (K['x1'] - 0.03, 3.05, 1.65), 0.1, 'X-', ia='instr_lockgauge')
def valve(bm):
    # tap wheel: rim, spokes, hub (pivot at origin, facing -X)
    lathe(bm, [(0.15, -0.015), (0.175, -0.015), (0.175, 0.015), (0.15, 0.015)], 18, (0, 0, 0), MI['brass'], axis='X')
    for k in range(4):
        a = k * math.pi / 2
        box(bm, -0.01, 0.01, min(0, math.cos(a) * 0.16), max(0, math.cos(a) * 0.16) + 0.012, min(0, math.sin(a) * 0.16), max(0, math.sin(a) * 0.16) + 0.012, MI['brass'])
    cylinder(bm, (0, 0, 0), 0.035, 0.08, 10, MI['iron'], axis='X')
o = obj_from('IA_valve', valve, props={'ia': 'valve'})
o.location = (K['x1'] - 0.1, 2.55, 1.2)
o.rotation_euler = (0, 0, math.pi)
def pumpknob(bm):
    cylinder(bm, (0, 0, 0), 0.04, -0.05, 10, MI['brass'], axis='X')
o = obj_from('IA_pump', pumpknob, props={'ia': 'pump'})
o.location = (K['x1'] - 0.01, 3.05, 1.25)

# doors (hinged; pivot at the hinge edge). Each door is a panel in its own object.
def door_obj(name, w, h, kind, ia, loc, rot_z, port=False):
    def b(bm):
        if kind == 'ebony':
            box(bm, 0, w, -0.03, 0.03, 0, h, MI['ebony'], step=0.5)
            for (z0, z1) in [(0.15, 0.95), (1.1, h - 0.15)]:
                box(bm, 0.1, w - 0.1, -0.04, 0.04, z0, z1, MI['ebony'])
            box(bm, w - 0.14, w - 0.08, -0.07, 0.07, 1.0, 1.06, MI['brass'])
        else:
            box(bm, 0, w, -0.04, 0.04, 0, h, MI['iron'], step=0.5)
            for zz in (0.12, h / 2, h - 0.12):
                for xx in [0.06 + i * (w - 0.12) / 6 for i in range(7)]:
                    cylinder(bm, (xx, 0.04, zz), 0.012, 0.012, 5, MI['iron'], axis='Y')
                    cylinder(bm, (xx, -0.04, zz), 0.012, -0.012, 5, MI['iron'], axis='Y')
            box(bm, w - 0.16, w - 0.1, -0.12, 0.12, 0.9, 1.15, MI['brass'])
            # india-rubber seal
            box(bm, -0.02, w + 0.02, -0.02, 0.02, -0.0, 0.02, MI['rubber'])
            if port:
                cylinder(bm, (w / 2, -0.05, 1.5), 0.11, 0.1, 14, MI['brass'], axis='Y')
                cylinder(bm, (w / 2, -0.052, 1.5), 0.08, 0.104, 14, MI['lensdark'], axis='Y')
    o = obj_from(name, b, props={'ia': ia, 'door': kind, 'col': 1})
    o.location = loc
    o.rotation_euler = (0, 0, rot_z)
    return o
# rotation 0 => panel lies along +X with face normal Y. For doors in X-normal walls rotate 90deg.
door_obj('IA_door_aronnax', 0.8, DOOR_H, 'ebony', 'door', (19.45, ARON['y0'] - 0.0, 0), 0)
door_obj('IA_door_nemo', 0.8, DOOR_H, 'ebony', 'doorLocked', (16.0, NEMO['y0'], 0), 0)
door_obj('IA_door_nemosaloon', 0.8, DOOR_H, 'ebony', 'doorLocked', (S['x1'] - 0.02, 1.6, 0), math.pi / 2)
door_obj('IA_door_saloonfore', 0.8, DOOR_H, 'ebony', 'door', (S['x1'] + 0.05, -2.85, 0), math.pi / 2)
door_obj('IA_door_library', 0.8, DOOR_H, 'ebony', 'door', (S['x0'] - 0.05, -2.85, 0), math.pi / 2)
door_obj('IA_door_waist', 0.8, DOOR_H, 'iron', 'door', (L['x0'] - 0.05, -2.85, 0), math.pi / 2)
door_obj('IA_door_wardrobe', 0.8, DOOR_H, 'iron', 'door', (D['x1'] + 0.03, -2.85, 0), math.pi / 2)
door_obj('IA_door_lockInner', 0.8, DOOR_H, 'iron', 'lockInner', (-19.7, D['y1'] + 0.08, 0), 0, port=True)
door_obj('IA_door_lockOuter', 0.8, DOOR_H, 'iron', 'lockOuter', (-19.7, K['y1'] + 0.06, 0), 0)

# ---------------------------------------------------------------- the hull (exterior)
def hull_profile(x):
    # cylinder in the middle, ogive ends (spindle). radius at station x
    Lh = 35.0
    if abs(x) < 14: return 4.0
    t = (abs(x) - 14) / (Lh - 14)
    return 4.0 * math.sqrt(max(0.0, 1 - t ** 1.6)) * (1 - 0.15 * t)
def hull(bm):
    # overlapping plate rings: each ring slightly larger at its aft edge, like reptile scales
    stations = []
    x = -34.6
    while x < 34.6:
        stations.append(x); x += 1.4
    stations.append(34.6)
    seg = 28
    rows = []
    for i, xs in enumerate(stations):
        r = hull_profile(xs)
        for lip in (0, 1):
            rr = r * (1.0 + 0.012 * lip) + (0.0 if lip == 0 else 0.02)
            if i == 0 and lip == 1: continue
            if i == len(stations) - 1 and lip == 1: continue
            xx = xs + (0.0 if lip == 0 else -0.02)
            rows.append([bm.verts.new(Vector((xx, math.cos(2 * math.pi * k / seg) * rr, 1.6 + math.sin(2 * math.pi * k / seg) * rr))) for k in range(seg)])
    for k in range(len(rows) - 1):
        A, B = rows[k], rows[k + 1]
        for j in range(seg):
            f = bm.faces.new([A[j], B[j], B[(j + 1) % seg], A[(j + 1) % seg]]); f.material_index = MI['hull']
    # nose and tail caps
    for (row, tip, flip) in [(rows[0], Vector((-35.4, 0, 1.6)), True), (rows[-1], Vector((35.2, 0, 1.6)), False)]:
        tv = bm.verts.new(tip)
        for j in range(seg):
            q = [row[j], row[(j + 1) % seg], tv]
            f = bm.faces.new(q[::-1] if not flip else q); f.material_index = MI['hull']
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
hullo = obj_from('hull', hull, c='EXT', props={'col': 1})
# cut window and door openings with booleans
def cutter(name, x0, x1, y0, y1, z0, z1):
    b2 = bmesh.new(); box(b2, x0, x1, y0, y1, z0, z1)
    return new_obj(name, b2, [], 'EXT')
cuts = [cutter('cut_wp', WIN['xc'] - WIN['w'] / 2, WIN['xc'] + WIN['w'] / 2, 2.0, 5.0, WIN['z0'], WIN['z1']),
        cutter('cut_ws', WIN['xc'] - WIN['w'] / 2, WIN['xc'] + WIN['w'] / 2, -5.0, -2.0, WIN['z0'], WIN['z1']),
        cutter('cut_door', -19.7, -18.9, 2.0, 5.0, 0.0, DOOR_H)]
bpy.context.view_layer.objects.active = hullo
for c in cuts:
    m_ = hullo.modifiers.new('b', 'BOOLEAN'); m_.object = c; m_.operation = 'DIFFERENCE'; m_.solver = 'EXACT'
    bpy.ops.object.modifier_apply(modifier=m_.name)
    bpy.data.objects.remove(c)

def hull_details(bm):
    # platform (deck) along the top, longboat bulge, pilot cage and lantern cage with lenticular glasses
    box(bm, -9.0, 9.0, -1.0, 1.0, 5.55, 5.7, MI['iron'], step=1.0)
    lathe(bm, [(0.0, 5.55), (1.0, 5.55), (1.15, 5.75), (1.0, 6.05), (0.0, 6.15)], 14, (0, 0, 0), MI['hull'])
    for (xc, nm) in [(11.0, 'lantern'), (-11.5, 'pilot')]:
        lathe(bm, [(1.0, 5.25), (1.0, 5.9), (0.75, 6.35), (0.0, 6.45)], 12, (xc, 0, 0), MI['hull'])
    # spur (ram) at the bow
    lathe(bm, [(0.35, 0.0), (0.0, 3.4)], 10, (34.8, 0, 1.6), MI['iron'], axis='X')
    # inclined planes (fins) near the stern and rudder
    for s in (-1, 1):
        vs = [Vector((-24, s * 3.4, 1.6)), Vector((-28.5, s * 6.0, 1.6)), Vector((-30.5, s * 6.0, 1.6)), Vector((-30.0, s * 2.6, 1.6))]
        f = bm.faces.new([bm.verts.new(v) for v in (vs if s > 0 else vs[::-1])]); f.material_index = MI['iron']
        vs2 = [v + Vector((0, 0, -0.06)) for v in vs]
        f = bm.faces.new([bm.verts.new(v) for v in (vs2[::-1] if s > 0 else vs2)]); f.material_index = MI['iron']
    box(bm, -35.5, -33.4, -0.06, 0.06, -1.9, 5.0, MI['iron'])
    # screw: hub and four blades, 19 ft across
    cylinder(bm, (-34.9, 0, 1.6), 0.45, -0.9, 10, MI['brass'], axis='X')
    # iron rungs on the hull below the side door, to climb back in
    for k in range(5):
        z = -1.9 + k * 0.42
        r = hull_profile(-19.3)
        yy = math.sqrt(max(0.1, r * r - (z - 1.6) ** 2)) + 0.12
        cylinder(bm, (-19.65, yy, z), 0.022, 0.7, 6, MI['iron'], axis='X')
obj_from('hull_details', hull_details, c='EXT', props={'col': 1}, smooth=50)
def screw(bm):
    for k in range(4):
        a = k * math.pi / 2
        vs = []
        for (r, w) in [(0.4, 0.35), (1.6, 0.9), (2.7, 0.75), (2.95, 0.2)]:
            vs.append((r, w))
        row0, row1 = [], []
        for (r, w) in vs:
            twist = 0.6
            p0 = Vector((-w / 2 * math.sin(twist), math.cos(a) * r - math.sin(a) * (-w / 2) * math.cos(twist), math.sin(a) * r + math.cos(a) * (-w / 2) * math.cos(twist)))
            p1 = Vector((w / 2 * math.sin(twist), math.cos(a) * r - math.sin(a) * (w / 2) * math.cos(twist), math.sin(a) * r + math.cos(a) * (w / 2) * math.cos(twist)))
            row0.append(bm.verts.new(p0)); row1.append(bm.verts.new(p1))
        for i in range(len(vs) - 1):
            f = bm.faces.new([row0[i], row0[i + 1], row1[i + 1], row1[i]]); f.material_index = MI['brass']
o = obj_from('screw', screw, c='EXT', props={'spin': 1})
o.location = (-35.1, 0, 1.6)
def lenses(bm):
    for (xc, nm) in [(11.0, 'lantern'), (-11.5, 'pilot')]:
        for k in range(8):
            a = 2 * math.pi * k / 8
            cylinder(bm, (xc + math.cos(a) * 0.98, math.sin(a) * 0.98, 5.6), 0.16, 0.0, 10, MI['lens' if nm == 'lantern' else 'lensdark'], axis='X')
    # crystal of the saloon windows seen from outside, and the side door frame
    for s in (1, -1):
        y = 3.74 * s
        grid_quad(bm, Vector((WIN['xc'] + WIN['w'] / 2, y, WIN['z0'])) if s > 0 else Vector((WIN['xc'] - WIN['w'] / 2, y, WIN['z0'])),
                  Vector((-WIN['w'], 0, 0)) if s > 0 else Vector((WIN['w'], 0, 0)), Vector((0, 0, WIN['z1'] - WIN['z0'])), 1, 1, MI['crystal'])
o = obj_from('lenses', lenses, c='EXT')
for (xc, nm) in [(11.0, 'lantern')]:
    o['lantern'] = json.dumps([xc, 0, 5.6])
# the sliding iron panels outside the crystal (separate objects so they can slide along X)
def panel_obj(name, s):
    def b(bm):
        w, z0, z1 = WIN['w'] + 0.3, WIN['z0'] - 0.15, WIN['z1'] + 0.15
        box(bm, -w / 2, w / 2, -0.04, 0.04, z0, z1, MI['hull'], step=0.6)
        for xx in [-w / 2 + 0.1 + i * (w - 0.2) / 8 for i in range(9)]:
            for zz in (z0 + 0.08, z1 - 0.08):
                cylinder(bm, (xx, 0.045 * s, zz), 0.02, 0.015 * s, 5, MI['iron'], axis='Y')
    o = obj_from(name, b, c='EXT', props={'ia': 'panel', 'side': s})
    o.location = (WIN['xc'], 3.84 * s, 0)
    return o
panel_obj('IA_panel_P', 1); panel_obj('IA_panel_S', -1)

# ---------------------------------------------------------------- UVs, AO, export
for o in coll('EXT').objects: o['zone'] = 'ext'
for o in list(coll('INT').objects) + list(coll('EXT').objects):
    if o.type == 'MESH' and len(o.data.polygons):
        world_uv(o, 1.0)
bake_targets = [o for o in list(coll('INT').objects) + list(coll('EXT').objects) if o.type == 'MESH' and not o.name.startswith('NEEDLE') and len(o.data.vertices) > 0]
bake_ao(bake_targets, distance=1.0, samples=int(os.environ.get('AO_SAMPLES', '24')))
export(OUT)
print('EXPORTED', OUT, len(bake_targets))
