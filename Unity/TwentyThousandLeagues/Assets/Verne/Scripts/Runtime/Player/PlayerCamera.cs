using UnityEngine;
using UnityEngine.Rendering.Universal;

namespace Verne
{
    /// <summary>
    /// Camera-side player settings: FOV from options (narrower in the helmet, whose three ports
    /// frame the view), post-processing on, and a last-resort guard that pulls the eye back
    /// toward the body if anything ever overlaps it (the capsule already prevents this).
    /// </summary>
    [RequireComponent(typeof(Camera))]
    public class PlayerCamera : MonoBehaviour
    {
        public float helmetFovScale = 0.9f;
        public float guardRadius = 0.1f;

        Camera m_Cam;
        PlayerMotor m_Motor;
        float m_Fov;

        void Awake()
        {
            m_Cam = GetComponent<Camera>();
            m_Motor = GetComponentInParent<PlayerMotor>();
            var data = m_Cam.GetUniversalAdditionalCameraData();
            data.renderPostProcessing = true;
            data.antialiasing = AntialiasingMode.FastApproximateAntialiasing;
            data.requiresDepthTexture = true;
            m_Fov = GameSettings.Current.fieldOfView;
        }

        void LateUpdate()
        {
            float target = GameSettings.Current.fieldOfView;
            if (m_Motor != null && m_Motor.mode != MoveMode.Air) target *= helmetFovScale;
            m_Fov = Mathf.Lerp(m_Fov, target, 1f - Mathf.Exp(-Time.unscaledDeltaTime * 4f));
            m_Cam.fieldOfView = m_Fov;

            // guard: the eye must stay in free space; if a thin object overlaps it, slide back toward the body centre
            if (m_Motor == null) return;
            Vector3 body = m_Motor.transform.position + Vector3.up * (m_Motor.GetComponent<CharacterController>().height * 0.5f);
            Vector3 eye = transform.parent.position;
            Vector3 dir = eye - body;
            float len = dir.magnitude;
            if (len > 0.001f && Physics.SphereCast(body, guardRadius, dir / len, out var hit, len, ~0, QueryTriggerInteraction.Ignore)
                && hit.collider.GetComponentInParent<PlayerMotor>() == null)
                transform.position = body + dir / len * Mathf.Max(0f, hit.distance - 0.02f);
            else
                transform.localPosition = Vector3.zero;
        }
    }
}
