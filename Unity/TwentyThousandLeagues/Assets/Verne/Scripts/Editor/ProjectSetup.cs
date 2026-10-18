using System.IO;
using TMPro;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEngine.TextCore.LowLevel;

namespace Verne.EditorTools
{
    /// <summary>Project-wide settings created from code (see VerneBootstrap).</summary>
    public static class ProjectSetup
    {
        public static readonly string[] LayerNames = { "Player", "Interactable", "HeldItem", "Water", "Hull", "Creature" };
        public const int PlayerLayer = 8, InteractableLayer = 9, HeldItemLayer = 10, WaterLayer = 11, HullLayer = 12, CreatureLayer = 13;

        public static void PlayerSettingsSetup()
        {
            PlayerSettings.colorSpace = ColorSpace.Linear;
            PlayerSettings.companyName = "Verne Workshop";
            PlayerSettings.productName = "Twenty Thousand Leagues Under the Sea";
            PlayerSettings.defaultScreenWidth = 1920;
            PlayerSettings.defaultScreenHeight = 1080;
            PlayerSettings.fullScreenMode = FullScreenMode.FullScreenWindow;
            PlayerSettings.runInBackground = false;
            PlayerSettings.gpuSkinning = true;
            PlayerSettings.SetGraphicsAPIs(BuildTarget.StandaloneWindows64, new[] { GraphicsDeviceType.Direct3D11 });
            PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.StandaloneWindows64, false);

            // input handling = Both (legacy keyboard/mouse + Input System gamepad)
            var ps = AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/ProjectSettings.asset");
            if (ps != null && ps.Length > 0)
            {
                var so = new SerializedObject(ps[0]);
                var p = so.FindProperty("activeInputHandler");
                if (p != null)
                {
                    if (p.intValue != 2)
                    {
                        p.intValue = 2;
                        so.ApplyModifiedPropertiesWithoutUndo();
                        VerneBootstrap.Note("Input handling set to Both. Unity may ask to restart the editor: say yes, then the game uses keyboard, mouse and gamepad.");
                    }
                    else VerneBootstrap.Note("Input handling already Both.");
                }
            }
            VerneBootstrap.Note("Colour space Linear, Direct3D 11, 1920×1080 borderless.");
        }

        public static void TagsAndLayers()
        {
            var tm = AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/TagManager.asset");
            var so = new SerializedObject(tm[0]);
            var layers = so.FindProperty("layers");
            for (int i = 0; i < LayerNames.Length; i++)
            {
                var e = layers.GetArrayElementAtIndex(8 + i);
                if (string.IsNullOrEmpty(e.stringValue) || e.stringValue == LayerNames[i]) e.stringValue = LayerNames[i];
                else VerneBootstrap.Note($"Layer {8 + i} is already '{e.stringValue}', kept.");
            }
            so.ApplyModifiedPropertiesWithoutUndo();
            // held items never collide with anything; creatures don't collide with each other
            for (int l = 0; l < 32; l++) Physics.IgnoreLayerCollision(HeldItemLayer, l, true);
            Physics.IgnoreLayerCollision(CreatureLayer, CreatureLayer, true);
            VerneBootstrap.Note("Layers: " + string.Join(", ", LayerNames));
        }

        public static void PhysicsAndTime()
        {
            Time.fixedDeltaTime = 1f / 50f;
            Time.maximumDeltaTime = 1f / 10f;
            Physics.defaultContactOffset = 0.01f;
            Physics.autoSyncTransforms = false;
            Physics.reuseCollisionCallbacks = true;
        }

