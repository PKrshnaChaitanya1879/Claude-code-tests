using UnityEngine;
using UnityEngine.SceneManagement;

namespace Verne
{
    /// <summary>
    /// The Ruhmkorff lamp hanging from the belt (I.XIV-XV): "a Bunsen pile ... a particularly made lantern
    /// ... giving out a white and continuous light", lit "by turning a screw" (L / right shoulder). A spot
    /// from the belt, a little warm, registered as a hero light so its beam is ray-marched through the water
    /// and the motes light up in it; colour comes alive where it lands (red returns to the coral).
    /// Carried on the first excursion only: "They will be useless" (II.IX).
    /// </summary>
    public class RuhmkorffLamp : MonoBehaviour
    {
        public float intensity = 9f, range = 18f, angle = 38f;
        Light m_Light;
        bool m_On;
        AudioClip m_Click;

        public static bool Carried =>
            SceneManager.GetActiveScene().name == SceneFlow.Mission1 ||
            (SceneManager.GetActiveScene().name == SceneFlow.Nautilus && SuitStation.HasLamp);

        void Start()
        {
            var go = new GameObject("Ruhmkorff lamp");
            go.transform.SetParent(transform, false);
            go.transform.localPosition = new Vector3(0.12f, -0.55f, 0.18f);     // at the belt, a little to the right
            go.transform.localRotation = Quaternion.Euler(8f, 0f, 0f);
            m_Light = go.AddComponent<Light>();
            m_Light.type = LightType.Spot; m_Light.range = range; m_Light.spotAngle = angle; m_Light.innerSpotAngle = angle * 0.72f;
            m_Light.color = new Color(0.86f, 0.94f, 1f); m_Light.intensity = intensity;
            m_Light.shadows = LightShadows.None;    // one shadowed light per area: the sun keeps it
            m_Light.enabled = false;
            go.AddComponent<LampBounce>();          // the sand throws a little of the beam back (Playdead's bounce)
            m_Click = Resources.Load<AudioClip>("VerneAudio/sfx/valve_squeak");
        }

        void Update()
        {
            if (m_Light == null) return;
            if (!Carried) { if (m_On) Set(false); return; }
            if (VerneInput.LampDown) { Set(!m_On); if (m_Click != null) VerneAudio.PlayAt(m_Click, transform.position, 0.35f); }
        }

        void Set(bool on)
        {
            m_On = on;
            m_Light.enabled = on;
            var w = VerneWater.Active;
            if (w != null)
            {
                if (on && !w.heroLights.Contains(m_Light)) w.heroLights.Insert(0, m_Light);
                if (!on) w.heroLights.Remove(m_Light);
            }
            if (on) Hud.Toast("I turned the screw of the Ruhmkorff lamp: a white and continuous light.", 3f);
        }
    }
}
