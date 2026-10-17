using System;
using UnityEngine;
using UnityEngine.Events;

namespace Verne
{
    /// <summary>
    /// A dial with a needle that has inertia and a little tremble, like a real gauge.
    /// Drive it by setting <see cref="target"/> (in the gauge's own units).
    /// </summary>
    public class Gauge : MonoBehaviour
    {
        public Transform needle;
        public Vector3 axis = Vector3.forward;
        public float minValue = 0f, maxValue = 10f;
        public float minAngle = -135f, maxAngle = 135f;
        public float target;
        public float response = 6f;
        public float tremble = 0.004f;
        float m_Value, m_Vel;

        public float Value => m_Value;

        void Update()
        {
            float k = response * response, c = 1.4f * response;
            m_Vel += ((target - m_Value) * k - m_Vel * c) * Time.deltaTime;
            m_Value += m_Vel * Time.deltaTime;
            float n = Mathf.InverseLerp(minValue, maxValue, m_Value);
            n += (Mathf.PerlinNoise(Time.time * 7f, GetInstanceID() * 0.01f) - 0.5f) * tremble;
            if (needle != null) needle.localRotation = Quaternion.AngleAxis(Mathf.LerpUnclamped(minAngle, maxAngle, n), axis);
        }
    }
}
