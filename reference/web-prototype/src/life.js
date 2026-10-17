// Living things: schools of fish that wheel and flee, medusae that pulse, polyps that hide.
import * as THREE from 'three';
import { makeMaterial } from './materials.js';
import { patchUnderwater } from './uw.js';

function fishMaterial(name) {
  // clone the prop material and add a swimming wiggle in the vertex shader
  const base = makeMaterial(name, false);
  const m = base.clone();
  m.vertexColors = true;
  patchUnderwater(m);
  const prev = m.onBeforeCompile;
  m.onBeforeCompile = (sh) => {
    prev(sh);
    sh.uniforms.uSwim = { value: 0 };
    m.userData.shader = sh;
    sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nuniform float uSwim;')
      .replace('#include <begin_vertex>', `#include <begin_vertex>
        float ph = uSwim * 9.0 + float(gl_InstanceID) * 1.7;
        transformed.z += sin(ph + position.x * 14.0) * 0.06 * smoothstep(0.1, -0.2, position.x);`);
  };
  m.customProgramCacheKey = () => 'fish' + name;
  return m;
}

export class FishSchool {
  constructor(props, name, count, center, radius = 4, depthBand = 2) {
    this.geo = props.geometry(name);
    this.mat = fishMaterial(props.items[name][0].matName);
    this.mesh = new THREE.InstancedMesh(this.geo, this.mat, count);
    this.mesh.castShadow = true; this.mesh.frustumCulled = false;
    this.fish = [];
    this.home = center.clone(); this.center = center.clone(); this.radius = radius; this.band = depthBand;
    for (let i = 0; i < count; i++) {
      const p = center.clone().add(new THREE.Vector3((Math.random() - 0.5) * radius * 2, (Math.random() - 0.5) * depthBand, (Math.random() - 0.5) * radius * 2));
      this.fish.push({ p, v: new THREE.Vector3((Math.random() - 0.5), 0, (Math.random() - 0.5)).normalize().multiplyScalar(0.8), s: 0.7 + Math.random() * 0.6, ph: Math.random() * 10 });
    }
    this.t = Math.random() * 100;
    this.M = new THREE.Matrix4(); this.Q = new THREE.Quaternion(); this.S = new THREE.Vector3();
  }
  update(dt, threat) {
    this.t += dt;
    // the school's centre wanders around its home
    this.center.set(this.home.x + Math.sin(this.t * 0.11) * this.radius * 1.5, this.home.y + Math.sin(this.t * 0.07) * this.band * 0.5, this.home.z + Math.cos(this.t * 0.09) * this.radius * 1.5);
    const tmp = new THREE.Vector3();
    const flee = threat && threat.distanceTo(this.center) < this.radius * 3;
    for (let i = 0; i < this.fish.length; i++) {
      const f = this.fish[i];
      // swirl around the centre, cohesion, a little noise
      tmp.subVectors(this.center, f.p);
      const d = tmp.length();
      const swirl = new THREE.Vector3(-tmp.z, 0, tmp.x).normalize();
      f.v.addScaledVector(tmp.normalize(), dt * 0.8 * Math.min(1, d / this.radius));
      f.v.addScaledVector(swirl, dt * 0.6);
      f.v.y += (Math.sin(this.t * 0.5 + f.ph) * 0.2 - f.v.y) * dt;
      if (flee) {
        const away = f.p.clone().sub(threat); const ad = away.length();
        if (ad < 4) f.v.addScaledVector(away.normalize(), dt * 6 * (1 - ad / 4));
      }
      const sp = f.v.length(); const maxv = flee ? 2.4 : 1.1;
      if (sp > maxv) f.v.multiplyScalar(maxv / sp);
      if (sp < 0.4) f.v.multiplyScalar(0.4 / Math.max(sp, 1e-3));
      f.p.addScaledVector(f.v, dt);
      // orient along velocity (fish front is +x in the model)
      const yaw = Math.atan2(-f.v.z, f.v.x);
      const pitch = Math.atan2(f.v.y, Math.hypot(f.v.x, f.v.z));
      this.Q.setFromEuler(new THREE.Euler(0, yaw, pitch, 'YZX'));
      this.S.setScalar(f.s);
      this.M.compose(f.p, this.Q, this.S);
      this.mesh.setMatrixAt(i, this.M);
    }
    this.mesh.instanceMatrix.needsUpdate = true;
    if (this.mat.userData.shader) this.mat.userData.shader.uniforms.uSwim.value = this.t;
  }
}

