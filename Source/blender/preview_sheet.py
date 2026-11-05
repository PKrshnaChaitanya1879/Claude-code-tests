"""A labelled sheet of named props from a .blend, side by side on a grey floor, clay-lit (quick look, Eevee 16 samples).
Run: python3 preview_sheet.py <file.blend> <out.png> name1 name2 ...   (5 Nov 2026)"""
import sys, math, bpy
from mathutils import Vector
a = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
blend, out, names = a[0], a[1], a[2:]
bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene
for o in sc.objects: o.hide_render = True
src = {o.name: o for o in sc.objects if o.type == 'MESH'}
names = [n for n in names if n in src]
cols = min(6, len(names)); rows = (len(names) + cols - 1) // cols
sizes = [max(src[n].dimensions) for n in names]
cell = max(sizes) * 1.15
for i, n in enumerate(names):
    o = src[n].copy(); o.data = src[n].data; sc.collection.objects.link(o); o.hide_render = False
    o.location = ((i % cols - (cols - 1) / 2) * cell, (i // cols) * cell * 1.1, 0); o.rotation_euler = (0, 0, math.radians(20))
    t = bpy.data.curves.new('t' + n, 'FONT'); t.body = n; t.size = cell * 0.08
    to = bpy.data.objects.new('t' + n, t); sc.collection.objects.link(to); to.location = o.location + Vector((-cell * 0.4, -cell * 0.45, 0.01))
sc.render.engine = 'BLENDER_EEVEE'; sc.render.resolution_x, sc.render.resolution_y = 1400, int(1400 * rows * 1.1 / cols * 0.8) + 200
try: sc.eevee.taa_render_samples = 16
except Exception: pass
sc.view_settings.view_transform = 'AgX'
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.32, 0.34, 0.36, 1)
bpy.ops.mesh.primitive_plane_add(size=cell * 30); fl = bpy.context.object
fm = bpy.data.materials.new('f'); fm.use_nodes = True; fm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.4, 0.39, 0.37, 1); fl.data.materials.append(fm)
for (rx, rz, e) in ((50, -35, 3.0), (65, 150, 1.2)):
    L = bpy.data.lights.new('s', 'SUN'); L.energy = e; L.angle = math.radians(8); lo = bpy.data.objects.new('s', L); lo.rotation_euler = (math.radians(rx), 0, math.radians(rz)); sc.collection.objects.link(lo)
cam = bpy.data.cameras.new('c'); cam.type = 'ORTHO'; cam.ortho_scale = cell * cols * 1.05
co = bpy.data.objects.new('c', cam); sc.collection.objects.link(co); sc.camera = co
cy = (rows - 1) * cell * 1.1 / 2
co.location = (0, cy - cell * rows * 2.2, cell * rows * 1.6 + max(sizes) * 0.5)
co.rotation_euler = (Vector((0, cy, max(sizes) * 0.35)) - co.location).to_track_quat('-Z', 'Y').to_euler()
sc.render.filepath = out; bpy.ops.render.render(write_still=True)
