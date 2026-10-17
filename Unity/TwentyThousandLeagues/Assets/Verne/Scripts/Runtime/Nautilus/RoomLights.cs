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
        public float fade = 0.35f;
        float m_T = 1f;
        float[] m_Base;
        Color[] m_Emit;
        MaterialPropertyBlock m_Mpb;
        static readonly int ID_Emission = Shader.PropertyToID("_EmissionColor");

        void Awake()
        {
            m_Mpb = new MaterialPropertyBlock();
            m_Base = new float[lights != null ? lights.Length : 0];
            for (int i = 0; i < m_Base.Length; i++) if (lights[i] != null) m_Base[i] = lights[i].intensity;
            m_Emit = new Color[glowing != null ? glowing.Length : 0];
            for (int i = 0; i < m_Emit.Length; i++)
            {
                var m = glowing[i] != null ? glowing[i].sharedMaterial : null;
                m_Emit[i] = m != null && m.HasProperty(ID_Emission) ? m.GetColor(ID_Emission) : Color.white;
            }
            m_T = on ? 1f : 0f;
        }

        public void Toggle() { on = !on; }
        public void Set(bool v) { on = v; }

        void Update()
        {
            float target = on ? 1f : 0f;
            if (Mathf.Approximately(m_T, target)) return;
            m_T = Mathf.MoveTowards(m_T, target, Time.deltaTime / Mathf.Max(0.01f, fade));
            for (int i = 0; i < m_Base.Length; i++) if (lights[i] != null) { lights[i].intensity = m_Base[i] * m_T; lights[i].enabled = m_T > 0.001f; }
            for (int i = 0; i < m_Emit.Length; i++)
            {
                if (glowing[i] == null) continue;
                glowing[i].GetPropertyBlock(m_Mpb);
                m_Mpb.SetColor(ID_Emission, m_Emit[i] * m_T);
                glowing[i].SetPropertyBlock(m_Mpb);
            }
        }
    }
}
