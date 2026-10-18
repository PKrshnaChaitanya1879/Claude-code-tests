using UnityEngine;
using UnityEngine.SceneManagement;

namespace Verne
{
    /// <summary>
    /// M6: the original score (Source/audio/score.py → Resources/VerneAudio/music). Two sources crossfade, so a cue never
    /// cuts. Each scene has its cue (Title: the Nautilus at rest; Mission I: wonder); scripted moments call <see cref="Play"/>
    /// (the burial). Aboard, the music leaves the field to the hull and to Nemo's organ. Volume follows Settings → Music.
    /// </summary>
    public class Music : MonoBehaviour
    {
        static Music s_I;
        AudioSource[] m_Src = new AudioSource[2];
        int m_Cur;
        float[] m_Target = new float[2];
        float m_Fade = 3f;
        Organ m_Organ; bool m_OrganSearched;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Boot()
        {
            if (s_I != null) return;
            var go = new GameObject("Music"); DontDestroyOnLoad(go);
            s_I = go.AddComponent<Music>();
        }

        void Awake()
        {
            for (int i = 0; i < 2; i++)
            {
                var s = gameObject.AddComponent<AudioSource>();
                s.playOnAwake = false; s.spatialBlend = 0f; s.volume = 0f; s.bypassListenerEffects = true;   // the helmet's low-pass is for the world, not the score
                m_Src[i] = s;
            }
            SceneManager.activeSceneChanged += (a, b) => ForScene(b.name);
            ForScene(SceneManager.GetActiveScene().name);
        }

        void ForScene(string scene)
        {
            m_Organ = null; m_OrganSearched = false;
            if (scene == SceneFlow.Title) Play("title", true, 0.8f, 2f);
            else if (scene == SceneFlow.Nautilus) Play("nautilus", true, 0.32f, 6f);        // under the hull's hum; the organ silences it
            else if (scene == SceneFlow.Mission1) Play("m1_wonder", true, 0.55f, 6f);
            else if (scene == SceneFlow.Mission2) Play("night_walk", true, 0.6f, 10f);
            else Play(null, false, 0f, 3f);
        }

        /// <summary>Crossfade to a cue (null = silence). Loop for beds, one-shot for scenes like the burial.</summary>
        public static void Play(string cue, bool loop, float volume = 0.7f, float fade = 3f)
        {
            if (s_I == null) return;
            s_I.Switch(cue, loop, volume, fade);
        }

        void Switch(string cue, bool loop, float volume, float fade)
        {
            var clip = string.IsNullOrEmpty(cue) ? null : Resources.Load<AudioClip>("VerneAudio/music/" + cue);
            var cur = m_Src[m_Cur];
            if (clip != null && cur.clip == clip && cur.isPlaying) { m_Target[m_Cur] = volume; return; }
            m_Fade = Mathf.Max(0.1f, fade);
            m_Target[m_Cur] = 0f;
            if (clip == null) return;
            m_Cur = 1 - m_Cur;
            var next = m_Src[m_Cur];
            next.clip = clip; next.loop = loop; next.volume = 0f; next.time = 0f; next.Play();
            m_Target[m_Cur] = volume;
        }

        void Update()
        {
            float mv = GameSettings.Current != null ? GameSettings.Current.musicVolume : 0.7f;
            if (!m_OrganSearched) { m_Organ = FindFirstObjectByType<Organ>(); m_OrganSearched = true; }
            if (m_Organ != null && m_Organ.IsPlaying) mv = 0f;                              // Nemo's organ has the saloon
            for (int i = 0; i < 2; i++)
            {
                var s = m_Src[i];
                s.volume = Mathf.MoveTowards(s.volume, m_Target[i] * mv, Time.unscaledDeltaTime / m_Fade);
                if (s.isPlaying && m_Target[i] <= 0f && s.volume <= 0.001f) s.Stop();
            }
        }
    }
}
