// A walkable route defined by waypoints (x, z, y): smooth interpolation, arc length, projection.
import * as THREE from 'three';

export class Route {
  constructor(points) {
    this.pts = points.map((p) => new THREE.Vector3(p[0], p[2], p[1])); // (x, y, z) from (x, z, y)
    this.curve = new THREE.CatmullRomCurve3(this.pts, false, 'centripetal');
    this.samples = this.curve.getSpacedPoints(Math.max(200, points.length * 40));
    this.len = [0];
    for (let i = 1; i < this.samples.length; i++) {
      const a = this.samples[i - 1], b = this.samples[i];
      this.len.push(this.len[i - 1] + Math.hypot(b.x - a.x, b.z - a.z));
    }
    this.total = this.len[this.len.length - 1];
    // monotonic in z (descending) so x and y can be looked up by z
    this.byZ = this.samples.map((p, i) => ({ z: p.z, x: p.x, y: p.y, s: this.len[i] }));
  }
  at(s) {
    s = Math.max(0, Math.min(this.total, s));
    let lo = 0, hi = this.len.length - 1;
    while (hi - lo > 1) { const m = (lo + hi) >> 1; if (this.len[m] < s) lo = m; else hi = m; }
    const t = (s - this.len[lo]) / Math.max(1e-6, this.len[hi] - this.len[lo]);
    const p = this.samples[lo].clone().lerp(this.samples[hi], t);
    const d = this.samples[hi].clone().sub(this.samples[lo]); d.y = 0; d.normalize();
    return { p, dir: d };
  }
  // interpolate path x, y and s at a given z (route descends in z)
  atZ(z) {
    const A = this.byZ;
    if (z >= A[0].z) return A[0];
    if (z <= A[A.length - 1].z) return A[A.length - 1];
    let lo = 0, hi = A.length - 1;
    while (hi - lo > 1) { const m = (lo + hi) >> 1; if (A[m].z > z) lo = m; else hi = m; }
    const t = (A[lo].z - z) / Math.max(1e-6, A[lo].z - A[hi].z);
    return { x: A[lo].x + (A[hi].x - A[lo].x) * t, y: A[lo].y + (A[hi].y - A[lo].y) * t, s: A[lo].s + (A[hi].s - A[lo].s) * t };
  }
  // distance along the route of the closest point to (x, z)
  project(x, z) {
    let best = 1e9, bs = 0;
    for (let i = 0; i < this.samples.length; i += 2) {
      const p = this.samples[i]; const d = (p.x - x) ** 2 + (p.z - z) ** 2;
      if (d < best) { best = d; bs = this.len[i]; }
    }
    return { s: bs, d: Math.sqrt(best) };
  }
}

// Procession: a leader walks the route at a pace that waits for the player; followers keep station.
export class Procession {
  constructor(route, divers, { speed = 0.85, gap = 1.6, wait = 14 } = {}) {
    this.route = route; this.divers = divers; this.speed = speed; this.gap = gap; this.wait = wait;
    this.s = 0; this.target = route.total; this.stopped = false; this.waiting = false;
    this.slots = divers.map((d, i) => ({ d, back: i === 0 ? 0 : 1.4 + Math.floor((i - 1) / 2) * gap, side: i === 0 ? 0 : ((i % 2) ? -0.75 : 0.75) + (Math.random() - 0.5) * 0.3, prev: null }));
  }
  update(dt, playerS) {
    const ahead = this.s - playerS;
    this.waiting = ahead > this.wait;
    let v = 0;
    if (!this.stopped && !this.waiting && this.s < this.target) v = this.speed * (ahead < 4 ? 1.15 : 1);
    this.s = Math.min(this.target, this.s + v * dt);
    for (const sl of this.slots) {
      if (sl.d.hold) continue;
      const s = Math.max(0, this.s - sl.back);
      const { p, dir } = this.route.at(s);
      const side = new THREE.Vector3(-dir.z, 0, dir.x);
      const tx = p.x + side.x * sl.side, tz = p.z + side.z * sl.side;
      const d = sl.d;
      const dx = tx - d.pos.x, dz = tz - d.pos.z;
      const dist = Math.hypot(dx, dz);
      const mv = Math.min(dist, (this.speed * 1.3) * dt);
      if (dist > 0.02) { d.pos.x += dx / dist * mv; d.pos.z += dz / dist * mv; }
      d.speed = dist > 0.05 ? Math.min(1.1, dist / Math.max(dt, 1e-3) * 0.25 + (v > 0 ? 0.6 : 0)) : 0;
      if (dist < 0.05 && v === 0) d.speed = 0;
      const want = dist > 0.08 ? Math.atan2(dx, dz) : Math.atan2(dir.x, dir.z);
      let dy = want - d.yaw; dy = Math.atan2(Math.sin(dy), Math.cos(dy));
      d.yaw += dy * Math.min(1, dt * 2.0);
    }
  }
}
