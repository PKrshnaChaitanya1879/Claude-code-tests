using UnityEngine;

namespace Verne
{
    /// <summary>"In the midst of a rain of stones and scoriae" (II.IX): stones thrown up from the crater sink back through
    /// the water (slow, with drag) and are thrown up again. Each keeps its own phase.</summary>
    public class Scoria : MonoBehaviour
    {
        Vector3 m_Origin, m_Vel; float m_Spin; Vector3 m_Axis;
        static readonly System.Random s_R = new System.Random(5);

        void Start() { m_Origin = transform.position; Throw(); transform.position += m_Vel * (float)s_R.NextDouble() * 6f; }

        void Throw()
        {
            m_Vel = new Vector3((float)(s_R.NextDouble() - 0.5) * 6f, 4f + (float)s_R.NextDouble() * 5f, (float)(s_R.NextDouble() - 0.5) * 6f);
            m_Axis = Random.onUnitSphere; m_Spin = 20f + (float)s_R.NextDouble() * 60f;
        }

        void Update()
        {
            float dt = Time.deltaTime;
            m_Vel += Vector3.down * 1.2f * dt;                  // heavy stone, buoyed and dragged by the water
            m_Vel *= 1f - 0.25f * dt;
            transform.position += m_Vel * dt;
            transform.Rotate(m_Axis, m_Spin * dt, Space.World);
            if (transform.position.y < m_Origin.y - 50f) { transform.position = AtlantisCrater; Throw(); }
        }

        /// <summary>Set by the scene builder: where the crater throws its stones from.</summary>
        public static Vector3 AtlantisCrater = new Vector3(70f, 68f, 215f);
    }
}
