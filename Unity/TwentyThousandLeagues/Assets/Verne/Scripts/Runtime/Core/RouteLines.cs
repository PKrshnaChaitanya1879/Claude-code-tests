using UnityEngine;

namespace Verne
{
    /// <summary>The book's own words along an excursion's way: each line is shown once, when the visitor first passes its z.</summary>
    public class RouteLines : MonoBehaviour
    {
        [System.Serializable] public struct Line { public float z; [TextArea] public string text; public float seconds; }
        public Line[] lines;
        int m_Next;

        void Update()
        {
            var p = PlayerMotor.Instance;
            if (p == null || lines == null || m_Next >= lines.Length) return;
            if (p.transform.position.z < lines[m_Next].z) return;
            Hud.Toast(lines[m_Next].text, lines[m_Next].seconds > 0f ? lines[m_Next].seconds : 6f);
            m_Next++;
        }
    }
}
