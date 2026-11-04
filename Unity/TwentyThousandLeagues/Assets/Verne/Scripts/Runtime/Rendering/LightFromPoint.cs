using UnityEngine;

namespace Verne
{
    /// <summary>
    /// A distant point of light (the volcano's crater) cast as the scene's shadowed main light. Each frame the light is aimed
    /// from the source to the eye, so its shadows, and the shafts the water march carves from them, fan out from the crater
    /// as they would from the fire itself. Over the 100–200 m between you and the crater the rays across your view are near
    /// parallel, which is what a directional shadow map can hold; the direction is right wherever you stand.
    /// </summary>
    [RequireComponent(typeof(Light))]
    public class LightFromPoint : MonoBehaviour
    {
        public Vector3 source;
        [Tooltip("Aim a little below the eye, so the light reaches the ground where you walk.")]
        public float aimBelowEye = 6f;

        void LateUpdate()
        {
            var cam = Camera.main;
            if (cam == null) return;
            var target = cam.transform.position - Vector3.up * aimBelowEye;
            var dir = target - source;
            if (dir.sqrMagnitude < 1f) return;
            transform.rotation = Quaternion.LookRotation(dir.normalized, Vector3.up);
        }
    }
}
