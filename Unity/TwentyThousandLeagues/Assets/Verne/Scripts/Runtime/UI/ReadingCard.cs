using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace Verne
{
    /// <summary>
    /// Full-screen reading view for notes and books (Nemo's invitations). The world dims behind a
    /// scrim; text sits in a single left column at a comfortable measure. Any confirm closes it.
    /// </summary>
    public class ReadingCard : MonoBehaviour
    {
        static ReadingCard s_Instance;
        Canvas m_Canvas;
        CanvasGroup m_Group;
        TextMeshProUGUI m_Title, m_Body, m_Sign, m_Hint;
        RawImage m_Image; AspectRatioFitter m_Fit; RectTransform m_Col, m_Frame;
        bool m_Open;
        float m_OpenedAt;

        public static bool IsOpen => s_Instance != null && s_Instance.m_Open;

        static ReadingCard Ensure()
        {
            if (s_Instance != null) return s_Instance;
            var go = new GameObject("Reading Card");
            DontDestroyOnLoad(go);
            s_Instance = go.AddComponent<ReadingCard>();
            s_Instance.Build();
            return s_Instance;
        }

        void Build()
        {
            m_Canvas = VerneUI.CreateCanvas("Reading Canvas", 40, transform);
            m_Group = m_Canvas.gameObject.AddComponent<CanvasGroup>();
            m_Group.alpha = 0f;
            var scrim = VerneUI.Panel(m_Canvas.transform, "Scrim", new Color(0.04f, 0.045f, 0.06f, 0.86f));
            var sr = scrim.rectTransform; sr.anchorMin = Vector2.zero; sr.anchorMax = Vector2.one; sr.offsetMin = sr.offsetMax = Vector2.zero;

            // the picture, large, on the left; the words beside it (only when there is a picture)
            // the left half of the screen (whatever its shape): the picture keeps its own proportions inside it,
            // in a thin gilt frame on a dark mount, like a canvas in the saloon (GUM: "horrible ratio")
            m_Frame = VerneUI.Rect("Picture area", m_Canvas.transform, new Vector2(0.04f, 0.08f), new Vector2(0.54f, 0.92f), new Vector2(0.5f, 0.5f), Vector2.zero, Vector2.zero);
            var fit = VerneUI.Rect("Framed", m_Frame, new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), new Vector2(0.5f, 0.5f), Vector2.zero, new Vector2(100, 100));
            m_Fit = fit.gameObject.AddComponent<AspectRatioFitter>(); m_Fit.aspectMode = AspectRatioFitter.AspectMode.FitInParent;
            var gilt = fit.gameObject.AddComponent<Image>(); gilt.color = new Color(0.62f, 0.47f, 0.22f, 1f);
            var mount = VerneUI.Rect("Mount", fit, Vector2.zero, Vector2.one, new Vector2(0.5f, 0.5f), Vector2.zero, Vector2.zero);
            mount.offsetMin = new Vector2(6, 6); mount.offsetMax = new Vector2(-6, -6);
            mount.gameObject.AddComponent<Image>().color = new Color(0.05f, 0.04f, 0.035f, 1f);
            var img = VerneUI.Rect("Image", mount, Vector2.zero, Vector2.one, new Vector2(0.5f, 0.5f), Vector2.zero, Vector2.zero);
            img.offsetMin = new Vector2(10, 10); img.offsetMax = new Vector2(-10, -10);
            m_Image = img.gameObject.AddComponent<RawImage>();
            m_Frame.gameObject.SetActive(false);
            var col = VerneUI.Rect("Column", m_Canvas.transform, new Vector2(0, 0.5f), new Vector2(0, 0.5f), new Vector2(0, 0.5f), new Vector2(240, 0), new Vector2(1020, 820));
            m_Col = col;
            m_Title = VerneUI.Text(col, "Title", "", 56, VerneUI.BoldFont, TextAlignmentOptions.TopLeft);
            Place(m_Title.rectTransform, 0, 90);
            VerneUI.Hairline(col, new Vector2(0, -104), 120, VerneUI.Accent);
            m_Body = VerneUI.Text(col, "Body", "", 36, VerneUI.TextFont, TextAlignmentOptions.TopLeft);
            m_Body.lineSpacing = 18f;
            Place(m_Body.rectTransform, 136, 560);
            m_Sign = VerneUI.Text(col, "Signature", "", 34, VerneUI.ItalicFont, TextAlignmentOptions.TopLeft, VerneUI.PaperDim);
            Place(m_Sign.rectTransform, 710, 60);
            m_Hint = VerneUI.Text(m_Canvas.transform, "Hint", "", 24, VerneUI.CapsFont, TextAlignmentOptions.BottomLeft, VerneUI.PaperDim);
            var hr = m_Hint.rectTransform; hr.anchorMin = hr.anchorMax = Vector2.zero; hr.pivot = Vector2.zero; hr.anchoredPosition = new Vector2(240, 80); hr.sizeDelta = new Vector2(800, 40);
            m_Canvas.enabled = false;
        }

        static void Place(RectTransform r, float top, float height)
        {
            r.anchorMin = new Vector2(0, 1); r.anchorMax = new Vector2(1, 1); r.pivot = new Vector2(0, 1);
            r.anchoredPosition = new Vector2(0, -top); r.sizeDelta = new Vector2(0, height);
        }

        public static void Show(string title, string body, string signature) => Show(title, body, signature, null);

        public static void Show(string title, string body, string signature, Texture image)
        {
            var c = Ensure();
            bool pic = image != null;
            c.m_Frame.gameObject.SetActive(pic);
            if (pic)
            {
                c.m_Image.texture = image;
                c.m_Fit.aspectRatio = image.height > 0 ? (float)image.width / image.height : 1f;   // the canvas' own proportions inside a 900 px box
            }
            if (pic)
            {   // the words take the right half
                c.m_Col.anchorMin = new Vector2(0.58f, 0.5f); c.m_Col.anchorMax = new Vector2(0.94f, 0.5f);
                c.m_Col.anchoredPosition = Vector2.zero; c.m_Col.sizeDelta = new Vector2(0, 820);
            }
            else
            {
                c.m_Col.anchorMin = c.m_Col.anchorMax = new Vector2(0, 0.5f);
                c.m_Col.anchoredPosition = new Vector2(240, 0); c.m_Col.sizeDelta = new Vector2(1020, 820);
            }
            c.m_Title.text = title ?? "";
            c.m_Body.text = body ?? "";
            c.m_Sign.text = string.IsNullOrEmpty(signature) ? "" : "— " + signature;
            c.m_Hint.text = (VerneInput.UsingGamepad ? "(A)" : "[E]") + "  close";
            c.m_Open = true;
            c.m_OpenedAt = Time.unscaledTime;
            c.m_Canvas.enabled = true;
            VerneInput.GameplayBlocked = true;
        }

        void Update()
        {
            float dt = Time.unscaledDeltaTime;
            m_Group.alpha = Mathf.MoveTowards(m_Group.alpha, m_Open ? 1f : 0f, dt / 0.25f);
            if (!m_Open && m_Group.alpha <= 0f && m_Canvas.enabled) m_Canvas.enabled = false;
            if (m_Open && Time.unscaledTime - m_OpenedAt > 0.3f &&
                (Input.GetKeyDown(KeyCode.E) || Input.GetMouseButtonDown(0) || VerneInput.SubmitDown || VerneInput.CancelDown))
            {
                m_Open = false;
                VerneInput.GameplayBlocked = false;
            }
        }
    }
}
