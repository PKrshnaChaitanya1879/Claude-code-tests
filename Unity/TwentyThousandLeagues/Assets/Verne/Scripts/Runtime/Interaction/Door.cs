using System;
using UnityEngine;
using UnityEngine.Events;

namespace Verne
{
    /// <summary>
    /// A hinged or sliding door. It refuses to close onto the player (no pushing anyone into a
    /// wall) and can be locked by scripts (the flooding cell interlocks).
    /// </summary>
    public class Door : Interactable
    {
        public enum Kind { Hinge, Slide }
        public Kind kind = Kind.Hinge;
        public Transform leaf;
        public float openAngle = 100f;
        public Vector3 slideOffset = new Vector3(0.9f, 0f, 0f);
        public float speed = 1.2f;
        public bool open;
        public bool locked;
        public string lockedMessage = "It is fastened from the other side.";
        public AudioClip openClip, closeClip, lockedClip;
        public UnityEvent onOpened = new UnityEvent(), onClosed = new UnityEvent();

        float m_T;
        Quaternion m_RestRot;
        Vector3 m_RestPos;
        Collider[] m_Colliders;

        public override string Prompt => locked ? "Locked" : (open ? "Close" : "Open") + (string.IsNullOrEmpty(noun) ? "" : " " + noun);

        protected override void Awake()
        {
            base.Awake();
            if (leaf == null) leaf = transform;
            if (openClip == null) openClip = Resources.Load<AudioClip>("VerneAudio/sfx/door_open");
            if (closeClip == null) closeClip = Resources.Load<AudioClip>("VerneAudio/sfx/door_close");
            if (lockedClip == null) lockedClip = Resources.Load<AudioClip>("VerneAudio/sfx/door_locked");
            m_RestRot = leaf.localRotation;
            m_RestPos = leaf.localPosition;
            m_Colliders = leaf.GetComponentsInChildren<Collider>();
            m_T = open ? 1f : 0f;
            Pose();
        }

        protected override void OnBegin(Interactor who)
        {
            if (locked) { PlayOneShot(lockedClip, 0.6f); Hud.Toast(lockedMessage); return; }
            SetOpen(!open);
            base.OnBegin(who);
        }

        public void SetOpen(bool o)
        {
            if (o == open) return;
            open = o;
            PlayOneShot(o ? openClip : closeClip, 0.8f);
        }

        // GUM: "the door is working on binary principles". A heavy leaf on its hinges: a push accelerates it, it swings
        // with its own inertia, the hinge's friction slows it and it settles against the stop with a small rebound.
        float m_V;
        public float stiffness = 14f, damping = 5.2f;
        void Update()
        {
            float target = open ? 1f : 0f;
            if (Mathf.Abs(m_T - target) < 0.0005f && Mathf.Abs(m_V) < 0.0005f) { if (m_T != target) { m_T = target; m_V = 0f; Pose(); } return; }
            float dt = Mathf.Min(Time.deltaTime, 0.05f);
            m_V += ((target - m_T) * stiffness * speed - m_V * damping) * dt;
            float next = m_T + m_V * dt;
            if (!open && next < m_T && BlockedByPlayer()) { m_V = 0f; return; }   // wait, don't crush
            if (next > 1.04f) { next = 1.04f; m_V = -m_V * 0.25f; }                // the stop: a soft knock back
            if (next < 0f) { next = 0f; m_V = -m_V * 0.15f; }                       // the frame: it thuds shut
            bool wasAway = Mathf.Abs(m_T - target) > 0.02f;
            m_T = next;
            Pose();
            if (wasAway && Mathf.Abs(m_T - target) <= 0.02f) { if (open) onOpened.Invoke(); else onClosed.Invoke(); }
        }

        bool BlockedByPlayer()
        {
            var p = PlayerMotor.Instance;
            if (p == null) return false;
            var cc = p.GetComponent<CharacterController>();
            Bounds pb = cc.bounds; pb.Expand(0.1f);
            foreach (var c in m_Colliders) if (c != null && !c.isTrigger && c.bounds.Intersects(pb)) return true;
            return false;
        }

        void Pose()
        {
            float e = m_T;   // the spring already gives the motion its ease
            if (kind == Kind.Hinge) leaf.localRotation = m_RestRot * Quaternion.Euler(0f, openAngle * e, 0f);
            else leaf.localPosition = m_RestPos + slideOffset * e;
        }
    }
}
