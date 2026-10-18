using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace Verne.EditorTools
{
    /// <summary>
    /// Verne → Capture Tour: plays each scene in turn, walks the player to fixed viewpoints and saves the real
    /// game frames to Logs/tour, so the lighting can be judged and tuned on this machine.
    /// </summary>
    [InitializeOnLoad]
    public static class VerneTour
    {
        const string Key = "VerneTourQueue";
        static readonly float G = -9999f;   // "find the ground here"
        static TourCapture.View V(string n, float x, float y, float z, float yaw, float pitch = 0f, bool lamp = false)
            => new TourCapture.View { name = n, pos = new Vector3(x, y, z), yaw = yaw, pitch = pitch, lamp = lamp };

        static TourCapture.View[] ViewsFor(string scene)
        {
            switch (scene)
            {
                case "Nautilus": return new[] {
                    V("saloon_fore", 0.4f, 0.05f, 11.2f, 0f, 4f), V("saloon_aft", 0.2f, 0.05f, 18.8f, 180f, 4f),
                    V("saloon_window", -2.0f, 0.05f, 15f, 90f, -4f), V("library", 1.6f, 0.05f, 9.3f, 205f, 6f),
                    V("dining", 2.4f, 0.05f, 4.6f, 205f, 10f), V("kitchen", -1.4f, 0.05f, -4.4f, 130f, 12f),
                    V("bathroom", -1.5f, 0.05f, -7.75f, 95f, 12f), V("robing", -1.3f, 0.05f, -12.9f, 120f, 8f),
                    V("engine", 0.3f, 0.05f, -19.5f, 180f, 2f) };
                case "Mission1": return new[] {
                    V("m1_start", 0f, G, 12f, 0f, 2f, true), V("divers_a", 0f, G, 0f, 0f, 6f, true), V("divers_b", 0f, G, 0f, 0f, 6f, true), V("m1_forest", 0f, G, 40f, 0f, 2f, true),
                    V("m1_coral", 0f, G, 70f, 0f, 0f, true), V("m1_cemetery", 0f, G, 96f, 0f, 4f, true) };
                case "Mission2": return new[] {
                    V("m2_plain", 0f, G, 22f, 0f, 0f), V("m2_copse", 0f, G, 70f, 0f, 0f), V("m2_trunk", 0f, G, 95f, 0f, 8f),
                    V("m2_platform", 0f, G, 128f, 0f, -2f), V("m2_summit", 0f, G, 149f, 0f, 12f) };
                default: return new[] { V("title", 0f, 0.05f, 0f, 0f) };
            }
        }

        [MenuItem("Verne/Capture Tour (all scenes)", priority = 40)]
        static void All() { SessionState.SetString(Key, "Nautilus,Mission1,Mission2"); Next(); }
        [MenuItem("Verne/Capture Tour (Nautilus)", priority = 41)] static void N() { SessionState.SetString(Key, "Nautilus"); Next(); }
        [MenuItem("Verne/Capture Tour (Missions)", priority = 42)] static void M() { SessionState.SetString(Key, "Mission1,Mission2"); Next(); }

        static void Next()
        {
            var q = SessionState.GetString(Key, "");
            if (string.IsNullOrEmpty(q)) { Debug.Log("[Verne] Capture tour finished: Logs/tour"); return; }
            string scene = q.Split(',')[0];
            EditorSceneManager.OpenScene(VerneBootstrap.Generated + "/Scenes/" + scene + ".unity");
            SessionState.SetString(Key + "_current", scene);
            EditorApplication.EnterPlaymode();
        }

        static VerneTour()
        {
            EditorApplication.playModeStateChanged += s =>
            {
                string cur = SessionState.GetString(Key + "_current", "");
                if (string.IsNullOrEmpty(cur)) return;
                if (s == PlayModeStateChange.EnteredPlayMode)
                {
                    var go = new GameObject("Tour capture");
                    var t = go.AddComponent<TourCapture>();
                    t.scene = cur; t.views = ViewsFor(cur);
                    t.onDone = () => EditorApplication.ExitPlaymode();
                }
                else if (s == PlayModeStateChange.EnteredEditMode)
                {
                    var q = SessionState.GetString(Key, "");
                    int i = q.IndexOf(',');
                    SessionState.SetString(Key, i < 0 ? "" : q.Substring(i + 1));
                    SessionState.SetString(Key + "_current", "");
                    EditorApplication.delayCall += Next;
                }
            };
        }
    }
}
