// Divers in the Nautilus dress, built from instanced parts and animated procedurally.
// No faces: the copper helmet is all anyone ever sees of the crew (and of Captain Nemo outside).
import * as THREE from 'three';

const PARTS = ['diver_hips', 'diver_torso', 'diver_helmet', 'diver_tank', 'diver_upperarm', 'diver_forearm', 'diver_thigh', 'diver_shin', 'diver_boot', 'diver_lamp'];
const HELD = ['diver_stick', 'pickaxe', 'diver_gun'];

const POSES = {
  stand: { hipsY: 1.0, torso: 0.02, head: 0.0, sh: [0.05, 0.05], roll: [0.12, 0.12], el: [0.25, 0.25], hip: [0, 0], knee: [0.05, 0.05] },
  kneel: { hipsY: 0.52, torso: 0.0, head: 0.15, sh: [0.2, 0.2], roll: [0.15, 0.15], el: [0.7, 0.7], hip: [-1.55, -0.3], knee: [1.6, 2.6] },
  kneelCross: { hipsY: 0.52, torso: 0.05, head: 0.25, sh: [-0.6, -0.6], roll: [-0.55, -0.55], el: [1.9, 1.9], hip: [-1.55, -0.3], knee: [1.6, 2.6] },
  kneelExtend: { hipsY: 0.52, torso: -0.1, head: 0.05, sh: [-1.25, -1.25], roll: [0.1, 0.1], el: [0.1, 0.1], hip: [-1.55, -0.3], knee: [1.6, 2.6] },
  crossArms: { hipsY: 1.0, torso: 0.05, head: 0.2, sh: [-0.6, -0.6], roll: [-0.55, -0.55], el: [1.9, 1.9], hip: [0, 0], knee: [0.05, 0.05] },
  carry: { hipsY: 0.98, torso: 0.0, head: -0.1, sh: [-2.7, -2.7], roll: [0.15, 0.15], el: [1.2, 1.2], hip: [0, 0], knee: [0.1, 0.1] },
  beckon: { hipsY: 1.0, torso: 0.0, head: 0.0, sh: [0.05, -1.4], roll: [0.12, 0.2], el: [0.25, 0.6], hip: [0, 0], knee: [0.05, 0.05] },
  point: { hipsY: 1.0, torso: 0.0, head: 0.0, sh: [0.05, -1.45], roll: [0.12, 0.05], el: [0.25, 0.05], hip: [0, 0], knee: [0.05, 0.05] },
  write: { hipsY: 1.0, torso: 0.1, head: 0.2, sh: [0.05, -1.2], roll: [0.12, 0.15], el: [0.25, 0.7], hip: [0, 0], knee: [0.05, 0.05] },
  lean: { hipsY: 0.98, torso: 0.25, head: 0.3, sh: [-0.3, -0.5], roll: [0.2, 0.2], el: [0.6, 0.5], hip: [-0.2, 0.1], knee: [0.3, 0.2] },
  dig: { hipsY: 0.95, torso: 0.35, head: 0.2, sh: [-1.0, -1.0], roll: [-0.2, -0.2], el: [0.4, 0.4], hip: [-0.25, 0.1], knee: [0.35, 0.2] },
  lower: { hipsY: 0.8, torso: 0.45, head: 0.3, sh: [-0.9, -0.9], roll: [0.1, 0.1], el: [0.3, 0.3], hip: [-0.6, -0.3], knee: [0.9, 0.7] },
};
const lerp = (a, b, t) => a + (b - a) * t;

