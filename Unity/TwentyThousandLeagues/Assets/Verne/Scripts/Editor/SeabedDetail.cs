using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

namespace Verne.EditorTools
{
    /// <summary>
    /// 5 Nov 2026: the sea floor is never flat or empty (GUM). Two layers, both laid in clusters, never grids:
    ///  1. Ground detail, GPU-instanced (InstancedScatter): pebbles, shells, gravel chips, coral crumbs and fine granules
    ///     within ~26 m of the way, densest in patches. Below the ankle: no colliders, no shadows.
    ///  2. More props in clusters (rocks here; coral and weed in CrespoFlora.Clusters; rubble in AtlantisKit.Debris):
    ///     above the ankle, so each has a collider; GPU instancing on their materials and a distance LOD.
    /// The walking route is kept clear by a corridor test (distance to the route polyline) in every placement, and RouteAudit
    /// checks the built scene again. Meshes come from Models/Seabed/Seabed_Detail.fbx (Blender) when present, else simple
    /// faceted shapes made here (geometry only; every texture is a CC0 scan from the packs).
    /// </summary>
    public static class SeabedDetail
    {
        public static int Instances;

        /// <summary>Shortest xz distance from p to the route polyline.</summary>
        public static float DistToRoute(Vector3 p, Vector3[] route)
        {
            float best = float.MaxValue;
            var q = new Vector2(p.x, p.z);
            for (int i = 0; i + 1 < route.Length; i++)
            {
                var a = new Vector2(route[i].x, route[i].z); var b = new Vector2(route[i + 1].x, route[i + 1].z);
                var ab = b - a; float t = Mathf.Clamp01(Vector2.Dot(q - a, ab) / Mathf.Max(ab.sqrMagnitude, 1e-4f));
                best = Mathf.Min(best, (a + ab * t - q).magnitude);
            }
            return best;
        }

        // ------------------------------------------------------------------ meshes
        static Mesh s_Fbx(string name)
        {
            var fbx = AssetDatabase.LoadAssetAtPath<GameObject>(VerneBootstrap.Root + "/Models/Seabed/Seabed_Detail.fbx");
            if (fbx == null) return null;
            foreach (var mf in fbx.GetComponentsInChildren<MeshFilter>(true)) if (mf.name == name) return mf.sharedMesh;
            return null;
        }

        /// <summary>A faceted lump: an icosphere pushed about by a seeded random, flattened (pebble, chip, granule).</summary>
        static Mesh Lump(string key, int seed, Vector3 scale, float rough, int subdiv)
        {
            string path = VerneBootstrap.Generated + "/Meshes/detail_" + key + ".asset";
            var m = AssetDatabase.LoadAssetAtPath<Mesh>(path);
            if (m != null) return m;
            var rnd = new System.Random(seed);
            // icosahedron
            float t = (1f + Mathf.Sqrt(5f)) / 2f;
            var v = new List<Vector3> { new(-1,t,0), new(1,t,0), new(-1,-t,0), new(1,-t,0), new(0,-1,t), new(0,1,t), new(0,-1,-t), new(0,1,-t), new(t,0,-1), new(t,0,1), new(-t,0,-1), new(-t,0,1) };
            var f = new List<int> { 0,11,5, 0,5,1, 0,1,7, 0,7,10, 0,10,11, 1,5,9, 5,11,4, 11,10,2, 10,7,6, 7,1,8, 3,9,4, 3,4,2, 3,2,6, 3,6,8, 3,8,9, 4,9,5, 2,4,11, 6,2,10, 8,6,7, 9,8,1 };
            for (int s = 0; s < subdiv; s++)
            {
                var nf = new List<int>(); var mid = new Dictionary<long, int>();
                int Mid(int a, int b) { long k = a < b ? ((long)a << 32) | (uint)b : ((long)b << 32) | (uint)a; if (mid.TryGetValue(k, out int i)) return i; v.Add((v[a] + v[b]) * 0.5f); mid[k] = v.Count - 1; return v.Count - 1; }
                for (int i = 0; i < f.Count; i += 3) { int a = f[i], b = f[i + 1], c = f[i + 2]; int ab = Mid(a, b), bc = Mid(b, c), ca = Mid(c, a); nf.AddRange(new[] { a, ab, ca, b, bc, ab, c, ca, bc, ab, bc, ca }); }
                f = nf;
            }
            for (int i = 0; i < v.Count; i++)
            {
                var d = v[i].normalized;
                float r = 1f + ((float)rnd.NextDouble() - 0.5f) * rough;
                var p = Vector3.Scale(d * r, scale);
                if (p.y < 0f) p.y *= 0.35f;                     // flat underside: it lies on the floor
                v[i] = p;
            }
            // flat shading: split vertices per face
            var fv = new List<Vector3>(); var fuv = new List<Vector2>(); var ft = new List<int>();
            for (int i = 0; i < f.Count; i += 3)
            {
                for (int k = 0; k < 3; k++) { var p = v[f[i + k]]; fv.Add(p); fuv.Add(new Vector2(p.x + p.y * 0.5f, p.z + p.y * 0.5f) * 4f); ft.Add(fv.Count - 1); }
            }
            m = new Mesh { name = "detail_" + key };
            m.SetVertices(fv); m.SetUVs(0, fuv); m.SetTriangles(ft, 0);
            m.RecalculateNormals(); m.RecalculateTangents(); m.RecalculateBounds();
            AssetDatabase.CreateAsset(m, path);
            return m;
        }

