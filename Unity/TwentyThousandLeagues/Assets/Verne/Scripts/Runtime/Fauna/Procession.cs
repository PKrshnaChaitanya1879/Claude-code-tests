using UnityEngine;

namespace Verne
{
    /// <summary>
    /// The four bearers of I.XXIV walk the whole way at the back of the party, the body in white linen on their
    /// shoulders: "Captain Nemo had stopped. I and my companions halted, and, turning round, I saw his men were
    /// forming a semi-circle round their chief. Watching attentively, I observed that four of them carried on their
    /// shoulders an object of an oblong shape." A formation anchor walks the route's waypoints some metres behind
    /// the visitor (never overtaking, catching up when left far behind); each bearer keeps its corner of the bier,
    /// feet on the sea floor, and the shroud rides between their shoulders. At the last waypoint they stand still,
    /// where the burial rite expects them.
    /// </summary>
    public class Procession : MonoBehaviour
    {
        public DiverPuppet[] bearers;              // fore-left, fore-right, aft-left, aft-right
        public Vector2[] corners = { new Vector2(-0.42f, 0.6f), new Vector2(0.42f, 0.6f), new Vector2(-0.42f, -0.6f), new Vector2(0.42f, -0.6f) };
        public Transform shroud;
        public float shoulder = 1.72f;
        public Vector3[] waypoints;
        public float pace = 0.65f;
        public float keepBehind = 7f;
        public bool Arrived { get; private set; }
        Vector3 m_Pos; Vector3 m_Fwd = Vector3.forward;
        int m_I;
        float m_Speed;

        void Start()
        {
            m_Pos = transform.position;
            if (waypoints != null && waypoints.Length > 0) { var d = waypoints[0] - m_Pos; d.y = 0; if (d.sqrMagnitude > 1e-3f) m_Fwd = d.normalized; }
            Pose(0f);
        }

        void Update()
        {
            if (Arrived) return;                     // the rite has them now
            if (waypoints == null || m_I >= waypoints.Length) { Arrived = true; Pose(0f); return; }
            var p = PlayerMotor.Instance;
            float target = 0f;
            if (p != null)
            {
                // how far ahead of us along the way the visitor is: walk while he leads by more than keepBehind
                Vector3 toP = p.transform.position - m_Pos; toP.y = 0f;
                float lead = Vector3.Dot(toP, m_Fwd);
                if (lead > keepBehind) target = lead > keepBehind * 3f ? pace * 1.5f : pace;
                // once the visitor is in the glade, they come on to their places whatever the distance
                var end = waypoints[waypoints.Length - 1]; end.y = p.transform.position.y;
                if (Vector3.Distance(p.transform.position, end) < 12f) target = pace;
            }
            else target = pace;
            m_Speed = Mathf.MoveTowards(m_Speed, target, Time.deltaTime * 0.5f);    // heavy: slow to start, slow to stop
            var to = waypoints[m_I] - m_Pos; to.y = 0f;
            if (to.magnitude < 0.3f)
            {
                m_I++;
                if (m_I >= waypoints.Length) { Arrived = true; m_Speed = 0f; }
                Pose(0f);
                return;
            }
            m_Fwd = Vector3.Slerp(m_Fwd, to.normalized, Time.deltaTime * 1.5f);
            m_Pos += to.normalized * Mathf.Min(m_Speed * Time.deltaTime, to.magnitude);
            Pose(m_Speed);
        }

        void Pose(float speed)
        {
            if (bearers == null) return;
            Vector3 right = Vector3.Cross(Vector3.up, m_Fwd);
            var rot = Quaternion.LookRotation(m_Fwd, Vector3.up);
            float ySum = 0f; int n = 0;
            for (int i = 0; i < bearers.Length && i < corners.Length; i++)
            {
                var b = bearers[i];
                if (b == null) continue;
                Vector3 at = m_Pos + right * corners[i].x + m_Fwd * corners[i].y;
                at.y = Ground(at, b.transform.position.y);
                b.transform.SetPositionAndRotation(at, rot);
                if (b.gesture == DiverPuppet.Gesture.Carry || b.gesture == DiverPuppet.Gesture.Walk || b.gesture == DiverPuppet.Gesture.Idle)
                    b.gesture = DiverPuppet.Gesture.Carry;
                b.speed = speed;
                ySum += at.y; n++;
            }
            if (shroud != null && n > 0)
                shroud.SetPositionAndRotation(new Vector3(m_Pos.x, ySum / n + shoulder, m_Pos.z), rot * m_ShroudRot);
        }
        Quaternion m_ShroudRot = Quaternion.identity;
        void Awake() { if (shroud != null) m_ShroudRot = shroud.rotation; }   // the bundle's own lie (built along the bier)

        static Vector3 s_Up = Vector3.up * 3f;
        static float Ground(Vector3 at, float fallback)
        {
            // the sea floor only (props and divers are skipped by name and layer)
            var hits = Physics.RaycastAll(at + s_Up, Vector3.down, 8f, ~(1 << 2), QueryTriggerInteraction.Ignore);
            float best = float.NegativeInfinity;
            foreach (var h in hits) if (h.collider != null && h.collider.name == "Sea floor") best = Mathf.Max(best, h.point.y);
            return float.IsNegativeInfinity(best) ? fallback : best;
        }
    }
}
