// Verne/SeaLit: things seen through water (the saloon window's exterior, and the first pass of the
// M3 water model). Physically flavoured, cheap, no URP light loop:
//  - one point "lamp" (the Nautilus' own light) attenuated along its path by per-channel extinction
//    sigma (red dies first: Jerlov-like coastal water), plus a depth-ambient;
//  - the result is seen through exp(-sigma * viewDistance) with in-scattered water colour, so colour
//    is vibrant where the light is and things fall away to dark silhouettes in luminous fog (INSIDE).
//  - _Wiggle > 0: a swimming tail for fish (vertex sway behind the head, phase from the instance position).
//  - _Backdrop > 0: a far shell drawing only the in-scattered gradient (brighter toward the lamp and up).
// Globals (set by SeaWindowView / later by the water controller): _VerneSigma, _VerneWater, _VerneAmbient,
// _VerneLampPos (xyz, w = range), _VerneLampColor.
Shader "Verne/SeaLit"
{
    Properties
    {
        _BaseColor ("Base colour", Color) = (0.6, 0.6, 0.6, 1)
        _BaseMap ("Base map", 2D) = "white" {}
        _Emission ("Emission", Color) = (0, 0, 0, 0)
        _Sheen ("Sheen (silver flanks)", Range(0, 1)) = 0
        _Wiggle ("Tail sway (m)", Float) = 0
        _WiggleSpeed ("Tail beat (Hz)", Float) = 2
        _Backdrop ("Backdrop shell", Float) = 0
        _Pulse ("Pulse (medusae)", Float) = 0
    }
    SubShader
    {
        Tags { "RenderType" = "Opaque" "RenderPipeline" = "UniversalPipeline" "Queue" = "Geometry" }
        Pass
        {
            Name "ForwardSea"
            Tags { "LightMode" = "UniversalForward" }
            Cull Back
            ZWrite On
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_instancing
            #pragma multi_compile_fog
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            TEXTURE2D(_BaseMap); SAMPLER(sampler_BaseMap);
            CBUFFER_START(UnityPerMaterial)
                float4 _BaseMap_ST;
                half4 _BaseColor;
                half4 _Emission;
                half _Sheen;
                float _Wiggle, _WiggleSpeed, _Backdrop, _Pulse;
            CBUFFER_END

            float4 _VerneSigma;      // extinction per metre, rgb
            float4 _VerneWater;      // in-scattered water colour, rgb
            float4 _VerneAmbient;    // depth ambient, rgb
            float4 _VerneLampPos;    // xyz, w = range
            float4 _VerneLampColor;  // rgb * intensity
            float4 _VerneLampMirror; // x > 0.5: a strip light along both window sides (x mirrored about w, z clamped to y..z)

            struct Attributes
            {
                float4 positionOS : POSITION;
                float3 normalOS : NORMAL;
                float2 uv : TEXCOORD0;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };
            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float3 positionWS : TEXCOORD0;
                float3 normalWS : TEXCOORD1;
                float2 uv : TEXCOORD2;
                float pulse : TEXCOORD3;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            Varyings vert(Attributes v)
            {
                Varyings o = (Varyings)0;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_TRANSFER_INSTANCE_ID(v, o);
                float3 p = v.positionOS.xyz;
                float3 originWS = TransformObjectToWorld(float3(0, 0, 0));
                float phase = dot(originWS, float3(1.7, 3.1, 2.3));
                if (_Wiggle > 0)
                {
                    // the head (+z) is still, the tail (-z) beats side to side
                    float behind = saturate(-p.z * 2.0 + 0.2);
                    p.x += sin(_Time.y * _WiggleSpeed * 6.2832 + phase + p.z * 5.0) * _Wiggle * behind * behind;
                }
                float pulse = 0;
                if (_Pulse > 0)
                {
                    // medusae: the bell contracts and relaxes
                    pulse = 0.5 + 0.5 * sin(_Time.y * _Pulse + phase);
                    float k = 1.0 - 0.18 * pulse * saturate(p.y * 2.0 + 0.5);
                    p.xz *= k; p.y *= 1.0 + 0.1 * pulse;
                }
                o.positionWS = TransformObjectToWorld(p);
                o.positionCS = TransformWorldToHClip(o.positionWS);
                o.normalWS = TransformObjectToWorldNormal(v.normalOS);
                o.uv = TRANSFORM_TEX(v.uv, _BaseMap);
                o.pulse = pulse;
                return o;
            }

            half4 frag(Varyings i) : SV_Target
            {
                UNITY_SETUP_INSTANCE_ID(i);
                float3 sigma = max(_VerneSigma.rgb, 0.001);
                float3 V = _WorldSpaceCameraPos - i.positionWS;
                float viewDist = length(V);
                float3 Vn = V / max(viewDist, 1e-4);
                float3 lampPos = _VerneLampPos.xyz;
                if (_VerneLampMirror.x > 0.5)
                {
                    lampPos.x = _VerneLampMirror.w + abs(lampPos.x - _VerneLampMirror.w) * (i.positionWS.x >= _VerneLampMirror.w ? 1.0 : -1.0);
                    lampPos.z = clamp(i.positionWS.z, _VerneLampMirror.y, _VerneLampMirror.z);
                }
                float3 toLamp = lampPos - i.positionWS;
                float lampDist = length(toLamp);
                float3 L = toLamp / max(lampDist, 1e-4);

                if (_Backdrop > 0.5)
                {
                    // looking out into open water: brighter toward the lamp and toward the surface, black below
                    float3 dir = -Vn;
                    float towardLamp = saturate(dot(dir, normalize(lampPos - _WorldSpaceCameraPos)) * 0.5 + 0.5);
                    float up = saturate(dir.y * 0.5 + 0.5);
                    float3 col = _VerneWater.rgb * (0.12 + 1.6 * up * up * up + 0.9 * towardLamp * towardLamp * towardLamp * towardLamp);
                    return half4(col, 1);
                }

                half4 tex = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, i.uv);
                half3 albedo = tex.rgb * _BaseColor.rgb;
                float3 N = normalize(i.normalWS);
                float wrap = saturate((dot(N, L) + 0.35) / 1.35);
                float range = max(_VerneLampPos.w, 0.01);
                float fall = 1.0 / (1.0 + (lampDist * lampDist) / (range * range) * 4.0);
                float3 lampAtSurface = _VerneLampColor.rgb * exp(-sigma * lampDist) * fall;
                // silver flanks of fish flash when they turn into the light
                float3 H = normalize(L + Vn);
                float spec = pow(saturate(dot(N, H)), 24.0) * _Sheen * 1.5;
                float3 lit = albedo * (lampAtSurface * wrap + _VerneAmbient.rgb * (0.6 + 0.4 * N.y)) + lampAtSurface * spec;
                lit += _Emission.rgb * (1.0 + i.pulse);
                float3 T = exp(-sigma * viewDist);
                float3 col = lit * T + _VerneWater.rgb * (1.0 - T);
                return half4(col, 1);
            }
            ENDHLSL
        }
    }
    FallBack Off
}
