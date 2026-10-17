using UnityEngine;

namespace Verne
{
    /// <summary>
    /// A climbable ladder. Put it on a trigger BoxCollider that covers the ladder plus ~0.4 m in
    /// front of it; transform.up is the climbing direction and transform.forward points away
    /// from the wall, toward the climber.
    /// </summary>
    [RequireComponent(typeof(Collider))]
    public class Ladder : MonoBehaviour
    {
        public float climbSpeed = 1.1f;
        public float length = 3f;

        public Vector3 ClosestPointOnLine(Vector3 p)
        {
            Vector3 a = transform.position + transform.forward * 0.45f;
            Vector3 dir = transform.up;
            float t = Mathf.Clamp(Vector3.Dot(p - a, dir), -0.2f, length + 0.5f);
            return a + dir * t;
        }

        void Reset() { GetComponent<Collider>().isTrigger = true; }

        void OnTriggerEnter(Collider other)
        {
            var m = other.GetComponent<PlayerMotor>();
            if (m != null) m.ActiveLadder = this;
        }

        void OnTriggerExit(Collider other)
        {
            var m = other.GetComponent<PlayerMotor>();
            if (m != null && m.ActiveLadder == this) m.ActiveLadder = null;
        }
    }
}
