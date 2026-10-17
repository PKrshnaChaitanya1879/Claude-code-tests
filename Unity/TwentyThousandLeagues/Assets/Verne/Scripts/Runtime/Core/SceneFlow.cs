using System.Collections;
using TMPro;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;

namespace Verne
{
    /// <summary>
    /// Scene changes behind a loading card: an original 1871 engraving with a line from the book,
    /// as in the prototype. Cards live in Resources/VerneCards (copied from reference/illustrations).
    /// </summary>
    public class SceneFlow : MonoBehaviour
    {
        public const string Title = "Title";
        public const string Nautilus = "Nautilus";
        public const string Mission1 = "Mission1";
        public const string Mission2 = "Mission2";

        public struct Card { public string image, quote, cite; }

        static SceneFlow s_Instance;
        Canvas m_Canvas;
        CanvasGroup m_Group;
        RawImage m_Image;
        AspectRatioFitter m_Fit;
        TextMeshProUGUI m_Quote, m_Cite;
        bool m_Busy;

        /// <summary>True while a gameplay scene (not the title or a loading card) is active.</summary>
        public static bool InGameplay => !(s_Instance != null && s_Instance.m_Busy) && SceneManager.GetActiveScene().name != Title;

        public static Card CardFor(string scene)
        {
            switch (scene)
            {
                case Mission1: return new Card { image = "im034", quote = "Words are impotent to relate such wonders!", cite = "Part I, Chapter XV" };
                case Mission2: return new Card { image = "im077", quote = "Branches, like fine black paper cuttings, showed distinctly on the watery ceiling.", cite = "Part II, Chapter IX" };
                case Nautilus: return new Card { image = "im022", quote = "It was no longer luminous water, but liquid light.", cite = "Part I, Chapter XIII" };
                default: return new Card { image = "im014", quote = "Mobilis in Mobili.", cite = "Part I, Chapter VIII" };
            }
        }

        static SceneFlow Ensure()
        {
            if (s_Instance != null) return s_Instance;
            var go = new GameObject("Scene Flow");
            DontDestroyOnLoad(go);
            s_Instance = go.AddComponent<SceneFlow>();
            s_Instance.Build();
            return s_Instance;
        }

        void Build()
        {
            m_Canvas = VerneUI.CreateCanvas("Loading Canvas", 100, transform);
            m_Group = m_Canvas.gameObject.AddComponent<CanvasGroup>();
            var bg = VerneUI.Panel(m_Canvas.transform, "Ink", VerneUI.Ink);
            var br = bg.rectTransform; br.anchorMin = Vector2.zero; br.anchorMax = Vector2.one; br.offsetMin = br.offsetMax = Vector2.zero;

            // engraving on the left two-thirds of the height, shown uncovered
            var frame = VerneUI.Rect("Engraving", m_Canvas.transform, new Vector2(0, 0.5f), new Vector2(0, 0.5f), new Vector2(0, 0.5f), new Vector2(200, 0), new Vector2(620, 860));
            var imgGo = new GameObject("Image", typeof(RectTransform), typeof(RawImage), typeof(AspectRatioFitter));
            imgGo.transform.SetParent(frame, false);
            m_Image = imgGo.GetComponent<RawImage>();
            m_Fit = imgGo.GetComponent<AspectRatioFitter>();
            m_Fit.aspectMode = AspectRatioFitter.AspectMode.FitInParent;
            m_Image.color = new Color(0.86f, 0.84f, 0.8f, 1f); // printed paper, slightly dimmed against the dark

            var col = VerneUI.Rect("Quote", m_Canvas.transform, new Vector2(0, 0.5f), new Vector2(0, 0.5f), new Vector2(0, 0.5f), new Vector2(940, -40), new Vector2(780, 400));
            m_Quote = VerneUI.Text(col, "Text", "", 52, VerneUI.ItalicFont, TextAlignmentOptions.BottomLeft);
            var qr = m_Quote.rectTransform; qr.anchorMin = new Vector2(0, 0.3f); qr.anchorMax = Vector2.one; qr.offsetMin = qr.offsetMax = Vector2.zero;
            m_Quote.lineSpacing = -6f;
            VerneUI.Hairline(col, new Vector2(0, -292), 120, VerneUI.Accent);
            m_Cite = VerneUI.Text(col, "Cite", "", 26, VerneUI.CapsFont, TextAlignmentOptions.TopLeft, VerneUI.PaperDim);
            var cr = m_Cite.rectTransform; cr.anchorMin = new Vector2(0, 0); cr.anchorMax = new Vector2(1, 0.3f); cr.offsetMin = Vector2.zero; cr.offsetMax = new Vector2(0, -22);
            m_Canvas.enabled = false;
        }

        public static void Load(string scene) { Ensure().StartCoroutine(Ensure().LoadRoutine(scene)); }

        IEnumerator LoadRoutine(string scene)
        {
            if (m_Busy) yield break;
            m_Busy = true;
            var card = CardFor(scene);
            var tex = Resources.Load<Texture2D>("VerneCards/" + card.image);
            m_Image.texture = tex;
            m_Image.enabled = tex != null;
            if (tex != null) m_Fit.aspectRatio = (float)tex.width / tex.height;
            m_Quote.text = "“" + card.quote + "”";
            m_Cite.text = "Jules Verne · " + card.cite;
            m_Canvas.enabled = true;
            VerneInput.GameplayBlocked = true;

            for (float t = 0; t < 1f; t += Time.unscaledDeltaTime / 0.5f) { m_Group.alpha = VerneUI.EaseOut(t); yield return null; }
            m_Group.alpha = 1f;
            float shownAt = Time.unscaledTime;
            var op = SceneManager.LoadSceneAsync(scene);
            if (op == null) { Debug.LogError("Scene not in build settings: " + scene + ". Run Verne → Build Everything."); }
            else
            {
                while (!op.isDone) yield return null;
            }
            // let the reader finish the line: at least 3 s on screen
            while (Time.unscaledTime - shownAt < 3f) yield return null;
            VerneInput.GameplayBlocked = false;
            for (float t = 0; t < 1f; t += Time.unscaledDeltaTime / 0.8f) { m_Group.alpha = 1f - VerneUI.EaseOut(t); yield return null; }
            m_Group.alpha = 0f;
            m_Canvas.enabled = false;
            m_Busy = false;
        }
    }
}