export class Medusae {
  constructor(props, count, area, ybase, yspan) {
    this.geo = props.geometry('jelly');
    this.mat = makeMaterial('M_jelly', false).clone();
    this.mat.color = new THREE.Color(0xe8c8d8); this.mat.emissive = new THREE.Color(0.1, 0.06, 0.12);
    patchUnderwater(this.mat);
    this.mesh = new THREE.InstancedMesh(this.geo, this.mat, count);
    this.mesh.frustumCulled = false;
    const cols = [0xf0c8d8, 0xc8d8f8, 0xe8e0f0, 0xf8d0c0];
    this.j = [];
    for (let i = 0; i < count; i++) {
      this.j.push({ p: new THREE.Vector3(area.x0 + Math.random() * (area.x1 - area.x0), ybase + Math.random() * yspan, area.z0 + Math.random() * (area.z1 - area.z0)), ph: Math.random() * 6, s: 0.6 + Math.random() * 1.2 });
      this.mesh.setColorAt(i, new THREE.Color(cols[i % cols.length]));
    }
    this.M = new THREE.Matrix4(); this.t = 0;
  }
  update(dt) {
    this.t += dt;
    for (let i = 0; i < this.j.length; i++) {
      const m = this.j[i];
      const pulse = Math.max(0, Math.sin(this.t * 1.4 + m.ph));
      m.p.y += (pulse * 0.25 - 0.06) * dt;
      m.p.x += Math.sin(this.t * 0.1 + m.ph) * 0.05 * dt;
      const sx = m.s * (1 + pulse * 0.15), sy = m.s * (1 - pulse * 0.12);
      this.M.compose(m.p, new THREE.Quaternion(), new THREE.Vector3(sx, sy, sx));
      this.mesh.setMatrixAt(i, this.M);
    }
    this.mesh.instanceMatrix.needsUpdate = true;
  }
}

// Polyps: white flowers in red cases that shrink back into stone when a hand approaches.
export class Polyps {
  constructor(props, spots) {
    // spots: array of { p: Vector3, n: count }
    this.list = [];
    for (const s of spots) for (let i = 0; i < s.n; i++) {
      const a = Math.random() * Math.PI * 2, r = Math.random() * (s.r || 0.35);
      this.list.push({ p: new THREE.Vector3(s.p.x + Math.cos(a) * r, s.p.y + Math.random() * (s.h || 0.3), s.p.z + Math.sin(a) * r), open: 1, target: 1, rot: Math.random() * 6, tilt: (Math.random() - 0.5) * 0.8, cool: 0 });
    }
    // the petals are the second material group; one mesh is enough for both colours via vertex colours
    const parts = props.items.polyp;
    this.meshes = parts.map((p) => { const m = new THREE.InstancedMesh(p.geometry, makeMaterial(p.matName, true), this.list.length); m.frustumCulled = false; return m; });
    this.group = new THREE.Group(); this.meshes.forEach((m) => this.group.add(m));
    this.M = new THREE.Matrix4();
  }
  update(dt, hand, onRetract) {
    let retracted = 0;
    for (let i = 0; i < this.list.length; i++) {
      const q = this.list[i];
      const near = hand && hand.distanceTo(q.p) < 1.25;
      if (near && q.target > 0.5) { q.target = 0; q.cool = 6 + Math.random() * 4; retracted++; }
      if (!near && q.target < 0.5) { q.cool -= dt; if (q.cool <= 0) q.target = 1; }
      q.open += (q.target - q.open) * Math.min(1, dt * (q.target > q.open ? 0.4 : 7));
      const s = 0.25 + 0.75 * q.open;
      this.M.compose(q.p, new THREE.Quaternion().setFromEuler(new THREE.Euler(q.tilt, q.rot, 0)), new THREE.Vector3(s, s * (0.3 + 0.7 * q.open), s));
      for (const m of this.meshes) m.setMatrixAt(i, this.M);
    }
    for (const m of this.meshes) m.instanceMatrix.needsUpdate = true;
    if (retracted && onRetract) onRetract(retracted);
  }
}
