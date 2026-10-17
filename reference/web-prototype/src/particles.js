// Marine snow: thousands of drifting specks in a box that wraps around the camera.
// Each speck is lit by the same lights as the water (sun shafts, lamps, volcano) so it
// only shows where light actually is, which is what makes beams read as volume.
import * as THREE from 'three';
import { UW, UW_GLSL } from './uw.js';

const VERT = /* glsl */`
#include <packing>
${UW_GLSL}
uniform sampler2D uSpotShadow0; uniform sampler2D uSpotShadow1; uniform sampler2D uSpotShadow2; uniform sampler2D uSpotShadow3;
uniform mat4 uSpotShadowMat[4]; uniform float uSpotShadowOn[4];
float pShadow(sampler2D map, mat4 m, vec3 p){
  vec4 sc = m * vec4(p, 1.0); sc.xyz /= sc.w;
  if (sc.x < 0.0 || sc.x > 1.0 || sc.y < 0.0 || sc.y > 1.0 || sc.z > 1.0 || sc.z < 0.0) return 1.0;
  return step(sc.z - 0.0005, unpackRGBAToDepth(textureLod(map, sc.xy, 0.0)));
}
float pSpotShadow(int i, vec3 p){
  if (uSpotShadowOn[i] < 0.5) return 1.0;
  if (i == 0) return pShadow(uSpotShadow0, uSpotShadowMat[0], p);
  if (i == 1) return pShadow(uSpotShadow1, uSpotShadowMat[1], p);
  if (i == 2) return pShadow(uSpotShadow2, uSpotShadowMat[2], p);
  return pShadow(uSpotShadow3, uSpotShadowMat[3], p);
}
attribute vec3 aSeed;
uniform vec3 uCenter; uniform float uBox; uniform float uSize; uniform float uPixelRatio;
uniform vec3 uSpotPos[4]; uniform vec3 uSpotDir[4]; uniform vec3 uSpotColor[4]; uniform vec2 uSpotCone[4]; uniform float uSpotCount;
uniform vec3 uPtPos[4]; uniform vec3 uPtColor[4]; uniform float uPtCount; uniform float uSunOn; uniform float uGlow;
uniform vec3 uDrift; uniform mat4 uAirInv; uniform vec3 uAirMin; uniform vec3 uAirMax; uniform float uAirOn; uniform float uSpotMedium[4];
varying vec3 vCol; varying float vViewZ;
void main(){
  vec3 p = position + uDrift * (0.6 + aSeed.x) ;
  p.x += sin(uTime * 0.21 + aSeed.y * 40.0) * 0.25;
  p.y += sin(uTime * 0.17 + aSeed.z * 40.0) * 0.2;
  p = uCenter + mod(p - uCenter + uBox * 0.5, uBox) - uBox * 0.5;
  vec3 st = uwSigmaT();
  vec3 E = uwAmbientAt(p.y) * 0.25;
  if (uSunOn > 0.5) { float s = uwCaustic(p, 3.0); E += uSunColor * uwSunAtten(p.y) * (0.1 + 2.0 * s * s) * 0.6; }
  for (int k = 0; k < 4; k++) {
    if (float(k) >= uSpotCount) break;
    if (uSpotMedium[k] > 0.5) continue;
    vec3 v = p - uSpotPos[k]; float dl = length(v);
    float cone = smoothstep(uSpotCone[k].x, uSpotCone[k].y, dot(v / max(dl, 1e-3), uSpotDir[k]));
    if (cone <= 0.0) continue;
    E += uSpotColor[k] * cone * exp(-st * dl) / (dl * dl + 0.6) * pSpotShadow(k, p);
  }
  for (int k = 0; k < 4; k++) {
    if (float(k) >= uPtCount) break;
    vec3 v = p - uPtPos[k]; float dl = length(v);
    E += uPtColor[k] * exp(-st * dl) / (dl * dl + 1.0);
  }
  vec4 mv = modelViewMatrix * vec4(p, 1.0);
  float dist = length(mv.xyz);
  vec3 T = exp(-st * dist);
  vCol = E * T * (0.35 + aSeed.x) * 0.06 + uGlow * vec3(0.25, 0.9, 1.0) * step(0.985, aSeed.y) * T * (0.6 + 0.4 * sin(uTime * 2.0 + aSeed.z * 30.0));
  vViewZ = -mv.z;
  gl_Position = projectionMatrix * mv;
  gl_PointSize = uSize * uPixelRatio * (0.5 + aSeed.z) / max(-mv.z, 0.1);
  if (-mv.z < 0.12) gl_PointSize = 0.0;
  if (uAirOn > 0.5) { vec3 lp = (uAirInv * vec4(p, 1.0)).xyz; if (all(greaterThan(lp, uAirMin)) && all(lessThan(lp, uAirMax))) gl_PointSize = 0.0; }
}`;

