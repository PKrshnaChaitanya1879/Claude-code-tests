using UnityEngine;

namespace Verne
{
    /// <summary>
    /// Pooled one-shot sounds. Every one-shot gets a little pitch and volume variation so repeated
    /// sounds never machine-gun. Underwater muffling is applied by the listener-side filter that
    /// the Underwater system drives (M6), not here.
    /// </summary>
    public static class VerneAudio
    {
        const int PoolSize = 24;
        static AudioSource[] s_Pool;
        static int s_Next;
        static AudioSource s_UI;

        static void Ensure()
        {
            if (s_Pool != null && s_Pool[0] != null) return;
            var root = new GameObject("Audio Pool");
            Object.DontDestroyOnLoad(root);
            s_Pool = new AudioSource[PoolSize];
            for (int i = 0; i < PoolSize; i++)
            {
                var go = new GameObject("Voice " + i);
                go.transform.SetParent(root.transform);
                var a = go.AddComponent<AudioSource>();
                a.playOnAwake = false;
                a.spatialBlend = 1f;
                a.rolloffMode = AudioRolloffMode.Logarithmic;
                a.minDistance = 1.2f;
                a.maxDistance = 40f;
                a.dopplerLevel = 0f;
                s_Pool[i] = a;
            }
            var ui = new GameObject("UI Voice");
            ui.transform.SetParent(root.transform);
            s_UI = ui.AddComponent<AudioSource>();
            s_UI.playOnAwake = false;
            s_UI.spatialBlend = 0f;
            s_UI.ignoreListenerPause = true;
        }

        public static AudioSource PlayAt(AudioClip clip, Vector3 pos, float volume = 1f, float pitchJitter = 0.05f, float spatial = 1f)
        {
            if (clip == null) return null;
            Ensure();
            var a = s_Pool[s_Next];
            s_Next = (s_Next + 1) % PoolSize;
            a.transform.position = pos;
            a.clip = clip;
            a.spatialBlend = spatial;
            a.pitch = 1f + Random.Range(-pitchJitter, pitchJitter);
            a.volume = volume * Random.Range(0.9f, 1f) * GameSettings.Current.sfxVolume;
            a.Play();
            return a;
        }

        public static void PlayUI(AudioClip clip, float volume = 1f)
        {
            if (clip == null) return;
            Ensure();
            s_UI.pitch = 1f + Random.Range(-0.02f, 0.02f);
            s_UI.PlayOneShot(clip, volume * GameSettings.Current.sfxVolume);
        }
    }
}
