// The Nautilus: loads the Blender model, splits interior (air) and exterior (water), merges static
// geometry by material, and wires every interactive thing the book lets Aronnax touch.
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import { RectAreaLightUniformsLib } from 'three/examples/jsm/lights/RectAreaLightUniformsLib.js';
import { makeMaterial } from './materials.js';
import { quadTris } from './collision.js';
import { bus } from './bus.js';
import { mulberry32 } from './noise.js';

export const b2t = (x, y, z) => new THREE.Vector3(x, z, -y);

const DOOR_SWING = {
  IA_door_aronnax: -1, IA_door_saloonfore: 1, IA_door_library: 1, IA_door_waist: 1, IA_door_wardrobe: 1,
  IA_door_lockInner: 1, IA_door_lockOuter: -1, IA_door_nemo: 1, IA_door_nemosaloon: 1,
};

function normalizeGeometry(g) {
  const n = g.attributes.position.count;
  if (!g.attributes.normal) g.computeVertexNormals();
  if (!g.attributes.uv) g.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(n * 2), 2));
  const c = g.attributes.color;
  const out = new Float32Array(n * 3);
  if (c) {
    for (let i = 0; i < n; i++) { out[i * 3] = c.getX(i); out[i * 3 + 1] = c.getY(i); out[i * 3 + 2] = c.getZ(i); }
  } else out.fill(1);
  g.setAttribute('color', new THREE.BufferAttribute(out, 3));
  for (const k of Object.keys(g.attributes)) if (!['position', 'normal', 'uv', 'color'].includes(k)) g.deleteAttribute(k);
  if (!g.index) {
    const idx = new Uint32Array(n); for (let i = 0; i < n; i++) idx[i] = i; g.setIndex(new THREE.BufferAttribute(idx, 1));
  }
  return g;
}

function dialTexture(kind) {
  const c = document.createElement('canvas'); c.width = c.height = 256;
  const x = c.getContext('2d');
  x.fillStyle = '#e9e1c8'; x.beginPath(); x.arc(128, 128, 126, 0, 7); x.fill();
  x.strokeStyle = '#2a2420'; x.fillStyle = '#2a2420';
  const ticks = kind === 'clock' ? 24 : kind === 'chrono' ? 12 : 30;
  const span = kind === 'clock' || kind === 'chrono' ? Math.PI * 2 : Math.PI * 1.5;
  const a0 = kind === 'clock' || kind === 'chrono' ? -Math.PI / 2 : Math.PI * 0.75;
  for (let i = 0; i <= ticks; i++) {
    if ((kind === 'clock' || kind === 'chrono') && i === ticks) break;
    const a = a0 + span * i / ticks;
    const major = i % (kind === 'clock' ? 2 : 5) === 0;
    x.lineWidth = major ? 4 : 2;
    x.beginPath(); x.moveTo(128 + Math.cos(a) * (major ? 92 : 102), 128 + Math.sin(a) * (major ? 92 : 102)); x.lineTo(128 + Math.cos(a) * 114, 128 + Math.sin(a) * 114); x.stroke();
    if (major) {
      x.font = 'bold 19px Georgia, serif'; x.textAlign = 'center'; x.textBaseline = 'middle';
      let label = '';
      if (kind === 'clock') label = String(i);
      else if (kind === 'manometer') label = String(i * 10);
      else if (kind === 'speed') label = String(i * 2);
      else if (kind === 'lockgauge') label = String(i / 5);
      else if (kind === 'barometer') label = String(720 + i * 2);
      if (label) x.fillText(label, 128 + Math.cos(a) * 74, 128 + Math.sin(a) * 74);
    }
  }
  x.font = 'italic 15px Georgia, serif'; x.textAlign = 'center';
  const names = { manometer: 'Manomètre · mètres', clock: 'XXIV heures', speed: 'Milles à l’heure', lockgauge: 'Atmosphères', barometer: 'Baromètre', chrono: '' };
  x.fillText(names[kind] || '', 128, 178);
  x.lineWidth = 3; x.beginPath(); x.arc(128, 128, 120, 0, 7); x.stroke();
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4;
  return t;
}

