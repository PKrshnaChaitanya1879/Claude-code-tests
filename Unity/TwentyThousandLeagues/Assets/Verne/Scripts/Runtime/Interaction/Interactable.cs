using UnityEngine;
using UnityEngine.Events;

namespace Verne
{
    /// <summary>
    /// Base for everything the player can operate, Iron Lung style: physical, deliberate, with a
    /// short verb prompt and no floating icons. Subclasses override the Begin/Hold/End hooks.
    /// </summary>
    public abstract class Interactable : MonoBehaviour
    {
        [Tooltip("Verb shown in the prompt, e.g. \"Pull\", \"Turn\", \"Open\".")]
        public string verb = "Use";
        [Tooltip("What it is, e.g. \"the ballast lever\".")]
        public string noun = "";
        public bool interactable = true;
        [Tooltip("Max distance from the eye at which this can be used.")]
        public float reach = 2.2f;

        public UnityEvent onUsed = new UnityEvent();

        Renderer[] m_Renderers;
        MaterialPropertyBlock m_Mpb;
        float m_Highlight, m_HighlightTarget;
        static readonly int s_BaseColor = Shader.PropertyToID("_BaseColor");
        static readonly int s_Highlight = Shader.PropertyToID("_VerneHighlight");
        Color[] m_BaseColors;

        public virtual string Prompt => string.IsNullOrEmpty(noun) ? verb : verb + " " + noun;
        /// <summary>When true, the look input drives this control while it is held (levers, wheels).</summary>
        public virtual bool CapturesLook => false;
        public bool IsHeld { get; private set; }

        protected virtual void Awake()
        {
            m_Renderers = GetComponentsInChildren<Renderer>();
            m_Mpb = new MaterialPropertyBlock();
            m_BaseColors = new Color[m_Renderers.Length];
            for (int i = 0; i < m_Renderers.Length; i++)
            {
                var m = m_Renderers[i].sharedMaterial;
                m_BaseColors[i] = m != null && m.HasProperty(s_BaseColor) ? m.GetColor(s_BaseColor) : Color.white;
            }
        }

        public virtual void SetFocused(bool focused) { m_HighlightTarget = focused && interactable ? 1f : 0f; }

        protected virtual void LateUpdate()
        {
            if (Mathf.Approximately(m_Highlight, m_HighlightTarget)) return;
            m_Highlight = Mathf.MoveTowards(m_Highlight, m_HighlightTarget, Time.unscaledDeltaTime * 5f);
            // a restrained lift in brightness, never an outline glow
            for (int i = 0; i < m_Renderers.Length; i++)
            {
                var r = m_Renderers[i];
                if (r == null) continue;
                r.GetPropertyBlock(m_Mpb);
                Color c = m_BaseColors[i];
                m_Mpb.SetColor(s_BaseColor, Color.Lerp(c, c * 1.35f + new Color(0.02f, 0.02f, 0.02f, 0f), m_Highlight));
                m_Mpb.SetFloat(s_Highlight, m_Highlight);
                r.SetPropertyBlock(m_Mpb);
            }
        }

        public void Begin(Interactor who) { IsHeld = true; OnBegin(who); }
        public void Hold(Interactor who, Vector2 look, float dt) { OnHold(who, look, dt); }
        public void End(Interactor who) { IsHeld = false; OnEnd(who); }

        protected virtual void OnBegin(Interactor who) { onUsed.Invoke(); }
        protected virtual void OnHold(Interactor who, Vector2 look, float dt) { }
        protected virtual void OnEnd(Interactor who) { }

        protected void PlayOneShot(AudioClip clip, float volume = 1f)
        {
            if (clip != null) VerneAudio.PlayAt(clip, transform.position, volume);
        }
    }
}
