"""Look-dev for M3 (Unity can't run here): the real Blender assets of Mission I (flora, rocks, divers) laid out
like CrespoFlora.cs, inside a participating-medium cube with the Mission1 VerneWater colour script
(sigma_s = sigma_t * albedo, sigma_a = sigma_t * (1 - albedo), surface at 9 m), a sun with volumetric shadows
(the shafts) and warm Ruhmkorff spots. Eevee, AgX. Three frames: the forest from the sand, the coral gallery
with lamps, the glade. Used to judge the INSIDE look (silhouettes in luminous fog, colour where light is).
Run: python3 lookdev_crespo.py <models dir (Unity Assets/Verne/Models)> <out prefix> [preset]"""
import sys, os, math, random
import bpy
from mathutils import Vector

_pos = [a for a in sys.argv if not a.startswith('--')]
models, out = _pos[-2], _pos[-1]
PRESET = dict(surfaceY=9.0, sigt=(0.16, 0.06, 0.056), alb=(0.42, 0.5, 0.52), sun=4.0, amb=(0.06, 0.11, 0.12))
for a in sys.argv:
    if a.startswith('--sigt='): PRESET['sigt'] = tuple(float(v) for v in a[7:].split(','))
    if a.startswith('--alb='): PRESET['alb'] = tuple(float(v) for v in a[6:].split(','))
    if a.startswith('--sun='): PRESET['sun'] = float(a[6:])

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
eng = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]
sc.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in eng else 'BLENDER_EEVEE'
sc.render.resolution_x, sc.render.resolution_y = 960, 540
ee = sc.eevee
for k, v in (('taa_render_samples', 24), ('volumetric_tile_size', '4'), ('volumetric_samples', 48), ('volumetric_end', 70.0),
             ('volumetric_start', 0.1), ('use_volumetric_shadows', True), ('volumetric_shadow_samples', 16), ('volumetric_light_clamp', 0.0)):
    try: setattr(ee, k, v)
    except Exception: pass
sc.view_settings.view_transform = 'AgX'
try: sc.view_settings.look = 'AgX - Medium High Contrast'
except Exception: pass
world = bpy.data.worlds.new('w'); sc.world = world; world.use_nodes = True
bg = world.node_tree.nodes['Background']; bg.inputs['Color'].default_value = (*PRESET['amb'], 1); bg.inputs['Strength'].default_value = 1.0

def imp(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    for o in new: o.hide_render = True; o.hide_viewport = True
    return {o.name.split('.')[0]: o for o in new if o.type == 'MESH'}

flora = imp(os.path.join(models, 'Crespo/Crespo_Flora.fbx'))
rocks = imp(os.path.join(models, 'Seabed/Seabed_Rocks.fbx'))
diver = imp(os.path.join(models, 'Divers/Diver_Parts.fbx'))

def ground(x, y):   # Blender: y = Unity z (north), z up
    return -min(max((y - 40) / 160, 0), 1) * 18 + 0.6 * math.sin(x * 0.11 + y * 0.07) * math.cos(y * 0.05)

# sea floor
bpy.ops.mesh.primitive_grid_add(x_subdivisions=120, y_subdivisions=120, size=240, location=(0, 60, 0))
floor = bpy.context.object
for v in floor.data.vertices: v.co.z = ground(v.co.x, v.co.y + 60)
sand = bpy.data.materials.new('sand'); sand.use_nodes = True
sand.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.36, 0.33, 0.26, 1)
sand.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.95
floor.data.materials.append(sand)

R = random.Random(1871)
def put(src, x, y, yaw=None, s=1.0, z=None):
    if src not in flora and src not in rocks: return None
    o0 = flora.get(src) or rocks.get(src)
    o = o0.copy(); o.data = o0.data; sc.collection.objects.link(o)
    o.hide_render = False; o.hide_viewport = False
    o.location = (x, y, ground(x, y) - 0.03 if z is None else z)
    o.rotation_euler = (o0.rotation_euler.x, o0.rotation_euler.y, math.radians(R.uniform(0, 360) if yaw is None else yaw))
    o.scale = (s * o0.scale.x, s * o0.scale.y, s * o0.scale.z)
    return o
def scatter(names, n, x0, x1, y0, y1, s0, s1, lane=0.0):
    i = 0; tries = 0
    while i < n and tries < n * 6:
        tries += 1
        x, y = R.uniform(x0, x1), R.uniform(y0, y1)
        if abs(x) < lane: continue
        put(R.choice(names), x, y, None, R.uniform(s0, s1)); i += 1

