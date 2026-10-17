# Blender helper library for scripted low-poly modelling, AO baking and glTF export.
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, Euler

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.context.scene
    if scn.world is None:
        scn.world = bpy.data.worlds.new('World')
    return scn

_colls = {}
def coll(name):
    if name in _colls: return _colls[name]
    c = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(c)
    _colls[name] = c
    return c

_mats = {}
def mat(name, color=(0.6, 0.6, 0.6), metal=0.0, rough=0.8, emit=None):
    if name in _mats: return _mats[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get('Principled BSDF')
    if b:
        b.inputs['Base Color'].default_value = (*color, 1)
        b.inputs['Metallic'].default_value = metal
        b.inputs['Roughness'].default_value = rough
        if emit:
            b.inputs['Emission Color'].default_value = (*emit, 1)
            b.inputs['Emission Strength'].default_value = 1.0
    _mats[name] = m
    return m

def new_obj(name, bm, mats, c='INT', props=None, smooth_angle=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    for m in mats: me.materials.append(m)
    o = bpy.data.objects.new(name, me)
    coll(c).objects.link(o)
    if smooth_angle is not None:
        me.shade_smooth()
        try: me.set_sharp_from_angle(angle=math.radians(smooth_angle))
        except Exception: pass
    if props:
        for k, v in props.items(): o[k] = v
    return o

def grid_quad(bm, p0, du, dv, nu, nv, mi=0, flip=False):
    """Add a subdivided quad: origin p0, edge vectors du, dv."""
    verts = [[bm.verts.new(p0 + du * (i / nu) + dv * (j / nv)) for i in range(nu + 1)] for j in range(nv + 1)]
    faces = []
    for j in range(nv):
        for i in range(nu):
            q = [verts[j][i], verts[j][i + 1], verts[j + 1][i + 1], verts[j + 1][i]]
            if flip: q = q[::-1]
            f = bm.faces.new(q); f.material_index = mi; faces.append(f)
    return faces

def _n(length, step):
    return max(1, int(math.ceil(length / step)))

def box(bm, x0, x1, y0, y1, z0, z1, mi=0, step=None, inside=False, skip=()):
    """Axis aligned box. inside=True makes normals point inwards (room shell). skip: faces to omit ('x0','x1','y0','y1','z0','z1')."""
    p = Vector
    sx, sy, sz = x1 - x0, y1 - y0, z1 - z0
    st = step or 1e9
    faces = []
    defs = {
        'z0': (p((x0, y0, z0)), p((0, sy, 0)), p((sx, 0, 0))),
        'z1': (p((x0, y0, z1)), p((sx, 0, 0)), p((0, sy, 0))),
        'y0': (p((x0, y0, z0)), p((sx, 0, 0)), p((0, 0, sz))),
        'y1': (p((x1, y1, z0)), p((-sx, 0, 0)), p((0, 0, sz))),
        'x0': (p((x0, y1, z0)), p((0, -sy, 0)), p((0, 0, sz))),
        'x1': (p((x1, y0, z0)), p((0, sy, 0)), p((0, 0, sz))),
    }
    for k, (o, du, dv) in defs.items():
        if k in skip: continue
        faces += grid_quad(bm, o, du, dv, _n(du.length, st), _n(dv.length, st), mi, flip=inside)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    return faces

def cylinder(bm, center, r, h, seg=12, mi=0, axis='Z', r2=None, cap=True, rings=1):
    r2 = r if r2 is None else r2
    rot = {'Z': Matrix.Identity(3), 'X': Matrix.Rotation(math.radians(90), 3, 'Y'), 'Y': Matrix.Rotation(math.radians(-90), 3, 'X')}[axis]
    c = Vector(center)
    rings_v = []
    for k in range(rings + 1):
        t = k / rings
        rr = r + (r2 - r) * t
        ring = [bm.verts.new(c + rot @ Vector((math.cos(a) * rr, math.sin(a) * rr, h * t))) for a in [2 * math.pi * i / seg for i in range(seg)]]
        rings_v.append(ring)
    faces = []
    for k in range(rings):
        A, B = rings_v[k], rings_v[k + 1]
        for i in range(seg):
            f = bm.faces.new([A[i], A[(i + 1) % seg], B[(i + 1) % seg], B[i]]); f.material_index = mi; faces.append(f)
    if cap:
        f = bm.faces.new(rings_v[0][::-1]); f.material_index = mi; faces.append(f)
        f = bm.faces.new(rings_v[-1]); f.material_index = mi; faces.append(f)
    return faces

def lathe(bm, profile, seg=16, center=(0, 0, 0), mi=0, axis='Z', cap0=False, cap1=False, arc=(0, 2 * math.pi)):
    """profile: list of (radius, height). Revolve around axis."""
    rot = {'Z': Matrix.Identity(3), 'X': Matrix.Rotation(math.radians(90), 3, 'Y'), 'Y': Matrix.Rotation(math.radians(-90), 3, 'X')}[axis]
    c = Vector(center)
    full = abs(arc[1] - arc[0] - 2 * math.pi) < 1e-6
    n = seg if full else seg + 1
    rows = []
    for (r, h) in profile:
        row = []
        for i in range(n):
            a = arc[0] + (arc[1] - arc[0]) * i / seg
            row.append(bm.verts.new(c + rot @ Vector((math.cos(a) * r, math.sin(a) * r, h))))
        rows.append(row)
    faces = []
    for k in range(len(rows) - 1):
        A, B = rows[k], rows[k + 1]
        for i in range(seg):
            i2 = (i + 1) % n
            q = [A[i], A[i2], B[i2], B[i]]
            if len(set(q)) < 3: continue
            try:
                f = bm.faces.new(q); f.material_index = mi; faces.append(f)
            except ValueError: pass
    if cap0 and full and profile[0][0] > 1e-5:
        f = bm.faces.new(rows[0][::-1]); f.material_index = mi
    if cap1 and full and profile[-1][0] > 1e-5:
        f = bm.faces.new(rows[-1]); f.material_index = mi
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    return faces

def transform(bm, verts, M):
    bmesh.ops.transform(bm, matrix=M, verts=verts)

def bevel_all(bm, off=0.01, seg=1):
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=off, segments=seg, affect='EDGES', profile=0.5, clamp_overlap=True)

def sub_bm(fn):
    """Build geometry in a temp bmesh and return it (for merging into another)."""
    b = bmesh.new(); fn(b); return b

def merge_into(dst, src, M=Matrix.Identity(4), mi_map=None):
    """Copy src bmesh into dst with transform M."""
    vm = {}
    for v in src.verts:
        vm[v] = dst.verts.new(M @ v.co)
    for f in src.faces:
        try:
            nf = dst.faces.new([vm[v] for v in f.verts])
            nf.material_index = mi_map[f.material_index] if mi_map else f.material_index
        except ValueError:
            pass
    src.free()

def cube_uv(o, size=1.5):
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.cube_project(cube_size=size, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode='OBJECT')

def world_uv(o, scale=1.0):
    """Planar-by-normal world-space UVs (fast, no operators)."""
    me = o.data
    if not me.uv_layers: me.uv_layers.new(name='UVMap')
    uv = me.uv_layers.active.data
    mw = o.matrix_world
    for poly in me.polygons:
        n = poly.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        for li in poly.loop_indices:
            co = mw @ me.vertices[me.loops[li].vertex_index].co
            if ax == 0: u, v = co.y, co.z
            elif ax == 1: u, v = co.x, co.z
            else: u, v = co.x, co.y
            uv[li].uv = (u / scale, v / scale)

def bake_ao(objs, distance=1.2, samples=24):
    scn = bpy.context.scene
    scn.render.engine = 'CYCLES'
    scn.cycles.device = 'CPU'
    scn.cycles.samples = samples
    scn.world.light_settings.distance = distance
    scn.render.bake.target = 'VERTEX_COLORS'
    for o in objs:
        me = o.data
        if 'AO' not in me.color_attributes:
            me.color_attributes.new('AO', 'BYTE_COLOR', 'POINT')
        me.color_attributes.active_color = me.color_attributes['AO']
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.bake(type='AO')

def export(path, collections=None):
    bpy.ops.object.select_all(action='DESELECT')
    if collections:
        for cn in collections:
            for o in coll(cn).objects: o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=bool(collections),
                              export_vertex_color='ACTIVE', export_all_vertex_colors=False,
                              export_extras=True, export_yup=True, export_apply=True,
                              export_materials='EXPORT', export_image_format='NONE')
