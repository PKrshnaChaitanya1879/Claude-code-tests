using System;
using UnityEngine;

namespace Verne
{
    /// <summary>Fills a MenuList with every option in GameSettings. Changes apply live and save on leave.</summary>
    public static class SettingsMenu
    {
        public static void Populate(MenuList menu, Action back)
        {
            var s = GameSettings.Current;
            menu.Clear();
            menu.Add("Quality", () => Cycle(ref s.quality, 1), () => s.quality.ToString(), d => Cycle(ref s.quality, d));
            menu.Add("Frame cap", () => Toggle30(s), () => s.frameCap + " fps", d => Toggle30(s));
            menu.Add("Field of view", null, () => Mathf.RoundToInt(s.fieldOfView) + "°", d => { s.fieldOfView = Mathf.Clamp(s.fieldOfView + d * 2f, 60f, 85f); s.Apply(); });
            menu.Add("Mouse sensitivity", null, () => s.mouseSensitivity.ToString("0.0"), d => { s.mouseSensitivity = Mathf.Clamp(Mathf.Round((s.mouseSensitivity + d * 0.1f) * 10f) / 10f, 0.2f, 3f); });
            menu.Add("Controller sensitivity", null, () => s.padSensitivity.ToString("0.0"), d => { s.padSensitivity = Mathf.Clamp(Mathf.Round((s.padSensitivity + d * 0.1f) * 10f) / 10f, 0.2f, 3f); });
            menu.Add("Invert look", () => s.invertY = !s.invertY, () => s.invertY ? "On" : "Off", d => s.invertY = !s.invertY);
            menu.Add("Head movement", null, () => Mathf.RoundToInt(s.headBob * 100f) + "%", d => s.headBob = Mathf.Clamp01(Mathf.Round((s.headBob + d * 0.25f) * 4f) / 4f));
            menu.Add("Subtitles", () => s.subtitles = !s.subtitles, () => s.subtitles ? "On" : "Off", d => s.subtitles = !s.subtitles);
            menu.Add("Master volume", null, () => Pct(s.masterVolume), d => { s.masterVolume = Step(s.masterVolume, d); s.Apply(); });
            menu.Add("Music", null, () => Pct(s.musicVolume), d => { s.musicVolume = Step(s.musicVolume, d); s.Apply(); });
            menu.Add("Effects", null, () => Pct(s.sfxVolume), d => { s.sfxVolume = Step(s.sfxVolume, d); s.Apply(); });
            menu.Add("Back", () => { s.Save(); back(); });
            menu.onCancel = () => { s.Save(); back(); };
        }

        static void Cycle(ref QualityTier q, int d)
        {
            q = (QualityTier)(((int)q + d + 3) % 3);
            GameSettings.Current.Apply();
        }

        static void Toggle30(GameSettings s) { s.frameCap = s.frameCap == 30 ? 60 : 30; s.Apply(); }
        static float Step(float v, int d) => Mathf.Clamp01(Mathf.Round((v + d * 0.1f) * 10f) / 10f);
        static string Pct(float v) => Mathf.RoundToInt(v * 100f) + "%";
    }
}
