using UnityEngine;
using UnityEngine.Rendering.Universal;

namespace Verne
{
    /// <summary>
    /// INSIDE's torch shadows, after Playdead's blog: "the shadows at the boy's feet are decals that track the
    /// torch, rotate around the feet and scale with the torch's height" (point-light shadows were too expensive).
    /// One URP decal per diver, projecting a soft dark blob straight down. With no lamp near, it is a round
    /// contact shadow under the feet, nudged away from the sun. Near a lamp (the hero lights of VerneWater, i.e.
    /// the Ruhmkorff lamps and the volcano), it swings away from the lamp and stretches as the lamp gets lower
    /// and closer, fading in with the lamp's strength at this distance. A diver's own lamp is skipped.
    /// </summary>
    public class LampShadow : MonoBehaviour
    {
        public Material material;               // the AO blob decal material (bootstrap: M_DecalAO)
        public float radius = 0.55f;            // round contact shadow under the feet
        public float bodyHeight = 1.8f;
        public float maxStretch = 3.2f;
        DecalProjector m_Decal;
        Light m_Own;

        void Start()
        {
            if (material == null) { enabled = false; return; }
            var go = new GameObject("Lamp shadow (decal)");
            go.transform.SetParent(transform, false);
            m_Decal = go.AddComponent<DecalProjector>();
            m_Decal.material = material;
            m_Decal.pivot = Vector3.zero;
            m_Decal.drawDistance = 40f;
            m_Own = GetComponentInChildren<Light>(true);
        }

        void LateUpdate()
        {
            if (m_Decal == null) return;
            Vector3 feet = transform.position;
            Vector2 away = Vector2.zero; float stretch = 0f, strength = 0f;
            var w = VerneWater.Active;
            if (w != null)
            {
                foreach (var l in w.heroLights)
                {
                    if (l == null || !l.isActiveAndEnabled || l == m_Own || l.transform.IsChildOf(transform)) continue;
                    Vector3 d = feet - l.transform.position;
                    float dist = d.magnitude;
                    if (dist > l.range) continue;
                    float s = Mathf.Clamp01(1f - dist / l.range);
                    if (l.type == LightType.Spot)
                        s *= Mathf.Clamp01(Mathf.InverseLerp(Mathf.Cos(l.spotAngle * 0.5f * Mathf.Deg2Rad), 1f, Vector3.Dot(l.transform.forward, d / Mathf.Max(dist, 1e-3f))) * 3f);
                    if (s <= strength) continue;
                    strength = s;
                    var flat = new Vector2(d.x, d.z);
                    float h = Mathf.Max(0.25f, l.transform.position.y - feet.y);
                    away = flat.sqrMagnitude > 1e-4f ? flat.normalized : Vector2.zero;
                    // the shadow of a body of height H under a lamp at height h and horizontal distance r ends at r·H/(h−H) (clamped)
                    stretch = Mathf.Min(maxStretch, h > bodyHeight + 0.1f ? flat.magnitude * bodyHeight / (h - bodyHeight) : maxStretch);
                }
            }
            if (strength <= 0.01f)
            {
                var sun = RenderSettings.sun;
                if (sun != null && sun.isActiveAndEnabled) { var f = sun.transform.forward; away = new Vector2(f.x, f.z) * 0.35f; }
                stretch = 0f;
            }
            float len = radius * 2f + stretch * strength;
            Vector3 dir3 = new Vector3(away.x, 0f, away.y);
            Vector3 centre = feet + dir3 * (len * 0.5f - radius) + Vector3.up * 0.2f;
            float yaw = away.sqrMagnitude > 1e-4f ? Mathf.Atan2(away.x, away.y) * Mathf.Rad2Deg : transform.eulerAngles.y;
            m_Decal.transform.SetPositionAndRotation(centre, Quaternion.Euler(90f, yaw, 0f));   // projects along its +Z: straight down
            m_Decal.size = new Vector3(radius * 2f, len, 1.6f);
            m_Decal.fadeFactor = Mathf.Lerp(0.75f, 0.95f, strength) / (1f + stretch * strength * 0.25f);   // a long shadow is a fainter one
        }
    }
}
