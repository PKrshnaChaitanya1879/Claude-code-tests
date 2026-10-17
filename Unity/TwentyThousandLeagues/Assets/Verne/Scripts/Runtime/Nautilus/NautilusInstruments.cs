using UnityEngine;

namespace Verne
{
    /// <summary>
    /// Drives Nemo's dials (I.XI) from the ship's state: the manometer reads the depth through the outside
    /// pressure, the speed dial the screw's real speed, and the electric clock, "divided into twenty-four
    /// hours, like the Italian clocks", keeps the player's own time. Iron Lung rule: every needle means something.
    /// </summary>
    public class NautilusInstruments : MonoBehaviour
    {
        public Gauge manometer, clock, speed, barometer;
        [Tooltip("Depth of the keel while under way, metres.")]
        public float cruisingDepth = 50f;
        [Tooltip("Knots, from the screw.")]
        public float knots = 20f;

        void Start()
        {
            if (manometer != null) { manometer.minValue = 0f; manometer.maxValue = 100f; }   // atmospheres of sea
            if (clock != null) { clock.minValue = 0f; clock.maxValue = 24f; clock.minAngle = 0f; clock.maxAngle = 360f; clock.response = 2f; }
            if (speed != null) { speed.minValue = 0f; speed.maxValue = 50f; }
            if (barometer != null) { barometer.minValue = 720f; barometer.maxValue = 790f; }
        }

        void Update()
        {
            // a slow breathing of depth and speed, as a ship under way
            float t = Time.time;
            float depth = Chapter.Excursion >= 2 ? 274f : cruisingDepth;
            if (manometer != null) manometer.target = depth / 10.06f + Mathf.Sin(t * 0.05f) * 0.3f;
            if (speed != null) speed.target = knots + Mathf.Sin(t * 0.11f) * 0.6f;
            if (barometer != null) barometer.target = 760f;
            if (clock != null)
            {
                var now = System.DateTime.Now;
                clock.target = now.Hour + now.Minute / 60f;
            }
        }
    }
}
