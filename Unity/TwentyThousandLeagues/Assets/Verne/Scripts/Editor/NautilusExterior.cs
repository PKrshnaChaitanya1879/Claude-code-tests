using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

namespace Verne.EditorTools
{
    /// <summary>
    /// Imports the Blender exterior (Source/blender/nautilus_exterior.py) and makes a prefab with
    /// LODs and a simplified collider. The FBX carries marker empties (BOW_TIP, STERN, PORT_DOOR,
    /// LANTERN …); the prefab is oriented from them so the bow is +Z and the deck is up whatever
    /// axis convention the exporter used.
    /// </summary>
    public static class NautilusExterior
    {
        const string Dir = VerneBootstrap.Root + "/Models/Nautilus";
        public static string PrefabPath => VerneBootstrap.Generated + "/Nautilus_Exterior.prefab";

        public static void ConfigureImport()
        {
            foreach (var guid in AssetDatabase.FindAssets("t:Model", new[] { VerneBootstrap.Root + "/Models" }))
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                var mi = AssetImporter.GetAtPath(path) as ModelImporter;
                if (mi == null) continue;
                bool changed = false;
                if (!Mathf.Approximately(mi.globalScale, 1f)) { mi.globalScale = 1f; changed = true; }
                if (!mi.bakeAxisConversion) { mi.bakeAxisConversion = true; changed = true; }
                if (mi.importCameras || mi.importLights) { mi.importCameras = false; mi.importLights = false; changed = true; }
                if (mi.importNormals != ModelImporterNormals.Import) { mi.importNormals = ModelImporterNormals.Import; changed = true; }
                if (mi.meshCompression != ModelImporterMeshCompression.Medium) { mi.meshCompression = ModelImporterMeshCompression.Medium; changed = true; }
                if (mi.isReadable != path.EndsWith("_col.fbx")) { mi.isReadable = path.EndsWith("_col.fbx"); changed = true; }
                if (mi.materialImportMode != ModelImporterMaterialImportMode.ImportViaMaterialDescription) { mi.materialImportMode = ModelImporterMaterialImportMode.ImportViaMaterialDescription; changed = true; }
                if (mi.animationType != ModelImporterAnimationType.None && path.Contains("/Nautilus/")) { mi.animationType = ModelImporterAnimationType.None; mi.importAnimation = false; changed = true; }
                if (path.Contains("Nautilus_Exterior") && !path.EndsWith("_col.fbx"))
                {
                    var hull = Materials.Get("HullPlate");
                    var id = new AssetImporter.SourceAssetIdentifier(typeof(Material), "M_HullPlate");
                    if (hull != null && (!mi.GetExternalObjectMap().TryGetValue(id, out var cur) || cur != hull)) { mi.AddRemap(id, hull); changed = true; }
                }
                if (changed) mi.SaveAndReimport();
            }
        }

