// Material library: maps the Blender material names to textured three.js materials.
// Exterior (underwater) copies are patched with the water light model.
import * as THREE from 'three';
import { patchUnderwater } from './uw.js';

const loader = new THREE.TextureLoader();
const texCache = {};
export function tex(name, { srgb = true, repeat = 1 } = {}) {
  const key = name + srgb + repeat;
  if (!texCache[key]) {
    const t = loader.load('assets/tex/' + name + '.jpg');
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.repeat.set(repeat, repeat);
    t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
    t.anisotropy = 4;
    texCache[key] = t;
  }
  return texCache[key];
}

// spec: map (texture base name), color tint, roughness, metalness, normal strength, uv scale
const SPEC = {
  M_ebony: { map: 'ebony', color: 0x8a6a5a, rough: 0.42, metal: 0, normal: 0.5, scale: 0.7 },
  M_oak: { map: 'oak', color: 0xb08a68, rough: 0.55, metal: 0, normal: 0.4, scale: 0.5 },
  M_tapestry: { map: 'tapestry', color: 0xffffff, boost: 1.35, rough: 0.95, metal: 0, normal: 0.0, scale: 0.9 },
  M_carpet: { map: 'carpet', color: 0xffffff, rough: 1.0, metal: 0, normal: 0.0, scale: 0.55 },
  M_leather: { map: 'leather', color: 0xc08a68, rough: 0.5, metal: 0, normal: 0.6, scale: 1.2 },
  M_brass: { map: 'brass', color: 0xd9b26a, rough: 0.32, metal: 1, normal: 0.0, scale: 1.0 },
  M_gilt: { map: 'brass', color: 0xb8904a, rough: 0.4, metal: 1, normal: 0.0, scale: 1.0 },
  M_copper: { map: 'brass', color: 0xd08a64, rough: 0.38, metal: 1, normal: 0.0, scale: 1.0 },
  M_bronze: { map: 'brass', color: 0x6b4a2a, rough: 0.45, metal: 1, normal: 0.0, scale: 1.0 },
  M_iron: { map: 'iron', color: 0x8a8a88, rough: 0.6, metal: 0.7, normal: 0.6, scale: 0.6 },
  M_ironpaint: { map: 'ironpaint', color: 0x9a9c96, rough: 0.7, metal: 0.2, normal: 0.4, scale: 0.6 },
  M_grate: { map: 'iron', color: 0x5a5a58, rough: 0.55, metal: 0.8, normal: 0.8, scale: 1.5 },
  M_plaster: { map: 'plaster', color: 0xd8d0c0, rough: 0.9, metal: 0, normal: 0.2, scale: 0.4 },
  M_marble: { map: 'plaster', color: 0xf0ece4, rough: 0.35, metal: 0, normal: 0.1, scale: 1.5 },
  M_hull: { map: 'iron', color: 0x6a6c68, rough: 0.55, metal: 0.6, normal: 0.8, scale: 0.35 },
  M_pipe: { color: 0xb8b8b4, rough: 0.28, metal: 1 },
  M_linen: { color: 0xd8d2c4, rough: 0.95, metal: 0 },
  M_paper: { color: 0xd8ceb0, rough: 0.95, metal: 0 },
  M_rubber: { color: 0x2a2420, rough: 0.7, metal: 0 },
  M_shell: { color: 0xe0d2c0, rough: 0.45, metal: 0 },
  M_coralspec: { color: 0xc03a2a, rough: 0.6, metal: 0 },
  M_pearl: { color: 0xf0ece4, rough: 0.2, metal: 0.1 },
  M_dial: { color: 0xe8e0c8, rough: 0.6, metal: 0 },
  M_black: { color: 0x080808, rough: 0.6, metal: 0 },
  M_lensdark: { color: 0x1a2224, rough: 0.08, metal: 0.3 },
  M_velvet: { color: 0x5a1416, rough: 0.9, metal: 0 },
  // props
  M_suit: { map: 'leather', color: 0x5a4a3c, rough: 0.72, metal: 0, normal: 0.35, scale: 3.0 },
  M_port: { color: 0x0c1214, rough: 0.05, metal: 0.5 },
  M_lead: { color: 0x55575a, rough: 0.6, metal: 0.6 },
  M_coral_red: { color: 0xb02a1c, rough: 0.7, metal: 0 },
  M_coral_orange: { color: 0xe07a2c, rough: 0.7, metal: 0 },
  M_coral_purple: { color: 0x8a3c9c, rough: 0.7, metal: 0 },
  M_coral_yellow: { color: 0xe0c050, rough: 0.7, metal: 0 },
  M_coral_pink: { color: 0xe8909a, rough: 0.7, metal: 0 },
  M_coral_white: { color: 0xe0dccf, rough: 0.75, metal: 0 },
  M_coral_teal: { color: 0x3a9a94, rough: 0.7, metal: 0 },
  M_coral_stone: { map: 'rock', color: 0xbcb2a2, rough: 0.9, metal: 0, normal: 0.7, scale: 0.6 },
  M_polyp: { color: 0xf6f0e2, rough: 0.5, metal: 0 },
  M_kelp: { color: 0x7a8a30, rough: 0.8, metal: 0 },
  M_kelp_red: { color: 0x8a3024, rough: 0.8, metal: 0 },
  M_rock: { map: 'rock', color: 0xa8a8a0, rough: 0.95, metal: 0, normal: 0.9, scale: 0.45 },
  M_basalt: { map: 'rock2', color: 0x48484a, rough: 0.85, metal: 0, normal: 0.8, scale: 0.5 },
  M_ruinstone: { map: 'plaster', color: 0xc8bea8, rough: 0.9, metal: 0, normal: 0.5, scale: 0.35 },
  M_deadwood: { map: 'ebony', color: 0x3a342e, rough: 0.95, metal: 0, normal: 0.8, scale: 0.8 },
  M_fish_a: { color: 0xe0c040, rough: 0.4, metal: 0.1 },
  M_fish_b: { color: 0x4a6ab0, rough: 0.4, metal: 0.1 },
  M_fish_c: { color: 0xc8ccd4, rough: 0.3, metal: 0.4 },
  M_crab: { color: 0x9a4020, rough: 0.6, metal: 0 },
  M_terrain: { map: 'sand', color: 0xffffff, rough: 1.0, metal: 0, normal: 0.6, scale: 0.3 },
  M_terrain_rock: { map: 'rock', color: 0xffffff, rough: 1.0, metal: 0, normal: 0.9, scale: 0.18 },
};

