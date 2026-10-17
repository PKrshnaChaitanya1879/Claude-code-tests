using UnityEngine;

namespace Verne
{
    /// <summary>Turns a machine part about a world-space axis through its pivot (the screw's axle, the great wheel, the cog).</summary>
    public class Rotator : MonoBehaviour
    {
        public Vector3 axis = Vector3.forward;
        public float rpm = 24f;
        public bool onlyWhenVisible = true;
        Renderer m_R;

        void Awake() { m_R = GetComponentInChildren<Renderer>(); }

        void Update()
        {
            if (onlyWhenVisible && m_R != null && !m_R.isVisible) return;
            transform.Rotate(axis, rpm * 6f * Time.deltaTime, Space.World);
        }
    }
}
