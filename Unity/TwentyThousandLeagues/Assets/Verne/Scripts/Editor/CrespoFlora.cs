using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

namespace Verne.EditorTools
{
    /// <summary>
    /// M4: lays the Blender flora (Source/blender/crespo_flora.py) along Mission I's route, in the book's order
    /// (I.XV–XVI, XXIII): the sandy plain with its sea-stars, shells, fungi and anemones → the prairie of red algae
    /// and peacock fans → the forest of Crespo's rigid laminaries ("the region of perpendicularity") → the dark
    /// coral gallery under arches hung with pendants → the glade of the coral cemetery, ringed by petrified trees
    /// with garlands of sea-bindweed, the coral cross on its rocks and the low white mounds.
    /// Deterministic (seeded), with simple colliders on everything taller than the ankle.
    /// </summary>
    public static class CrespoFlora
    {
        const string Fbx = VerneBootstrap.Root + "/Models/Crespo/Crespo_Flora.fbx";
        static readonly Dictionary<string, GameObject> s_Src = new Dictionary<string, GameObject>();
        static System.Func<Vector3, float> s_Ground;
        static System.Random s_R;
        static Transform s_Root;
        public static int Placed;
        static readonly List<(GameObject go, string name)> s_NeedCollider = new List<(GameObject, string)>();

