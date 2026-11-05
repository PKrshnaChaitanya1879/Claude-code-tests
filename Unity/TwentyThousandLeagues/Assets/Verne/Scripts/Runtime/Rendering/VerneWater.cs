using System.Collections.Generic;
using UnityEngine;
#if VERNE_INPUT_SYSTEM
using UnityEngine.InputSystem;
#endif

namespace Verne
{
    public enum WaterOpticsMode { Artistic = 0, Physical = 1 }

    /// <summary>
    /// The water a scene is set in (M3). One per underwater scene. It is the per-scene "colour script":
    /// per-channel extinction (red dies first), the in-scattering colour, how light falls off below the
    /// surface (diffuse attenuation Kd), and the hero lights whose beams are ray-marched (Ruhmkorff lamps,
    /// the volcano). VerneUnderwaterFeature reads it every frame; Verne/SeaLit materials share its globals.
    ///
    /// 5 Nov 2026 (Docs/RESEARCH_underwater.md): two ways to set the water.
    ///  - Physical: from what is in it (chlorophyll, CDOM, silt) through WaterOptics, so absorption, scattering,
    ///    albedo and Kd all agree with real sea water: red is absorbed within ~3 m, green and blue scatter.
    ///  - Artistic: the hand-tuned colours (the look GUM approved in tour 13), kept for comparison.
    /// F7 in play flips between them. Everything reads the effective values (Extinction, Albedo, Kd).
    /// Hero lamps' surface light is filtered by the water over their own reach (red dies with distance from the
    /// lamp too); the march gets their untinted colour (BaseColor) because it absorbs per sample itself.
    /// </summary>
    [ExecuteAlways]
    public class VerneWater : MonoBehaviour
    {
        public static VerneWater Active { get; private set; }

        [Header("Optics")]
        public WaterOpticsMode optics = WaterOpticsMode.Artistic;
        [Tooltip("Physical: chlorophyll (mg/m³). 0.02 clearest ocean, 0.1–0.3 clear, 1+ green coastal.")]
        public float chlorophyll = 0.08f;
        [Tooltip("Physical: dissolved organic matter, absorption at 440 nm (1/m). 0.005 ocean, 0.03 coastal.")]
        public float cdom = 0.01f;
        [Tooltip("Physical: mineral silt scattering (1/m), nearly grey. 0 clear, 0.05 hazy.")]
        public float silt = 0.0f;
        [Tooltip("Physical: extra silt in the bottom metres (stirred-up floor), fading upward over siltLayer m.")]
        public float floorSilt = 0.0f;
        public float siltLayer = 4f;
        [Tooltip("Physical: sky light gain. Physical water scatters less green than the old tuned albedo, so the same sky reads darker; this restores the overall level without changing the colour.")]
        public float physicalAmbientGain = 1f;
        [Tooltip("Physical: the eye's white balance. The water colours the light; a diver's eye adapts to it (as an underwater photographer sets white balance). 0 = none, 1 = fully neutral.")]
        [Range(0f, 1f)] public float eyeAdaptation = 0.7f;

        [Header("Water, artistic (per metre)")]
        [Tooltip("Extinction σt per channel. Coastal water: red dies first.")]
        public Color extinction = new Color(0.30f, 0.07f, 0.06f);
        [Tooltip("Single-scattering albedo per channel (σs / σt): how much of the extinguished light is scattered toward the eye.")]
        public Color scatterAlbedo = new Color(0.55f, 0.75f, 0.8f);
        [Tooltip("Diffuse attenuation of daylight with depth (Kd, per metre), per channel.")]
        public Color kd = new Color(0.35f, 0.07f, 0.05f);

        [Header("Light")]
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
        [Tooltip("Caustic web on the floor, added by the water pass (sharp under the surface, blurring with depth).")]
        public float caustics = 1f;
        [Tooltip("Depth (m below the surface) by which the caustics have faded out.")]
        public float causticDepth = 22f;
        [Tooltip("Multiple scattering: soft light in shadowed water, weighted by albedo² (0 = single scattering only).")]
        public float multiScatter = 0.6f;
        [Tooltip("Filter the hero lamps' surface light by the water over a third of their range (red dies with distance from the lamp).")]
        public bool filterLampLight = true;

        [Tooltip("How far the main light's shadows reach in this scene (0 = the quality tier's own). God rays are the shadows of things\n" +
                 "in the water: past this distance nothing blocks the light and it falls evenly, like daylight.")]
        public float shadowDistance = 0f;

