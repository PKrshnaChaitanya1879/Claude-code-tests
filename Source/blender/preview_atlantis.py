"""Preview of the Atlantis kit composed like plate im079: the summit in the foreground with Nemo's silhouette,
the volcano behind raining fire, the city below lit only by its glow, in dark water.
Run: python3 preview_atlantis.py <atlantis.blend> <Diver_Parts.fbx> <out.png>"""
import sys, math, random, bpy
from mathutils import Vector
blend, divers, out = sys.argv[-3], sys.argv[-2], sys.argv[-1]
bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene
for o in list(sc.objects): o.hide_render = True
sc.render.engine = 'BLENDER_EEVEE'; sc.render.resolution_x, sc.render.resolution_y = 600, 860
for k, v in (('taa_render_samples', 24), ('volumetric_tile_size', '4'), ('volumetric_samples', 48), ('volumetric_end', 400.0), ('use_volumetric_shadows', True)):
    try: setattr(sc.eevee, k, v)
    except Exception: pass
sc.view_settings.view_transform = 'AgX'
try: sc.view_settings.look = 'AgX - Medium High Contrast'
except Exception: pass
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.0, 0.0, 0.0, 1)
src = {o.name: o for o in bpy.data.objects if o.type == 'MESH'}
R = random.Random(5)
def put(n, loc, rz=0, s=1.0):
    o = src[n].copy(); o.data = src[n].data; sc.collection.objects.link(o); o.hide_render = False
    o.location = loc; o.rotation_euler = (0, 0, math.radians(rz)); o.scale = (s, s, s); return o
# ground of the city
bpy.ops.mesh.primitive_plane_add(size=900, location=(0, 150, -40)); g = bpy.context.object
gm = bpy.data.materials.new('g'); gm.use_nodes = True; gm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.08, 0.07, 0.07, 1); g.data.materials.append(gm)
put('summit', (0, 0, -22))
put('volcano', (60, 260, -40), 0, 1.0); put('lava_runs', (60, 260, -40), 200)
put('acropolis', (-40, 220, -40), 15)
put('aqueduct', (-90, 150, -40), 70)
for i in range(4): put('temple_ruin' if i % 2 == 0 else 'temple_ruin_small', (-30 + i * 22, 90 + R.uniform(-10, 10), -40), R.uniform(-10, 10))
for i in range(18): put(R.choice(['house_ruin_a', 'house_ruin_b', 'house_ruin_c']), (R.uniform(-100, 60), R.uniform(110, 200), -40), R.uniform(0, 90))
for i in range(14): put(R.choice(['col_tuscan', 'col_broken_a', 'col_broken_b']), (-50 + i * 4, 60 + R.uniform(-3, 3), -40))
for i in range(10): put('col_drum', (R.uniform(-50, 10), R.uniform(55, 75), -40), R.uniform(0, 360))
put('quay', (-20, 240, -40), 5, 2.0)
for i in range(40):
    put('scoria', (60 + R.uniform(-60, 60), 260 + R.uniform(-60, 60), R.uniform(-10, 60)), R.uniform(0, 360), R.uniform(2, 5))
# Nemo on the summit
bpy.ops.import_scene.fbx(filepath=divers)
parts = {o.name.split('.')[0]: o for o in bpy.context.selected_objects}
for o in parts.values(): o.hide_render = True
def part(n, off):
    if n not in parts: return
    o = parts[n].copy(); o.data = parts[n].data; sc.collection.objects.link(o); o.hide_render = False
    o.location = Vector((1.0 + off[0], 1.5 + off[2], 0.1 + off[1]))
part('diver_hips', (0, 1.04, 0)); part('diver_torso', (0, 1.04, 0)); part('diver_tank', (0, 1.31, -0.1)); part('diver_helmet', (0, 1.81, 0))
for sx in (-0.22, 0.22): part('diver_upperarm', (sx, 1.52, 0)); part('diver_forearm', (sx, 1.22, 0))
for sx in (-0.09, 0.09): part('diver_thigh', (sx, 0.92, 0)); part('diver_shin', (sx, 0.5, 0)); part('diver_boot', (sx, 0.1, 0))
part('diver_stick', (0.3, 0.9, 0.0))
# the only light: the volcano
for loc, e in (((60, 260, 30), 4.0e6), ((40, 190, -25), 1.5e6), ((-20, 120, -10), 3.0e5)):
    L = bpy.data.objects.new('glow', bpy.data.lights.new('glow', 'POINT')); L.data.energy = e; L.data.color = (1.0, 0.35, 0.12); L.data.shadow_soft_size = 8
    L.location = loc; sc.collection.objects.link(L)
# the water at 150 fathoms: little scattering, art-directed so the red carries
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 150, 0)); cube = bpy.context.object; cube.scale = (900, 900, 200)
wm = bpy.data.materials.new('water'); wm.use_nodes = True; nt = wm.node_tree
for n in list(nt.nodes):
    if n.type != 'OUTPUT_MATERIAL': nt.nodes.remove(n)
o_ = [n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'][0]
v = nt.nodes.new('ShaderNodeVolumePrincipled'); v.inputs['Color'].default_value = (0.9, 0.7, 0.6, 1); v.inputs['Density'].default_value = 0.0035
try: v.inputs['Anisotropy'].default_value = 0.45
except Exception: pass
v.inputs['Absorption Color'].default_value = (0.85, 0.75, 0.7, 1)
nt.links.new(v.outputs[0], o_.inputs['Volume']); cube.data.materials.append(wm)
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
cam.location = (-16, -10, 3.0); cam.rotation_euler = (Vector((8, 90, -18)) - cam.location).to_track_quat('-Z', 'Y').to_euler(); cam.data.lens = 22; cam.data.clip_end = 1200
sc.render.filepath = out; bpy.ops.render.render(write_still=True)
