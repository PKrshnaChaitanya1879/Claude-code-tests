// Static world collision (one BVH over every collider triangle in world space) plus a few
// dynamic triangles for doors. Each triangle carries a surface id used for footstep sounds.
import * as THREE from 'three';
import { MeshBVH, ExtendedTriangle } from 'three-mesh-bvh';

export const SURF = { none: 0, carpet: 1, wood: 2, grate: 3, iron: 4, sand: 5, rock: 6, stone: 7, coral: 8, leather: 9 };
export function surfaceFor(matName = '') {
  if (/carpet/.test(matName)) return SURF.carpet;
  if (/oak|ebony/.test(matName)) return SURF.wood;
  if (/grate/.test(matName)) return SURF.grate;
  if (/iron|hull|brass|copper|gilt|bronze/.test(matName)) return SURF.iron;
  if (/sand|terrain/.test(matName)) return SURF.sand;
  if (/rock|basalt/.test(matName)) return SURF.rock;
  if (/marble|stone|ruin/.test(matName)) return SURF.stone;
  if (/coral/.test(matName)) return SURF.coral;
  if (/leather/.test(matName)) return SURF.leather;
  return SURF.wood;
}

export class World {
  constructor() {
    this.parts = []; // { positions: Float32Array (non-indexed, world), surf }
    this.dynamic = []; // ExtendedTriangle list rebuilt each frame by owners
    this.dynamicOwners = [];
    this.bvh = null;
  }
  // add a mesh (or BufferGeometry + matrix) as collider
  addMesh(mesh, surf) {
    mesh.updateMatrixWorld(true);
    const g = mesh.geometry;
    const pos = g.attributes.position;
    const idx = g.index;
    const n = idx ? idx.count : pos.count;
    const out = new Float32Array(n * 3);
    const v = new THREE.Vector3();
    for (let i = 0; i < n; i++) {
      const k = idx ? idx.getX(i) : i;
      v.fromBufferAttribute(pos, k).applyMatrix4(mesh.matrixWorld);
      out[i * 3] = v.x; out[i * 3 + 1] = v.y; out[i * 3 + 2] = v.z;
    }
    // per-triangle surfaces from material groups when available
    let surfArr = null;
    if (Array.isArray(mesh.material) && g.groups.length) {
      surfArr = new Uint8Array(n / 3);
      for (const gr of g.groups) {
        const s = surfaceFor(mesh.material[gr.materialIndex]?.name);
        for (let t = gr.start / 3; t < (gr.start + gr.count) / 3; t++) surfArr[t] = s;
      }
    }
    this.parts.push({ positions: out, surf: surf ?? surfaceFor(mesh.material?.name), surfArr });
  }
  build() {
    let total = 0;
    for (const p of this.parts) total += p.positions.length;
    const pos = new Float32Array(total);
    const surf = new Uint8Array(total / 9);
    let o = 0, t = 0;
    for (const p of this.parts) {
      pos.set(p.positions, o); o += p.positions.length;
      const nt = p.positions.length / 9;
      for (let i = 0; i < nt; i++) surf[t + i] = p.surfArr ? p.surfArr[i] : p.surf;
      t += nt;
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    this.geometry = g;
    this.triSurf = surf;
    this.bvh = new MeshBVH(g, { maxLeafTris: 8 });
    // the BVH may reorder an index it creates; keep a map from triangle to surface via index buffer
    this.mesh = new THREE.Mesh(g);
  }
  surfaceAtTriangle(faceIndex) {
    const idx = this.geometry.index;
    if (!idx) return this.triSurf[faceIndex] || 0;
    const v0 = idx.getX(faceIndex * 3);
    return this.triSurf[Math.floor(v0 / 3)] || 0;
  }
  raycast(origin, dir, far = 10) {
    if (!this.bvh) return null;
    const ray = new THREE.Ray(origin, dir);
    const hit = this.bvh.raycastFirst(ray, THREE.DoubleSide, 0, far);
    if (hit) hit.surf = this.surfaceAtTriangle(hit.faceIndex);
    return hit;
  }
  // push a capsule segment (start/end world points) out of geometry; returns accumulated push
  resolveCapsule(seg, radius) {
    const box = new THREE.Box3();
    box.expandByPoint(seg.start); box.expandByPoint(seg.end);
    box.min.addScalar(-radius); box.max.addScalar(radius);
    const triPoint = new THREE.Vector3(), capPoint = new THREE.Vector3(), dir = new THREE.Vector3();
    const handle = (tri) => {
      const d = tri.closestPointToSegment(seg, triPoint, capPoint);
      if (d < radius) {
        const depth = radius - d;
        dir.subVectors(capPoint, triPoint);
        if (dir.lengthSq() < 1e-10) dir.copy(tri.getNormal(new THREE.Vector3()));
        dir.normalize();
        seg.start.addScaledVector(dir, depth);
        seg.end.addScaledVector(dir, depth);
      }
    };
    if (this.bvh) this.bvh.shapecast({
      intersectsBounds: (b) => b.intersectsBox(box),
      intersectsTriangle: (tri) => { handle(tri); return false; },
    });
    for (const tri of this.dynamic) handle(tri);
  }
  // owners register a function that appends ExtendedTriangles each frame (doors etc.)
  refreshDynamic() {
    this.dynamic.length = 0;
    for (const f of this.dynamicOwners) f(this.dynamic);
  }
}

export function quadTris(a, b, c, d) {
  const t1 = new ExtendedTriangle(a.clone(), b.clone(), c.clone()); t1.needsUpdate = true;
  const t2 = new ExtendedTriangle(a.clone(), c.clone(), d.clone()); t2.needsUpdate = true;
  return [t1, t2];
}
