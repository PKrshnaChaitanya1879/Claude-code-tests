// Verne/Flora (M4): the living things of Crespo's forest and the coral kingdom, lit by URP's own PBR
// (main light + its shadows and caustic cookie, the lamps as additional lights, SH ambient, fog), plus:
//  - _Yield > 0: Verne's forest of Crespo is MOTIONLESS ("Not a filament, not a ribbon ... but kept as straight as
//    a rod of iron ... Motionless, yet when bent to one side by the hand, they directly resumed their former
//    position", I.XVI). So the weed does not sway: it leans away from a diver brushing through it and springs
//    straight again as he passes (the newest entries of _VerneVisitors only).
//  - _Sway > 0: a slow swell, kept for the animals (the anemones' crowns). Height above the prop's own origin drives the bend, so the
//    holdfast stays put and the fronds lean and recover; phase from the world position, two frequencies so a
//    forest never moves in lockstep. Verne's laminaries are "rigid" ("the region of perpendicularity", I.XVI):
//    the stems sway little, the fronds of algae and the anemones' crowns more.
//  - _Polyp > 0: the white polyps of the red coral draw back into their cells when a visitor comes near
//    ("the polypi ... retracted", I.XXIII). VerneVisitors keeps a short trail of where the divers have
//    been (_VerneVisitors: xyz + w = age 0..1); the polyps close at once and open again slowly.
// The shader carries no lightmap path (flora is not lightmapped) and opts out of batching, because the sway
// needs each prop's own origin.
Shader "Verne/Flora"
{
    Properties
    {
        _BaseColor ("Base colour", Color) = (0.6, 0.6, 0.6, 1)
        _BaseMap ("Base map", 2D) = "white" {}
        _Metallic ("Metallic", Range(0, 1)) = 0
        _Smoothness ("Smoothness", Range(0, 1)) = 0.3
        _EmissionColor ("Emission", Color) = (0, 0, 0, 0)
        _Sway ("Sway (m at 1 m height)", Float) = 0
        _SwayHeight ("Height of full bend (m)", Float) = 2
        _SwaySpeed ("Swell period scale", Float) = 1
        _Polyp ("Polyp retract depth (m)", Float) = 0
        _Yield ("Bend away from a diver (m at full height)", Float) = 0
        _Wrap ("Wrap lighting (translucent fronds)", Range(0, 1)) = 0.25
    }

    HLSLINCLUDE
    #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

    CBUFFER_START(UnityPerMaterial)
        float4 _BaseMap_ST;
        half4 _BaseColor;
        half4 _EmissionColor;
        half _Metallic, _Smoothness, _Wrap;
        float _Sway, _SwayHeight, _SwaySpeed, _Polyp, _Yield;
    CBUFFER_END
    TEXTURE2D(_BaseMap); SAMPLER(sampler_BaseMap);

    float4 _VerneVisitors[8];      // xyz world position, w age 0 (now) .. 1 (forgotten); unused slots have w = 1
    float4 _VerneCurrent;          // xz direction of the swell's push, z strength multiplier (0 = unset → 1)

    // world-space displacement of one vertex; returns the new world position and how retracted it is (0..1)
    float3 Displace(float3 posWS, float3 normalWS, out float retract)
    {
        retract = 0;
        float3 originWS = TransformObjectToWorld(float3(0, 0, 0));
        if (_Sway > 0)
        {
            float h = max(0.0, posWS.y - originWS.y);
            float bend = pow(saturate(h / max(_SwayHeight, 0.05)), 1.6) * h;
            float ph = dot(originWS.xz, float2(0.37, 0.23));
            float t = _Time.y * _SwaySpeed;
            float2 dir = _VerneCurrent.z > 0 ? normalize(_VerneCurrent.xy) : float2(0.6, 0.8);
            float s = _VerneCurrent.z > 0 ? _VerneCurrent.z : 1.0;
            float a = sin(t * 0.9 + ph) * 0.7 + sin(t * 2.3 + ph * 1.7 + h * 0.8) * 0.3;     // the swell, then the eddies
            float c = sin(t * 1.3 + ph * 2.1 + h) * 0.35;                                      // a sideways wander
            float2 off = (dir * (a + 0.25) + float2(-dir.y, dir.x) * c) * _Sway * s * bend;
            posWS.xz += off;
            posWS.y -= dot(off, off) / max(2.0 * h, 0.1);                                      // keep the frond's length
        }
        if (_Yield > 0)
        {
            float h = max(0.0, posWS.y - originWS.y);
            float bend = pow(saturate(h / max(_SwayHeight, 0.05)), 1.5);
            float2 push = 0;
            [unroll] for (int i = 0; i < 8; i++)
            {
                float2 d = originWS.xz - _VerneVisitors[i].xz;
                float r = length(d);
                float fresh = 1.0 - saturate(_VerneVisitors[i].w * 4.0);          // springs back within ~1 s of the diver leaving
                push += (d / max(r, 1e-3)) * smoothstep(1.3, 0.35, r) * fresh;
            }
            float m = length(push);
            push = m > 1.0 ? push / m : push;
            float2 off = push * _Yield * bend;
            posWS.xz += off;
            posWS.y -= dot(off, off) / max(2.0 * max(h, 0.1), 0.1);
        }
        if (_Polyp > 0)
        {
            float k = 0;
            [unroll] for (int i = 0; i < 8; i++)
            {
                float d = distance(posWS, _VerneVisitors[i].xyz);
                k = max(k, smoothstep(2.2, 0.9, d) * (1.0 - _VerneVisitors[i].w));
            }
            retract = k;
            posWS -= normalWS * _Polyp * k;
        }
        return posWS;
    }
    ENDHLSL

    SubShader
    {
        Tags { "RenderType" = "Opaque" "RenderPipeline" = "UniversalPipeline" "Queue" = "Geometry" "DisableBatching" = "True" }

        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode" = "UniversalForward" }
            Cull Off
            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile _ _ADDITIONAL_LIGHTS_VERTEX _ADDITIONAL_LIGHTS
            #pragma multi_compile_fragment _ _ADDITIONAL_LIGHT_SHADOWS
            #pragma multi_compile_fragment _ _SHADOWS_SOFT _SHADOWS_SOFT_LOW _SHADOWS_SOFT_MEDIUM _SHADOWS_SOFT_HIGH
            #pragma multi_compile_fragment _ _LIGHT_COOKIES
            #pragma multi_compile _ _FORWARD_PLUS
            #pragma multi_compile_fragment _ _SCREEN_SPACE_OCCLUSION
            #pragma multi_compile_fog
            #pragma multi_compile_instancing
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; float2 uv : TEXCOORD0; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float3 positionWS : TEXCOORD0;
                float3 normalWS : TEXCOORD1;
                float2 uv : TEXCOORD2;
                float4 fogRetract : TEXCOORD3;    // x fog factor, y retract
                half3 vertexLight : TEXCOORD4;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            Varyings vert(Attributes v)
            {
                Varyings o = (Varyings)0;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_TRANSFER_INSTANCE_ID(v, o);
                float3 nWS = TransformObjectToWorldNormal(v.normalOS);
                float r;
                float3 pWS = Displace(TransformObjectToWorld(v.positionOS.xyz), nWS, r);
                o.positionWS = pWS;
                o.positionCS = TransformWorldToHClip(pWS);
                o.normalWS = nWS;
                o.uv = TRANSFORM_TEX(v.uv, _BaseMap);
                o.fogRetract = float4(ComputeFogFactor(o.positionCS.z), r, 0, 0);
                o.vertexLight = VertexLighting(pWS, nWS);
                return o;
            }

            half4 frag(Varyings i, bool front : SV_IsFrontFace) : SV_Target
            {
                UNITY_SETUP_INSTANCE_ID(i);
                half4 tex = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, i.uv);
                float3 n = normalize(i.normalWS);
                n = front ? n : -n;                                   // fronds are seen from both sides

                InputData id = (InputData)0;
                id.positionWS = i.positionWS;
                id.positionCS = i.positionCS;
                id.normalWS = n;
                id.viewDirectionWS = GetWorldSpaceNormalizeViewDir(i.positionWS);
                id.shadowCoord = TransformWorldToShadowCoord(i.positionWS);
                id.fogCoord = i.fogRetract.x;
                id.vertexLighting = i.vertexLight;
                id.bakedGI = SampleSH(n);
                id.normalizedScreenSpaceUV = GetNormalizedScreenSpaceUV(i.positionCS);
                id.shadowMask = half4(1, 1, 1, 1);

                SurfaceData sd = (SurfaceData)0;
                sd.albedo = tex.rgb * _BaseColor.rgb * (1.0 - 0.45 * i.fogRetract.y);   // a closed polyp shows its darker cell
                sd.metallic = _Metallic;
                sd.smoothness = _Smoothness;
                sd.normalTS = half3(0, 0, 1);
                sd.occlusion = 1;
                sd.alpha = 1;
                sd.emission = _EmissionColor.rgb;

                half4 col = UniversalFragmentPBR(id, sd);
                // a little light through thin fronds from behind (the sun above the forest roof)
                Light sun = GetMainLight(id.shadowCoord, i.positionWS, id.shadowMask);
                half back = saturate(-dot(n, sun.direction) + _Wrap) / (1.0 + _Wrap);
                col.rgb += sd.albedo * sun.color * sun.shadowAttenuation * back * _Wrap * 0.6;
                col.rgb = MixFog(col.rgb, id.fogCoord);
                return half4(col.rgb, 1);
            }
            ENDHLSL
        }

        Pass
        {
            Name "ShadowCaster"
            Tags { "LightMode" = "ShadowCaster" }
            ZWrite On ZTest LEqual ColorMask 0 Cull Off
            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_instancing
            #pragma multi_compile_vertex _ _CASTING_PUNCTUAL_LIGHT_SHADOW
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Shadows.hlsl"
            float3 _LightDirection;
            float3 _LightPosition;
            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct Varyings { float4 positionCS : SV_POSITION; };
            Varyings vert(Attributes v)
            {
                Varyings o;
                UNITY_SETUP_INSTANCE_ID(v);
                float3 nWS = TransformObjectToWorldNormal(v.normalOS);
                float r;
                float3 pWS = Displace(TransformObjectToWorld(v.positionOS.xyz), nWS, r);
            #if _CASTING_PUNCTUAL_LIGHT_SHADOW
                float3 L = normalize(_LightPosition - pWS);
            #else
                float3 L = _LightDirection;
            #endif
                float4 cs = TransformWorldToHClip(ApplyShadowBias(pWS, nWS, L));
            #if UNITY_REVERSED_Z
                cs.z = min(cs.z, UNITY_NEAR_CLIP_VALUE);
            #else
                cs.z = max(cs.z, UNITY_NEAR_CLIP_VALUE);
            #endif
                o.positionCS = cs;
                return o;
            }
            half4 frag(Varyings i) : SV_Target { return 0; }
            ENDHLSL
        }

        Pass
        {
            Name "DepthOnly"
            Tags { "LightMode" = "DepthOnly" }
            ZWrite On ColorMask R Cull Off
            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_instancing
            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct Varyings { float4 positionCS : SV_POSITION; };
            Varyings vert(Attributes v)
            {
                Varyings o;
                UNITY_SETUP_INSTANCE_ID(v);
                float r;
                o.positionCS = TransformWorldToHClip(Displace(TransformObjectToWorld(v.positionOS.xyz), TransformObjectToWorldNormal(v.normalOS), r));
                return o;
            }
            half frag(Varyings i) : SV_Target { return i.positionCS.z; }
            ENDHLSL
        }

        Pass
        {
            Name "DepthNormals"
            Tags { "LightMode" = "DepthNormals" }
            ZWrite On Cull Off
            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_instancing
            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct Varyings { float4 positionCS : SV_POSITION; float3 normalWS : TEXCOORD0; };
            Varyings vert(Attributes v)
            {
                Varyings o;
                UNITY_SETUP_INSTANCE_ID(v);
                float r;
                o.normalWS = TransformObjectToWorldNormal(v.normalOS);
                o.positionCS = TransformWorldToHClip(Displace(TransformObjectToWorld(v.positionOS.xyz), o.normalWS, r));
                return o;
            }
            half4 frag(Varyings i, bool front : SV_IsFrontFace) : SV_Target
            {
                float3 n = normalize(i.normalWS); n = front ? n : -n;
                return half4(NormalizeNormalPerPixel(n), 0.0);
            }
            ENDHLSL
        }
    }
    FallBack Off
}
