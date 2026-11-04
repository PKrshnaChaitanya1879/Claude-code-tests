"""One object under plain soft light, three-quarter view, on a neutral floor.
Run: python3 preview_object.py <file.blend> <object> <out.png> [dist] [height]"""
import sys, math, bpy
from mathutils import Vector
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[-5:]
blend, name, out = args[0], args[1], args[2]
dist = float(args[3]) if len(args) > 3 else 4.0; ht = float(args[4]) if len(args) > 4 else 1.6
bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene
for o in sc.objects: o.hide_render = o.name != name
ob = sc.objects[name]; ob.location = (0, 0, 0); ob.rotation_euler = (0, 0, 0); ob.scale = (1, 1, 1)
sc.render.engine = 'BLENDER_EEVEE'; sc.render.resolution_x, sc.render.resolution_y = 700, 520
try: sc.eevee.taa_render_samples = 32
except Exception: pass
sc.view_settings.view_transform = 'AgX'
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.42, 0.45, 0.48, 1)
bpy.ops.mesh.primitive_plane_add(size=60); fl = bpy.context.object
fm = bpy.data.materials.new('f'); fm.use_nodes = True; fm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.45, 0.43, 0.4, 1); fl.data.materials.append(fm)
S = bpy.data.lights.new('sun', 'SUN'); S.energy = 3.0; S.angle = math.radians(8); so = bpy.data.objects.new('sun', S); so.rotation_euler = (math.radians(40), 0, math.radians(-30)); sc.collection.objects.link(so)
bb = [ob.matrix_world @ Vector(c) for c in ob.bound_box]; cz = sum(v.z for v in bb) / 8
cam = bpy.data.cameras.new('c'); cam.lens = 40; co = bpy.data.objects.new('c', cam); sc.collection.objects.link(co); sc.camera = co
co.location = (dist * 0.75, -dist, ht); d = Vector((0, 0, cz)) - co.location; co.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
sc.render.filepath = out; bpy.ops.render.render(write_still=True)