export class Nautilus {
  constructor() {
    this.root = new THREE.Object3D();   // placement transform
    this.int = new THREE.Group();       // goes into the interior scene
    this.ext = new THREE.Group();       // goes into the exterior (water) scene
    this.ia = [];                       // interactable descriptors
    this.doors = {};
    this.needles = [];
    this.colliderGeos = [];             // { geo (local), surfMat }
    this.state = { ceiling: 1, panels: 0, panelsTarget: 0, depth: 9, speed: 0, lockWater: 0, lockPressure: 1 };
    this.time = 0;
    this.lightEmitters = [];            // interior point light positions (local)
  }

  async load(url = 'assets/nautilus.json') {
    RectAreaLightUniformsLib.init();
    const gltf = await new GLTFLoader().loadAsync(url);
    const scene = gltf.scene;
    scene.updateMatrixWorld(true);
    const statics = {}; // key zone|mat -> [geo]
    const top = scene.children.slice();
    for (const node of top) {
      const ud = node.userData || {};
      const ext = ud.zone === 'ext';
      const meshes = [];
      node.traverse((o) => { if (o.isMesh) meshes.push(o); });
      if (ud.ia || ud.needle || ud.spin) {
        for (const m of meshes) {
          normalizeGeometry(m.geometry);
          m.material = makeMaterial(m.material.name, ext, m.material);
          if (m.material.name === 'M_brass' && ud.door) m.castShadow = true;
        }
        (ext ? this.ext : this.int).add(node);
        this.registerInteractive(node, ext);
        if (ud.door) node.userData.closedQuat = node.quaternion.clone();
        continue;
      }
      for (const m of meshes) {
        const g = normalizeGeometry(m.geometry.clone()).applyMatrix4(m.matrixWorld);
        const key = (ext ? 'e|' : 'i|') + m.material.name;
        (statics[key] ||= []).push(g);
        if (ud.col) this.colliderGeos.push({ geo: g, mat: m.material.name, ext });
      }
      if (ud.pictures) this.pictures = JSON.parse(ud.pictures);
      if (ud.shelves) this.shelves = JSON.parse(ud.shelves);
      if (ud.cases) this.cases = JSON.parse(ud.cases.replace(/\(/g, '[').replace(/\)/g, ']'));
      if (ud.lights) this.lightEmitters.push(...JSON.parse(ud.lights).map((p) => b2t(...p)));
      if (ud.lantern) this.lanternPos = b2t(...JSON.parse(ud.lantern));
    }
    for (const key in statics) {
      const [z, name] = key.split('|');
      const geo = mergeGeometries(statics[key], false);
      const mesh = new THREE.Mesh(geo, makeMaterial(name, z === 'e'));
      mesh.name = 'static_' + key;
      mesh.matrixAutoUpdate = false;
      if (z === 'e') { mesh.castShadow = true; mesh.receiveShadow = true; }
      (z === 'e' ? this.ext : this.int).add(mesh);
    }
    // extra emitters for rooms
    this.lightEmitters.push(b2t(19.9, 0.4, 2.35), b2t(16.4, 0.4, 2.5), b2t(-19.0, -1.6, 2.35), b2t(-18.2, 0.6, 2.35), b2t(9.55, -2.2, 3.2), b2t(9.55, 2.2, 3.2));
    this.buildDetails();
    this.buildLights();
    return this;
  }

  registerInteractive(node, ext) {
    const ud = node.userData;
    if (ud.needle) {
      const box = new THREE.Box3().setFromObject(node);
      const size = box.getSize(new THREE.Vector3());
      const r = Math.max(size.y, 0.01) / 0.93;
      this.needles.push({ node, kind: ud.needle, r, base: node.quaternion.clone() });
      const face = new THREE.Mesh(new THREE.CircleGeometry(r * 0.86, 40), new THREE.MeshStandardMaterial({ map: dialTexture(ud.needle.startsWith('chrono') ? 'chrono' : ud.needle), roughness: 0.6 }));
      // needle local +X is the facing direction (Blender X) for X-facing dials
      const dir = new THREE.Vector3(1, 0, 0).applyQuaternion(node.quaternion);
      const facingSign = node.position.x - Math.round(node.position.x * 0) ; // unused
      face.position.copy(node.position);
      // the dial faces outward from its wall: decide by which side the needle sits relative to the dial mount
      const out = this._dialOutward(node);
      face.position.addScaledVector(out, -0.004);
      face.lookAt(face.position.clone().add(out));
      (ext ? this.ext : this.int).add(face);
      if (ud.ia) this.ia.push({ obj: node, kind: ud.ia, ext, label: this.labelFor(ud.ia), extra: face });
      return;
    }
    const kind = ud.ia;
    if (ud.door) this.doors[node.name] = { node, open: 0, target: 0, swing: DOOR_SWING[node.name] ?? 1, kind };
    if (ud.spin) this.screw = node;
    if (kind === 'panel') { (this.panels ||= []).push({ node, x0: node.position.x }); return; }
    if (kind === 'ceiling') { this.ceilingMesh = node.isMesh ? node : node.children[0]; return; }
    this.ia.push({ obj: node, kind, ext, label: this.labelFor(kind, node.name) });
  }
  _dialOutward(node) {
    // the needle sits 0.046 m in front of its dial; dials on the saloon aft wall face +x, on the captain's board -x
    const p = node.position;
    if (p.x < 5.2 && p.x > 4.9) return new THREE.Vector3(1, 0, 0);
    if (p.x < -18 && p.x > -18.4) return new THREE.Vector3(-1, 0, 0);
    return new THREE.Vector3(-1, 0, 0);
  }

