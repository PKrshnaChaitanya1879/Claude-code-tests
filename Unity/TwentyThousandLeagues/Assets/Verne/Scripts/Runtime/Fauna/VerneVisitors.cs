using UnityEngine;

namespace Verne
{
    /// <summary>
    /// Feeds Verne/Flora where the visitors are, so the red coral's polyps draw back into their cells as a diver
    /// passes and open again slowly behind him (I.XXIII). Slots 0–4: the player's trail (a sample every 0.6 s,
    /// forgotten over 5 s); slots 5–7: the three divers nearest the player, as they are now.
    /// One global vector array per frame, nothing else.
    /// </summary>
    public class VerneVisitors : MonoBehaviour
    {
        static readonly int ID = Shader.PropertyToID("_VerneVisitors");
        readonly Vector4[] m_Slots = new Vector4[8];
        readonly float[] m_Time = new float[5];
        int m_Next;
        float m_Sample;
        DiverPuppet[] m_Divers;
        const float Memory = 5f;

        void OnEnable()
        {
            for (int i = 0; i < 8; i++) m_Slots[i] = new Vector4(0, -9999, 0, 1);
            for (int i = 0; i < 5; i++) m_Time[i] = -999f;
            Shader.SetGlobalVectorArray(ID, m_Slots);
        }

        void Start() { m_Divers = FindObjectsByType<DiverPuppet>(FindObjectsSortMode.None); }

        void Update()
        {
            var p = PlayerMotor.Instance;
            float now = Time.time;
            if (p != null && now >= m_Sample)
            {
                m_Sample = now + 0.6f;
                var pos = p.transform.position + Vector3.up * 0.8f;
                m_Slots[m_Next] = new Vector4(pos.x, pos.y, pos.z, 0);
                m_Time[m_Next] = now;
                m_Next = (m_Next + 1) % 5;
            }
            for (int i = 0; i < 5; i++) m_Slots[i].w = Mathf.Clamp01((now - m_Time[i]) / Memory);
            // the divers nearest the player (the polyps only matter where someone can see them)
            for (int i = 5; i < 8; i++) m_Slots[i] = new Vector4(0, -9999, 0, 1);
            if (m_Divers != null && p != null)
            {
                Vector3 pp = p.transform.position;
                float d0 = float.MaxValue, d1 = float.MaxValue, d2 = float.MaxValue;
                foreach (var d in m_Divers)
                {
                    if (d == null || !d.isActiveAndEnabled) continue;
                    var dp = d.transform.position;
                    float dd = (dp - pp).sqrMagnitude;
                    var v = new Vector4(dp.x, dp.y + 0.8f, dp.z, 0);
                    if (dd < d0) { m_Slots[7] = m_Slots[6]; d2 = d1; m_Slots[6] = m_Slots[5]; d1 = d0; m_Slots[5] = v; d0 = dd; }
                    else if (dd < d1) { m_Slots[7] = m_Slots[6]; d2 = d1; m_Slots[6] = v; d1 = dd; }
                    else if (dd < d2) { m_Slots[7] = v; d2 = dd; }
                }
            }
            Shader.SetGlobalVectorArray(ID, m_Slots);
        }
    }
}
