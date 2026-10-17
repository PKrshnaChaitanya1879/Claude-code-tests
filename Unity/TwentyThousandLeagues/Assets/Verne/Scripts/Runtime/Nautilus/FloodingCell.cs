using System.Collections;
using UnityEngine;

namespace Verne
{
    /// <summary>
    /// The flooding cell, as the book tells it (I.XV): the water-tight inner door with its stopper
    /// plates closes; a tap admits the sea with a loud hiss, the cold rising from the feet to the
    /// chest; when the cell is full and the pressures are equal, the second door in the hull can
    /// be opened onto a faint light.
    /// Iron Lung rules: everything is a physical control, nothing happens by itself.
    /// </summary>
    public class FloodingCell : MonoBehaviour
    {
        public Door innerDoor;
        public Door outerDoor;
        public Valve floodTap;
        public PushButton pumpKnob;
        public Gauge pressureGauge;          // atmospheres
        public Transform waterSurface;       // a plane that rises with the level
        public float floorY = 0f, ceilingY = 2.3f;
        public float outsideDepth = 9f;      // metres of sea outside (five fathoms at Crespo)
        public float fillSeconds = 14f;      // with the tap fully open
        public AudioSource hissLoop, gurgleLoop;

        [Tooltip("World-space volume of the cell (set by the bootstrap).")]
        public Bounds volume = new Bounds(Vector3.zero, new Vector3(3f, 2.4f, 2.5f));
        [Range(0, 1)] public float level;
        bool m_Draining;

        public float OutsidePressure => 1f + outsideDepth / 10.06f;   // atm, sea water
        public bool Full => level >= 0.999f;

        void Start()
        {
            if (outerDoor != null) { outerDoor.locked = true; outerDoor.lockedMessage = "The sea presses on it. The cell must be flooded first."; }
            if (floodTap != null) floodTap.interactable = innerDoor == null || !innerDoor.open;
            if (pumpKnob != null) pumpKnob.onUsed.AddListener(() => { if (outerDoor == null || !outerDoor.open) m_Draining = true; });
            UpdateVisuals();
        }

        void Update()
        {
            bool sealedIn = innerDoor == null || (!innerDoor.open && !innerDoor.IsHeld);
            if (innerDoor != null) innerDoor.locked = level > 0.02f;           // the sea holds it shut
            if (floodTap != null) floodTap.interactable = sealedIn && !m_Draining;

            float rate = 0f;
            if (floodTap != null && sealedIn && !m_Draining) rate = floodTap.openness / fillSeconds;
            if (m_Draining) rate = -1f / (fillSeconds * 0.7f);
            float prev = level;
            level = Mathf.Clamp01(level + rate * Time.deltaTime);
            if (m_Draining && level <= 0f) { m_Draining = false; if (floodTap != null) floodTap.Set(0f); }

            if (outerDoor != null) outerDoor.locked = !Full;
            if (prev < 0.999f && Full) Hud.Toast("The pressures are equal. The outer door will open now.");

            // the player feels it: underwater movement once the water is over the chest
            var p = PlayerMotor.Instance;
            if (p != null && p.mode != MoveMode.Air && IsInside(p.transform.position))
                p.SetMode(level > 0.55f ? MoveMode.Water : MoveMode.Suited);

            UpdateVisuals();
            UpdateAudio(rate);
        }

        bool IsInside(Vector3 pos)
        {
            var b = volume; b.Expand(0.2f);
            return b.Contains(pos + Vector3.up * 0.5f);
        }

        void UpdateVisuals()
        {
            if (waterSurface != null)
            {
                waterSurface.gameObject.SetActive(level > 0.005f);
                var lp = waterSurface.position; lp.y = Mathf.Lerp(floorY, ceilingY, level); waterSurface.position = lp;
            }
            if (pressureGauge != null) pressureGauge.target = Mathf.Lerp(1f, OutsidePressure, level);
        }

        void UpdateAudio(float rate)
        {
            if (hissLoop != null)
            {
                float target = rate > 0f ? Mathf.Lerp(0.2f, 0.9f, floodTap != null ? floodTap.openness : 1f) * (1f - level * 0.6f) : 0f;
                hissLoop.volume = Mathf.MoveTowards(hissLoop.volume, target, Time.deltaTime * 2f);
                if (hissLoop.volume > 0.01f && !hissLoop.isPlaying) hissLoop.Play();
                if (hissLoop.volume <= 0.01f && hissLoop.isPlaying) hissLoop.Stop();
            }
            if (gurgleLoop != null)
            {
                float target = Mathf.Abs(rate) > 0f ? 0.6f : 0f;
                gurgleLoop.volume = Mathf.MoveTowards(gurgleLoop.volume, target, Time.deltaTime);
                gurgleLoop.pitch = Mathf.Lerp(0.8f, 1.25f, level);   // the cavity above the water shrinks, the gurgle rises
                if (gurgleLoop.volume > 0.01f && !gurgleLoop.isPlaying) gurgleLoop.Play();
                if (gurgleLoop.volume <= 0.01f && gurgleLoop.isPlaying) gurgleLoop.Stop();
            }
        }
    }
}
