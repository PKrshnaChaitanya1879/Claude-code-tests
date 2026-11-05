using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

namespace Verne.EditorTools
{
    /// <summary>
    /// The CC0 texture packs in Assets/Verne/Textures/&lt;Pack&gt;/ (README_texture_packs.md lists every source): import
    /// settings sized for a 4 GB GPU, and URP Lit materials made from them. URP Lit reads smoothness from the albedo's
    /// alpha, so each pack's roughness scan is folded into a generated albedo+smoothness texture (1 − roughness) the first
    /// time the material is built. Nothing here invents a texture: every pixel comes from the scans.
    /// </summary>
    public static class TexturePacks
    {
        public static string Dir(string pack) => VerneBootstrap.Root + "/Textures/" + pack;
        static readonly Dictionary<string, Material> s_Cache = new Dictionary<string, Material>();

        public static bool Exists(string pack) => AssetDatabase.LoadAssetAtPath<Texture2D>(Dir(pack) + "/" + pack + "_albedo.jpg") != null;

        /// <summary>Import settings: albedo sRGB BC7, normal BC5, roughness/metal linear BC4; mipmaps, trilinear, aniso 4; 1K (SeabedSand 2K).</summary>
        public static void ImportAll()
        {
            var root = VerneBootstrap.Root + "/Textures";
            if (!AssetDatabase.IsValidFolder(root)) return;
            int n = 0;
            foreach (var guid in AssetDatabase.FindAssets("t:Texture2D", new[] { root }))
            {
                string p = AssetDatabase.GUIDToAssetPath(guid);
                string file = System.IO.Path.GetFileNameWithoutExtension(p);
                bool albedo = file.EndsWith("_albedo"), normal = file.EndsWith("_normal"), rough = file.EndsWith("_rough"), metal = file.EndsWith("_metal");
                if (!(albedo || normal || rough || metal)) continue;
                var ti = AssetImporter.GetAtPath(p) as TextureImporter;
                if (ti == null) continue;
                bool big = file.StartsWith("SeabedSand");
                bool changed = false;
                void SetIf<T>(ref T field, T v, System.Action<T> apply) { if (!EqualityComparer<T>.Default.Equals(field, v)) { apply(v); changed = true; } }
                var tt = ti.textureType; SetIf(ref tt, normal ? TextureImporterType.NormalMap : TextureImporterType.Default, v => ti.textureType = v);
                bool srgb = ti.sRGBTexture; SetIf(ref srgb, albedo, v => ti.sRGBTexture = v);
                bool mips = ti.mipmapEnabled; SetIf(ref mips, true, v => ti.mipmapEnabled = v);
                int max = ti.maxTextureSize; SetIf(ref max, big ? 2048 : 1024, v => ti.maxTextureSize = v);
                int aniso = ti.anisoLevel; SetIf(ref aniso, 4, v => ti.anisoLevel = v);
                var fm = ti.filterMode; SetIf(ref fm, FilterMode.Trilinear, v => ti.filterMode = v);
                var wm = ti.wrapMode; SetIf(ref wm, TextureWrapMode.Repeat, v => ti.wrapMode = v);
                var ps = ti.GetDefaultPlatformTextureSettings();
                var fmt = ps.format;
                var want = albedo ? TextureImporterFormat.BC7 : (normal ? TextureImporterFormat.BC5 : TextureImporterFormat.BC4);
                if (fmt != want || ps.maxTextureSize != (big ? 2048 : 1024))
                {
                    ps.format = want; ps.maxTextureSize = big ? 2048 : 1024; ps.textureCompression = TextureImporterCompression.CompressedHQ;
                    ti.SetPlatformTextureSettings(ps); changed = true;
                }
                if (changed) { ti.SaveAndReimport(); n++; }
            }
            VerneBootstrap.Note($"Texture packs: {n} textures (re)imported (BC7 albedo, BC5 normal, BC4 roughness; 1K, SeabedSand 2K).");
        }

