using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

namespace Verne.EditorTools
{
    /// <summary>
    /// M5 (started in Part 3): lays Mission II out from the Blender kit (Source/blender/atlantis.py → Models/Atlantis/Atlantis.fbx),
    /// in the order of II.IX: the stony plain with its phosphorescent pennatules → the petrified copse ("trees petrified by the
    /// action of the water and here and there overtopped by gigantic pines") → the crevice and the dead trunk thrown across it →
    /// the crustaceans' rocks and the cromlechs → the first platform's ruins under their mantle of weed → the summit with the
    /// rock of black basalt → beyond and below, the city: temples, the acropolis with the outline of a Parthenon, the aqueduct,
    /// the quay, streets and houses; the volcano raining scoriae with its lava runs. Deterministic.
    /// </summary>
    public static class AtlantisKit
    {
        const string Fbx = VerneBootstrap.Root + "/Models/Atlantis/Atlantis.fbx";
        public const float SummitZ = 150f, SummitH = 60f, CityY = -60f, CrevZ0 = 100f, CrevZ1 = 103.2f;
        public static readonly Vector3 VolcanoBase = new Vector3(70f, CityY, 215f);
        public static Vector3 CraterGlow => VolcanoBase + new Vector3(0f, 128f, 0f);
        static readonly Dictionary<string, GameObject> s_Src = new Dictionary<string, GameObject>();
        static System.Func<Vector3, float> s_Ground;
        static System.Random s_R;
        static Transform s_Root;

