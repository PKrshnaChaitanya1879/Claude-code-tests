using UnityEngine;
using UnityEngine.SceneManagement;

namespace Verne
{
    /// <summary>
    /// M6, first pass: the bed under every scene and the breath in the helmet (Source/audio/ambience.py).
    /// Aboard: the hum of Bunsen's piles, the screw's thrum and the sea sliding along the plates. Outside: the deep
    /// rumble heard through copper and glass. With the helmet on, the Rouquayrol hisses on each inhalation and the
    /// exhalation leaves as bubbles, and everything is heard through the helmet (a low-pass on the listener).
    /// </summary>
    public class Ambience : MonoBehaviour
    {
        static Ambience s_Instance;
        AudioSource m_Bed, m_Rain;
        AudioClip m_Hull, m_Water;
        AudioClip[] m_In, m_Out;
        AudioLowPassFilter m_Lp;
        AudioListener m_Listener;
        float m_BedTarget, m_RainTarget;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Boot()
        {
            if (s_Instance != null) return;
            var go = new GameObject("Ambience");
            DontDestroyOnLoad(go);
            s_Instance = go.AddComponent<Ambience>();
        }

        void Awake()
        {
            m_Hull = Resources.Load<AudioClip>("VerneAudio/loops/hull_hum");
            m_Water = Resources.Load<AudioClip>("VerneAudio/loops/underwater_bed");
            m_In = new[] { Resources.Load<AudioClip>("VerneAudio/breath/breath_in_0"), Resources.Load<AudioClip>("VerneAudio/breath/breath_in_1"), Resources.Load<AudioClip>("VerneAudio/breath/breath_in_2") };
            m_Out = new[] { Resources.Load<AudioClip>("VerneAudio/breath/breath_out_0"), Resources.Load<AudioClip>("VerneAudio/breath/breath_out_1"), Resources.Load<AudioClip>("VerneAudio/breath/breath_out_2") };
            m_Bed = gameObject.AddComponent<AudioSource>();
            m_Bed.loop = true; m_Bed.spatialBlend = 0f; m_Bed.playOnAwake = false; m_Bed.volume = 0f;
            // II.IX: the rain on the surface, heard from 150 fathoms down (Source/audio/rain_below.py)
            m_Rain = gameObject.AddComponent<AudioSource>();
            m_Rain.loop = true; m_Rain.spatialBlend = 0f; m_Rain.playOnAwake = false; m_Rain.volume = 0f;
            m_Rain.clip = Resources.Load<AudioClip>("VerneAudio/loops/rain_below");
            HelmetView.Inhale += () => Breath(m_In, 0.45f);
            HelmetView.Exhale += () => Breath(m_Out, 0.55f);
            SceneManager.activeSceneChanged += (a, b) => Choose(b.name);
            Choose(SceneManager.GetActiveScene().name);
        }

        void Breath(AudioClip[] set, float vol)
        {
            var c = set[Random.Range(0, set.Length)];
            if (c != null) VerneAudio.PlayAt(c, Camera.main != null ? Camera.main.transform.position : Vector3.zero, vol, 0.04f, 0f);
        }

        void Choose(string scene)
        {
            var clip = scene == SceneFlow.Nautilus ? m_Hull : (scene == SceneFlow.Mission1 || scene == SceneFlow.Mission2 || scene == SceneFlow.Title) ? m_Water : null;
            m_BedTarget = clip == null ? 0f : (scene == SceneFlow.Nautilus ? 0.55f : 0.7f);
            if (clip != null && m_Bed.clip != clip) { m_Bed.clip = clip; m_Bed.time = Random.Range(0f, Mathf.Max(0f, clip.length - 1f)); m_Bed.Play(); }
            m_RainTarget = scene == SceneFlow.Mission2 ? 0.5f : 0f;
            if (m_RainTarget > 0f && m_Rain.clip != null && !m_Rain.isPlaying) { m_Rain.time = Random.Range(0f, m_Rain.clip.length - 1f); m_Rain.Play(); }
            m_Listener = null;
        }

        void Update()
        {
            m_Bed.volume = Mathf.MoveTowards(m_Bed.volume, m_BedTarget * GameSettings.Current.sfxVolume, Time.unscaledDeltaTime * 0.5f);
            m_Rain.volume = Mathf.MoveTowards(m_Rain.volume, m_RainTarget * GameSettings.Current.sfxVolume, Time.unscaledDeltaTime * 0.15f);   // fades in slowly: "I heard a kind of pattering above my head"
            if (m_RainTarget <= 0f && m_Rain.isPlaying && m_Rain.volume <= 0.001f) m_Rain.Stop();
            // heard through the helmet: a low-pass on the listener while it is on
            if (m_Listener == null) { m_Listener = FindFirstObjectByType<AudioListener>(); m_Lp = m_Listener != null ? m_Listener.GetComponent<AudioLowPassFilter>() : null; }
            if (m_Listener != null && m_Lp == null) { m_Lp = m_Listener.gameObject.AddComponent<AudioLowPassFilter>(); m_Lp.cutoffFrequency = 22000f; }
            // depth: the deeper the dive, the darker the world sounds through the copper (9 m at Crespo, 274 m at Atlantis)
            float depth = 0f;
            var w = VerneWater.Active;
            if (w != null && m_Listener != null) depth = Mathf.Max(0f, w.surfaceY - m_Listener.transform.position.y);
            float helmetCut = Mathf.Lerp(2600f, 1500f, Mathf.Clamp01(depth / 300f));
            if (m_Lp != null) m_Lp.cutoffFrequency = Mathf.MoveTowards(m_Lp.cutoffFrequency, HelmetView.On ? helmetCut : 22000f, Time.unscaledDeltaTime * 30000f);
            m_Bed.pitch = m_Bed.clip == m_Water ? Mathf.Lerp(1f, 0.85f, Mathf.Clamp01(depth / 300f)) : 1f;   // the bed's rumble sinks with the pressure
        }
    }
}