        public static bool Place(Transform parent, System.Func<Vector3, float> groundAt)
        {
            var fbx = AssetDatabase.LoadAssetAtPath<GameObject>(Fbx);
            if (fbx == null) return false;
            s_Src.Clear();
            foreach (var t in fbx.GetComponentsInChildren<Transform>(true))
                if (t.GetComponent<MeshFilter>() != null) s_Src[t.name] = t.gameObject;
            s_Ground = groundAt; s_R = new System.Random(1871); Placed = 0; s_NeedCollider.Clear();
            s_Root = new GameObject("Flora of Crespo (Blender)").transform;
            s_Root.SetParent(parent, false);
            s_Collect = true;

            // 1. the sandy plain (z 3–35)
            Scatter(new[] { "sea_star_red", "sea_star_orange", "sea_star_violet" }, 70, -22, 22, 3, 36, 1.0f, 1.6f);
            Scatter(new[] { "shells" }, 18, -20, 20, 3, 36, 0.9f, 1.3f);
            Scatter(new[] { "fungia" }, 12, -18, 18, 5, 36, 0.9f, 1.3f);
            Scatter(new[] { "anemone" }, 14, -18, 18, 5, 36, 0.8f, 1.5f, lane: 2.2f);
            Scatter(new[] { "cup_corals", "sponge" }, 14, -18, 18, 8, 40, 0.9f, 1.3f, lane: 2.2f);
            Scatter(new[] { "brain_coral", "brain_coral_teal" }, 6, -16, 16, 10, 40, 0.7f, 1.4f, lane: 2.5f);
            // 2. the prairie (z 28–46)
            Scatter(new[] { "red_algae", "padina", "acetabularia" }, 110, -20, 20, 22, 48, 1.1f, 2.0f);   // the prairie in colour (look-dev: 70 small ones read bare)
            Scatter(new[] { "fucus" }, 14, -18, 18, 32, 50, 0.9f, 1.3f, lane: 2.2f);
            // 3. the forest (z 44–96): laminaries and alariae, a walkable lane kept clear down the middle
            Scatter(new[] { "laminaria_a", "laminaria_b" }, 130, -26, 26, 44, 96, 0.85f, 1.25f, lane: 2.2f);
            Scatter(new[] { "alaria", "fucus" }, 50, -24, 24, 44, 96, 0.85f, 1.3f, lane: 2.2f);
            Scatter(new[] { "red_algae", "padina" }, 40, -24, 24, 44, 96, 1f, 1.6f);
            // 4. the coral gallery (z 96–106): "a dark gallery" vaulted over, with ragged skylights the sun falls through in shafts;
            //    arches across the way, pendants from their crowns, the coral kingdom on both sides
            Put("gallery_vault", new Vector3(0, 0, 101f), YawAlong("gallery_vault", 0f), 1f);
            foreach (float z in new[] { 97.5f, 101f, 104.5f })
            {
                var a = Put("coral_arch", new Vector3(0, 0, z), YawAlong("coral_arch", 90f), 1f + (float)s_R.NextDouble() * 0.1f);   // spans the way
                float g = s_Ground(new Vector3(0, 0, z));
                for (int k = 0; k < 3; k++)
                    PutAt("coral_pendant", new Vector3(-1.2f + k * 1.2f, g + 3.85f, z + (float)(s_R.NextDouble() - 0.5) * 0.3f), (float)s_R.NextDouble() * 360f, 0.9f);
            }
            Scatter(new[] { "red_coral", "tuft_coral", "pink_coral", "isis", "gorgonian_fan", "gorgonian_fan_yellow", "basket_star", "cup_corals", "brain_coral" },
                    70, -9, 9, 95, 107, 0.9f, 1.6f, lane: 2.2f);
            // 5. the glade and the cemetery (centre z = 110)
            var c = new Vector3(0, 0, 110);
            Put("coral_cross", c, 0f, 1.0f);
            for (int k = 0; k < 6; k++)    // the graves before the cross
            {
                float x = -3.0f + (k % 3) * 3.0f, z = 106.6f - (k / 3) * 2.6f;
                if (k == 4) continue;      // the new grave, still to be dug (M4 burial)
                Put("grave_mound", new Vector3(x, 0, z), (float)(s_R.NextDouble() - 0.5) * 12f, 1.0f);
            }
            var ring = new List<Vector3>();
            for (int k = 0; k < 9; k++)
            {
                float a = (k / 9f) * Mathf.PI * 2f + 0.3f;
                if (Mathf.Abs(Mathf.DeltaAngle(a * Mathf.Rad2Deg, 270f)) < 22f) continue;   // the way in, from the south
                var p = c + new Vector3(Mathf.Cos(a), 0, Mathf.Sin(a)) * (8.5f + (float)s_R.NextDouble() * 1.5f);
                ring.Add(p);
                Put(k % 2 == 0 ? "coral_tree" : "coral_tree2", p, (float)s_R.NextDouble() * 360f, 1.3f + (float)s_R.NextDouble() * 0.4f);
            }
            for (int k = 0; k + 1 < ring.Count; k++)   // garlands of sea-bindweed between neighbours
            {
                var m = (ring[k] + ring[k + 1]) * 0.5f;
                var d = ring[k + 1] - ring[k];
                float g = s_Ground(m);
                var gar = PutAt("bindweed_garland", new Vector3(m.x, g + 3.4f, m.z), YawAlong("bindweed_garland", Mathf.Atan2(d.x, d.z) * Mathf.Rad2Deg), 1f);
                gar.transform.localScale = LongAxisIsX("bindweed_garland") ? new Vector3(d.magnitude / 4f, 1f, 1f) : new Vector3(1f, 1f, d.magnitude / 4f);
            }
            Scatter(new[] { "red_coral", "isis", "gorgonian_fan", "anemone", "sea_star_red" }, 30, -10, 10, 102, 120, 0.9f, 1.4f, lane: 0f, avoid: c, avoidR: 4.5f);
            // colliders last, so every prop above was grounded on the sea floor and not on another prop
            s_Collect = false;
            foreach (var (go, name) in s_NeedCollider) if (go != null) AddCollider(go, name);
            s_NeedCollider.Clear();
            int living = Animate(s_Root);
            int culled = CullByDistance(s_Root);
            s_Root.gameObject.AddComponent<VerneVisitors>();
            VerneBootstrap.Note($"Mission I flora: {Placed} props from {s_Src.Count} Blender species; {living} sway or close their polyps (Verne/Flora); {culled} fade out by distance (LODGroup), small things sooner.");
            return true;
        }

