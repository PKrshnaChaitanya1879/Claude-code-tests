using System;
using System.IO;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace Verne.EditorTools
{
    /// <summary>
    /// Self-assembly. Menu Verne → Build Everything (also runs once automatically on the first open)
    /// creates project settings, layers, URP assets and quality tiers, fonts, materials, scenes and
    /// build settings from code, then writes Logs/verne_setup_report.txt.
    /// Every step is independent: a failure is reported and the rest still runs.
    /// </summary>
    [InitializeOnLoad]
    public static class VerneBootstrap
    {
        public const string Root = "Assets/Verne";
        public const string Generated = "Assets/Verne/Generated";
        const string DoneMarker = "ProjectSettings/VerneBootstrap.done";
        const string ReportPath = "Logs/verne_setup_report.txt";
        public const int Version = 4;   // bump to re-run the first-open build after an update

        static StringBuilder s_Report;
        static int s_Ok, s_Fail;

        static VerneBootstrap()
        {
            EditorApplication.delayCall += AutoRunOnce;
        }

        static void AutoRunOnce()
        {
            if (AssetDatabase.IsAssetImportWorkerProcess()) return;      // background import workers must never build
            if (Application.isBatchMode && Environment.GetEnvironmentVariable("VERNE_NO_AUTORUN") == "1") return;
            if (File.Exists(DoneMarker))
            {
                if (File.ReadAllText(DoneMarker).Trim() == Version.ToString()) return;
            }
            if (EditorApplication.isCompiling || EditorApplication.isUpdating || EditorApplication.isPlayingOrWillChangePlaymode)
            {
                EditorApplication.delayCall += AutoRunOnce;
                return;
            }
            Debug.Log("[Verne] First open: building everything. This takes a minute or two.");
            BuildEverything();
        }

        [MenuItem("Verne/Build Everything", priority = 0)]
        public static void BuildEverything()
        {
            if (!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
            s_Report = new StringBuilder();
            s_Ok = s_Fail = 0;
            var started = DateTime.Now;
            Line("Twenty Thousand Leagues: setup report");
            Line($"Unity {Application.unityVersion} · {SystemInfo.operatingSystem} · {SystemInfo.graphicsDeviceName}");
            Line($"Started {started:yyyy-MM-dd HH:mm:ss}");
            Line("");

            EnsureFolder(Generated);
            try
            {
                AssetDatabase.StartAssetEditing();
                Step("Folders", () => { foreach (var f in new[] { "Materials", "Scenes", "Rendering", "Meshes", "Profiles" }) EnsureFolder(Generated + "/" + f); });
            }
            finally { AssetDatabase.StopAssetEditing(); }

            Step("Player settings (linear colour, input handling, window)", ProjectSetup.PlayerSettingsSetup);
            Step("Tags and layers", ProjectSetup.TagsAndLayers);
            Step("Physics and time", ProjectSetup.PhysicsAndTime);
            Step("Texture import (1024 max, compressed)", ProjectSetup.TextureImport);
            Step("Audio import (score streamed, beds compressed in memory)", AudioImport.Configure);
            Step("Fonts (TextMesh Pro SDF assets)", ProjectSetup.Fonts);
            Step("URP assets and quality tiers (Light / Balanced / Full)", ProjectSetup.RenderPipelines);
            Step("Volume profiles (grade per scene)", ProjectSetup.VolumeProfiles);
            Step("Materials", Materials.BuildAll);
            Step("Model: Nautilus exterior (Blender FBX → prefab with LODs and collider)", NautilusExterior.BuildPrefab);
            Step("Scene: Title", SceneBuilders.Title);
            Step("Scene: Nautilus", SceneBuilders.Nautilus);
            Step("Scene: Mission I (Crespo forest, coral kingdom)", SceneBuilders.Mission1);
            Step("Scene: Mission II (Atlantis)", SceneBuilders.Mission2);
            Step("Build settings", SceneBuilders.BuildSettings);
            int realFailures = s_Fail;      // the validation pass only reports; it never forces a rebuild on every open
            Step("Validate scenes (missing scripts, references, budgets)", SceneBuilders.Validate);
            EditorUtility.ClearProgressBar();

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            try { EditorSceneManager.OpenScene(Generated + "/Scenes/Title.unity"); } catch { }

            Line("");
            Line($"Finished in {(DateTime.Now - started).TotalSeconds:0.0} s: {s_Ok} steps OK, {s_Fail} failed.");
            if (s_Fail == 0) Line("Open Assets/Verne/Generated/Scenes/Title.unity and press Play.");
            else Line("Some steps failed. The details are above; the rest of the project is still usable. Running Verne → Build Everything again is safe.");
            WriteReport();
            if (realFailures == 0) File.WriteAllText(DoneMarker, Version.ToString());   // a failed first build tries again on the next open
            Debug.Log($"[Verne] Build Everything: {s_Ok} OK, {s_Fail} failed. Report: {ReportPath}");
        }

        [MenuItem("Verne/Open Setup Report", priority = 20)]
        static void OpenReport()
        {
            if (File.Exists(ReportPath)) EditorUtility.OpenWithDefaultApp(Path.GetFullPath(ReportPath));
            else EditorUtility.DisplayDialog("Verne", "No report yet. Run Verne → Build Everything.", "OK");
        }

        static void Step(string name, Action a)
        {
            var t = DateTime.Now;
            EditorUtility.DisplayProgressBar("Twenty Thousand Leagues: building everything", name, Mathf.Clamp01((s_Ok + s_Fail) / 20f));
            try
            {
                SceneBuilders.Notes.Clear();
                a();
                s_Ok++;
                Line($"[ OK ] {name}  ({(DateTime.Now - t).TotalSeconds:0.0} s)");
                foreach (var n in SceneBuilders.Notes) Line("       " + n);
            }
            catch (Exception e)
            {
                s_Fail++;
                Line($"[FAIL] {name}: {e.GetType().Name}: {e.Message}");
                foreach (var n in SceneBuilders.Notes) Line("       " + n);
                Line("       " + (e.StackTrace ?? "").Split('\n')[0].Trim());
                Debug.LogException(e);
            }
        }

        public static void Note(string s) { SceneBuilders.Notes.Add(s); }
        static void Line(string s) { s_Report.AppendLine(s); }

        static void WriteReport()
        {
            Directory.CreateDirectory("Logs");
            File.WriteAllText(ReportPath, s_Report.ToString());
        }

        public static void EnsureFolder(string path)
        {
            if (AssetDatabase.IsValidFolder(path)) return;
            string parent = Path.GetDirectoryName(path).Replace('\\', '/');
            EnsureFolder(parent);
            AssetDatabase.CreateFolder(parent, Path.GetFileName(path));
        }
    }
}
