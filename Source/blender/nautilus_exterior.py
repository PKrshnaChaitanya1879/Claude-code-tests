"""The Nautilus, outside: built from the book's figures (Design Bible §1) and the 1871 plates.

    "an elongated cylinder with conical ends ... very like a cigar in shape" (I.XII)
    length 70 m, maximum breadth 8 m; plates "slightly overlaying each other ... like the shell
    which clothes the bodies of our large terrestrial reptiles" (I.XIII); the platform; "fore and
    aft rose two cages of medium height with inclined sides, and partly closed by thick lenticular
    glasses; one destined for the steersman ... the other containing a brilliant lantern"; the boat
    "half buried in the hull"; the spur; a four-bladed screw 6 m across; rudder on the stern-post;
    two inclined planes "fastened to its sides, opposite the centre of flotation"; the saloon's two
    crystal windows behind iron panels; the flooding cell's door "cut in the side".

Low-poly in the Iron Lung / ULTRAKILL sense: faceted, every plate edge a real step that catches light.
Axes here: +X toward the bow, +Y to port, +Z up. Deck of the main interior at Z = 0, hull axis at Z = 2.
The Unity bootstrap orients the import using the empties BOW_TIP and PORT_DOOR, so axis conventions
in the FBX exporter cannot turn the boat around.

Run: python3 nautilus_exterior.py [out_dir]   →  Nautilus_Exterior.fbx (+ LOD1, LOD2, _col) and previews.
"""
import math, os, sys
import bpy, bmesh
from mathutils import Vector, Matrix

OUT = sys.argv[-1] if len(sys.argv) > 1 and not sys.argv[-1].endswith('.py') else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
os.makedirs(OUT, exist_ok=True)

L = 70.0          # length
R = 4.0           # radius (beam 8 m)
AXIS_Z = 2.0      # hull axis above the main deck
HALF = L / 2
SEG = 24          # around the hull: faceted, not round

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for c in list(bpy.data.collections): bpy.data.collections.remove(c)

def mat(name, color, metal=0.0, rough=0.6, emit=None, emit_strength=0.0, alpha=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Metallic'].default_value = metal
    b.inputs['Roughness'].default_value = rough
    if emit:
        b.inputs['Emission Color'].default_value = (*emit, 1)
        b.inputs['Emission Strength'].default_value = emit_strength
    if alpha < 1:
        b.inputs['Alpha'].default_value = alpha
        m.blend_method = 'BLEND' if hasattr(m, 'blend_method') else None
    return m

MATS = {}
def M(name): return MATS[name]

# ---------------------------------------------------------------- profile
def radius_at(x):
    """Cylinder amidships, long conical-ogive ends (the plates in ill-011 show a long taper)."""
    a = abs(x)
    flat = 17.0
    if a <= flat: return R
    t = min(1.0, (a - flat) / (HALF - flat))
    # ogive: tangent to the cylinder, pointed at the end; the stern a little fuller than the bow
    k = 1.0 if x > 0 else 0.92
    return max(0.0, R * math.sqrt(max(0.0, 1 - t ** (1.9 * k))) * (1 - 0.08 * t))

# ---------------------------------------------------------------- hull with overlapping plates
def build_hull():
    """Each ring of plates is a short frustum whose aft edge stands proud of the next ring by a
    few centimetres, so the hull reads as overlapping scales. Longitudinal seams are staggered."""
    bm = bmesh.new()
    pitch = 1.75                      # plate length
    lip = 0.055                       # how far a plate's aft edge stands over the next
    xs = []
    x = -HALF + 0.6
    while x < HALF - 0.6:
        xs.append(x); x += pitch
    xs.append(HALF - 0.6)
    rings = []
    for i in range(len(xs) - 1):
        x0, x1 = xs[i], xs[i + 1]
        r0, r1 = radius_at(x0), radius_at(x1)
        # plates overlap toward the stern (water slides off): the aft edge (x0) is proud
        stagger = (i % 2) * math.pi / SEG
        ring0, ring1 = [], []
        for k in range(SEG):
            a = 2 * math.pi * k / SEG + stagger
            ring0.append(bm.verts.new((x0, math.cos(a) * (r0 + lip), AXIS_Z + math.sin(a) * (r0 + lip))))
            ring1.append(bm.verts.new((x1, math.cos(a) * r1, AXIS_Z + math.sin(a) * r1)))
        for k in range(SEG):
            f = bm.faces.new([ring0[k], ring0[(k + 1) % SEG], ring1[(k + 1) % SEG], ring1[k]])
            f.material_index = 0
        # the step face where this ring's proud aft edge meets the previous ring's fore edge
        rings.append((ring0, ring1))
    for i in range(len(rings) - 1):
        a1 = rings[i][1]; b0 = rings[i + 1][0]
        # previous ring's fore edge (radius r) to next ring's proud aft edge: short skirt
        # stagger means vertices don't line up; bridge with a fan per segment
        for k in range(SEG):
            p, q = a1[k], a1[(k + 1) % SEG]
            # nearest proud vertices
            u, v = b0[k], b0[(k + 1) % SEG]
            f = bm.faces.new([p, q, v, u]) if True else None
            f.material_index = 1
    # tips
    for ring, tipx in ((rings[0][0], -HALF), (rings[-1][1], HALF)):
        tv = bm.verts.new((tipx, 0, AXIS_Z))
        for k in range(SEG):
            f = bm.faces.new([ring[k], ring[(k + 1) % SEG], tv]); f.material_index = 0
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new('Hull'); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new('Hull', me)
    me.materials.append(M('hull')); me.materials.append(M('hull_seam'))
    return o

def add_obj(name, bm, mats):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    for m in mats: me.materials.append(M(m))
    bpy.context.collection.objects.link(o)
    return o

def box(bm, c, s, mi=0, rot=None):
    r = bmesh.ops.create_cube(bm, size=1.0)
    vs = r['verts']
    bmesh.ops.scale(bm, vec=s, verts=vs)
    if rot is not None: bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=rot, verts=vs)
    bmesh.ops.translate(bm, vec=c, verts=vs)
    for f in {f for v in vs for f in v.link_faces}: f.material_index = mi
    return vs