        /// <summary>A ribbed bivalve shell (cockle-like), convex up.</summary>
        static Mesh Shell(string key)
        {
            string path = VerneBootstrap.Generated + "/Meshes/detail_" + key + ".asset";
            var m = AssetDatabase.LoadAssetAtPath<Mesh>(path);
            if (m != null) return m;
            int ribs = 14, rings = 5;
            var v = new List<Vector3>(); var uv = new List<Vector2>(); var tr = new List<int>();
            v.Add(new Vector3(0f, 0.02f, -0.45f)); uv.Add(new Vector2(0.5f, 0f));   // the hinge
            for (int r = 1; r <= rings; r++)
            {
                float fr = r / (float)rings;
                for (int k = 0; k <= ribs; k++)
                {
                    float a = Mathf.Lerp(-1.25f, 1.25f, k / (float)ribs);
                    float rib = 1f + 0.06f * Mathf.Cos(k * Mathf.PI);
                    float x = Mathf.Sin(a) * fr * 0.55f * rib, z = -0.45f + (1f - Mathf.Cos(a) * 0.35f) * fr * 0.85f;
                    float y = Mathf.Sin(fr * Mathf.PI * 0.9f) * 0.22f * (1f - Mathf.Abs(a) * 0.3f) * rib;
                    v.Add(new Vector3(x, y, z)); uv.Add(new Vector2(k / (float)ribs, fr));
                }
            }
            int row = ribs + 1;
            for (int k = 0; k < ribs; k++) { tr.Add(0); tr.Add(1 + k + 1); tr.Add(1 + k); }
            for (int r = 0; r < rings - 1; r++)
                for (int k = 0; k < ribs; k++)
                {
                    int a = 1 + r * row + k, b = a + 1, c = a + row, d = c + 1;
                    tr.AddRange(new[] { a, b, d, a, d, c });
                }
            m = new Mesh { name = "detail_" + key };
            m.SetVertices(v); m.SetUVs(0, uv); m.SetTriangles(tr, 0);
            m.RecalculateNormals(); m.RecalculateTangents(); m.RecalculateBounds();
            AssetDatabase.CreateAsset(m, path);
            return m;
        }

        // ------------------------------------------------------------------ ground detail
        struct Kind { public string name; public Mesh mesh; public Material mat; public float sMin, sMax, perM2, draw; public bool fine, upright; }

