using UnityEngine;
using UnityEngine.AI;

namespace Verne
{
    /// <summary>
    /// Ned Land and Conseil walking with the Professor (I.XV–XVI: "Conseil and I remained near each other";
    /// I.XXIV: Ned and Conseil at the burial). Each keeps a slot a few metres behind and to one side of the
    /// visitor on the NavMesh, stops when close, catches up when left behind, and turns to look where the visitor
    /// looks when standing. A scripted scene can take over with <see cref="hold"/>.
    /// </summary>
    public class DiverFollower : MonoBehaviour
    {
        public Vector2 slot = new Vector2(-1.6f, -2.4f);     // x right, y forward, in the visitor's frame
        public float pace = 0.8f;
        public bool hold;
        public string firstLine = "";
        DiverPuppet m_Puppet;
        NavMeshAgent m_Agent;
        float m_Repath;
        bool m_Spoke;

        void Start()
        {
            m_Puppet = GetComponent<DiverPuppet>();
            m_Agent = Agents.Attach(gameObject, pace);
        }

        void Update()
        {
            var p = PlayerMotor.Instance;
            if (m_Puppet == null || p == null) return;
            if (hold) { if (m_Agent != null) m_Agent.isStopped = true; return; }
            var pt = p.transform;
            Vector3 fwd = pt.forward; fwd.y = 0f; fwd = fwd.sqrMagnitude > 1e-4f ? fwd.normalized : Vector3.forward;
            Vector3 right = Vector3.Cross(Vector3.up, fwd);
            Vector3 goal = pt.position + right * slot.x + fwd * slot.y;
            float far = (goal - transform.position).magnitude;
            if (!m_Spoke && !string.IsNullOrEmpty(firstLine) && Vector3.Distance(pt.position, transform.position) < 4f) { m_Spoke = true; Hud.Toast(firstLine, 5f); }

            if (m_Agent != null)
            {
                float speed = far > 8f ? pace * 1.6f : pace;          // a heavier stride to catch up, never a run
                m_Agent.speed = speed;
                if (far < 1.2f) { m_Agent.isStopped = true; }
                else if (Time.time >= m_Repath)
                {
                    m_Repath = Time.time + 0.5f;
                    m_Agent.isStopped = false;
                    if (NavMesh.SamplePosition(goal, out var hit, 3f, NavMesh.AllAreas)) m_Agent.SetDestination(hit.position);
                }
                float v = m_Agent.velocity.magnitude;
                m_Puppet.gesture = v > 0.05f ? DiverPuppet.Gesture.Walk : DiverPuppet.Gesture.Idle;
                m_Puppet.speed = v;
                if (v < 0.05f) Face(transform.position + fwd);
                return;
            }
            // no NavMesh: straight steps on the ground
            if (far > 1.2f)
            {
                var to = goal - transform.position; to.y = 0f;
                var pos = transform.position + to.normalized * pace * Time.deltaTime;
                if (Physics.Raycast(pos + Vector3.up * 2f, Vector3.down, out var h2, 6f, ~(1 << 2), QueryTriggerInteraction.Ignore)) pos.y = h2.point.y;
                transform.position = pos;
                Face(transform.position + to);
                m_Puppet.gesture = DiverPuppet.Gesture.Walk; m_Puppet.speed = pace;
            }
            else { m_Puppet.gesture = DiverPuppet.Gesture.Idle; m_Puppet.speed = 0f; Face(transform.position + fwd); }
        }

        void Face(Vector3 at)
        {
            var dir = at - transform.position; dir.y = 0f;
            if (dir.sqrMagnitude < 1e-4f) return;
            transform.rotation = Quaternion.Slerp(transform.rotation, Quaternion.LookRotation(dir), Time.deltaTime * 2f);
        }
    }
}
