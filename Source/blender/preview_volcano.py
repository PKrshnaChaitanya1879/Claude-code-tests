"""Preview of the volcano alone at night under water, beside the West Mata reference.
Run: python3 preview_volcano.py <atlantis.blend> <out.png>"""
import sys, math, bpy
from mathutils import Vector
blend, out, mode = sys.argv[-3], sys.argv[-2], sys.argv[-1]
bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene
for o in list(sc.objects): o.hide_render = o.name not in ('volcano', 'lava_runs')
for o in sc.objects:
    if o.name in ('volcano', 'lava_runs'): o.location = (0, 0, 0); o.rotation_euler = (0, 0, 0); o.scale = (1, 1, 1)
sc.render.engine = 'BLENDER_EEVEE'; sc.render.resolution_x, sc.render.resolution_y = 900, 700
for k, v in (('taa_render_samples', 32), ('volumetric_tile_size', '4'), ('volumetric_samples', 64), ('volumetric_end', 400.0), ('use_volumetric_shadows', True), ('use_bloom', True)):
    try: setattr(sc.eevee, k, v)
    except Exception: pass
sc.view_settings.view_transform = 'AgX'
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; nt = w.node_tree
nt.nodes['Background'].inputs['Color'].default_value = (0.004, 0.003, 0.0025, 1)
# the water: a thin scattering medium so the fire lights it
vol = nt.nodes.new('ShaderNodeVolumePrincipled'); vol.inputs['Density'].default_value = 0.0025
vol.inputs['Color'].default_value = (0.75, 0.72, 0.7, 1); vol.inputs['Anisotropy'].default_value = 0.6
nt.links.new(vol.outputs[0], nt.nodes['World Output'].inputs['Volume'])
# the lava glows: crank emission for the preview (Unity sets its own)
for m in bpy.data.materials:
    if m.name.startswith('M_lava'):
        b = m.node_tree.nodes.get('Principled BSDF')
        b.inputs['Emission Strength'].default_value = 12.0 if m.name == 'M_lava' else 1.5
# the fire's light: one in the crater, one down the main fissure
for loc, e in (((0, 0, 97), 9e4), ((3, -2, 99), 4e4), ((22, -8, 82), 2.5e4), ((45, -17, 60), 2e4), ((70, -26, 38), 1.5e4)):
    L = bpy.data.lights.new('fire', 'POINT'); L.energy = e; L.color = (1.0, 0.45, 0.16); L.shadow_soft_size = 4
    lo = bpy.data.objects.new('fire', L); lo.location = loc; sc.collection.objects.link(lo)
# the vapour: a rising column of steam, lit from below by the crater
bpy.ops.mesh.primitive_cone_add(radius1=14, radius2=45, depth=140, location=(0, 0, 182)); plume = bpy.context.object
pm = bpy.data.materials.new('plume'); pm.use_nodes = True; pn = pm.node_tree
pn.nodes.remove(pn.nodes['Principled BSDF'])
pv = pn.nodes.new('ShaderNodeVolumePrincipled'); tex = pn.nodes.new('ShaderNodeTexNoise'); tex.inputs['Scale'].default_value = 0.35; tex.inputs['Detail'].default_value = 6
grad = pn.nodes.new('ShaderNodeMapRange'); grad.inputs['From Min'].default_value = 0.5; grad.inputs['From Max'].default_value = 0.85; grad.inputs['To Max'].default_value = 1.2
pn.links.new(tex.outputs['Fac'], grad.inputs['Value']); pn.links.new(grad.outputs['Result'], pv.inputs['Density'])
pv.inputs['Color'].default_value = (0.85, 0.84, 0.82, 1)
pn.links.new(pv.outputs[0], pn.nodes['Material Output'].inputs['Volume']); plume.data.materials.append(pm)
cam = bpy.data.cameras.new('c'); cam.lens = 28; co = bpy.data.objects.new('c', cam); sc.collection.objects.link(co); sc.camera = co
if mode == 'clay':
    for m in bpy.data.materials:
        if m.name.startswith('M_lava'): m.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 2.0
    plume.hide_render = True; vol.inputs['Density'].default_value = 0.0
    nt.nodes['Background'].inputs['Color'].default_value = (0.25, 0.27, 0.3, 1)
    S = bpy.data.lights.new('sun', 'SUN'); S.energy = 3.5; so = bpy.data.objects.new('sun', S); so.rotation_euler = (math.radians(50), 0, math.radians(35)); sc.collection.objects.link(so)
    co.location = (230, -200, 120); tgt = Vector((0, 0, 45))
elif mode == 'crater':
    cam.lens = 26; co.location = (34, -30, 132); tgt = Vector((0, 0, 96))
elif mode == 'close':
    cam.lens = 24; co.location = (30, -24, 112); tgt = Vector((0, 0, 98))
else:
    co.location = (230, -170, 60); tgt = Vector((0, 0, 55))
d = tgt - co.location; co.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
sc.render.filepath = out; bpy.ops.render.render(write_still=True)