        [Header("March")]
        [Tooltip("How the samples spread along the eye ray: 1 = evenly (distant rays, the volcano), 2 = packed near the eye (the kelp).")]
        [Range(1f, 2.5f)] public float sampleSpread = 2f;
        public float maxDistance = 45f;
        [Tooltip("The beams to march through: Ruhmkorff lamps, the volcano. Up to four.")]
        public List<Light> heroLights = new List<Light>();
        [Tooltip("Art direction: multiplies the hero lights in the water (a volcano two miles off must still glow).")]
        public float heroGain = 1f;

        // ---- effective optics (what everything reads) ----
        public Color Extinction { get; private set; }
        public Color Albedo { get; private set; }
        public Color Kd { get; private set; }
        public float VisibilityGreen { get; private set; }
        /// <summary>Sky light just under the surface, as the active optics mode uses it.</summary>
        public Color SurfaceAmbient
        {
            get
            {
                if (optics != WaterOpticsMode.Physical) return surfaceAmbient;
                // physical: the sky is white light; the water itself does the colouring (absorption, Kd, albedo)
                float l = (surfaceAmbient.r * 0.2126f + surfaceAmbient.g * 0.7152f + surfaceAmbient.b * 0.0722f) * physicalAmbientGain;
                return new Color(l, l, l, 1f);
            }
        }

        /// <summary>Divisor for the eye's chromatic adaptation (physical mode): the far-water colour at the eye, normalised, part-way to grey.</summary>
        public Color WhiteBalance(float eyeY)
        {
            if (optics != WaterOpticsMode.Physical || eyeAdaptation <= 0f) return Color.white;
            var w = InScatterAt(eyeY);
            float m = (w.r + w.g + w.b) / 3f;
            if (m < 1e-5f) return Color.white;
            return new Color(1f + (w.r / m - 1f) * eyeAdaptation, 1f + (w.g / m - 1f) * eyeAdaptation, 1f + (w.b / m - 1f) * eyeAdaptation, 1f);
        }
        WaterOpticsMode m_LastMode = (WaterOpticsMode)(-1);
        float m_LastChl = -1, m_LastCdom = -1, m_LastSilt = -1;
        Color m_LastExt, m_LastAlb, m_LastKd;

        bool m_SceneFog;
        Light m_Sun; Color m_SunBase; Color m_AmbSky, m_AmbEq, m_AmbGround; bool m_Captured;
        readonly Dictionary<Light, Color> m_LampBase = new Dictionary<Light, Color>();

        static readonly int ID_Sigma = Shader.PropertyToID("_VerneSigma"), ID_Water = Shader.PropertyToID("_VerneWater"),
            ID_Ambient = Shader.PropertyToID("_VerneAmbient"), ID_SunRaw = Shader.PropertyToID("_VerneSunRaw"),
            ID_SurfaceY = Shader.PropertyToID("_VerneSurfaceY");

        float m_OldShadowDist = -1f;

        /// <summary>Recompute the effective optics if anything changed (cheap; runs every frame).</summary>
        public void RefreshOptics()
        {
            if (optics == m_LastMode && chlorophyll == m_LastChl && cdom == m_LastCdom && silt == m_LastSilt &&
                extinction == m_LastExt && scatterAlbedo == m_LastAlb && kd == m_LastKd) return;
            m_LastMode = optics; m_LastChl = chlorophyll; m_LastCdom = cdom; m_LastSilt = silt;
            m_LastExt = extinction; m_LastAlb = scatterAlbedo; m_LastKd = kd;
            if (optics == WaterOpticsMode.Physical)
            {
                var r = WaterOptics.Compute(chlorophyll, cdom, silt);
                Extinction = r.extinction; Albedo = r.albedo; Kd = r.kd; VisibilityGreen = r.visibilityGreen;
            }
            else
            {
                Extinction = extinction; Albedo = scatterAlbedo; Kd = kd;
                VisibilityGreen = 4.8f / Mathf.Max(extinction.g, 1e-4f);
            }
        }

        void OnEnable()
        {
            Active = this; m_SceneFog = RenderSettings.fog; RefreshOptics(); PushGlobals();
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
                RestoreLamps();
            }
            Shader.SetGlobalVector(ID_SurfaceY, Vector4.zero);
        }

