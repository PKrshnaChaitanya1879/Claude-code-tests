"""Coral forest preview: bubblegum-coral trees and a black-coral garland, deep, lit by a diver's lamp; or plain light.
Run: python3 preview_coral.py <crespo_flora.blend> <out.png> <lamp|clay>"""
import sys, math, bpy
from mathutils import Vector
blend, out, mode = sys.argv[-3], sys.argv[-2], sys.argv[-1]
bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene
for o in sc.objects: o.hide_render = True
src = {o.name: o for o in sc.objects if o.type == 'MESH'}
sc.render.engine = 'BLENDER_EEVEE'; sc.render.resolution_x, sc.render.resolution_y = 900, 640
for k, v in (('taa_render_samples', 32), ('volumetric_tile_size', '4'), ('volumetric_samples', 64), ('use_volumetric_shadows', True)):
    try: setattr(sc.eevee, k, v)
    except Exception: pass
sc.view_settings.view_transform = 'AgX'
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; nt = w.node_tree
def put(n, loc, rz=0, s=1.0, sx=None):
    o = src[n].copy(); o.data = src[n].data; sc.collection.objects.link(o); o.hide_render = False
    o.location = loc; o.rotation_euler = (0, 0, math.radians(rz)); o.scale = (sx or s, s, s); return o
put('coral_tree', (-2.2, 6, 0), 0, 1.4); put('coral_tree2', (3.0, 7.5, 0), 20, 1.4); put('coral_tree', (0.5, 13, 0), 70, 1.6)
g = put('bindweed_garland', (0.4, 6.8, 3.4), 15, 1.0, sx=1.3)
bpy.ops.mesh.primitive_plane_add(size=80, location=(0, 10, 0)); fl = bpy.context.object
fm = bpy.data.materials.new('floor'); fm.use_nodes = True; fm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.35, 0.32, 0.28, 1); fl.data.materials.append(fm)
cam = bpy.data.cameras.new('c'); cam.lens = 26; co = bpy.data.objects.new('c', cam); sc.collection.objects.link(co); sc.camera = co
co.location = (0.4, -3.5, 1.7); tgt = Vector((0.4, 8, 2.4))
if mode == 'clay':
    nt.nodes['Background'].inputs['Color'].default_value = (0.3, 0.32, 0.34, 1)
    S = bpy.data.lights.new('sun', 'SUN'); S.energy = 3.0; so = bpy.data.objects.new('sun', S); so.rotation_euler = (math.radians(45), 0, math.radians(20)); sc.collection.objects.link(so)
else:
    nt.nodes['Background'].inputs['Color'].default_value = (0.0, 0.004, 0.008, 1)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 10, 4)); wb = bpy.context.object; wb.scale = (60, 60, 20)
    wm = bpy.data.materials.new('water'); wm.use_nodes = True; wn = wm.node_tree; wn.nodes.remove(wn.nodes['Principled BSDF'])
    wv = wn.nodes.new('ShaderNodeVolumePrincipled'); wv.inputs['Density'].default_value = 0.06; wv.inputs['Color'].default_value = (0.5, 0.75, 0.8, 1); wv.inputs['Anisotropy'].default_value = 0.6
    wn.links.new(wv.outputs[0], wn.nodes['Material Output'].inputs['Volume']); wb.data.materials.append(wm)
    for x, e in ((0.7, 900), (-0.6, 700)):   # two divers' Ruhmkorff lamps, warm white
        L = bpy.data.lights.new('lamp', 'SPOT'); L.energy = e; L.spot_size = math.radians(40); L.spot_blend = 0.6; L.color = (1.0, 0.93, 0.8)
        lo = bpy.data.objects.new('lamp', L); lo.location = (x, -2.8, 1.2); sc.collection.objects.link(lo)
        d = Vector((0.4, 8, 1.8)) - lo.location; lo.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
d = tgt - co.location; co.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
sc.render.filepath = out; bpy.ops.render.render(write_still=True)