def frustum(bm, c, base, top, h, mi=0, lens_mi=None, lens_r=0.0):
    """Cage with inclined sides: rectangular base (bx, by), smaller top (tx, ty)."""
    bx, by = base; tx, ty = top
    z0, z1 = c[2], c[2] + h
    vb = [bm.verts.new((c[0] + sx * bx / 2, c[1] + sy * by / 2, z0)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    vt = [bm.verts.new((c[0] + sx * tx / 2, c[1] + sy * ty / 2, z1)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    for i in range(4):
        f = bm.faces.new([vb[i], vb[(i + 1) % 4], vt[(i + 1) % 4], vt[i]]); f.material_index = mi
    # low dome on top (im027: the cage reads rounded, its glasses take most of each face)
    apex = bm.verts.new((c[0], c[1], z1 + 0.22))
    for i in range(4):
        f = bm.faces.new([vt[i], vt[(i + 1) % 4], apex]); f.material_index = mi
    f = bm.faces.new(vb[::-1]); f.material_index = mi
    # lenticular glasses: a shallow convex disc centred on each inclined face
    if lens_mi is not None:
        for i in range(4):
            a, b, cc, d = vb[i].co, vb[(i + 1) % 4].co, vt[(i + 1) % 4].co, vt[i].co
            ctr = (a + b + cc + d) / 4
            n = (b - a).cross(d - a).normalized()
            u = (b - a).normalized(); v = n.cross(u).normalized()
            rr = lens_r * (1.0 if (b - a).length > 1.2 else 0.75)
            ring = []
            for k in range(12):
                ang = 2 * math.pi * k / 12
                ring.append(bm.verts.new(ctr + n * 0.02 + (u * math.cos(ang) + v * math.sin(ang)) * rr))
            mid = []
            for k in range(12):
                ang = 2 * math.pi * k / 12
                mid.append(bm.verts.new(ctr + n * 0.09 + (u * math.cos(ang) + v * math.sin(ang)) * rr * 0.6))
            tip = bm.verts.new(ctr + n * 0.12)
            for k in range(12):
                f = bm.faces.new([ring[k], ring[(k + 1) % 12], mid[(k + 1) % 12], mid[k]]); f.material_index = lens_mi
                f = bm.faces.new([mid[k], mid[(k + 1) % 12], tip]); f.material_index = lens_mi
            # iron bezel
            bez = [bm.verts.new(ctr + n * 0.025 + (u * math.cos(2 * math.pi * k / 12) + v * math.sin(2 * math.pi * k / 12)) * (rr + 0.06)) for k in range(12)]
            for k in range(12):
                f = bm.faces.new([bez[k], bez[(k + 1) % 12], ring[(k + 1) % 12], ring[k]]); f.material_index = mi

def hull_top(x):
    return AXIS_Z + radius_at(x)

def build_details():
    bm = bmesh.new()
    # ---- the platform: a flat iron deck along the top, "only three feet out of water" when afloat
    px0, px1 = -9.5, 9.5
    deck_z = AXIS_Z + R + 0.08                       # top of the platform, just proud of the crown
    w = 2.4
    box(bm, (0, 0, deck_z - 0.2), (px1 - px0, w, 0.4), 2)
    for i in range(int((px1 - px0) / 1.2)):          # deck plates with visible seams
        x = px0 + 0.6 + i * 1.2
        box(bm, (x, 0, deck_z + 0.005), (1.15, w - 0.08, 0.01), 2)
    for s in (-1, 1):                                # chamfered skirts down to the hull
        box(bm, (0, s * (w / 2 + 0.18), deck_z - 0.34), (px1 - px0, 0.5, 0.14), 0, Matrix.Rotation(-s * 0.45, 3, 'X'))
    for s in (-1, 1):                                # low rail on stanchions (im027)
        for i in range(17):
            x = px0 + 0.4 + i * (px1 - px0 - 0.8) / 16
            box(bm, (x, s * (w / 2 - 0.05), deck_z + 0.4), (0.04, 0.04, 0.8), 3)
        box(bm, (0, s * (w / 2 - 0.05), deck_z + 0.8), (px1 - px0 - 0.8, 0.035, 0.035), 3)
    bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.45, radius2=0.42, depth=0.12,
                          matrix=Matrix.Translation((-1.0, 0.6, deck_z + 0.06)))   # hatch of the central staircase
    bvs = bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=1.0)['verts']   # the boat, half buried
    bmesh.ops.scale(bm, vec=(3.2, 0.85, 0.5), verts=bvs)
    bmesh.ops.translate(bm, vec=(2.6, -0.25, deck_z), verts=bvs)
    for f in {f for v in bvs for f in v.link_faces}: f.material_index = 0
    # ---- the two cages: pilot fore, lantern aft ("behind the steersman's cage ... a powerful reflector")
    frustum(bm, (7.6, 0, deck_z), (2.0, 1.7), (1.3, 1.1), 1.15, 0, 4, 0.46)
    frustum(bm, (-7.4, 0, deck_z), (1.9, 1.6), (1.2, 1.0), 1.05, 0, 5, 0.44)
    # ---- the spur: a long steel beak continuing the bow (Motala, I.XII)
    bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=0.42, radius2=0.0, depth=4.2,
                          matrix=Matrix.Translation((HALF + 1.6, 0, AXIS_Z)) @ Matrix.Rotation(math.pi / 2, 4, 'Y'))
    # ---- stern: the screw turns just behind the hull's tip; aft of it the stern-post carries the rudder,
    #      tied to the hull by a keel bar under the screw (I.XII: "an ordinary rudder fixed on the back of the stern-post")
    bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.55, radius2=0.3, depth=1.6,
                          matrix=Matrix.Translation((-HALF - 0.5, 0, AXIS_Z)) @ Matrix.Rotation(math.pi / 2, 4, 'Y'))   # shaft boss
    box(bm, (-HALF - 1.0, 0, AXIS_Z - 3.25), (4.6, 0.22, 0.3), 3)          # keel bar running aft under the screw
    box(bm, (-HALF - 3.2, 0, AXIS_Z - 0.2), (0.25, 0.25, 6.4), 3)          # stern-post
    box(bm, (-HALF - 4.0, 0, AXIS_Z - 0.1), (1.5, 0.12, 5.2), 3)           # rudder blade
    # ---- inclined planes amidships, "opposite the centre of flotation", worked by levers inside
    for s in (-1, 1):
        y_root = s * (R - 0.15)
        vs = [Vector((1.2, y_root, AXIS_Z - 0.2)), Vector((0.4, s * (R + 2.2), AXIS_Z - 0.2)),
              Vector((-1.6, s * (R + 2.2), AXIS_Z - 0.2)), Vector((-2.4, y_root, AXIS_Z - 0.2))]
        top = [bm.verts.new(v + Vector((0, 0, 0.08))) for v in vs]
        bot = [bm.verts.new(v - Vector((0, 0, 0.08))) for v in vs]
        faces = [top if s > 0 else top[::-1], (bot[::-1] if s > 0 else bot)]
        for q in faces:
            f = bm.faces.new(q); f.material_index = 3
        for i in range(4):
            q = [top[i], bot[i], bot[(i + 1) % 4], top[(i + 1) % 4]]
            f = bm.faces.new(q if s > 0 else q[::-1]); f.material_index = 3
    # ---- the saloon windows: two oblong crystal plates banded in copper, behind iron panels
    for s in (-1, 1):
        xc, wdt, z0, z1 = 15.0, 4.2, 1.0, 3.0
        y = s * (R + 0.02)
        box(bm, (xc, y, (z0 + z1) / 2), (wdt, 0.04, z1 - z0), 6)
        for k in range(3):
            box(bm, (xc - wdt / 2 + wdt * (k + 1) / 4, y + s * 0.03, (z0 + z1) / 2), (0.06, 0.03, z1 - z0), 7)
        box(bm, (xc, y + s * 0.03, z0), (wdt + 0.12, 0.05, 0.08), 7)
        box(bm, (xc, y + s * 0.03, z1), (wdt + 0.12, 0.05, 0.08), 7)
    # ---- the flooding cell's door, port side, with iron rungs below
    dx = -16.25
    r_d = R
    box(bm, (dx, R + 0.03, 1.0), (0.95, 0.05, 2.05), 3)
    for k in range(5):
        z = 0.0 - 0.45 * k
        yy = math.sqrt(max(0.1, R * R - (z - AXIS_Z) ** 2)) + 0.1
        box(bm, (dx, yy, z), (0.7, 0.04, 0.04), 3)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return add_obj('Details', bm, ['hull', 'hull_seam', 'deck', 'iron', 'lens_dark', 'lens_lamp', 'crystal', 'copper'])

