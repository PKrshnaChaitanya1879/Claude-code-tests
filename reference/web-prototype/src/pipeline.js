// Render pipeline: two scene passes (exterior water world + interior air world) into one HDR target,
// ray-marched volumetric light at reduced resolution with temporal accumulation, an analytic water
// composite, lit particles, bloom, then filmic tonemap/grade and a final FXAA/grain/helmet pass.
import * as THREE from 'three';
import { UW, UW_GLSL } from './uw.js';

const FSQ_VERT = /* glsl */`
varying vec2 vUv;
void main(){ vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }`;

const COMMON = /* glsl */`
#include <packing>
uniform mat4 uInvProj; uniform mat4 uCamWorld; uniform vec3 uCamPos; uniform float uNear; uniform float uFar;
uniform mat4 uAirInv; uniform vec3 uAirMin; uniform vec3 uAirMax; uniform float uAirOn;
vec3 viewPosFromDepth(vec2 uv, float d){
  vec4 p = uInvProj * vec4(uv * 2.0 - 1.0, d * 2.0 - 1.0, 1.0);
  return p.xyz / p.w;
}
vec3 viewDirFromUv(vec2 uv){
  vec4 p = uInvProj * vec4(uv * 2.0 - 1.0, 1.0, 1.0);
  return normalize(p.xyz / p.w);
}
// returns distance at which ray leaves the interior air box (0 if camera not inside)
float airStart(vec3 ro, vec3 rd){
  if (uAirOn < 0.5) return 0.0;
  vec3 o = (uAirInv * vec4(ro, 1.0)).xyz; vec3 d = (uAirInv * vec4(rd, 0.0)).xyz;
  if (any(lessThan(o, uAirMin)) || any(greaterThan(o, uAirMax))) return 0.0;
  vec3 inv = 1.0 / (d + sign(d) * 1e-6 + vec3(1e-9));
  vec3 t1 = (uAirMin - o) * inv; vec3 t2 = (uAirMax - o) * inv;
  vec3 tmax = max(t1, t2);
  float tExit = min(min(tmax.x, tmax.y), tmax.z);
  return max(tExit, 0.0);
}
float ign(vec2 p){ return fract(52.9829189 * fract(dot(p, vec2(0.06711056, 0.00583715)))); }
`;

