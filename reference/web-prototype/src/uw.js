// Underwater light model shared by every exterior material, the volumetric pass and the composite.
// Physical idea: sunlight enters at the surface and is absorbed per colour channel with depth
// (red first, then green, blue last). Anything seen through water is attenuated along the
// view ray (beam attenuation c = absorption a + scattering b) and the water itself glows with
// in-scattered ambient light, brighter above and darker below.
import * as THREE from 'three';

export const UW = {
  uniforms: {
    uSigmaA: { value: new THREE.Vector3(0.12, 0.045, 0.03) },   // absorption per metre (RGB)
    uSigmaS: { value: new THREE.Vector3(0.034, 0.040, 0.044) }, // scattering per metre (RGB)
    uKd: { value: new THREE.Vector3(0.11, 0.035, 0.022) },      // diffuse attenuation of daylight per metre of depth
    uDepthBase: { value: 9.0 },   // physical depth (m) at uYRef
    uYRef: { value: 0.0 },        // world height that maps to uDepthBase
    uDepthScale: { value: 1.0 },  // physical metres of depth per world metre of height
    uDepthQuad: { value: 0.0 },   // extra depth per (world metre below yRef)^2, for long descents
    uSunDir: { value: new THREE.Vector3(0.35, -0.9, 0.2).normalize() }, // direction light travels (refracted)
    uSunColor: { value: new THREE.Vector3(3.2, 3.1, 2.9) },     // direct irradiance just below the surface
    uAmbTop: { value: new THREE.Vector3(1.2, 1.5, 1.7) },      // ambient (sky) irradiance just below the surface
    uAmbFloor: { value: 0.0 },    // extra ambient that does not fade with depth (night glow, bioluminescence)
    uAmbFloorColor: { value: new THREE.Vector3(0.02, 0.03, 0.035) },
    uCaustics: { value: null },
    uCausticStrength: { value: 1.0 },
    uTime: { value: 0 },
    uWaterOn: { value: 1.0 },
  },
};

export function depthAt(y) {
  const u = UW.uniforms; const d = u.uYRef.value - y;
  return Math.max(0, u.uDepthBase.value + d * u.uDepthScale.value + Math.sign(d) * d * d * u.uDepthQuad.value);
}

export const UW_GLSL = /* glsl */`
uniform vec3 uSigmaA; uniform vec3 uSigmaS; uniform vec3 uKd;
uniform float uDepthBase; uniform float uYRef; uniform float uDepthScale; uniform float uDepthQuad;
uniform vec3 uSunDir; uniform vec3 uSunColor; uniform vec3 uAmbTop;
uniform float uAmbFloor; uniform vec3 uAmbFloorColor;
uniform sampler2D uCaustics; uniform float uCausticStrength; uniform float uTime; uniform float uWaterOn;

float uwDepth(float y){ float d = uYRef - y; return max(0.0, uDepthBase + d * uDepthScale + sign(d) * d * d * uDepthQuad); }
float uwDepthSlope(float y){ return uDepthScale + 2.0 * uDepthQuad * abs(uYRef - y); }
vec3 uwSigmaT(){ return uSigmaA + uSigmaS; }
vec3 uwT(float dist){ return mix(vec3(1.0), exp(-uwSigmaT() * dist), uWaterOn); }
vec3 uwSunAtten(float y){ return exp(-uKd * uwDepth(y)); }
vec2 uwSunProj(vec3 p){ return p.xz - uSunDir.xz / min(uSunDir.y, -0.05) * (p.y - uYRef); }
float uwCaustic(vec3 p, float lod){
  vec2 q = uwSunProj(p) * 0.11;
  float a = textureLod(uCaustics, q + uTime * vec2(0.010, 0.006), lod).r;
  float b = textureLod(uCaustics, q * 1.37 + vec2(0.31, 0.77) - uTime * vec2(0.008, -0.0075), lod).r;
  return min(a, b);
}
// direct sun reaching point p (before any shadowing)
vec3 uwSunAt(vec3 p){
  float d = uwDepth(p.y);
  float cst = uwCaustic(p, 0.0);
  float contrast = uCausticStrength * exp(-d * 0.045);       // caustics blur out with depth
  float c = mix(1.0, 0.25 + 2.6 * cst * cst, contrast);
  return uSunColor * uwSunAtten(p.y) * c;
}
// broad, slowly drifting beams of sunlight (low-frequency version of the caustic net)
float uwShaft(vec3 p){
  vec2 q = uwSunProj(p) * 0.016;
  float a = textureLod(uCaustics, q + uTime * vec2(0.0016, 0.001), 3.0).r;
  float b = textureLod(uCaustics, q * 0.63 + vec2(0.5, 0.2) - uTime * vec2(0.0012, -0.0009), 3.0).r;
  float c = max(a, b);
  return smoothstep(0.08, 0.7, c) * c;
}
vec3 uwAmbientAt(float y){ return uAmbTop * uwSunAtten(y) + uAmbFloor * uAmbFloorColor; }
`;

