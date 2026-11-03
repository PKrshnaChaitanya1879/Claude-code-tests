using System.Collections.Generic;
using UnityEngine;

namespace Verne
{
    /// <summary>
    /// The water a scene is set in (M3). One per underwater scene. It is the per-scene "colour script":
    /// per-channel extinction (red dies first), the in-scattering colour, how light falls off below the
    /// surface (diffuse attenuation Kd), and the hero lights whose beams are ray-marched (Ruhmkorff lamps,
    /// the volcano). VerneUnderwaterFeature reads it every frame; Verne/SeaLit materials share its globals.
    /// Ported from the prototype's src/uw.js and pipeline.js, retuned for INSIDE: luminance falloff, near-black
    /// shadows, colour only where the light is.
    /// </summary>
    [ExecuteAlways]
    public class VerneWater : MonoBehaviour
    {
        public static VerneWater Active { get; private set; }

        [Header("Water (per metre)")]
        [Tooltip("Extinction σt per channel. Coastal water: red dies first.")]
        public Color extinction = new Color(0.30f, 0.07f, 0.06f);
        [Tooltip("Single-scattering albedo per channel (σs / σt): how much of the extinguished light is scattered toward the eye.")]
        public Color scatterAlbedo = new Color(0.55f, 0.75f, 0.8f);
        [Tooltip("Diffuse attenuation of daylight with depth (Kd, per metre), per channel.")]
        public Color kd = new Color(0.35f, 0.07f, 0.05f);
        [Tooltip("World height of the sea surface.")]
        public float surfaceY = 9f;
        [Tooltip("Sky light that reaches the water just below the surface (multiplied by the main light colour if one exists).")]
        public Color surfaceAmbient = new Color(0.18f, 0.32f, 0.34f);
        [Range(0f, 0.95f)] public float forwardScatter = 0.6f;   // Henyey-Greenstein g: shafts glow when looked into
        public float sunShafts = 1f;
        [Tooltip("Light in the water that does not come from the surface (night glow, light scattered many times). From the browser build's uAmbFloor.")]
        public Color ambientFloor = Color.black;
        [Tooltip("A distant glow scattered through the water (the volcano): rgb, and the distance over which it fades.")]
        public Color glowColor = Color.black;
        public Vector3 glowPosition;
        public float glowRange = 120f;

        [Tooltip("How far the main light's shadows reach in this scene (0 = the quality tier's own). God rays are the shadows of things\n" +
                 "in the water: past this distance nothing blocks the light and it falls evenly, like daylight.")]
        public float shadowDistance = 0f;

        [Tooltip("God rays: the main light's beams broken into streaks by a slowly drifting pattern in the light's own plane (the browser\n" +
                 "build's uwShaft, INSIDE's light cookies). Scale = streaks per metre; breakup 0 = even light, 1 = only the streaks.")]
        public float shaftScale = 0.1f;
        [Range(0f, 1f)] public float shaftBreakup = 0f;

        [Header("March")]
        public float maxDistance = 45f;
        [Tooltip("The beams to march through: Ruhmkorff lamps, the volcano. Up to four.")]
        public List<Light> heroLights = new List<Light>();
        [Tooltip("Art direction: multiplies the hero lights in the water (a volcano two miles off must still glow).")]
        public float heroGain = 1f;

        bool m_SceneFog;
        Light m_Sun; Color m_SunBase; Color m_AmbSky, m_AmbEq, m_AmbGround; bool m_Captured;

        static readonly int ID_Sigma = Shader.PropertyToID("_VerneSigma"), ID_Water = Shader.PropertyToID("_VerneWater"),
            ID_Ambient = Shader.PropertyToID("_VerneAmbient"), ID_SunRaw = Shader.PropertyToID("_VerneSunRaw");