const VOL_FRAG = /* glsl */`
${UW_GLSL}
${COMMON}
varying vec2 vUv;
uniform sampler2D tDepth;
uniform float uMaxDist; uniform float uSteps; uniform float uFrame; uniform vec2 uRes;
uniform float uSunOn; uniform sampler2D uSunShadow; uniform mat4 uSunShadowMat; uniform float uSunShadowOn; uniform float uShaftGain;
uniform vec3 uSpotPos[4]; uniform vec3 uSpotDir[4]; uniform vec3 uSpotColor[4]; uniform vec2 uSpotCone[4]; uniform float uSpotShadowOn[4]; uniform mat4 uSpotShadowMat[4];
uniform sampler2D uSpotShadow0; uniform sampler2D uSpotShadow1; uniform sampler2D uSpotShadow2; uniform sampler2D uSpotShadow3;
uniform float uSpotCount; uniform float uSpotG; uniform float uSpotMedium[4]; uniform float uPtMedium[4]; uniform float uSigmaAir; uniform float uAirSteps;
uniform vec3 uPtPos[4]; uniform vec3 uPtColor[4]; uniform float uPtCount;

float hg(float c, float g){ float g2 = g*g; return (1.0 - g2) / (12.566 * pow(max(1.0 + g2 - 2.0*g*c, 1e-3), 1.5)); }
float shadowSample(sampler2D map, mat4 m, vec3 p, float bias){
  vec4 sc = m * vec4(p, 1.0); sc.xyz /= sc.w;
  if (sc.x < 0.0 || sc.x > 1.0 || sc.y < 0.0 || sc.y > 1.0 || sc.z > 1.0 || sc.z < 0.0) return 1.0;
  return step(sc.z - bias, unpackRGBAToDepth(texture2D(map, sc.xy)));
}
float spotShadow(int i, vec3 p){
  if (uSpotShadowOn[i] < 0.5) return 1.0;
  if (i == 0) return shadowSample(uSpotShadow0, uSpotShadowMat[0], p, 0.0005);
  if (i == 1) return shadowSample(uSpotShadow1, uSpotShadowMat[1], p, 0.0005);
  if (i == 2) return shadowSample(uSpotShadow2, uSpotShadowMat[2], p, 0.0005);
  return shadowSample(uSpotShadow3, uSpotShadowMat[3], p, 0.0005);
}
void main(){
  float d = texture2D(tDepth, vUv).r;
  vec3 vdir = viewDirFromUv(vUv);
  vec3 rd = normalize((uCamWorld * vec4(vdir, 0.0)).xyz);
  float dist = d >= 1.0 ? 1e5 : length(viewPosFromDepth(vUv, d));
  float t0 = airStart(uCamPos, rd);
  float t1 = min(dist, t0 + uMaxDist);
  vec3 L = vec3(0.0);
  // dust in the air of the cabins: only interior ("air") lights scatter here
  float ta1 = min(dist, t0);
  if (ta1 > 0.05 && uAirSteps > 0.5) {
    float j = fract(ign(gl_FragCoord.xy + 17.0) + uFrame * 0.61803398875);
    for (int i = 0; i < 16; i++) {
      if (float(i) >= uAirSteps) break;
      float t = ta1 * (float(i) + j) / uAirSteps;
      float dt = ta1 / uAirSteps;
      vec3 p = uCamPos + rd * t;
      vec3 S = vec3(0.0);
      for (int k = 0; k < 4; k++) {
        if (float(k) >= uSpotCount) break;
        if (uSpotMedium[k] < 0.5) continue;
        vec3 v = p - uSpotPos[k]; float dl = length(v); vec3 l = v / max(dl, 1e-3);
        float cone = smoothstep(uSpotCone[k].x, uSpotCone[k].y, dot(l, uSpotDir[k]));
        if (cone <= 0.0) continue;
        float sh = spotShadow(k, p);
        S += uSpotColor[k] * cone * sh / (dl * dl + 0.6) * hg(dot(l, -rd), 0.35);
      }
      for (int k = 0; k < 4; k++) {
        if (float(k) >= uPtCount) break;
        if (uPtMedium[k] < 0.5) continue;
        vec3 v = p - uPtPos[k]; float dl = length(v);
        S += uPtColor[k] / (dl * dl + 0.4) * (1.0 / 12.566);
      }
      L += uSigmaAir * S * dt;
    }
  }
  if (t1 > t0 && uWaterOn > 0.5) {
    float j = fract(ign(gl_FragCoord.xy) + uFrame * 0.61803398875);
    vec3 st = uwSigmaT();
    float cSun = dot(uSunDir, -rd);
    float phSun = hg(cSun, 0.72) * 0.85 + 0.15 / 12.566;
    float N = uSteps;
    float prevT = t0;
    for (int i = 0; i < 64; i++) {
      if (float(i) >= N) break;
      float f = (float(i) + j) / N;
      float t = t0 + (t1 - t0) * f * f;
      float tn = t0 + (t1 - t0) * min(1.0, ((float(i) + 1.0 + j) / N) * ((float(i) + 1.0 + j) / N));
      float dt = max(tn - t, 1e-3);
      vec3 p = uCamPos + rd * t;
      vec3 Tr = exp(-st * (t - t0));
      vec3 S = vec3(0.0);
      if (uSunOn > 0.5) {
        float shaft = 0.08 + 6.0 * uwShaft(p);
        float sh = uSunShadowOn > 0.5 ? shadowSample(uSunShadow, uSunShadowMat, p, 0.002) : 1.0;
        S += uSunColor * uwSunAtten(p.y) * mix(1.0, shaft, uShaftGain) * sh * phSun;
      }
      for (int k = 0; k < 4; k++) {
        if (float(k) >= uSpotCount) break;
        if (uSpotMedium[k] > 0.5) continue;
        vec3 v = p - uSpotPos[k]; float dl = length(v); vec3 l = v / max(dl, 1e-3);
        float cone = smoothstep(uSpotCone[k].x, uSpotCone[k].y, dot(l, uSpotDir[k]));
        if (cone <= 0.0) continue;
        float sh = spotShadow(k, p);
        vec3 E = uSpotColor[k] * cone * sh * exp(-st * dl) / (dl * dl + 0.6);
        S += E * hg(dot(l, -rd), uSpotG);
      }
      for (int k = 0; k < 4; k++) {
        if (float(k) >= uPtCount) break;
        if (uPtMedium[k] > 0.5) continue;
        vec3 v = p - uPtPos[k]; float dl = length(v);
        S += uPtColor[k] * exp(-st * dl) / (dl * dl + 1.0) * (1.0 / 12.566);
      }
      L += Tr * uSigmaS * S * dt;
    }
  }
  gl_FragColor = vec4(L, min(dist, 1e4));
}`;

