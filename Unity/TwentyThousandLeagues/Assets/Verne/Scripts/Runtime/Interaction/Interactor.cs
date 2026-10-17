using UnityEngine;

namespace Verne
{
    /// <summary>
    /// Lives on the player camera. Finds what the player is looking at, shows the prompt, and
    /// drives press/hold/release. While a look-capturing control (lever, wheel) is held, the mouse
    /// moves the control instead of the view.
    /// </summary>
    public class Interactor : MonoBehaviour
    {
        public float maxReach = 2.6f;
        public float probeRadius = 0.06f;
        public LayerMask mask = ~0;

        public static Interactor Instance { get; private set; }
        public Interactable Focused { get; private set; }
        public Interactable Held { get; private set; }
        public float HoldTime { get; private set; }

        PlayerMotor m_Motor;
        readonly RaycastHit[] m_Hits = new RaycastHit[8];

        void Awake()
        {
            Instance = this;
            m_Motor = GetComponentInParent<PlayerMotor>();
        }

        void OnDestroy() { if (Instance == this) Instance = null; }

        void Update()
        {
            if (Held != null)
            {
                bool stillLooking = Held.interactable && Vector3.Distance(transform.position, Held.transform.position) < Held.reach + 0.8f;
                if (!VerneInput.InteractHeld || !stillLooking)
                {
                    Release();
                }
                else
                {
                    HoldTime += Time.deltaTime;
                    Vector2 look = Vector2.zero;
                    if (Held.CapturesLook)
                    {
                        // raw look delta, unaffected by invert-Y so "push up" always pushes the control up
                        look = new Vector2(Input.GetAxisRaw("Mouse X"), Input.GetAxisRaw("Mouse Y")) * GameSettings.Current.mouseSensitivity;
                        look += VerneInput.Move * (Time.deltaTime * 6f);
                    }
                    Held.Hold(this, look, Time.deltaTime);
                }
                return;
            }

            Interactable best = Probe();
            if (best != Focused)
            {
                if (Focused != null) Focused.SetFocused(false);
                Focused = best;
                if (Focused != null) Focused.SetFocused(true);
            }

            if (Focused != null && VerneInput.InteractDown)
            {
                Held = Focused;
                HoldTime = 0f;
                if (Held.CapturesLook && m_Motor != null) { m_Motor.LookLocked = true; m_Motor.MovementLocked = true; }
                Held.Begin(this);
            }
        }

        void Release()
        {
            var h = Held;
            Held = null;
            if (m_Motor != null) { m_Motor.LookLocked = false; m_Motor.MovementLocked = false; }
            if (h != null) h.End(this);
        }

        Interactable Probe()
        {
            var ray = new Ray(transform.position, transform.forward);
            int n = Physics.SphereCastNonAlloc(ray, probeRadius, m_Hits, maxReach, mask, QueryTriggerInteraction.Collide);
            float bestDist = float.MaxValue;
            Interactable best = null;
            float blocker = float.MaxValue;
            // nearest solid, non-interactable surface blocks anything behind it
            for (int i = 0; i < n; i++)
            {
                var h = m_Hits[i];
                if (h.collider.isTrigger) continue;
                if (h.collider.GetComponentInParent<PlayerMotor>() != null) continue;
                if (h.collider.GetComponentInParent<Interactable>() == null && h.distance < blocker) blocker = h.distance;
            }
            for (int i = 0; i < n; i++)
            {
                var h = m_Hits[i];
                var it = h.collider.GetComponentInParent<Interactable>();
                if (it == null || !it.interactable || !it.isActiveAndEnabled) continue;
                if (h.distance > it.reach || h.distance > blocker + 0.02f) continue;
                if (h.distance < bestDist) { bestDist = h.distance; best = it; }
            }
            return best;
        }
    }
}
