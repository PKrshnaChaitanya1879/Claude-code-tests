"""Giant kelp preview: a patch of forest at 12 m in clear sun (I.XVI), and one plant under plain light.
Run: python3 preview_kelp.py <crespo_flora.blend> <out.png> <forest|clay>"""
import sys, math, random, bpy
from mathutils import Vector
args = [a for a in sys.argv if a != "--novol"]; blend, out, mode = args[-3], args[-2], args[-1]
bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene
for o in sc.objects: o.hide_render = True
src = {o.name: o for o in sc.objects if o.type == 'MESH'}
sc.render.engine = 'BLENDER_EEVEE'; sc.render.resolution_x, sc.render.resolution_y = 900, 640
for k, v in (('taa_render_samples', 32), ('volumetric_tile_size', '4'), ('volumetric_samples', 64), ('volumetric_end', 120.0), ('use_volumetric_shadows', True), ('use_shadows', True), ('shadow_ray_count', 2)):
    try: setattr(sc.eevee, k, v)
    except Exception: pass
sc.view_settings.view_transform = 'AgX'
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; nt = w.node_tree
R = random.Random(3)
def put(n, loc, rz=0, s=1.0):
    o = src[n].copy(); o.data = src[n].data; sc.collection.objects.link(o); o.hide_render = False
    o.location = loc; o.rotation_euler = (0, 0, math.radians(rz)); o.scale = (s, s, s); return o
cam = bpy.data.cameras.new('c'); co = bpy.data.objects.new('c', cam); sc.collection.objects.link(co); sc.camera = co
if mode == 'clay':
    put('laminaria_a', (0, 0, 0))
    nt.nodes['Background'].inputs['Color'].default_value = (0.3, 0.32, 0.34, 1)
    S = bpy.data.lights.new('sun', 'SUN'); S.energy = 3.0; so = bpy.data.objects.new('sun', S); so.rotation_euler = (math.radians(40), 0, math.radians(30)); sc.collection.objects.link(so)
    cam.lens = 35; co.location = (9, -12, 6); tgt = Vector((0, 0, 5.5))
else:
    nt.nodes['Background'].inputs['Color'].default_value = (0.05, 0.16, 0.2, 1)
    vol = nt.nodes.new('ShaderNodeVolumePrincipled'); vol.inputs['Density'].default_value = 0.012
    vol.inputs['Color'].default_value = (0.35, 0.75, 0.8, 1); vol.inputs['Anisotropy'].default_value = 0.75
    if '--novol' not in sys.argv:
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 25, 6.5)); wb = bpy.context.object; wb.scale = (90, 110, 13)
        wm = bpy.data.materials.new('water'); wm.use_nodes = True; wn = wm.node_tree; wn.nodes.remove(wn.nodes['Principled BSDF'])
        wv = wn.nodes.new('ShaderNodeVolumePrincipled'); wv.inputs['Density'].default_value = 0.03
        wv.inputs['Color'].default_value = (0.45, 0.8, 0.85, 1); wv.inputs['Anisotropy'].default_value = 0.75
        wv.inputs['Absorption Color'].default_value = (0.82, 0.95, 0.97, 1)
        wn.links.new(wv.outputs[0], wn.nodes['Material Output'].inputs['Volume']); wb.data.materials.append(wm)
    # sand floor
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, 0)); g = bpy.context.object
    gm = bpy.data.materials.new('sand'); gm.use_nodes = True; gm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.55, 0.5, 0.38, 1); g.data.materials.append(gm)
    for i in range(70):
        x, y = R.uniform(-22, 22), R.uniform(4, 60)
        if abs(x) < 1.6: continue
        put(R.choice(['laminaria_a', 'laminaria_a', 'laminaria_b']), (x, y, 0), R.uniform(0, 360), R.uniform(0.9, 1.2))
    S = bpy.data.lights.new('sun', 'SUN'); S.energy = 6.0; S.color = (1.0, 0.97, 0.88); S.angle = math.radians(1.5)
    so = bpy.data.objects.new('sun', S); so.rotation_euler = (math.radians(28), 0, math.radians(175)); sc.collection.objects.link(so)
    cam.lens = 24; co.location = (0, -2, 1.7); tgt = Vector((0, 30, 6.5))
d = tgt - co.location; co.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
sc.render.filepath = out; bpy.ops.render.render(write_still=True)
