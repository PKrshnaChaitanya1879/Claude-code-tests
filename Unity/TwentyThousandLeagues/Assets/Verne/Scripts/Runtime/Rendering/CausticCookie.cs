using UnityEngine;
using UnityEngine.Rendering.Universal;

namespace Verne
{
    /// <summary>
    /// The sun through the swell: a caustic light cookie (Source/tools/caustics_cookie.py, made by refracting
    /// photons through a wave field) drifting slowly across the sea floor, with a second slow sway so the web
    /// breathes rather than slides. Cookies were how Playdead gave simple scenes richer light (INSIDE_NOTES.md).
    /// </summary>
    [RequireComponent(typeof(Light))]
    public class CausticCookie : MonoBehaviour
    {
        public Texture cookie;
        [Tooltip("Metres covered by one tile of the pattern on the floor.")]
        public float size = 7f;
        public Vector2 drift = new Vector2(0.22f, 0.13f);
        public float sway = 0.35f;
        UniversalAdditionalLightData m_Data;

        void Start()
        {
            var l = GetComponent<Light>();
            if (cookie != null) l.cookie = cookie;
            m_Data = GetComponent<UniversalAdditionalLightData>();
            if (m_Data == null) m_Data = gameObject.AddComponent<UniversalAdditionalLightData>();
            m_Data.lightCookieSize = new Vector2(size, size);
        }

        void Update()
        {
            if (m_Data == null) return;
            float t = Time.time;
            m_Data.lightCookieOffset = drift * t + new Vector2(Mathf.Sin(t * 0.37f), Mathf.Cos(t * 0.29f)) * sway;
        }
    }
}
