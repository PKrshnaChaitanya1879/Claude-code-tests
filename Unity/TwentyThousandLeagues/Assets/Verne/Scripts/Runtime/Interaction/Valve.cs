using System;
using UnityEngine;
using UnityEngine.Events;

namespace Verne
{
    /// <summary>
    /// A hand-wheel or tap. Hold to turn: it opens progressively (the flooding-cell tap, the
    /// ballast taps). Optional spring return closes it when released.
    /// </summary>
    public class Valve : Interactable
    {
        public Transform wheel;
        public Vector3 axis = Vector3.forward;
        [Tooltip("Full turns from closed to open.")]
        public float turns = 2.5f;
        public float turnRate = 0.45f;        // openness per second while held
        public bool springReturn = false;
        public float returnRate = 0.6f;
        [Range(0, 1)] public float openness = 0f;
        public FloatEvent onOpenness = new FloatEvent();
        public UnityEvent onFullyOpen = new UnityEvent();
        public UnityEvent onClosed = new UnityEvent();
        public AudioClip squeak;
        [Tooltip("If set, turning closes instead of opens.")]
        public bool closing;

        float m_Squeak;
        bool m_WasOpen;
        Quaternion m_Rest;

        [Tooltip("Turns back the other way once fully open (and forward again once closed): door dogs, the pump cock.")]
        public bool bidirectional;
        [Tooltip("Prompt nouns for the two directions when bidirectional, e.g. \"Dog\" / \"Undog\".")]
        public string verbOpen = "", verbClose = "";

        public override bool CapturesLook => true;
        public override string Prompt => !bidirectional || string.IsNullOrEmpty(verbOpen) ? base.Prompt : (closing ? verbClose : verbOpen) + (string.IsNullOrEmpty(noun) ? "" : " " + noun);

        protected override void OnBegin(Interactor who)
        {
            if (bidirectional) { if (openness >= 0.999f) closing = true; else if (openness <= 0.001f) closing = false; }
            base.OnBegin(who);
        }

        protected override void OnEnd(Interactor who)
        {
            if (bidirectional) { if (openness >= 0.999f) closing = true; else if (openness <= 0.001f) closing = false; }
            base.OnEnd(who);
        }

        protected override void Awake()
        {
            base.Awake();
            if (wheel == null) wheel = transform;
            if (squeak == null) squeak = Resources.Load<AudioClip>("VerneAudio/sfx/valve_squeak");
            m_Rest = wheel.localRotation;
            Pose();
        }

        protected override void OnHold(Interactor who, Vector2 look, float dt)
        {
            float effort = 1f + Mathf.Clamp(look.magnitude * 0.08f, 0f, 1.5f); // circling the mouse turns it faster
            float d = turnRate * effort * dt * (closing ? -1f : 1f);
            Set(openness + d);
            m_Squeak -= dt;
            if (m_Squeak <= 0f) { m_Squeak = 0.55f; PlayOneShot(squeak, 0.5f); }
        }

        void Update()
        {
            if (!IsHeld && springReturn && openness > 0f) Set(openness - returnRate * Time.deltaTime);
        }

        public void Set(float v)
        {
            float prev = openness;
            openness = Mathf.Clamp01(v);
            if (Mathf.Approximately(prev, openness)) return;
            Pose();
            onOpenness.Invoke(openness);
            if (openness >= 1f && !m_WasOpen) { m_WasOpen = true; onFullyOpen.Invoke(); }
            if (openness <= 0f && prev > 0f) { m_WasOpen = false; onClosed.Invoke(); }
        }

        void Pose() { if (wheel != null) wheel.localRotation = m_Rest * Quaternion.AngleAxis(-openness * turns * 360f, axis); }
    }
}
