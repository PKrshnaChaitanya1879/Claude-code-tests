using UnityEngine;

namespace Verne
{
    /// <summary>
    /// A school of fish for the excursions (I.XVI: "little fishes ... more numerous than the birds";
    /// "fish-flies ... like humming-birds"). The school's centre wanders between waypoints near the route;
    /// each fish keeps its place in the school with a little noise, beats its tail (a yaw flick), and darts
    /// away when the visitor comes close, then drifts back. Lit by the scene (sun, Ruhmkorff lamps) and
    /// coloured by the water pass like everything else. Medusae use the same component, slow and pulsing.
    /// </summary>
    public class FishSchool : MonoBehaviour
    {
        public enum Kind { Fish, Medusa, BigFish, Floater }   // Floater: porphitae and physalides drifting just under the surface (I.XV)
        public Kind kind = Kind.Fish;
        public Material material;
        public int count = 30;
        public float size = 0.22f;
        public float speed = 1.2f;
        public float spread = 2.2f;
        public Vector3[] waypoints;
        public float fleeRadius = 2.2f;

        Transform[] m_Fish;
        Vector3[] m_Offset, m_Vel, m_Flee;
        float[] m_Phase;
        Vector3 m_Centre, m_Target;
        int m_Wp;

        // Solid things fish must never enter (GUM: "fishes are glitching through the submarine").
        // Every collider on the Hull layer becomes a capsule along its longest axis, gathered once per scene.
        struct Capsule { public Vector3 a, b; public float r; }
        static Capsule[] s_Obstacles; static string s_ObstacleScene;
        static void GatherObstacles()
        {
            string sc = UnityEngine.SceneManagement.SceneManager.GetActiveScene().path;   // (a path: SceneHandle changed type in Unity 6.6)
            if (s_Obstacles != null && s_ObstacleScene == sc) return;
            s_ObstacleScene = sc;
            int hull = LayerMask.NameToLayer("Hull");
            var list = new System.Collections.Generic.List<Capsule>();
            if (hull >= 0)
                foreach (var c in Object.FindObjectsByType<Collider>(FindObjectsInactive.Exclude, FindObjectsSortMode.None))
                {
                    if (c.isTrigger || c.gameObject.layer != hull) continue;
                    var b = c.bounds; var e = b.extents;
                    int ax = e.x >= e.y && e.x >= e.z ? 0 : (e.y >= e.z ? 1 : 2);
                    float len = e[ax], r = ax == 0 ? Mathf.Max(e.y, e.z) : ax == 1 ? Mathf.Max(e.x, e.z) : Mathf.Max(e.x, e.y);
                    var dir = Vector3.zero; dir[ax] = Mathf.Max(0f, len - r);
                    list.Add(new Capsule { a = b.center - dir, b = b.center + dir, r = r * 1.08f + 0.35f });
                }
            s_Obstacles = list.ToArray();
        }
        /// <summary>Pushes p out of every hull capsule; returns the outward normal if it was inside (else zero).</summary>
        static Vector3 PushOut(ref Vector3 p, float margin)
        {
            Vector3 n = Vector3.zero;
            for (int k = 0; k < s_Obstacles.Length; k++)
            {
                var c = s_Obstacles[k];
                Vector3 ab = c.b - c.a; float t = ab.sqrMagnitude > 1e-6f ? Mathf.Clamp01(Vector3.Dot(p - c.a, ab) / ab.sqrMagnitude) : 0f;
                Vector3 q = c.a + ab * t, d = p - q; float dist = d.magnitude, r = c.r + margin;
                if (dist >= r) continue;
                Vector3 dn = dist > 1e-4f ? d / dist : Vector3.up;
                p = q + dn * r; n += dn;
            }
            return n;
        }

