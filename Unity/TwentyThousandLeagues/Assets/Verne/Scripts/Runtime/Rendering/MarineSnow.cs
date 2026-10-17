using UnityEngine;

namespace Verne
{
    /// <summary>
    /// Marine snow: the motes that make light visible underwater ("you can see the dust and other particles",
    /// GUM). A box of slow, sinking particles that follows the eye; each mote is brightened by the hero lamps
    /// and the sun's daylight at its depth, so the dust shows where the light is and vanishes in the dark
    /// (INSIDE). One draw call; 350 particles (180 on Light quality).
    /// </summary>
    public class MarineSnow : MonoBehaviour
    {
        public Material material;
        public Vector3 box = new Vector3(14f, 8f, 14f);
        ParticleSystem m_PS;
        ParticleSystem.Particle[] m_P;
        Transform m_Eye;

        void Start()
        {
            int max = QualitySettings.GetQualityLevel() <= 0 ? 180 : 350;
            m_PS = gameObject.AddComponent<ParticleSystem>();
            m_PS.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            var main = m_PS.main;
            main.loop = true; main.playOnAwake = false; main.maxParticles = max;
            main.startLifetime = 1e6f; main.startSpeed = 0f; main.startSize = new ParticleSystem.MinMaxCurve(0.012f, 0.035f);
            main.simulationSpace = ParticleSystemSimulationSpace.World;
            var em = m_PS.emission; em.enabled = false;
            var sh = m_PS.shape; sh.enabled = false;
            var r = GetComponent<ParticleSystemRenderer>();
            r.sharedMaterial = material; r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; r.receiveShadows = false;
            r.renderMode = ParticleSystemRenderMode.Billboard;
            m_PS.Emit(max);
            m_P = new ParticleSystem.Particle[max];
            int n = m_PS.GetParticles(m_P);
            var c = Eye();
            for (int i = 0; i < n; i++)
                m_P[i].position = c + Vector3.Scale(new Vector3(Random.value - 0.5f, Random.value - 0.5f, Random.value - 0.5f), box);
            m_PS.SetParticles(m_P, n);
            m_PS.Play();
        }

        Vector3 Eye()
        {
            if (m_Eye == null && Camera.main != null) m_Eye = Camera.main.transform;
            return m_Eye != null ? m_Eye.position : transform.position;
        }

        void LateUpdate()
        {
            if (m_PS == null) return;
            int n = m_PS.GetParticles(m_P);
            var c = Eye();
            var w = VerneWater.Active;
            float t = Time.time, dt = Time.deltaTime;
            Vector3 h = box * 0.5f;
            for (int i = 0; i < n; i++)
            {
                var p = m_P[i].position;
                // slow sinking and a lazy drift with the current
                p += new Vector3(Mathf.Sin(t * 0.21f + i) * 0.03f, -0.025f - (i % 7) * 0.003f, Mathf.Cos(t * 0.17f + i * 1.3f) * 0.03f) * dt;
                // wrap round the eye so the box follows without popping
                Vector3 d = p - c;
                if (d.x > h.x) p.x -= box.x; else if (d.x < -h.x) p.x += box.x;
                if (d.y > h.y) p.y -= box.y; else if (d.y < -h.y) p.y += box.y;
                if (d.z > h.z) p.z -= box.z; else if (d.z < -h.z) p.z += box.z;
                m_P[i].position = p;
                // brightness = the light at this mote: daylight left at its depth, plus the hero lamps' beams
                float lum = 0.05f;
                if (w != null)
                {
                    var day = w.DaylightAt(p.y);
                    lum = 0.25f * (day.g + day.b) * (w.surfaceAmbient.g * 4f);
                    foreach (var l in w.heroLights)
                    {
                        if (l == null || !l.isActiveAndEnabled) continue;
                        Vector3 v = p - l.transform.position;
                        float dist = v.magnitude;
                        if (dist > l.range) continue;
                        float cone = 1f;
                        if (l.type == LightType.Spot) cone = Mathf.Clamp01((Vector3.Dot(v / Mathf.Max(dist, 1e-3f), l.transform.forward) - Mathf.Cos(l.spotAngle * 0.5f * Mathf.Deg2Rad)) * 8f);
                        lum += cone * l.intensity * 0.6f / (1f + dist * dist) * (1f - dist / l.range);
                    }
                }
                float a = Mathf.Clamp01(lum);
                m_P[i].startColor = new Color(0.85f, 0.92f, 0.95f, a);
            }
            m_PS.SetParticles(m_P, n);
        }
    }
}
