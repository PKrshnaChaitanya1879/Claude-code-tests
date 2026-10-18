using UnityEngine;

namespace Verne
{
    /// <summary>
    /// The saloon's luminous ceiling on a switch. In the book the ceiling goes dark before the panels slide
    /// open: "all was suddenly darkness. The luminous ceiling was gone" (I.XIV) – so the sea outside, lit
    /// by the Nautilus' own light, becomes "liquid light". Fades the room's lights and the ceiling's emission.
    /// </summary>
    public class RoomLights : MonoBehaviour
    {
        public Light[] lights;
        public Renderer[] glowing;
        public bool on = true;
        float m_T = 1f;
        float[] m_Base;
        Color[] m_Emit;
        MaterialPropertyBlock m_Mpb;
        static readonly int ID_Emission = Shader.PropertyToID("_EmissionColor");

        // An incandescent filament, not an LED (GUM: "fade in light and fade out, because it's incandescent").
        // m_T is the filament's normalised temperature: it heats fast and cools slower (thermal mass), light
        // output follows roughly T^3.5, and the colour slides toward deep orange as it cools.
        public float heatTime = 0.22f, coolTime = 0.55f;
        static readonly Color k_Ember = new Color(1f, 0.38f, 0.12f);
        Color[] m_LightCol;
        float m_SwitchedAt = -10f;

        void Awake()
        {
            m_Mpb = new MaterialPropertyBlock();
            m_Base = new float[lights != null ? lights.Length : 0];
            m_LightCol = new Color[m_Base.Length];
            for (int i = 0; i < m_Base.Length; i++) if (lights[i] != null) { m_Base[i] = lights[i].intensity; m_LightCol[i] = lights[i].color; }
            m_Emit = new Color[glowing != null ? glowing.Length : 0];
            for (int i = 0; i < m_Emit.Length; i++)
            {
                var m = glowing[i] != null ? glowing[i].sharedMaterial : null;
                m_Emit[i] = m != null && m.HasProperty(ID_Emission) ? m.GetColor(ID_Emission) : Color.white;
            }
            m_T = on ? 1f : 0f;
            Apply();
        }

        public void Toggle() { Set(!on); }
        public void Set(bool v) { if (v != on) m_SwitchedAt = Time.time; on = v; }

        void Update()
        {
            float target = on ? 1f : 0f;
            if (Mathf.Abs(m_T - target) < 0.0005f && Time.time - m_SwitchedAt > 0.3f) { if (m_T != target) { m_T = target; Apply(); } return; }
            float tau = target > m_T ? heatTime : coolTime;
            m_T = Mathf.Lerp(m_T, target, 1f - Mathf.Exp(-Time.deltaTime / Mathf.Max(0.01f, tau) * 2.2f));
            Apply();
        }

        void Apply()
        {
            float out_ = Mathf.Pow(Mathf.Clamp01(m_T), 3.5f);
            // a switch closing on an 1860s circuit: the contact chatters twice before it holds
            float since = Time.time - m_SwitchedAt;
            if (on && since < 0.16f) out_ *= since < 0.04f ? 0.35f : since < 0.08f ? 1f : since < 0.11f ? 0.55f : 1f;
            Color tint = Color.Lerp(k_Ember, Color.white, Mathf.SmoothStep(0f, 1f, m_T));
            for (int i = 0; i < m_Base.Length; i++)
                if (lights[i] != null) { lights[i].intensity = m_Base[i] * out_; lights[i].color = m_LightCol[i] * tint; lights[i].enabled = out_ > 0.002f; }
            for (int i = 0; i < m_Emit.Length; i++)
            {
                if (glowing[i] == null) continue;
                glowing[i].GetPropertyBlock(m_Mpb);
                m_Mpb.SetColor(ID_Emission, m_Emit[i] * tint * out_);
                glowing[i].SetPropertyBlock(m_Mpb);
            }
        }
    }
}
