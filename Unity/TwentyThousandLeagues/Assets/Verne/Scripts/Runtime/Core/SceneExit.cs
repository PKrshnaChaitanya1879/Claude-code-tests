using UnityEngine;

namespace Verne
{
    /// <summary>A trigger that loads another scene when the player walks into it, optionally only when a flooding cell is full.</summary>
    [RequireComponent(typeof(Collider))]
    public class SceneExit : MonoBehaviour
    {
        public string scene = SceneFlow.Mission1;
        public FloodingCell requiresFlooded;
        bool m_Used;

        void Reset() { GetComponent<Collider>().isTrigger = true; }

        void OnTriggerEnter(Collider other)
        {
            if (m_Used || other.GetComponent<PlayerMotor>() == null) return;
            if (requiresFlooded != null && !requiresFlooded.Full) return;
            m_Used = true;
            SceneFlow.Load(scene);
        }
    }
}