const TEMPORAL_FRAG = /* glsl */`
${COMMON}
varying vec2 vUv;
uniform sampler2D tCur; uniform sampler2D tHist; uniform mat4 uPrevViewProj; uniform float uBlend; uniform float uReset;
void main(){
  vec4 cur = texture2D(tCur, vUv);
  vec3 vdir = viewDirFromUv(vUv);
  vec3 rd = normalize((uCamWorld * vec4(vdir, 0.0)).xyz);
  float dist = min(cur.a, 60.0);
  vec3 wp = uCamPos + rd * dist;
  vec4 pc = uPrevViewProj * vec4(wp, 1.0);
  vec2 puv = pc.xy / pc.w * 0.5 + 0.5;
  vec4 hist = texture2D(tHist, puv);
  float valid = (puv.x > 0.0 && puv.x < 1.0 && puv.y > 0.0 && puv.y < 1.0 && uReset < 0.5) ? 1.0 : 0.0;
  float rel = abs(hist.a - cur.a) / max(cur.a, 0.5);
  valid *= 1.0 - smoothstep(0.08, 0.25, rel);
  // neighbourhood clamp keeps light changes responsive
  vec2 px = 1.0 / vec2(textureSize(tCur, 0));
  vec3 mn = cur.rgb, mx = cur.rgb;
  for (int y = -1; y <= 1; y++) for (int x = -1; x <= 1; x++) {
    vec3 s = texture2D(tCur, vUv + vec2(x, y) * px).rgb; mn = min(mn, s); mx = max(mx, s);
  }
  vec3 h = clamp(hist.rgb, mn - (mx - mn) * 0.5, mx + (mx - mn) * 0.5);
  gl_FragColor = vec4(mix(cur.rgb, h, uBlend * valid), cur.a);
}`;

const COMPOSITE_FRAG = /* glsl */`
${UW_GLSL}
${COMMON}
varying vec2 vUv;
uniform sampler2D tColor; uniform sampler2D tDepth; uniform sampler2D tVol; uniform vec2 uVolRes;
uniform float uSurfaceOn; uniform float uLocalFog; uniform vec3 uLocalFogColor;
uniform float uAirHaze; uniform float uDbg; uniform float uVolGain; uniform float uFogGain;
vec3 bilateralVol(vec2 uv, float dist){
  vec2 res = uVolRes; vec2 p = uv * res - 0.5; vec2 f = fract(p); vec2 b = (floor(p) + 0.5) / res;
  vec3 acc = vec3(0.0); float wsum = 0.0;
  for (int y = 0; y <= 1; y++) for (int x = 0; x <= 1; x++) {
    vec2 o = vec2(x, y);
    vec4 s = texture2D(tVol, b + o / res);
    float w = (x == 0 ? 1.0 - f.x : f.x) * (y == 0 ? 1.0 - f.y : f.y);
    w *= 1.0 / (1e-3 + abs(s.a - dist) / max(dist, 0.3) * 8.0);
    acc += s.rgb * w; wsum += w;
  }
  return acc / max(wsum, 1e-5);
}
void main(){
  vec3 col = texture2D(tColor, vUv).rgb;
  float d = texture2D(tDepth, vUv).r;
  vec3 vdir = viewDirFromUv(vUv);
  vec3 rd = normalize((uCamWorld * vec4(vdir, 0.0)).xyz);
  bool bg = d >= 1.0;
  float dist = bg ? 1e5 : length(viewPosFromDepth(vUv, d));
  float t0 = airStart(uCamPos, rd);
  if (uLocalFog > 0.5) { // flooded airlock: dense water right around the camera
    vec3 T = exp(-vec3(0.6, 0.25, 0.2) * dist);
    gl_FragColor = vec4(col * T + uLocalFogColor * (1.0 - T), 1.0); return;
  }
  if (dist <= t0 + 1e-3 || uWaterOn < 0.5) {
    gl_FragColor = vec4(col + bilateralVol(vUv, min(dist, 1e4)) * uVolGain, 1.0); return;
  }
  vec3 st = uwSigmaT();
  vec3 ro = uCamPos + rd * t0;
  float D = dist - t0;
  float depth0 = uwDepth(ro.y);
  float slope0 = uwDepthSlope(ro.y);
  float Dsurf = rd.y > 0.0 ? depth0 / (slope0 * rd.y) : 1e5;
  float Dfog = min(min(D, Dsurf), 600.0);
  vec3 T = exp(-st * D);
  // ambient light scattered by the water itself, brighter towards the surface
  vec3 A0 = uAmbTop * uwSunAtten(ro.y) * uFogGain;
  vec3 kap = uKd * slope0 * rd.y;
  vec3 den = st - kap;
  vec3 sden = sign(den) * max(abs(den), vec3(1e-4)) + vec3(step(abs(den), vec3(0.0))) * 1e-4;
  vec3 g = (1.0 - exp(-sden * Dfog)) / sden;
  vec3 amb = uSigmaS * A0 * g;
  amb += uSigmaS * uAmbFloor * uAmbFloorColor * 0.3 * (1.0 - exp(-st * Dfog)) / st;
  vec3 res = (bg ? vec3(0.0) : col * T) + amb;
  // the surface seen from below: Snell's window and total internal reflection
  if (uSurfaceOn > 0.5 && rd.y > 0.0 && Dsurf < D) {
    vec3 hp = ro + rd * Dsurf;
    float rip = uwCaustic(hp * 0.6 + vec3(0.0, 0.0, uTime * 0.2), clamp(log2(Dsurf * 0.35), 1.0, 7.0));
    float win = smoothstep(0.55, 0.78, rd.y);
    vec3 sky = uSunColor * (0.18 + 0.25 * rip) + uSunColor * 3.0 * pow(max(dot(rd, -uSunDir), 0.0), 40.0);
    vec3 tir = uAmbTop * uwSunAtten(hp.y) * (0.05 + 0.08 * rip);
    res += mix(tir, sky, win) * exp(-st * Dsurf);
  }
  res += bilateralVol(vUv, min(dist, 1e4)) * uVolGain;
  if (uDbg > 0.5) res = bilateralVol(vUv, min(dist, 1e4)) * 4.0;
  gl_FragColor = vec4(res, 1.0);
}`;