class Rig {
  constructor() {
    const O = () => new THREE.Object3D();
    this.root = O(); this.hips = O(); this.torso = O(); this.helmet = O(); this.tank = O();
    this.sh = [O(), O()]; this.ua = [O(), O()]; this.fa = [O(), O()]; this.hand = [O(), O()];
    this.th = [O(), O()]; this.sn = [O(), O()]; this.bt = [O(), O()]; this.lamp = O(); this.held = O();
    this.root.add(this.hips); this.hips.add(this.torso); this.torso.add(this.helmet, this.tank);
    for (let i = 0; i < 2; i++) {
      const s = i === 0 ? -1 : 1;
      this.sh[i].position.set(0.22 * s, 0.47, 0.0); this.torso.add(this.sh[i]);
      this.sh[i].add(this.ua[i]); this.fa[i].position.set(0, -0.29, 0); this.ua[i].add(this.fa[i]);
      this.hand[i].position.set(0, -0.36, 0.02); this.fa[i].add(this.hand[i]);
      this.th[i].position.set(0.1 * s, -0.1, 0); this.hips.add(this.th[i]);
      this.sn[i].position.set(0, -0.41, 0); this.th[i].add(this.sn[i]);
      this.bt[i].position.set(0, -0.4, 0); this.sn[i].add(this.bt[i]);
    }
    this.helmet.position.set(0, 0.76, 0.0);
    this.tank.position.set(0, 0.2, -0.14);
    this.lamp.position.set(0.15, -0.02, 0.12); this.hips.add(this.lamp);
    this.hand[1].add(this.held);
    this.held.rotation.set(-1.5, 0, 0);
  }
}

export class Diver {
  constructor(opts = {}) {
    this.rig = new Rig();
    this.pos = new THREE.Vector3(); this.yaw = 0; this.speed = 0; this.phase = Math.random() * 6;
    this.pose = { ...POSES.stand, sh: [...POSES.stand.sh], roll: [...POSES.stand.roll], el: [...POSES.stand.el], hip: [...POSES.stand.hip], knee: [...POSES.stand.knee] };
    this.poseName = 'stand'; this.poseRate = 1.5;
    this.held = opts.held || null; this.lampOn = opts.lamp ?? true; this.scale = opts.scale || 1;
    this.anim = null; this.t = 0; this.name = opts.name || 'crew';
    this.visible = true;
    this.headYaw = 0; this.lookAt = null;
  }
  setPose(name, rate = 1.5) { this.poseName = name; this.poseRate = rate; }
  update(dt, groundFn) {
    this.t += dt;
    const target = POSES[this.poseName] || POSES.stand;
    const k = Math.min(1, dt * this.poseRate);
    const P = this.pose;
    P.hipsY = lerp(P.hipsY, target.hipsY, k); P.torso = lerp(P.torso, target.torso, k); P.head = lerp(P.head, target.head, k);
    for (const key of ['sh', 'roll', 'el', 'hip', 'knee']) for (let i = 0; i < 2; i++) P[key][i] = lerp(P[key][i], target[key][i], k);
    const r = this.rig;
    const moving = this.speed > 0.05;
    // heavy, slow stride with lead soles
    this.phase += dt * (moving ? this.speed * 3.3 : 0);
    const sw = moving ? Math.min(1, this.speed / 0.9) : 0;
    const s = Math.sin(this.phase), c = Math.cos(this.phase);
    const g = groundFn ? groundFn(this.pos.x, this.pos.z) : this.pos.y;
    this.pos.y = g;
    r.root.position.copy(this.pos);
    r.root.rotation.set(0, this.yaw, 0);
    r.root.scale.setScalar(this.scale);
    const breath = Math.sin(this.t * 1.3) * 0.008;
    r.hips.position.set(0, P.hipsY + Math.abs(c) * 0.03 * sw + breath, 0);
    r.hips.rotation.set(0, s * 0.06 * sw, Math.sin(this.t * 0.4) * 0.01);
    r.torso.position.set(0, 0.02, 0);
    r.torso.rotation.set(P.torso + 0.05 * sw, -s * 0.08 * sw, 0);
    // the head turns inside the helmet; the helmet turns with the body (as it is screwed to the collar)
    let hy = 0;
    if (this.lookAt) {
      const d = new THREE.Vector3().subVectors(this.lookAt, this.pos);
      hy = Math.atan2(d.x, d.z) - this.yaw; hy = Math.atan2(Math.sin(hy), Math.cos(hy)); hy = THREE.MathUtils.clamp(hy, -0.6, 0.6);
    }
    this.headYaw = lerp(this.headYaw, hy, Math.min(1, dt * 2));
    r.helmet.rotation.set(P.head * 0.4, this.headYaw * 0.5, 0);
    for (let i = 0; i < 2; i++) {
      const side = i === 0 ? -1 : 1;
      const ph = i === 0 ? s : -s;
      let shx = P.sh[i] + ph * 0.3 * sw;
      let el = P.el[i] + Math.max(0, ph) * 0.2 * sw;
      if (this.poseName === 'beckon' && i === 1) el = P.el[i] + (Math.sin(this.t * 4) * 0.5 + 0.5) * 0.9;
      if (this.poseName === 'dig') { const d = Math.sin(this.t * 3.6); shx = P.sh[i] - 1.4 * Math.max(0, d); el = P.el[i] + 0.6 * Math.max(0, d); }
      if (this.poseName === 'write' && i === 1) { shx += Math.sin(this.t * 2.2) * 0.12; el += Math.cos(this.t * 3.1) * 0.15; }
      r.sh[i].rotation.set(shx, 0, P.roll[i] * side);
      r.fa[i].rotation.set(-el, 0, 0);
      r.th[i].rotation.set(P.hip[i] + (i === 0 ? -s : s) * 0.42 * sw, 0, 0);
      r.sn[i].rotation.set(P.knee[i] + Math.max(0, (i === 0 ? c : -c)) * 0.55 * sw, 0, 0);
      r.bt[i].rotation.set(-(P.hip[i] + P.knee[i]) * 0.25, 0, 0);
    }
    r.lamp.rotation.set(Math.sin(this.t * 1.7 + this.phase) * 0.12, 0, Math.cos(this.t * 1.3) * 0.08);
    r.root.updateMatrixWorld(true);
  }
  partMatrices() {
    const r = this.rig;
    return {
      diver_hips: [r.hips.matrixWorld], diver_torso: [r.torso.matrixWorld], diver_helmet: [r.helmet.matrixWorld], diver_tank: [r.tank.matrixWorld],
      diver_upperarm: [r.ua[0].matrixWorld, r.ua[1].matrixWorld], diver_forearm: [r.fa[0].matrixWorld, r.fa[1].matrixWorld],
      diver_thigh: [r.th[0].matrixWorld, r.th[1].matrixWorld], diver_shin: [r.sn[0].matrixWorld, r.sn[1].matrixWorld],
      diver_boot: [r.bt[0].matrixWorld, r.bt[1].matrixWorld], diver_lamp: this.lampOn !== null ? [r.lamp.matrixWorld] : [],
    };
  }
  handWorld() { return this.rig.hand[1].getWorldPosition(new THREE.Vector3()); }
  lampWorld() { return this.rig.lamp.getWorldPosition(new THREE.Vector3()); }
}