def build_screw():
    """Four blades, 6 m across (Verne: 19 ft), pitch 7.5 m: blades twisted along the radius."""
    bm = bmesh.new()
    hub = bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.5, radius2=0.5, depth=0.9,
                                matrix=Matrix.Rotation(math.pi / 2, 4, 'Y'))
    pitch = 7.5
    for k in range(4):
        a0 = k * math.pi / 2
        rows = []
        for r, chord in ((0.45, 0.7), (1.2, 1.25), (2.2, 1.2), (2.85, 0.75), (3.0, 0.25)):
            twist = math.atan2(pitch, 2 * math.pi * r)
            row = []
            for side in (-1, 1):
                c = side * chord / 2
                # blade element: along the circumference (tangent) and along the axis by the helix angle
                ang = a0 + (c * math.cos(twist)) / r
                xax = c * math.sin(twist)
                row.append(bm.verts.new((xax, math.cos(ang) * r, math.sin(ang) * r)))
            rows.append(row)
        for i in range(len(rows) - 1):
            q = [rows[i][0], rows[i][1], rows[i + 1][1], rows[i + 1][0]]
            bm.faces.new(q)
    o = add_obj('Screw', bm, ['bronze'])
    sol = o.modifiers.new('thickness', 'SOLIDIFY'); sol.thickness = 0.09; sol.offset = 0
    o.location = (-HALF - 1.9, 0, AXIS_Z)
    return o

