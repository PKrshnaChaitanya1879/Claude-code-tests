using UnityEngine;

namespace Verne
{
    /// <summary>
    /// The iron panels that cover the saloon's crystal windows (I.XIII: "A sliding noise was heard").
    /// Driven 0..1 by a lever; each panel slides by its own offset.
    /// </summary>
    public class SlidingPanels : MonoBehaviour
    {
        public Transform[] panels;
        public Vector3[] offsets;
        public float speed = 0.25f;           // the panels are heavy: four seconds end to end
        public AudioSource rumble;
        [Range(0, 1)] public float target;
        float m_T;
        Vector3[] m_Rest;

        void Awake()
        {
            m_Rest = new Vector3[panels.Length];
            for (int i = 0; i < panels.Length; i++) m_Rest[i] = panels[i].localPosition;
        }

        public void SetOpen(float v) { target = Mathf.Clamp01(v); }

        void Update()
        {
            float prev = m_T;
            m_T = Mathf.MoveTowards(m_T, target, speed * Time.deltaTime);
            float e = m_T * m_T * (3f - 2f * m_T);
            for (int i = 0; i < panels.Length; i++)
                if (panels[i] != null) panels[i].localPosition = m_Rest[i] + (i < offsets.Length ? offsets[i] : Vector3.zero) * e;
            if (rumble != null)
            {
                bool moving = !Mathf.Approximately(prev, m_T);
                rumble.volume = Mathf.MoveTowards(rumble.volume, moving ? 0.5f : 0f, Time.deltaTime * 3f);
                if (moving && !rumble.isPlaying) rumble.Play();
                if (!moving && rumble.volume <= 0.01f && rumble.isPlaying) rumble.Stop();
            }
        }
    }
}