        /// <summary>
        /// Lays the instanced ground detail along the route. kind: "crespo" (sand plain, prairie, forest, coral kingdom) or
        /// "atlantis" (basalt plain, copse, the climb). groundAt must return the sea floor's height.
        /// </summary>
        public static void Ground(Transform parent, Vector3[] route, string kind, System.Func<Vector3, (float y, Vector3 n)> floor, int seed)
        {
            var rnd = new System.Random(seed);
            bool crespo = kind == "crespo";
            var kinds = new List<Kind>();
            Material Pack(string pack, Color tint, string fallback) => TexturePacks.Get(pack, tint, 1f) ?? Materials.Get(fallback);
            var pebble = s_Fbx("pebble_a") ?? Lump("pebble", 11, new Vector3(0.5f, 0.32f, 0.42f), 0.35f, 1);
            var pebble2 = s_Fbx("pebble_b") ?? Lump("pebble2", 12, new Vector3(0.38f, 0.28f, 0.5f), 0.45f, 1);
            var chip = s_Fbx("gravel_chip") ?? Lump("chip", 13, new Vector3(0.5f, 0.3f, 0.36f), 0.8f, 0);
            var granule = s_Fbx("granule") ?? Lump("granule", 14, new Vector3(0.5f, 0.4f, 0.5f), 0.5f, 0);
            var shell = s_Fbx("shell_cockle") ?? Shell("shell");
            var crumb = s_Fbx("coral_crumb") ?? Lump("crumb", 15, new Vector3(0.28f, 0.22f, 0.6f), 0.9f, 0);
            if (crespo)
            {
                kinds.Add(new Kind { name = "pebbles", mesh = pebble, mat = Pack("Pebbles", new Color(0.62f, 0.6f, 0.56f), "Rock"), sMin = 0.05f, sMax = 0.16f, perM2 = 0.55f, draw = 24f });
                kinds.Add(new Kind { name = "pebbles2", mesh = pebble2, mat = Pack("Basalt", new Color(0.55f, 0.55f, 0.55f), "Rock2"), sMin = 0.04f, sMax = 0.12f, perM2 = 0.35f, draw = 22f });
                kinds.Add(new Kind { name = "shells", mesh = shell, mat = Pack("Shells", new Color(0.95f, 0.9f, 0.82f), "Sand"), sMin = 0.03f, sMax = 0.075f, perM2 = 0.8f, draw = 16f });
                kinds.Add(new Kind { name = "gravel", mesh = chip, mat = Pack("Gravel", new Color(0.8f, 0.75f, 0.68f), "Sand"), sMin = 0.02f, sMax = 0.05f, perM2 = 2.2f, draw = 12f, fine = true });
                kinds.Add(new Kind { name = "granules", mesh = granule, mat = Pack("SeabedSand", new Color(0.85f, 0.82f, 0.74f), "Sand"), sMin = 0.008f, sMax = 0.02f, perM2 = 5f, draw = 7f, fine = true });
                kinds.Add(new Kind { name = "coral crumbs", mesh = crumb, mat = Pack("Coral", new Color(0.9f, 0.62f, 0.55f), "CoralRed"), sMin = 0.04f, sMax = 0.1f, perM2 = 0.45f, draw = 16f });
            }
            else
            {
                kinds.Add(new Kind { name = "basalt pebbles", mesh = pebble, mat = Pack("Basalt", new Color(0.5f, 0.5f, 0.52f), "Basalt"), sMin = 0.06f, sMax = 0.2f, perM2 = 0.8f, draw = 22f });
                kinds.Add(new Kind { name = "scoria chips", mesh = chip, mat = Pack("LavaRock", new Color(0.55f, 0.5f, 0.48f), "Rock2"), sMin = 0.03f, sMax = 0.09f, perM2 = 2.4f, draw = 12f, fine = true });
                kinds.Add(new Kind { name = "granules", mesh = granule, mat = Pack("LavaRock", new Color(0.45f, 0.42f, 0.4f), "Rock2"), sMin = 0.01f, sMax = 0.025f, perM2 = 4f, draw = 7f, fine = true });
                kinds.Add(new Kind { name = "shells", mesh = shell, mat = Pack("Shells", new Color(0.7f, 0.68f, 0.64f), "Rock2"), sMin = 0.03f, sMax = 0.07f, perM2 = 0.25f, draw = 14f });
            }

            var host = new GameObject("Ground detail (instanced)");
            host.transform.SetParent(parent, false);
            var scatter = host.AddComponent<InstancedScatter>();
            const float cell = 12f, reach = 26f;
            // the cells along the route
            var min = new Vector2(float.MaxValue, float.MaxValue); var max = new Vector2(float.MinValue, float.MinValue);
            foreach (var r in route) { min = Vector2.Min(min, new Vector2(r.x, r.z)); max = Vector2.Max(max, new Vector2(r.x, r.z)); }
            min -= Vector2.one * reach; max += Vector2.one * reach;
            // patches: a few hundred soft cluster centres, so density varies the way real floors do
            var patches = new List<(Vector2 c, float r, float k)>();
            for (int i = 0; i < 220; i++)
                patches.Add((new Vector2(Mathf.Lerp(min.x, max.x, (float)rnd.NextDouble()), Mathf.Lerp(min.y, max.y, (float)rnd.NextDouble())),
                             Mathf.Lerp(1.2f, 4.5f, (float)rnd.NextDouble()), Mathf.Lerp(1.5f, 4f, (float)rnd.NextDouble())));
            float Density(Vector2 q)
            {
                float d = 0.35f;                                    // a thin sprinkling everywhere
                foreach (var p in patches) { float r2 = (q - p.c).sqrMagnitude; if (r2 < p.r * p.r * 4f) d += p.k * Mathf.Exp(-r2 / (p.r * p.r)); }
                return d;
            }
            Instances = 0;
            for (float cx = min.x; cx < max.x; cx += cell)
                for (float cz = min.y; cz < max.y; cz += cell)
                {
                    var cc = new Vector3(cx + cell * 0.5f, 0f, cz + cell * 0.5f);
                    if (DistToRoute(cc, route) > reach + cell * 0.7f) continue;
                    foreach (var k in kinds)
                    {
                        if (k.mesh == null || k.mat == null) continue;
                        k.mat.enableInstancing = true;
                        int tries = Mathf.RoundToInt(k.perM2 * cell * cell);
                        var list = new List<Matrix4x4>();
                        float ySum = 0f;
                        for (int i = 0; i < tries; i++)
                        {
                            var q = new Vector2(cx + (float)rnd.NextDouble() * cell, cz + (float)rnd.NextDouble() * cell);
                            var p3 = new Vector3(q.x, 0f, q.y);
                            float dr = DistToRoute(p3, route);
                            if (dr > reach) continue;
                            // denser near the walker (what the eye sees), patchy everywhere
                            float keep = Density(q) * Mathf.Lerp(1f, 0.35f, dr / reach) / 3f;
                            if ((float)rnd.NextDouble() > keep) continue;
                            if (p3.z < 3f && Mathf.Abs(p3.x) < 3f) continue;          // the Nautilus' door
                            var (y, n) = floor(p3);
                            if (float.IsNaN(y) || n.y < 0.55f) continue;              // not on cliffs
                            float s = Mathf.Lerp(k.sMin, k.sMax, Mathf.Pow((float)rnd.NextDouble(), 1.8f));
                            var rot = Quaternion.FromToRotation(Vector3.up, n) * Quaternion.Euler(0f, (float)rnd.NextDouble() * 360f, 0f)
                                      * Quaternion.Euler(((float)rnd.NextDouble() - 0.5f) * 30f, 0f, ((float)rnd.NextDouble() - 0.5f) * 30f);
                            float sink = s * 0.25f;                                   // settled into the sand
                            list.Add(Matrix4x4.TRS(new Vector3(p3.x, y - sink, p3.z), rot, Vector3.one * s));
                            ySum += y;
                        }
                        if (list.Count == 0) continue;
                        scatter.cells.Add(new InstancedScatter.Cell
                        {
                            mesh = k.mesh, material = k.mat, center = new Vector3(cc.x, ySum / list.Count, cc.z), radius = cell * 0.75f,
                            drawDistance = k.draw, fine = k.fine, matrices = list.ToArray()
                        });
                        Instances += list.Count;
                    }
                }
            EditorUtility.SetDirty(scatter);
            SceneBuilders.Notes.Add($"Ground detail ({kind}): {Instances} instanced pebbles, shells, gravel and granules in {scatter.cells.Count} cells (GPU instancing, no colliders, culled by distance per tier).");
        }

