// Excursion II — A Vanished Continent (Part II, ch. IX).
// Midnight, 150 fathoms, no lamps. A reddish spot two miles off lights the way. Rain on the surface,
// heard through the water. A copse of dead, petrified trees on the mountain's flank; a crevice to jump,
// a trunk thrown across an abyss, the eyes of giant crustacea in their holes, ruins on the first
// platform; and from the summit, by the light of a submarine volcano, a drowned city: Atlantis.
import * as THREE from 'three';
import { UW, depthAt, patchUnderwater } from './uw.js';
import { Terrain } from './terrain.js';
import { Route, Procession } from './path.js';
import { fbm2, ridge2, mulberry32, smoothstep, clamp, lerp } from './noise.js';
import { makeMaterial, tex } from './materials.js';
import { trs } from './props.js';
import { Diver } from './npc.js';
import { b2t } from './nautilus.js';
import { bus } from './bus.js';

const WAY = [
  [-19.3, 8, -2.45], [-19.3, -5.4, -1.25], [-16, -20, -1.7], [-10, -45, -1.3], [-6, -75, -0.6], [-2, -100, 1.0],
  [2, -118, 4.0], [6, -130, 9.0], [4, -140, 13.5], [-2, -149, 18.5], [-5, -157, 23.0], [-3, -166, 28.5],
  [1, -174, 33.0], [5, -186, 36.0], [8, -194, 41.0], [6, -201, 47.0], [3, -207, 52.0], [1, -214, 57.5], [0, -221, 61.5], [0, -225, 62.0],
];
const SUMMIT = new THREE.Vector3(0, 62, -224);
const CRATER = new THREE.Vector3(55, 80, -236);
const CREVICE_Z = -163, CHASM_Z0 = -177.5, CHASM_Z1 = -184.5;

export class MissionAtlantis {
  constructor(game) {
    this.g = game; this.objs = [];
    this.hullDepth = 274; this.outsideAtm = 28.4; this.cullDistance = 420; this.needs = 'stick'; this.sunOn = false; this.glow = 1.0;
    this.current = new THREE.Vector3(0.02, 0.005, 0.01);
    this.stress = 0; this.reusable = true;
  }
  add(o) { this.g.ext.add(o); this.objs.push(o); return o; }
  wants(k) { return ['suit', 'tank', 'stick', 'helmet'].includes(k); }

