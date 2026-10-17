using UnityEditor;
using UnityEngine;

namespace Verne.EditorTools
{
    /// <summary>
    /// The Blender interior (Source/blender/nautilus_interior_fore.py): rooms at the book's dimensions,
    /// laid out exactly on the greybox so the greybox boxes can stay as invisible colliders.
    /// Furniture objects named "*__col" get their own MeshColliders (static, low-poly).
    /// </summary>
    public static class NautilusInterior
    {
        public const string Fore = "Nautilus_Interior_Fore", Aft = "Nautilus_Interior_Aft";
        static string FbxPath(string block) => VerneBootstrap.Root + "/Models/Nautilus/" + block + ".fbx";
        static string PrefabPath(string block) => VerneBootstrap.Generated + "/" + block + ".prefab";

        static readonly (string from, string to)[] Remap =
        {
            ("M_ebony", "Ebony"), ("M_oak", "Oak"), ("M_carpet", "Carpet"), ("M_tapestry", "Tapestry"), ("M_plaster", "Plaster"),
            ("M_marble", "Marble"), ("M_brass", "Brass"), ("M_iron", "Iron"), ("M_ironpaint", "IronPaint"), ("M_leather", "Leather"),
            ("M_ceiling", "LuminousCeiling"), ("M_linen", "Linen"), ("M_grate", "Iron"), ("M_glass", "Glass"),
        };

        /// <summary>Imports one Blender block, swaps its flat colours for the project's textured CC0 materials and
        /// the saloon canvases for the Met paintings, gives furniture its colliders, and saves a prefab.
        /// Rebuilt on every Build Everything so a newer FBX is always used.</summary>
        public static bool BuildPrefab(string block)
        {
            var mi = AssetImporter.GetAtPath(FbxPath(block)) as ModelImporter;
            if (mi == null) return false;
            foreach (var (from, to) in Remap)
            {
                var m = Materials.Get(to);
                if (m != null) mi.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), from), m);
            }
            foreach (var guid in AssetDatabase.FindAssets("t:Texture2D", new[] { VerneBootstrap.Root + "/Textures/Paint" }))
            {
                string file = System.IO.Path.GetFileNameWithoutExtension(AssetDatabase.GUIDToAssetPath(guid));   // p437373
                if (!file.StartsWith("p")) continue;
                var m = Materials.Paint(file.Substring(1));
                if (m != null) mi.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), "M_pic_" + file.Substring(1)), m);
            }
            mi.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), "M_seadoor"), Materials.Emissive("SeaDoor", new Color(0.02f, 0.12f, 0.14f), new Color(0.05f, 0.32f, 0.36f)));
            mi.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), "M_bulb"), Materials.Emissive("Bulb", new Color(1f, 0.95f, 0.85f), new Color(4f, 3.6f, 3f)));
            mi.AddRemap(new AssetImporter.SourceAssetIdentifier(typeof(Material), "M_coal"), Materials.Emissive("Coal", new Color(0.6f, 0.2f, 0.05f), new Color(3f, 0.9f, 0.2f)));
            mi.SaveAndReimport();
            var src = AssetDatabase.LoadAssetAtPath<GameObject>(FbxPath(block));
            if (src == null) return false;
            var root = new GameObject(block == Fore ? "Nautilus interior, fore (art)" : "Nautilus interior, aft (art)");
            root.AddComponent<NautilusArtMarker>();
            var inst = ((GameObject)PrefabUtility.InstantiatePrefab(src)).transform;
            inst.SetParent(root.transform, false);
            if (!Markers.Orient(inst, out string note)) VerneBootstrap.Note(block + ": " + note);
            int cols = 0;
            foreach (var mf in inst.GetComponentsInChildren<MeshFilter>(true))
            {
                var go = mf.gameObject;
                bool kit = go.name.StartsWith("kit_") || go.name.StartsWith("rot_");   // these move: never static
                if (!kit) GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic | StaticEditorFlags.ContributeGI | StaticEditorFlags.OccluderStatic | StaticEditorFlags.OccludeeStatic | StaticEditorFlags.ReflectionProbeStatic);
                if (go.name.Contains("__col") && !go.name.Contains("shell"))
                {
                    var mc = go.AddComponent<MeshCollider>();
                    mc.sharedMesh = mf.sharedMesh;
                    cols++;
                }
                var mr = go.GetComponent<MeshRenderer>();
                if (mr != null && (go.name.Contains("bulb") || go.name.Contains("glow") || go.name.Contains("canvases"))) mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            }
            PrefabUtility.SaveAsPrefabAsset(root, PrefabPath(block));
            Object.DestroyImmediate(root);
            VerneBootstrap.Note($"{block} prefab: {cols} furniture colliders.");
            return true;
        }

        /// <summary>Places one block's art in the Nautilus scene; null when its FBX is not there (the greybox stays).</summary>
        public static Transform Place(Transform ship, string block = Fore)
        {
            if (!BuildPrefab(block)) return null;
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath(block));
            if (prefab == null) return null;
            var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab, ship);
            go.transform.localPosition = Vector3.zero;
            go.transform.localRotation = Quaternion.identity;
            return go.transform;
        }
    }

    /// <summary>Shared orientation from the BOW_TIP / STERN / LANTERN / PORT_DOOR marker empties in our FBX files.</summary>
    public static class Markers
    {
        public static Transform Find(Transform t, string name)
        {
            foreach (var c in t.GetComponentsInChildren<Transform>(true)) if (c.name == name) return c;
            return null;
        }

        /// <summary>Rotates <paramref name="model"/> (about its own origin) so the bow is +Z and the deck is up; checks that port is −X.</summary>
        public static bool Orient(Transform model, out string note)
        {
            note = "";
            var bow = Find(model, "BOW_TIP"); var stern = Find(model, "STERN"); var up = Find(model, "LANTERN"); var port = Find(model, "PORT_DOOR");
            if (bow == null || stern == null || up == null) { note = "marker empties missing; orientation left as imported."; return false; }
            Vector3 fwd = (bow.position - stern.position).normalized;
            Vector3 mid = (bow.position + stern.position) * 0.5f;
            Vector3 u = Vector3.ProjectOnPlane(up.position - mid, fwd).normalized;
            model.rotation = Quaternion.Inverse(Quaternion.LookRotation(fwd, u)) * model.rotation;
            if (port != null && port.position.x - model.position.x > 0f) { note = "port came in on the starboard side (mirrored export?)."; return false; }
            return true;
        }
    }
}
