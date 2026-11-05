using UnityEngine;

namespace Verne
{
    /// <summary>
    /// Marine snow: the motes that make light visible underwater ("you can see the dust and other particles",
    /// GUM). A box of particles that follows the eye; each mote is coloured by the light that actually reaches it
    /// (daylight left at its depth, per channel, plus the hero lamps through the water between lamp and mote), so the
    /// dust shows where the light is and vanishes in the dark (INSIDE), warm close to a lamp and blue-green further off.
    ///
    /// Motion (Docs/RESEARCH_underwater.md §3.2): real marine snow sinks at ~5–200 m/day, i.e. ~0.1–2 mm/s: on screen it is
    /// practically suspended. What it does visibly is drift with the current (a few cm/s), sway with the wave surge in
    /// shallow water (period ~10 s, fading with depth), and swirl in the wake of anything moving through it (the visitor,
    /// the divers). Bigger aggregates are fluffier and sink slower. One draw call; 350 motes (180 on Light), 600 on Full.
    /// </summary>
    public class MarineSnow : MonoBehaviour
    {
        public Material material;
        public Vector3 box = new Vector3(14f, 8f, 14f);
        [Tooltip("Slow horizontal current (m/s).")]
        public Vector3 current = new Vector3(0.03f, 0f, 0.018f);
        [Tooltip("Wave surge amplitude just under the surface (m/s); fades with depth.")]
        public float surge = 0.05f;
        public float surgePeriod = 10f;
        ParticleSystem m_PS;
        ParticleSystem.Particle[] m_P;
        Vector3[] m_Vel;
        Transform m_Eye;
        Vector3 m_LastEye;