const cache = {};
export function makeMaterial(name, ext = false, src = null) {
  const key = name + (ext ? ':ext' : '');
  if (cache[key]) return cache[key];
  let m;
  const s = SPEC[name];
  if (name === 'M_ceiling') {
    m = new THREE.MeshBasicMaterial({ map: tex('ceiling_c'), color: new THREE.Color(1.6, 1.55, 1.4) });
  } else if (name === 'M_globe' || name === 'M_bulb') {
    m = new THREE.MeshBasicMaterial({ color: new THREE.Color(3.0, 2.7, 2.2) });
  } else if (name === 'M_coal') {
    m = new THREE.MeshBasicMaterial({ color: new THREE.Color(2.5, 0.6, 0.12) });
  } else if (name === 'M_lampglass') {
    m = new THREE.MeshBasicMaterial({ color: new THREE.Color(3.2, 3.4, 3.6) });
  } else if (name === 'M_eye') {
    m = new THREE.MeshBasicMaterial({ color: new THREE.Color(0.5, 2.4, 1.6) });
  } else if (name === 'M_jelly') {
    m = new THREE.MeshStandardMaterial({ color: 0xc8d8f0, roughness: 0.2, transparent: true, opacity: 0.45, emissive: new THREE.Color(0.05, 0.12, 0.16), depthWrite: false });
  } else if (name === 'M_lens') {
    m = new THREE.MeshBasicMaterial({ color: new THREE.Color(6, 6.3, 6.6) });
  } else if (name === 'M_glass') {
    m = new THREE.MeshStandardMaterial({ color: 0xbfd6d8, roughness: 0.05, metalness: 0.0, transparent: true, opacity: 0.16, depthWrite: false });
  } else if (name === 'M_crystal') {
    // the saloon's crystal plates seen from outside: a faint sheen, mostly transparent
    m = new THREE.MeshStandardMaterial({ color: 0xa8c8cc, roughness: 0.04, metalness: 0.0, transparent: true, opacity: 0.12, depthWrite: false });
  } else if (name === 'M_water') {
    m = new THREE.MeshStandardMaterial({ color: 0x5e8e96, roughness: 0.05, metalness: 0.2, transparent: true, opacity: 0.7 });
  } else if (s) {
    m = new THREE.MeshStandardMaterial({ color: s.color, roughness: s.rough, metalness: s.metal ?? 0, vertexColors: true });
    if (s.boost) m.color.multiplyScalar(s.boost);
    if (s.map) {
      m.map = tex(s.map + '_c', { repeat: s.scale });
      if (s.normal) { m.normalMap = tex(s.map + '_n', { srgb: false, repeat: s.scale }); m.normalScale = new THREE.Vector2(s.normal, s.normal); }
    }
  } else {
    const c = src && src.color ? src.color : new THREE.Color(0.6, 0.6, 0.6);
    m = new THREE.MeshStandardMaterial({ color: c, roughness: 0.8, vertexColors: true });
  }
  m.name = name;
  if (ext && m.isMeshStandardMaterial) patchUnderwater(m);
  cache[key] = m;
  return m;
}

// scale UVs of a geometry in place (world-planar UVs from Blender are 1 unit per metre)
export function scaleUV(geo, s) {
  const uv = geo.attributes.uv;
  if (!uv || s === 1) return;
  for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) * s, uv.getY(i) * s);
  uv.needsUpdate = true;
}