  async build() {
    const g = this.g, P = g.props;
    const U = UW.uniforms;
    // 150 fathoms at the Nautilus; the summit stands ~800 ft above the plain, about 30 m below the surface
    U.uDepthBase.value = 274; U.uYRef.value = -1.25; U.uDepthScale.value = 3.85; U.uDepthQuad.value = 0;
    U.uSigmaA.value.set(0.0046, 0.0037, 0.0035); U.uSigmaS.value.set(0.0018, 0.002, 0.0023);
    U.uKd.value.set(0.08, 0.04, 0.03);
    U.uSunDir.value.set(0.12, -0.97, 0.2).normalize();
    U.uSunColor.value.set(0, 0, 0); U.uAmbTop.value.set(0.0, 0.0, 0.0);
    U.uAmbFloor.value = 1.0; U.uAmbFloorColor.value.set(0.04, 0.05, 0.065);
    U.uCausticStrength.value = 0.6; U.uWaterOn.value = 1;
    this.route = new Route(WAY);
    const R = this.route;
    // ---------------------------------------------------------------- terrain: plain, mountain, chasm, city below
    const mountain = (x, z) => {
      // near flank rises along the route; far side falls twice as far to the plain of Atlantis
      const dz = z - SUMMIT.z, dx = x - SUMMIT.x;
      const near = dz > 0 ? Math.max(0, 1 - dz / 115) : 0;
      const far = dz <= 0 ? Math.max(0, 1 - (-dz) / 30) : 0;
      const across = Math.exp(-(dx * dx) / (2 * 70 * 70));
      let h = 0;
      if (dz > 0) h = 63 * Math.pow(near, 1.35) * across;
      else h = lerp(-24, 63, Math.pow(far, 0.6)) * lerp(1, across, 0.3);
      return h;
    };
    const hfn = (x, z) => {
      const r = R.atZ(z);
      const dx = x - r.x;
      let h;
      const m = mountain(x, z);
      if (z > -112) {
        // the stony plain
        h = -1.4 + fbm2(x * 0.05, z * 0.05, 4) * 1.2 + ridge2(x * 0.12, z * 0.12, 3) * 0.6 + Math.max(0, Math.abs(dx) - 30) * 0.15;
        h = Math.max(h, m - 2);
      } else {
        // the mountain: a ledge path cut into the slope, steep rock either side
        const w = z < -205 ? 7 : 3.2;
        const wall = Math.max(0, Math.abs(dx) - w);
        const taper = smoothstep(SUMMIT.z + 1, SUMMIT.z + 24, z);
        h = Math.max(m, r.y) + (Math.min(wall * wall * 0.08, 9) + ridge2(x * 0.08, z * 0.08, 4) * Math.min(6, wall * 0.6)) * taper;
        if (z > SUMMIT.z) h = lerp(h, r.y, smoothstep(w + 2, w - 1, Math.abs(dx)));
        h += fbm2(x * 0.35, z * 0.35, 2) * 0.25;
      }
      // beyond the summit the far side falls away at once towards the plain of the city
      if (z < SUMMIT.z) {
        const b = SUMMIT.z - z;
        const hb = m + (ridge2(x * 0.03, z * 0.03, 4) * 6 + fbm2(x * 0.1, z * 0.1, 3) * 2) * smoothstep(3, 16, b);
        h = lerp(h, hb, smoothstep(0, 2.5, b));
      }
      // the summit: a small crown of rock with a brink on the city side, so the eye can range over the plain
      const sd = Math.hypot(x - SUMMIT.x, z - SUMMIT.z);
      const sc = Math.hypot(x - SUMMIT.x, z - (SUMMIT.z + 1.5));
      const bey = Math.max(0, SUMMIT.z - 0.5 - z);
      h = lerp(h, SUMMIT.y + fbm2(x * 0.3, z * 0.3, 2) * 0.3 - bey * bey * 0.4, smoothstep(5, 2.5, sc));
      // and the mountain narrows to its peak: nothing on the flanks stands higher than the summit
      h = Math.min(h, SUMMIT.y + 0.3 - 0.62 * Math.max(0, sd - 3.5) + Math.max(0, sd - 34) * 1.2);
      // crevice across the path, and the abyss spanned by a dead trunk
      const cz = Math.abs(z - CREVICE_Z);
      if (z < -150 && z > -175) h -= smoothstep(0.85, 0.55, cz) * 5.5;
      if (z < CHASM_Z0 + 0.5 && z > CHASM_Z1 - 0.5) h -= smoothstep(CHASM_Z0 + 0.5, CHASM_Z0 - 0.8, z) * smoothstep(CHASM_Z1 - 0.5, CHASM_Z1 + 0.8, z) * 16;
      // the volcano: its cone rises beside the summit, its crater fifty feet above the peak
      const vr = Math.hypot(x - CRATER.x, z - CRATER.z);
      if (vr < 100) {
        const vc = vr < 6 ? CRATER.y + 1 - (6 - vr) * 0.55
          : CRATER.y + 1 - Math.min(vr - 6, 19) * 1.6 - Math.max(0, vr - 25) * 1.0 + (fbm2(x * 0.12, z * 0.12, 3) - 0.5) * 5 * smoothstep(9, 22, vr);
        h = Math.max(h, vc);
      }
      // the Nautilus's bed and the bank under the side door
      // the bed where the Nautilus rests: flat sand all along her length, open water around her
      const bed = smoothstep(16, 7, Math.abs(z)) * smoothstep(48, 38, Math.abs(x));
      h = lerp(h, -2.5 + fbm2(x * 0.08, z * 0.08, 2) * 0.25, bed);
      const near = smoothstep(30, 14, Math.abs(z)) * smoothstep(60, 42, Math.abs(x));
      h = Math.min(h, lerp(h, -2.0 + Math.abs(z) * 0.08, near));
      h = lerp(h, -1.25, Math.exp(-((x + 19.3) ** 2) / 6 - ((z + 5.6) ** 2) / 4));
      return h;
    };
    this.hfn = hfn;
    const colorFn = (x, z, h, slope) => {
      const n = fbm2(x * 0.2, z * 0.2, 3);
      let c = [0.36 + n * 0.06, 0.35 + n * 0.06, 0.33 + n * 0.05];
      const weed = smoothstep(0.1, 0.35, fbm2(x * 0.08 + 9, z * 0.08, 3)) * smoothstep(-100, -130, z) * (1 - smoothstep(0.4, 0.7, slope));
      c = c.map((v, i) => lerp(v, [0.2, 0.24, 0.12][i], weed));
      const rk = smoothstep(0.3, 0.65, slope);
      c = c.map((v, i) => lerp(v, [0.2, 0.2, 0.21][i], rk));
      if (z < -240) c = c.map((v, i) => lerp(v, [0.44, 0.41, 0.36][i], 0.6)); // the old streets
      const vr = Math.hypot(x - CRATER.x, z - CRATER.z);
      c = c.map((v, i) => lerp(v, [0.15 + n * 0.05, 0.14 + n * 0.04, 0.14 + n * 0.04][i], smoothstep(88, 45, vr))); // basalt and ash
      c = c.map((v, i) => lerp(v, [0.42, 0.22, 0.13][i], smoothstep(16, 7, vr))); // the scorched lip
      return c;
    };
    // near terrain (fine) and the far city plain (coarse)
    this.terrain = new Terrain({ x0: -60, z0: -236, x1: 55, z1: 30, cell: 1.2, fn: hfn, colorFn, jitter: 0.24, seed: 9 });
    const tmesh = new THREE.Mesh(this.terrain.geometry, makeMaterial('M_terrain_rock', true));
    tmesh.receiveShadow = true; tmesh.castShadow = true; this.add(tmesh);
    g.world.addMesh(tmesh, 6);
    this.far = new Terrain({ x0: -170, z0: -470, x1: 170, z1: -230, cell: 3.0, fn: hfn, colorFn, jitter: 0.3, seed: 10 });
    const fmesh = new THREE.Mesh(this.far.geometry, makeMaterial('M_terrain_rock', true));
    fmesh.receiveShadow = true; fmesh.castShadow = true; this.add(fmesh);
    this.side = new Terrain({ x0: 53.8, z0: -236, x1: 150, z1: -130, cell: 2.4, fn: hfn, colorFn, jitter: 0.3, seed: 11 });
    const smesh = new THREE.Mesh(this.side.geometry, makeMaterial('M_terrain_rock', true));
    smesh.receiveShadow = true; smesh.castShadow = true; this.add(smesh);
    const ground = (x, z) => (z > -235 ? (x > 55 ? this.side.height(x, z) : this.terrain.height(x, z)) : this.far.height(x, z));
    this.groundFn = ground;
    const rnd = mulberry32(91);
    const place = (name, list, opts = {}) => { if (!list.length) return null; const grp = P.instanced(name, list, opts); this.add(grp); return grp; };
    const colliders = (name, list, geoOverride) => {
      const geo = geoOverride || P.geometry(name); if (!geo) return;
      for (const m of list) { const mesh = new THREE.Mesh(geo); mesh.matrixWorld.copy(m); mesh.matrixAutoUpdate = false; mesh.updateMatrixWorld = () => {}; g.world.addMesh(mesh, 6); }
    };
    // ---------------------------------------------------------------- stony plain with zoophytes and phosphorescent things
    const rocks = [[], [], [], [], [], []];
    for (let i = 0; i < 260; i++) {
      const z = -8 - rnd() * 110; const r = R.atZ(z); const off = (rnd() < 0.5 ? -1 : 1) * (1.5 + rnd() * 26);
      const x = r.x + off; rocks[Math.floor(rnd() * 6)].push(trs(x, ground(x, z) - 0.2, z, rnd() * 6.3, 0.3 + rnd() * (Math.abs(off) > 6 ? 2.2 : 0.7)));
    }
    rocks.forEach((l, i) => place('rock_' + i, l));
    // pennatules and medusae: tiny cold lights on the bottom
    const glowMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(0.25, 1.4, 1.1) });
    const pen = [];
    for (let i = 0; i < 380; i++) { const z = -6 - rnd() * 130; const r = R.atZ(z); const x = r.x + (rnd() - 0.5) * 40; pen.push(trs(x, ground(x, z) + 0.05, z, 0, 0.02 + rnd() * 0.03)); }
    const penMesh = new THREE.InstancedMesh(new THREE.SphereGeometry(1, 6, 4), glowMat, pen.length);
    pen.forEach((m, i) => penMesh.setMatrixAt(i, m)); this.add(penMesh); this.pennatules = penMesh; this.penBase = pen;
    // ---------------------------------------------------------------- the copse of dead trees on the mountain's flank
    const dead = [[], [], [], []];
    for (let i = 0; i < 230; i++) {
      const z = -112 - rnd() * 80; const r = R.atZ(z); const off = (rnd() < 0.5 ? -1 : 1) * (2.2 + rnd() * 24);
      const x = r.x + off; const y = ground(x, z);
      dead[Math.floor(rnd() * 4)].push(trs(x, y - 0.4, z, rnd() * 6.3, 0.9 + rnd() * 0.7, (rnd() - 0.5) * 0.25, (rnd() - 0.5) * 0.25));
    }
    // and on the ridges against the glow (the "fine black paper cuttings")
    for (let i = 0; i < 60; i++) { const x = (rnd() - 0.5) * 120, z = -150 - rnd() * 60; dead[i % 4].push(trs(x, ground(x, z) - 0.3, z, rnd() * 6, 1.2 + rnd() * 0.8)); }
    dead.forEach((l, i) => { place('deadtree_' + i, l, { shadow: true }); });
    const trunk = new THREE.CylinderGeometry(0.28, 0.34, 5, 6); trunk.translate(0, 2.5, 0);
    for (const l of dead) colliders(null, l.filter((m) => { const p = new THREE.Vector3().setFromMatrixPosition(m); return Math.abs(p.x - R.atZ(p.z).x) < 8; }), trunk);
    // boulders and steps along the climb
    const steps = [[], [], [], [], []];
    for (let s = R.atZ(-112).s; s < R.atZ(-205).s; s += 2.0) {
      const { p, dir } = R.at(s); for (const sd of [-1, 1]) { const nx = -dir.z * sd, nz = dir.x * sd; const d = 3.3 + rnd() * 1.5; const x = p.x + nx * d, z = p.z + nz * d; steps[Math.floor(rnd() * 5)].push(trs(x, ground(x, z) + 0.2, z, rnd() * 6, 0.8 + rnd() * 1.4)); }
    }
    steps.forEach((l, i) => { place('rock_' + i, l); colliders('rock_' + i, l); });
    // the trunk thrown across the abyss
    const lz = (CHASM_Z0 + CHASM_Z1) / 2, lr = R.atZ(lz);
    const logM = trs(lr.x, Math.max(ground(lr.x, CHASM_Z0 + 1.2), ground(lr.x, CHASM_Z1 - 1.2)) + 0.05, lz, Math.PI / 2, new THREE.Vector3(1.15, 1, 1.1));
    place('log_bridge', [logM]); colliders('log_bridge', [logM]);
    // a flat walking strip along the top of the trunk (narrow, but fair)
    const strip = new THREE.BoxGeometry(0.62, 0.1, 8.0); strip.translate(0, 0.27, 0);
    const sm = new THREE.Matrix4().compose(new THREE.Vector3().setFromMatrixPosition(logM), new THREE.Quaternion(), new THREE.Vector3(1, 1, 1));
    colliders(null, [sm], strip);
    this.logZ = lz;
    // giant crustacea in their holes, eyes shining in the dark
    this.beasts = [];
    for (const [z, side, name] of [[-188, -1, 'lobster_giant'], [-193, 1, 'crab_giant'], [-197, -1, 'crab_giant'], [-200, 1, 'lobster_giant'], [-146, 1, 'crab_giant']]) {
      const r = R.atZ(z); const x = r.x + side * 4.0; const m = P.mesh(name);
      m.position.set(x, ground(x, z) - 0.2, z); m.rotation.y = side > 0 ? -Math.PI / 2 : Math.PI / 2; m.scale.setScalar(name === 'crab_giant' ? 1.0 : 1.2);
      this.add(m); this.beasts.push({ m, t: rnd() * 10, clicked: false, base: m.rotation.y });
    }
    // ---------------------------------------------------------------- ruins on the first platform
    const plat = { cols: [], broken: [], drums: [], blocks: [] };
    for (let i = 0; i < 26; i++) {
      const z = -203 - rnd() * 16; const r = R.atZ(z); const x = r.x + (rnd() < 0.5 ? -1 : 1) * (3 + rnd() * 9);
      const y = ground(x, z); const k = rnd();
      if (k < 0.35) plat.broken.push(trs(x, y - 0.2, z, rnd() * 6, 0.5 + rnd() * 0.3));
      else if (k < 0.7) plat.drums.push(trs(x, y + 0.25, z, rnd() * 6, 0.5 + rnd() * 0.3, 0, (rnd() - 0.5) * 0.3));
      else plat.blocks.push(trs(x, y - 0.4, z, rnd() * 6, new THREE.Vector3(0.6 + rnd() * 0.4, 0.5 + rnd() * 0.6, 0.8)));
    }
    place('col_broken', plat.broken); place('col_drum', plat.drums); place('wall_block', plat.blocks);
    colliders('wall_block', plat.blocks);
    // ---------------------------------------------------------------- the basalt rock on the summit, and the chalk
    this.slab = P.mesh('basalt_slab');
    this.slab.position.set(SUMMIT.x - 3.0, ground(SUMMIT.x - 3.0, SUMMIT.z + 2.0) - 0.2, SUMMIT.z + 2.0); this.slab.rotation.y = -1.29;
    this.add(this.slab); this.slab.updateMatrixWorld(true);
    colliders('basalt_slab', [this.slab.matrixWorld.clone()]);
    const cv = document.createElement('canvas'); cv.width = 512; cv.height = 128;
    this.chalkCanvas = cv; this.chalkTex = new THREE.CanvasTexture(cv); this.chalkTex.colorSpace = THREE.SRGBColorSpace;
    const chalk = new THREE.Mesh(new THREE.PlaneGeometry(1.9, 0.48), patchMat(new THREE.MeshStandardMaterial({ map: this.chalkTex, transparent: true, roughness: 1, depthWrite: false })));
    chalk.position.set(0, 1.25, -0.37); chalk.rotation.y = Math.PI; this.slab.add(chalk);
    this.chalkProgress = 0;
    // ---------------------------------------------------------------- the volcano: crater, lava cascades, stones and scoriae
    const white = (geo) => { geo.setAttribute('color', new THREE.BufferAttribute(new Float32Array(geo.attributes.position.count * 3).fill(1), 3)); return geo; };
    const lavaTex = tex('lava_c', { repeat: 1 });
    this.lavaMat = new THREE.MeshBasicMaterial({ map: lavaTex, color: new THREE.Color(6.5, 2.1, 0.45) });
    const pool = new THREE.Mesh(new THREE.CircleGeometry(5, 18), this.lavaMat); pool.rotation.x = -Math.PI / 2; pool.position.copy(CRATER).add(new THREE.Vector3(0, -0.8, 0)); this.add(pool);
    // cascades: ribbons draped down the flank towards the plain of the city
    this.lavaFlows = [];
    { const c = document.createElement('canvas'); c.width = 64; c.height = 4; const x = c.getContext('2d');
      const gr = x.createLinearGradient(0, 0, 64, 0); gr.addColorStop(0, 'rgba(255,255,255,0)'); gr.addColorStop(0.5, 'rgba(255,255,255,1)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
      x.fillStyle = gr; x.fillRect(0, 0, 64, 4);
      this.lavaGlowMat = new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(c), color: new THREE.Color(1.3, 0.38, 0.08), transparent: true, opacity: 0.45, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide }); }
    for (const [ang, len, W0] of [[-2.25, 62, 2.4], [-1.6, 110, 3.0], [-1.2, 95, 2.6], [-0.8, 75, 2.0]]) {
      const pts = []; const W = W0;
      for (let i = 0; i <= 40; i++) {
        const t = i / 40;
        const r = 6 + t * len;
        const x = CRATER.x + Math.cos(ang + Math.sin(t * 5) * 0.08) * r, z = CRATER.z + Math.sin(ang + Math.sin(t * 5) * 0.08) * r;
        pts.push(new THREE.Vector3(x, ground(x, z) + 0.35 + (r < 9 ? 0.4 : 0), z));
      }
      const pos = [], uv = [];
      for (let i = 0; i < pts.length; i++) {
        const a = pts[i], b = pts[Math.min(i + 1, pts.length - 1)];
        const d = new THREE.Vector3().subVectors(b, a); d.y = 0; d.normalize(); const wv = W * (0.75 + 0.5 * fbm2(i * 0.3, ang * 7, 2)) * (i / pts.length < 0.6 ? 1 - i / pts.length * 0.5 : 0.7 + (i / pts.length - 0.6) * 2.2); const sx = -d.z * wv, sz = d.x * wv;
        pos.push(a.x - sx, a.y, a.z - sz, a.x + sx, a.y, a.z + sz); uv.push(0, i / 6, 1, i / 6);
      }
      const idx = []; for (let i = 0; i < pts.length - 1; i++) { const k = i * 2; idx.push(k, k + 1, k + 2, k + 1, k + 3, k + 2); }
      const geo = new THREE.BufferGeometry(); geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); geo.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2)); geo.setIndex(idx);
      const m = new THREE.Mesh(geo, this.lavaMat); this.add(m); this.lavaFlows.push(m);
      // the heat of the torrent: a soft skirt of light on the rock either side
      const gpos = [];
      for (let i = 0; i < pts.length; i++) { const k = i * 6; const ax = pos[k], ay = pos[k + 1], az = pos[k + 2], bx = pos[k + 3], by = pos[k + 4], bz = pos[k + 5];
        const cx = (ax + bx) / 2, cz = (az + bz) / 2, ex = (bx - ax) * 2.2, ez = (bz - az) * 2.2;
        gpos.push(cx - ex, Math.min(ay, by) + 0.5, cz - ez, cx + ex, Math.max(ay, by) + 0.5, cz + ez); }
      const gg = new THREE.BufferGeometry(); gg.setAttribute('position', new THREE.Float32BufferAttribute(gpos, 3)); gg.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2)); gg.setIndex(idx);
      this.add(new THREE.Mesh(gg, this.lavaGlowMat));
    }
    // the fountain of fire above the crater: a column of incandescent lava, flung stones
    this.fountain = new THREE.Mesh(new THREE.CylinderGeometry(0.9, 2.6, 16, 10, 1, true), new THREE.MeshBasicMaterial({ color: new THREE.Color(4.2, 1.3, 0.3), transparent: true, opacity: 0.7, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide }));
    this.fountain.position.copy(CRATER).add(new THREE.Vector3(0, 8, 0)); this.add(this.fountain);
    // the glow of the crater seen through two miles of water: a soft halo that the ridge cuts
    const gc = document.createElement('canvas'); gc.width = gc.height = 128; const gx = gc.getContext('2d');
    const grd = gx.createRadialGradient(64, 64, 0, 64, 64, 64); grd.addColorStop(0, 'rgba(255,255,255,1)'); grd.addColorStop(0.25, 'rgba(255,255,255,0.45)'); grd.addColorStop(1, 'rgba(255,255,255,0)');
    gx.fillStyle = grd; gx.fillRect(0, 0, 128, 128);
    const gtex = new THREE.CanvasTexture(gc);
    this.halo = new THREE.Sprite(new THREE.SpriteMaterial({ map: gtex, color: new THREE.Color(3.2, 1.1, 0.35), transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
    this.halo.position.copy(CRATER).add(new THREE.Vector3(0, 6, 0)); this.halo.scale.setScalar(70); this.add(this.halo);
    const NS = 160; const sg = new THREE.BufferGeometry(); sg.setAttribute('position', new THREE.BufferAttribute(new Float32Array(NS * 3), 3));
    this.scoria = new THREE.Points(sg, new THREE.PointsMaterial({ color: new THREE.Color(3.5, 1.2, 0.35), size: 0.9, sizeAttenuation: true, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
    this.scoria.frustumCulled = false; this.add(this.scoria);
    this.scoriaS = Array.from({ length: NS }, () => ({ p: CRATER.clone(), v: new THREE.Vector3(), life: Math.random() * 6 }));
    // ---------------------------------------------------------------- Atlantis: a town, its temples, an acropolis, an aqueduct, a quay
    const city = { cols: [], broken: [], broken2: [], drums: [], bases: [], ent: [], ped: [], walls: [], aq: [], stairs: [] };
    const temple = (cx, cz, yaw, sc, ruined) => {
      const y = ground(cx, cz);
      city.bases.push(trs(cx, y - 0.3, cz, yaw, sc));
      const cos = Math.cos(yaw), sin = Math.sin(yaw);
      for (let i = 0; i < 6; i++) for (const side of [-1, 1]) {
        const lx = (-5 + i * 2) * sc, lz = side * 2.6 * sc;
        const x = cx + lx * cos + lz * sin, z = cz - lx * sin + lz * cos;
        const k = rnd();
        if (ruined && k < 0.35) { city.drums.push(trs(x + (rnd() - 0.5) * 3, y + 0.4, z + (rnd() - 0.5) * 3, rnd() * 6, sc * 0.9, 0, (rnd() - 0.5) * 0.4)); continue; }
        if (ruined && k < 0.6) { (rnd() < 0.5 ? city.broken : city.broken2).push(trs(x, y + 1.05 * sc, z, rnd() * 6, sc)); continue; }
        city.cols.push(trs(x, y + 1.05 * sc, z, 0, sc));
      }
      if (!ruined || rnd() < 0.5) { for (const side of [-1, 1]) city.ent.push(trs(cx + side * 2.6 * sc * sin, y + 1.05 * sc + 5.45 * sc, cz + side * 2.6 * sc * cos, yaw, new THREE.Vector3(sc * 0.95, sc, sc * 0.6))); }
      city.ped.push(trs(cx + 7 * sc * cos, y + 0.2, cz - 7 * sc * sin, yaw + 0.3, sc, 1.3, 0));
    };
    // acropolis with the floating outline of a Parthenon
    const ax = -32, az = -330;
    temple(ax, az, 0.25, 1.35, false);
    for (let i = 0; i < 4; i++) city.stairs.push(trs(ax + 9 * Math.cos(0.25), ground(ax + 9, az) - 0.2, az - 9 * Math.sin(0.25) + i * 0.1, 0.25 + Math.PI / 2, 1.5));
    temple(-2, -306, -0.4, 1.0, true); temple(-6, -365, 0.9, 1.1, true); temple(40, -350, 0.1, 0.9, true); temple(-62, -290, -0.2, 0.9, true);
    // long lines of sunken walls and broad deserted streets
    for (let r = 0; r < 9; r++) for (let k = 0; k < 14; k++) {
      if (rnd() < 0.35) continue;
      const x = -90 + k * 13 + (rnd() - 0.5) * 3, z = -270 - r * 18 + (rnd() - 0.5) * 3;
      if (Math.hypot(x - ax, z - az) < 18 || Math.hypot(x - CRATER.x, z - CRATER.z) < 92) continue;
      city.walls.push(trs(x, ground(x, z) - 0.6, z, (r % 2) * Math.PI / 2 + (rnd() - 0.5) * 0.2, new THREE.Vector3(1 + rnd() * 1.2, 0.6 + rnd() * 1.2, 1)));
      if (rnd() < 0.25) city.drums.push(trs(x + 4, ground(x + 4, z + 3) + 0.4, z + 3, rnd() * 6, 0.9, 0, 1.4));
    }
    // remains of a gigantic aqueduct
    for (let k = 0; k < 9; k++) {
      const x = 60 - k * 9.5, z = -395 + k * 2.2;
      if (k === 3 || k === 6) continue;
      city.aq.push(trs(x, ground(x, z) - 0.5, z, 0.23, 1.25));
    }
    // traces of a quay, where an ancient port abutted the ocean
    for (let k = 0; k < 18; k++) { const x = -110 + k * 8.5, z = -440; city.walls.push(trs(x, ground(x, z) - 0.3, z, 0, new THREE.Vector3(2.1, 0.7, 1.6))); }
    place('col_tuscan', city.cols); place('col_broken', city.broken); place('col_broken2', city.broken2); place('col_drum', city.drums);
    place('temple_base', city.bases); place('entablature', city.ent); place('pediment', city.ped); place('wall_block', city.walls);
    place('aqueduct', city.aq); place('stairs', city.stairs);
    // seaweed mantles on the ruins
    const weeds = [];
    for (let i = 0; i < 160; i++) { const x = -100 + rnd() * 180, z = -260 - rnd() * 180; weeds.push(trs(x, ground(x, z), z, rnd() * 6, new THREE.Vector3(0.8, 0.4 + rnd() * 0.6, 0.8))); }
    place('fucus', weeds, { shadow: false });
    // ---------------------------------------------------------------- the volcano's light
    this.nautilusPlace();
  }
  nautilusPlace() { this.g.nautilus.place(new THREE.Vector3(0, 0, 0), 0); }

  reset() {
    const g = this.g, n = g.nautilus;
    this.nautilusPlace();
    n.state.ceiling = 1; n.state.ceilingVis = 1; n.state.panels = 0; n.state.panelsTarget = 0; n.state.clockHours = 23; n.state.speed = 0;
    n.state.interiorPower = 0.65; // night lighting aboard
    n.outside.brightness = 0.12; n.outside.color.setRGB(0.6, 0.7, 0.85);
    g.crowd.divers.length = 0; g.intCrowd.divers.length = 0; g.crowd.shrouds.length = 0;
    this.nemo = new Diver({ name: 'nemo', held: 'diver_stick', lamp: null });
    this.nemo.lampOn = null;
    g.intCrowd.add(this.nemo);
    this.nemo.pos.copy(n.toWorld(b2t(-18.6, 1.4, 0))); this.nemo.yaw = Math.PI * 0.5;
    this.nemoState = 'wardrobe';
    this.phase = 'aboard'; this.t = 0; this.triggers = {}; this.rain = 0; this.tremorT = 18; this.moon = 0; this.reveal = 0;
    this.chalkProgress = 0; this.drawChalk(0);
    this.procession = null;
    g.player.teleport(n.toWorld(b2t(19.75, -0.55, 0)), 0.39, -0.3);
    // the volcano's two lights: one floods the plain of the city, one throws rays back over the ridge
    const A = g.volA, B = g.volB;
    A.position.copy(CRATER).add(new THREE.Vector3(0, 10, 0)); A.target.position.set(-10, -60, -340); A.angle = 1.05; A.penumbra = 0.8;
    B.position.copy(CRATER).add(new THREE.Vector3(0, 12, 0)); B.target.position.set(-12, 10, -60); B.angle = 0.62; B.penumbra = 0.5;
    A.target.updateMatrixWorld(); B.target.updateMatrixWorld();
    A.intensity = 0; B.intensity = 0; A.userData.volumetric = 0.12; B.userData.volumetric = 1.3;
    B.shadow.autoUpdate = false; B.shadow.needsUpdate = true;
  }

  start() {
    const g = this.g;
    g.pipe.finalMat.uniforms.uFade.value = 1; g.fadeTo(0, 3);
    setTimeout(() => bus.emit('say', 'That night, about eleven o’clock, I received a most unexpected visit. He had gone, but left these lines.'), 1500);
    g.ui.objective('Read the note on the writing table.');
  }
  readNote() {
    const g = this.g; g.modal = true;
    g.ui.showNote({
      head: 'Eleven o’clock at night',
      body: 'M. Aronnax —\nYou have hitherto only visited the submarine depths by daylight, under the brightness of the sun. Would it suit you to see them in the darkness of the night?\n\nI warn you, the way will be tiring. We shall have far to walk, and must climb a mountain. The roads are not well kept.',
      sign: '— N.',
    }).then(() => {
      g.modal = false;
      if (!this.triggers.note) { this.triggers.note = 1; bus.emit('say', 'What he said only heightened my curiosity. Neither Ned nor Conseil was to follow us.'); g.ui.objective('Go aft to the robing-room.'); }
    });
  }
  nemoInCell() { return this.nemoState === 'waitingCell'; }
  onSuited() { this.g.ui.objective('Step into the cell.'); this.nemoState = 'toCell'; }
  onLockClosed() { this.g.ui.objective('Turn the tap.'); }
  onOuterOpen() { this.nemoState = 'exiting'; }
  onOutside() {
    const g = this.g;
    bus.emit('say', 'We set foot on the bottom of the Atlantic at a depth of 150 fathoms. Midnight was near. The waters were profoundly dark.');
    this.phase = 'walk';
    this.procession = new Procession(this.route, [this.nemo], { speed: 0.78, gap: 1.5, wait: 12 });
    this.procession.s = this.route.project(g.player.pos.x, g.player.pos.z).s + 5;
    this.procession.target = this.route.atZ(SUMMIT.z + 1.5).s;
    setTimeout(() => bus.emit('say', 'Captain Nemo pointed out in the distance a reddish spot, a sort of large light shining brilliantly about two miles from the Nautilus.'), 6000);
    g.ui.objective('Follow the Captain towards the red light.');
  }
  interactables() { return []; }
  onInteract() { return false; }
  ground(x, z) { return this.groundFn ? this.groundFn(x, z) : 0; }
  volumetricSpots() { return [this.g.volB, this.g.volA]; }
  audioEnv(water) {
    const p = this.g.player.pos;
    const dv = p.distanceTo(CRATER);
    return { reef: 0, rain: water ? this.rain : 0, volcano: clamp(1 - dv / 260, 0, 1) * (water ? 1 : 0.3) + (this.shake || 0) * 0.5, nearHull: water ? clamp(1 - Math.hypot(p.x, p.z) / 40, 0, 1) : 0 };
  }

  drawChalk(k) {
    const c = this.chalkCanvas.getContext('2d');
    c.clearRect(0, 0, 512, 128);
    c.font = '600 92px "EB Garamond", Georgia, serif'; c.textAlign = 'left'; c.textBaseline = 'middle';
    const word = 'ATLANTIS'; const w = c.measureText(word).width; const x0 = (512 - w) / 2;
    c.save(); c.beginPath(); c.rect(0, 0, x0 + w * k, 128); c.clip();
    c.fillStyle = 'rgba(235,232,222,0.92)';
    for (let i = 0; i < 3; i++) { c.globalAlpha = 0.45; c.fillText(word, x0 + (Math.random() - 0.5) * 2, 68 + (Math.random() - 0.5) * 2); }
    c.restore();
    this.chalkTex.needsUpdate = true;
  }

  update(dt, title) {
    const g = this.g, n = g.nautilus, P = g.player;
    this.t += dt;
    // the volcano breathes: its light swells with the eruption
    const flick = 0.85 + 0.1 * Math.sin(this.t * 0.7) + 0.06 * Math.sin(this.t * 2.3) + 0.04 * Math.sin(this.t * 7.1);
    const surge = this.surge || 0;
    g.volA.intensity = 1100000 * flick * (1 + surge * 0.8);
    g.crewLights[0].position.copy(CRATER).add(new THREE.Vector3(-4, 16, 4)); g.crewLights[0].intensity = 14000 * flick * (1 + surge); g.crewLights[0].color.setRGB(1, 0.45, 0.18); g.crewLights[0].userData.volumetric = 0.12;
    g.crewLights[1].position.set(CRATER.x - 22, -6, CRATER.z - 70); g.crewLights[1].intensity = 16000 * flick; g.crewLights[1].color.setRGB(1, 0.4, 0.15); g.crewLights[1].userData.volumetric = 0.1;
    g.volB.intensity = 260000 * flick * (1 + surge * 0.6);
    g.volA.color.setRGB(1.0, 0.42 + 0.05 * flick, 0.16);
    g.volB.color.setRGB(1.0, 0.36, 0.12);
    this.surge = Math.max(0, surge - dt * 0.4);
    if (this.lavaMat.map) { this.lavaMat.map.offset.y -= dt * 0.05; this.lavaMat.map.offset.x = Math.sin(this.t * 0.1) * 0.05; }
    this.fountain.scale.set(1 + Math.sin(this.t * 3) * 0.05, 0.85 + 0.25 * Math.abs(Math.sin(this.t * 0.9)) + surge * 0.4, 1);
    this.fountain.material.opacity = 0.55 + 0.2 * Math.sin(this.t * 5);
    if (this.halo) this.halo.material.color.setRGB(2.4, 0.8, 0.25).multiplyScalar(flick * (1 + surge * 0.5) * lerp(0.15, 1, smoothstep(50, 170, g.camera.position.distanceTo(CRATER))));
    g.pipe.volMat.uniforms.uMaxDist.value = 240;
    // light scattered many times in the water: the glow over the ridge warms the dark flank as we climb
    { const warm = smoothstep(-110, -215, g.camera.position.z) * (0.85 + 0.15 * flick);
      const ch = Math.exp(-(((g.camera.position.z + 181) / 12) ** 2)) * 0.5;
      UW.uniforms.uAmbFloorColor.value.set(lerp(0.04, 0.095, warm) * (1 + ch), lerp(0.05, 0.052, warm) * (1 + ch * 0.8), lerp(0.065, 0.045, warm) * (1 + ch * 0.6)); }
    // a rain of stones and scoriae
    const a = this.scoria.geometry.attributes.position;
    this.scoriaS.forEach((s, i) => {
      s.life -= dt;
      if (s.life <= 0) { s.p.copy(CRATER).add(new THREE.Vector3((Math.random() - 0.5) * 3, 2, (Math.random() - 0.5) * 3)); s.v.set((Math.random() - 0.5) * 10, 10 + Math.random() * 14, (Math.random() - 0.5) * 10); s.life = 3 + Math.random() * 4; }
      s.v.y -= 6 * dt; s.v.multiplyScalar(Math.exp(-dt * 0.6)); s.p.addScaledVector(s.v, dt);
      a.setXYZ(i, s.p.x, s.p.y, s.p.z);
    });
    a.needsUpdate = true;
    // pennatules pulse
    g.pipe.gradeMat.uniforms.uSat.value = g.headMedium === 'water' ? 0.78 : 0.8;
    const dCrater = g.camera.position.distanceTo(CRATER);
    g.pipe.gradeMat.uniforms.uExposure.value = g.headMedium === 'water' ? lerp(0.95, 1.5, smoothstep(60, 200, dCrater)) : 1.0;
    g.pipe.compMat.uniforms.uFogGain.value = 0.11;
    // moonlight at the end
    const U = UW.uniforms;
    U.uSunColor.value.set(0.16, 0.2, 0.26).multiplyScalar(this.moon * 4.0);
    U.uKd.value.set(lerp(0.08, 0.03, this.moon), lerp(0.04, 0.009, this.moon), lerp(0.03, 0.006, this.moon));
    U.uAmbTop.value.set(0.02, 0.03, 0.045).multiplyScalar(this.moon);
    this.sunOn = this.moon > 0.01;
    if (this.sunOn) {
      const c = SUMMIT.clone(); g.sun.position.copy(c).addScaledVector(U.uSunDir.value, -80); g.sun.target.position.copy(c); g.sun.target.updateMatrixWorld();
      g.sun.shadow.autoUpdate = false; if (!this.moonShadow) { this.moonShadow = 1; g.sun.shadow.needsUpdate = true; }
    }
    if (title) return;
    if (this.t < 1.5) g.volB.shadow.needsUpdate = true;
    this.updateNemoAboard(dt);
    if (this.procession) {
      const pr = this.route.project(P.pos.x, P.pos.z);
      this.procession.update(dt, pr.s);
      if (this.procession.waiting && this.phase === 'walk') { this.nemo.setPose('beckon'); this.nemo.lookAt = P.pos; } else if (this.phase === 'walk') { this.nemo.setPose('stand'); this.nemo.lookAt = null; }
      const z = P.pos.z;
      // rain on the surface, far above
      if (this.t > 0 && z < -14) this.rain = Math.min(1, this.rain + dt * 0.05);
      this.beat('rain', z < -22, 'I heard a kind of pattering above my head. It was rain falling violently, and crisping the surface of the waves. By the water! in the midst of the water! I could not help laughing.');
      this.beat('phos', z < -52, 'Medusae, microscopic crustacea and pennatules lit the stony soil slightly with their phosphorescent gleam.');
      this.beat('lantern', z < -80, 'In turning round, I could still see the whitish lantern of the Nautilus beginning to pale in the distance.');
      this.beat('rays', z < -100, 'The white glimmer came in rays from the summit of a mountain. The source of this inexplicable light was a fire on the opposite side.');
      this.beat('copse', z < -122, 'A copse of dead trees, without leaves, without sap, petrified by the action of the water; their branches, like fine black paper cuttings, showed distinctly on the watery ceiling.');
      this.beat('crevice', z < CREVICE_Z + 4, 'Now I jumped a crevice, the depth of which would have made me hesitate had it been among the glaciers on the land.');
      if (z < CREVICE_Z + 4 && z > CREVICE_Z - 2 && !this.triggers.hopHint) { this.triggers.hopHint = 1; g.ui.objective('Jump the crevice (Space).'); }
      this.beat('log', z < CHASM_Z0 + 3, 'Now I ventured on the unsteady trunk of a tree thrown across from one abyss to the other, without looking under my feet.');
      this.beat('beasts', z < -186, 'Millions of luminous spots shone in the darkness. They were the eyes of giant crustacea crouched in their holes.');
      this.beat('ruins', z < -203, 'Before us lay some picturesque ruins, which betrayed the hand of man and not that of the Creator. Where was I?');
      if (z < -203 && !this.triggers.come) { this.triggers.come = 1; setTimeout(() => bus.emit('say', 'He shook his head, and pointing to the highest point of the mountain, he seemed to say: “Come, come along; come higher!”'), 6000); }
      // crustacea click their claws as we pass
      for (const b of this.beasts) {
        b.t += dt; b.m.rotation.y = b.base + Math.sin(b.t * 0.6) * 0.08;
        const d = b.m.position.distanceTo(P.pos);
        if (d < 6 && !b.clicked) { b.clicked = true; g.audio.sfx('claws', b.m.position); this.stress = Math.min(1, this.stress + 0.5); }
        if (d > 10) b.clicked = false;
      }
      // a false step into the crevice or the abyss: the captain's hand brings you back
      const ry = this.route.atZ(z).y;
      if (P.onGround && Math.abs(P.pos.y - ry) < 1.2 && pr.d < 4) { this.safeT = (this.safeT || 0) + dt; if (this.safeT > 0.8) { this.lastSafe = P.pos.clone(); this.safeT = 0; } }
      if (P.pos.y < ry - 2.6) { this.fallT = (this.fallT || 0) + dt; } else this.fallT = 0;
      if (this.fallT > 2.2 && this.lastSafe && !this.respawning) {
        this.respawning = true;
        g.fadeTo(1, 0.8).then(() => {
          P.teleport(this.lastSafe.clone(), P.yaw, 0);
          this.procession.s = Math.max(this.procession.s, this.route.project(P.pos.x, P.pos.z).s + 3);
          bus.emit('say', 'A false step would have been dangerous. Captain Nemo’s strong hand hauled me back onto the path.');
          g.fadeTo(0, 1.0).then(() => { this.respawning = false; this.fallT = 0; });
        });
      }
      // the summit and the revelation
      if (this.phase === 'walk' && P.pos.distanceTo(SUMMIT) < 7 && this.procession.s >= this.procession.target - 1) this.beginSummit();
    }
    if (this.phase === 'summit') this.updateSummit(dt);
    // tremors from the bubbling of the mountain
    this.tremorT -= dt;
    if (this.tremorT <= 0 && this.phase !== 'aboard') {
      this.tremorT = 22 + Math.random() * 20;
      const near = clamp(1 - P.pos.distanceTo(CRATER) / 250, 0.2, 1);
      g.audio.sfx('tremor', CRATER, { ref: 200 }); P.shake = 0.8 * near; this.surge = 1; this.shake = 1;
      if (near > 0.5) setTimeout(() => g.audio.sfx('rockfall', P.pos.clone().add(new THREE.Vector3(6, 4, -5))), 1200);
    }
    this.shake = Math.max(0, (this.shake || 0) - dt * 0.3);
    this.stress = Math.max(0, this.stress - dt * 0.08);
    // the stick taps the rocks
    if (P.medium === 'water' && P.onGround && Math.hypot(P.vel.x, P.vel.z) > 0.4 && Math.random() < dt * 0.6 && g.seq.stick) g.audio.sfx('stick', P.pos);
  }
  beat(key, cond, text) { if (cond && !this.triggers[key]) { this.triggers[key] = 1; bus.emit('say', text); } }

  updateNemoAboard(dt) {
    const g = this.g, n = g.nautilus, d = this.nemo;
    if (!d) return;
    d.hold = this.nemoState !== 'outside';
    const goTo = (local, speed = 0.8) => {
      const t = n.toWorld(local); const dx = t.x - d.pos.x, dz = t.z - d.pos.z; const dist = Math.hypot(dx, dz);
      if (dist > 0.05) { const mv = Math.min(dist, speed * dt); d.pos.x += dx / dist * mv; d.pos.z += dz / dist * mv; d.speed = 0.7; d.yaw += Math.atan2(Math.sin(Math.atan2(dx, dz) - d.yaw), Math.cos(Math.atan2(dx, dz) - d.yaw)) * Math.min(1, dt * 3); }
      else d.speed = 0;
      return dist < 0.06;
    };
    if (this.nemoState === 'wardrobe') { d.lookAt = g.player.pos; if (g.player.pos.distanceTo(d.pos) < 3.5 && !this.triggers.nemoGreet) { this.triggers.nemoGreet = 1; bus.emit('say', 'They placed on our backs the reservoirs, abundantly filled with air, but no electric lamps were prepared. “They will be useless,” he replied.'); g.ui.objective('Put on the diving dress.'); } }
    if (this.nemoState === 'toCell') { if (goTo(b2t(-19.3, 1.4, 0))) this.nemoState = 'toCell2'; }
    if (this.nemoState === 'toCell2') { if (goTo(b2t(-19.6, 3.0, 0))) { this.nemoState = 'waitingCell'; d.yaw = Math.PI; } }
    if (this.nemoState === 'waitingCell') { d.lookAt = g.player.pos; if (g.inCell() && g.seq.lock === 'open' && !this.triggers.closeHint) { this.triggers.closeHint = 1; g.ui.objective('Close the watertight door.'); } }
    if (this.nemoState === 'exiting') { if (goTo(b2t(-19.3, 4.6, 0), 0.6)) this.nemoState = 'drop'; }
    if (this.nemoState === 'drop') { const i = g.intCrowd.divers.indexOf(d); if (i >= 0) g.intCrowd.divers.splice(i, 1); g.crowd.add(d); this.nemoState = 'outside'; d.pos.set(-19.3, 0, -6.2); d.yaw = Math.PI; }
    if (this.nemoState !== 'outside') d.pos.y = 0;
  }

  beginSummit() {
    const g = this.g;
    this.phase = 'summit'; this.st = 0;
    this.procession.stopped = true;
    g.audio.pad(true, 6);
    bus.emit('say', 'I looked down the side we had just climbed. On the opposite side my eyes ranged far over a large space lit by a violent fulguration. In fact, the mountain was a volcano.', 9);
    g.ui.objective('Step to the brink.');
    this.edge = false;
  }
  updateSummit(dt) {
    const g = this.g, d = this.nemo, P = g.player;
    // the revelation waits for Aronnax to stand at the brink (or for a patient reader)
    if (!this.edge) {
      this.edgeWait = (this.edgeWait || 0) + dt;
      if (P.pos.z < SUMMIT.z + 1.2 || this.edgeWait > 30) { this.edge = true; g.ui.objective(''); }
      const tg = new THREE.Vector3(SUMMIT.x + 1.6, 0, SUMMIT.z - 0.4); const dx = tg.x - d.pos.x, dz = tg.z - d.pos.z, dist = Math.hypot(dx, dz);
      if (dist > 0.1) { const mv = Math.min(dist, 0.5 * dt); d.pos.x += dx / dist * mv; d.pos.z += dz / dist * mv; d.speed = 0.5; d.yaw = Math.atan2(dx, dz); } else { d.speed = 0; d.lookAt = new THREE.Vector3(-20, -20, -320); }
      if (this.st > 1) return;
    }
    this.st += dt;
    const at = (t) => this.st > t && this.st - dt <= t;
    if (at(10)) bus.emit('say', 'There indeed under my eyes, ruined, destroyed, lay a town: its roofs open to the sky, its temples fallen, its arches dislocated, its columns lying on the ground.', 9);
    if (at(19)) bus.emit('say', 'Further on, some remains of a gigantic aqueduct; here the high base of an Acropolis, with the floating outline of a Parthenon; there traces of a quay. A perfect Pompeii escaped beneath the waters.', 10);
    if (at(25)) { this.writing = true; }
    if (this.writing) {
      // the captain walks to the black basalt and traces one word
      const tgt = this.slab.localToWorld(new THREE.Vector3(0, 0, -1.2));
      const dx = tgt.x - d.pos.x, dz = tgt.z - d.pos.z, dist = Math.hypot(dx, dz);
      if (dist > 0.1) { const mv = Math.min(dist, 0.6 * dt); d.pos.x += dx / dist * mv; d.pos.z += dz / dist * mv; d.speed = 0.6; d.yaw = Math.atan2(dx, dz); }
      else {
        d.speed = 0; d.yaw = this.slab.rotation.y; d.setPose('write');
        if (this.chalkProgress < 1) {
          this.chalkProgress = Math.min(1, this.chalkProgress + dt / 7);
          if (Math.random() < dt * 5) g.audio.sfx('chalk', this.slab.position);
          this.drawChalk(this.chalkProgress);
          if (this.chalkProgress >= 1) { d.setPose('stand'); bus.emit('say', 'ATLANTIS. What a light shot through my mind! The Atlantis of Plato, that continent denied by Origen and Humboldt. I had it there before my eyes.', 9); this.writing = false; this.wroteAt = this.st; g.ui.objective('Look out over the drowned city. Take your time.'); }
        }
      }
    }
    if (this.wroteAt && at(this.wroteAt + 12)) { d.setPose('lean'); d.lookAt = new THREE.Vector3(-10, -40, -330); bus.emit('say', 'Captain Nemo remained motionless, as if petrified in mute ecstasy, leaning on a mossy stone. What would I not have given to know his thoughts!', 9); }
    if (this.wroteAt && this.st > this.wroteAt + 24) {
      this.moon = Math.min(1, this.moon + dt / 10);
      if (!this.triggers.moon) { this.triggers.moon = 1; bus.emit('say', 'At this moment the moon appeared through the mass of waters and threw her pale rays on the buried continent. It was but a gleam, but what an indescribable effect!', 9); }
    }
    if (this.wroteAt && at(this.wroteAt + 44)) { d.setPose('stand'); d.lookAt = null; bus.emit('say', 'The Captain rose, cast one last look on the immense plain, and then bade me follow him.', 6); }
    if (this.wroteAt && at(this.wroteAt + 52)) this.finish();
  }
  finish() {
    const g = this.g;
    g.audio.pad(false, 4);
    g.fadeTo(1, 4).then(() => {
      g.mode = 'end'; if (document.pointerLockElement) document.exitPointerLock();
      g.ui.showEnd({
        title: 'A Vanished Continent',
        lines: [
          'Thus, led by the strangest destiny, I was treading under foot the mountains of this continent, touching with my hand those ruins a thousand generations old.',
          'We descended the mountain rapidly, and the mineral forest once passed, I saw the lantern of the Nautilus shining like a star.',
          'We got on board as the first rays of light whitened the surface of the ocean.',
        ],
        cite: 'Part II, chapter IX',
      });
    });
  }
  dispose() {
    for (const o of this.objs) this.g.ext.remove(o);
    this.objs.length = 0;
    this.g.volA.intensity = 0; this.g.volB.intensity = 0;
    this.g.crewLights.forEach((l) => { l.intensity = 0; l.color.setRGB(0.9, 0.93, 1); });
  }
}

function patchMat(m) { return patchUnderwater(m); }