        /// <summary>The sea floor's shape (metres): flat plain, the climb, a crevice across the way, the peak, the sheer fall to the city.</summary>
        public static float Height(float x, float z)
        {
            float side = Mathf.Exp(-(x / 75f) * (x / 75f));
            float up = z <= SummitZ ? SummitH * Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(25f, SummitZ, z))   // ≤ 35° before noise: under the 42° the visitor can climb
                                    : SummitH * (1f - Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(SummitZ, SummitZ + 26f, z)));
            float h = up * side + (z > SummitZ ? CityY * Mathf.SmoothStep(0f, 1f, Mathf.InverseLerp(SummitZ, SummitZ + 34f, z)) : 0f);
            // the crevice: a narrow trench across the way, 14 m deep
            if (z > CrevZ0 - 1.5f && z < CrevZ1 + 1.5f && Mathf.Abs(x) < 120f)
            {
                float t = Mathf.Min(Mathf.InverseLerp(CrevZ0 - 1.5f, CrevZ0, z), Mathf.InverseLerp(CrevZ1 + 1.5f, CrevZ1, z));
                h -= 14f * Mathf.Clamp01(t) * Mathf.Clamp01((120f - Mathf.Abs(x)) / 6f);
            }
            // the summit: a small flat platform ("a circle of ten yards")
            float r = new Vector2(x, z - SummitZ).magnitude;
            if (r < 6f) h = Mathf.Max(h, SummitH * side - 0.3f);
            return h;
        }

        public static bool Place(Transform parent, System.Func<Vector3, float> groundAt)
        {
            var fbx = AssetDatabase.LoadAssetAtPath<GameObject>(Fbx);
            if (fbx == null) { VerneBootstrap.Note("Atlantis.fbx missing: Mission II keeps its greybox."); return false; }
            s_Src.Clear();
            foreach (var t in fbx.GetComponentsInChildren<Transform>(true)) if (t.GetComponent<MeshFilter>() != null) s_Src[t.name] = t.gameObject;
            s_Ground = groundAt; s_R = new System.Random(1869);
            s_Root = new GameObject("Atlantis (Blender kit)").transform; s_Root.SetParent(parent, false);
            int n0 = s_Root.childCount;

            // 1. the stony plain (z 5–50): pennatules glimmering on the weed, a few cromlechs
            for (int i = 0; i < 160; i++) { var p = Rnd(-30, 30, 5, 55, 1.2f); Put("pennatule", p, Yaw(), Rf(0.8f, 1.6f), false); }
            for (int i = 0; i < 6; i++) Put("cromlech", Rnd(-28, 28, 15, 50, 4f), Yaw(), Rf(0.9f, 1.4f));
            // 2. the petrified copse (z 50–96), a lane kept clear; gigantic pines here and there
            for (int i = 0; i < 110; i++) { var p = Rnd(-34, 34, 50, 97, 2.4f); if (p.z > CrevZ0 - 3f) continue; Put("deadtree_" + s_R.Next(4), p, Yaw(), Rf(0.9f, 1.4f)); }
            for (int i = 0; i < 9; i++) { var p = Rnd(-30, 30, 56, 94, 4f); Put("dead_pine", p, Yaw(), Rf(0.9f, 1.2f)); }
            // 3. the crevice and the trunk thrown across it (II.IX: "the unsteady trunk of a tree thrown across from one abyss to the other")
            float lip = Mathf.Max(groundAt(new Vector3(0, 0, CrevZ0 - 1.6f)), groundAt(new Vector3(0, 0, CrevZ1 + 1.6f)));
            var log = PutAt("log_bridge", new Vector3(0f, lip + 0.15f, (CrevZ0 + CrevZ1) * 0.5f), 90f, 1f, true);
            if (log != null) log.AddComponent<Surface>().kind = "wood";
            // 4. the crustaceans' rocks, the cromlechs "leaning on their regularly-cut bases" (z 104–132)
            for (int i = 0; i < 14; i++) Put("cromlech", Rnd(-24, 24, 105, 132, 3f), Yaw(), Rf(1.0f, 1.8f));
            // 5. the first platform: castles and temples under the vegetable mantle (z 120–138)
            foreach (var (x, z, nm, yaw) in new[] { (-14f, 124f, "house_ruin_a", 20f), (12f, 128f, "house_ruin_c", -15f), (-9f, 134f, "temple_ruin_small", 8f), (16f, 136f, "house_ruin_b", 40f) })
                Put(nm, new Vector3(x, 0, z), yaw, 1f);
            for (int i = 0; i < 10; i++) Put(i % 3 == 0 ? "col_drum" : (i % 2 == 0 ? "col_broken_a" : "col_broken_b"), Rnd(-18, 18, 118, 140, 3f), Yaw(), 1f);
            // 6. the summit and the rock of black basalt
            // two crags of black basalt flank the platform, as in im079 (the platform itself stays open ground to stand on)
            Put("summit", new Vector3(9.5f, 0, SummitZ + 5f), 160f, 1f).transform.localScale = new Vector3(0.45f, 0.4f, 0.45f);
            Put("summit", new Vector3(-10f, 0, SummitZ + 2f), 20f, 1f).transform.localScale = new Vector3(0.38f, 0.3f, 0.38f);
            // 7. the city below, lit only by the volcano
            float y = CityY;
            PutAt("acropolis", new Vector3(-70f, y, 255f), 12f, 1f, true);
            PutAt("aqueduct", new Vector3(-120f, y, 205f), 64f, 1.4f, true);
            PutAt("aqueduct", new Vector3(-150f, y, 240f), 64f, 1.4f, true);
            PutAt("quay", new Vector3(-10f, y, 300f), 4f, 1.6f, true);
            PutAt("temple_ruin", new Vector3(-28f, y, 205f), -8f, 1.2f, true);
            PutAt("temple_ruin", new Vector3(14f, y, 232f), 14f, 1.2f, true);
            PutAt("temple_ruin_small", new Vector3(-48f, y, 222f), 4f, 1.2f, true);
            for (int s = 0; s < 4; s++)                      // "long lines of sunken walls and broad, deserted streets"
            {
                float sz = 196f + s * 22f;
                PutAt("street", new Vector3(-95f + 0f, y + 0.05f, sz), 0f, 1.6f, false);
                for (int k = 0; k < 7; k++)
                {
                    float sx = -150f + k * 18f + Rf(-3f, 3f);
                    PutAt(s_R.Next(3) switch { 0 => "house_ruin_a", 1 => "house_ruin_b", _ => "house_ruin_c" }, new Vector3(sx, y, sz + 9f), Rf(-6f, 6f) + (k % 2) * 90f, Rf(1.1f, 1.5f), false);
                }
            }
            for (int i = 0; i < 16; i++) PutAt(i % 4 == 0 ? "col_drum" : "col_tuscan", new Vector3(-36f + i * 3.6f, y, 186f + Rf(-1f, 1f)), Yaw(), 1.2f, false);   // a colonnade, as in im079
            // 8. the volcano: crater, lava runs, scoriae in the water
            PutAt("volcano", VolcanoBase, 0f, 1.85f, false).transform.localScale = new Vector3(1.4f, 1.85f, 1.4f);
            PutAt("lava_runs", VolcanoBase, 200f, 1f, false).transform.localScale = new Vector3(1.4f, 1.85f, 1.4f);
            for (int i = 0; i < 40; i++)
                PutAt("scoria", VolcanoBase + new Vector3(Rf(-120f, 80f), Rf(5f, 60f), Rf(-90f, 70f)), Yaw(), Rf(2f, 6f), false);
            Glow();
            VerneBootstrap.Note($"Mission II: {s_Root.childCount - n0} pieces of the Atlantis kit placed (plain, copse, crevice, platform, summit, city, volcano).");
            return true;
        }

        /// <summary>The rock of black basalt at the summit and the eight chalk letters Nemo traces; the moon's gleam at the end.</summary>
        public static void Summit(Transform parent, DiverGuide nemo)
        {
            if (s_Root == null) return;
            var at = new Vector3(-2.2f, 0, SummitZ + 1.8f);
            var slab = Put("basalt_slab", at, 200f, 1f);
            if (slab == null) return;
            var letters = new List<GameObject>();
            for (int i = 0; i < 8; i++)
            {
                if (!s_Src.TryGetValue("chalk_" + i, out var src)) continue;
                // the letters were modelled in place on the slab's smooth face, about the same origin: give them the slab's transform
                var go = Object.Instantiate(src, s_Root);
                go.name = "chalk " + "ATLANTIS"[i];
                go.transform.SetPositionAndRotation(slab.transform.position, Quaternion.Euler(0f, 200f, 0f) * src.transform.rotation);
                go.transform.localScale = slab.transform.localScale;
                var r = go.GetComponent<MeshRenderer>(); if (r != null) { r.sharedMaterial = Materials.Emissive("Chalk", new Color(0.9f, 0.9f, 0.86f), new Color(0.18f, 0.18f, 0.17f)); r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; }
                letters.Add(go);
            }
            var w = new GameObject("ATLANTIS in chalk (II.IX)").AddComponent<ChalkWriter>();
            w.transform.SetParent(parent, false);
            w.transform.position = slab.transform.position;
            w.letters = letters.ToArray(); w.nemo = nemo;
            var moon = new GameObject("The moon through the water").AddComponent<Light>();
            moon.transform.SetParent(w.transform, false);
            moon.type = LightType.Directional; moon.color = new Color(0.62f, 0.72f, 0.9f); moon.intensity = 0f; moon.shadows = LightShadows.None;
            moon.transform.rotation = Quaternion.Euler(62f, 160f, 0f);
            w.moon = moon;
        }

        static void Glow()
        {
            // the lava's own light on the city (the crater light is built by the scene, at CraterGlow)
            var go = new GameObject("Lava light on the city"); go.transform.SetParent(s_Root, false);
            go.transform.position = VolcanoBase + new Vector3(-40f, 40f, -30f);
            var l = go.AddComponent<Light>(); l.type = LightType.Point; l.color = new Color(1f, 0.32f, 0.1f); l.intensity = 8f; l.range = 260f; l.shadows = LightShadows.None;
        }

        static float Rf(float a, float b) => Mathf.Lerp(a, b, (float)s_R.NextDouble());
        static float Yaw() => (float)s_R.NextDouble() * 360f;
        static Vector3 Rnd(float x0, float x1, float z0, float z1, float lane)
        {
            for (int k = 0; k < 20; k++)
            {
                var p = new Vector3(Rf(x0, x1), 0, Rf(z0, z1));
                if (Mathf.Abs(p.x) >= lane && !(p.z < 6f && Mathf.Abs(p.x) < 6f)) return p;
            }
            return new Vector3(x1, 0, z1);
        }

        static GameObject Put(string name, Vector3 xz, float yaw, float scale, bool collide = true)
            => PutAt(name, new Vector3(xz.x, s_Ground(xz) - 0.05f, xz.z), yaw, scale, collide);

        static GameObject PutAt(string name, Vector3 pos, float yaw, float scale, bool collide)
        {
            if (!s_Src.TryGetValue(name, out var src)) return new GameObject("(missing " + name + ")");
            var go = Object.Instantiate(src, s_Root);
            go.name = name;
            go.transform.SetPositionAndRotation(pos, Quaternion.Euler(0f, yaw, 0f) * src.transform.rotation);
            go.transform.localScale = Vector3.one * scale;
            var mr = go.GetComponent<MeshRenderer>();
            if (mr != null)
            {
                var mats = mr.sharedMaterials;
                for (int i = 0; i < mats.Length; i++)
                {
                    if (mats[i] == null) continue;
                    string m = mats[i].name;
                    if (m.StartsWith("M_lava_crust")) mats[i] = Materials.Emissive("LavaCrust", new Color(0.18f, 0.06f, 0.03f), new Color(0.9f, 0.18f, 0.03f));
                    else if (m.StartsWith("M_lava")) mats[i] = Materials.Emissive("LavaRun", new Color(1f, 0.4f, 0.1f), new Color(6f, 1.7f, 0.35f));
                    else if (m.StartsWith("M_pennatule")) mats[i] = Materials.Emissive("Pennatule", new Color(0.4f, 0.6f, 0.7f), new Color(0.25f, 0.9f, 1.3f));
                }
                mr.sharedMaterials = mats;
                if (name == "pennatule" || name == "scoria") mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            }
            bool big = name == "summit" || name == "volcano" || name == "acropolis";
            GameObjectUtility.SetStaticEditorFlags(go, (name == "scoria" ? 0 : StaticEditorFlags.BatchingStatic) | StaticEditorFlags.OccludeeStatic | (big ? StaticEditorFlags.OccluderStatic : 0));
            if (collide && mr != null && name != "pennatule")
            {
                var mc = go.AddComponent<MeshCollider>(); mc.sharedMesh = go.GetComponent<MeshFilter>().sharedMesh;   // low-poly kit: exact and cheap
                go.AddComponent<Surface>().kind = "rock";
            }
            if (name == "scoria") go.AddComponent<Scoria>();
            return go;
        }
    }
}
