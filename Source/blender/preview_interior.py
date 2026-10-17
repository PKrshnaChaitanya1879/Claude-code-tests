"""Interior previews (Eevee): one view per room, framed like the engravings.
Run: python3 preview_interior.py <blend> <out_prefix>"""
import math, sys
import bpy
from mathutils import Vector

blend, out = sys.argv[-2], sys.argv[-1]
bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene
eng = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]
sc.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in eng else 'BLENDER_EEVEE'
sc.render.resolution_x, sc.render.resolution_y = 800, 560
try: sc.eevee.taa_render_samples = 16
except Exception: pass
try:
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
except Exception: pass
if sc.world is None: sc.world = bpy.data.worlds.new('w')
sc.world.use_nodes = True
sc.world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.02, 0.02, 0.025, 1)
for m in bpy.data.materials:
    m.use_backface_culling = True   # as in Unity (URP Lit culls back faces): coplanar room shells don't z-fight
    if m.use_nodes and m.name in ('M_ceiling', 'M_globe', 'M_bulb'):
        b = m.node_tree.nodes.get('Principled BSDF')
        if b: b.inputs['Emission Strength'].default_value = 6.0

def pl(loc, energy, color=(1, 0.92, 0.8)):
    ld = bpy.data.lights.new('l', 'POINT'); ld.energy = energy; ld.color = color; ld.shadow_soft_size = 0.5
    o = bpy.data.objects.new('l', ld); o.location = loc; sc.collection.objects.link(o)
for loc, e in [((15, 0, 4.2), 900), ((12, 0, 4.0), 500), ((18, 0, 4.0), 500), ((7.5, 0, 2.9), 400), ((22.5, 0, 2.6), 300),
               ((26.2, 0, 2.4), 150), ((2.5, 0, 2.9), 400)]:
    pl(loc, e)
cd = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cd); sc.collection.objects.link(cam); sc.camera = cam
cd.clip_start = 0.05
def shot(name, loc, target, lens=18):
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    cd.lens = lens
    sc.render.filepath = out + '_' + name + '.png'
    bpy.ops.render.render(write_still=True)
shot('saloon', (10.5, -0.9, 1.7), (20, 0.2, 2.0), 16)      # like im022: looking forward at the organ
shot('saloon_window', (15.0, -2.0, 1.4), (15.0, 3.5, 2.0), 16)
shot('library', (9.6, -2.5, 1.6), (5.0, 1.8, 1.2), 16)
shot('nemo', (20.6, 2.4, 1.6), (23.0, -3.2, 1.7), 16)
shot('dining', (4.6, 2.6, 1.6), (0.2, -1.5, 1.0), 16)
shot('aronnax', (25.3, -2.0, 1.6), (27.4, 1.5, 0.8), 16)
print('done')
