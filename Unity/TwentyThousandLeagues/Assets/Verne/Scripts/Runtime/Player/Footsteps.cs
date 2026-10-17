using System.Collections.Generic;
using UnityEngine;

namespace Verne
{
    /// <summary>
    /// Plays footstep sounds by surface. Clips are loaded from Resources/VerneAudio/steps/&lt;surface&gt;_N.
    /// Underwater, the lead soles are a dull thud felt more than heard, with a sand hiss.
    /// </summary>
    [RequireComponent(typeof(PlayerMotor))]
    public class Footsteps : MonoBehaviour
    {
        readonly Dictionary<string, AudioClip[]> m_Cache = new Dictionary<string, AudioClip[]>();
        PlayerMotor m_Motor;
        int m_Last = -1;

        void Awake()
        {
            m_Motor = GetComponent<PlayerMotor>();
            m_Motor.Footstep += OnStep;
        }

        void OnDestroy() { if (m_Motor != null) m_Motor.Footstep -= OnStep; }

        AudioClip[] Clips(string surface)
        {
            if (m_Cache.TryGetValue(surface, out var c)) return c;
            var all = Resources.LoadAll<AudioClip>("VerneAudio/steps");
            var list = new List<AudioClip>();
            foreach (var a in all) if (a.name.StartsWith(surface + "_")) list.Add(a);
            if (list.Count == 0 && surface != "iron") return m_Cache[surface] = Clips(m_Motor.mode == MoveMode.Water ? "sand" : "iron");
            c = list.ToArray();
            m_Cache[surface] = c;
            return c;
        }

        void OnStep(string surface, float loudness)
        {
            if (m_Motor.mode == MoveMode.Water && surface == "iron") surface = "sand";
            var clips = Clips(surface);
            if (clips == null || clips.Length == 0) return;
            int i = Random.Range(0, clips.Length);
            if (clips.Length > 1 && i == m_Last) i = (i + 1) % clips.Length;
            m_Last = i;
            float vol = loudness * (m_Motor.mode == MoveMode.Water ? 0.7f : 0.55f);
            VerneAudio.PlayAt(clips[i], transform.position, vol, 0.06f, 0.6f);
        }
    }
}
