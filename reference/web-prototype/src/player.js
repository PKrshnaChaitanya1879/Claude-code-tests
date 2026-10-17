// First-person body. Two media: in air (inside the Nautilus) a measured BioShock-like walk;
// in water (the diving dress, lead soles, Rouquayrol tank) slow, heavy and drifting.
import * as THREE from 'three';
import { SURF } from './collision.js';

const AIR = { walk: 2.4, run: 3.7, accel: 16, friction: 12, gravity: 9.81, jump: 3.0, air: 2.0, bobFreq: 1.9, bobAmp: 0.035 };
const WATER = { walk: 1.05, run: 1.45, accel: 1.6, friction: 1.9, gravity: 2.4, jump: 2.2, air: 0.5, bobFreq: 0.85, bobAmp: 0.055 };

export class Player {
  constructor(camera, world, input) {
    this.camera = camera; this.world = world; this.input = input;
    this.pos = new THREE.Vector3();          // feet
    this.vel = new THREE.Vector3();
    this.yaw = 0; this.pitch = 0;
    this.radius = 0.26; this.height = 1.72; this.eye = 1.62;
    this.onGround = false; this.medium = 'air';
    this.bobT = 0; this.stepPhase = 0; this.lastStepSign = 1;
    this.crouch = 0; this.kneel = 0;
    this.locked = false;      // cutscene control
    this.lookLocked = false;
    this.onStep = null;       // (surface, intensity) => {}
    this.onLand = null;
    this.surface = SURF.none;
    this.sway = new THREE.Vector3();
    this.shake = 0;
    this.speedScale = 1;
    this.ladder = null;       // { x, z, y0, y1, yawFace }
    this.lookTarget = null;   // optional point to ease the view towards (cutscenes)
    this._seg = new THREE.Line3(new THREE.Vector3(), new THREE.Vector3());
  }
  setMedium(m) { this.medium = m; }
  get P() { return this.medium === 'water' ? WATER : AIR; }
  teleport(p, yaw = this.yaw, pitch = 0) { this.pos.copy(p); this.vel.set(0, 0, 0); this.yaw = yaw; this.pitch = pitch; }

