"""Preview renders of the Nautilus exterior next to the 1871 engravings.
Run: python3 preview_exterior.py <blend> <out_png>"""
import math, sys, os
import bpy
from mathutils import Vector

blend, out = sys.argv[-2], sys.argv[-1]
bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE'
sc.render.resolution_x, sc.render.resolution_y = 960, 540
try: sc.eevee.taa_render_samples = 16
except Exception: pass
sc.view_settings.view_transform = 'AgX' if 'AgX' in [i.identifier for i in sc.view_settings.bl_rna.properties['view_transform'].enum_items] else 'Filmic'
try: sc.view_settings.look = 'AgX - Medium High Contrast'
except Exception: pass
world = bpy.data.worlds.new('w'); sc.world = world; world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.045, 0.05, 0.055, 1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 1.0
for o in bpy.data.objects:
    if o.name.endswith(('_LOD1', '_LOD2', '_col')): o.hide_render = True

def light(name, loc, energy, size, rot):
    ld = bpy.data.lights.new(name, 'AREA'); ld.energy = energy; ld.size = size
    o = bpy.data.objects.new(name, ld); o.location = loc; o.rotation_euler = rot
    sc.collection.objects.link(o)
light('key', (20, 30, 40), 60000, 20, (math.radians(-35), math.radians(20), math.radians(150)))
light('rim', (-30, -25, 15), 25000, 15, (math.radians(70), 0, math.radians(-50)))
light('fill', (0, -40, 5), 6000, 30, (math.radians(85), 0, 0))

cam_data = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cam_data); sc.collection.objects.link(cam); sc.camera = cam

def shot(path, loc, target, lens):
    cam.location = loc
    d = Vector(target) - Vector(loc)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    cam_data.lens = lens
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)

base = os.path.splitext(out)[0]
shot(base + '_side.png', (0, 95, 3), (0, 0, 2), 50)          # port profile, like ill-011
shot(base + '_deck.png', (26, 16, 14), (2, 0, 6), 35)         # platform, cages, boat (im027)
shot(base + '_bow.png', (52, 14, 5), (20, 0, 2), 40)          # bow and spur, three-quarter
shot(base + '_stern.png', (-50, -16, 3), (-30, 0, 2), 40)     # screw, rudder, planes
print('rendered', base)
