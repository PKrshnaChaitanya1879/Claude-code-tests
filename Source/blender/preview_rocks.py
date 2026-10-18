"""Preview of the sea-floor rocks on sand under a high sun, for comparison with im034.
Run: python3 preview_rocks.py <rocks.blend> <out_png>"""
import math, sys, bpy
from mathutils import Vector
blend, out = sys.argv[-2], sys.argv[-1]
bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE'
sc.render.resolution_x, sc.render.resolution_y = 1200, 420
try: sc.eevee.taa_render_samples = 16
except Exception: pass
sc.view_settings.view_transform = 'AgX'
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.05, 0.16, 0.17, 1)
bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0))
sand = bpy.data.materials.new('sand'); sand.use_nodes = True
sand.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.42, 0.39, 0.32, 1)
bpy.context.object.data.materials.append(sand)
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); sun.data.energy = 2.5; sun.rotation_euler = (math.radians(25), math.radians(15), 0)
sc.collection.objects.link(sun)
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
cam.location = (0, -15, 4.0); d = Vector((0, 0, 0.7)) - cam.location
cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler(); cam.data.lens = 32
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