const BRIGHT_FRAG = /* glsl */`
varying vec2 vUv; uniform sampler2D tSrc; uniform vec2 uTexel; uniform float uThreshold;
void main(){
  vec3 c = vec3(0.0);
  c += texture2D(tSrc, vUv + uTexel * vec2(-1.0, -1.0)).rgb;
  c += texture2D(tSrc, vUv + uTexel * vec2( 1.0, -1.0)).rgb;
  c += texture2D(tSrc, vUv + uTexel * vec2(-1.0,  1.0)).rgb;
  c += texture2D(tSrc, vUv + uTexel * vec2( 1.0,  1.0)).rgb;
  c *= 0.25;
  float l = dot(c, vec3(0.2126, 0.7152, 0.0722));
  float k = max(l - uThreshold, 0.0) / max(l, 1e-4);
  gl_FragColor = vec4(min(c * k, vec3(40.0)), 1.0);
}`;
const DOWN_FRAG = /* glsl */`
varying vec2 vUv; uniform sampler2D tSrc; uniform vec2 uTexel;
void main(){
  vec3 c = texture2D(tSrc, vUv).rgb * 4.0;
  c += texture2D(tSrc, vUv + uTexel * vec2(-1.0, -1.0)).rgb;
  c += texture2D(tSrc, vUv + uTexel * vec2( 1.0, -1.0)).rgb;
  c += texture2D(tSrc, vUv + uTexel * vec2(-1.0,  1.0)).rgb;
  c += texture2D(tSrc, vUv + uTexel * vec2( 1.0,  1.0)).rgb;
  gl_FragColor = vec4(c / 8.0, 1.0);
}`;
const UP_FRAG = /* glsl */`
varying vec2 vUv; uniform sampler2D tSrc; uniform sampler2D tPrev; uniform vec2 uTexel;
void main(){
  vec3 c = vec3(0.0);
  c += texture2D(tSrc, vUv + uTexel * vec2(-1.0, 0.0)).rgb * 2.0;
  c += texture2D(tSrc, vUv + uTexel * vec2( 1.0, 0.0)).rgb * 2.0;
  c += texture2D(tSrc, vUv + uTexel * vec2( 0.0,-1.0)).rgb * 2.0;
  c += texture2D(tSrc, vUv + uTexel * vec2( 0.0, 1.0)).rgb * 2.0;
  c += texture2D(tSrc, vUv + uTexel * vec2(-1.0,-1.0)).rgb;
  c += texture2D(tSrc, vUv + uTexel * vec2( 1.0,-1.0)).rgb;
  c += texture2D(tSrc, vUv + uTexel * vec2(-1.0, 1.0)).rgb;
  c += texture2D(tSrc, vUv + uTexel * vec2( 1.0, 1.0)).rgb;
  gl_FragColor = vec4(c / 12.0 + texture2D(tPrev, vUv).rgb, 1.0);
}`;

const GRADE_FRAG = /* glsl */`
varying vec2 vUv;
uniform sampler2D tSrc; uniform sampler2D tBloom; uniform float uBloom; uniform float uExposure;
uniform float uSat; uniform vec3 uLift; uniform vec3 uGain; uniform float uGamma; uniform float uContrast;
// AgX (minimal fit) — soft, desaturating highlight roll-off
vec3 agxContrast(vec3 x){ vec3 x2 = x*x; vec3 x4 = x2*x2;
  return 15.5*x4*x2 - 40.14*x4*x + 31.96*x4 - 6.868*x2*x + 0.4298*x2 + 0.1191*x - 0.00232; }
vec3 agx(vec3 v){
  const mat3 m = mat3(0.842479062253094, 0.0423282422610123, 0.0423756549057051,
                      0.0784335999999992, 0.878468636469772, 0.0784336,
                      0.0792237451477643, 0.0791661274605434, 0.879142973793104);
  const mat3 mi = mat3(1.19687900512017, -0.0528968517574562, -0.0529716355144438,
                      -0.0980208811401368, 1.15190312990417, -0.0980434501171241,
                      -0.0990297440797205, -0.0989611768448433, 1.15107367264116);
  v = m * v;
  v = clamp(log2(max(v, 1e-10)), -12.47393, 4.026069);
  v = (v + 12.47393) / (4.026069 + 12.47393);
  v = agxContrast(v);
  v = mi * v;
  return pow(max(v, 0.0), vec3(2.2));
}
void main(){
  vec3 c = texture2D(tSrc, vUv).rgb + texture2D(tBloom, vUv).rgb * uBloom;
  c *= uExposure;
  c = agx(c);
  float l = dot(c, vec3(0.2126, 0.7152, 0.0722));
  c = mix(vec3(l), c, uSat);
  c = pow(max(c, 0.0), vec3(1.0 / uGamma));
  c = (c - 0.5) * uContrast + 0.5;
  c = uLift + c * (uGain - uLift);
  gl_FragColor = vec4(clamp(c, 0.0, 1.0), 1.0);
}`;

