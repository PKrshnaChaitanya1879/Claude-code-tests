using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace Verne
{
    /// <summary>
    /// The in-game overlay, kept almost invisible: a tiny aim point, a one-line verb prompt when
    /// something can be operated, quiet toasts, and subtitles. Nothing else (Iron Lung restraint).
    /// </summary>
    public class Hud : MonoBehaviour
    {
        public static Hud Instance { get; private set; }

        Canvas m_Canvas;
        Image m_Dot;
        TextMeshProUGUI m_Prompt, m_Toast, m_Sub, m_SubSpeaker;
        CanvasGroup m_PromptGroup, m_ToastGroup, m_SubGroup;
        float m_ToastTimer, m_SubTimer;
        readonly Queue<(string speaker, string line, float dur)> m_SubQueue = new Queue<(string, string, float)>();
        string m_LastPrompt;

        public static Hud Ensure()
        {
            if (Instance != null) return Instance;
            var go = new GameObject("HUD");
            DontDestroyOnLoad(go);
            return go.AddComponent<Hud>();
        }

        void Awake()
        {
            if (Instance != null && Instance != this) { Destroy(gameObject); return; }
            Instance = this;
            Build();
        }

        void Build()
        {
            m_Canvas = VerneUI.CreateCanvas("HUD Canvas", 10, transform);
            var root = m_Canvas.transform;

            // aim point: 4 px, soft off-white, grows a little and takes the accent on focus
            m_Dot = VerneUI.Panel(root, "Aim", VerneUI.PaperDim);
            var dr = m_Dot.rectTransform; dr.anchorMin = dr.anchorMax = new Vector2(0.5f, 0.5f); dr.sizeDelta = new Vector2(4, 4);

            var pr = VerneUI.Rect("Prompt", root, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0.5f, 1f), new Vector2(0, -34), new Vector2(900, 60));
            m_PromptGroup = pr.gameObject.AddComponent<CanvasGroup>(); m_PromptGroup.alpha = 0;
            m_Prompt = VerneUI.Text(pr, "Text", "", 30, VerneUI.CapsFont, TextAlignmentOptions.Top);
            Stretch(m_Prompt.rectTransform);

            var tr = VerneUI.Rect("Toast", root, new Vector2(0f, 0f), new Vector2(0f, 0f), new Vector2(0f, 0f), new Vector2(96, 96), new Vector2(760, 120));
            m_ToastGroup = tr.gameObject.AddComponent<CanvasGroup>(); m_ToastGroup.alpha = 0;
            m_Toast = VerneUI.Text(tr, "Text", "", 30, VerneUI.ItalicFont, TextAlignmentOptions.BottomLeft);
            Stretch(m_Toast.rectTransform);

            var sr = VerneUI.Rect("Subtitles", root, new Vector2(0.5f, 0f), new Vector2(0.5f, 0f), new Vector2(0.5f, 0f), new Vector2(0, 92), new Vector2(1300, 140));
            m_SubGroup = sr.gameObject.AddComponent<CanvasGroup>(); m_SubGroup.alpha = 0;
            m_SubSpeaker = VerneUI.Text(sr, "Speaker", "", 26, VerneUI.CapsFont, TextAlignmentOptions.Bottom, VerneUI.Accent);
            var spr = m_SubSpeaker.rectTransform; spr.anchorMin = new Vector2(0, 1); spr.anchorMax = new Vector2(1, 1); spr.pivot = new Vector2(0.5f, 0f); spr.anchoredPosition = new Vector2(0, -36); spr.sizeDelta = new Vector2(0, 34);
            m_Sub = VerneUI.Text(sr, "Line", "", 36, VerneUI.TextFont, TextAlignmentOptions.Top);
            var lr = m_Sub.rectTransform; lr.anchorMin = Vector2.zero; lr.anchorMax = new Vector2(1, 1); lr.offsetMin = Vector2.zero; lr.offsetMax = new Vector2(0, -38);
            AddShadow(m_Sub); AddShadow(m_Prompt); AddShadow(m_Toast);
        }

        static void Stretch(RectTransform r) { r.anchorMin = Vector2.zero; r.anchorMax = Vector2.one; r.offsetMin = r.offsetMax = Vector2.zero; }

        static void AddShadow(TextMeshProUGUI t)
        {
            // soft dark underlay via the SDF material: readable over bright water without a box
            var m = t.fontMaterial;
            if (m.HasProperty(ShaderUtilities.ID_UnderlayColor))
            {
                m.EnableKeyword(ShaderUtilities.Keyword_Underlay);
                m.SetColor(ShaderUtilities.ID_UnderlayColor, new Color(0.04f, 0.045f, 0.06f, 0.75f));
                m.SetFloat(ShaderUtilities.ID_UnderlaySoftness, 0.6f);
                m.SetFloat(ShaderUtilities.ID_UnderlayDilate, 0.3f);
            }
        }

        void Update()
        {
            float dt = Time.unscaledDeltaTime;
            var it = Interactor.Instance;
            Interactable focus = it != null ? (it.Held != null ? it.Held : it.Focused) : null;
            bool show = focus != null && !VerneInput.GameplayBlocked;
            string p = show ? Glyph() + "   " + focus.Prompt.ToLowerInvariant() : m_LastPrompt;
            if (show && p != m_LastPrompt) { m_Prompt.text = p; m_LastPrompt = p; }
            m_PromptGroup.alpha = Mathf.MoveTowards(m_PromptGroup.alpha, show ? 1f : 0f, dt * 6f);
            m_Dot.color = Color.Lerp(m_Dot.color, show ? VerneUI.Accent : VerneUI.PaperDim, 1f - Mathf.Exp(-dt * 12f));
            float s = Mathf.Lerp(m_Dot.rectTransform.sizeDelta.x, show ? 6f : 4f, 1f - Mathf.Exp(-dt * 12f));
            m_Dot.rectTransform.sizeDelta = new Vector2(s, s);
            m_Dot.enabled = !VerneInput.GameplayBlocked && Cursor.lockState == CursorLockMode.Locked;

            if (m_ToastTimer > 0f) m_ToastTimer -= dt;
            m_ToastGroup.alpha = Mathf.MoveTowards(m_ToastGroup.alpha, m_ToastTimer > 0f ? 1f : 0f, dt * 2.5f);

            if (m_SubTimer > 0f) m_SubTimer -= dt;
            else if (m_SubQueue.Count > 0)
            {
                var (sp, line, dur) = m_SubQueue.Dequeue();
                m_SubSpeaker.text = sp; m_Sub.text = line; m_SubTimer = dur;
            }
            bool subsOn = GameSettings.Current.subtitles;
            m_SubGroup.alpha = Mathf.MoveTowards(m_SubGroup.alpha, subsOn && m_SubTimer > 0f ? 1f : 0f, dt * 4f);
        }

        static string Glyph() => VerneInput.UsingGamepad ? "(A)" : "[E]";

        public static void Toast(string message, float seconds = 3.5f)
        {
            var h = Ensure();
            h.m_Toast.text = message;
            h.m_ToastTimer = seconds;
        }

        /// <summary>Queue a subtitle line. Duration defaults to reading speed (≈ 15 characters per second, min 2.2 s).</summary>
        public static void Say(string speaker, string line, float seconds = -1f)
        {
            var h = Ensure();
            if (seconds <= 0f) seconds = Mathf.Max(2.2f, line.Length / 15f + 0.8f);
            h.m_SubQueue.Enqueue((speaker ?? "", line, seconds));
        }

        public void SetVisible(bool v) { m_Canvas.enabled = v; }
    }
}
