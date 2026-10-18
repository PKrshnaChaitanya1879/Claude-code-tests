using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace Verne.EditorTools
{
    // Builds a standalone Windows game, from the menu or headless:
    //   Unity.exe -batchmode -quit -projectPath <project> -executeMethod Verne.EditorTools.BuildWindows.Run
    public static class BuildWindows
    {
        const string OutDir = "Build";
        const string ExeName = "TwentyThousandLeagues.exe";

        [MenuItem("Verne/Build Windows Game (.exe)", priority = 20)]
        public static void FromMenu() => Build(false);

        public static void Run() => Build(true);

        static void Build(bool batch)
        {
            var scenes = EditorBuildSettings.scenes.Where(s => s.enabled && File.Exists(s.path)).Select(s => s.path).ToArray();
            if (scenes.Length == 0)
            {
                // First run on a fresh copy: make the scenes, then build.
                VerneBootstrap.BuildEverything();
                scenes = EditorBuildSettings.scenes.Where(s => s.enabled && File.Exists(s.path)).Select(s => s.path).ToArray();
            }
            string outPath = Path.Combine(OutDir, ExeName);
            Directory.CreateDirectory(OutDir);
            var opts = new BuildPlayerOptions
            {
                scenes = scenes,
                locationPathName = outPath,
                target = BuildTarget.StandaloneWindows64,
                options = BuildOptions.None,
            };
            BuildReport r = BuildPipeline.BuildPlayer(opts);
            string msg = $"[Verne] Windows build {r.summary.result}: {Path.GetFullPath(outPath)} ({r.summary.totalSize / (1024 * 1024)} MB, {r.summary.totalErrors} errors, {r.summary.totalTime.TotalMinutes:0.0} min)";
            Debug.Log(msg);
            File.WriteAllText(Path.Combine("Logs", "verne_build_report.txt"), msg + "\n");
            if (batch) EditorApplication.Exit(r.summary.result == BuildResult.Succeeded ? 0 : 1);
            else if (r.summary.result == BuildResult.Succeeded) EditorUtility.RevealInFinder(outPath);
        }
    }
}