const FINAL_FRAG = /* glsl */`
varying vec2 vUv;
uniform sampler2D tSrc; uniform vec2 uRes; uniform float uTime; uniform float uGrain; uniform float uVignette;
uniform float uHelmet; uniform float uFade; uniform vec3 uFadeColor; uniform float uAberration; uniform float uFlash;
float luma(vec3 c){ return dot(c, vec3(0.299, 0.587, 0.114)); }
vec3 fxaa(vec2 uv){
  vec2 px = 1.0 / uRes;
  vec3 rgbM = texture2D(tSrc, uv).rgb;
  float lM = luma(rgbM);
  float lNW = luma(texture2D(tSrc, uv + vec2(-1.0, -1.0) * px).rgb);
  float lNE = luma(texture2D(tSrc, uv + vec2( 1.0, -1.0) * px).rgb);
  float lSW = luma(texture2D(tSrc, uv + vec2(-1.0,  1.0) * px).rgb);
  float lSE = luma(texture2D(tSrc, uv + vec2( 1.0,  1.0) * px).rgb);
  float lMin = min(lM, min(min(lNW, lNE), min(lSW, lSE)));
  float lMax = max(lM, max(max(lNW, lNE), max(lSW, lSE)));
  vec2 dir = vec2(-((lNW + lNE) - (lSW + lSE)), ((lNW + lSW) - (lNE + lSE)));
  float red = max((lNW + lNE + lSW + lSE) * 0.03125, 1.0 / 128.0);
  float rcp = 1.0 / (min(abs(dir.x), abs(dir.y)) + red);
  dir = clamp(dir * rcp, -8.0, 8.0) * px;
  vec3 a = 0.5 * (texture2D(tSrc, uv + dir * (1.0/3.0 - 0.5)).rgb + texture2D(tSrc, uv + dir * (2.0/3.0 - 0.5)).rgb);
  vec3 b = a * 0.5 + 0.25 * (texture2D(tSrc, uv - dir * 0.5).rgb + texture2D(tSrc, uv + dir * 0.5).rgb);
  float lB = luma(b);
  return (lB < lMin || lB > lMax) ? a : b;
}
float hash(vec2 p){ return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
void main(){
  vec2 uv = vUv;
  vec2 cuv = uv - 0.5; cuv.x *= uRes.x / uRes.y;
  float r = length(cuv);
  // helmet glass: slight barrel distortion and colour fringing towards the rim
  if (uHelmet > 0.0) {
    vec2 q = uv - 0.5;
    q *= 1.0 + uHelmet * 0.05 * dot(q, q);
    uv = q + 0.5;
  }
  vec3 c = fxaa(uv);
  if (uAberration > 0.0) {
    vec2 off = (uv - 0.5) * uAberration * 0.006;
    c.r = mix(c.r, texture2D(tSrc, uv + off).r, 0.8);
    c.b = mix(c.b, texture2D(tSrc, uv - off).b, 0.8);
  }
  float vig = 1.0 - uVignette * smoothstep(0.35, 1.05, r);
  c *= vig;
  if (uHelmet > 0.0) {
    // the round port of the copper helmet: soft rim, bevel highlight, near-black beyond
    float rim = smoothstep(0.98, 1.06, r);
    float bevel = smoothstep(0.93, 0.98, r) * (1.0 - smoothstep(0.98, 1.02, r));
    c = mix(c, c * 0.3 + vec3(0.07, 0.04, 0.022) * bevel, uHelmet * smoothstep(0.9, 1.02, r));
    c = mix(c, vec3(0.008, 0.007, 0.006), uHelmet * rim);
  }
  c += uFlash;
  float g = hash(uv * uRes + fract(uTime * 13.17) * 100.0) - 0.5;
  c += g * uGrain * (0.6 + 0.4 * (1.0 - luma(c)));
  c = mix(c, uFadeColor, uFade);
  c += (hash(gl_FragCoord.xy + uTime) - 0.5) / 255.0;
  gl_FragColor = vec4(c, 1.0);
}`;

function rt(w, h, opts = {}) {
  return new THREE.WebGLRenderTarget(Math.max(1, w | 0), Math.max(1, h | 0), {
    type: THREE.HalfFloatType, format: THREE.RGBAFormat, minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter,
    depthBuffer: false, stencilBuffer: false, ...opts,
  });
}

