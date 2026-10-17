// Hidden/Verne/Underwater: the three passes of VerneUnderwaterFeature (M3).
// 0 March (reduced res)  1 Temporal (reprojection + neighbourhood clamp)  2 Composite (full res, dithered).
// Conservative URP HLSL: Core.hlsl, Lighting.hlsl (main light + shadows), DeclareDepthTexture.hlsl, core Blit.hlsl.
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
        TEXTURE2D(_VerneHistory);
        TEXTURE2D(_VerneScatterTex);

        float IGN(float2 p) { return frac(52.9829189 * frac(dot(p, float2(0.06711056, 0.00583715)))); }

        float PhaseHG(float c, float g)
        {
            float g2 = g * g;
            return (1.0 - g2) / (4.0 * PI * pow(max(1e-3, 1.0 + g2 - 2.0 * g * c), 1.5));
        }

        float3 Daylight(float y) { return exp(-_VerneKd.rgb * max(0.0, _VerneSurface.x - y)); }

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
                float jitter = IGN(i.positionCS.xy + _VerneMarch.z * 5.588238);
                float dt = tMax / max(steps, 1);
                float3 sigT = max(_VerneSigmaT.rgb, 1e-4);
                float3 sigS = sigT * _VerneAlbedo.rgb;
                Light sun = GetMainLight();
                float phaseSun = PhaseHG(dot(rd, sun.direction), _VerneSurface.y) * _VerneSurface.z;
                float3 T = 1.0, S = 0.0;
                [loop] for (int k = 0; k < 16; k++)
                {
                    if (k >= steps) break;
                    float t = (k + jitter) * dt;
                    float3 p = ro + rd * t;
                    float3 day = Daylight(p.y);
                    float3 Lin = _VerneSurfaceAmbient.rgb * day;                         // diffuse sky light, isotropic
                    float sh = MainLightRealtimeShadow(TransformWorldToShadowCoord(p));   // real shafts through the scene
                    Lin += sun.color * day * sh * phaseSun;
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
                // beyond the march: the analytic far field, lit by daylight at that depth
                float3 Tm = exp(-sigT * tMax);
                float3 farP = ro + rd * tMax;
                float3 Lfar = _VerneSurfaceAmbient.rgb * Daylight(farP.y);
                float3 Sfar = Tm * Lfar * _VerneAlbedo.rgb * (1.0 - exp(-sigT * max(0.0, dist - tMax)));
                float3 T = exp(-sigT * dist);
                float3 col = scene.rgb * T + S + Sfar;
                col += (IGN(i.positionCS.xy + _VerneMarch.z * 3.1) - 0.5) * (1.0 / 255.0);   // dither against banding
                return half4(max(col, 0.0), scene.a);
            }
            ENDHLSL
        }
    }
    Fallback Off
}
