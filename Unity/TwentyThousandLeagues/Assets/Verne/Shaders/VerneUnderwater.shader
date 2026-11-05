// Hidden/Verne/Underwater: the three passes of VerneUnderwaterFeature (M3).
// 0 March (reduced res)  1 Temporal (reprojection + neighbourhood clamp)  2 Composite (full res, dithered).
// Conservative URP HLSL: Core.hlsl, Lighting.hlsl (main light + shadows), DeclareDepthTexture.hlsl, core Blit.hlsl.
// 5 Nov 2026: physical optics feed it (WaterOptics), caustics moved here from the light cookie (depth-blurred, chromatic on
// Full), floor silt, albedo² multiple scattering, golden-ratio temporal jitter, INSIDE's fog cap on bright pixels.
Shader "Hidden/Verne/Underwater"
{
    SubShader
    {
        Tags { "RenderType" = "Opaque" "RenderPipeline" = "UniversalPipeline" }
        ZTest Always ZWrite Off Cull Off

        HLSLINCLUDE
        #pragma target 3.5
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareDepthTexture.hlsl"
        #include "Packages/com.unity.render-pipelines.core/Runtime/Utilities/Blit.hlsl"

        float4 _VerneMarch;            // x steps, y max distance, z frame (0..63), w history weight
        float4 _VerneSigmaT;           // extinction per metre (rgb)
        float4 _VerneAlbedo;           // single-scattering albedo (rgb)
        float4 _VerneKd;               // diffuse attenuation of daylight with depth (rgb)
        float4 _VerneSurface;          // x surface height, y HG g, z sun shaft strength
        float4 _VerneSurfaceAmbient;   // sky light just under the surface (rgb)
        float4 _VerneLowSize;          // low-res width, height, 1/width, 1/height
        float4 _VerneLampPosArr[4];    // xyz, w range
        float4 _VerneLampDirArr[4];    // xyz forward, w cos(outer half-angle) (-2 = point light)
        float4 _VerneLampColArr[4];    // rgb * intensity, w cos(inner half-angle)
        int _VerneLampCount;
        float4x4 _VernePrevVP;
        float4 _VerneAmbientFloor;     // light in the water that is not daylight (night, scattered glow)
        float4 _VerneGlowPos;          // xyz, w = range: a distant glow scattered many times (the volcano)
        float4 _VerneGlowCol;
        float4 _VerneSunRaw;           // the sun before VerneWater tints it for the eye's depth (w = 1 when set)
        float4 _VerneExtra;            // x multiple-scatter strength, y caustic strength, z chromatic caustics (0/1), w bright-light fog cap
        float4 _VerneWhiteBalance;     // rgb divisor: the eye adapting to the water's colour (physical optics; 1 = none)
        float4 _VerneSilt;             // x floor silt (1/m), y silt layer height (m)
        float4 _VerneCausticXform;     // x 1/tile size (1/m), y depth of full fade (m), zw drift offset
        TEXTURE2D(_VerneCausticTex); SAMPLER(sampler_VerneCausticTex);
        TEXTURE2D(_VerneHistory);
        TEXTURE2D(_VerneScatterTex);

        float IGN(float2 p) { return frac(52.9829189 * frac(dot(p, float2(0.06711056, 0.00583715)))); }

        float PhaseHG(float c, float g)
        {
            float g2 = g * g;
            return (1.0 - g2) / (4.0 * PI * pow(max(1e-3, 1.0 + g2 - 2.0 * g * c), 1.5));
        }

        // The sun's caustic web at p (Docs/RESEARCH_underwater.md §1.4): the pattern is projected along the sun from the
        // surface, two drifting layers combined with min() so the bright lines are thin, sharp just under the surface and
        // blurred (higher mip) and fading with depth. chroma > 0 samples R, G and B a little apart: Verne's prism fringes.
        float3 Caustic(float3 p, float depth, float chroma)
        {
            if (_VerneExtra.y <= 0.0) return 1.0;
            Light sun = GetMainLight();
            float3 L = sun.direction;                                   // toward the light
            float2 xz = p.xz + L.xz / max(L.y, 0.2) * depth;          // where this point's light came through the surface
            float2 uv = xz * _VerneCausticXform.x;
            float lod = clamp(depth * 0.16, 0.0, 6.0);
            float2 o1 = _VerneCausticXform.zw, o2 = -_VerneCausticXform.zw * 0.73 + float2(0.31, 0.57);
            float2 disp = float2(0.004, 0.0025) * (1.0 + depth * 0.15) * chroma;
            float3 c;
            c.r = min(SAMPLE_TEXTURE2D_LOD(_VerneCausticTex, sampler_VerneCausticTex, uv + o1 + disp, lod).r, SAMPLE_TEXTURE2D_LOD(_VerneCausticTex, sampler_VerneCausticTex, uv * 1.37 + o2 + disp, lod).r);
            c.g = min(SAMPLE_TEXTURE2D_LOD(_VerneCausticTex, sampler_VerneCausticTex, uv + o1, lod).r, SAMPLE_TEXTURE2D_LOD(_VerneCausticTex, sampler_VerneCausticTex, uv * 1.37 + o2, lod).r);
            c.b = chroma > 0.0 ? min(SAMPLE_TEXTURE2D_LOD(_VerneCausticTex, sampler_VerneCausticTex, uv + o1 - disp, lod).r, SAMPLE_TEXTURE2D_LOD(_VerneCausticTex, sampler_VerneCausticTex, uv * 1.37 + o2 - disp, lod).r) : c.g;
            float fade = saturate(1.0 - depth / max(_VerneCausticXform.y, 1.0));
            return lerp(1.0, c * 2.2, fade * fade);                      // mean ≈ 1: the web redistributes light, it doesn't add it
        }
        float3 VolumeCookie(float3 p, float depth) { return Caustic(p, depth, 0.0); }
        float3 Daylight(float y) { return exp(-_VerneKd.rgb * max(0.0, _VerneSurface.x - y)); }
        // the water's own light at p besides the sun: the floor ambient and the glow, art-directed as in the browser build
        float3 WaterGlow(float3 p)
        {
            float3 g = p - _VerneGlowPos.xyz;
            return _VerneAmbientFloor.rgb + _VerneGlowCol.rgb / (1.0 + dot(g, g) / (_VerneGlowPos.w * _VerneGlowPos.w));
        }

        // eye ray to the opaque surface under uv; far plane = open water
        void EyeRay(float2 uv, out float3 ro, out float3 rd, out float dist)
        {
            float raw = SampleSceneDepth(uv);
            float3 posWS = ComputeWorldSpacePosition(uv, raw, UNITY_MATRIX_I_VP);
            ro = _WorldSpaceCameraPos;
            float3 v = posWS - ro;
            dist = length(v);
            rd = v / max(dist, 1e-4);
        #if UNITY_REVERSED_Z
            if (raw <= 1e-6) dist = 1e5;
        #else
            if (raw >= 1.0 - 1e-6) dist = 1e5;
        #endif
        }
        ENDHLSL

        Pass
        {
            Name "VerneMarch"
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment FragMarch
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE

            half4 FragMarch(Varyings i) : SV_Target
            {
                float3 ro, rd; float dist;
                EyeRay(i.texcoord, ro, rd, dist);
                float tMax = min(dist, _VerneMarch.y);
                int steps = (int)_VerneMarch.x;
                float jitter = frac(IGN(i.positionCS.xy) + _VerneMarch.z * 0.6180339887);   // IGN in space, golden ratio in time (blue-noise-like after the temporal pass)
                float invN = 1.0 / max(steps, 1);
                float spread = max(_VerneSurface.w, 1.0);                                // 1 = even spacing, 2 = packed toward the eye
                float3 sigT0 = max(_VerneSigmaT.rgb, 1e-4);
                float3 sigS0 = sigT0 * _VerneAlbedo.rgb;
                float floorY = ro.y + rd.y * dist;                                       // the floor this ray ends on (silt hangs above it)
                bool hitsFloor = dist < 1e4;
                Light sun = GetMainLight();
                float phaseSun = PhaseHG(dot(rd, sun.direction), _VerneSurface.y) * _VerneSurface.z;
                float3 T = 1.0, S = 0.0;
                [loop] for (int k = 0; k < 32; k++)
                {
                    if (k >= steps) break;
                    // samples packed toward the eye (quadratic), each standing for its own segment of the ray
                    float u = (k + jitter) * invN;
                    float t = tMax * pow(u, spread);
                    float dt = tMax * (pow((k + 1.0) * invN, spread) - pow(k * invN, spread));
                    float3 p = ro + rd * t;
                    // stirred-up silt in the bottom metres: grey, strongly scattering (Docs/RESEARCH_underwater.md §3.3)
                    float silt = hitsFloor ? _VerneSilt.x * exp(-max(0.0, p.y - floorY) / max(_VerneSilt.y, 0.3)) : 0.0;
                    float3 sigT = sigT0 + silt;
                    float3 sigS = sigS0 + silt * 0.92;
                    float3 day = Daylight(p.y);
                    float3 amb = _VerneSurfaceAmbient.rgb * day + WaterGlow(p);
                    float3 alb = sigS / sigT;
                    float3 Lin = amb * (1.0 + _VerneExtra.x * alb * alb);                 // diffuse sky light + light scattered again (albedo²)
                    float sh = MainLightRealtimeShadow(TransformWorldToShadowCoord(p));   // real shafts through the scene
                    float3 sunCol = _VerneSunRaw.w > 0.5 ? _VerneSunRaw.rgb : sun.color;   // daylight is applied per sample, once
                    // god rays, from two real causes only: what the shadow map says blocks the light (ridge, kelp, trees),
                    // and the surface's waves focusing sunlight (the sun's caustic cookie, the same light that draws the web on
                    // the floor), whose lines run down through the water as shafts and blur out with depth as real caustics do
                    Lin += sunCol * day * sh * phaseSun * VolumeCookie(p, max(0.0, _VerneSurface.x - p.y));
                    [loop] for (int j = 0; j < 4; j++)
                    {
                        if (j >= _VerneLampCount) break;
                        float3 Lv = _VerneLampPosArr[j].xyz - p;
                        float d = length(Lv);
                        float3 l = Lv / max(d, 1e-3);
                        float cone = 1.0;
                        if (_VerneLampDirArr[j].w > -1.5) cone = smoothstep(_VerneLampDirArr[j].w, _VerneLampColArr[j].w, dot(-l, _VerneLampDirArr[j].xyz));
                        float r = max(_VerneLampPosArr[j].w, 0.01);
                        float win = saturate(1.0 - (d * d) / (r * r));
                        Lin += _VerneLampColArr[j].rgb * (cone * win * win / (1.0 + d * d)) * exp(-sigT * d) * PhaseHG(dot(rd, l), _VerneSurface.y) * 4.0 * PI;
                    }
                    float3 stepT = exp(-sigT * dt);
                    S += T * Lin * sigS * (1.0 - stepT) / sigT;                           // energy-conserving per channel
                    T *= stepT;
                }
                return half4(S, tMax);
            }
            ENDHLSL
        }

        Pass
        {
            Name "VerneTemporal"
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment FragTemporal

            half4 FragTemporal(Varyings i) : SV_Target
            {
                float2 uv = i.texcoord;
                float2 o = _VerneLowSize.zw;
                float4 c0 = SAMPLE_TEXTURE2D_X_LOD(_BlitTexture, sampler_PointClamp, uv, 0);
                float4 c1 = SAMPLE_TEXTURE2D_X_LOD(_BlitTexture, sampler_PointClamp, uv + float2(o.x, 0), 0);
                float4 c2 = SAMPLE_TEXTURE2D_X_LOD(_BlitTexture, sampler_PointClamp, uv - float2(o.x, 0), 0);
                float4 c3 = SAMPLE_TEXTURE2D_X_LOD(_BlitTexture, sampler_PointClamp, uv + float2(0, o.y), 0);
                float4 c4 = SAMPLE_TEXTURE2D_X_LOD(_BlitTexture, sampler_PointClamp, uv - float2(0, o.y), 0);
                float3 mn = min(c0.rgb, min(min(c1.rgb, c2.rgb), min(c3.rgb, c4.rgb)));
                float3 mx = max(c0.rgb, max(max(c1.rgb, c2.rgb), max(c3.rgb, c4.rgb)));
                float3 ro, rd; float dist;
                EyeRay(uv, ro, rd, dist);
                float3 pEnd = ro + rd * min(dist, c0.a);
                float2 puv = ComputeNormalizedDeviceCoordinates(pEnd, _VernePrevVP);
                float valid = all(puv > 0.0) && all(puv < 1.0) ? 1.0 : 0.0;
                float4 h = SAMPLE_TEXTURE2D_LOD(_VerneHistory, sampler_LinearClamp, puv, 0);
                float3 hc = clamp(h.rgb, mn, mx);
                float w = _VerneMarch.w * valid;
                return half4(lerp(c0.rgb, hc, w), c0.a);
            }
            ENDHLSL
        }

        Pass
        {
            Name "VerneComposite"
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment FragComposite
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE

            half4 FragComposite(Varyings i) : SV_Target
            {
                float2 uv = i.texcoord;
                float4 scene = SAMPLE_TEXTURE2D_X_LOD(_BlitTexture, sampler_PointClamp, uv, 0);
                float3 ro, rd; float dist;
                EyeRay(uv, ro, rd, dist);
                float tMax = min(dist, _VerneMarch.y);
                // depth-aware upsample of the in-scattering: the four low-res neighbours, bilinear weights
                // scaled down where their march length disagrees with this pixel's (no halos round silhouettes)
                float2 lp = uv * _VerneLowSize.xy - 0.5;
                float2 f = frac(lp);
                float2 b = (floor(lp) + 0.5) * _VerneLowSize.zw;
                float3 S = 0; float wsum = 0;
                [unroll] for (int k = 0; k < 4; k++)
                {
                    float2 off = float2(k & 1, k >> 1);
                    float4 s = SAMPLE_TEXTURE2D_LOD(_VerneScatterTex, sampler_PointClamp, b + off * _VerneLowSize.zw, 0);
                    float bw = (off.x > 0.5 ? f.x : 1.0 - f.x) * (off.y > 0.5 ? f.y : 1.0 - f.y);
                    float dw = 1.0 / (0.05 + abs(s.a - tMax) / max(tMax, 0.5));
                    float wk = bw * dw + 1e-5;
                    S += s.rgb * wk; wsum += wk;
                }
                S /= max(wsum, 1e-5);
                float3 sigT = max(_VerneSigmaT.rgb, 1e-4);
                // caustics on surfaces that face the sun and aren't shadowed (normal from the depth's derivatives)
                float3 posWS = ro + rd * min(dist, 1e4);
                float3 n = normalize(cross(ddy(posWS), ddx(posWS)) + 1e-7);    // derivatives taken outside any branch
                if (dot(n, -rd) < 0.0) n = -n;
                if (dist < 1e4 && _VerneExtra.y > 0.0)
                {
                    Light sun = GetMainLight();
                    float ndl = saturate(dot(n, sun.direction));
                    float depthW = max(0.0, _VerneSurface.x - posWS.y);
                    float sh = MainLightRealtimeShadow(TransformWorldToShadowCoord(posWS));
                    float3 c = Caustic(posWS, depthW, _VerneExtra.z);
                    scene.rgb *= lerp(1.0, c, saturate(ndl * 1.5) * sh * _VerneExtra.y);
                }
                // beyond the march: the analytic far field, lit by daylight at that depth
                float3 Tm = exp(-sigT * tMax);
                float3 farP = ro + rd * tMax;
                float3 Lfar = _VerneSurfaceAmbient.rgb * Daylight(farP.y) + WaterGlow(farP);
                float3 Sfar = Tm * Lfar * _VerneAlbedo.rgb * (1.0 - exp(-sigT * max(0.0, dist - tMax)));
                float3 T = exp(-sigT * dist);
                // INSIDE capped the fog so very bright sources still shine through: lava, lamp glass, the moon's gleam
                float bright = saturate((dot(scene.rgb, float3(0.2126, 0.7152, 0.0722)) - 1.0) * 0.5) * _VerneExtra.w;
                T = lerp(T, sqrt(T), bright);
                float3 col = scene.rgb * T + (S + Sfar) * (1.0 - 0.5 * bright);
                // Snell's window: looking up through open water, the sky is squeezed into a bright disc of
                // half-angle 48.6°; outside it the surface is a dim mirror (total internal reflection)
                if (dist > 1e4 && rd.y > 0.05)
                {
                    float dS = (_VerneSurface.x - ro.y) / rd.y;
                    float3 Ts = exp(-sigT * max(dS, 0.0));
                    float win = smoothstep(0.64, 0.69, rd.y);
                    float3 sky = _VerneSurfaceAmbient.rgb * (win * 7.0 + (1.0 - win) * 0.5 * rd.y);
                    col += Ts * sky;
                }
                col /= max(_VerneWhiteBalance.rgb, 0.2);                                     // the diver's eye adapts to the water (RESEARCH §1)
                col += (IGN(i.positionCS.xy + _VerneMarch.z * 3.1) - 0.5) * (1.0 / 255.0);   // dither against banding
                return half4(max(col, 0.0), scene.a);
            }
            ENDHLSL
        }
    }
    Fallback Off
}