  update(dt) {
    const inp = this.input, P = this.P;
    // look
    if (!this.lookLocked) {
      const sens = inp.sensitivity * 0.0022;
      this.yaw -= inp.mouseDX * sens;
      this.pitch -= inp.mouseDY * sens * (inp.invertY ? -1 : 1);
      this.pitch = THREE.MathUtils.clamp(this.pitch, -1.45, 1.45);
    }
    inp.mouseDX = 0; inp.mouseDY = 0;
    if (this.lookTarget) {
      const d = new THREE.Vector3().subVectors(this.lookTarget, this.camera.position);
      const ty = Math.atan2(-d.x, -d.z), tp = Math.atan2(d.y, Math.hypot(d.x, d.z));
      let dy = ty - this.yaw; dy = Math.atan2(Math.sin(dy), Math.cos(dy));
      this.yaw += dy * Math.min(1, dt * 1.8); this.pitch += (tp - this.pitch) * Math.min(1, dt * 1.8);
    }
    // wish direction
    let fx = 0, fz = 0;
    if (!this.locked) {
      if (inp.key('KeyW') || inp.key('ArrowUp')) fz -= 1;
      if (inp.key('KeyS') || inp.key('ArrowDown')) fz += 1;
      if (inp.key('KeyA') || inp.key('ArrowLeft')) fx -= 1;
      if (inp.key('KeyD') || inp.key('ArrowRight')) fx += 1;
    }
    const wish = new THREE.Vector3(fx, 0, fz);
    if (wish.lengthSq() > 0) wish.normalize().applyAxisAngle(new THREE.Vector3(0, 1, 0), this.yaw);
    const crouching = !this.locked && (inp.key('KeyC') || inp.key('ControlLeft'));
    this.crouch += ((crouching ? 1 : 0) - this.crouch) * Math.min(1, dt * 8);
    const running = !this.locked && inp.key('ShiftLeft');
    const maxSpeed = (running ? P.run : P.walk) * (1 - this.crouch * 0.45) * this.speedScale;

    if (this.ladder) { this.updateLadder(dt, fz); return this.updateCamera(dt); }

    const hv = new THREE.Vector3(this.vel.x, 0, this.vel.z);
    const target = wish.multiplyScalar(maxSpeed);
    const accel = this.onGround ? P.accel : P.air;
    const diff = target.clone().sub(hv);
    const maxDv = (target.lengthSq() > 0 ? accel : (this.onGround ? P.friction : P.air * 0.6)) * dt;
    if (diff.length() > maxDv) diff.setLength(maxDv);
    hv.add(diff);
    this.vel.x = hv.x; this.vel.z = hv.z;
    this.vel.y -= P.gravity * dt;
    if (this.medium === 'water') this.vel.y *= Math.exp(-dt * 1.2); // water drag on the fall
    if (!this.locked && this.onGround && inp.pressed('Space')) { this.vel.y = P.jump; this.onGround = false; }

    // integrate with sub-steps, resolving the capsule each step
    const steps = 4;
    const wasGround = this.onGround;
    let grounded = false;
    for (let s = 0; s < steps; s++) {
      const h = dt / steps;
      const prev = this.pos.clone();
      this.pos.addScaledVector(this.vel, h);
      const seg = this._seg;
      const top = this.height - this.radius - this.crouch * 0.55;
      seg.start.set(this.pos.x, this.pos.y + this.radius, this.pos.z);
      seg.end.set(this.pos.x, this.pos.y + top, this.pos.z);
      const before = seg.start.clone();
      this.world.resolveCapsule(seg, this.radius);
      const delta = seg.start.clone().sub(before);
      this.pos.add(delta);
      if (delta.y > 1e-5 && delta.y > Math.abs(delta.x) * 0.6 && delta.y > Math.abs(delta.z) * 0.6) {
        grounded = true;
        if (this.vel.y < 0) this.vel.y = 0;
      } else if (delta.lengthSq() > 1e-10) {
        const n = delta.clone().normalize();
        const vn = this.vel.dot(n);
        if (vn < 0) this.vel.addScaledVector(n, -vn);
      }
      if (delta.y < -1e-5 && this.vel.y > 0) this.vel.y = 0;
    }
    // ground probe keeps us glued when walking down slopes
    const probe = this.world.raycast(new THREE.Vector3(this.pos.x, this.pos.y + 0.3, this.pos.z), new THREE.Vector3(0, -1, 0), 0.6);
    if (probe && (grounded || (wasGround && this.vel.y <= 0.01))) {
      const gap = this.pos.y - probe.point.y;
      if (gap > 0 && gap < 0.28 && probe.face && probe.face.normal.y > 0.55) { this.pos.y = probe.point.y; grounded = true; if (this.vel.y < 0) this.vel.y = 0; }
      this.surface = probe.surf;
    }
    if (grounded && !wasGround && this.onLand) this.onLand(this.surface, Math.min(1, -this.lastVy / 4));
    this.lastVy = this.vel.y;
    this.onGround = grounded;
    if (this.pos.y < -400) this.pos.y = 0;
    this.updateCamera(dt);
  }

  updateLadder(dt, fz) {
    const L = this.ladder;
    const v = -fz * (this.medium === 'water' ? 0.8 : 1.4);
    this.pos.x += (L.x - this.pos.x) * Math.min(1, dt * 6);
    this.pos.z += (L.z - this.pos.z) * Math.min(1, dt * 6);
    this.pos.y = THREE.MathUtils.clamp(this.pos.y + v * dt, L.y0, L.y1);
    this.vel.set(0, 0, 0);
    if (Math.abs(v) > 0) { this.stepPhase += dt * 2.2; if (this.stepPhase > 1) { this.stepPhase = 0; this.onStep && this.onStep(SURF.iron, 0.6, true); } }
    if (this.pos.y >= L.y1 - 1e-3 && L.onTop) L.onTop();
    if (this.pos.y <= L.y0 + 1e-3 && fz > 0 && L.onBottom) L.onBottom();
  }