def markers():
    for name, loc in (('BOW_TIP', (HALF + 3.7, 0, AXIS_Z)), ('STERN', (-HALF - 4.8, 0, AXIS_Z)),
                      ('PORT_DOOR', (-16.25, R + 0.1, 1.0)), ('LANTERN', (-7.4, 0, AXIS_Z + R + 0.5)),
                      ('PILOT', (7.6, 0, AXIS_Z + R + 0.5)), ('SALOON_WINDOW_PORT', (15.0, R, 2.0)),
                      ('SALOON_WINDOW_STARBOARD', (15.0, -R, 2.0))):
        e = bpy.data.objects.new(name, None); e.location = loc; e.empty_display_size = 0.5
        bpy.context.collection.objects.link(e)

def build_collision():
    """Simple convex-ish collision: 14 sided hull, no plates; the deck as a box."""
    bm = bmesh.new()
    seg = 14
    xs = [-HALF] + [x for x in [i * 2.5 - HALF + 2.5 for i in range(27)]] + [HALF]
    rings = []
    for x in xs:
        r = max(0.05, radius_at(x))
        rings.append([bm.verts.new((x, math.cos(2 * math.pi * k / seg) * r, AXIS_Z + math.sin(2 * math.pi * k / seg) * r)) for k in range(seg)])
    for i in range(len(rings) - 1):
        for k in range(seg):
            bm.faces.new([rings[i][k], rings[i][(k + 1) % seg], rings[i + 1][(k + 1) % seg], rings[i + 1][k]])
    bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = add_obj('Nautilus_Exterior_col', bm, [])
    return o

