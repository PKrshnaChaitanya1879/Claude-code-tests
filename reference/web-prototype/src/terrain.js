// Faceted heightfield terrain. The same grid answers height queries, so walking matches the mesh.
import * as THREE from 'three';

export class Terrain {
  // fn(x, z) -> height; colorFn(x, z, h, slope) -> [r,g,b]
  constructor({ x0, z0, x1, z1, cell = 1.0, fn, colorFn, jitter = 0.18, seed = 1 }) {
    this.x0 = x0; this.z0 = z0; this.cell = cell;
    this.nx = Math.ceil((x1 - x0) / cell) + 1; this.nz = Math.ceil((z1 - z0) / cell) + 1;
    const nx = this.nx, nz = this.nz;
    this.h = new Float32Array(nx * nz);
    for (let j = 0; j < nz; j++) for (let i = 0; i < nx; i++) this.h[j * nx + i] = fn(x0 + i * cell, z0 + j * cell);
    // jittered vertex positions (xz) give the hand-made low-poly look without breaking height queries
    const jx = new Float32Array(nx * nz), jz = new Float32Array(nx * nz);
    let s = seed * 9301 + 49297;
    const rnd = () => { s = (s * 9301 + 49297) % 233280; return s / 233280 - 0.5; };
    for (let k = 0; k < nx * nz; k++) { jx[k] = rnd() * jitter * cell; jz[k] = rnd() * jitter * cell; }
    const P = (i, j) => { const k = j * nx + i; return [x0 + i * cell + jx[k], this.h[k], z0 + j * cell + jz[k]]; };
    const pos = [], col = [];
    const tmpA = new THREE.Vector3(), tmpB = new THREE.Vector3(), n = new THREE.Vector3();
    for (let j = 0; j < nz - 1; j++) for (let i = 0; i < nx - 1; i++) {
      const a = P(i, j), b = P(i + 1, j), c = P(i, j + 1), d = P(i + 1, j + 1);
      const tris = ((i + j) & 1) ? [[a, c, b], [b, c, d]] : [[a, c, d], [a, d, b]];
      for (const t of tris) {
        tmpA.set(t[1][0] - t[0][0], t[1][1] - t[0][1], t[1][2] - t[0][2]);
        tmpB.set(t[2][0] - t[0][0], t[2][1] - t[0][1], t[2][2] - t[0][2]);
        n.crossVectors(tmpA, tmpB).normalize();
        const cx = (t[0][0] + t[1][0] + t[2][0]) / 3, cz = (t[0][2] + t[1][2] + t[2][2]) / 3, cy = (t[0][1] + t[1][1] + t[2][1]) / 3;
        const rgb = colorFn ? colorFn(cx, cz, cy, 1 - n.y) : [0.5, 0.5, 0.5];
        for (const v of t) { pos.push(v[0], v[1], v[2]); col.push(rgb[0], rgb[1], rgb[2]); }
      }
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
    g.computeVertexNormals();
    // triplanar-ish uv from world xz
    const uv = new Float32Array((pos.length / 3) * 2);
    for (let k = 0; k < pos.length / 3; k++) { uv[k * 2] = pos[k * 3] * 0.25; uv[k * 2 + 1] = pos[k * 3 + 2] * 0.25; }
    g.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
    this.geometry = g;
  }
  height(x, z) {
    const fx = (x - this.x0) / this.cell, fz = (z - this.z0) / this.cell;
    const i = Math.max(0, Math.min(this.nx - 2, Math.floor(fx))), j = Math.max(0, Math.min(this.nz - 2, Math.floor(fz)));
    const u = Math.max(0, Math.min(1, fx - i)), v = Math.max(0, Math.min(1, fz - j));
    const h = this.h, nx = this.nx;
    const a = h[j * nx + i], b = h[j * nx + i + 1], c = h[(j + 1) * nx + i], d = h[(j + 1) * nx + i + 1];
    return a * (1 - u) * (1 - v) + b * u * (1 - v) + c * (1 - u) * v + d * u * v;
  }
}