        float m_OldShadowDist = -1f;
        void OnEnable()
        {
            Active = this; m_SceneFog = RenderSettings.fog; PushGlobals();
            if (Application.isPlaying && shadowDistance > 0f && UnityEngine.Rendering.GraphicsSettings.currentRenderPipeline is UnityEngine.Rendering.Universal.UniversalRenderPipelineAsset urp)
            { m_OldShadowDist = urp.shadowDistance; urp.shadowDistance = shadowDistance; }
            if (Application.isPlaying)
            {
                m_Sun = RenderSettings.sun; if (m_Sun != null) m_SunBase = m_Sun.color;
                m_AmbSky = RenderSettings.ambientSkyColor; m_AmbEq = RenderSettings.ambientEquatorColor; m_AmbGround = RenderSettings.ambientGroundColor;
                m_Captured = true;
            }
        }
        void OnDisable()
        {
            if (Active == this) Active = null;
            if (m_OldShadowDist >= 0f && UnityEngine.Rendering.GraphicsSettings.currentRenderPipeline is UnityEngine.Rendering.Universal.UniversalRenderPipelineAsset urp)
            { urp.shadowDistance = m_OldShadowDist; m_OldShadowDist = -1f; }
            if (Application.isPlaying)
            {
                RenderSettings.fog = m_SceneFog;
                if (m_Captured) { if (m_Sun != null) m_Sun.color = m_SunBase; RenderSettings.ambientSkyColor = m_AmbSky; RenderSettings.ambientEquatorColor = m_AmbEq; RenderSettings.ambientGroundColor = m_AmbGround; }
            }
        }

        /// <summary>Daylight left at height y, per channel (URP lights surfaces without knowing the depth; we tint its sun and ambient).</summary>
        public Color DaylightAt(float y)
        {
            float d = Mathf.Max(0f, surfaceY - y);
            return new Color(Mathf.Exp(-kd.r * d), Mathf.Exp(-kd.g * d), Mathf.Exp(-kd.b * d));
        }
        void Update()
        {
            if (Active == null) Active = this;
            PushGlobals();
            // the built-in fog is only the fallback: off while the water pass runs, back on if it cannot
            if (Application.isPlaying)
            {
                RenderSettings.fog = m_SceneFog && !VerneUnderwaterFeature.RanRecently;
                // surfaces get the light that is left at the eye's depth: red first, then green (cheap, and matches the march)
                var cam = Camera.main;
                if (m_Captured && cam != null)
                {
                    var day = DaylightAt(cam.transform.position.y - 1f);
                    if (m_Sun != null)
                    {
                        m_Sun.color = m_SunBase * day;
                        // the march applies daylight per sample itself: give it the untinted sun
                        Shader.SetGlobalVector(ID_SunRaw, new Vector4(m_SunBase.linear.r * m_Sun.intensity, m_SunBase.linear.g * m_Sun.intensity, m_SunBase.linear.b * m_Sun.intensity, 1f));
                    }
                    else Shader.SetGlobalVector(ID_SunRaw, Vector4.zero);
                    RenderSettings.ambientSkyColor = m_AmbSky * day; RenderSettings.ambientEquatorColor = m_AmbEq * day; RenderSettings.ambientGroundColor = m_AmbGround * day;
                }
            }
        }

        /// <summary>The far-field colour the eye sees at depth y (in-scattered daylight), for SeaLit and the composite.</summary>
        public Color InScatterAt(float y)
        {
            float d = Mathf.Max(0f, surfaceY - y);
            var c = new Color(surfaceAmbient.r * Mathf.Exp(-kd.r * d), surfaceAmbient.g * Mathf.Exp(-kd.g * d), surfaceAmbient.b * Mathf.Exp(-kd.b * d));
            c += ambientFloor;
            return new Color(c.r * scatterAlbedo.r, c.g * scatterAlbedo.g, c.b * scatterAlbedo.b);
        }

        void PushGlobals()
        {
            var cam = Camera.main;
            float y = cam != null ? cam.transform.position.y : transform.position.y;
            Shader.SetGlobalVector(ID_Sigma, (Vector4)extinction);
            Shader.SetGlobalVector(ID_Water, (Vector4)InScatterAt(y));
            Shader.SetGlobalVector(ID_Ambient, (Vector4)(InScatterAt(y) * 0.5f));
        }
    }
}
