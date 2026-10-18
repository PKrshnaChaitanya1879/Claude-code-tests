using UnityEngine;
using UnityEngine.AI;

namespace Verne
{
    /// <summary>
    /// Captain Nemo leading the way (I.XV: "Captain Nemo walked in front, his companion followed some steps
    /// behind"): walks the route's waypoints at a heavy pace, keeps to the ground, waits and beckons when the
    /// visitor falls behind, and stands at the last point. (M4) On the scene's baked NavMesh it walks with a
    /// NavMeshAgent, so it goes round rocks, stems and the visitor instead of through them; without a NavMesh it
    /// falls back to straight legs.
    /// </summary>
    public class DiverGuide : MonoBehaviour
    {
        public Vector3[] waypoints;
        public float pace = 0.75f;               // m/s: slow, deliberate
        public float waitDistance = 9f, resumeDistance = 6f;
        public string arrivedLine = "";
        [Tooltip("The Ruhmkorff lamp at the belt, lit once the way goes dark (the coral gallery, I.XXIII).")]
        public Light lamp;
        public float lampOnAfterZ = 1e9f;
        public string lampLine = "";
        bool m_LampLit;
        DiverPuppet m_Puppet;
        int m_I;
        bool m_Waiting, m_Done;
        public bool Arrived => m_Done;
        /// <summary>A scripted scene (the burial) has taken over this diver: the guide stands still and lets it act.</summary>
        public bool hold;
        float m_BeckonTimer;

        NavMeshAgent m_Agent;
        int m_SetFor = -1;

        void Start()
        {
            m_Puppet = GetComponent<DiverPuppet>();
            m_Agent = Agents.Attach(gameObject, pace);
        }

        void Update()
        {
            if (m_Puppet == null || waypoints == null || waypoints.Length == 0) return;
            if (lamp != null && !m_LampLit && transform.position.z > lampOnAfterZ)
            {
                m_LampLit = true; lamp.enabled = true;
                var w = VerneWater.Active; if (w != null && !w.heroLights.Contains(lamp)) w.heroLights.Add(lamp);
                if (!string.IsNullOrEmpty(lampLine)) Hud.Toast(lampLine, 5f);
            }
            var p = PlayerMotor.Instance;
            float d = p != null ? Vector3.Distance(p.transform.position, transform.position) : 0f;
            if (hold) { if (m_Agent != null) m_Agent.isStopped = true; return; }
            if (m_Done) { if (m_Agent != null) m_Agent.isStopped = true; }
            if (m_Done) { m_Puppet.gesture = DiverPuppet.Gesture.Idle; m_Puppet.speed = 0f; Face(p != null ? p.transform.position : transform.position + transform.forward); return; }
            if (!m_Waiting && d > waitDistance) m_Waiting = true;
            if (m_Waiting && d < resumeDistance) m_Waiting = false;
            if (m_Agent != null) m_Agent.isStopped = m_Waiting;
            if (m_Waiting)
            {
                m_Puppet.speed = 0f;
                m_BeckonTimer -= Time.deltaTime;
                if (m_BeckonTimer <= 0f) m_BeckonTimer = 6f;
                m_Puppet.gesture = m_BeckonTimer > 3.5f ? DiverPuppet.Gesture.Beckon : DiverPuppet.Gesture.Idle;
                if (p != null) Face(p.transform.position);
                return;
            }
            var target = waypoints[m_I];
            var to = target - transform.position; to.y = 0f;
            if (m_Agent != null)
            {
                if (m_SetFor != m_I) { m_Agent.SetDestination(target); m_SetFor = m_I; return; }
                m_Agent.speed = pace;
                bool there = !m_Agent.pathPending && (m_Agent.remainingDistance < 0.5f || to.magnitude < 0.5f);
                if (there)
                {
                    m_I++;
                    if (m_I >= waypoints.Length) { m_Done = true; if (!string.IsNullOrEmpty(arrivedLine)) Hud.Toast(arrivedLine, 5f); }
                    return;
                }
                float v = m_Agent.velocity.magnitude;
                m_Puppet.gesture = v > 0.05f ? DiverPuppet.Gesture.Walk : DiverPuppet.Gesture.Idle;
                m_Puppet.speed = v;
                return;
            }
            if (to.magnitude < 0.4f)
            {
                m_I++;
                if (m_I >= waypoints.Length) { m_Done = true; if (!string.IsNullOrEmpty(arrivedLine)) Hud.Toast(arrivedLine, 5f); }
                return;
            }
            var step = to.normalized * pace * Time.deltaTime;
            var pos = transform.position + step;
            if (Physics.Raycast(pos + Vector3.up * 2f, Vector3.down, out var hit, 6f, ~(1 << 2), QueryTriggerInteraction.Ignore)) pos.y = Mathf.Lerp(transform.position.y, hit.point.y, 0.2f);
            transform.position = pos;
            Face(transform.position + to);
            m_Puppet.gesture = DiverPuppet.Gesture.Walk;
            m_Puppet.speed = pace;
        }

        void Face(Vector3 at)
        {
            var dir = at - transform.position; dir.y = 0f;
            if (dir.sqrMagnitude < 1e-4f) return;
            transform.rotation = Quaternion.Slerp(transform.rotation, Quaternion.LookRotation(dir), Time.deltaTime * 2.5f);
        }
    }
}