        // the swell in the weed and the polyps that close: (sway m at 1 m, height of full bend, period scale, polyp depth, wrap)
        static readonly Dictionary<string, (float sway, float h, float speed, float polyp, float wrap)> s_Living =
            new Dictionary<string, (float, float, float, float, float)>
        {
            { "M_kelp",        (0.05f, 3.0f, 0.8f, 0f,    0.35f) },   // Verne's laminaries are "rigid": a slow lean, no flutter
            { "M_kelp_dark",   (0.05f, 3.0f, 0.8f, 0f,    0.35f) },
            { "M_algae_red",   (0.20f, 0.8f, 1.1f, 0f,    0.45f) },   // the fronds of the prairie move most
            { "M_algae_brown", (0.16f, 1.0f, 1.0f, 0f,    0.40f) },
            { "M_anemone",     (0.14f, 0.3f, 1.3f, 0f,    0.30f) },
            { "M_polyp",       (0f,    1.0f, 1.0f, 0.04f, 0.20f) },   // the white polyps on the "Flower of Blood"
        };
        static readonly Dictionary<Material, Material> s_LivingCache = new Dictionary<Material, Material>();

        /// <summary>Moves the weed, the anemones and the coral's polyps onto Verne/Flora (they leave static batching: the sway needs each prop's origin).</summary>
        static int Animate(Transform root)
        {
            var sh = Shader.Find("Verne/Flora");
            if (sh == null) { VerneBootstrap.Note("Verne/Flora shader missing: the flora stays still."); return 0; }
            s_LivingCache.Clear();
            int n = 0;
            foreach (var mr in root.GetComponentsInChildren<MeshRenderer>(true))
            {
                var mats = mr.sharedMaterials;
                bool any = false, sways = false;
                for (int i = 0; i < mats.Length; i++)
                {
                    var src = mats[i];
                    if (src == null) continue;
                    string key = src.name.Replace(" (Instance)", "");
                    if (!s_Living.TryGetValue(key, out var spec)) continue;
                    if (!s_LivingCache.TryGetValue(src, out var m))
                    {
                        string path = VerneBootstrap.Generated + "/Materials/M_Flora_" + key.Substring(2) + ".mat";
                        m = AssetDatabase.LoadAssetAtPath<Material>(path);
                        if (m == null) { m = new Material(sh); AssetDatabase.CreateAsset(m, path); }
                        m.shader = sh;
                        Color c = src.HasProperty("_BaseColor") ? src.GetColor("_BaseColor") : (src.HasProperty("_Color") ? src.GetColor("_Color") : Color.grey);
                        m.SetColor("_BaseColor", c);
                        if (src.HasProperty("_BaseMap") && src.GetTexture("_BaseMap") != null) m.SetTexture("_BaseMap", src.GetTexture("_BaseMap"));
                        m.SetFloat("_Smoothness", src.HasProperty("_Smoothness") ? Mathf.Min(src.GetFloat("_Smoothness"), 0.5f) : 0.3f);
                        m.SetFloat("_Metallic", 0f);
                        m.SetFloat("_Sway", spec.sway); m.SetFloat("_SwayHeight", spec.h); m.SetFloat("_SwaySpeed", spec.speed);
                        m.SetFloat("_Polyp", spec.polyp); m.SetFloat("_Wrap", spec.wrap);
                        m.enableInstancing = true;
                        EditorUtility.SetDirty(m);
                        s_LivingCache[src] = m;
                    }
                    mats[i] = m; any = true; sways |= spec.sway > 0f;
                }
                if (!any) continue;
                mr.sharedMaterials = mats;
                if (sways)
                {
                    var f = GameObjectUtility.GetStaticEditorFlags(mr.gameObject) & ~StaticEditorFlags.BatchingStatic;
                    GameObjectUtility.SetStaticEditorFlags(mr.gameObject, f);
                }
                n++;
            }
            AssetDatabase.SaveAssets();
            return n;
        }