        /// <summary>Daylight left at height y, per channel (URP lights surfaces without knowing the depth; we tint its sun and ambient).</summary>
        public Color DaylightAt(float y)
        {
            float d = Mathf.Max(0f, surfaceY - y);
            var k = Kd;
            return new Color(Mathf.Exp(-k.r * d), Mathf.Exp(-k.g * d), Mathf.Exp(-k.b * d));
        }

        /// <summary>A hero light's own colour × intensity before the water filter (the march absorbs per sample itself).</summary>
        public Color BaseColor(Light l)
        {
            if (l == null) return Color.black;
            return m_LampBase.TryGetValue(l, out var c) ? c : l.color;
        }

        void Update()
        {
            if (Active == null) Active = this;
            RefreshOptics();
            PushGlobals();
            if (!Application.isPlaying) return;
#if VERNE_INPUT_SYSTEM
            var kb = Keyboard.current;
            if (kb != null && kb.f7Key.wasPressedThisFrame)
            {
                optics = optics == WaterOpticsMode.Physical ? WaterOpticsMode.Artistic : WaterOpticsMode.Physical;
                RefreshOptics();
                Hud.Toast(optics == WaterOpticsMode.Physical
                    ? $"Water: physical optics (red gone in ~{1f / Mathf.Max(Extinction.r, 1e-3f):0.0} m, black things vanish at ~{VisibilityGreen:0} m)"
                    : "Water: artistic (the tuned look from tour 13)", 3f);
            }
#endif
            // the built-in fog is only the fallback: off while the water pass runs, back on if it cannot
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
            FilterLamps();
        }

        /// <summary>
        /// Lamps under water: a beam's light reaches the floor through water too, so its red is absorbed with distance
        /// from the lamp. URP can't do that per pixel for its own lights, so each hero lamp's colour is filtered by the
        /// water over a third of its range (where most of what it lights lies). Volcano-size lights (range ≥ 60 m) keep
        /// Verne's art direction instead ("a reddish spot ... two miles", II.IX).
        /// </summary>
        void FilterLamps()
        {
            var ext = Extinction;
            for (int i = 0; i < heroLights.Count; i++)
            {
                var l = heroLights[i];
                if (l == null) continue;
                if (!m_LampBase.ContainsKey(l)) m_LampBase[l] = l.color;
                var baseC = m_LampBase[l];
                if (!filterLampLight || l.type == LightType.Directional || l.range >= 60f) { l.color = baseC; continue; }
                var t = WaterOptics.Transmit(ext, l.range / 3f);
                float norm = Mathf.Max(t.r, Mathf.Max(t.g, t.b));                // keep its brightness; change its colour
                l.color = new Color(baseC.r * t.r / norm, baseC.g * t.g / norm, baseC.b * t.b / norm, baseC.a);
            }
            // a lamp taken off the list (switched off) gets its own colour back
            if (m_LampBase.Count > heroLights.Count)
            {
                s_Drop.Clear();
                foreach (var kv in m_LampBase) if (kv.Key == null || !heroLights.Contains(kv.Key)) s_Drop.Add(kv.Key);
                foreach (var l in s_Drop) { if (l != null) l.color = m_LampBase[l]; m_LampBase.Remove(l); }
            }
        }
        static readonly List<Light> s_Drop = new List<Light>();

        void RestoreLamps()
        {
            foreach (var kv in m_LampBase) if (kv.Key != null) kv.Key.color = kv.Value;
            m_LampBase.Clear();
        }

        /// <summary>The far-field colour the eye sees at depth y (in-scattered daylight), for SeaLit and the composite.</summary>
        public Color InScatterAt(float y)
        {
            var c = DaylightAt(y);
            var sa = SurfaceAmbient;
            c = new Color(sa.r * c.r, sa.g * c.g, sa.b * c.b);
            c += ambientFloor;
            var a = Albedo;
            return new Color(c.r * a.r, c.g * a.g, c.b * a.b);
        }

        void PushGlobals()
        {
            var cam = Camera.main;
            float y = cam != null ? cam.transform.position.y : transform.position.y;
            Shader.SetGlobalVector(ID_Sigma, (Vector4)Extinction);
            Shader.SetGlobalVector(ID_Water, (Vector4)InScatterAt(y));
            Shader.SetGlobalVector(ID_Ambient, (Vector4)(InScatterAt(y) * 0.5f));
            Shader.SetGlobalVector(ID_SurfaceY, new Vector4(surfaceY, 1f, 0f, 0f));   // y = 1: set (Flora's surge falls off with depth below it)
        }
    }
}
