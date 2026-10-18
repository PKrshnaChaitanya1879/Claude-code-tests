using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

namespace Verne.EditorTools
{
    /// <summary>
    /// Greybox construction kit: boxes with world-scaled UVs (so textures keep their size on long
    /// walls), walls with door openings, rooms. Every solid piece gets a BoxCollider of exactly its
    /// size, so nothing can be walked through. Meshes are saved as assets and shared.
    /// </summary>
    public static class Greybox
    {
        static readonly Dictionary<string, Mesh> s_Meshes = new Dictionary<string, Mesh>();
        public const float WallT = 0.15f;

        public static GameObject Box(string name, Transform parent, Vector3 center, Vector3 size, string mat,
            float tile = 1.6f, bool collide = true, string surface = null, bool isStatic = true)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            go.transform.localPosition = center;
            go.AddComponent<MeshFilter>().sharedMesh = BoxMesh(size, tile);
            var mr = go.AddComponent<MeshRenderer>();
            mr.sharedMaterial = Materials.Get(mat);
            if (collide) go.AddComponent<BoxCollider>().size = size;
            if (surface != null) go.AddComponent<Surface>().kind = surface;
            if (isStatic) GameObjectUtility.SetStaticEditorFlags(go, StaticEditorFlags.BatchingStatic | StaticEditorFlags.ContributeGI | StaticEditorFlags.OccluderStatic | StaticEditorFlags.OccludeeStatic | StaticEditorFlags.ReflectionProbeStatic);
            return go;
        }

        public static Mesh BoxMesh(Vector3 s, float tile)
        {
            string key = $"box_{s.x:0.###}_{s.y:0.###}_{s.z:0.###}_{tile:0.##}";
            if (s_Meshes.TryGetValue(key, out var cached) && cached != null) return cached;
            string path = VerneBootstrap.Generated + "/Meshes/" + key + ".asset";
            var existing = AssetDatabase.LoadAssetAtPath<Mesh>(path);
            if (existing != null) { s_Meshes[key] = existing; return existing; }

            Vector3 h = s * 0.5f;
            var v = new List<Vector3>(); var n = new List<Vector3>(); var uv = new List<Vector2>(); var tri = new List<int>();
            void Face(Vector3 normal, Vector3 u, Vector3 w, float su, float sw)
            {
                int b = v.Count;
                Vector3 c = Vector3.Scale(normal, h);
                Vector3 hu = u * (su * 0.5f), hw = w * (sw * 0.5f);
                v.Add(c - hu - hw); v.Add(c + hu - hw); v.Add(c + hu + hw); v.Add(c - hu + hw);
                for (int i = 0; i < 4; i++) n.Add(normal);
                uv.Add(new Vector2(0, 0)); uv.Add(new Vector2(su / tile, 0)); uv.Add(new Vector2(su / tile, sw / tile)); uv.Add(new Vector2(0, sw / tile));
                tri.Add(b); tri.Add(b + 1); tri.Add(b + 2); tri.Add(b); tri.Add(b + 2); tri.Add(b + 3); // cross(u, w) = normal: front faces point out
            }
            Face(Vector3.right, Vector3.back, Vector3.up, s.z, s.y);
            Face(Vector3.left, Vector3.forward, Vector3.up, s.z, s.y);
            Face(Vector3.up, Vector3.right, Vector3.back, s.x, s.z);
            Face(Vector3.down, Vector3.right, Vector3.forward, s.x, s.z);
            Face(Vector3.forward, Vector3.right, Vector3.up, s.x, s.y);
            Face(Vector3.back, Vector3.left, Vector3.up, s.x, s.y);
            var m = new Mesh { name = key };
            m.SetVertices(v); m.SetNormals(n); m.SetUVs(0, uv); m.SetTriangles(tri, 0);
            m.RecalculateTangents();
            m.RecalculateBounds();
            AssetDatabase.CreateAsset(m, path);
            s_Meshes[key] = m;
            return m;
        }

        public struct Opening { public float at, width, height, sill; public Opening(float at, float width, float height, float sill = 0f) { this.at = at; this.width = width; this.height = height; this.sill = sill; } }

        /// <summary>
        /// A straight wall from a to b (on the floor, y = floor), with openings measured along the
        /// wall from a. Pieces: segments between openings, lintels above, sills below windows.
        /// </summary>
        public struct Doorway { public Transform wall; public float at, width, height; }
        /// <summary>Every walk-through opening made by Wall() since the scene started (cleared per scene).</summary>
        public static readonly List<Doorway> Doorways = new List<Doorway>();

