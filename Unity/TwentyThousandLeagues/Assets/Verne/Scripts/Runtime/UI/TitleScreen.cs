using TMPro;
using UnityEngine;

namespace Verne
{
    /// <summary>
    /// Title: a live in-engine shot with a slow camera drift, the title set left in the serif, and
    /// four quiet options. The excursion entries jump straight to each mission (chapter select).
    /// </summary>
    public class TitleScreen : MonoBehaviour
    {
        public Transform driftCamera;
        public Vector3 driftAmplitude = new Vector3(0.6f, 0.15f, 0.3f);
        public float driftPeriod = 40f;

        MenuList m_Menu;
        TextMeshProUGUI m_Heading;
        CanvasGroup m_Group;
        Vector3 m_CamBase;
        Quaternion m_CamRot;
        float m_Fade;

        void Start()
        {
            VerneInput.LockCursor(false);
            if (driftCamera == null && Camera.main != null) driftCamera = Camera.main.transform;
            if (driftCamera != null) { m_CamBase = driftCamera.position; m_CamRot = driftCamera.rotation; }

            var canvas = VerneUI.CreateCanvas("Title Canvas", 20, transform);
            m_Group = canvas.gameObject.AddComponent<CanvasGroup>();
            m_Group.alpha = 0f;
            var root = canvas.transform;

            // a left-hand reading scrim keeps the type legible over the moving water without a box
            var scrim = VerneUI.Panel(root, "Scrim", new Color(0.04f, 0.045f, 0.06f, 0.55f));
            var sr = scrim.rectTransform; sr.anchorMin = Vector2.zero; sr.anchorMax = new Vector2(0.48f, 1f); sr.offsetMin = sr.offsetMax = Vector2.zero;

            var kicker = VerneUI.Text(root, "Kicker", "Jules Verne · 1870", 28, VerneUI.CapsFont, TextAlignmentOptions.TopLeft, VerneUI.PaperDim);
            Place(kicker.rectTransform, 160, 150, 900, 40);
            var title = VerneUI.Text(root, "Title", "Twenty Thousand\nLeagues Under\nthe Sea", 104, VerneUI.BoldFont, TextAlignmentOptions.TopLeft);
            title.lineSpacing = -22f;
            title.characterSpacing = -2f;
            Place(title.rectTransform, 160, 196, 1000, 330);
            VerneUI.Hairline(root, new Vector2(160, -556), 120, VerneUI.Accent);
            m_Heading = VerneUI.Text(root, "Chapter", "Chapter One", 30, VerneUI.CapsFont, TextAlignmentOptions.TopLeft, VerneUI.PaperDim);
            Place(m_Heading.rectTransform, 160, 578, 600, 40);

            m_Menu = MenuList.Create(root, new Vector2(160, -650), 700f);
            m_Menu.rowHeight = 58f; m_Menu.labelSize = 38f;
            ShowMain();

            var credit = VerneUI.Text(root, "Credit", "Engravings by Alphonse de Neuville and Édouard Riou, 1871", 22, VerneUI.ItalicFont, TextAlignmentOptions.BottomLeft, VerneUI.PaperDim);
            var cr = credit.rectTransform; cr.anchorMin = cr.anchorMax = Vector2.zero; cr.pivot = Vector2.zero; cr.anchoredPosition = new Vector2(160, 64); cr.sizeDelta = new Vector2(1000, 30);
        }

        static void Place(RectTransform r, float x, float top, float w, float h)
        {
            r.anchorMin = r.anchorMax = new Vector2(0, 1); r.pivot = new Vector2(0, 1);
            r.anchoredPosition = new Vector2(x, -top); r.sizeDelta = new Vector2(w, h);
        }

        void ShowMain()
        {
            m_Heading.text = "Chapter One";
            m_Menu.Clear();
            m_Menu.Add("Begin aboard the Nautilus", () => SceneFlow.Load(SceneFlow.Nautilus));
            m_Menu.Add("The forest of Crespo", () => SceneFlow.Load(SceneFlow.Mission1));
            m_Menu.Add("A vanished continent", () => SceneFlow.Load(SceneFlow.Mission2));
            m_Menu.Add("Settings", ShowSettings);
            m_Menu.Add("Quit", Application.Quit);
            m_Menu.onCancel = null;
        }

        void ShowSettings()
        {
            m_Heading.text = "Settings";
            SettingsMenu.Populate(m_Menu, ShowMain);
        }

        void Update()
        {
            m_Fade = Mathf.MoveTowards(m_Fade, 1f, Time.unscaledDeltaTime / 1.2f);
            m_Group.alpha = VerneUI.EaseOut(m_Fade);
            if (driftCamera == null) return;
            float t = Time.time * Mathf.PI * 2f / driftPeriod;
            driftCamera.position = m_CamBase + new Vector3(Mathf.Sin(t) * driftAmplitude.x, Mathf.Sin(t * 0.7f) * driftAmplitude.y, Mathf.Cos(t * 0.5f) * driftAmplitude.z);
            driftCamera.rotation = m_CamRot * Quaternion.Euler(Mathf.Sin(t * 0.6f) * 0.8f, Mathf.Sin(t * 0.4f) * 1.5f, 0f);
        }
    }
}
