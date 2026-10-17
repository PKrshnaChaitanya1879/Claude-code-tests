// Excursion I — The Coral Kingdom (Part I, ch. XXIII), with the vertical forest of ch. XVI.
// From the Nautilus resting on the bottom at thirty feet, down a slight declivity to fifteen fathoms
// through the coral kingdom, into a dark gallery down to a hundred yards, to the immense forest of
// petrified trees at three hundred yards, and the glade where the crew bury their companion.
import * as THREE from 'three';
import { UW, depthAt, patchUnderwater } from './uw.js';
import { Terrain } from './terrain.js';
import { Route, Procession } from './path.js';
import { fbm2, ridge2, mulberry32, smoothstep, clamp, lerp } from './noise.js';
import { makeMaterial } from './materials.js';
import { trs } from './props.js';
import { Diver } from './npc.js';
import { FishSchool, Medusae, Polyps } from './life.js';
import { b2t } from './nautilus.js';
import { bus } from './bus.js';

const WAY = [
  [-19.3, 8, -2.45], [-19.3, -5.4, -1.25], [-18, -14, -2.6], [-13, -30, -5.0], [-9, -48, -8.0], [-12, -66, -11.0],
  [-5, -86, -14.5], [3, -106, -18.0], [6, -125, -21.0], [5, -145, -24.5], [3, -165, -28.5], [-4, -185, -33.5],
  [-8, -205, -39.0], [-10, -225, -45.0], [-9, -245, -50.5], [-7, -262, -53.5], [-6, -280, -54.0], [-6, -300, -54.2],
];
const GLADE = new THREE.Vector3(-6, -54.0, -281);

export class MissionCoral {
  constructor(game) {
    this.g = game; this.objs = []; this.ia = [];
    this.hullDepth = 9; this.outsideAtm = 1.9; this.cullDistance = 75; this.needs = 'lamp'; this.sunOn = true; this.glow = 0;
    this.current = new THREE.Vector3(0.05, 0.0, -0.02);
    this.stress = 0; this.reusable = true;
  }
  add(o) { this.g.ext.add(o); this.objs.push(o); return o; }
  wants(k) { return ['suit', 'tank', 'lamp', 'helmet'].includes(k); }

