using UnityEngine;

namespace Verne
{
    /// <summary>
    /// Mission II's falls (the crevice, the far side of the summit): when the visitor drops well below the last firm
    /// ground he stood on, the screen dims and he is set back there, as the prototype did after the book's
    /// "Captain Nemo's strong hand" on the mountain. Remembers firm ground only while grounded and not falling.
    /// </summary>
    public class FallRescue : MonoBehaviour
    {
        public float dropBelow = 6f;
        Vector3 m_Safe; float m_Yaw; bool m_Has; float m_Cool, m_GroundedFor, m_LastGroundY;

        void Update()
        {
            var p = PlayerMotor.Instance;
            if (p == null) return;
            var pos = p.transform.position;
            m_Cool -= Time.deltaTime;
            if (p.Grounded)
            {
                m_GroundedFor += Time.deltaTime; m_LastGroundY = pos.y;
                // firm ground only: standing a moment, on a slope the visitor can stand on, not on the log
                if (m_Cool <= 0f && m_GroundedFor > 0.3f && Physics.Raycast(pos + Vector3.up * 0.5f, Vector3.down, out var hit, 1.5f, ~((1 << 2) | (1 << 8)), QueryTriggerInteraction.Ignore)
                    && hit.normal.y > 0.74f && !hit.collider.name.StartsWith("Log") && !hit.collider.name.StartsWith("log"))
                { m_Safe = pos; m_Yaw = p.transform.eulerAngles.y; m_Has = true; }
                return;
            }
            m_GroundedFor = 0f;
            if (m_Has && pos.y < m_LastGroundY - dropBelow)
            {
                p.Teleport(m_Safe + Vector3.up * 0.1f, m_Yaw);
                m_Cool = 1.5f;
                Hud.Toast("Captain Nemo's strong hand hauled me back.", 4f);
            }
        }
    }
}