        // ------------------------------------------------------------------ clustered props (rocks)
        /// <summary>Clustered boulders and slabs either side of the way (never on it), each with its collider and an AO decal.</summary>
        public static int RockClusters(System.Func<Vector3, float, string, GameObject> rockAt, Vector3[] route, int clusters, float zMin, float zMax, float xSpan, float clearance, int seed)
        {
            var rnd = new System.Random(seed);
            int n = 0;
            for (int c = 0; c < clusters; c++)
            {
                var centre = new Vector3(((float)rnd.NextDouble() * 2f - 1f) * xSpan, 0f, Mathf.Lerp(zMin, zMax, (float)rnd.NextDouble()));
                if (DistToRoute(centre, route) < clearance + 1.5f) centre.x += Mathf.Sign(centre.x == 0 ? 1 : centre.x) * (clearance + 3f);
                int count = 2 + rnd.Next(6);
                for (int i = 0; i < count; i++)
                {
                    float a = (float)rnd.NextDouble() * Mathf.PI * 2f, r = Mathf.Abs(Gauss(rnd)) * 2.2f;
                    var p = centre + new Vector3(Mathf.Cos(a) * r, 0f, Mathf.Sin(a) * r);
                    if (DistToRoute(p, route) < clearance) continue;
                    if (p.z < 4f && Mathf.Abs(p.x) < 5f) continue;
                    float scale = i == 0 ? Mathf.Lerp(0.9f, 1.6f, (float)rnd.NextDouble()) : Mathf.Lerp(0.3f, 0.9f, (float)rnd.NextDouble());   // one big stone, smaller ones round it
                    if (rockAt(p, scale, null) != null) n++;
                }
            }
            return n;
        }

        public static float Gauss(System.Random r)
        {
            double u1 = 1.0 - r.NextDouble(), u2 = r.NextDouble();
            return (float)(System.Math.Sqrt(-2.0 * System.Math.Log(u1)) * System.Math.Sin(2.0 * System.Math.PI * u2));
        }
    }
}