        /// <summary>
        /// Every prop culls itself once it is too small to matter in the water (the fog has it by then): a stem at ~45 m,
        /// a sea-star at ~12 m. Keeps the draw calls of the swaying (unbatched) forest inside the laptop budget.
        /// </summary>
        static int CullByDistance(Transform root)
        {
            int n = 0;
            foreach (Transform t in root)
            {
                var mr = t.GetComponent<MeshRenderer>();
                if (mr == null || t.name.StartsWith("gallery_vault") || t.name.StartsWith("coral_cross")) continue;
                float size = Mathf.Max(mr.bounds.size.x, mr.bounds.size.y, mr.bounds.size.z);
                float dist = Mathf.Clamp(10f + size * 9f, 12f, 48f);
                var lg = t.gameObject.AddComponent<LODGroup>();
                lg.SetLODs(new[] { new LOD(Mathf.Clamp(size / (1.155f * dist), 0.002f, 0.5f), new Renderer[] { mr }) });
                lg.fadeMode = LODFadeMode.None;
                lg.RecalculateBounds();
                n++;
            }
            return n;
        }

        /// <summary>Whether the imported mesh is long along its local X (else Z): the FBX axis conversion decides, so we measure.</summary>
        static bool LongAxisIsX(string name)
        {
            if (!s_Src.TryGetValue(name, out var src)) return true;
            var mf = src.GetComponent<MeshFilter>();
            if (mf == null || mf.sharedMesh == null) return true;
            var sz = mf.sharedMesh.bounds.size;
            return sz.x >= sz.z;
        }

        /// <summary>The yaw that lays a prop's long axis along a world heading (degrees from +Z).</summary>
        static float YawAlong(string name, float heading) => LongAxisIsX(name) ? heading - 90f : heading;

        /// <summary>Places one more prop after Place() (the burial's mound).</summary>
        public static GameObject Spawn(string name, Vector3 pos, float yaw) => s_Root != null ? PutAt(name, pos, yaw, 1f) : null;
        static bool s_Collect;

        /// <summary>Clears placed props within r metres (xz) of p, so a scene's actors stand free.</summary>
        public static void ClearAround(Vector3 p, float r)
        {
            if (s_Root == null) return;
            var kill = new List<GameObject>();
            foreach (Transform t in s_Root)
            {
                var d = t.position - p; d.y = 0f;
                string n = t.name;
                bool keep = n.StartsWith("coral_cross") || n.StartsWith("grave_mound") || n.StartsWith("gallery_vault") || n.StartsWith("coral_arch")
                            || n.StartsWith("coral_pendant") || n.StartsWith("bindweed_garland") || n.StartsWith("coral_tree");
                if (d.magnitude < r && !keep) kill.Add(t.gameObject);
            }
            foreach (var g in kill) { Object.DestroyImmediate(g); Placed--; }
        }

        static void Scatter(string[] names, int count, float x0, float x1, float z0, float z1, float sMin, float sMax, float lane = 0f, Vector3 avoid = default, float avoidR = 0f)
        {
            int tries = 0;
            for (int i = 0; i < count && tries < count * 6; tries++)
            {
                var p = new Vector3(Mathf.Lerp(x0, x1, (float)s_R.NextDouble()), 0, Mathf.Lerp(z0, z1, (float)s_R.NextDouble()));
                if (Mathf.Abs(p.x) < lane) continue;
                if (p.z < 4f && Mathf.Abs(p.x) < 4f) continue;                       // the spawn and the Nautilus' door
                if (avoidR > 0f && (new Vector2(p.x - avoid.x, p.z - avoid.z)).magnitude < avoidR) continue;
                Put(names[s_R.Next(names.Length)], p, (float)s_R.NextDouble() * 360f, Mathf.Lerp(sMin, sMax, (float)s_R.NextDouble()));
                i++;
            }
        }

        static GameObject Put(string name, Vector3 xz, float yaw, float scale)
        {
            return PutAt(name, new Vector3(xz.x, s_Ground(xz) - 0.03f, xz.z), yaw, scale);
        }

        static GameObject PutAt(string name, Vector3 pos, float yaw, float scale)
        {
            if (!s_Src.TryGetValue(name, out var src)) return new GameObject("(missing " + name + ")");
            var go = Object.Instantiate(src, s_Root);
            go.name = name;
            go.transform.SetPositionAndRotation(pos, Quaternion.Euler(0f, yaw, 0f) * src.transform.rotation);
            go.transform.localScale = Vector3.one * scale;
            GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccludeeStatic);
            var mr = go.GetComponent<MeshRenderer>();
            if (mr != null && scale < 1.4f && (name.StartsWith("sea_star") || name == "shells" || name == "fungia" || name == "acetabularia" || name == "padina"))
                mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;   // ankle-high: no shadow cost
            if (s_Root != null && s_R != null && s_NeedCollider != null && s_Collect) s_NeedCollider.Add((go, name)); else AddCollider(go, name);
            Placed++;
            return go;
        }