        /// <summary>
        /// GUM: "the door ways get blocked by some models". Sweeps a box through every doorway (60 cm each side
        /// of the wall) and clears what is in it: invisible leftover greybox colliders are switched off, visible
        /// loose furniture is slid out of the way along the wall, art colliders inside the opening are switched off.
        /// Returns a line for the setup report.
        /// </summary>
        public static string ClearDoorways()
        {
            Physics.SyncTransforms();
            int hidden = 0, moved = 0, art = 0; var where = new List<string>();
            foreach (var d in Doorways)
            {
                if (d.wall == null) continue;
                var c = d.wall.TransformPoint(new Vector3(0f, 0.1f + (d.height - 0.25f) * 0.5f, d.at));
                var half = new Vector3(0.6f, (d.height - 0.25f) * 0.5f, d.width * 0.5f - 0.05f);
                var rot = d.wall.rotation;
                foreach (var col in Physics.OverlapBox(c, half, rot, ~0, QueryTriggerInteraction.Ignore))
                {
                    if (col.transform.IsChildOf(d.wall)) continue;                          // the wall's own jambs and lintel
                    if (col.GetComponentInParent<Verne.Door>() != null) continue;            // the door leaf swings in its own frame
                    if (col.GetComponentInParent<Verne.Ladder>() != null) continue;
                    var b = col.bounds;
                    if (b.size.x > 4f && b.size.z > 4f) continue;                            // floors and ceilings
                    var r = col.GetComponent<Renderer>();
                    bool isArt = col.GetComponentInParent<Verne.NautilusArtMarker>() != null;
                    if (r == null || !r.enabled) { col.enabled = false; hidden++; where.Add(col.name); continue; }
                    if (isArt) { col.enabled = false; art++; where.Add(col.name); continue; }
                    // loose greybox furniture: slide it along the wall until it clears the opening
                    var along = rot * Vector3.forward;
                    float side = Vector3.Dot(b.center - c, along) >= 0f ? 1f : -1f;
                    float need = half.z + Vector3.Scale(b.extents, new Vector3(Mathf.Abs(along.x), 0f, Mathf.Abs(along.z))).magnitude - Mathf.Abs(Vector3.Dot(b.center - c, along)) + 0.1f;
                    var t = col.transform; while (t.parent != null && t.parent.GetComponent<Collider>() == null && t.parent.childCount == 1) t = t.parent;
                    t.position += along * side * Mathf.Max(0f, need); moved++; where.Add(col.name);
                }
            }
            Physics.SyncTransforms();
            string list = where.Count > 0 ? ": " + string.Join(", ", where.GetRange(0, Mathf.Min(12, where.Count))) : "";
            return $"Doorways: {Doorways.Count} checked; {hidden} invisible leftover colliders removed, {art} art colliders opened, {moved} pieces of furniture slid clear{list}.";
        }

        public static Transform Wall(string name, Transform parent, Vector2 a, Vector2 b, float floor, float height, string mat, params Opening[] openings)
        {
            var root = new GameObject(name).transform;
            root.SetParent(parent, false);
            Vector2 d = b - a;
            float len = d.magnitude;
            Vector2 dir = d / len;
            float yaw = Mathf.Atan2(dir.x, dir.y) * Mathf.Rad2Deg; // wall runs along local +Z
            root.localPosition = new Vector3(a.x, floor, a.y);
            root.localRotation = Quaternion.Euler(0, yaw, 0);

            var list = new List<Opening>(openings);
            list.Sort((p, q) => p.at.CompareTo(q.at));
            float cursor = 0f;
            int i = 0;
            foreach (var o in list)
            {
                if (o.sill < 0.05f && o.height >= 1.8f) Doorways.Add(new Doorway { wall = root, at = o.at, width = o.width, height = o.height });
                float s0 = o.at - o.width * 0.5f, s1 = o.at + o.width * 0.5f;
                if (s0 > cursor + 0.01f) Piece(root, $"{name} {i++}", cursor, s0, 0f, height, mat);
                if (o.height + o.sill < height - 0.01f) Piece(root, $"{name} lintel {i++}", s0, s1, o.sill + o.height, height, mat);
                if (o.sill > 0.01f) Piece(root, $"{name} sill {i++}", s0, s1, 0f, o.sill, mat);
                cursor = s1;
            }
            if (cursor < len - 0.01f) Piece(root, $"{name} {i}", cursor, len, 0f, height, mat);
            return root;
        }

        static void Piece(Transform root, string name, float z0, float z1, float y0, float y1, string mat)
        {
            var size = new Vector3(WallT, y1 - y0, z1 - z0);
            Box(name, root, new Vector3(0f, (y0 + y1) * 0.5f, (z0 + z1) * 0.5f), size, mat);
        }

        /// <summary>Floor and ceiling slabs for a rectangular room (x0..x1, z0..z1).</summary>
        public static void Slabs(string name, Transform parent, float x0, float x1, float z0, float z1, float floor, float height, string floorMat, string ceilMat, string surface)
        {
            Box(name + " floor", parent, new Vector3((x0 + x1) * 0.5f, floor - 0.1f, (z0 + z1) * 0.5f), new Vector3(x1 - x0, 0.2f, z1 - z0), floorMat, 1.6f, true, surface);
            Box(name + " ceiling", parent, new Vector3((x0 + x1) * 0.5f, floor + height + 0.1f, (z0 + z1) * 0.5f), new Vector3(x1 - x0, 0.2f, z1 - z0), ceilMat, 2.0f);
        }

        public static Light PointLight(string name, Transform parent, Vector3 pos, Color color, float intensity, float range, LightShadows shadows = LightShadows.None)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            go.transform.localPosition = pos;
            var l = go.AddComponent<Light>();
            l.type = LightType.Point;
            l.color = color;
            l.intensity = intensity;
            l.range = range;
            l.shadows = shadows;
            l.lightmapBakeType = LightmapBakeType.Mixed;
            return l;
        }

        public static GameObject Cylinder(string name, Transform parent, Vector3 pos, float radius, float height, string mat, bool collide = true)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            go.name = name;
            go.transform.SetParent(parent, false);
            go.transform.localPosition = pos;
            go.transform.localScale = new Vector3(radius * 2f, height * 0.5f, radius * 2f);
            go.GetComponent<MeshRenderer>().sharedMaterial = Materials.Get(mat);
            var c = go.GetComponent<Collider>();
            if (!collide) Object.DestroyImmediate(c);
            return go;
        }
    }
}
