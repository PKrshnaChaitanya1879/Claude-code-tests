using System;
using UnityEngine;
using UnityEngine.Events;

namespace Verne
{
    /// <summary>
    /// A physical lever. Grab it and move the mouse (or stick) to throw it; it has mass, travels
    /// between its stops, and clicks into notches. A quick tap throws it to the far notch.
    /// The handle rotates about the pivot's local X axis.
    /// </summary>
    public class Lever : Interactable
    {
        public Transform pivot;
        public float minAngle = -35f, maxAngle = 35f;
        [Range(0, 1)] public float value = 0f;
        [Tooltip("Number of detents including both ends (2 = on/off).")]
        public int notches = 2;
        public float stiffness = 0.012f;    // value per unit of mouse travel
        public FloatEvent onValueChanged = new FloatEvent();
        public IntEvent onNotch = new IntEvent();
        public AudioClip clunk;

        float m_Vel;
        int m_LastNotch = -1;
        float m_Target;
        bool m_Dragged;

        public override bool CapturesLook => true;
        public int Notch => notches <= 1 ? 0 : Mathf.RoundToInt(value * (notches - 1));

        protected override void Awake()
        {
            base.Awake();
            if (pivot == null) pivot = transform;
            m_Target = value;
            m_LastNotch = Notch;
            Pose();
        }

        protected override void OnBegin(Interactor who) { m_Dragged = false; }

        protected override void OnHold(Interactor who, Vector2 look, float dt)
        {
            if (Mathf.Abs(look.y) > 0.01f) m_Dragged = true;
            m_Target = Mathf.Clamp01(m_Target + look.y * stiffness * 4f);
        }

        protected override void OnEnd(Interactor who)
        {
            if (!m_Dragged && who.HoldTime < 0.35f)
            {
                // tap: throw to the opposite end
                m_Target = value < 0.5f ? 1f : 0f;
            }
            // settle into the nearest notch
            if (notches > 1) m_Target = Mathf.Round(m_Target * (notches - 1)) / (notches - 1);
            onUsed.Invoke();
        }

        void Update()
        {
            float target = m_Target;
            if (!IsHeld && notches > 1) target = Mathf.Round(m_Target * (notches - 1)) / (notches - 1);
            // critically-damped-ish spring: the lever has weight
            float k = 120f, c = 18f;
            m_Vel += ((target - value) * k - m_Vel * c) * Time.deltaTime;
            float prev = value;
            value = Mathf.Clamp01(value + m_Vel * Time.deltaTime);
            if (value <= 0f || value >= 1f) m_Vel = 0f;
            if (!Mathf.Approximately(prev, value)) { Pose(); onValueChanged.Invoke(value); }
            int n = Notch;
            if (n != m_LastNotch && Mathf.Abs(value - (float)n / Mathf.Max(1, notches - 1)) < 0.04f)
            {
                m_LastNotch = n;
                PlayOneShot(clunk, 0.8f);
                onNotch.Invoke(n);
            }
        }

        void Pose()
        {
            if (pivot != null) pivot.localRotation = Quaternion.Euler(Mathf.Lerp(minAngle, maxAngle, value), 0f, 0f);
        }

        public void SetValueImmediate(float v) { value = m_Target = Mathf.Clamp01(v); m_Vel = 0f; m_LastNotch = Notch; Pose(); }
    }
}
