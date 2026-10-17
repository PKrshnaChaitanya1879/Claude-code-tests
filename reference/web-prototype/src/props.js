// Prop library from props.glb: instancing helpers and single-mesh clones.
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { makeMaterial } from './materials.js';

function normalize(g) {
  const n = g.attributes.position.count;
  if (!g.attributes.uv) g.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(n * 2), 2));
  const c = g.attributes.color, out = new Float32Array(n * 3);
  if (c) for (let i = 0; i < n; i++) { out[i * 3] = c.getX(i); out[i * 3 + 1] = c.getY(i); out[i * 3 + 2] = c.getZ(i); } else out.fill(1);
  g.setAttribute('color', new THREE.BufferAttribute(out, 3));
  for (const k of Object.keys(g.attributes)) if (!['position', 'normal', 'uv', 'color'].includes(k)) g.deleteAttribute(k);
  return g;
}

export class Props {
  async load(url = 'assets/props.json') {
    const gltf = await new GLTFLoader().loadAsync(url);
    this.items = {};
    for (const node of gltf.scene.children) {
      const parts = [];
      node.updateMatrixWorld(true);
      node.traverse((o) => {
        if (!o.isMesh) return;
        const g = normalize(o.geometry.clone());
        // props are exported at the origin; keep any child offset
        if (o !== node) g.applyMatrix4(o.matrix);
        parts.push({ geometry: g, matName: o.material.name });
      });
      this.items[node.name] = parts;
    }
    return this;
  }
  has(name) { return !!this.items[name]; }
  // single object (a Group of meshes) with exterior materials
  mesh(name, { shadow = true, material = null, ext = true } = {}) {
    const grp = new THREE.Group();
    for (const p of this.items[name] || []) {
      const m = new THREE.Mesh(p.geometry, material || makeMaterial(p.matName, ext));
      m.castShadow = shadow; m.receiveShadow = true;
      grp.add(m);
    }
    grp.name = name;
    return grp;
  }
  // many copies: matrices = array of Matrix4; returns a Group of InstancedMeshes
  instanced(name, matrices, { shadow = true, colors = null, material = null, ext = true, chunk = 40, cull = 1e9 } = {}) {
    if (chunk && matrices.length > 8) {
      // split into spatial cells so whole cells can be frustum- and distance-culled
      const cells = new Map();
      const P = new THREE.Vector3();
      matrices.forEach((m, i) => { P.setFromMatrixPosition(m); const k = Math.floor(P.x / chunk) + ':' + Math.floor(P.z / chunk); if (!cells.has(k)) cells.set(k, { m: [], c: [] }); cells.get(k).m.push(m); if (colors) cells.get(k).c.push(colors[i]); });
      const grp = new THREE.Group(); grp.name = name + '_chunks';
      for (const [, cell] of cells) {
        const sub = this.instanced(name, cell.m, { shadow, colors: colors ? cell.c : null, material, ext, chunk: 0 });
        const box = new THREE.Box3(); cell.m.forEach((m) => box.expandByPoint(P.setFromMatrixPosition(m)));
        sub.userData.center = box.getCenter(new THREE.Vector3()); sub.userData.radius = box.getSize(new THREE.Vector3()).length() / 2 + 6;
        sub.userData.cullable = true; sub.userData.cull = cull;
        grp.add(sub);
      }
      return grp;
    }
    const grp = new THREE.Group();
    for (const p of this.items[name] || []) {
      const im = new THREE.InstancedMesh(p.geometry, material || makeMaterial(p.matName, ext), matrices.length);
      matrices.forEach((m, i) => im.setMatrixAt(i, m));
      if (colors) colors.forEach((c, i) => im.setColorAt(i, c));
      im.instanceMatrix.needsUpdate = true;
      im.castShadow = shadow; im.receiveShadow = true;
      im.computeBoundingSphere();
      grp.add(im);
    }
    grp.name = name + '_x' + matrices.length;
    return grp;
  }
  geometry(name) { return (this.items[name] || [])[0]?.geometry; }
}

export function trs(x, y, z, ry = 0, s = 1, rx = 0, rz = 0) {
  const m = new THREE.Matrix4();
  m.compose(new THREE.Vector3(x, y, z), new THREE.Quaternion().setFromEuler(new THREE.Euler(rx, ry, rz)), typeof s === 'number' ? new THREE.Vector3(s, s, s) : s);
  return m;
}