        /// <summary>Nothing taller than the ankle can be walked through: capsules for stems and trunks, spheres and boxes for the rest.</summary>
        static void AddCollider(GameObject go, string name)
        {
            var mr = go.GetComponent<MeshRenderer>();
            if (mr == null) return;
            Bounds b = mr.bounds;
            var host = new GameObject("collider"); host.transform.SetParent(go.transform, false);
            host.transform.position = new Vector3(b.center.x, b.min.y, b.center.z);
            host.transform.rotation = Quaternion.identity;
            Vector3 ls = go.transform.lossyScale;
            host.transform.localScale = new Vector3(1f / ls.x, 1f / ls.y, 1f / ls.z);   // colliders sized in world metres
            switch (name)
            {
                case "laminaria_a": case "laminaria_b": case "alaria":
                    Capsule(host, 0.14f, b.size.y); break;
                case "coral_tree": case "coral_tree2":
                    Capsule(host, 0.45f * ls.x, b.size.y * 0.55f); break;
                case "coral_arch":
                {
                    Object.DestroyImmediate(host);
                    bool alongX = LongAxisIsX(name);
                    foreach (float sx in new[] { -2.5f, 2.5f })
                    {
                        var leg = new GameObject("leg"); leg.transform.SetParent(go.transform, false);
                        leg.transform.localPosition = alongX ? new Vector3(sx, 0f, 0f) : new Vector3(0f, 0f, sx);
                        var cc = leg.AddComponent<CapsuleCollider>(); cc.radius = 0.7f; cc.height = 3.2f; cc.center = new Vector3(0, 1.6f, 0); cc.direction = 1;
                    }
                    return;
                }
                case "coral_cross":
                {
                    var bc = host.AddComponent<BoxCollider>(); bc.size = new Vector3(1.4f, 0.9f, 1.4f); bc.center = new Vector3(0, 0.45f, 0);
                    Capsule(host, 0.16f, b.size.y); break;
                }
                case "grave_mound":
                {
                    var bc = host.AddComponent<BoxCollider>(); bc.size = new Vector3(b.size.x, Mathf.Max(0.15f, b.size.y), b.size.z); bc.center = new Vector3(0, bc.size.y * 0.5f, 0); break;
                }
                case "brain_coral": case "brain_coral_teal":
                {
                    var sc = host.AddComponent<SphereCollider>(); sc.radius = Mathf.Max(b.extents.x, b.extents.z) * 0.9f; sc.center = new Vector3(0, b.size.y * 0.3f, 0); break;
                }
                case "gallery_vault":
                {
                    Object.DestroyImmediate(host);
                    var mc = go.AddComponent<MeshCollider>(); mc.sharedMesh = go.GetComponent<MeshFilter>().sharedMesh;
                    var r0 = go.GetComponent<MeshRenderer>(); if (r0 != null) r0.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.TwoSided;
                    return;
                }
                case "coral_pendant": case "bindweed_garland":
                    Object.DestroyImmediate(host); return;                                   // overhead
                default:
                    if (b.size.y < 0.25f) { Object.DestroyImmediate(host); return; }        // ankle-high: walk over it
                    Capsule(host, Mathf.Clamp(Mathf.Min(b.extents.x, b.extents.z) * 0.6f, 0.08f, 0.4f), b.size.y); break;
            }
        }

        static void Capsule(GameObject host, float r, float h)
        {
            var cc = host.AddComponent<CapsuleCollider>();
            cc.radius = r; cc.height = Mathf.Max(h, 2f * r); cc.center = new Vector3(0, cc.height * 0.5f, 0); cc.direction = 1;
        }
    }
}