        public static void TextureImport()
        {
            int n = 0;
            foreach (var guid in AssetDatabase.FindAssets("t:Texture2D", new[] { "Assets/Verne" }))
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                var ti = AssetImporter.GetAtPath(path) as TextureImporter;
                if (ti == null) continue;
                bool card = path.Contains("/VerneCards/");
                bool normal = Path.GetFileNameWithoutExtension(path).EndsWith("_n");
                bool changed = false;
                if (ti.maxTextureSize != 1024) { ti.maxTextureSize = 1024; changed = true; }
                if (normal && ti.textureType != TextureImporterType.NormalMap) { ti.textureType = TextureImporterType.NormalMap; changed = true; }
                if (card && ti.mipmapEnabled) { ti.mipmapEnabled = false; changed = true; }
                if (ti.textureCompression != TextureImporterCompression.Compressed) { ti.textureCompression = TextureImporterCompression.Compressed; changed = true; }
                if (!card && ti.anisoLevel < 4) { ti.anisoLevel = 4; changed = true; }
                if (changed) { ti.SaveAndReimport(); n++; }
            }
            VerneBootstrap.Note($"{n} textures re-imported.");
        }

        public static void Fonts()
        {
            string outDir = VerneBootstrap.Root + "/Resources/VerneFonts";
            VerneBootstrap.EnsureFolder(outDir);
            string chars = " !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~" +
                           "ÀÂÄÆÇÈÉÊËÎÏÔŒÙÛÜàâäæçèéêëîïôœùûüÿ°·—–‘’“”…′″×½¼¾";
            int made = 0;
            foreach (var guid in AssetDatabase.FindAssets("t:Font", new[] { VerneBootstrap.Root + "/Fonts" }))
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                var font = AssetDatabase.LoadAssetAtPath<Font>(path);
                if (font == null) continue;
                string name = Path.GetFileNameWithoutExtension(path) + " SDF";
                string assetPath = outDir + "/" + name + ".asset";
                if (AssetDatabase.LoadAssetAtPath<TMP_FontAsset>(assetPath) != null) continue;
                var fa = TMP_FontAsset.CreateFontAsset(font, 72, 8, GlyphRenderMode.SDFAA, 1024, 1024, AtlasPopulationMode.Dynamic, true);
                if (fa == null) { VerneBootstrap.Note("Could not create " + name); continue; }
                fa.name = name;
                AssetDatabase.CreateAsset(fa, assetPath);
                fa.atlasTextures[0].name = name + " Atlas";
                AssetDatabase.AddObjectToAsset(fa.atlasTextures[0], fa);
                fa.material.name = name + " Material";
                AssetDatabase.AddObjectToAsset(fa.material, fa);
                fa.TryAddCharacters(chars, out string missing);
                EditorUtility.SetDirty(fa);
                made++;
                if (!string.IsNullOrEmpty(missing)) VerneBootstrap.Note($"{name}: no glyphs for '{missing}'");
            }
            AssetDatabase.SaveAssets();
            VerneBootstrap.Note($"{made} font assets created in {outDir}.");
        }

        // ---------------------------------------------------------------- URP
        struct Tier
        {
            public string name; public float scale; public bool fsr; public float shadowDist; public int shadowRes, cascades, addLights; public bool soft;
        }

        static readonly Tier[] Tiers =
        {
            new Tier { name = "Light",    scale = 0.70f, fsr = true,  shadowDist = 25f, shadowRes = 1024, cascades = 1, addLights = 4, soft = false },
            new Tier { name = "Balanced", scale = 0.80f, fsr = true,  shadowDist = 35f, shadowRes = 2048, cascades = 2, addLights = 6, soft = false },
            new Tier { name = "Full",     scale = 1.00f, fsr = false, shadowDist = 50f, shadowRes = 2048, cascades = 2, addLights = 8, soft = true  },
        };

        public static UniversalRendererData RendererData;
        public static UniversalRenderPipelineAsset[] PipelineAssets = new UniversalRenderPipelineAsset[3];

        public static void RenderPipelines()
        {
            string dir = VerneBootstrap.Generated + "/Rendering";
            string rdPath = dir + "/Verne_Renderer.asset";
            var rd = AssetDatabase.LoadAssetAtPath<UniversalRendererData>(rdPath);
            if (rd == null)
            {
                rd = ScriptableObject.CreateInstance<UniversalRendererData>();
                rd.postProcessData = AssetDatabase.LoadAssetAtPath<PostProcessData>("Packages/com.unity.render-pipelines.universal/Runtime/Data/PostProcessData.asset");
                AssetDatabase.CreateAsset(rd, rdPath);
            }
            var rso = new SerializedObject(rd);
            Set(rso, "m_RenderingMode", 0);          // Forward: cheapest on an integrated GPU with few lights
            Set(rso, "m_DepthPrimingMode", 0);
            Set(rso, "m_IntermediateTextureMode", 0); // Auto
            rso.ApplyModifiedPropertiesWithoutUndo();
            RendererFeatures.Install(rd);
            RendererData = rd;

            for (int i = 0; i < Tiers.Length; i++)
            {
                var t = Tiers[i];
                string path = dir + "/Verne_URP_" + t.name + ".asset";
                var a = AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>(path);
                if (a == null)
                {
                    a = UniversalRenderPipelineAsset.Create(rd);
                    AssetDatabase.CreateAsset(a, path);
                }
                a.renderScale = t.scale;
                a.upscalingFilter = t.fsr ? UpscalingFilterSelection.FSR : UpscalingFilterSelection.Auto;
                a.fsrOverrideSharpness = true;
                a.fsrSharpness = 0.75f;
                a.supportsHDR = true;
                a.msaaSampleCount = 1;
                a.supportsCameraDepthTexture = true;
                a.supportsCameraOpaqueTexture = false;
                a.shadowDistance = t.shadowDist;
                a.shadowCascadeCount = t.cascades;
                a.cascade2Split = 0.3f;
                a.mainLightShadowmapResolution = t.shadowRes;
                a.maxAdditionalLightsCount = t.addLights;
                a.shadowDepthBias = 1.0f;
                a.shadowNormalBias = 0.8f;
                a.useSRPBatcher = true;
                // a.supportsDynamicBatching = false;  (removed in Unity 6.6)
                a.colorGradingMode = ColorGradingMode.HighDynamicRange;
                a.colorGradingLutSize = 32;
                var so = new SerializedObject(a);
                Set(so, "m_MainLightRenderingMode", 1);
                Set(so, "m_MainLightShadowsSupported", true);
                Set(so, "m_AdditionalLightsRenderingMode", 1);
                Set(so, "m_AdditionalLightsPerObjectLimit", Mathf.Min(t.addLights, 8));
                Set(so, "m_AdditionalLightShadowsSupported", i == 2);
                Set(so, "m_SoftShadowsSupported", t.soft);
                Set(so, "m_ReflectionProbeBlending", i > 0);
                so.ApplyModifiedPropertiesWithoutUndo();
                EditorUtility.SetDirty(a);
                PipelineAssets[i] = a;
            }

            GraphicsSettings.defaultRenderPipeline = PipelineAssets[1];
            // URP's FBX material preprocessor only acts when URP is active at import time: re-import the models now that it is
            foreach (var guid in AssetDatabase.FindAssets("t:Model", new[] { VerneBootstrap.Root + "/Models" }))
                AssetDatabase.ImportAsset(AssetDatabase.GUIDToAssetPath(guid), ImportAssetOptions.ForceUpdate);

            // quality levels: exactly Light, Balanced, Full
            var qs = AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/QualitySettings.asset")[0];
            var q = new SerializedObject(qs);
            var arr = q.FindProperty("m_QualitySettings");
            arr.arraySize = 3;
            for (int i = 0; i < 3; i++)
            {
                var e = arr.GetArrayElementAtIndex(i);
                SetRel(e, "name", Tiers[i].name);
                var crp = e.FindPropertyRelative("customRenderPipeline");
                if (crp != null) crp.objectReferenceValue = PipelineAssets[i];
                SetRel(e, "pixelLightCount", Tiers[i].addLights);
                SetRel(e, "vSyncCount", 0);
                SetRel(e, "antiAliasing", 0);
                SetRel(e, "anisotropicTextures", i == 0 ? 1 : 2);
                SetRel(e, "softParticles", i > 0);
                SetRel(e, "realtimeReflectionProbes", false);
                SetRel(e, "lodBias", i == 0 ? 0.7f : (i == 1 ? 1f : 1.5f));
                SetRel(e, "maximumLODLevel", 0);
                SetRel(e, "particleRaycastBudget", i == 0 ? 64 : 256);
                SetRel(e, "skinWeights", i == 0 ? 2 : 4);
                SetRel(e, "globalTextureMipmapLimit", 0);
                SetRel(e, "asyncUploadTimeSlice", 2);
                SetRel(e, "asyncUploadBufferSize", 16);
            }
            var cur = q.FindProperty("m_CurrentQuality");
            if (cur != null) cur.intValue = 1;
            var per = q.FindProperty("m_PerPlatformDefaultQuality");
            if (per != null)
                for (int i = 0; i < per.arraySize; i++)
                {
                    var e = per.GetArrayElementAtIndex(i);
                    var second = e.FindPropertyRelative("second");
                    if (second != null) second.intValue = 1;
                }
            q.ApplyModifiedPropertiesWithoutUndo();
            AssetDatabase.SaveAssets();
            VerneBootstrap.Note("URP assets: Light (0.70× + FSR, 1 cascade, 25 m shadows), Balanced (0.80× + FSR, 2 cascades), Full (1.0×, soft shadows).");
            VerneBootstrap.Note("Quality levels now: " + string.Join(", ", QualitySettings.names) + "; default Balanced; the game picks Light on integrated GPUs on first run.");
        }

        static void Set(SerializedObject so, string prop, int v) { var p = so.FindProperty(prop); if (p != null) p.intValue = v; else VerneBootstrap.Note("missing property " + prop); }
        static void Set(SerializedObject so, string prop, bool v) { var p = so.FindProperty(prop); if (p != null) p.boolValue = v; else VerneBootstrap.Note("missing property " + prop); }
        static void SetRel(SerializedProperty e, string prop, int v) { var p = e.FindPropertyRelative(prop); if (p != null) { if (p.propertyType == SerializedPropertyType.Boolean) p.boolValue = v != 0; else p.intValue = v; } }
        static void SetRel(SerializedProperty e, string prop, bool v) { var p = e.FindPropertyRelative(prop); if (p != null) { if (p.propertyType == SerializedPropertyType.Boolean) p.boolValue = v; else p.intValue = v ? 1 : 0; } }
        static void SetRel(SerializedProperty e, string prop, float v) { var p = e.FindPropertyRelative(prop); if (p != null) p.floatValue = v; }
        static void SetRel(SerializedProperty e, string prop, string v) { var p = e.FindPropertyRelative(prop); if (p != null) p.stringValue = v; }

        // ---------------------------------------------------------------- grades
        public static void VolumeProfiles()
        {
            // underwater: split-toning keeps the shadows in the cold of the water and warms whatever the sun or a lamp reaches,
            // so colour comes alive where the light is (GUM: INSIDE, but vibrant, not bleak)
            Grade("Title", exposure: 0.0f, contrast: 22f, saturation: -12f, bloom: 0.8f, vignette: 0.34f, tint: new Color(0.92f, 1.0f, 1.04f),
                  splitShadows: new Color(0.16f, 0.32f, 0.40f), splitHighlights: new Color(0.55f, 0.60f, 0.62f));
            // aboard: a hand-coloured 1870s engraving: umber shadows, ivory lights, oxblood and verdigris, nothing pure white
            Grade("Nautilus", exposure: -0.15f, contrast: 18f, saturation: -10f, bloom: 0.45f, vignette: 0.3f, tint: new Color(1.04f, 0.98f, 0.88f),
                  splitShadows: new Color(0.32f, 0.26f, 0.2f), splitHighlights: new Color(0.62f, 0.55f, 0.42f));
            Grade("Mission1", exposure: 0.0f, contrast: 22f, saturation: -6f, bloom: 0.75f, vignette: 0.34f, tint: new Color(0.92f, 1.0f, 1.04f),
                  splitShadows: new Color(0.16f, 0.34f, 0.40f), splitHighlights: new Color(0.52f, 0.60f, 0.62f));
            Grade("Mission2", exposure: -0.35f, contrast: 26f, saturation: -10f, bloom: 0.9f, vignette: 0.38f, tint: new Color(0.95f, 0.98f, 1.04f),
                  splitShadows: new Color(0.14f, 0.18f, 0.30f), splitHighlights: new Color(0.70f, 0.48f, 0.34f));
        }

        public static VolumeProfile Grade(string scene, float exposure, float contrast, float saturation, float bloom, float vignette, Color tint,
                                          Color splitShadows = default, Color splitHighlights = default)
        {
            string path = VerneBootstrap.Generated + "/Profiles/Grade_" + scene + ".asset";
            var old = AssetDatabase.LoadAssetAtPath<VolumeProfile>(path);
            if (old != null) AssetDatabase.DeleteAsset(path);
            var p = ScriptableObject.CreateInstance<VolumeProfile>();
            AssetDatabase.CreateAsset(p, path);

            var tm = Add<Tonemapping>(p); tm.mode.Override(TonemappingMode.Neutral);
            var b = Add<Bloom>(p); b.threshold.Override(1.0f); b.intensity.Override(bloom); b.scatter.Override(0.65f); b.highQualityFiltering.Override(false);
            var ca = Add<ColorAdjustments>(p); ca.postExposure.Override(exposure); ca.contrast.Override(contrast); ca.saturation.Override(saturation); ca.colorFilter.Override(tint);
            if (splitShadows.maxColorComponent > 0f)
            {
                var st = Add<SplitToning>(p); st.shadows.Override(splitShadows); st.highlights.Override(splitHighlights); st.balance.Override(-10f);
            }
            var v = Add<Vignette>(p); v.intensity.Override(vignette); v.smoothness.Override(0.45f); v.color.Override(new Color(0.02f, 0.025f, 0.035f));
            AssetDatabase.SaveAssets();
            return p;
        }

        static T Add<T>(VolumeProfile p) where T : VolumeComponent
        {
            var c = p.Add<T>(true);
            c.name = typeof(T).Name;
            AssetDatabase.AddObjectToAsset(c, p);
            return c;
        }

        public static VolumeProfile LoadGrade(string scene) => AssetDatabase.LoadAssetAtPath<VolumeProfile>(VerneBootstrap.Generated + "/Profiles/Grade_" + scene + ".asset");
    }
}
