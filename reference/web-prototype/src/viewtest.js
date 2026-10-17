import * as THREE from 'three';
import { Pipeline, QUALITY } from './pipeline.js';
import { UW, makeCausticTexture } from './uw.js';
import { MarineSnow } from './particles.js';
import { Nautilus, b2t } from './nautilus.js';

const cfg = Object.assign({ cam: [8, 0, 1.6], look: [14, 0, 1.6], q: 'medium', ceiling: 1, panels: 0 }, window.__cfg || {});
const renderer = new THREE.WebGLRenderer({ antialias: false });
renderer.setPixelRatio(1); renderer.setSize(innerWidth, innerHeight);
renderer.shadowMap.enabled = true;
document.body.appendChild(renderer.domElement);
const pipe = new Pipeline(renderer); pipe.setQuality(QUALITY[cfg.q]); pipe.setSize(innerWidth, innerHeight);
UW.uniforms.uCaustics.value = makeCausticTexture();
const ext = new THREE.Scene(), int = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(72, innerWidth / innerHeight, 0.05, 400);
const n = new Nautilus();
n.load().then(() => {
  n.place(new THREE.Vector3(0, 0, 0), 0);
  int.add(n.int); ext.add(n.ext);
  // a sea floor so the window has something to look at
  const g = new THREE.PlaneGeometry(200, 200, 40, 40); g.rotateX(-Math.PI / 2);
  const m = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ color: 0x8a8070 }));
  m.position.y = -2.4; ext.add(m);
  camera.position.copy(b2t(...cfg.cam)); camera.lookAt(b2t(...cfg.look));
  n.state.ceiling = cfg.ceiling; n.state.ceilingVis = cfg.ceiling; n.state.panels = cfg.panels; n.state.panelsTarget = cfg.panels;
  THREE.DefaultLoadingManager.onLoad = () => { window.__ready = true; };
  setTimeout(() => { window.__ready = true; }, 8000);
});
let t = 0;
window.__renderFrames = (k) => {
  for (let i = 0; i < k; i++) {
    t += 1 / 30; UW.uniforms.uTime.value = t;
    n.update(1 / 30, camera.position);
    pipe.finalMat.uniforms.uFade.value = 0;
    if (cfg.raw) { renderer.setRenderTarget(null); int.overrideMaterial = cfg.raw === 2 ? new THREE.MeshNormalMaterial({side: THREE.DoubleSide}) : new THREE.MeshNormalMaterial(); renderer.render(int, camera); continue; }
    pipe.render({ extScene: ext, intScene: int, camera, air: n.airBox(), lights: { sun: null, spots: [n.lantern, ...n.windowLights] } }, 1 / 30, t);
  }
  return renderer.info.render.calls;
};
