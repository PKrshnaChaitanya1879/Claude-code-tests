using System;
using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace Verne
{
    /// <summary>
    /// A vertical, left-aligned menu usable with keyboard, gamepad and mouse. Focus is shown by an
    /// accent hairline and a small nudge to the right; options with values change with left/right.
    /// </summary>
    public class MenuList : MonoBehaviour
    {
        public class Item
        {
            public string label;
            public Func<string> value;          // null for plain actions
            public Action onSubmit;
            public Action<int> onAdjust;        // -1 / +1
            public TextMeshProUGUI labelText, valueText;
            public RectTransform rect;
            public Image bar;
            public float focusT;
        }

        public readonly List<Item> items = new List<Item>();
        public int index;
        public Action onCancel;
        public float rowHeight = 64f;
        public float labelSize = 40f;
        public float width = 820f;
        public AudioClip tick;

        RectTransform m_Root;
        float m_Repeat;
        int m_RepeatDir;
        Vector3 m_LastMouse;

        public static MenuList Create(Transform parent, Vector2 anchoredTopLeft, float width = 820f)
        {
            var r = VerneUI.Rect("Menu", parent, new Vector2(0, 1), new Vector2(0, 1), new Vector2(0, 1), anchoredTopLeft, new Vector2(width, 600));
            var m = r.gameObject.AddComponent<MenuList>();
            m.m_Root = r; m.width = width;
            return m;
        }

        public Item Add(string label, Action submit, Func<string> value = null, Action<int> adjust = null)
        {
            var it = new Item { label = label, onSubmit = submit, value = value, onAdjust = adjust };
            int i = items.Count;
            it.rect = VerneUI.Rect("Row " + label, m_Root, new Vector2(0, 1), new Vector2(0, 1), new Vector2(0, 1), new Vector2(0, -i * rowHeight), new Vector2(width, rowHeight));
            it.bar = VerneUI.Panel(it.rect, "Focus", VerneUI.Accent);
            var br = it.bar.rectTransform; br.anchorMin = new Vector2(0, 0.5f); br.anchorMax = new Vector2(0, 0.5f); br.pivot = new Vector2(0, 0.5f); br.sizeDelta = new Vector2(0, 2); br.anchoredPosition = new Vector2(-56, -2);
            it.labelText = VerneUI.Text(it.rect, "Label", label, labelSize, VerneUI.TextFont, TextAlignmentOptions.MidlineLeft);
            var lr = it.labelText.rectTransform; lr.anchorMin = Vector2.zero; lr.anchorMax = new Vector2(0.62f, 1); lr.offsetMin = lr.offsetMax = Vector2.zero;
            if (value != null)
            {
                it.valueText = VerneUI.Text(it.rect, "Value", value(), labelSize * 0.8f, VerneUI.CapsFont, TextAlignmentOptions.MidlineRight, VerneUI.PaperDim);
                var vr = it.valueText.rectTransform; vr.anchorMin = new Vector2(0.62f, 0); vr.anchorMax = Vector2.one; vr.offsetMin = vr.offsetMax = Vector2.zero;
            }
            items.Add(it);
            return it;
        }

        public void Clear()
        {
            foreach (var it in items) if (it.rect != null) Destroy(it.rect.gameObject);
            items.Clear(); index = 0;
        }

        void Update()
        {
            if (items.Count == 0) return;
            float dt = Time.unscaledDeltaTime;
            var nav = VerneInput.MenuNav;
            if (nav.y != 0) Move(-nav.y);
            if (nav.x != 0) Adjust(nav.x);

            // held left/right repeats for sliders
            int held = (Input.GetKey(KeyCode.RightArrow) || Input.GetKey(KeyCode.D)) ? 1 : (Input.GetKey(KeyCode.LeftArrow) || Input.GetKey(KeyCode.A)) ? -1 : 0;
            if (held != 0 && held == m_RepeatDir) { m_Repeat += dt; if (m_Repeat > 0.4f) { m_Repeat = 0.33f; Adjust(held); } }
            else { m_RepeatDir = held; m_Repeat = 0f; }

            // mouse: hover focuses, click submits, wheel adjusts
            if ((Input.mousePosition - m_LastMouse).sqrMagnitude > 1f || Input.GetMouseButtonDown(0))
            {
                m_LastMouse = Input.mousePosition;
                for (int i = 0; i < items.Count; i++)
                    if (RectTransformUtility.RectangleContainsScreenPoint(items[i].rect, Input.mousePosition, null))
                    {
                        if (index != i) { index = i; Tick(); }
                        if (Input.GetMouseButtonDown(0)) Submit();
                        break;
                    }
            }
            if (Input.mouseScrollDelta.y != 0) Adjust(Input.mouseScrollDelta.y > 0 ? 1 : -1);

            if (VerneInput.SubmitDown) Submit();
            else if (VerneInput.CancelDown) onCancel?.Invoke();

            for (int i = 0; i < items.Count; i++)
            {
                var it = items[i];
                it.focusT = Mathf.MoveTowards(it.focusT, i == index ? 1f : 0f, dt / 0.18f);
                float e = VerneUI.EaseOut(it.focusT);
                it.labelText.rectTransform.anchoredPosition = new Vector2(12f * e, 0);
                it.labelText.color = Color.Lerp(VerneUI.PaperDim, VerneUI.Paper, e);
                it.bar.rectTransform.sizeDelta = new Vector2(40f * e, 2f);
                if (it.valueText != null) it.valueText.text = it.value();
            }
        }

        void Move(int d)
        {
            index = (index + d + items.Count) % items.Count; // wrap-around
            Tick();
        }

        void Adjust(int d)
        {
            var it = items[index];
            if (it.onAdjust != null) { it.onAdjust(d); Tick(); }
        }

        void Submit()
        {
            var it = items[index];
            if (it.onSubmit != null) { Tick(); it.onSubmit(); }
            else if (it.onAdjust != null) Adjust(1);
        }

        void Tick() { if (tick != null) VerneAudio.PlayUI(tick, 0.4f); }
    }
}
