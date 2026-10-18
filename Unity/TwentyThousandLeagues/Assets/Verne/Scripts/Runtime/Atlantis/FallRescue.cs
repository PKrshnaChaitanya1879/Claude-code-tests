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
        Vector3 m_Safe; float m_Yaw; bool m_Has; float m_Cool;

        void Update()
        {
            var p = PlayerMotor.Instance;
            if (p == null) return;
            var pos = p.transform.position;
            m_Cool -= Time.deltaTime;
            if (p.Grounded && m_Cool <= 0f)
            {
                if (!m_Has || pos.y > m_Safe.y - 1.5f) { m_Safe = pos; m_Yaw = p.transform.eulerAngles.y; m_Has = true; }
            }
            if (m_Has && pos.y < m_Safe.y - dropBelow)
            {
                p.Teleport(m_Safe + Vector3.up * 0.1f, m_Yaw);
                m_Cool = 1.5f;
                Hud.Toast("Captain Nemo's strong hand hauled me back.", 4f);
            }
        }
    }
}
