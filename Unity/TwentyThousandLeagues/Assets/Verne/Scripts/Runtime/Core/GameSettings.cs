using System;
using UnityEngine;

namespace Verne
{
    public enum QualityTier { Light = 0, Balanced = 1, Full = 2 }

    /// <summary>
    /// Player options, saved in PlayerPrefs. Quality tiers map onto the three Quality levels the
    /// editor bootstrap creates (Light, Balanced, Full), each with its own URP asset.
    /// </summary>
    [Serializable]
    public class GameSettings
    {
        public QualityTier quality = QualityTier.Balanced;
        public float mouseSensitivity = 1f;   // 0.2 .. 3
        public float padSensitivity = 1f;     // 0.2 .. 3
        public bool invertY = false;
        public float masterVolume = 0.9f;
        public float musicVolume = 0.7f;
        public float sfxVolume = 0.9f;
        public float voiceVolume = 0.9f;
        public bool subtitles = true;
        public int frameCap = 30;             // 30 or 60
        public float fieldOfView = 68f;       // 60 .. 85
        public float headBob = 1f;            // 0 .. 1 (comfort)

        const string Key = "verne.settings.v1";
        static GameSettings s_Current;

        public static event Action<GameSettings> Changed;

        public static GameSettings Current
        {
            get
            {
                if (s_Current == null) Load();
                return s_Current;
            }
        }

        public static void Load()
        {
            s_Current = new GameSettings();
            try
            {
                string json = PlayerPrefs.GetString(Key, "");
                if (!string.IsNullOrEmpty(json)) JsonUtility.FromJsonOverwrite(json, s_Current);
                else s_Current.quality = GuessTier();
            }
            catch (Exception e) { Debug.LogWarning("Settings reset: " + e.Message); }
        }

        public void Save()
        {
            PlayerPrefs.SetString(Key, JsonUtility.ToJson(this));
            PlayerPrefs.Save();
            Apply();
        }

        public void Apply()
        {
            int level = FindQualityLevel(quality.ToString());
            if (level >= 0 && QualitySettings.GetQualityLevel() != level) QualitySettings.SetQualityLevel(level, true);
            QualitySettings.vSyncCount = 0;
            Application.targetFrameRate = Mathf.Clamp(frameCap, 30, 240);
            AudioListener.volume = Mathf.Clamp01(masterVolume);
            Changed?.Invoke(this);
        }

        public static int FindQualityLevel(string name)
        {
            var names = QualitySettings.names;
            for (int i = 0; i < names.Length; i++)
                if (string.Equals(names[i], name, StringComparison.OrdinalIgnoreCase)) return i;
            return -1;
        }

        /// <summary>First-run guess: integrated GPUs and small VRAM start on Light, big GPUs on Full.</summary>
        static QualityTier GuessTier()
        {
            int vram = SystemInfo.graphicsMemorySize;
            string gpu = (SystemInfo.graphicsDeviceName ?? "").ToLowerInvariant();
            bool integrated = gpu.Contains("vega") || gpu.Contains("radeon(tm) graphics") || gpu.Contains("intel") || gpu.Contains("uhd") || vram < 2048;
            if (integrated) return QualityTier.Light;
            return vram >= 6000 ? QualityTier.Full : QualityTier.Balanced;
        }

        /// <summary>The tier actually active right now (by Quality level name).</summary>
        public static QualityTier ActiveTier
        {
            get
            {
                var n = QualitySettings.names;
                int i = QualitySettings.GetQualityLevel();
                if (i >= 0 && i < n.Length && Enum.TryParse(n[i], true, out QualityTier t)) return t;
                return Current.quality;
            }
        }
    }
}
