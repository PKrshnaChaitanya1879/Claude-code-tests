using UnityEngine;
using UnityEngine.SceneManagement;

namespace Verne
{
    /// <summary>Runs before the first scene: applies settings and creates the persistent UI.</summary>
    public static class GameBoot
    {
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
        static void Boot()
        {
            GameSettings.Load();
            GameSettings.Current.Apply();
            Hud.Ensure();
            PauseMenu.Ensure();
            SceneManager.sceneLoaded += (s, m) =>
            {
                bool gameplay = s.name != SceneFlow.Title;
                VerneInput.LockCursor(gameplay);
                if (Hud.Instance != null) Hud.Instance.SetVisible(gameplay);
            };
        }
    }
}
