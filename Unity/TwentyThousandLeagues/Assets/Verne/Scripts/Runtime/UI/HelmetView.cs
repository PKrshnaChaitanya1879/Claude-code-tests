using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;

namespace Verne
{
    /// <summary>
    /// Seeing through the copper helmet's front glass (I.XIV): the port frames the view, Iron Lung style,
    /// and the breath fogs the lower glass with every exhalation of the Rouquayrol (faster when walking
    /// hard, slower at rest). Shown whenever the helmet is on: in the excursions, and aboard once dressed.
    /// Art: Source/tools/helmet_port.py. Sits under the HUD and the reading cards.
    /// </summary>
    public class HelmetView : MonoBehaviour
    {
        static HelmetView s_Instance;
        /// <summary>The breathing cycle (0..1): inhale from 0, exhale from 0.6. Ambience plays the Rouquayrol on it.</summary>
        public static float BreathPhase { get; private set; }
        public static bool On { get; private set; }
        public static event System.Action Inhale, Exhale;
        CanvasGroup m_Group;
        RawImage m_Fog;
        float m_Breath;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Boot()
        {
            if (s_Instance != null) return;
            var go = new GameObject("Helmet View");
            DontDestroyOnLoad(go);
            s_Instance = go.AddComponent<HelmetView>();
        }

        void Awake()
        {
            var canvas = VerneUI.CreateCanvas("Helmet Canvas", 2, transform);
            canvas.GetComponent<GraphicRaycaster>().enabled = false;
            m_Group = canvas.gameObject.AddComponent<CanvasGroup>();
            m_Group.alpha = 0f; m_Group.blocksRaycasts = false; m_Group.interactable = false;
            m_Fog = Layer(canvas.transform, "Breath fog", Resources.Load<Texture2D>("VerneUI/helmet_fog"));
            Layer(canvas.transform, "Port", Resources.Load<Texture2D>("VerneUI/helmet_port"));
        }

        static RawImage Layer(Transform parent, string name, Texture2D tex)
        {
            var go = new GameObject(name, typeof(RectTransform), typeof(RawImage));
            go.transform.SetParent(parent, false);
            var r = (RectTransform)go.transform;
            r.anchorMin = Vector2.zero; r.anchorMax = Vector2.one; r.offsetMin = r.offsetMax = Vector2.zero;
            var img = go.GetComponent<RawImage>();
            img.texture = tex; img.raycastTarget = false;
            if (tex == null) img.enabled = false;
            return img;
        }

        static bool HelmetOn()
        {
            var p = PlayerMotor.Instance;
            if (p == null || p.mode == MoveMode.Air || !SceneFlow.InGameplay) return false;
            return SceneManager.GetActiveScene().name != SceneFlow.Nautilus || SuitStation.Dressed;
        }

        void Update()
        {
            On = HelmetOn();
            float target = On ? 1f : 0f;
            m_Group.alpha = Mathf.MoveTowards(m_Group.alpha, target, Time.unscaledDeltaTime / 0.45f);
            if (m_Group.alpha <= 0f || m_Fog == null) return;
            var p = PlayerMotor.Instance;
            float exertion = p != null ? Mathf.Clamp01(p.SpeedNormalized) : 0f;
            m_Breath += Time.deltaTime / Mathf.Lerp(4.6f, 2.6f, exertion);         // seconds per breath
            float phase = Mathf.Repeat(m_Breath, 1f);
            if (On && BreathPhase < 0.6f && phase >= 0.6f) Exhale?.Invoke();
            if (On && phase < BreathPhase) Inhale?.Invoke();
            BreathPhase = phase;
            // exhale over the last 40% of the cycle: the fog blooms quickly and clears slowly
            float fog = phase > 0.6f ? Mathf.SmoothStep(0f, 1f, (phase - 0.6f) / 0.15f) : Mathf.Clamp01(1f - phase / 0.55f) * 0.9f;
            var c = m_Fog.color; c.a = fog * Mathf.Lerp(0.55f, 0.9f, exertion); m_Fog.color = c;
        }
    }
}