def setup_materials():
    MATS['hull'] = mat('M_HullPlate', (0.13, 0.15, 0.15), metal=0.55, rough=0.5)
    MATS['hull_seam'] = mat('M_HullSeam', (0.05, 0.055, 0.06), metal=0.5, rough=0.65)
    MATS['deck'] = mat('M_Deck', (0.20, 0.20, 0.19), metal=0.5, rough=0.6)
    MATS['iron'] = mat('M_Iron', (0.10, 0.10, 0.10), metal=0.7, rough=0.45)
    MATS['lens_dark'] = mat('M_LensDark', (0.05, 0.12, 0.14), metal=0.0, rough=0.05)
    MATS['lens_lamp'] = mat('M_LensLamp', (0.9, 0.95, 1.0), metal=0.0, rough=0.05, emit=(0.95, 0.97, 1.0), emit_strength=25.0)
    MATS['crystal'] = mat('M_Crystal', (0.05, 0.1, 0.12), metal=0.0, rough=0.02)
    MATS['copper'] = mat('M_Copper', (0.72, 0.38, 0.22), metal=1.0, rough=0.35)
    MATS['bronze'] = mat('M_Bronze', (0.55, 0.42, 0.22), metal=1.0, rough=0.4)

def tri_count(objs):
    n = 0
    for o in objs:
        if o.type != 'MESH': continue
        me = o.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
        n += sum(len(p.vertices) - 2 for p in me.polygons)
    return n

def export_fbx(path, objs):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS',
                             axis_forward='-Z', axis_up='Y', bake_space_transform=True, object_types={'MESH', 'EMPTY'},
                             use_mesh_modifiers=True, mesh_smooth_type='FACE', add_leaf_bones=False, path_mode='STRIP')

def main():
    reset()
    setup_materials()
    hull = build_hull(); bpy.context.collection.objects.link(hull)
    det = build_details()
    scr = build_screw()
    markers()
    col = build_collision()
    lod0 = [hull, det, scr]
    # plates read by their stepped edges; the curvature between steps is smoothed (30° split),
    # so the hull is low-poly in outline but not a checkerboard of facets
    for o in lod0:
        o.data.polygons.foreach_set('use_smooth', [True] * len(o.data.polygons))
        bpy.context.view_layer.objects.active = o
        o.select_set(True)
        try:
            bpy.ops.object.shade_smooth_by_angle(angle=math.radians(30))
        except Exception:
            o.data.set_sharp_from_angle(angle=math.radians(30))
        o.select_set(False)
    print('LOD0 triangles:', tri_count(lod0))
    empties = [o for o in bpy.data.objects if o.type == 'EMPTY']
    export_fbx(os.path.join(OUT, 'Nautilus_Exterior.fbx'), lod0 + empties)
    export_fbx(os.path.join(OUT, 'Nautilus_Exterior_col.fbx'), [col])
    # LOD1 / LOD2 by decimation of copies
    for lvl, ratio in ((1, 0.5), (2, 0.22)):
        copies = []
        for o in lod0:
            c = o.copy(); c.data = o.data.copy(); c.name = o.name + f'_LOD{lvl}'
            bpy.context.collection.objects.link(c)
            m = c.modifiers.new('dec', 'DECIMATE'); m.ratio = ratio; m.use_collapse_triangulate = True
            copies.append(c)
        print(f'LOD{lvl} triangles:', tri_count(copies))
        export_fbx(os.path.join(OUT, f'Nautilus_Exterior_LOD{lvl}.fbx'), copies)
        for c in copies: c.hide_render = True; c.hide_set(True)
    col.hide_render = True
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'nautilus_exterior.blend'))

if __name__ == '__main__':
    main()
