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
        const string Fbx = VerneBootstrap.Root + "/Models/Nautilus/Nautilus_Interior_Fore.fbx";
        static string PrefabPath => VerneBootstrap.Generated + "/Nautilus_Interior_Fore.prefab";

        public static bool BuildPrefab()
        {
            var src = AssetDatabase.LoadAssetAtPath<GameObject>(Fbx);
            if (src == null) return false;
            var root = new GameObject("Nautilus interior (art)");
            root.AddComponent<NautilusArtMarker>();
            var inst = ((GameObject)PrefabUtility.InstantiatePrefab(src)).transform;
            inst.SetParent(root.transform, false);
            if (!Markers.Orient(inst, out string note)) VerneBootstrap.Note("Interior: " + note);
            int cols = 0;
            foreach (var mf in inst.GetComponentsInChildren<MeshFilter>(true))
            {
                var go = mf.gameObject;
                GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic | StaticEditorFlags.ContributeGI | StaticEditorFlags.OccluderStatic | StaticEditorFlags.OccludeeStatic | StaticEditorFlags.ReflectionProbeStatic);
                if (go.name.Contains("__col") && !go.name.Contains("shell"))
                {
                    var mc = go.AddComponent<MeshCollider>();
                    mc.sharedMesh = mf.sharedMesh;
                    cols++;
                }
            }
            PrefabUtility.SaveAsPrefabAsset(root, PrefabPath);
            Object.DestroyImmediate(root);
            VerneBootstrap.Note($"Interior prefab: {cols} furniture colliders.");
            return true;
        }

        /// <summary>Places the forward-block art in the Nautilus scene; false when the FBX is not there (greybox stays).</summary>
        public static bool Place(Transform ship)
        {
            if (AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath) == null && !BuildPrefab()) return false;
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath);
            if (prefab == null) return false;
            var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab, ship);
            go.transform.localPosition = Vector3.zero;
            go.transform.localRotation = Quaternion.identity;
            return true;
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