// Patch a MeshStandardMaterial so it is lit like an object under water.
export function patchUnderwater(material, opts = {}) {
  const ambientScale = opts.ambientScale ?? 1.0;
  material.onBeforeCompile = (shader) => {
    for (const k in UW.uniforms) shader.uniforms[k] = UW.uniforms[k];
    shader.uniforms.uAmbScale = { value: ambientScale };
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vUwWorld;')
      .replace('#include <project_vertex>', `#include <project_vertex>
        vec4 uwWp = vec4(transformed, 1.0);
        #ifdef USE_INSTANCING
          uwWp = instanceMatrix * uwWp;
        #endif
        vUwWorld = (modelMatrix * uwWp).xyz;`);
    const lights = THREE.ShaderChunk.lights_fragment_begin
      .replace('getDirectionalLightInfo( directionalLight, directLight );',
        'getDirectionalLightInfo( directionalLight, directLight ); directLight.color *= uwSunAt(vUwWorld);')
      .replace('getSpotLightInfo( spotLight, geometryPosition, directLight );',
        'getSpotLightInfo( spotLight, geometryPosition, directLight ); directLight.color *= uwT(length(spotLight.position - geometryPosition));')
      .replace('getPointLightInfo( pointLight, geometryPosition, directLight );',
        'getPointLightInfo( pointLight, geometryPosition, directLight ); directLight.color *= uwT(length(pointLight.position - geometryPosition));');
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vUwWorld;\nuniform float uAmbScale;\n' + UW_GLSL)
      .replace('#include <lights_fragment_begin>', lights)
      .replace('#include <aomap_fragment>', `#include <aomap_fragment>
        {
          vec3 upV = normalize((viewMatrix * vec4(0.0, 1.0, 0.0, 0.0)).xyz);
          float up = dot(normal, upV);
          vec3 amb = uwAmbientAt(vUwWorld.y) * (0.55 + 0.45 * up) * uAmbScale;
          reflectedLight.indirectDiffuse += BRDF_Lambert(diffuseColor.rgb) * amb * 3.14159;
        }`);
  };
  material.customProgramCacheKey = () => 'uw' + ambientScale;
  return material;
}

// Tileable caustic pattern (Voronoi edge network), generated once.
export function makeCausticTexture(size = 256) {
  const cells = 9;
  const pts = [];
  let seed = 7;
  const rnd = () => { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; };
  for (let j = 0; j < cells; j++) for (let i = 0; i < cells; i++) pts.push([(i + rnd()) / cells, (j + rnd()) / cells]);
  const data = new Uint8Array(size * size * 4);
  for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
    const u = x / size, v = y / size;
    let f1 = 9, f2 = 9;
    for (const p of pts) for (let oy = -1; oy <= 1; oy++) for (let ox = -1; ox <= 1; ox++) {
      const dx = u - (p[0] + ox), dy = v - (p[1] + oy);
      const d = Math.sqrt(dx * dx + dy * dy);
      if (d < f1) { f2 = f1; f1 = d; } else if (d < f2) f2 = d;
    }
    const e = Math.min(1, (f2 - f1) * cells * 1.6);
    const c = Math.pow(1 - e, 3.0);
    const i = (y * size + x) * 4;
    data[i] = data[i + 1] = data[i + 2] = Math.round(c * 255); data[i + 3] = 255;
  }
  const tex = new THREE.DataTexture(data, size, size, THREE.RGBAFormat);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.minFilter = THREE.LinearMipmapLinearFilter; tex.magFilter = THREE.LinearFilter;
  tex.generateMipmaps = true; tex.needsUpdate = true;
  return tex;
}
