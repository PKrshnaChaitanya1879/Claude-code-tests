// Verne/ShaftCard: the fallback for INSIDE's ray-marched shafts (M3), drawn only when the water pass is not
// running (VerneUnderwaterFeature unsupported or switched off). A vertical additive card, brightest at the
// top, soft at the edges, faded where it meets geometry (soft-particle depth fade), faded when seen edge-on
// and when the eye is inside it, so it never reads as a flat 2D ray.
Shader "Verne/ShaftCard"
{
    Properties
    {
        _Color ("Colour (rgb) × intensity", Color) = (0.5, 0.8, 0.75, 1)
        _Intensity ("Intensity", Float) = 0.35
        _Soft ("Depth fade (m)", Float) = 1.5
    }
    SubShader
    {
        Tags { "RenderType" = "Transparent" "Queue" = "Transparent" "RenderPipeline" = "UniversalPipeline" "IgnoreProjector" = "True" }
        Pass
        {
            Name "Shaft"
            Tags { "LightMode" = "UniversalForward" }
            Blend One One
            ZWrite Off
            Cull Off
            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_instancing
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareDepthTexture.hlsl"

            CBUFFER_START(UnityPerMaterial)
                half4 _Color;
                half _Intensity, _Soft;
            CBUFFER_END

            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; float2 uv : TEXCOORD0; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float2 uv : TEXCOORD0;
                float4 screen : TEXCOORD1;
                float3 positionWS : TEXCOORD2;
                float3 normalWS : TEXCOORD3;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            Varyings vert(Attributes v)
            {
                Varyings o = (Varyings)0;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_TRANSFER_INSTANCE_ID(v, o);
                o.positionWS = TransformObjectToWorld(v.positionOS.xyz);
                o.positionCS = TransformWorldToHClip(o.positionWS);
                o.screen = ComputeScreenPos(o.positionCS);
                o.normalWS = TransformObjectToWorldNormal(v.normalOS);
                o.uv = v.uv;
                return o;
            }

            half4 frag(Varyings i) : SV_Target
            {
                UNITY_SETUP_INSTANCE_ID(i);
                float2 suv = i.screen.xy / max(i.screen.w, 1e-5);
                float sceneEye = LinearEyeDepth(SampleSceneDepth(suv), _ZBufferParams);
                float fragEye = i.screen.w;
                float soft = saturate((sceneEye - fragEye) / max(_Soft, 0.01));
                float3 V = _WorldSpaceCameraPos - i.positionWS;
                float dist = length(V);
                float facing = abs(dot(normalize(i.normalWS), V / max(dist, 1e-4)));
                facing = smoothstep(0.15, 0.6, facing);                     // edge-on cards vanish
                float near = saturate((dist - 1.0) / 4.0);                  // and so does the one you stand in
                float across = sin(i.uv.x * PI);                            // soft edges
                float down = pow(saturate(i.uv.y), 1.5);                    // brightest near the surface (uv.y = 1 at the top)
                float a = across * across * down * soft * facing * near * _Intensity;
                return half4(_Color.rgb * a, 0);
            }
            ENDHLSL
        }
    }
    FallBack Off
}
