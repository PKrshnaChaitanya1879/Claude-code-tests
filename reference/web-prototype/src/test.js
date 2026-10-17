import * as THREE from 'three';
import { Pipeline, QUALITY } from './pipeline.js';
import { UW, patchUnderwater, makeCausticTexture } from './uw.js';
import { MarineSnow } from './particles.js';
import { Terrain } from './terrain.js';
import { fbm2, ridge2, mulberry32 } from './noise.js';

const cfg = Object.assign({ cam: [0, 1.6, 8], look: [0, 1.2, -10], depth: 9, lamp: 0, sun: 1, q: 'medium' }, window.__cfg || {});
const renderer = new THREE.WebGLRenderer({ antialias: false, powerPreference: 'high-performance' });
renderer.setPixelRatio(1);
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFShadowMap;
document.body.appendChild(renderer.domElement);
const pipe = new Pipeline(renderer);
pipe.setQuality(QUALITY[cfg.q]);
pipe.setSize(window.innerWidth, window.innerHeight);
UW.uniforms.uCaustics.value = makeCausticTexture();
UW.uniforms.uDepthBase.value = cfg.depth;

const ext = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(70, window.innerWidth / window.innerHeight, 0.05, 400);

const terr = new Terrain({ x0: -80, z0: -120, x1: 80, z1: 40, cell: 1.2,
  fn: (x, z) => fbm2(x * 0.03, z * 0.03, 4) * 4 + Math.max(0, -z - 30) * -0.15 + ridge2(x * 0.05 + 3, z * 0.05, 3) * 1.5,
  colorFn: (x, z, h, s) => { const n = fbm2(x * 0.3, z * 0.3, 2); const sand = [0.44 + n * 0.08, 0.41 + n * 0.06, 0.34]; const rock = [0.35, 0.36, 0.34]; const t = Math.min(1, s * 3); return sand.map((v, i) => v * (1 - t) + rock[i] * t); } });
const tmat = patchUnderwater(new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.95, flatShading: true }));
const tmesh = new THREE.Mesh(terr.geometry, tmat); tmesh.receiveShadow = true; tmesh.castShadow = true; ext.add(tmesh);

camera.position.set(cfg.cam[0], terr.height(cfg.cam[0], cfg.cam[2]) + cfg.cam[1], cfg.cam[2]);
camera.lookAt(new THREE.Vector3(cfg.look[0], terr.height(cfg.cam[0], cfg.cam[2]) + cfg.look[1], cfg.look[2]));
const rnd = mulberry32(3);
const rockMat = patchUnderwater(new THREE.MeshStandardMaterial({ color: 0x575c58, roughness: 0.9, flatShading: true }));
for (let i = 0; i < 40; i++) {
  const g = new THREE.IcosahedronGeometry(1, 1);
  const p = g.attributes.position; for (let k = 0; k < p.count; k++) p.setXYZ(k, p.getX(k) * (1 + rnd() * 0.3), p.getY(k) * (0.6 + rnd() * 0.3), p.getZ(k) * (1 + rnd() * 0.3));
  g.computeVertexNormals();
  const m = new THREE.Mesh(g, rockMat); const x = (rnd() - 0.5) * 60, z = -rnd() * 90; const s = 0.6 + rnd() * 2.5;
  m.position.set(x, terr.height(x, z), z); m.scale.setScalar(s); m.rotation.y = rnd() * 6; m.castShadow = m.receiveShadow = true; ext.add(m);
}
// rigid vertical fucus (the book's "region of perpendicularity")
const kelpMat = patchUnderwater(new THREE.MeshStandardMaterial({ color: 0x7a8a3a, roughness: 0.8, side: THREE.DoubleSide, flatShading: true }));
for (let i = 0; i < 160; i++) {
  const hgt = 3 + rnd() * 9; const g = new THREE.CylinderGeometry(0.03, 0.09, hgt, 5, 1);
  const m = new THREE.Mesh(g, kelpMat); const x = (rnd() - 0.5) * 50, z = -10 - rnd() * 60;
  m.position.set(x, terr.height(x, z) + hgt / 2, z); m.castShadow = true; ext.add(m);
  const leaf = new THREE.Mesh(new THREE.PlaneGeometry(0.35, hgt * 0.8), kelpMat); leaf.position.copy(m.position); leaf.rotation.y = rnd() * 3; leaf.castShadow = true; ext.add(leaf);
}
// columns
const colMat = patchUnderwater(new THREE.MeshStandardMaterial({ color: 0xb8b2a2, roughness: 0.9, flatShading: true }));
for (let i = 0; i < 6; i++) { const c = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.55, 6, 12), colMat); c.position.set(-8 + i * 3.2, terr.height(-8 + i * 3.2, -25) + 3, -25); c.castShadow = c.receiveShadow = true; ext.add(c); }
// coral colours test
const coralCols = [0xd2493a, 0xe39b2f, 0x9a4fb0, 0xe7d36a, 0x3aa0b8];
for (let i = 0; i < 30; i++) { const m = new THREE.Mesh(new THREE.IcosahedronGeometry(0.4 + rnd() * 0.4, 0), patchUnderwater(new THREE.MeshStandardMaterial({ color: coralCols[i % 5], roughness: 0.7, flatShading: true }))); const x = (rnd() - 0.5) * 10, z = 2 - rnd() * 10; m.position.set(x, terr.height(x, z) + 0.3, z); ext.add(m); }

const sun = new THREE.DirectionalLight(0xffffff, 1.0);
sun.castShadow = true; sun.shadow.mapSize.set(1024, 1024);
const sc = sun.shadow.camera; sc.left = -40; sc.right = 40; sc.top = 40; sc.bottom = -40; sc.near = 1; sc.far = 140;
sun.shadow.bias = -0.0008;
ext.add(sun); ext.add(sun.target);
const sdir = UW.uniforms.uSunDir.value;
const lamp = new THREE.SpotLight(0xe8f0ff, cfg.lamp ? 60 : 0, 0, 0.75, 0.6, 2);
lamp.castShadow = true; lamp.shadow.mapSize.set(512, 512); lamp.shadow.camera.near = 0.2; lamp.shadow.camera.far = 40;
camera.add(lamp); lamp.position.set(0.25, -0.5, 0); camera.add(lamp.target); lamp.target.position.set(0, -0.6, -5);
ext.add(camera);
const snow = new MarineSnow(5000, 22);

let t = 0;
function frame(dt) {
  t += dt;
  UW.uniforms.uTime.value = t;
  sun.position.copy(camera.position).addScaledVector(sdir, -60); sun.target.position.copy(camera.position).addScaledVector(sdir, 10);
  sun.intensity = cfg.sun;
  pipe.finalMat.uniforms.uFade.value = 0;
  if (cfg.dbg) pipe.compMat.uniforms.uDbg.value = cfg.dbg;
  pipe.finalMat.uniforms.uHelmet.value = cfg.helmet || 0;
  pipe.render({ extScene: ext, camera, lights: { sun: cfg.sun ? sun : null, spots: cfg.lamp ? [lamp] : [] }, particles: snow }, dt, t);
}
window.__renderFrames = (n) => { for (let i = 0; i < n; i++) frame(1 / 30); return renderer.info.render.calls; };
window.__ready = true;
