using UnityEngine;

namespace Verne
{
    /// <summary>
    /// Pause: the world freezes and dims (a cheap scrim; no blur on the target laptop), and a quiet
    /// left-aligned menu appears. Transitions take 200 ms.
    /// </summary>
    public class PauseMenu : MonoBehaviour
    {
        public static PauseMenu Instance { get; private set; }
        public static bool Paused { get; private set; }

        Canvas m_Canvas;
        CanvasGroup m_Group;
        MenuList m_Menu;
        TMPro.TextMeshProUGUI m_Heading;
        float m_PrevTimeScale = 1f;
        int m_ClosedFrame = -10;

        public static PauseMenu Ensure()
        {
            if (Instance != null) return Instance;
            var go = new GameObject("Pause Menu");
            DontDestroyOnLoad(go);
            return go.AddComponent<PauseMenu>();
        }

        void Awake()
        {
            if (Instance != null && Instance != this) { Destroy(gameObject); return; }
            Instance = this;
            m_Canvas = VerneUI.CreateCanvas("Pause Canvas", 30, transform);
            m_Group = m_Canvas.gameObject.AddComponent<CanvasGroup>();
            var scrim = VerneUI.Panel(m_Canvas.transform, "Scrim", VerneUI.Scrim);
            var sr = scrim.rectTransform; sr.anchorMin = Vector2.zero; sr.anchorMax = Vector2.one; sr.offsetMin = sr.offsetMax = Vector2.zero;
            m_Heading = VerneUI.Text(m_Canvas.transform, "Heading", "Paused", 30, VerneUI.CapsFont, TMPro.TextAlignmentOptions.TopLeft, VerneUI.PaperDim);
            var hr = m_Heading.rectTransform; hr.anchorMin = hr.anchorMax = new Vector2(0, 1); hr.pivot = new Vector2(0, 1); hr.anchoredPosition = new Vector2(160, -150); hr.sizeDelta = new Vector2(800, 40);
            VerneUI.Hairline(m_Canvas.transform, new Vector2(160, -196), 120, VerneUI.Accent);
            m_Menu = MenuList.Create(m_Canvas.transform, new Vector2(160, -236));
            m_Canvas.enabled = false;
            m_Group.alpha = 0f;
            m_Menu.enabled = false;
        }

        void Update()
        {
            if (!Paused && Time.frameCount > m_ClosedFrame + 1 && VerneInput.PauseDown && !ReadingCard.IsOpen && SceneFlow.InGameplay) Open();
            float dt = Time.unscaledDeltaTime;
            m_Group.alpha = Mathf.MoveTowards(m_Group.alpha, Paused ? 1f : 0f, dt / 0.2f);
            if (!Paused && m_Group.alpha <= 0f && m_Canvas.enabled) m_Canvas.enabled = false;
        }

        public void Open()
        {
            Paused = true;
            m_Menu.enabled = true;
            m_Canvas.enabled = true;
            m_PrevTimeScale = Time.timeScale;
            Time.timeScale = 0f;
            AudioListener.pause = true;
            VerneInput.GameplayBlocked = true;
            VerneInput.LockCursor(false);
            ShowMain();
        }

        public void Close()
        {
            Paused = false;
            m_ClosedFrame = Time.frameCount;
            m_Menu.enabled = false;
            Time.timeScale = m_PrevTimeScale <= 0f ? 1f : m_PrevTimeScale;
            AudioListener.pause = false;
            VerneInput.GameplayBlocked = false;
            VerneInput.LockCursor(true);
        }

        void ShowMain()
        {
            m_Heading.text = "Paused";
            m_Menu.Clear();
            m_Menu.Add("Continue", Close);
            m_Menu.Add("Settings", ShowSettings);
            m_Menu.Add("Return to the title", () => { Close(); SceneFlow.Load(SceneFlow.Title); });
            m_Menu.Add("Quit", () => { Close(); Application.Quit(); });
            m_Menu.onCancel = Close;
        }

        void ShowSettings()
        {
            m_Heading.text = "Settings";
            SettingsMenu.Populate(m_Menu, ShowMain);
        }
    }
}
