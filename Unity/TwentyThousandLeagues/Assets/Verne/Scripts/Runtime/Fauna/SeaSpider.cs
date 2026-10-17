using UnityEngine;

namespace Verne
{
    /// <summary>
    /// The sea-spider of I.XVI: it watches the visitor "with squinting eyes, ready to spring", rising a little on its
    /// legs and trembling as he comes near; when Captain Nemo passes close, the blow of the gun's butt knocks it over
    /// and "the horrible claws of the monster writhe in terrible convulsions", then it lies still.
    /// </summary>
    public class SeaSpider : MonoBehaviour
    {
        public Transform nemo;
        bool m_Seen, m_Over;
        float m_T, m_OverT;
        Quaternion m_Rest; Vector3 m_RestPos;

        void Start() { m_Rest = transform.rotation; m_RestPos = transform.position; }

        void Update()
        {
            m_T += Time.deltaTime;
            var p = PlayerMotor.Instance;
            float d = p != null ? Vector3.Distance(p.transform.position, transform.position) : 99f;
            if (m_Over)
            {
                m_OverT += Time.deltaTime;
                float writhe = Mathf.Exp(-m_OverT * 0.8f) * Mathf.Sin(m_OverT * 22f) * 9f;
                transform.rotation = m_Rest * Quaternion.Euler(0f, writhe, 165f + writhe * 0.5f);
                transform.position = Vector3.Lerp(transform.position, m_RestPos + Vector3.up * 0.85f, Time.deltaTime * 4f);
                return;
            }
            if (!m_Seen && d < 6f)
            {
                m_Seen = true;
                Hud.Toast("“A few steps off, a monstrous sea-spider, about thirty-eight inches high, was watching me with squinting eyes, ready to spring upon me.”", 6f);
            }
            float alert = Mathf.Clamp01((7f - d) / 4f);
            // turn to face the visitor, rise and tremble
            if (p != null && alert > 0f)
            {
                var to = p.transform.position - transform.position; to.y = 0f;
                if (to.sqrMagnitude > 0.01f) m_Rest = Quaternion.Slerp(m_Rest, Quaternion.LookRotation(to.normalized), Time.deltaTime * 1.5f);   // its front is +Z (Blender -Y after the FBX axis conversion)
            }
            transform.rotation = m_Rest * Quaternion.Euler(Mathf.Sin(m_T * 17f) * 1.5f * alert, 0f, Mathf.Sin(m_T * 13f) * 1.5f * alert);
            transform.position = m_RestPos + Vector3.up * 0.12f * alert;
            if (m_Seen && nemo != null && Vector3.Distance(nemo.position, transform.position) < 3.2f)
            {
                m_Over = true;
                Hud.Toast("“Captain Nemo pointed out the hideous crustacean, which a blow from the butt end of the gun knocked over.”", 6f);
            }
        }
    }
}
