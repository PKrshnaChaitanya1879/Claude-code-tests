"""The diver assembled on DiverPuppet's joints (Divers.cs), rendered from the front three-quarter and the back.
Run: python3 preview_diver.py <diver_parts.blend> <out_prefix>"""
import sys, math, bpy
from mathutils import Vector
blend, out = sys.argv[-2], sys.argv[-1]
bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene
src = {o.name: o for o in sc.objects}
for o in sc.objects: o.hide_render = True
def U(x, y, z): return Vector((x, -z, y))          # Unity (x, y, z) -> Blender, front = -Y
def put(name, p):
    o = src[name].copy(); o.data = src[name].data; sc.collection.objects.link(o)
    o.location = p; o.rotation_euler = (0, 0, 0); o.hide_render = False
hips = U(0, 1.04, 0)
put('diver_hips', hips); put('diver_torso', hips); put('diver_tank', hips + U(0, 0.27, -0.1)); put('diver_helmet', hips + U(0, 0.77, 0))
for x in (-0.22, 0.22):
    sh = hips + U(x, 0.48, 0); put('diver_upperarm', sh); el = sh + U(0, -0.3, 0); put('diver_forearm', el)
    if x > 0: put('diver_stick', el + U(0, -0.36, 0.02))
for x in (-0.09, 0.09):
    hp = hips + U(x, -0.12, 0); put('diver_thigh', hp); kn = hp + U(0, -0.42, 0); put('diver_shin', kn); put('diver_boot', kn + U(0, -0.4, 0))
put('diver_lamp', hips + U(0.14, 0.06, 0.15))
sc.render.engine = 'BLENDER_EEVEE'; sc.render.resolution_x, sc.render.resolution_y = 400, 600
try: sc.eevee.taa_render_samples = 16
except Exception: pass
sc.view_settings.view_transform = 'AgX'
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.3, 0.32, 0.34, 1)
bpy.ops.mesh.primitive_plane_add(size=40); fl = bpy.context.object
fm = bpy.data.materials.new('f'); fm.use_nodes = True; fm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.35, 0.34, 0.32, 1); fl.data.materials.append(fm)
for (rx, rz, e) in ((50, -35, 3.2), (60, 150, 1.4)):
    L = bpy.data.lights.new('s', 'SUN'); L.energy = e; L.angle = math.radians(10); lo = bpy.data.objects.new('s', L); lo.rotation_euler = (math.radians(rx), 0, math.radians(rz)); sc.collection.objects.link(lo)
cam = bpy.data.cameras.new('c'); cam.lens = 50; co = bpy.data.objects.new('c', cam); sc.collection.objects.link(co); sc.camera = co
for tag, ang in (('front', -28), ('back', 160), ('side', 90)):
    a = math.radians(ang); r = 4.2
    co.location = (r * math.sin(a), -r * math.cos(a), 1.15)
    co.rotation_euler = (Vector((0, 0, 0.95)) - co.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = f'{out}_{tag}.png'; bpy.ops.render.render(write_still=True)