        void Start()
        {
            var mesh = kind == Kind.Medusa || kind == Kind.Floater ? SeaWindowView.MedusaMesh : SeaWindowView.FishMesh;
            var rnd = new System.Random(name.GetHashCode() ^ transform.position.GetHashCode());
            m_Fish = new Transform[count]; m_Offset = new Vector3[count]; m_Vel = new Vector3[count]; m_Flee = new Vector3[count]; m_Phase = new float[count];
            m_Centre = waypoints != null && waypoints.Length > 0 ? waypoints[0] : transform.position;
            GatherObstacles();
            PushOut(ref m_Centre, 1.5f);
            m_Target = Next();
            for (int i = 0; i < count; i++)
            {
                var go = new GameObject(kind + " " + i);
                go.transform.SetParent(transform, false);
                go.AddComponent<MeshFilter>().sharedMesh = mesh;
                var mr = go.AddComponent<MeshRenderer>();
                mr.sharedMaterial = material;
                mr.shadowCastingMode = kind == Kind.BigFish ? UnityEngine.Rendering.ShadowCastingMode.On : UnityEngine.Rendering.ShadowCastingMode.Off;
                m_Offset[i] = new Vector3((float)(rnd.NextDouble() - 0.5), (float)(rnd.NextDouble() - 0.5) * 0.5f, (float)(rnd.NextDouble() - 0.5)) * spread;
                m_Phase[i] = (float)rnd.NextDouble() * 6.28f;
                float s = size * (0.8f + 0.4f * (float)rnd.NextDouble());
                go.transform.localScale = kind == Kind.Floater ? new Vector3(s, s * 0.35f, s) : Vector3.one * s;   // a flat float, a blue disc
                go.transform.position = m_Centre + m_Offset[i];
                m_Fish[i] = go.transform;
            }
        }

        Vector3 Next()
        {
            if (waypoints == null || waypoints.Length == 0) return transform.position + Random.insideUnitSphere * 6f;
            m_Wp = (m_Wp + 1) % waypoints.Length;
            return waypoints[m_Wp];
        }

        void Update()
        {
            if (m_Fish == null) return;
            float dt = Time.deltaTime, t = Time.time;
            Vector3 toT = m_Target - m_Centre;
            if (toT.magnitude < 1.5f) m_Target = Next();
            m_Centre += toT.normalized * Mathf.Min(speed * dt, toT.magnitude);
            if (PushOut(ref m_Centre, spread * 0.5f + 0.5f) != Vector3.zero) m_Target = Next();   // the school skirts the hull
            var p = PlayerMotor.Instance != null ? PlayerMotor.Instance.transform.position + Vector3.up * 1.5f : new Vector3(0, -1e4f, 0);
            for (int i = 0; i < m_Fish.Length; i++)
            {
                var f = m_Fish[i];
                float ph = m_Phase[i];
                Vector3 want = m_Centre + m_Offset[i] + new Vector3(Mathf.Sin(t * 0.7f + ph), Mathf.Sin(t * 0.5f + ph * 1.7f) * 0.4f, Mathf.Cos(t * 0.6f + ph)) * 0.4f;
                // the visitor comes close: a dart away, then the school's pull brings it back
                Vector3 away = f.position - p;
                if (kind != Kind.Medusa && kind != Kind.Floater && away.magnitude < fleeRadius) m_Flee[i] = away.normalized * (fleeRadius - away.magnitude) * 3f;
                m_Flee[i] = Vector3.MoveTowards(m_Flee[i], Vector3.zero, dt * 2f);
                if (kind == Kind.Floater) want.y = m_Centre.y + Mathf.Sin(t * 0.4f + ph) * 0.08f;   // riding the swell's underside
                Vector3 acc = (want - f.position) * (kind == Kind.Medusa || kind == Kind.Floater ? 0.3f : 2.2f) + m_Flee[i] * 4f - m_Vel[i] * 1.8f;
                m_Vel[i] += acc * dt;
                var np = f.position + m_Vel[i] * dt;
                var hit = PushOut(ref np, size);
                if (hit != Vector3.zero) { hit.Normalize(); m_Vel[i] -= hit * Mathf.Min(0f, Vector3.Dot(m_Vel[i], hit)) * 1.6f; }   // glance off, never through
                f.position = np;
                if (kind == Kind.Floater) { f.Rotate(0f, dt * 6f, 0f, Space.World); continue; }
                if (kind == Kind.Medusa)
                {
                    float pulse = 0.5f + 0.5f * Mathf.Sin(t * 1.6f + ph);
                    f.localScale = Vector3.one * size * new Vector3(1f - 0.12f * pulse, 1f + 0.1f * pulse, 1f - 0.12f * pulse).x;
                    f.position += Vector3.up * pulse * 0.15f * dt;
                    continue;
                }
                Vector3 v = m_Vel[i].sqrMagnitude > 1e-4f ? m_Vel[i] : (m_Target - m_Centre);
                if (v.sqrMagnitude < 1e-6f) continue;
                float beat = Mathf.Sin(t * (kind == Kind.BigFish ? 2.5f : 9f) + ph) * (kind == Kind.BigFish ? 4f : 12f);   // the tail's flick
                f.rotation = Quaternion.Slerp(f.rotation, Quaternion.LookRotation(v.normalized, Vector3.up) * Quaternion.Euler(0f, beat, 0f), dt * 6f);
            }
        }
    }
}
