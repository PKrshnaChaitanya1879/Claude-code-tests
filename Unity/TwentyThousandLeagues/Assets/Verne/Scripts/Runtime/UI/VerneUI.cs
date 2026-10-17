using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace Verne
{
    /// <summary>
    /// Shared look for every screen. Literary serif (Cormorant Garamond, OFL) because the game is
    /// an 1870 novel and the cards quote it; small caps (Cormorant SC) for labels; one accent,
    /// coral red ("Flower of Blood", I.XXIII), used only for the focused item.
    /// Off-black and soft off-white, never pure black or white.
    /// </summary>
    public static class VerneUI
    {
        public static readonly Color Ink = new Color32(0x0A, 0x0B, 0x0F, 0xFF);
        public static readonly Color Paper = new Color32(0xEC, 0xED, 0xEF, 0xFF);
        public static readonly Color PaperDim = new Color32(0xEC, 0xED, 0xEF, 0x99);
        public static readonly Color Accent = new Color32(0xC8, 0x55, 0x3D, 0xFF);
        public static readonly Color Scrim = new Color32(0x0A, 0x0B, 0x0F, 0xB8);

        static TMP_FontAsset s_Text, s_Bold, s_Italic, s_Caps;
        public static TMP_FontAsset TextFont => s_Text != null ? s_Text : (s_Text = Load("CormorantGaramond-Medium SDF"));
        public static TMP_FontAsset BoldFont => s_Bold != null ? s_Bold : (s_Bold = Load("CormorantGaramond-SemiBold SDF"));
        public static TMP_FontAsset ItalicFont => s_Italic != null ? s_Italic : (s_Italic = Load("CormorantGaramond-MediumItalic SDF"));
        public static TMP_FontAsset CapsFont => s_Caps != null ? s_Caps : (s_Caps = Load("CormorantSC-Medium SDF"));

        static TMP_FontAsset Load(string name)
        {
            var f = Resources.Load<TMP_FontAsset>("VerneFonts/" + name);
            if (f == null) f = TMP_Settings.defaultFontAsset;
            return f;
        }

        public static Canvas CreateCanvas(string name, int order, Transform parent = null)
        {
            var go = new GameObject(name, typeof(RectTransform), typeof(Canvas), typeof(CanvasScaler), typeof(GraphicRaycaster));
            if (parent != null) go.transform.SetParent(parent, false);
            var c = go.GetComponent<Canvas>();
            c.renderMode = RenderMode.ScreenSpaceOverlay;
            c.sortingOrder = order;
            var s = go.GetComponent<CanvasScaler>();
            s.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            s.referenceResolution = new Vector2(1920, 1080);
            s.matchWidthOrHeight = 0.5f;
            return c;
        }

        public static RectTransform Rect(string name, Transform parent, Vector2 anchorMin, Vector2 anchorMax, Vector2 pivot, Vector2 pos, Vector2 size)
        {
            var go = new GameObject(name, typeof(RectTransform));
            go.transform.SetParent(parent, false);
            var r = (RectTransform)go.transform;
            r.anchorMin = anchorMin; r.anchorMax = anchorMax; r.pivot = pivot;
            r.anchoredPosition = pos; r.sizeDelta = size;
            return r;
        }

        public static RectTransform Stretch(string name, Transform parent)
        {
            return Rect(name, parent, Vector2.zero, Vector2.one, new Vector2(0.5f, 0.5f), Vector2.zero, Vector2.zero);
        }

        public static TextMeshProUGUI Text(Transform parent, string name, string text, float size, TMP_FontAsset font = null,
            TextAlignmentOptions align = TextAlignmentOptions.TopLeft, Color? color = null)
        {
            var go = new GameObject(name, typeof(RectTransform), typeof(TextMeshProUGUI));
            go.transform.SetParent(parent, false);
            var t = go.GetComponent<TextMeshProUGUI>();
            t.font = font != null ? font : TextFont;
            t.fontSize = size;
            t.text = text;
            t.alignment = align;
            t.color = color ?? Paper;
            t.raycastTarget = false;
            t.textWrappingMode = TextWrappingModes.Normal;
            t.overflowMode = TextOverflowModes.Overflow;
            return t;
        }

        public static Image Panel(Transform parent, string name, Color color)
        {
            var go = new GameObject(name, typeof(RectTransform), typeof(Image));
            go.transform.SetParent(parent, false);
            var i = go.GetComponent<Image>();
            i.color = color;
            i.raycastTarget = false;
            return i;
        }

        /// <summary>A 1-px hairline.</summary>
        public static Image Hairline(Transform parent, Vector2 anchoredPos, float width, Color color)
        {
            var i = Panel(parent, "Hairline", color);
            var r = i.rectTransform;
            r.anchorMin = r.anchorMax = new Vector2(0f, 1f); r.pivot = new Vector2(0f, 1f);
            r.anchoredPosition = anchoredPos; r.sizeDelta = new Vector2(width, 1f);
            return i;
        }

        public static float EaseOut(float t) { t = Mathf.Clamp01(t); return 1f - Mathf.Pow(1f - t, 3f); }
    }
}
