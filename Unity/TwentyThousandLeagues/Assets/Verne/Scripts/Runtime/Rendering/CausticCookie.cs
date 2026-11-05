using UnityEngine;

namespace Verne
{
    /// <summary>
    /// The sun through the swell: the caustic pattern (Source/tools/caustics_cookie.py, made by refracting photons
    /// through a wave field), drifting slowly with a second slow sway so the web breathes rather than slides.
    /// 5 Nov 2026 (Docs/RESEARCH_underwater.md §1.4): no longer a URP light cookie, which lit every surface equally
    /// sharp at every depth. The water pass (VerneUnderwater) projects it along the sun itself: sharp just under the
    /// surface, blurring and fading with depth, chromatic fringes on Full, and the same web drives the light shafts.
    /// Without the water pass (fallback), it goes back on the light as a cookie.
    /// </summary>
    [RequireComponent(typeof(Light))]
    public class CausticCookie : MonoBehaviour
    {
        public Texture cookie;
        [Tooltip("Metres covered by one tile of the pattern on the floor.")]
        public float size = 7f;
        public Vector2 drift = new Vector2(0.22f, 0.13f);
        public float sway = 0.35f;

        public static Texture Texture { get; private set; }
        public static float TileSize { get; private set; } = 7f;
        public static Vector2 Offset { get; private set; }

        Light m_Light;
        UnityEngine.Rendering.Universal.UniversalAdditionalLightData m_Data;
        bool m_OnLight;

        void OnEnable() { Texture = cookie; TileSize = size; }
        void OnDisable() { if (Texture == cookie) Texture = null; }

        void Start()
        {
            m_Light = GetComponent<Light>();
            m_Data = GetComponent<UnityEngine.Rendering.Universal.UniversalAdditionalLightData>();
            if (m_Data == null) m_Data = gameObject.AddComponent<UnityEngine.Rendering.Universal.UniversalAdditionalLightData>();
            m_Data.lightCookieSize = new Vector2(size, size);
            Texture = cookie; TileSize = size;
        }

        void Update()
        {
            float t = Time.time;
            // offsets in pattern tiles (the shader works in 1/size units)
            Offset = (drift * t + new Vector2(Mathf.Sin(t * 0.37f), Mathf.Cos(t * 0.29f)) * sway) / Mathf.Max(size, 0.5f);
            Texture = cookie; TileSize = size;
            // fallback: the water pass isn't running, so the cookie goes back on the light
            bool want = !VerneUnderwaterFeature.RanRecently && cookie != null;
            if (m_Light != null && want != m_OnLight)
            {
                m_Light.cookie = want ? cookie : null;
                m_OnLight = want;
            }
            if (m_OnLight && m_Data != null) m_Data.lightCookieOffset = Offset * size;
        }
    }
}