        /// <summary>The pack's albedo with smoothness (1 − roughness) in alpha, generated once into Generated/Textures.</summary>
        static Texture2D Smoothness(string pack)
        {
            string outDir = VerneBootstrap.Generated + "/Textures";
            if (!AssetDatabase.IsValidFolder(outDir)) AssetDatabase.CreateFolder(VerneBootstrap.Generated, "Textures");
            string outPath = outDir + "/" + pack + "_albedo_smooth.png";
            var done = AssetDatabase.LoadAssetAtPath<Texture2D>(outPath);
            if (done != null) return done;
            var a = AssetDatabase.LoadAssetAtPath<Texture2D>(Dir(pack) + "/" + pack + "_albedo.jpg");
            var r = AssetDatabase.LoadAssetAtPath<Texture2D>(Dir(pack) + "/" + pack + "_rough.jpg");
            if (a == null) return null;
            if (r == null) return a;
            int w = a.width, h = a.height;
            // read through a temporary uncompressed copy (the imported textures are block-compressed)
            Color32[] ca = ReadPixels(a, w, h, true), cr = ReadPixels(r, w, h, false);
            var o = new Texture2D(w, h, TextureFormat.RGBA32, false, false);
            for (int i = 0; i < ca.Length; i++) { var c = ca[i]; c.a = (byte)(255 - cr[i].r); ca[i] = c; }
            o.SetPixels32(ca); o.Apply();
            System.IO.File.WriteAllBytes(outPath, o.EncodeToPNG());
            Object.DestroyImmediate(o);
            AssetDatabase.ImportAsset(outPath);
            var ti = AssetImporter.GetAtPath(outPath) as TextureImporter;
            if (ti != null)
            {
                ti.sRGBTexture = true; ti.alphaSource = TextureImporterAlphaSource.FromInput; ti.mipmapEnabled = true; ti.anisoLevel = 4;
                ti.maxTextureSize = pack == "SeabedSand" ? 2048 : 1024; ti.filterMode = FilterMode.Trilinear; ti.wrapMode = TextureWrapMode.Repeat;
                var ps = ti.GetDefaultPlatformTextureSettings(); ps.format = TextureImporterFormat.BC7; ps.textureCompression = TextureImporterCompression.CompressedHQ; ti.SetPlatformTextureSettings(ps);
                ti.SaveAndReimport();
            }
            return AssetDatabase.LoadAssetAtPath<Texture2D>(outPath);
        }

        static Color32[] ReadPixels(Texture2D src, int w, int h, bool srgb)
        {
            // through the GPU (the imported textures are block-compressed and not CPU-readable); sRGB in, sRGB out for albedo
            var rt = RenderTexture.GetTemporary(w, h, 0, RenderTextureFormat.ARGB32, srgb ? RenderTextureReadWrite.sRGB : RenderTextureReadWrite.Linear);
            Graphics.Blit(src, rt);
            var prev = RenderTexture.active; RenderTexture.active = rt;
            var t = new Texture2D(w, h, TextureFormat.RGBA32, false, true);
            t.ReadPixels(new Rect(0, 0, w, h), 0, 0); t.Apply();
            RenderTexture.active = prev; RenderTexture.ReleaseTemporary(rt);
            var px = t.GetPixels32(); Object.DestroyImmediate(t);
            return px;
        }

        /// <summary>A URP Lit material from a pack (tint multiplies the scan; tiling in metres per repeat via the mesh UVs).</summary>
        public static Material Get(string pack, Color tint, float tile = 1f, float metallic = 0f, float normalScale = 1f)
        {
            string key = pack + "_" + ColorUtility.ToHtmlStringRGB(tint) + "_" + tile.ToString("0.##");
            if (s_Cache.TryGetValue(key, out var cached) && cached != null) return cached;
            if (!Exists(pack)) return null;
            var lit = Shader.Find("Universal Render Pipeline/Lit");
            string path = VerneBootstrap.Generated + "/Materials/M_Pack_" + key.Replace('.', '_') + ".mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (m == null) { m = new Material(lit); AssetDatabase.CreateAsset(m, path); }
            m.shader = lit;
            var albedo = Smoothness(pack);
            m.SetTexture("_BaseMap", albedo);
            m.SetTextureScale("_BaseMap", Vector2.one * tile);
            m.SetColor("_BaseColor", tint);
            m.SetFloat("_Metallic", metallic);
            m.SetFloat("_Smoothness", 1f);                    // scaled by the scan's own smoothness in alpha
            m.SetFloat("_SmoothnessTextureChannel", 1f);      // albedo alpha
            m.EnableKeyword("_SMOOTHNESS_TEXTURE_ALBEDO_CHANNEL_A");
            var n = AssetDatabase.LoadAssetAtPath<Texture2D>(Dir(pack) + "/" + pack + "_normal.jpg");
            if (n != null) { m.SetTexture("_BumpMap", n); m.SetFloat("_BumpScale", normalScale); m.EnableKeyword("_NORMALMAP"); }
            if (metallic > 0f)
            {
                var mt = AssetDatabase.LoadAssetAtPath<Texture2D>(Dir(pack) + "/" + pack + "_metal.jpg");
                if (mt != null) { m.SetTexture("_MetallicGlossMap", mt); m.EnableKeyword("_METALLICSPECGLOSSMAP"); }
            }
            m.enableInstancing = true;
            EditorUtility.SetDirty(m);
            s_Cache[key] = m;
            return m;
        }

        public static void ClearCache() => s_Cache.Clear();
    }
}