scatter(['sea_star_red', 'sea_star_orange', 'sea_star_violet', 'shells', 'fungia'], 60, -20, 20, 3, 36, 0.9, 1.4)
scatter(['anemone', 'cup_corals', 'sponge', 'brain_coral', 'brain_coral_teal'], 30, -18, 18, 6, 40, 0.8, 1.4, 2.2)
scatter(['red_algae', 'padina', 'acetabularia'], 70, -20, 20, 26, 48, 0.9, 1.6)
scatter(['fucus'], 14, -18, 18, 32, 50, 0.9, 1.3, 2.2)
scatter(['laminaria_a', 'laminaria_b'], 240, -26, 26, 44, 96, 1.0, 1.6, 2.2)
scatter(['alaria', 'fucus', 'red_algae', 'padina'], 80, -24, 24, 44, 96, 0.85, 1.5, 2.2)
scatter(['rock_boulder_a', 'rock_boulder_b', 'rock_boulder_c', 'rock_slab_a', 'rock_slab_b', 'rock_outcrop_a', 'rock_outcrop_b', 'rock_pebbles'], 40, -30, 30, 4, 110, 0.7, 1.6, 3.0)
put('gallery_vault', 0, 101, 0)
for y in (97.5, 101, 104.5): put('coral_arch', 0, y, 90 if flora['coral_arch'].dimensions.x < flora['coral_arch'].dimensions.y else 0)
scatter(['red_coral', 'tuft_coral', 'pink_coral', 'isis', 'gorgonian_fan', 'gorgonian_fan_yellow', 'basket_star', 'cup_corals', 'brain_coral'], 70, -9, 9, 95, 107, 0.9, 1.6, 2.2)
put('coral_cross', 0, 110, 0)
for k in range(6):
    if k == 4: continue
    put('grave_mound', -3 + (k % 3) * 3, 106.6 - (k // 3) * 2.6, R.uniform(-6, 6))
for k in range(9):
    a = k / 9 * math.tau + 0.3
    if abs(((math.degrees(a) - 270 + 180) % 360) - 180) < 22: continue
    put('coral_tree' if k % 2 == 0 else 'coral_tree2', math.cos(a) * 9, 110 + math.sin(a) * 9, None, R.uniform(1.3, 1.7))

# divers: the rigid parts at Divers.cs' joint offsets (Unity x,y,z -> Blender x,z,y), standing
def diver_at(x, y, yaw, lamp=False):
    root = bpy.data.objects.new('diver', None); sc.collection.objects.link(root)
    g = ground(x, y); root.location = (x, y, g); root.rotation_euler = (0, 0, math.radians(yaw))
    def part(name, off):
        if name not in diver: return
        o = diver[name].copy(); o.data = diver[name].data; sc.collection.objects.link(o)
        o.hide_render = False; o.parent = root; o.location = Vector((off[0], off[2], off[1]))
    part('diver_hips', (0, 1.04, 0)); part('diver_torso', (0, 1.04, 0)); part('diver_tank', (0, 1.31, -0.1)); part('diver_helmet', (0, 1.81, 0))
    for sx in (-0.22, 0.22): part('diver_upperarm', (sx, 1.52, 0)); part('diver_forearm', (sx, 1.22, 0))
    for sx in (-0.09, 0.09): part('diver_thigh', (sx, 0.92, 0)); part('diver_shin', (sx, 0.5, 0)); part('diver_boot', (sx, 0.1, 0))
    if lamp:
        ld = bpy.data.lights.new('lamp', 'SPOT'); ld.energy = 4000; ld.spot_size = math.radians(50); ld.color = (1, 0.93, 0.8)
        try: ld.use_shadow = False
        except Exception: pass
        lo = bpy.data.objects.new('lamp', ld); sc.collection.objects.link(lo); lo.parent = root
        lo.location = (0.14, 0.25, 1.1); lo.rotation_euler = (math.radians(75), 0, math.radians(R.uniform(-20, 20)))
    return root

# the water: a cube from the floor to the surface
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 60, (PRESET['surfaceY'] - 30) / 2))
cube = bpy.context.object; cube.scale = (240, 240, PRESET['surfaceY'] + 30)
wm = bpy.data.materials.new('water'); wm.use_nodes = True; nt = wm.node_tree
for n in list(nt.nodes):
    if n.type != 'OUTPUT_MATERIAL': nt.nodes.remove(n)
outn = [n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'][0]
sigt, alb = PRESET['sigt'], PRESET['alb']
ss = [sigt[i] * alb[i] for i in range(3)]; sa = [sigt[i] * (1 - alb[i]) for i in range(3)]
dS = max(ss); dA = max(sa)
scat = nt.nodes.new('ShaderNodeVolumeScatter'); scat.inputs['Color'].default_value = (*[c / dS for c in ss], 1); scat.inputs['Density'].default_value = dS
try: scat.inputs['Anisotropy'].default_value = 0.65
except Exception: pass
absn = nt.nodes.new('ShaderNodeVolumeAbsorption'); absn.inputs['Color'].default_value = (*[1 - c / dA for c in sa], 1); absn.inputs['Density'].default_value = dA
add = nt.nodes.new('ShaderNodeAddShader')
nt.links.new(scat.outputs[0], add.inputs[0]); nt.links.new(absn.outputs[0], add.inputs[1]); nt.links.new(add.outputs[0], outn.inputs['Volume'])
cube.data.materials.append(wm)

sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); sc.collection.objects.link(sun)
sun.data.energy = PRESET['sun']; sun.data.color = (0.9, 0.97, 0.92); sun.rotation_euler = (math.radians(32), 0, math.radians(180))   # from ahead, high
try: sun.data.angle = math.radians(1.5)
except Exception: pass

cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens = 24; cam.data.clip_end = 300
def shot(name, eye, target):
    cam.location = eye
    cam.rotation_euler = (Vector(target) - Vector(eye)).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = out + '_' + name + '.png'
    bpy.ops.render.render(write_still=True)

d1 = diver_at(0.6, 30, 0); d2 = diver_at(-1.2, 27, 0)
shot('forest', (0.4, 18, ground(0.4, 18) + 1.6), (0, 60, ground(0, 60) + 1.5))
d3 = diver_at(-1.0, 99, 25, lamp=True); d4 = diver_at(1.4, 96, -30, lamp=True)
shot('gallery', (0.2, 90, ground(0.2, 90) + 1.6), (0, 104, ground(0, 104) + 1.2))
shot('glade', (0.5, 100.5, ground(0.5, 100.5) + 1.7), (0, 112, ground(0, 112) + 1.4))
print('LOOKDEV', out)
