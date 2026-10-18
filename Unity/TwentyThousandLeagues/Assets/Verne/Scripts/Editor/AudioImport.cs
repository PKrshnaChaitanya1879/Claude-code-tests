using UnityEditor;
using UnityEngine;

namespace Verne.EditorTools
{
    /// <summary>
    /// Lean audio memory for GUM's laptop: the score's two-minute cues stream from disk instead of decompressing
    /// (~20 MB each), the looping beds stay compressed in memory, and short effects decompress on load (no CPU cost to play).
    /// </summary>
    public static class AudioImport
    {
        public static void Configure()
        {
            int n = 0;
            foreach (var guid in AssetDatabase.FindAssets("t:AudioClip", new[] { VerneBootstrap.Root + "/Resources/VerneAudio" }))
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                var ai = AssetImporter.GetAtPath(path) as AudioImporter;
                if (ai == null) continue;
                var s = ai.defaultSampleSettings;
                var want = path.Contains("/music/") ? AudioClipLoadType.Streaming : path.Contains("/loops/") ? AudioClipLoadType.CompressedInMemory : AudioClipLoadType.DecompressOnLoad;
                if (s.loadType == want && s.compressionFormat == AudioCompressionFormat.Vorbis) continue;
                s.loadType = want; s.compressionFormat = AudioCompressionFormat.Vorbis; s.quality = path.Contains("/music/") ? 0.6f : 0.5f;
                if (want == AudioClipLoadType.Streaming) ai.loadInBackground = true;
                ai.defaultSampleSettings = s;
                ai.SaveAndReimport();
                n++;
            }
            VerneBootstrap.Note($"Audio import: {n} clips set (music streamed, loops compressed, effects decompressed).");
        }
    }
}