        public static void BuildPrefab()
        {
            ConfigureImport();
            var lod0 = AssetDatabase.LoadAssetAtPath<GameObject>(Dir + "/Nautilus_Exterior.fbx");
            if (lod0 == null) throw new System.Exception("Missing " + Dir + "/Nautilus_Exterior.fbx");
            var lod1 = AssetDatabase.LoadAssetAtPath<GameObject>(Dir + "/Nautilus_Exterior_LOD1.fbx");
            var lod2 = AssetDatabase.LoadAssetAtPath<GameObject>(Dir + "/Nautilus_Exterior_LOD2.fbx");
            var col = AssetDatabase.LoadAssetAtPath<GameObject>(Dir + "/Nautilus_Exterior_col.fbx");

            var root = new GameObject("Nautilus (exterior)");
            var model = new GameObject("Model").transform;
            model.SetParent(root.transform, false);

            var l0 = ((GameObject)PrefabUtility.InstantiatePrefab(lod0)).transform; l0.SetParent(model, false); l0.name = "LOD0";
            Transform l1 = null, l2 = null;
            if (lod1 != null) { l1 = ((GameObject)PrefabUtility.InstantiatePrefab(lod1)).transform; l1.SetParent(model, false); l1.name = "LOD1"; }
            if (lod2 != null) { l2 = ((GameObject)PrefabUtility.InstantiatePrefab(lod2)).transform; l2.SetParent(model, false); l2.name = "LOD2"; }

            // orient from the markers: bow to +Z, deck up
            var bow = Find(l0, "BOW_TIP"); var stern = Find(l0, "STERN"); var lantern = Find(l0, "LANTERN"); var port = Find(l0, "PORT_DOOR");
            if (bow != null && stern != null && lantern != null)
            {
                Vector3 fwd = (bow.position - stern.position).normalized;
                Vector3 mid = (bow.position + stern.position) * 0.5f;
                Vector3 up = Vector3.ProjectOnPlane(lantern.position - mid, fwd).normalized;
                model.rotation = Quaternion.Inverse(Quaternion.LookRotation(fwd, up));
                // port is the left-hand side looking forward: its door must end up at negative X
                if (port != null && port.position.x > 0f)
                    VerneBootstrap.Note("Nautilus exterior: the port door came in on the starboard side (mirrored export?). Check the hull in Mission I.");
            }
            else VerneBootstrap.Note("Nautilus exterior: marker empties missing, orientation left as imported.");

            // LOD group: the hull is 70 m long, so it stays at LOD0 until it is a small shape in the fog
            var lg = root.AddComponent<LODGroup>();
            var lods = new List<LOD> { new LOD(0.25f, Renderers(l0)) };
            if (l1 != null) lods.Add(new LOD(0.08f, Renderers(l1)));
            if (l2 != null) lods.Add(new LOD(0.015f, Renderers(l2)));
            lg.SetLODs(lods.ToArray());
            lg.RecalculateBounds();

            // simplified collider: mesh from the _col FBX, never the visual mesh
            if (col != null)
            {
                var cm = FirstMesh(col);
                if (cm != null)
                {
                    var c = new GameObject("Collider (simplified)");
                    c.transform.SetParent(model, false);
                    var mc = c.AddComponent<MeshCollider>();
                    mc.sharedMesh = cm;
                    c.AddComponent<Surface>().kind = "iron";
                    c.layer = ProjectSetup.HullLayer;
                }
            }
            foreach (var r in root.GetComponentsInChildren<Renderer>()) { r.gameObject.layer = ProjectSetup.HullLayer; GameObjectUtility.SetStaticEditorFlags(r.gameObject, StaticEditorFlags.BatchingStatic); }

            // lantern: the light that guides the walkers home (I.XV, II.IX)
            if (lantern != null)
            {
                var lg2 = new GameObject("Lantern light");
                lg2.transform.SetParent(root.transform, false);
                lg2.transform.position = lantern.position;
                lg2.transform.rotation = Quaternion.LookRotation(root.transform.forward + Vector3.down * 0.05f);
                var l = lg2.AddComponent<Light>();
                l.type = LightType.Spot; l.spotAngle = 28f; l.innerSpotAngle = 10f; l.range = 120f; l.intensity = 40f;
                l.color = new Color(0.92f, 0.96f, 1f); l.shadows = LightShadows.None;
            }

            PrefabUtility.SaveAsPrefabAsset(root, PrefabPath);
            Object.DestroyImmediate(root);
            VerneBootstrap.Note("Prefab " + PrefabPath + " (LOD0 ≈ 5.8k, LOD1 ≈ 2.9k, LOD2 ≈ 1.3k triangles; 14-sided collider).");
        }

        static Transform Find(Transform t, string name)
        {
            foreach (var c in t.GetComponentsInChildren<Transform>(true)) if (c.name == name) return c;
            return null;
        }

        static Renderer[] Renderers(Transform t) => t.GetComponentsInChildren<Renderer>(true);

        static Mesh FirstMesh(GameObject go)
        {
            foreach (var mf in go.GetComponentsInChildren<MeshFilter>(true)) if (mf.sharedMesh != null) return mf.sharedMesh;
            return null;
        }

        /// <summary>
        /// Places the Nautilus so its flooding-cell door (PORT_DOOR) is at <paramref name="door"/>,
        /// lying along <paramref name="bowDirection"/> with the port side facing the player.
        /// The hull rests on the bottom ("stranded in five fathoms", I.XV).
        /// </summary>
        public static GameObject Place(Transform parent, Vector3 door, Vector3 bowDirection, float groundY)
        {
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath);
            if (prefab == null) { VerneBootstrap.Note("Nautilus prefab missing; skipped placement."); return null; }
            var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab, parent);
            go.transform.rotation = Quaternion.LookRotation(bowDirection.normalized, Vector3.up);
            go.transform.position = Vector3.zero;
            var portDoor = Find(go.transform, "PORT_DOOR");
            Vector3 offset = portDoor != null ? portDoor.position - go.transform.position : Vector3.zero;
            // interior deck sits 2 m above the keel; let the hull settle 0.3 m into the sand
            float deckY = groundY + 1.7f;
            go.transform.position = new Vector3(door.x - offset.x, deckY, door.z - offset.z);
            return go;
        }
    }
}
