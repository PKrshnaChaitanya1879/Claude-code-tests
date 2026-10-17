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
        [Tooltip("The hand-wheel that drives the stopper-plates home on the inner door. Dogged = 1.")]
        public Valve dogs;
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
        bool m_ToldCold, m_ToldChest, m_ToldDress, m_ToldDogs;
        CanvasGroup m_Under;
        float m_TellCooldown;

        public float OutsidePressure => 1f + outsideDepth / 10.06f;   // atm, sea water
        public bool Full => level >= 0.999f;

        void Start()
        {
            if (hissLoop == null) hissLoop = MakeLoop("VerneAudio/loops/cell_hiss");
            if (gurgleLoop == null) gurgleLoop = MakeLoop("VerneAudio/loops/cell_gurgle");
            if (outerDoor != null) { outerDoor.locked = true; outerDoor.lockedMessage = "The sea presses on it. The cell must be flooded first."; }
            if (floodTap != null) floodTap.interactable = innerDoor == null || !innerDoor.open;
            if (pumpKnob != null) pumpKnob.onUsed.AddListener(() => { if (outerDoor == null || !outerDoor.open) m_Draining = true; });
            if (dogs != null) { dogs.bidirectional = true; dogs.verbOpen = "Dog"; dogs.verbClose = "Undog"; }
            if (pressureGauge != null) pressureGauge.maxValue = Mathf.Max(4f, Mathf.Ceil(OutsidePressure / 5f) * 5f);
            BuildUnderwaterTint();
            UpdateVisuals();
        }

        void Update()
        {
            bool doorShut = innerDoor == null || (!innerDoor.open && !innerDoor.IsHeld);
            bool dogged = dogs == null || dogs.openness >= 0.98f;
            bool sealedIn = doorShut && dogged;
            if (innerDoor != null)
            {
                innerDoor.locked = level > 0.02f || (dogs != null && dogs.openness > 0.02f);   // the sea, or the stopper-plates, hold it shut
                innerDoor.lockedMessage = level > 0.02f ? "The sea presses on it. Pump the cell out first." : "The stopper-plates are home. Turn the wheel back first.";
            }
            if (dogs != null) dogs.interactable = doorShut && level < 0.02f;
            if (floodTap != null) floodTap.interactable = sealedIn && !m_Draining;

            // Iron Lung rules: the controls answer, but the sea does not come in on an unready man
            bool dressed = SuitStation.Dressed || PlayerMotor.Instance == null || !IsInside(PlayerMotor.Instance.transform.position);
            m_TellCooldown -= Time.deltaTime;
            if (floodTap != null && floodTap.IsHeld && !dressed && m_TellCooldown <= 0f) { Hud.Toast("Not without the diving-dress and its helmet."); m_TellCooldown = 4f; }
            if (floodTap != null && !floodTap.interactable && floodTap.IsHeld == false && !dogged && doorShut && !m_ToldDogs && PlayerInside()) { m_ToldDogs = true; Hud.Toast("The water-tight door, furnished with stopper-plates: turn the wheel to drive them home."); }

            float rate = 0f;
            if (floodTap != null && sealedIn && !m_Draining && dressed) rate = floodTap.openness / fillSeconds;
            if (m_Draining) rate = -1f / (fillSeconds * 0.7f);
            float prev = level;
            level = Mathf.Clamp01(level + rate * Time.deltaTime);
            if (m_Draining && level <= 0f) { m_Draining = false; if (floodTap != null) floodTap.Set(0f); }

            if (outerDoor != null) outerDoor.locked = !Full;
            if (prev < 0.999f && Full) Hud.Toast("A second door cut in the side of the Nautilus can open now. The pressures are equal.");
            if (rate > 0f && level > 0.08f && !m_ToldCold) { m_ToldCold = true; Hud.Toast("A loud hissing. I felt the cold mount from my feet to my chest.", 4f); }
            if (rate > 0f && level > 0.6f && !m_ToldChest) { m_ToldChest = true; Hud.Toast("The water rose over the glass of the helmet.", 3f); }

            // the player feels it: underwater movement once the water is over the chest
            var p = PlayerMotor.Instance;
            if (p != null && p.mode != MoveMode.Air && IsInside(p.transform.position))
                p.SetMode(level > 0.55f ? MoveMode.Water : MoveMode.Suited);

            UpdateVisuals();
            UpdateTint();
            UpdateAudio(rate);
        }

        AudioSource MakeLoop(string res)
        {
            var clip = Resources.Load<AudioClip>(res);
            if (clip == null) return null;
            var go = new GameObject(clip.name);
            go.transform.SetParent(transform, false);
            go.transform.position = volume.center;
            var a = go.AddComponent<AudioSource>();
            a.clip = clip; a.loop = true; a.volume = 0f; a.spatialBlend = 0.8f; a.minDistance = 1.5f; a.maxDistance = 15f; a.playOnAwake = false;
            return a;
        }

        bool PlayerInside() => PlayerMotor.Instance != null && IsInside(PlayerMotor.Instance.transform.position);

        /// <summary>A cold green veil while the eye is under the cell's water (the M3 water model takes over outside).</summary>
        void BuildUnderwaterTint()
        {
            var canvas = VerneUI.CreateCanvas("Cell water tint", 5, transform);
            m_Under = canvas.gameObject.AddComponent<CanvasGroup>();
            m_Under.alpha = 0f; m_Under.blocksRaycasts = false; m_Under.interactable = false;
            var img = VerneUI.Panel(canvas.transform, "Tint", new Color(0.05f, 0.22f, 0.24f, 0.55f));
            var r = img.rectTransform; r.anchorMin = Vector2.zero; r.anchorMax = Vector2.one; r.offsetMin = r.offsetMax = Vector2.zero;
            img.raycastTarget = false;
        }

        void UpdateTint()
        {
            if (m_Under == null) return;
            var cam = Camera.main;
            float target = 0f;
            if (cam != null && level > 0.005f && IsInside(cam.transform.position - Vector3.up * 0.5f))
                target = cam.transform.position.y < Mathf.Lerp(floorY, ceilingY, level) ? 1f : 0f;
            m_Under.alpha = Mathf.MoveTowards(m_Under.alpha, target, Time.deltaTime * 3f);
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