  async build() {
    const g = this.g, P = g.props;
    // water: clear tropical shallows, the depth scale stretches the long descent to 300 yards
    const U = UW.uniforms;
    U.uDepthBase.value = 9; U.uYRef.value = -1.25; U.uDepthScale.value = 0.8; U.uDepthQuad.value = 0.0761;
    U.uSigmaA.value.set(0.08, 0.036, 0.026); U.uSigmaS.value.set(0.026, 0.031, 0.035);
    U.uKd.value.set(0.05, 0.028, 0.019);
    U.uSunDir.value.set(0.42, -0.86, 0.28).normalize();
    U.uSunColor.value.set(3.3, 3.2, 3.0); U.uAmbTop.value.set(1.15, 1.45, 1.65); U.uAmbFloor.value = 0.0;
    U.uCausticStrength.value = 1.0; U.uWaterOn.value = 1;
    this.route = new Route(WAY);
    const R = this.route;
    // ---------------------------------------------------------------- terrain
    const halfWidth = (z) => z > -70 ? 22 : z > -105 ? 14 : z > -172 ? 4.5 : z > -255 ? 13 : 18;
    const hfn = (x, z) => {
      const r = R.atZ(z);
      const dx = x - r.x;
      const w = halfWidth(z);
      let h = r.y;
      // valley walls
      const wall = Math.max(0, Math.abs(dx) - w);
      h += Math.min(0.0035 * dx * dx, 10) + Math.min(wall * wall * 0.06, 18) + ridge2(x * 0.04, z * 0.04, 4) * Math.min(12, wall * 0.9);
      h += fbm2(x * 0.06, z * 0.06, 4) * 1.4 + fbm2(x * 0.3, z * 0.3, 2) * 0.18;
      // the Nautilus rests in a shallow bed; a sand bank under the side door
      // the bed where the Nautilus rests: flat sand all along her length, open water around her
      const bed = smoothstep(16, 7, Math.abs(z)) * smoothstep(48, 38, Math.abs(x));
      h = lerp(h, -2.5 + fbm2(x * 0.08, z * 0.08, 2) * 0.25, bed);
      const near = smoothstep(30, 14, Math.abs(z)) * smoothstep(60, 42, Math.abs(x));
      h = Math.min(h, lerp(h, -2.0 + Math.abs(z) * 0.08, near));
      const door = Math.exp(-((x + 19.3) ** 2) / 6 - ((z + 5.6) ** 2) / 4);
      h = lerp(h, -1.25, door);
      // the glade: flat, a clearing in the petrified forest
      const gd = Math.hypot(x - GLADE.x, z - GLADE.z);
      h = lerp(h, GLADE.y + fbm2(x * 0.2, z * 0.2, 2) * 0.15, smoothstep(17, 9, gd));
      return h;
    };
    this.hfn = hfn;
    const colorFn = (x, z, h, slope) => {
      const n = fbm2(x * 0.15, z * 0.15, 3), n2 = fbm2(x * 0.7 + 7, z * 0.7, 2);
      const deep = smoothstep(-70, -170, z);
      // fine sand sown with the impalpable dust of shells -> ooze and algae -> white coral rubble
      let c = [0.86 + n * 0.08, 0.8 + n * 0.07, 0.66 + n * 0.05];
      const weed = smoothstep(0.05, 0.25, fbm2(x * 0.05 + 3, z * 0.05, 3)) * (1 - deep) * smoothstep(-20, -40, z);
      c = c.map((v, i) => lerp(v, [0.42, 0.46, 0.22][i], weed * 0.8));
      c = c.map((v, i) => lerp(v, [0.62, 0.6, 0.56][i], deep));
      const gl = smoothstep(16, 6, Math.hypot(x - GLADE.x, z - GLADE.z));
      c = c.map((v, i) => lerp(v, [0.8, 0.78, 0.74][i], gl));
      const rk = smoothstep(0.35, 0.7, slope);
      c = c.map((v, i) => lerp(v, [0.42, 0.41, 0.4][i] * (0.9 + n2 * 0.2), rk));
      return c.map((v) => v * (0.92 + n2 * 0.1));
    };
    this.terrain = new Terrain({ x0: -72, z0: -318, x1: 62, z1: 30, cell: 1.35, fn: hfn, colorFn, jitter: 0.22, seed: 3 });
    const tmesh = new THREE.Mesh(this.terrain.geometry, makeMaterial('M_terrain', true));
    tmesh.receiveShadow = true; tmesh.castShadow = true; tmesh.name = 'terrain';
    this.add(tmesh);
    g.world.addMesh(tmesh, 5);
    const ground = (x, z) => this.terrain.height(x, z);
    const rnd = mulberry32(77);
    const place = (name, list, opts = {}) => { if (!list.length) return null; const grp = P.instanced(name, list, opts); this.add(grp); return grp; };
    const colliders = (name, list) => {
      const geo = P.geometry(name); if (!geo) return;
      for (const m of list) { const mesh = new THREE.Mesh(geo); mesh.matrixWorld.copy(m); mesh.matrixAutoUpdate = false; mesh.updateMatrixWorld = () => {}; g.world.addMesh(mesh, 6); }
    };
    const scatter = (z0, z1, n, wmax, fn) => {
      for (let i = 0; i < n; i++) {
        const z = lerp(z0, z1, rnd()); const r = R.atZ(z);
        const side = (rnd() < 0.5 ? -1 : 1);
        const off = side * (1.6 + rnd() * wmax);
        const x = r.x + off;
        fn(x, ground(x, z), z, rnd);
      }
    };
    // ---------------------------------------------------------------- the coral kingdom (shallows, vivid)
    const sets = { coral_branch: [], coral_branch2: [], coral_brain: [], coral_brain2: [], coral_fan: [], coral_fan2: [], coral_tubes: [], anemone: [], coral_table: [], coral_white: [], coral_blood: [], fucus: [], fucus_red: [], rock_0: [], rock_1: [], rock_2: [], rock_3: [], rock_4: [] };
    scatter(-8, -78, 260, 18, (x, y, z, r) => {
      const k = r();
      const s = 0.7 + r() * 1.1;
      const name = k < 0.18 ? 'coral_branch' : k < 0.3 ? 'coral_branch2' : k < 0.42 ? 'coral_brain' : k < 0.5 ? 'coral_brain2' : k < 0.6 ? 'coral_fan' : k < 0.68 ? 'coral_fan2' : k < 0.78 ? 'coral_tubes' : k < 0.88 ? 'anemone' : k < 0.95 ? 'coral_table' : 'coral_blood';
      sets[name].push(trs(x, y - 0.05, z, r() * 6.28, s * (name === 'anemone' ? 1.6 : 1)));
    });
    // coral heads: rock mounds crowned with mixed colonies, the "brilliant garden of flowers"
    const clusterRocks = [[], [], [], [], []];
    for (let c = 0; c < 46; c++) {
      const z = -5 - rnd() * 72; const r = R.atZ(z);
      const side = rnd() < 0.5 ? -1 : 1; const off = side * (2.6 + rnd() * 12);
      const cx = r.x + off, cz = z + (rnd() - 0.5) * 3; const cy = ground(cx, cz);
      const rs = 0.8 + rnd() * 1.1;
      clusterRocks[Math.floor(rnd() * 5)].push(trs(cx, cy - rs * 0.35, cz, rnd() * 6, rs));
      const n = 7 + Math.floor(rnd() * 10);
      for (let i = 0; i < n; i++) {
        const a = rnd() * Math.PI * 2, d = rnd() * rs * 1.2;
        const x = cx + Math.cos(a) * d, zz = cz + Math.sin(a) * d;
        const top = cy + Math.max(0, rs * 0.55 - d * 0.45);
        const k = rnd();
        const name = k < 0.2 ? 'coral_branch' : k < 0.32 ? 'coral_branch2' : k < 0.44 ? 'coral_fan' : k < 0.52 ? 'coral_fan2' : k < 0.64 ? 'coral_brain' : k < 0.7 ? 'coral_brain2' : k < 0.8 ? 'coral_tubes' : k < 0.9 ? 'anemone' : k < 0.96 ? 'coral_table' : 'coral_blood';
        const sc = (name === 'coral_brain' || name === 'coral_brain2') ? 0.4 + rnd() * 0.6 : name === 'anemone' ? 1.3 + rnd() * 1.2 : 0.7 + rnd() * 1.0;
        sets[name].push(trs(x, Math.max(top, ground(x, zz)) - 0.05, zz, rnd() * 6.28, sc, (rnd() - 0.5) * 0.2, (rnd() - 0.5) * 0.2));
      }
    }
    clusterRocks.forEach((l, i) => { if (l.length) { this.add(P.instanced('rock_' + i, l)); colliders('rock_' + i, l); } });
    // sea-stars studding the sandy bottom; shells strewing the ground by thousands
    {
      const sh = new THREE.Shape(); const N = 5;
      for (let i = 0; i <= N * 2; i++) { const a = i / (N * 2) * Math.PI * 2; const rr = i % 2 ? 0.035 : 0.11; const px = Math.cos(a) * rr, py = Math.sin(a) * rr; i ? sh.lineTo(px, py) : sh.moveTo(px, py); }
      const sg = new THREE.ExtrudeGeometry(sh, { depth: 0.018, bevelEnabled: false }); sg.rotateX(-Math.PI / 2);
      const starMat = patchUnderwater(new THREE.MeshStandardMaterial({ roughness: 0.75 }));
      const stars = []; const cols = [0xd8502a, 0xe08a30, 0x9a3a8a, 0xc8302a, 0xe8b040];
      for (let i = 0; i < 260; i++) { const z = -4 - rnd() * 60; const r = R.atZ(z); const x = r.x + (rnd() - 0.5) * 26; stars.push(trs(x, ground(x, z) + 0.01, z, rnd() * 6, 0.7 + rnd() * 0.9)); }
      const im = new THREE.InstancedMesh(sg, starMat, stars.length);
      stars.forEach((m, i) => { im.setMatrixAt(i, m); im.setColorAt(i, new THREE.Color(cols[i % cols.length])); });
      im.receiveShadow = true; this.add(im);
      const shellG = new THREE.ConeGeometry(0.03, 0.08, 6); shellG.rotateZ(Math.PI / 2.3);
      const shells = []; const scol = [0xf0e2cc, 0xd8a070, 0xe8d0b8, 0xb06a44, 0xf4ece0];
      for (let i = 0; i < 700; i++) { const z = -3 - rnd() * 90; const r = R.atZ(z); const x = r.x + (rnd() - 0.5) * 30; shells.push(trs(x, ground(x, z) + 0.015, z, rnd() * 6, 0.6 + rnd() * 1.2)); }
      const sm = new THREE.InstancedMesh(shellG, patchUnderwater(new THREE.MeshStandardMaterial({ roughness: 0.5 })), shells.length);
      shells.forEach((m, i) => { sm.setMatrixAt(i, m); sm.setColorAt(i, new THREE.Color(scol[i % scol.length])); });
      this.add(sm);
    }
    // clusters hugging the hull, seen from the saloon windows
    for (let i = 0; i < 70; i++) {
      const x = 2 + rnd() * 16, side = rnd() < 0.5 ? 1 : -1, z = side * (5.5 + rnd() * 9);
      const y = ground(x, z); const k = rnd();
      const name = k < 0.25 ? 'coral_branch' : k < 0.4 ? 'coral_fan' : k < 0.55 ? 'coral_brain' : k < 0.7 ? 'coral_tubes' : k < 0.85 ? 'anemone' : 'coral_branch2';
      sets[name].push(trs(x, y - 0.05, z, rnd() * 6.28, 0.8 + rnd() * 1.4));
    }
    // a plain of sea-weed: rigid, perpendicular fucus ("the region of perpendicularity")
    scatter(-22, -62, 200, 20, (x, y, z, r) => { sets[r() < 0.75 ? 'fucus' : 'fucus_red'].push(trs(x, y, z, r() * 6.28, new THREE.Vector3(1, 0.6 + r() * 1.3, 1))); });
    // ---------------------------------------------------------------- petrified thickets (transition)
    scatter(-70, -108, 120, 12, (x, y, z, r) => {
      const k = r(); const name = k < 0.45 ? 'coral_white' : k < 0.65 ? 'coral_blood' : k < 0.85 ? 'coral_table' : 'coral_fan';
      sets[name].push(trs(x, y - 0.05, z, r() * 6.28, 0.9 + r() * 1.6));
    });
    scatter(-60, -110, 60, 14, (x, y, z, r) => sets['rock_' + Math.floor(r() * 5)].push(trs(x, y - 0.3, z, r() * 6.28, 0.7 + r() * 2.0)));
    // ---------------------------------------------------------------- the dark gallery: natural arches with pendants like lustres
    const arches = [], pendants = [], wallRocks = [], roofRocks = [];
    for (let s = R.atZ(-108).s; s < R.atZ(-170).s; s += 4.6 + rnd() * 1.6) {
      const { p, dir } = R.at(s);
      const y = ground(p.x, p.z);
      const sc = 1.0 + rnd() * 0.35;
      arches.push(trs(p.x, y - 0.4, p.z, Math.atan2(dir.x, dir.z) + (rnd() - 0.5) * 0.2, sc));
      for (let k = 0; k < 2; k++) pendants.push(trs(p.x + (rnd() - 0.5) * 2.4, y - 0.4 + 3.9 * sc, p.z + (rnd() - 0.5) * 1.0, rnd() * 6, 0.7 + rnd() * 0.6));
      // a roof of coral rock over the arches, broken here and there so the last daylight falls through in blades
      if (rnd() < 0.82) roofRocks.push(trs(p.x + (rnd() - 0.5) * 1.5, y - 0.4 + 4.3 * sc + rnd() * 0.4, p.z + (rnd() - 0.5) * 1.5, rnd() * 6, new THREE.Vector3(3.2 + rnd() * 1.2, 0.9 + rnd() * 0.5, 3.0 + rnd() * 1.4)));
      for (const sd of [-1, 1]) {
        const nx = -dir.z * sd, nz = dir.x * sd;
        wallRocks.push(trs(p.x + nx * (3.2 + rnd()), y + rnd() * 1.5, p.z + nz * (3.2 + rnd()), rnd() * 6, 1.6 + rnd() * 1.6));
      }
    }
    // ---------------------------------------------------------------- the forest of mineral trees
    const trees = [], trees2 = [];
    scatter(-170, -262, 70, 12, (x, y, z, r) => { (r() < 0.5 ? trees : trees2).push(trs(x, y - 0.2, z, r() * 6.28, 1.1 + r() * 1.1)); });
    scatter(-170, -262, 120, 12, (x, y, z, r) => { const k = r(); sets[k < 0.45 ? 'coral_white' : k < 0.75 ? 'coral_blood' : 'coral_fan'].push(trs(x, y - 0.05, z, r() * 6.28, 0.8 + r() * 1.4)); });
    // trees ring the glade
    for (let i = 0; i < 18; i++) {
      const a = i / 18 * Math.PI * 2 + rnd() * 0.2, d = 15 + rnd() * 6;
      const x = GLADE.x + Math.cos(a) * d, z = GLADE.z + Math.sin(a) * d;
      if (Math.abs(a - Math.PI / 2) < 0.35) continue; // the way in, from the north (+z)
      (i % 2 ? trees : trees2).push(trs(x, ground(x, z) - 0.2, z, rnd() * 6, 1.4 + rnd() * 0.8));
    }
    for (const k in sets) place(k, sets[k], { cull: /coral|anemone|fucus/.test(k) ? 42 : 1e9 });
    place('coral_arch', arches); colliders('coral_arch', arches);
    place('pendant', pendants, { shadow: true });
    place('rock_1', roofRocks, { shadow: true });
    for (let i = 0; i < 5; i++) { const sub = wallRocks.filter((_, j) => j % 5 === i); place('rock_' + i, sub); colliders('rock_' + i, sub); }
    place('coral_tree', trees); place('coral_tree2', trees2);
    for (let i = 0; i < 5; i++) colliders('rock_' + i, sets['rock_' + i]);
    // trunks block the way (cylinders as proxies)
    const trunkGeo = new THREE.CylinderGeometry(0.45, 0.6, 4, 7); trunkGeo.translate(0, 2, 0);
    for (const m of [...trees, ...trees2]) { const mesh = new THREE.Mesh(trunkGeo); const p = new THREE.Vector3().setFromMatrixPosition(m); const s = new THREE.Vector3().setFromMatrixScale(m); mesh.matrixWorld.compose(p, new THREE.Quaternion(), s); mesh.updateMatrixWorld = () => {}; g.world.addMesh(mesh, 6); }
    // ---------------------------------------------------------------- the cemetery
    const mounds = [];
    for (let row = 0; row < 3; row++) for (let k = 0; k < 4; k++) {
      const x = GLADE.x - 5 + k * 2.6 + (row % 2) * 0.6, z = GLADE.z + 3 + row * 3.0;
      if (row === 0 && k === 3) continue; // room for the new grave
      mounds.push(trs(x, ground(x, z) - 0.05, z, (rnd() - 0.5) * 0.15, new THREE.Vector3(0.9 + rnd() * 0.15, 1, 0.9 + rnd() * 0.15)));
    }
    // the old graves: low tumuli of stones that the polypi have begun to seal with coral
    const moundMat = makeMaterial('M_coral_stone', true);
    place('grave_mound', mounds, { material: moundMat });
    const tufts = { coral_white: [], coral_blood: [], coral_brain: [] };
    for (const m of mounds) {
      const c = new THREE.Vector3().setFromMatrixPosition(m);
      for (let i = 0; i < 5; i++) {
        const a = rnd() * 6.28, rr = Math.sqrt(rnd());
        const x = c.x + Math.cos(a) * 0.45 * rr, z = c.z + Math.sin(a) * 0.95 * rr; const k = rnd();
        tufts[k < 0.5 ? 'coral_white' : k < 0.8 ? 'coral_brain' : 'coral_blood'].push(trs(x, c.y + 0.16 * (1 - rr * rr), z, rnd() * 6.28, 0.12 + rnd() * 0.16));
      }
    }
    for (const k in tufts) place(k, tufts[k], { shadow: false });
    this.cross = P.mesh('coral_cross'); this.cross.position.set(GLADE.x, ground(GLADE.x, GLADE.z - 2), GLADE.z - 2); this.add(this.cross);
    colliders('coral_cross', [this.cross.matrixWorld.clone()]);
    this.cross.updateMatrixWorld(true);
    this.graveSpot = new THREE.Vector3(GLADE.x + 2.6, 0, GLADE.z + 3.0); this.graveSpot.y = ground(this.graveSpot.x, this.graveSpot.z);
    // the new grave: hole, earth beside it, and the mound that seals it
    this.hole = new THREE.Mesh(new THREE.CircleGeometry(1, 20), new THREE.MeshBasicMaterial({ color: 0x050505 }));
    this.hole.rotation.x = -Math.PI / 2; this.hole.scale.set(0.001, 0.001, 1); this.hole.position.copy(this.graveSpot).add(new THREE.Vector3(0, 0.03, 0));
    this.add(this.hole);
    this.spoil = P.mesh('grave_mound', { material: moundMat }); this.spoil.position.copy(this.graveSpot).add(new THREE.Vector3(1.3, -0.05, 0)); this.spoil.scale.setScalar(0.001); this.add(this.spoil);
    this.newMound = P.mesh('grave_mound', { material: moundMat }); this.newMound.position.copy(this.graveSpot).add(new THREE.Vector3(0, -0.05, 0)); this.newMound.scale.setScalar(0.001); this.add(this.newMound);
    // sparks from the pickaxe
    const sg = new THREE.BufferGeometry(); sg.setAttribute('position', new THREE.BufferAttribute(new Float32Array(30 * 3), 3));
    this.sparks = new THREE.Points(sg, new THREE.PointsMaterial({ color: new THREE.Color(4, 3, 1.6), size: 0.05, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
    this.sparks.frustumCulled = false; this.sparkLife = 0; this.sparkV = Array.from({ length: 30 }, () => new THREE.Vector3());
    this.add(this.sparks);
    // ---------------------------------------------------------------- life
    this.schools = [
      new FishSchool(P, 'fish_a', 40, new THREE.Vector3(-14, -1.5, -26), 4, 2),
      new FishSchool(P, 'fish_b', 30, new THREE.Vector3(-8, -4.5, -52), 5, 3),
      new FishSchool(P, 'fish_c', 60, new THREE.Vector3(8, 1.0, 9), 5, 2),
      new FishSchool(P, 'fish_a', 30, new THREE.Vector3(-4, -12, -95), 3, 2),
    ];
    for (const s of this.schools) this.add(s.mesh);
    this.medusae = new Medusae(P, 24, { x0: -30, x1: 10, z0: -60, z1: 10 }, 3, 8); this.add(this.medusae.mesh);
    const polypSpots = [];
    for (let i = 0; i < 26; i++) { const z = -6 - rnd() * 60; const r = R.atZ(z); const x = r.x + (rnd() - 0.5) * 7; polypSpots.push({ p: new THREE.Vector3(x, ground(x, z) + 0.1, z), n: 14, r: 0.4, h: 0.4 }); }
    this.polypSpots = polypSpots;
    this.polyps = new Polyps(P, polypSpots); this.add(this.polyps.group);
    // ---------------------------------------------------------------- the company: Captain Nemo, a dozen of the crew, Ned Land, Conseil
    this.nautilusPlace();
    this.lampMat = makeMaterial('M_lampglass', true);
  }
  nautilusPlace() { this.g.nautilus.place(new THREE.Vector3(0, 0, 0), 0); }

  reset() {
    const g = this.g, n = g.nautilus;
    this.nautilusPlace();
    n.state.ceiling = 1; n.state.ceilingVis = 1; n.state.panels = 0; n.state.panelsTarget = 0; n.state.clockHours = 8; n.state.speed = 0;
    n.outside.brightness = 1.0; n.outside.color.setRGB(0.55, 0.85, 0.9);
    n.state.interiorPower = 1;
    // the company
    g.crowd.divers.length = 0; g.intCrowd.divers.length = 0; g.crowd.shrouds.length = 0;
    this.nemo = new Diver({ name: 'nemo' });
    g.intCrowd.add(this.nemo);
    this.nemo.pos.copy(n.toWorld(b2t(-18.6, 1.4, 0))); this.nemo.yaw = Math.PI * 0.5;
    this.nemoState = 'wardrobe';
    this.crew = [];
    const heldFor = (i) => (i === 4 ? 'pickaxe' : null);
    for (let i = 0; i < 12; i++) { const d = new Diver({ name: 'crew' + i, held: heldFor(i), scale: 0.97 + Math.random() * 0.08 }); this.crew.push(d); g.crowd.add(d); }
    this.ned = new Diver({ name: 'ned', scale: 1.08 }); this.conseil = new Diver({ name: 'conseil', scale: 0.95 });
    g.crowd.add(this.ned); g.crowd.add(this.conseil);
    // waiting outside by the hull, in a loose knot
    const door = new THREE.Vector3(-19.3, 0, -9);
    [...this.crew, this.ned, this.conseil].forEach((d, i) => {
      const a = i * 0.9, r = 2.2 + (i % 4) * 0.9;
      d.pos.set(door.x + Math.cos(a) * r - 2, 0, door.z - 3 + Math.sin(a) * r);
      d.yaw = Math.PI; d.setPose('stand'); d.speed = 0; d.lookAt = null;
    });
    this.bearers = this.crew.slice(0, 4);
    this.digger = this.crew[4];
    this.shroud = { visible: true, matrix: new THREE.Matrix4() };
    g.crowd.shrouds.push(this.shroud);
    this.lampsOn = false; this.crewLampsLevel = 0;
    this.lampMat && this.lampMat.color.setRGB(0.15, 0.16, 0.17);
    this.phase = 'aboard'; this.cer = null; this.t = 0; this.triggers = {};
    this.procession = null;
    this.stress = 0;
    // the player wakes in his room
    g.player.teleport(n.toWorld(b2t(19.75, -0.55, 0)), 0.39, -0.3);
    g.seq && (g.seq.stage = 'cabin');
  }

  start() {
    const g = this.g;
    g.pipe.finalMat.uniforms.uFade.value = 1; g.fadeTo(0, 2.5);
    setTimeout(() => bus.emit('say', 'The next morning I went to my table. Captain Nemo had left a note for me.'), 1500);
    g.ui.objective('Read the note on the writing table.');
  }

  readNote() {
    const g = this.g; g.modal = true;
    g.ui.showNote({
      head: 'On board the Nautilus',
      body: 'Professor, will it be convenient to you to make a submarine excursion to-day?\n\nWith your companions, if they like. Put on your diving dress in the wardrobe, aft, near the machinery. I shall wait for you there.',
      sign: '— Captain Nemo',
    }).then(() => {
      g.modal = false;
      if (!this.triggers.note) {
        this.triggers.note = 1;
        bus.emit('say', 'It was not a question of dead or dying. Conseil hastened to accept; this time even the Canadian seemed quite willing.');
        g.ui.objective('Go aft, through the saloon and the library, to the wardrobe.');
      }
    });
  }

  nemoInCell() { return this.nemoState === 'cell' || this.nemoState === 'waitingCell'; }
  onSuited() { this.g.ui.objective('Step into the little cell beside the wardrobe.'); this.nemoState = 'toCell'; }
  onLockClosed() { this.g.ui.objective('Turn the tap to flood the cell.'); }
  onFlood() {}
  onOuterOpen() { this.nemoState = 'exiting'; this.g.ui.objective('Follow Captain Nemo.'); }
  onOutside() {
    bus.emit('say', 'I set foot, at a depth of about thirty feet, on the solid bottom on which the Nautilus rested.');
    this.phase = 'walk';
    const all = [this.nemo, ...this.crew, this.ned, this.conseil];
    this.procession = new Procession(this.route, [this.nemo, ...this.crew], { speed: 0.82, gap: 1.5, wait: 15 });
    this.procession.s = this.route.project(this.g.player.pos.x, this.g.player.pos.z).s + 6;
    this.procession.target = this.route.atZ(GLADE.z + 10).s;
    this.g.ui.objective('Follow the Captain and his men down the slope.');
  }
  onLamp() {
    if (!this.triggers.lampSaid) { this.triggers.lampSaid = 1; bus.emit('say', 'By turning a screw I established a communication between the wire and the spiral glass, and the sea was illuminated.'); }
  }

  interactables() {
    const out = [];
    return out;
  }
  onInteract(kind) { return false; }

  ground(x, z) { return this.terrain ? this.terrain.height(x, z) : 0; }
  volumetricSpots() { return []; }
  audioEnv(water) {
    const p = this.g.player.pos;
    return { reef: water ? clamp(1 - (depthAt(p.y) - 9) / 30, 0, 1) : 0, rain: 0, volcano: 0, nearHull: water ? clamp(1 - Math.hypot(p.x, p.z) / 40, 0, 1) : 0 };
  }

  update(dt, title) {
    const g = this.g, n = g.nautilus, P = g.player;
    this.t += dt;
    g.pipe.volMat.uniforms.uMaxDist.value = 90;
    // sun: shadow box follows the player in steps so its map is not redrawn every frame
    const focus = title ? n.toWorld(b2t(9.5, 6, 0)) : P.pos;
    const snap = (v) => Math.round(v / 6) * 6;
    const cx = snap(focus.x), cz = snap(focus.z);
    const sd = UW.uniforms.uSunDir.value;
    if (cx !== this.sunCx || cz !== this.sunCz || !this.sunInit) {
      this.sunCx = cx; this.sunCz = cz; this.sunInit = true;
      const c = new THREE.Vector3(cx, focus.y, cz);
      g.sun.position.copy(c).addScaledVector(sd, -70); g.sun.target.position.copy(c).addScaledVector(sd, 10);
      g.sun.target.updateMatrixWorld(); g.sun.shadow.needsUpdate = true;
    }
    g.sun.shadow.autoUpdate = false;
    this.sunTick = (this.sunTick || 0) + 1;
    if (this.t < 1 || (g.headMedium === 'water' && this.sunTick % 4 === 0)) g.sun.shadow.needsUpdate = true;
    g.sun.intensity = 1;
    // life
    const threat = title ? null : P.pos;
    for (const s of this.schools) s.update(dt, threat);
    this.medusae.update(dt);
    if (!title && this.polyps) this.polyps.update(dt, g.headMedium === 'water' ? g.camera.position.clone().add(P.forward().multiplyScalar(0.7)) : null, (k) => g.audio.sfx('polyp', P.pos));
    // grading: vivid in the shallows, colours drain with depth
    const d = depthAt(g.camera.position.y);
    const water = g.headMedium === 'water';
    const gm = g.pipe.gradeMat.uniforms;
    gm.uSat.value = water ? lerp(1.02, 0.72, smoothstep(12, 90, d)) : 0.86;
    // deeper water is clearer: less scattering, so lamp beams read as beams rather than fog
    const clear = smoothstep(20, 160, d);
    UW.uniforms.uSigmaS.value.set(lerp(0.026, 0.012, clear), lerp(0.031, 0.014, clear), lerp(0.035, 0.016, clear));
    UW.uniforms.uSigmaA.value.set(lerp(0.08, 0.06, clear), lerp(0.036, 0.024, clear), lerp(0.026, 0.018, clear));
    gm.uExposure.value = water ? lerp(1.0, 1.35, smoothstep(30, 200, d)) : 1.08;
    g.pipe.compMat.uniforms.uFogGain.value = 0.11;
    if (title) return;
    // ---------------------------------------------------------------- aboard: the captain dresses and waits
    this.updateNemoAboard(dt);
    // ---------------------------------------------------------------- outside
    if (this.procession) {
      const ps = this.route.project(P.pos.x, P.pos.z).s;
      this.procession.update(dt, ps);
      const lead = this.procession.s;
      if (this.procession.waiting && this.phase === 'walk') { this.nemo.setPose('beckon'); this.nemo.lookAt = P.pos; } else if (this.phase === 'walk') { this.nemo.setPose('stand'); this.nemo.lookAt = null; }
      // Ned and Conseil keep near the professor
      this.companions(dt);
      // story beats by distance along the route
      const z = P.pos.z;
      this.beat('declivity', z < -16, 'A slight declivity ended in an uneven bottom, at fifteen fathoms. Here there was no fine sand, no submarine prairies: it was the coral kingdom.');
      this.beat('flowers', z < -32, 'If my hand approached these living flowers, the whole colony took alarm. The white petals re-entered their red cases.');
      this.beat('perpend', z < -46, 'Not a filament, not a ribbon, however thin, but kept as straight as a rod of iron. Truly it was the region of perpendicularity!');
      this.beat('thickets', z < -80, 'But soon the bushes contract, and the arborisations increase. Real petrified thickets were disclosed before us.');
      if (z < -104 && !this.triggers.gallery) {
        this.triggers.gallery = 1;
        bus.emit('say', 'Captain Nemo placed himself under a dark gallery, where by a slight declivity we reached a depth of a hundred yards.');
        this.procession.stopped = true;
        setTimeout(() => { this.lampsOn = true; g.audio.sfx('lamp', this.nemo.pos); }, 2500);
        setTimeout(() => { this.procession.stopped = false; if (!g.lampOn) g.ui.objective('Turn the screw of your lamp (F).'); }, 5500);
      }
      this.beat('lustres', z < -128, 'The light from our lamps produced magical effects, following the rough outlines of the arches and pendants disposed like lustres, tipped with points of fire.');
      this.beat('forest', z < -178, 'It was an immense forest of large mineral vegetations, enormous petrified trees, united by garlands of elegant sea-bindweed.');
      if (this.phase === 'walk' && this.procession.s >= this.procession.target - 0.5 && P.pos.distanceTo(GLADE) < 24) this.beginCeremony();
    }
    // lamps of the company
    this.crewLampsLevel += ((this.lampsOn ? 1 : 0) - this.crewLampsLevel) * Math.min(1, dt * 2);
    this.lampMat.color.setScalar(0.15 + 3.2 * this.crewLampsLevel);
    const nl = g.nemoLamp;
    if (this.nemo && this.lampsOn && this.nemoState === 'outside') {
      const lp = this.nemo.lampWorld(); nl.position.copy(lp);
      const f = new THREE.Vector3(Math.sin(this.nemo.yaw), -0.35, Math.cos(this.nemo.yaw));
      nl.target.position.copy(lp).add(f); nl.target.updateMatrixWorld();
      nl.intensity = 240 * this.crewLampsLevel;
    } else nl.intensity = 0;
    // the crew's lamps, gathered into two lights around the procession
    if (this.procession && this.crewLampsLevel > 0.01) {
      const mid = this.crew.slice(1, 7), back = this.crew.slice(7);
      const avg = (arr) => arr.reduce((a, d) => a.add(d.lampWorld()), new THREE.Vector3()).multiplyScalar(1 / arr.length);
      g.crewLights[0].position.copy(avg(mid)); g.crewLights[1].position.copy(avg(back));
      g.crewLights.forEach((l) => { l.intensity = 70 * this.crewLampsLevel; l.userData.volumetric = 0.4; });
    } else g.crewLights.forEach((l) => (l.intensity = 0));
    if (this.cer) this.updateCeremony(dt);
    // shroud carried on the bearers' shoulders
    this.updateShroud();
    // sparks
    if (this.sparkLife > 0) {
      this.sparkLife -= dt;
      const a = this.sparks.geometry.attributes.position;
      for (let i = 0; i < 30; i++) { const v = this.sparkV[i]; a.setXYZ(i, a.getX(i) + v.x * dt, a.getY(i) + v.y * dt, a.getZ(i) + v.z * dt); v.multiplyScalar(Math.exp(-dt * 3)); v.y -= dt * 0.5; }
      a.needsUpdate = true;
      this.sparks.material.opacity = Math.max(0, this.sparkLife / 0.5);
      g.crewLights[1].position.copy(this.sparkAt); g.crewLights[1].intensity = Math.max(g.crewLights[1].intensity, 50 * Math.max(0, this.sparkLife / 0.5));
    }
    this.stress = Math.max(0, this.stress - dt * 0.1);
  }
  beat(key, cond, text) { if (cond && !this.triggers[key]) { this.triggers[key] = 1; bus.emit('say', text); } }

  companions(dt) {
    const P = this.g.player;
    const back = new THREE.Vector3(Math.sin(P.yaw), 0, Math.cos(P.yaw));
    const right = new THREE.Vector3(Math.cos(P.yaw), 0, -Math.sin(P.yaw));
    const follow = (d, ox, oz) => {
      if (this.cer) return;
      const t = P.pos.clone().addScaledVector(back, oz).addScaledVector(right, ox);
      const dx = t.x - d.pos.x, dz = t.z - d.pos.z, dist = Math.hypot(dx, dz);
      if (dist > 1.2) { const mv = Math.min(dist - 1.0, 1.15 * dt * (dist > 6 ? 1.6 : 1)); d.pos.x += dx / dist * mv; d.pos.z += dz / dist * mv; d.speed = 0.9; d.yaw += Math.atan2(Math.sin(Math.atan2(dx, dz) - d.yaw), Math.cos(Math.atan2(dx, dz) - d.yaw)) * Math.min(1, dt * 2); }
      else { d.speed = 0; d.lookAt = P.pos; }
    };
    follow(this.conseil, 1.6, 2.2);
    follow(this.ned, -1.8, 3.0);
  }

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
    if (this.nemoState === 'wardrobe') { d.lookAt = g.player.pos; d.pos.y = 0; if (g.player.pos.distanceTo(d.pos) < 3.5 && !this.triggers.nemoGreet) { this.triggers.nemoGreet = 1; bus.emit('say', 'Captain Nemo was already in his dress. He waited, motionless, his head enclosed in its copper box.'); g.ui.objective('Put on the diving dress.'); } }
    if (this.nemoState === 'toCell') { if (goTo(b2t(-19.3, 1.4, 0))) this.nemoState = 'toCell2'; }
    if (this.nemoState === 'toCell2') { if (goTo(b2t(-19.6, 3.0, 0))) { this.nemoState = 'waitingCell'; d.yaw = Math.PI; } }
    if (this.nemoState === 'waitingCell') {
      d.lookAt = g.player.pos;
      if (g.inCell() && g.seq.lock === 'open' && !this.triggers.closeHint) { this.triggers.closeHint = 1; g.ui.objective('Close the watertight door behind you.'); }
    }
    if (this.nemoState === 'exiting') { if (goTo(b2t(-19.3, 4.6, 0), 0.6)) { this.nemoState = 'drop'; } }
    if (this.nemoState === 'drop') {
      // step out of the hull and sink to the sand: move him into the water world
      const i = g.intCrowd.divers.indexOf(d); if (i >= 0) g.intCrowd.divers.splice(i, 1);
      g.crowd.add(d); this.nemoState = 'outside';
      d.pos.set(-19.3, 0, -6.2); d.yaw = Math.PI;
    }
    if (this.nemoState !== 'outside') { d.pos.y = n.toWorld(new THREE.Vector3()).y; }
  }

  updateShroud() {
    const b = this.bearers; if (!b || !this.shroud) return;
    if (this.cer && this.cer.stage >= 4) return; // lowered into the grave by the ceremony
    const c = new THREE.Vector3(); b.forEach((d) => c.add(d.pos)); c.multiplyScalar(0.25);
    const dir = new THREE.Vector3().subVectors(b[0].pos, b[3].pos); dir.y = 0;
    const yaw = Math.atan2(dir.x, dir.z);
    c.y += (this.phase === 'cemetery' && this.cer && this.cer.stage >= 2) ? 0.2 : 2.05;
    this.shroud.matrix.compose(c, new THREE.Quaternion().setFromEuler(new THREE.Euler(0, yaw + Math.PI / 2, 0)), new THREE.Vector3(1, 1, 1));
  }

  beginCeremony() {
    const g = this.g;
    this.phase = 'cemetery';
    this.procession.stopped = true;
    this.cer = { t: 0, stage: 0, strikes: 0 };
    bus.emit('say', 'Captain Nemo had stopped. Turning round, I saw his men forming a semi-circle round their chief. Four of them carried on their shoulders an object of an oblong shape.', 8);
    // stations around the new grave
    const G = this.graveSpot;
    const ring = (i, n, r, a0, a1) => { const a = lerp(a0, a1, n > 1 ? i / (n - 1) : 0.5); return new THREE.Vector3(G.x + Math.cos(a) * r, 0, G.z + Math.sin(a) * r); };
    const others = this.crew.filter((d) => !this.bearers.includes(d) && d !== this.digger);
    this.cer.stations = new Map();
    others.forEach((d, i) => this.cer.stations.set(d, ring(i, others.length, 4.2, Math.PI * 0.15, Math.PI * 0.85)));
    this.bearers.forEach((d, i) => this.cer.stations.set(d, new THREE.Vector3(G.x - 2.4 + (i % 2) * 1.0, 0, G.z - 1.6 + Math.floor(i / 2) * 1.4)));
    this.cer.stations.set(this.digger, new THREE.Vector3(G.x + 1.0, 0, G.z - 0.6));
    this.cer.stations.set(this.nemo, new THREE.Vector3(G.x - 0.3, 0, G.z - 3.0));
    this.cer.stations.set(this.ned, new THREE.Vector3(G.x - 3.6, 0, G.z + 2.5));
    this.cer.stations.set(this.conseil, new THREE.Vector3(G.x - 2.6, 0, G.z + 3.2));
    this.procession = this.procession; // stays for player tracking
    g.ui.objective('Watch. Kneel with them when they kneel (C).');
  }

  updateCeremony(dt) {
    const g = this.g, c = this.cer, G = this.graveSpot;
    c.t += dt;
    // walk everyone to their stations
    for (const [d, p] of c.stations) {
      const dx = p.x - d.pos.x, dz = p.z - d.pos.z, dist = Math.hypot(dx, dz);
      if (dist > 0.08) { const mv = Math.min(dist, 0.7 * dt); d.pos.x += dx / dist * mv; d.pos.z += dz / dist * mv; d.speed = 0.7; const want = Math.atan2(dx, dz); d.yaw += Math.atan2(Math.sin(want - d.yaw), Math.cos(want - d.yaw)) * Math.min(1, dt * 2.5); }
      else { d.speed = 0; const want = Math.atan2(G.x - d.pos.x, G.z - d.pos.z); d.yaw += Math.atan2(Math.sin(want - d.yaw), Math.cos(want - d.yaw)) * Math.min(1, dt * 1.5); }
    }
    const at = (t) => c.t > t && c.prev <= t;
    c.prev = c.prevT ?? 0; c.prevT = c.t;
    if (at(6)) { bus.emit('say', 'In the midst of the glade, on a pedestal of rocks roughly piled up, stood a cross of coral that extended its long arms, that one might have thought were made of petrified blood.', 8); }
    if (at(13)) { c.stage = 1; bus.emit('say', 'Upon a sign from Captain Nemo one of the men advanced, and began to dig a hole with a pickaxe. I understood all! This glade was a cemetery, this hole a tomb.', 9); this.digger.setPose('dig', 3); }
    if (c.stage === 1) {
      // strikes land when the swing reaches the bottom
      const ph = Math.sin(this.digger.t * 3.6);
      if (ph > 0.95 && !c.down) { c.down = true; c.strikes++; this.strike(); }
      if (ph < 0) c.down = false;
      const k = clamp((c.t - 13) / 16, 0, 1);
      this.hole.scale.set(0.45 * k + 0.001, 0.95 * k + 0.001, 1);
      this.spoil.scale.set(0.55 * k + 0.001, 0.5 * k + 0.001, 0.6 * k + 0.001);
    }
    if (at(30)) { c.stage = 2; this.digger.setPose('stand'); this.bearers.forEach((d) => d.setPose('lower', 1)); bus.emit('say', 'The bearers approached; the body, enveloped in a tissue of white linen, was lowered into the damp grave.', 7); }
    if (c.stage >= 2 && c.stage < 4) {
      const k = clamp((c.t - 30) / 6, 0, 1);
      const p = G.clone(); p.y = G.y + lerp(1.0, -0.35, k);
      this.shroud.matrix.compose(p, new THREE.Quaternion().setFromEuler(new THREE.Euler(0, Math.PI / 2, 0)), new THREE.Vector3(1, 1, 1));
      if (k >= 1) c.stage = 4;
    }
    if (at(37)) { this.bearers.forEach((d) => d.setPose('stand')); this.shroud.visible = false; }
    if (c.stage >= 4 && c.t > 37 && c.t < 43) {
      const k = clamp((c.t - 37) / 5, 0, 1);
      this.hole.scale.set((0.45 + 0.001) * (1 - k), (0.95 + 0.001) * (1 - k), 1); this.spoil.scale.setScalar(Math.max(0.001, 0.55 * (1 - k)));
      this.newMound.scale.set(0.9 * k + 0.001, 1.1 * k + 0.001, 0.95 * k + 0.001);
    }
    if (at(43)) {
      c.stage = 5; c.kneelPrompt = true;
      bus.emit('say', 'Captain Nemo, with his arms crossed on his breast, and all the friends of him who had loved them, knelt in prayer.', 9);
      this.nemo.setPose('kneelCross', 0.8);
      for (const d of [...this.crew, this.ned, this.conseil]) d.setPose('kneel', 0.6 + Math.random() * 0.5);
    }
    if (c.stage === 5 && g.player.crouch > 0.6) { g.player.kneel = Math.min(1, g.player.kneel + dt); }
    if (at(56)) {
      c.stage = 6; c.kneelPrompt = false;
      bus.emit('say', 'Then they rose, approached the grave, knelt again, and all extended their hands in sign of a last adieu.', 8);
      for (const [d, p] of c.stations) { const v = new THREE.Vector3(p.x - G.x, 0, p.z - G.z).multiplyScalar(0.7); c.stations.set(d, G.clone().add(v)); d.setPose('stand'); }
    }
    if (at(62)) for (const d of [this.nemo, ...this.crew, this.ned, this.conseil]) d.setPose('kneelExtend', 0.7);
    if (at(72)) { for (const d of [this.nemo, ...this.crew, this.ned, this.conseil]) d.setPose('stand', 0.8); bus.emit('say', 'Then the funeral procession returned to the Nautilus, passing under the arches of the forest, still on the ascent.', 7); g.player.kneel = 0; }
    if (at(80)) this.finish();
  }

  strike() {
    const g = this.g;
    const hp = this.digger.handWorld(); const p = this.graveSpot.clone(); p.y += 0.1; p.x += (hp.x - p.x) * 0.3; p.z += (hp.z - p.z) * 0.3;
    this.sparkAt = p;
    g.audio.sfx('pickaxe', p, { ref: 8 });
    // "the strokes of the pickaxe, which sparkled when it hit upon some flint lost at the bottom of the waters"
    if (Math.random() < 0.7) {
      const a = this.sparks.geometry.attributes.position;
      for (let i = 0; i < 30; i++) { a.setXYZ(i, p.x, p.y, p.z); this.sparkV[i].set((Math.random() - 0.5) * 2, Math.random() * 1.6, (Math.random() - 0.5) * 2); }
      a.needsUpdate = true; this.sparkLife = 0.5;
    }
  }

  finish() {
    const g = this.g;
    g.fadeTo(1, 4).then(() => {
      g.mode = 'end'; if (document.pointerLockElement) document.exitPointerLock();
      g.ui.showEnd({
        title: 'The Coral Kingdom',
        lines: [
          '“So, as I said he would, this man died in the night?” — “Yes, M. Aronnax.”',
          '“We dug the grave, and the polypi undertake to seal our dead for eternity.” And, burying his face quickly in his hands, he tried in vain to suppress a sob.',
          '“Your dead sleep quietly, at least, Captain, out of the reach of sharks.” — “Yes, sir, of sharks and men.”',
        ],
        cite: 'Part I, chapter XXIII',
      });
    });
  }

  dispose() {
    for (const o of this.objs) { this.g.ext.remove(o); o.traverse((x) => { if (x.isMesh && x.geometry && !x.isInstancedMesh) {} }); }
    this.objs.length = 0;
  }
}
