using UnityEngine;

namespace Verne
{
    /// <summary>
    /// Playdead's hand-placed bounce light, automated for a moving lamp: where a Ruhmkorff beam lands, the lit sand
    /// or coral throws a little of its colour back up onto the diver and the stems around it ("there is no global
    /// illumination ... bounce light, specular, rim, AO ... all placed by hand"). One small unshadowed point light
    /// per lamp, at the beam's footprint, tinted by what it lands on, faded with distance. Off on "Light" quality.
    /// </summary>
    [RequireComponent(typeof(Light))]
    public class LampBounce : MonoBehaviour
    {
        public float gain = 0.10f;
        public float radius = 3.0f;
        Light m_Lamp, m_Bounce;
        static readonly Color Sand = new Color(0.95f, 0.85f, 0.65f), Coral = new Color(0.95f, 0.45f, 0.38f), Stone = new Color(0.6f, 0.58f, 0.55f);

        void Start()
        {
            m_Lamp = GetComponent<Light>();
            var go = new GameObject("Bounce (from the beam's footprint)");
            go.transform.SetParent(transform, false);
            m_Bounce = go.AddComponent<Light>();
            m_Bounce.type = LightType.Point; m_Bounce.shadows = LightShadows.None; m_Bounce.range = radius;
            m_Bounce.renderMode = LightRenderMode.Auto;
            m_Bounce.enabled = false;
        }

        void LateUpdate()
        {
            if (m_Bounce == null) return;
            bool on = m_Lamp != null && m_Lamp.isActiveAndEnabled && QualitySettings.GetQualityLevel() > 0;
            if (on && Physics.Raycast(transform.position, transform.forward, out var hit, m_Lamp.range * 0.8f, ~((1 << 2) | (1 << 8)), QueryTriggerInteraction.Ignore))
            {
                Color tint = Stone;
                var s = hit.collider.GetComponentInParent<Surface>();
                string n = hit.collider.name;
                if (s != null && s.kind == "sand") tint = Sand;
                else if (n.Contains("coral") || n.Contains("collider")) tint = Coral;   // flora colliders are named "collider" under their prop
                float fall = 1f / (1f + hit.distance * hit.distance * 0.08f);
                m_Bounce.transform.position = hit.point + hit.normal * 0.5f;
                m_Bounce.color = m_Lamp.color * tint;
                m_Bounce.intensity = m_Lamp.intensity * gain * fall;
                m_Bounce.enabled = m_Bounce.intensity > 0.02f;
            }
            else m_Bounce.enabled = false;
        }
    }
}