// Draws any number of divers with one InstancedMesh per part type.
export class DiverCrowd {
  constructor(props, max = 20, ext = true) {
    this.props = props; this.divers = []; this.group = new THREE.Group(); this.max = max;
    this.meshes = {};
    const zero = new THREE.Matrix4().makeScale(0, 0, 0);
    for (const name of [...PARTS, ...HELD, 'shroud']) {
      const per = name.includes('arm') || name.includes('thigh') || name.includes('shin') || name.includes('boot') ? 2 : 1;
      const count = name === 'shroud' ? 2 : max * per;
      const mats = Array.from({ length: count }, () => zero);
      const g = props.instanced(name, mats, { shadow: true, ext, chunk: 0 });
      g.children.forEach((im) => { im.frustumCulled = false; im.count = 0; });
      this.meshes[name] = g;
      this.group.add(g);
    }
    this.shrouds = [];
  }
  add(d) { this.divers.push(d); return d; }
  update(dt, groundFn) {
    const counts = {};
    const setM = (name, m) => {
      const g = this.meshes[name]; const i = counts[name] = (counts[name] || 0);
      for (const im of g.children) im.setMatrixAt(i, m);
      counts[name] = i + 1;
    };
    for (const d of this.divers) {
      if (!d.visible) continue;
      d.update(dt, groundFn);
      const pm = d.partMatrices();
      for (const k in pm) for (const m of pm[k]) setM(k, m);
      if (d.held) setM(d.held, d.rig.held.matrixWorld);
    }
    for (const s of this.shrouds) if (s.visible) setM('shroud', s.matrix);
    for (const name in this.meshes) for (const im of this.meshes[name].children) { im.count = counts[name] || 0; im.instanceMatrix.needsUpdate = true; }
  }
}
export { POSES };