        void Start()
        {
            int q = QualitySettings.GetQualityLevel();
            int max = q <= 0 ? 180 : (q == 1 ? 350 : 600);
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
            m_Vel = new Vector3[max];
            int n = m_PS.GetParticles(m_P);
            var c = Eye();
            m_LastEye = c;
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

        /// <summary>The light (rgb, linear-ish 0..1+) that reaches a point in the water: daylight at its depth and the hero lamps through the water.</summary>
        public static Color LightAt(VerneWater w, Vector3 p, Color ext)
        {
            if (w == null) return new Color(0.05f, 0.05f, 0.05f);
            var day = w.DaylightAt(p.y);
            var sa = w.SurfaceAmbient;
            Color c = new Color(day.r * sa.r, day.g * sa.g, day.b * sa.b) * 2.2f + w.ambientFloor * 3f;
            foreach (var l in w.heroLights)
            {
                if (l == null || !l.isActiveAndEnabled) continue;
                Vector3 v = p - l.transform.position;
                float dist = v.magnitude;
                if (dist > l.range) continue;
                float cone = 1f;
                if (l.type == LightType.Spot) cone = Mathf.Clamp01((Vector3.Dot(v / Mathf.Max(dist, 1e-3f), l.transform.forward) - Mathf.Cos(l.spotAngle * 0.5f * Mathf.Deg2Rad)) * 8f);
                if (cone <= 0f) continue;
                var baseC = w.BaseColor(l);
                var t = l.range >= 60f ? Color.white : WaterOptics.Transmit(ext, dist);   // lamps: absorbed on the way; the volcano: Verne's art direction
                float k = cone * l.intensity * 0.6f / (1f + dist * dist) * (1f - dist / l.range);
                c += new Color(baseC.r * t.r, baseC.g * t.g, baseC.b * t.b) * k;
            }
            return c;
        }

        void LateUpdate()
        {
            if (m_PS == null) return;
            int max = m_PS.main.maxParticles;
            if (m_P == null || m_P.Length < max) m_P = new ParticleSystem.Particle[max];   // survives a script reload in play
            if (m_Vel == null || m_Vel.Length < max) m_Vel = new Vector3[max];
            int n = m_PS.GetParticles(m_P);
            var c = Eye();
            var w = VerneWater.Active;
            float t = Time.time, dt = Mathf.Min(Time.deltaTime, 0.1f);
            Vector3 h = box * 0.5f;
            Color ext = w != null ? w.Extinction : new Color(0.3f, 0.06f, 0.05f);

            // the things that stir the water: the visitor (from the eye's motion) and the divers
            Vector3 eyeVel = dt > 0f ? (c - m_LastEye) / dt : Vector3.zero;
            if (eyeVel.sqrMagnitude > 25f) eyeVel = Vector3.zero;   // a teleport, not a wake
            m_LastEye = c;
            var s_Divers = DiverPuppet.All;

            float depthBelow = w != null ? Mathf.Max(0f, w.surfaceY - c.y) : 50f;
            float surgeNow = surge * Mathf.Exp(-depthBelow * 0.12f) * Mathf.Sin(t * 2f * Mathf.PI / Mathf.Max(surgePeriod, 1f));
            Vector3 surgeDir = current.sqrMagnitude > 1e-6f ? current.normalized : Vector3.right;

            for (int i = 0; i < n; i++)
            {
                var p = m_P[i].position;
                float size = m_P[i].startSize;
                // sinking: 0.5–2 mm/s, the big fluffy motes the slowest
                float sink = Mathf.Lerp(0.002f, 0.0005f, Mathf.InverseLerp(0.012f, 0.035f, size));
                Vector3 drift = current * (0.8f + 0.4f * Mathf.Sin(i * 1.7f)) + surgeDir * surgeNow + Vector3.down * sink;
                // tiny turbulence so neighbours don't move as one sheet
                drift += new Vector3(Mathf.Sin(t * 0.21f + i), Mathf.Sin(t * 0.13f + i * 0.5f) * 0.3f, Mathf.Cos(t * 0.17f + i * 1.3f)) * 0.006f;
                // wakes: pushed along by a body passing within ~1 m, then the water's drag lets it go
                var v = m_Vel[i];
                Vector3 d = p - (c - Vector3.up * 0.9f);
                float r2 = d.sqrMagnitude;
                if (r2 < 1.2f && eyeVel.sqrMagnitude > 0.01f) v += (eyeVel * 0.6f + d.normalized * eyeVel.magnitude * 0.4f) * (1f - r2 / 1.2f) * dt * 3f;
                for (int k = 0; k < s_Divers.Count; k++)
                {
                    var dv = s_Divers[k];
                    if (dv == null || dv.speed < 0.05f) continue;
                    Vector3 dd = p - (dv.transform.position + Vector3.up * 0.9f);
                    float rr = dd.sqrMagnitude;
                    if (rr < 1.0f) v += (dv.transform.forward * dv.speed * 0.5f + dd.normalized * dv.speed * 0.3f) * (1f - rr) * dt * 3f;
                }
                v *= Mathf.Exp(-dt * 1.5f);
                m_Vel[i] = v;
                p += (drift + v) * dt;
                // wrap round the eye so the box follows without popping
                Vector3 e = p - c;
                if (e.x > h.x) p.x -= box.x; else if (e.x < -h.x) p.x += box.x;
                if (e.y > h.y) p.y -= box.y; else if (e.y < -h.y) p.y += box.y;
                if (e.z > h.z) p.z -= box.z; else if (e.z < -h.z) p.z += box.z;
                m_P[i].position = p;
                // colour = the light at this mote
                var L = LightAt(w, p, ext);
                float a = Mathf.Clamp01((L.r + L.g + L.b) * 0.5f);
                float m = Mathf.Max(L.r, Mathf.Max(L.g, L.b), 1e-4f);
                m_P[i].startColor = new Color(0.55f + 0.45f * L.r / m, 0.55f + 0.45f * L.g / m, 0.55f + 0.45f * L.b / m, a);
            }
            m_PS.SetParticles(m_P, n);
        }
    }
}
