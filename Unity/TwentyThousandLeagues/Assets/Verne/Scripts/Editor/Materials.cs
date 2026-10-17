using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace Verne.EditorTools
{
    /// <summary>
    /// URP Lit materials from the CC0 textures in Assets/Verne/Textures (ambientCG, 512 px), plus
    /// a few flat and emissive ones. Colours lean on the book: ebony and brass in the library,
    /// tapestry in the saloon, iron plates with a dark paint, the luminous ceilings.
    /// </summary>
    public static class Materials
    {
        struct Spec
        {
            public string name, tex; public Color tint; public float metal, smooth, tile; public Color emission; public bool transparent;
        }

        static readonly Spec[] Specs =
        {
            new Spec { name = "Iron",        tex = "iron",      tint = new Color(0.55f, 0.56f, 0.58f), metal = 0.8f, smooth = 0.45f, tile = 1f },
            new Spec { name = "IronPaint",   tex = "ironpaint", tint = new Color(0.30f, 0.31f, 0.30f), metal = 0.3f, smooth = 0.35f, tile = 1f },
            new Spec { name = "Brass",       tex = "brass",     tint = new Color(0.86f, 0.70f, 0.42f), metal = 1.0f, smooth = 0.6f,  tile = 1f },
            new Spec { name = "Oak",         tex = "oak",       tint = new Color(0.75f, 0.62f, 0.48f), metal = 0f,   smooth = 0.35f, tile = 1f },
            new Spec { name = "Ebony",       tex = "ebony",     tint = new Color(0.32f, 0.26f, 0.30f), metal = 0f,   smooth = 0.55f, tile = 1f },
            new Spec { name = "Carpet",      tex = "carpet",    tint = new Color(0.80f, 0.68f, 0.62f), metal = 0f,   smooth = 0.05f, tile = 1f },
            new Spec { name = "Leather",     tex = "leather",   tint = new Color(0.55f, 0.38f, 0.26f), metal = 0f,   smooth = 0.4f,  tile = 1f },
            new Spec { name = "Marble",      tex = "marble",    tint = new Color(0.92f, 0.92f, 0.90f), metal = 0f,   smooth = 0.7f,  tile = 1f },
            new Spec { name = "Plaster",     tex = "plaster",   tint = new Color(0.86f, 0.83f, 0.78f), metal = 0f,   smooth = 0.15f, tile = 1f },
            new Spec { name = "Tapestry",    tex = "tapestry",  tint = new Color(0.72f, 0.60f, 0.52f), metal = 0f,   smooth = 0.08f, tile = 1f },
            new Spec { name = "Ceiling",     tex = "ceiling",   tint = new Color(0.95f, 0.92f, 0.86f), metal = 0f,   smooth = 0.2f,  tile = 1f },
            new Spec { name = "Rock",        tex = "rock",      tint = new Color(0.62f, 0.62f, 0.62f), metal = 0f,   smooth = 0.25f, tile = 1f },
            new Spec { name = "Rock2",       tex = "rock2",     tint = new Color(0.55f, 0.55f, 0.56f), metal = 0f,   smooth = 0.25f, tile = 1f },
            new Spec { name = "Sand",        tex = "sand",      tint = new Color(0.95f, 0.92f, 0.84f), metal = 0f,   smooth = 0.15f, tile = 1f },
            new Spec { name = "Basalt",      tex = "rock2",     tint = new Color(0.16f, 0.16f, 0.18f), metal = 0f,   smooth = 0.3f,  tile = 1f },
            new Spec { name = "Lava",        tex = "lava",      tint = new Color(0.25f, 0.2f, 0.18f),  metal = 0f,   smooth = 0.2f,  tile = 1f, emission = new Color(4f, 1.1f, 0.25f) },
            new Spec { name = "Glass",       tex = null,        tint = new Color(0.6f, 0.75f, 0.8f, 0.18f), metal = 0f, smooth = 0.95f, tile = 1f, transparent = true },
            new Spec { name = "LuminousCeiling", tex = "ceiling", tint = new Color(1f, 0.97f, 0.9f), metal = 0f, smooth = 0.1f, tile = 1f, emission = new Color(1.6f, 1.5f, 1.3f) },
            new Spec { name = "LampWhite",   tex = null,        tint = Color.white, metal = 0f, smooth = 0.5f, tile = 1f, emission = new Color(6f, 6.2f, 6.4f) },
            new Spec { name = "Linen",       tex = null,        tint = new Color(0.86f, 0.85f, 0.82f), metal = 0f, smooth = 0.1f, tile = 1f },
            new Spec { name = "CoralRed",    tex = null,        tint = new Color(0.78f, 0.12f, 0.10f), metal = 0f, smooth = 0.3f, tile = 1f },
            new Spec { name = "Greybox",     tex = null,        tint = new Color(0.5f, 0.5f, 0.5f), metal = 0f, smooth = 0.2f, tile = 1f },
        };

        static readonly Dictionary<string, Material> s_Cache = new Dictionary<string, Material>();

        public static void BuildAll()
        {
            s_Cache.Clear();
            var lit = Shader.Find("Universal Render Pipeline/Lit");
            if (lit == null) throw new System.Exception("URP Lit shader not found. Is the URP package installed?");
            foreach (var s in Specs) Make(s, lit);
            AssetDatabase.SaveAssets();
            VerneBootstrap.Note($"{Specs.Length} materials in {VerneBootstrap.Generated}/Materials.");
        }

        static Material Make(Spec s, Shader lit)
        {
            string path = VerneBootstrap.Generated + "/Materials/M_" + s.name + ".mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (m == null) { m = new Material(lit); AssetDatabase.CreateAsset(m, path); }
            m.shader = lit;
            m.SetColor("_BaseColor", s.tint);
            m.SetFloat("_Metallic", s.metal);
            m.SetFloat("_Smoothness", s.smooth);
            if (!string.IsNullOrEmpty(s.tex))
            {
                var c = AssetDatabase.LoadAssetAtPath<Texture2D>(VerneBootstrap.Root + "/Textures/" + s.tex + "_c.jpg");
                var n = AssetDatabase.LoadAssetAtPath<Texture2D>(VerneBootstrap.Root + "/Textures/" + s.tex + "_n.jpg");
                if (c != null) m.SetTexture("_BaseMap", c);
                if (n != null) { m.SetTexture("_BumpMap", n); m.SetFloat("_BumpScale", 0.8f); m.EnableKeyword("_NORMALMAP"); }
                m.SetTextureScale("_BaseMap", Vector2.one * s.tile);
            }
            if (s.emission.maxColorComponent > 0f)
            {
                m.EnableKeyword("_EMISSION");
                m.SetColor("_EmissionColor", s.emission);
                m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.BakedEmissive;
            }
            else { m.DisableKeyword("_EMISSION"); m.SetColor("_EmissionColor", Color.black); }
            if (s.transparent)
            {
                m.SetFloat("_Surface", 1f);
                m.SetFloat("_Blend", 0f);
                m.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha);
                m.SetFloat("_DstBlend", (float)BlendMode.OneMinusSrcAlpha);
                m.SetFloat("_ZWrite", 0f);
                m.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
                m.renderQueue = (int)RenderQueue.Transparent;
                m.SetOverrideTag("RenderType", "Transparent");
            }
            m.enableInstancing = true;
            EditorUtility.SetDirty(m);
            s_Cache[s.name] = m;
            return m;
        }

        public static Material Get(string name)
        {
            if (s_Cache.TryGetValue(name, out var m) && m != null) return m;
            m = AssetDatabase.LoadAssetAtPath<Material>(VerneBootstrap.Generated + "/Materials/M_" + name + ".mat");
            if (m == null) m = AssetDatabase.LoadAssetAtPath<Material>(VerneBootstrap.Generated + "/Materials/M_Greybox.mat");
            s_Cache[name] = m;
            return m;
        }
    }
}