  labelFor(kind, name = '') {
    const L = {
      door: 'Open the door', doorLocked: 'Try the door', lockInner: 'Close the watertight door', lockOuter: 'Open the outer door',
      ceilingSwitch: 'Luminous ceiling', panelLever: 'Iron panels', valve: 'Turn the tap', pump: 'Press the knob',
      note: 'Read the note', organ: 'Sit at the organ', instr_manometer: 'Manometer', instr_clock: 'Electric clock',
      instr_speed: 'Speed dial', instr_barometer: 'Barometer', instr_lockgauge: 'Pressure gauge',
    };
    return L[kind] || kind;
  }

  buildDetails() {
    const rnd = mulberry32(21);
    // ---- paintings (real works by painters Verne names, The Met, CC0)
    this.paintingMeshes = [];
    if (this.pictures) {
      const loader = new THREE.TextureLoader();
      fetch('assets/paint/paintings.json').then((r) => r.json()).then((list) => {
        this.pictures.forEach((p, i) => {
          const info = list[i % list.length];
          const t = loader.load('assets/paint/' + info.file);
          t.colorSpace = THREE.SRGBColorSpace;
          // cover-fit the painting into the frame
          const fa = p.w / p.h, ia = info.w / info.h;
          if (ia > fa) { t.repeat.set(fa / ia, 1); t.offset.set((1 - fa / ia) / 2, 0); } else { t.repeat.set(1, ia / fa); t.offset.set(0, (1 - ia / fa) / 2); }
          const m = new THREE.Mesh(new THREE.PlaneGeometry(p.w, p.h), new THREE.MeshStandardMaterial({ map: t, roughness: 0.55, color: 0xb0aaa0 }));
          const c = b2t(...p.c), n = b2t(...p.n);
          m.position.copy(c); m.lookAt(c.clone().add(n));
          m.userData.painting = info;
          this.int.add(m); this.paintingMeshes.push(m);
          this.ia.push({ obj: m, kind: 'painting', ext: false, label: info.artist, info });
        });
      }).catch(() => {});
    }
    // ---- twelve thousand volumes (instanced)
    if (this.shelves) {
      const books = [];
      const pal = [0x4a1a14, 0x2c3a24, 0x3a2a1a, 0x1a1a22, 0x5a3a20, 0x6a5030, 0x22303a, 0x3c1c2c, 0x4a4030];
      for (const s of this.shelves) {
        let a = s.a0 + 0.04;
        while (a < s.a1 - 0.06) {
          const th = 0.025 + rnd() * 0.04, h = 0.24 + rnd() * 0.15, d = 0.17 + rnd() * 0.1;
          if (rnd() < 0.03) { a += 0.1 + rnd() * 0.2; continue; }
          const lean = rnd() < 0.04 ? (rnd() - 0.5) * 0.4 : 0;
          books.push({ s, a: a + th / 2, th, h, d, col: pal[Math.floor(rnd() * pal.length)], lean });
          a += th + 0.002;
        }
      }
      const g = new THREE.BoxGeometry(1, 1, 1);
      const spine = document.createElement('canvas'); spine.width = 64; spine.height = 256;
      const sx = spine.getContext('2d'); sx.fillStyle = '#cfcfcf'; sx.fillRect(0, 0, 64, 256);
      sx.fillStyle = '#ffffff'; for (const y of [16, 26, 220, 230]) sx.fillRect(0, y, 64, 5);
      sx.fillStyle = '#ececec'; sx.fillRect(6, 60, 52, 50);
      const stex = new THREE.CanvasTexture(spine); stex.colorSpace = THREE.SRGBColorSpace;
      const im = new THREE.InstancedMesh(g, new THREE.MeshStandardMaterial({ map: stex, roughness: 0.6 }), books.length);
      const M = new THREE.Matrix4(), Q = new THREE.Quaternion(), S = new THREE.Vector3(), P = new THREE.Vector3(), C = new THREE.Color();
      books.forEach((b, i) => {
        const s = b.s;
        let x, y;
        if (s.ax === 'y') { x = b.a; y = s.c + s.d * (b.d / 2 + 0.02); Q.setFromEuler(new THREE.Euler(0, 0, 0)); S.set(b.th, b.h, b.d); }
        else { y = b.a; x = s.c + s.d * (b.d / 2 + 0.02); S.set(b.d, b.h, b.th); }
        P.copy(b2t(x, y, s.z + b.h / 2));
        const e = s.ax === 'y' ? new THREE.Euler(0, 0, b.lean) : new THREE.Euler(b.lean, 0, 0);
        Q.setFromEuler(e);
        M.compose(P, Q, S); im.setMatrixAt(i, M); im.setColorAt(i, C.setHex(b.col));
      });
      im.instanceMatrix.needsUpdate = true;
      this.int.add(im);
    }
    // ---- specimens in the glass cases
    if (this.cases) {
      const shellG = new THREE.ConeGeometry(0.03, 0.07, 7, 1); shellG.rotateZ(Math.PI / 2);
      const pearlG = new THREE.SphereGeometry(0.012, 8, 6);
      const coralG = new THREE.CylinderGeometry(0.004, 0.01, 0.12, 5);
      const mk = (geo, col, rough, n) => new THREE.InstancedMesh(geo, new THREE.MeshStandardMaterial({ color: col, roughness: rough, metalness: 0.0 }), n);
      const shells = mk(shellG, 0xffffff, 0.45, 160), pearls = mk(pearlG, 0xf2eee6, 0.15, 220), corals = mk(coralG, 0xc4402c, 0.6, 120);
      let ns = 0, np = 0, nc = 0;
      const M = new THREE.Matrix4(), C = new THREE.Color();
      const shellCols = [0xe8d8c0, 0xc8784a, 0xd4b080, 0xf0e8e0, 0x9a5a3a, 0xb8c0a8];
      for (const [x0, x1, y0, y1] of this.cases) {
        const area = (x1 - x0) * (y1 - y0);
        const nShell = Math.floor(area * 90), nPearl = Math.floor(area * 60), nCor = Math.floor(area * 30);
        for (let k = 0; k < nShell && ns < 160; k++, ns++) {
          M.compose(b2t(x0 + 0.05 + rnd() * (x1 - x0 - 0.1), y0 + 0.05 + rnd() * (y1 - y0 - 0.1), 0.83), new THREE.Quaternion().setFromEuler(new THREE.Euler(0, rnd() * 6, 0)), new THREE.Vector3(1, 1, 1).multiplyScalar(0.6 + rnd() * 0.9));
          shells.setMatrixAt(ns, M); shells.setColorAt(ns, C.setHex(shellCols[Math.floor(rnd() * shellCols.length)]));
        }
        for (let k = 0; k < nPearl && np < 220; k++, np++) {
          M.compose(b2t(x0 + 0.05 + rnd() * (x1 - x0 - 0.1), y0 + 0.05 + rnd() * (y1 - y0 - 0.1), 0.815), new THREE.Quaternion(), new THREE.Vector3(1, 1, 1).multiplyScalar(0.6 + rnd() * 1.4));
          pearls.setMatrixAt(np, M); pearls.setColorAt(np, C.setHSL(0.1 + rnd() * 0.5, 0.15, 0.82 + rnd() * 0.12));
        }
        for (let k = 0; k < nCor && nc < 120; k++, nc++) {
          M.compose(b2t(x0 + 0.05 + rnd() * (x1 - x0 - 0.1), y0 + 0.05 + rnd() * (y1 - y0 - 0.1), 0.86), new THREE.Quaternion().setFromEuler(new THREE.Euler((rnd() - 0.5) * 0.8, 0, (rnd() - 0.5) * 0.8)), new THREE.Vector3(1, 1, 1));
          corals.setMatrixAt(nc, M); corals.setColorAt(nc, C.setHSL(0.0 + rnd() * 0.05, 0.6, 0.35 + rnd() * 0.2));
        }
      }
      shells.count = ns; pearls.count = np; corals.count = nc;
      this.int.add(shells, pearls, corals);
    }
    // ---- the electrically lit jet of the fountain
    const jetMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(0.9, 1.2, 1.3), transparent: true, opacity: 0.55, depthWrite: false, blending: THREE.AdditiveBlending });
    const jet = new THREE.Mesh(new THREE.CylinderGeometry(0.008, 0.016, 1.1, 8, 1, true), jetMat);
    jet.position.copy(b2t(9.55, 0.0, 1.22 + 0.55));
    this.int.add(jet); this.jet = jet;
    // airlock water surface (rises when the cell floods)
    const wm = new THREE.MeshStandardMaterial({ color: 0x0c1a1e, roughness: 0.15, metalness: 0.6, transparent: true, opacity: 0.85, side: THREE.DoubleSide });
    this.lockWater = new THREE.Mesh(new THREE.PlaneGeometry(2.2, 1.3, 8, 6), wm);
    this.lockWater.rotation.x = -Math.PI / 2;
    this.lockWater.position.copy(b2t(-19.3, 2.8, 0.0));
    this.lockWater.visible = false;
    this.int.add(this.lockWater);
  }

  buildLights() {
    // luminous ceiling of the saloon: a soft area light
    const rect = new THREE.RectAreaLight(0xfff1dc, 10.0, 7.2, 3.9);
    rect.position.copy(b2t(9.55, 0, 4.42));
    rect.lookAt(rect.position.clone().add(new THREE.Vector3(0, -1, 0)));
    this.int.add(rect); this.ceilingLight = rect;
    // pooled point lights follow the player through the rooms
    this.pool = [];
    for (let i = 0; i < 4; i++) {
      const l = new THREE.PointLight(0xffe2b8, 0, 9, 2);
      l.userData.medium = 'air'; l.userData.volumetric = 0.12;
      this.int.add(l); this.pool.push(l);
    }
    // the faint light that comes through the round port of the cell's inner door
    const port = new THREE.PointLight(0xffd8a8, 0.9, 3.2, 2);
    port.position.copy(b2t(-19.3, 2.35, 1.5)); this.int.add(port); this.portLight = port;
    const hemi = new THREE.HemisphereLight(0x8a8478, 0x2a2420, 0.25);
    this.int.add(hemi); this.intHemi = hemi;
    // exterior: the lantern, and the glow of the saloon windows into the sea
    const lantern = new THREE.SpotLight(0xe6f0ff, 900, 0, 0.42, 0.55, 2);
    lantern.position.copy(this.lanternPos || b2t(11, 0, 5.6));
    lantern.target.position.copy(lantern.position.clone().add(new THREE.Vector3(14, -3.2, 0)));
    lantern.castShadow = true; lantern.shadow.mapSize.set(512, 512); lantern.shadow.camera.near = 0.5; lantern.shadow.camera.far = 80; lantern.shadow.bias = -0.0005;
    lantern.userData.volumetric = 1.0;
    this.ext.add(lantern, lantern.target); this.lantern = lantern;
    // daylight from the sea pouring in through the crystal when the panels are open
    this.beams = [];
    for (const s of [1, -1]) {
      const b = new THREE.SpotLight(0x9fd0d8, 0, 0, 0.62, 0.5, 2);
      b.position.copy(b2t(9.55, 4.6 * s, 3.4));
      b.target.position.copy(b2t(9.55, -1.5 * s, 0.0));
      b.castShadow = true; b.shadow.mapSize.set(512, 512); b.shadow.camera.near = 0.5; b.shadow.camera.far = 14; b.shadow.bias = -0.0008;
      b.userData.medium = 'air'; b.userData.volumetric = 1.0;
      this.int.add(b, b.target); this.beams.push(b);
    }
    this.outside = { brightness: 1, color: new THREE.Color(0x9fd0d8) };
    this.windowLights = [];
    for (const s of [1, -1]) {
      const wl = new THREE.SpotLight(0xffe6c4, 0, 0, 0.95, 0.9, 2);
      wl.position.copy(b2t(9.55, 2.0 * s, 1.9));
      wl.target.position.copy(b2t(9.55, 9 * s, 0.6));
      wl.userData.volumetric = 0.6;
      this.ext.add(wl, wl.target); this.windowLights.push(wl);
    }
  }

  // place both halves in the world
  place(pos, yaw = 0) {
    this.root.position.copy(pos); this.root.rotation.set(0, yaw, 0); this.root.updateMatrixWorld(true);
    for (const g of [this.int, this.ext]) { g.position.copy(pos); g.rotation.set(0, yaw, 0); g.updateMatrixWorld(true); }
  }
  toWorld(v) { return v.clone().applyMatrix4(this.root.matrixWorld); }
  airBox() {
    return { matrixInv: this.root.matrixWorld.clone().invert(), min: new THREE.Vector3(-21.3, -0.2, -3.5), max: new THREE.Vector3(21.3, 4.8, 3.25), on: true };
  }
  isInside(p) {
    const l = p.clone().applyMatrix4(this.root.matrixWorld.clone().invert());
    return l.x > -21.3 && l.x < 21.3 && l.y > -0.2 && l.y < 4.8 && l.z > -3.5 && l.z < 3.25;
  }
  localOf(p) { return p.clone().applyMatrix4(this.root.matrixWorld.clone().invert()); }

  addColliders(world) {
    for (const c of this.colliderGeos) {
      const m = new THREE.Mesh(c.geo, makeMaterial(c.mat));
      m.matrixAutoUpdate = false; m.matrix.copy(this.root.matrixWorld); m.matrixWorld.copy(this.root.matrixWorld);
      m.updateMatrixWorld = () => {};
      world.addMesh(m);
    }
    // closed doors block the way
    world.dynamicOwners.push((out) => {
      for (const k in this.doors) {
        const d = this.doors[k];
        if (d.open > 0.25) continue;
        d.node.updateMatrixWorld(true);
        const box = new THREE.Box3().setFromObject(d.node);
        const c = box.getCenter(new THREE.Vector3()), s = box.getSize(new THREE.Vector3());
        // thin doors: a vertical quad through the centre along the larger horizontal axis
        let a, b, cc, dd;
        if (s.x > s.z) { a = new THREE.Vector3(box.min.x, box.min.y, c.z); b = new THREE.Vector3(box.max.x, box.min.y, c.z); cc = new THREE.Vector3(box.max.x, box.max.y, c.z); dd = new THREE.Vector3(box.min.x, box.max.y, c.z); }
        else { a = new THREE.Vector3(c.x, box.min.y, box.min.z); b = new THREE.Vector3(c.x, box.min.y, box.max.z); cc = new THREE.Vector3(c.x, box.max.y, box.max.z); dd = new THREE.Vector3(c.x, box.max.y, box.min.z); }
        out.push(...quadTris(a, b, cc, dd));
      }
    });
  }

  interact(entry, player) {
    const k = entry.kind;
    if (k === 'door') { const d = this.doors[entry.obj.name]; d.target = d.target > 0.5 ? 0 : 1; bus.emit('sfx', d.node.userData.door === 'iron' ? 'doorIron' : 'doorWood', this.worldPosOf(entry.obj)); return; }
    if (k === 'doorLocked') { bus.emit('sfx', 'doorLocked', this.worldPosOf(entry.obj)); bus.emit('say', entry.obj.name === 'IA_door_nemo' || entry.obj.name === 'IA_door_nemosaloon' ? 'The captain’s door. Shut.' : 'Shut. I could hear nothing beyond it.'); return; }
    if (k === 'ceilingSwitch') { this.state.ceiling = this.state.ceiling > 0.5 ? 0 : 1; this.flipLever(entry.obj); bus.emit('sfx', 'switch', this.worldPosOf(entry.obj)); bus.emit('ceiling', this.state.ceiling); return; }
    if (k === 'panelLever') { this.state.panelsTarget = this.state.panelsTarget > 0.5 ? 0 : 1; this.flipLever(entry.obj); bus.emit('sfx', 'lever', this.worldPosOf(entry.obj)); bus.emit('panels', this.state.panelsTarget); return; }
    bus.emit('interact', k, entry, player);
  }
  flipLever(obj) { obj.userData.flip = !obj.userData.flip; }
  worldPosOf(o) { return o.getWorldPosition(new THREE.Vector3()); }

  setDoor(name, open) { const d = this.doors[name]; if (d) d.target = open ? 1 : 0; }

  update(dt, playerPos) {
    this.time += dt;
    const st = this.state;
    // doors swing (heavier for iron)
    for (const k in this.doors) {
      const d = this.doors[k];
      const sp = d.node.userData.door === 'iron' ? 0.9 : 1.6;
      d.open += Math.sign(d.target - d.open) * Math.min(Math.abs(d.target - d.open), dt * sp);
      const e = d.open * d.open * (3 - 2 * d.open);
      d.node.quaternion.copy(d.node.userData.closedQuat).multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), d.swing * e * 1.75));
    }
    // levers
    for (const e of this.ia) if (e.kind === 'ceilingSwitch' || e.kind === 'panelLever') {
      const tgt = e.obj.userData.flip ? -0.9 : 0;
      e.obj.userData.ang = (e.obj.userData.ang ?? 0) + (tgt - (e.obj.userData.ang ?? 0)) * Math.min(1, dt * 8);
      e.obj.rotation.z = e.obj.userData.ang;
    }
    // luminous ceiling fades; panels slide back into the hull
    st.ceilingVis = (st.ceilingVis ?? 1) + ((st.ceiling) - (st.ceilingVis ?? 1)) * Math.min(1, dt * 5);
    this.ceilingLight.intensity = 10.0 * st.ceilingVis;
    if (this.ceilingMesh) this.ceilingMesh.material.color.setScalar(0.08 + 1.5 * st.ceilingVis);
    if (this.intHemi) this.intHemi.intensity = 0.06 + 0.2 * st.ceilingVis;
    const prevP = st.panels;
    st.panels += Math.sign(st.panelsTarget - st.panels) * Math.min(Math.abs(st.panelsTarget - st.panels), dt / 5.5);
    st.panelsMoving = Math.abs(st.panels - prevP) > 1e-6;
    if (this.panels) for (const p of this.panels) {
      const e = st.panels * st.panels * (3 - 2 * st.panels);
      p.node.position.x = p.x0 + e * 3.4;
    }
    for (let i = 0; i < this.windowLights.length; i++) this.windowLights[i].intensity = 60 * st.panels * (0.15 + 0.85 * st.ceilingVis);
    for (const b of this.beams) { b.intensity = 26 * st.panels * this.outside.brightness; b.color.copy(this.outside.color); }
    // instruments read the real state
    for (const n of this.needles) {
      let a = 0;
      const k = n.kind;
      if (k === 'manometer') a = -Math.PI * 0.75 + Math.min(1, st.depth / 300) * Math.PI * 1.5;
      else if (k === 'clock') { const h = (st.clockHours ?? 10) + this.time / 3600; a = (h / 24) * Math.PI * 2; }
      else if (k === 'speed') a = -Math.PI * 0.75 + Math.min(1, st.speed / 60) * Math.PI * 1.5;
      else if (k === 'barometer') a = 0.3 + Math.sin(this.time * 0.01) * 0.02;
      else if (k === 'lockgauge') a = -Math.PI * 0.75 + Math.min(1, st.lockPressure / 6) * Math.PI * 1.5;
      n.node.quaternion.copy(n.base).multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), -a));
    }
    if (this.jet) { this.jet.scale.y = 0.92 + Math.sin(this.time * 9) * 0.04; this.jet.material.opacity = 0.45 + Math.sin(this.time * 13) * 0.08; }
    if (this.screw) this.screw.rotation.x += dt * st.speed * 0.4;
    // airlock water
    this.lockWater.visible = st.lockWater > 0.01;
    this.lockWater.position.y = st.lockWater * 2.32 + 0.01;
    // light pool: nearest emitters to the player
    if (playerPos) {
      const lp = this.localOf(playerPos);
      const sorted = this.lightEmitters.map((p) => ({ p, d: p.distanceToSquared(lp) })).sort((a, b) => a.d - b.d);
      for (let i = 0; i < this.pool.length; i++) {
        const l = this.pool[i]; const e = sorted[i];
        if (!e) { l.intensity = 0; continue; }
        l.position.copy(e.p);
        l.intensity = (e.d < 260 ? 11 : 0) * (st.interiorPower ?? 1);
      }
    }
  }
  interactables() { return this.ia; }
}