  updateCamera(dt) {
    const P = this.P;
    const hs = Math.hypot(this.vel.x, this.vel.z);
    const moving = this.onGround && hs > 0.15;
    if (moving) {
      const f = P.bobFreq * (0.55 + 0.45 * hs / P.walk);
      this.bobT += dt * f * Math.PI * 2;
      const s = Math.sin(this.bobT);
      if (Math.sign(s) !== this.lastStepSign) {
        this.lastStepSign = Math.sign(s);
        if (this.onStep) this.onStep(this.surface, Math.min(1, hs / P.walk));
      }
    } else {
      this.bobT += dt * 0.6;
    }
    const amp = moving ? P.bobAmp * Math.min(1.2, hs / P.walk) : 0.004;
    const bobY = Math.abs(Math.sin(this.bobT)) * amp * 1.2 - amp * 0.6;
    const bobX = Math.cos(this.bobT) * amp * 0.5;
    // underwater the head drifts a little even when still
    const t = performance.now() * 0.001;
    const drift = this.medium === 'water' ? 0.02 : 0.004;
    this.sway.set(Math.sin(t * 0.37) * drift, Math.sin(t * 0.29 + 1) * drift, 0);
    const eye = this.eye - this.crouch * 0.6 - this.kneel * 0.75;
    const cam = this.camera;
    cam.position.set(this.pos.x, this.pos.y + eye + bobY + this.sway.y, this.pos.z);
    const right = new THREE.Vector3(Math.cos(this.yaw), 0, -Math.sin(this.yaw));
    cam.position.addScaledVector(right, bobX + this.sway.x);
    const roll = (this.medium === 'water' ? Math.sin(t * 0.21) * 0.012 : 0) + bobX * 0.15;
    cam.rotation.set(this.pitch, this.yaw, roll, 'YXZ');
    if (this.shake > 0) {
      cam.position.x += (Math.random() - 0.5) * this.shake * 0.05;
      cam.position.y += (Math.random() - 0.5) * this.shake * 0.05;
      cam.rotation.z += (Math.random() - 0.5) * this.shake * 0.01;
      this.shake = Math.max(0, this.shake - dt * 1.5);
    }
  }
  forward() { return new THREE.Vector3(0, 0, -1).applyEuler(this.camera.rotation); }
}

export class Input {
  constructor(el) {
    this.keys = new Set(); this.justPressed = new Set();
    this.mouseDX = 0; this.mouseDY = 0; this.sensitivity = 1.0; this.invertY = false;
    this.mouseDown = false; this.clicked = false; this.locked = false; this.dragLook = false;
    this.el = el;
    addEventListener('keydown', (e) => {
      if (!this.keys.has(e.code)) this.justPressed.add(e.code);
      this.keys.add(e.code);
      if (['Space', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.code)) e.preventDefault();
    });
    addEventListener('keyup', (e) => this.keys.delete(e.code));
    addEventListener('blur', () => this.keys.clear());
    document.addEventListener('pointerlockchange', () => { this.locked = document.pointerLockElement === el; });
    el.addEventListener('mousemove', (e) => {
      if (this.locked || (this.dragLook && this.mouseDown)) { this.mouseDX += e.movementX || 0; this.mouseDY += e.movementY || 0; }
    });
    el.addEventListener('mousedown', (e) => { if (e.button === 0) { this.mouseDown = true; this.clicked = true; } });
    addEventListener('mouseup', () => { this.mouseDown = false; });
  }
  key(c) { return this.keys.has(c); }
  pressed(c) { return this.justPressed.has(c); }
  endFrame() { this.justPressed.clear(); this.clicked = false; }
  requestLock() {
    try {
      const p = this.el.requestPointerLock && this.el.requestPointerLock();
      if (p && p.catch) p.catch(() => { this.dragLook = true; });
    } catch (e) { this.dragLook = true; }
    setTimeout(() => { if (!this.locked) this.dragLook = true; }, 400);
  }
}