export const QUALITY = {
  low: { scale: 0.6, volScale: 0.25, steps: 14, airSteps: 6, shadow: 512, bloom: true },
  medium: { scale: 0.8, volScale: 0.33, steps: 20, airSteps: 8, shadow: 1024, bloom: true },
  high: { scale: 1.0, volScale: 0.5, steps: 28, airSteps: 12, shadow: 2048, bloom: true },
};

export class Pipeline {
  constructor(renderer) {
    this.renderer = renderer;
    this.quality = QUALITY.medium;
    this.cam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
    this.quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2));
    this.quad.frustumCulled = false;
    this.fsScene = new THREE.Scene(); this.fsScene.add(this.quad);
    this.frame = 0;
    this.prevViewProj = new THREE.Matrix4();
    this.resetHistory = true;

    const common = {
      uInvProj: { value: new THREE.Matrix4() }, uCamWorld: { value: new THREE.Matrix4() }, uCamPos: { value: new THREE.Vector3() },
      uNear: { value: 0.05 }, uFar: { value: 500 },
      uAirInv: { value: new THREE.Matrix4() }, uAirMin: { value: new THREE.Vector3() }, uAirMax: { value: new THREE.Vector3() }, uAirOn: { value: 0 },
    };
    this.common = common;
    const mk = (frag, uniforms) => new THREE.ShaderMaterial({ vertexShader: FSQ_VERT, fragmentShader: frag, uniforms, depthTest: false, depthWrite: false });
    const spotArr = (n, f) => Array.from({ length: n }, f);
    this.volMat = mk(VOL_FRAG, {
      ...UW.uniforms, ...common,
      tDepth: { value: null }, uMaxDist: { value: 90 }, uSteps: { value: 20 }, uFrame: { value: 0 }, uRes: { value: new THREE.Vector2() },
      uSunOn: { value: 1 }, uSunShadow: { value: null }, uSunShadowMat: { value: new THREE.Matrix4() }, uSunShadowOn: { value: 0 }, uShaftGain: { value: 1 },
      uSpotPos: { value: spotArr(4, () => new THREE.Vector3()) }, uSpotDir: { value: spotArr(4, () => new THREE.Vector3(0, -1, 0)) },
      uSpotColor: { value: spotArr(4, () => new THREE.Vector3()) }, uSpotCone: { value: spotArr(4, () => new THREE.Vector2(0.8, 0.9)) },
      uSpotShadowOn: { value: [0, 0, 0, 0] }, uSpotShadowMat: { value: spotArr(4, () => new THREE.Matrix4()) },
      uSpotShadow0: { value: null }, uSpotShadow1: { value: null }, uSpotShadow2: { value: null }, uSpotShadow3: { value: null },
      uSpotCount: { value: 0 }, uSpotG: { value: 0.55 }, uSpotMedium: { value: [0, 0, 0, 0] }, uPtMedium: { value: [0, 0, 0, 0] }, uSigmaAir: { value: 0.014 }, uAirSteps: { value: 10 },
      uPtPos: { value: spotArr(4, () => new THREE.Vector3()) }, uPtColor: { value: spotArr(4, () => new THREE.Vector3()) }, uPtCount: { value: 0 },
    });
    this.temporalMat = mk(TEMPORAL_FRAG, { ...common, tCur: { value: null }, tHist: { value: null }, uPrevViewProj: { value: new THREE.Matrix4() }, uBlend: { value: 0.88 }, uReset: { value: 1 } });
    this.compMat = mk(COMPOSITE_FRAG, {
      ...UW.uniforms, ...common, tColor: { value: null }, tDepth: { value: null }, tVol: { value: null }, uVolRes: { value: new THREE.Vector2() },
      uSurfaceOn: { value: 1 }, uDbg: { value: 0 }, uVolGain: { value: 1.6 }, uFogGain: { value: 0.11 }, uLocalFog: { value: 0 }, uLocalFogColor: { value: new THREE.Vector3(0.0, 0.004, 0.006) }, uAirHaze: { value: 0 },
    });
    this.brightMat = mk(BRIGHT_FRAG, { tSrc: { value: null }, uTexel: { value: new THREE.Vector2() }, uThreshold: { value: 0.9 } });
    this.downMat = mk(DOWN_FRAG, { tSrc: { value: null }, uTexel: { value: new THREE.Vector2() } });
    this.upMat = mk(UP_FRAG, { tSrc: { value: null }, tPrev: { value: null }, uTexel: { value: new THREE.Vector2() } });
    this.gradeMat = mk(GRADE_FRAG, {
      tSrc: { value: null }, tBloom: { value: null }, uBloom: { value: 0.12 }, uExposure: { value: 1.0 },
      uSat: { value: 0.82 }, uLift: { value: new THREE.Vector3(0.006, 0.01, 0.012) }, uGain: { value: new THREE.Vector3(1.0, 1.0, 0.98) },
      uGamma: { value: 1.0 }, uContrast: { value: 1.1 },
    });
    this.finalMat = mk(FINAL_FRAG, {
      tSrc: { value: null }, uRes: { value: new THREE.Vector2() }, uTime: { value: 0 }, uGrain: { value: 0.035 }, uVignette: { value: 0.55 },
      uHelmet: { value: 0 }, uFade: { value: 1 }, uFadeColor: { value: new THREE.Vector3(0, 0, 0) }, uAberration: { value: 0 }, uFlash: { value: 0 },
    });
    this.blackTex = new THREE.DataTexture(new Uint8Array([255, 255, 255, 255]), 1, 1); this.blackTex.needsUpdate = true;
    this.setSize(1, 1);
  }

  setQuality(q) { this.quality = q; this.setSize(this.w, this.h); this.resetHistory = true; }

  setSize(w, h) {
    this.w = w; this.h = h;
    const q = this.quality;
    const sw = Math.max(1, Math.round(w * q.scale)), sh = Math.max(1, Math.round(h * q.scale));
    const dispose = (x) => x && x.dispose();
    [this.sceneRT, this.compRT, this.ldrRT, this.volRaw, this.volA, this.volB, ...(this.bloomDown || []), ...(this.bloomUp || [])].forEach(dispose);
    this.sceneRT = rt(sw, sh, { depthBuffer: true });
    this.sceneRT.depthTexture = new THREE.DepthTexture(sw, sh, THREE.UnsignedIntType);
    this.compRT = rt(sw, sh);
    this.ldrRT = rt(sw, sh, { type: THREE.UnsignedByteType });
    const vw = Math.max(1, Math.round(sw * q.volScale)), vh = Math.max(1, Math.round(sh * q.volScale));
    const nearest = { minFilter: THREE.NearestFilter, magFilter: THREE.NearestFilter };
    this.volRaw = rt(vw, vh, nearest); this.volA = rt(vw, vh, nearest); this.volB = rt(vw, vh, nearest);
    this.volRes = new THREE.Vector2(vw, vh);
    this.bloomDown = []; this.bloomUp = [];
    let bw = sw >> 1, bh = sh >> 1;
    for (let i = 0; i < 5; i++) { this.bloomDown.push(rt(bw, bh)); this.bloomUp.push(rt(bw, bh)); bw = Math.max(1, bw >> 1); bh = Math.max(1, bh >> 1); }
    this.sw = sw; this.sh = sh;
    this.resetHistory = true;
  }

  pass(mat, target) {
    this.quad.material = mat;
    this.renderer.setRenderTarget(target);
    this.renderer.render(this.fsScene, this.cam);
  }

  // env: { extScene, intScene, camera, air: {matrixInv, min, max, on}, lights: {...}, particles: Points (rendered after composite) }
  render(env, dt, time) {
    const r = this.renderer;
    const cam = env.camera;
    cam.updateMatrixWorld();
    const q = this.quality;
    // 1) scenes
    r.setRenderTarget(this.sceneRT);
    r.setClearColor(0x000000, 1);
    r.clear(true, true, true);
    r.autoClear = false;
    if (env.extScene) r.render(env.extScene, cam);
    if (env.intScene) r.render(env.intScene, cam);
    r.autoClear = true;

    // shared camera uniforms
    const c = this.common;
    c.uInvProj.value.copy(cam.projectionMatrixInverse);
    c.uCamWorld.value.copy(cam.matrixWorld);
    c.uCamPos.value.setFromMatrixPosition(cam.matrixWorld);
    c.uNear.value = cam.near; c.uFar.value = cam.far;
    if (env.air) {
      c.uAirInv.value.copy(env.air.matrixInv); c.uAirMin.value.copy(env.air.min); c.uAirMax.value.copy(env.air.max); c.uAirOn.value = env.air.on ? 1 : 0;
    } else c.uAirOn.value = 0;
    if (env.particles) env.particles.alwaysAir = !!env.air;

    // 2) volumetric light
    const vm = this.volMat.uniforms;
    vm.tDepth.value = this.sceneRT.depthTexture;
    vm.uSteps.value = q.steps; vm.uAirSteps.value = env.air && env.air.on && env.insideAir ? q.airSteps : 0; vm.uFrame.value = this.frame % 64; vm.uRes.value.copy(this.volRes);
    const L = env.lights || {};
    vm.uSunOn.value = L.sun ? 1 : 0;
    if (L.sun && L.sun.castShadow && L.sun.shadow.map) {
      vm.uSunShadow.value = L.sun.shadow.map.texture; vm.uSunShadowMat.value.copy(L.sun.shadow.matrix); vm.uSunShadowOn.value = 1;
    } else { vm.uSunShadowOn.value = 0; vm.uSunShadow.value = this.blackTex; }
    const spots = (L.spots || []).filter((s) => s.visible && s.intensity > 0).slice(0, 4);
    vm.uSpotCount.value = spots.length;
    const tmp = new THREE.Vector3();
    for (let i = 0; i < 4; i++) {
      const s = spots[i];
      const key = 'uSpotShadow' + i;
      if (!s) { vm[key].value = this.blackTex; vm.uSpotShadowOn.value[i] = 0; continue; }
      s.updateMatrixWorld();
      vm.uSpotPos.value[i].setFromMatrixPosition(s.matrixWorld);
      tmp.setFromMatrixPosition(s.target.matrixWorld);
      vm.uSpotDir.value[i].copy(tmp).sub(vm.uSpotPos.value[i]).normalize();
      const vol = s.userData.volumetric ?? 1;
      vm.uSpotMedium.value[i] = s.userData.medium === 'air' ? 1 : 0;
      vm.uSpotColor.value[i].set(s.color.r, s.color.g, s.color.b).multiplyScalar(s.intensity * vol);
      vm.uSpotCone.value[i].set(Math.cos(s.angle), Math.cos(s.angle * (1 - s.penumbra)));
      if (s.castShadow && s.shadow.map) { vm[key].value = s.shadow.map.texture; vm.uSpotShadowMat.value[i].copy(s.shadow.matrix); vm.uSpotShadowOn.value[i] = 1; }
      else { vm[key].value = this.blackTex; vm.uSpotShadowOn.value[i] = 0; }
    }
    const pts = (L.points || []).filter((p) => p.visible && p.intensity > 0).slice(0, 4);
    vm.uPtCount.value = pts.length;
    pts.forEach((p, i) => { vm.uPtMedium.value[i] = p.userData.medium === 'air' ? 1 : 0; p.updateMatrixWorld(); vm.uPtPos.value[i].setFromMatrixPosition(p.matrixWorld); vm.uPtColor.value[i].set(p.color.r, p.color.g, p.color.b).multiplyScalar(p.intensity * (p.userData.volumetric ?? 1)); });
    this.pass(this.volMat, this.volRaw);

    // 3) temporal accumulation
    const tm = this.temporalMat.uniforms;
    tm.tCur.value = this.volRaw.texture; tm.tHist.value = this.volB.texture;
    tm.uPrevViewProj.value.copy(this.prevViewProj); tm.uReset.value = this.resetHistory ? 1 : 0;
    this.pass(this.temporalMat, this.volA);
    [this.volA, this.volB] = [this.volB, this.volA];
    this.resetHistory = false;
    this.prevViewProj.multiplyMatrices(cam.projectionMatrix, cam.matrixWorldInverse);

    // 4) composite
    const cm = this.compMat.uniforms;
    cm.tColor.value = this.sceneRT.texture; cm.tDepth.value = this.sceneRT.depthTexture; cm.tVol.value = this.volB.texture; cm.uVolRes.value.copy(this.volRes);
    this.pass(this.compMat, this.compRT);

    // 5) particles (they fog themselves and test against scene depth)
    if (env.particles || env.overlay) {
      r.setRenderTarget(this.compRT);
      r.autoClear = false;
      if (env.particles) { env.particles.update(this, cam, dt, env.current); r.render(env.particles.scene, cam); }
      if (env.overlay) r.render(env.overlay, cam);
      r.autoClear = true;
    }

    // 6) bloom
    let bloomTex = this.blackTex;
    if (q.bloom) {
      const bm = this.brightMat.uniforms;
      bm.tSrc.value = this.compRT.texture; bm.uTexel.value.set(1 / this.sw, 1 / this.sh);
      this.pass(this.brightMat, this.bloomDown[0]);
      for (let i = 1; i < this.bloomDown.length; i++) {
        const src = this.bloomDown[i - 1];
        this.downMat.uniforms.tSrc.value = src.texture; this.downMat.uniforms.uTexel.value.set(1 / src.width, 1 / src.height);
        this.pass(this.downMat, this.bloomDown[i]);
      }
      const n = this.bloomDown.length;
      let prev = this.blackTex;
      for (let i = n - 1; i >= 0; i--) {
        const src = i === n - 1 ? this.bloomDown[i] : this.bloomUp[i + 1];
        this.upMat.uniforms.tSrc.value = src.texture; this.upMat.uniforms.tPrev.value = i === n - 1 ? this.blackTex : this.bloomDown[i].texture;
        this.upMat.uniforms.uTexel.value.set(1 / src.width, 1 / src.height);
        this.pass(this.upMat, this.bloomUp[i]);
      }
      bloomTex = this.bloomUp[0].texture;
    }
    // 7) grade
    this.gradeMat.uniforms.tSrc.value = this.compRT.texture; this.gradeMat.uniforms.tBloom.value = bloomTex;
    this.pass(this.gradeMat, this.ldrRT);
    // 8) final
    const fm = this.finalMat.uniforms;
    fm.tSrc.value = this.ldrRT.texture; fm.uRes.value.set(this.sw, this.sh); fm.uTime.value = time;
    this.pass(this.finalMat, null);
    this.frame++;
  }
}