const FRAG = /* glsl */`
#include <packing>
uniform sampler2D tDepth; uniform vec2 uRes; uniform float uNear; uniform float uFar;
varying vec3 vCol; varying float vViewZ;
void main(){
  vec2 c = gl_PointCoord - 0.5; float r = dot(c, c);
  if (r > 0.25) discard;
  float d = texture2D(tDepth, gl_FragCoord.xy / uRes).r;
  float sceneZ = -perspectiveDepthToViewZ(d, uNear, uFar);
  float soft = clamp((sceneZ - vViewZ) * 4.0, 0.0, 1.0);
  float a = (1.0 - r * 4.0);
  gl_FragColor = vec4(vCol * a * soft, 1.0);
}`;

export class MarineSnow {
  constructor(count = 5000, box = 22) {
    const pos = new Float32Array(count * 3), seed = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      pos[i * 3] = (Math.random() - 0.5) * box; pos[i * 3 + 1] = (Math.random() - 0.5) * box; pos[i * 3 + 2] = (Math.random() - 0.5) * box;
      seed[i * 3] = Math.random(); seed[i * 3 + 1] = Math.random(); seed[i * 3 + 2] = Math.random();
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    g.setAttribute('aSeed', new THREE.BufferAttribute(seed, 3));
    const arr = (n, f) => Array.from({ length: n }, f);
    this.uniforms = {
      ...UW.uniforms,
      uCenter: { value: new THREE.Vector3() }, uBox: { value: box }, uSize: { value: 26 }, uPixelRatio: { value: 1 },
      uSpotPos: { value: arr(4, () => new THREE.Vector3()) }, uSpotDir: { value: arr(4, () => new THREE.Vector3()) },
      uSpotColor: { value: arr(4, () => new THREE.Vector3()) }, uSpotCone: { value: arr(4, () => new THREE.Vector2()) }, uSpotCount: { value: 0 },
      uPtPos: { value: arr(4, () => new THREE.Vector3()) }, uPtColor: { value: arr(4, () => new THREE.Vector3()) }, uPtCount: { value: 0 },
      uSunOn: { value: 1 }, uGlow: { value: 0 }, uDrift: { value: new THREE.Vector3() },
      uAirInv: { value: new THREE.Matrix4() }, uAirMin: { value: new THREE.Vector3() }, uAirMax: { value: new THREE.Vector3() }, uAirOn: { value: 0 }, uSpotMedium: { value: [0, 0, 0, 0] },
      uSpotShadow0: { value: null }, uSpotShadow1: { value: null }, uSpotShadow2: { value: null }, uSpotShadow3: { value: null }, uSpotShadowMat: { value: arr(4, () => new THREE.Matrix4()) }, uSpotShadowOn: { value: [0, 0, 0, 0] },
      tDepth: { value: null }, uRes: { value: new THREE.Vector2() }, uNear: { value: 0.05 }, uFar: { value: 500 },
    };
    this.material = new THREE.ShaderMaterial({
      vertexShader: VERT, fragmentShader: FRAG, uniforms: this.uniforms,
      transparent: true, depthTest: false, depthWrite: false, blending: THREE.AdditiveBlending,
    });
    this.points = new THREE.Points(g, this.material);
    this.points.frustumCulled = false;
    this.scene = new THREE.Scene();
    this.scene.add(this.points);
    this.drift = new THREE.Vector3();
  }
  // copy light state from the pipeline's volumetric uniforms so both always agree
  update(pipeline, camera, dt, current = new THREE.Vector3(0.02, 0.01, 0.015)) {
    const u = this.uniforms, vm = pipeline.volMat.uniforms;
    u.uCenter.value.setFromMatrixPosition(camera.matrixWorld);
    this.drift.addScaledVector(current, dt);
    u.uDrift.value.copy(this.drift);
    u.uSpotCount.value = vm.uSpotCount.value; u.uPtCount.value = vm.uPtCount.value; u.uSunOn.value = vm.uSunOn.value;
    for (let i = 0; i < 4; i++) {
      u.uSpotPos.value[i].copy(vm.uSpotPos.value[i]); u.uSpotDir.value[i].copy(vm.uSpotDir.value[i]);
      u.uSpotColor.value[i].copy(vm.uSpotColor.value[i]); u.uSpotCone.value[i].copy(vm.uSpotCone.value[i]);
      u.uPtPos.value[i].copy(vm.uPtPos.value[i]); u.uPtColor.value[i].copy(vm.uPtColor.value[i]);
    }
    const c = pipeline.common;
    u.uAirInv.value.copy(c.uAirInv.value); u.uAirMin.value.copy(c.uAirMin.value); u.uAirMax.value.copy(c.uAirMax.value); u.uAirOn.value = c.uAirOn.value > 0.5 || this.alwaysAir ? 1 : 0;
    for (let i = 0; i < 4; i++) {
      u.uSpotMedium.value[i] = vm.uSpotMedium.value[i];
      u['uSpotShadow' + i].value = vm['uSpotShadow' + i].value; u.uSpotShadowMat.value[i].copy(vm.uSpotShadowMat.value[i]); u.uSpotShadowOn.value[i] = vm.uSpotShadowOn.value[i];
    }
    u.tDepth.value = pipeline.sceneRT.depthTexture; u.uRes.value.set(pipeline.sw, pipeline.sh);
    u.uNear.value = camera.near; u.uFar.value = camera.far;
    u.uPixelRatio.value = pipeline.sh / 720;
  }
}
