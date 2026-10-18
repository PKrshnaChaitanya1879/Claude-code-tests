using System.Collections.Generic;
using UnityEngine;
using UnityEngine.AI;

namespace Verne.EditorTools
{
    /// <summary>
    /// M8 (started in Part 3): an automatic audit of an excursion as the bootstrap builds it, written into the setup report.
    ///  1. Walk-through risk: renderers taller than the ankle with no collider anywhere in their hierarchy.
    ///  2. The way: every metre along the route, does a body (0.35 m capsule, 1.8 m tall) fit standing on the sea floor?
    ///  3. The guide's legs: a complete NavMesh path between consecutive waypoints (else the guide walks straight legs).
    /// It reports; it never changes the scene.
    /// </summary>
    public static class RouteAudit
    {
        public static void Run(string scene, Transform root, Vector3[] route)
        {
            Physics.SyncTransforms();
            // 1. renderers with no collider
            int bare = 0; var names = new Dictionary<string, int>();
            foreach (var r in root.GetComponentsInChildren<MeshRenderer>(true))
            {
                if (r.bounds.size.y < 0.3f || r.bounds.size.x * r.bounds.size.z < 0.04f) continue;
                if (r.GetComponentInChildren<Collider>(true) != null || r.GetComponentInParent<Collider>(true) != null) continue;
                string n = r.name; if (n.Contains("pendant") || n.Contains("garland") || n.Contains("Shaft") || n.Contains("scoria") || n.Contains("lava") || n.Contains("volcano")) continue;   // overhead or out of reach
                if (r.GetComponentInParent<FishSchool>() != null || r.GetComponentInParent<DiverPuppet>() != null) continue;
                bare++; names[n] = names.TryGetValue(n, out var c) ? c + 1 : 1;
            }
            var top = new List<string>(); foreach (var kv in names) top.Add(kv.Key + " ×" + kv.Value);
            SceneBuilders.Notes.Add($"Audit {scene}: {bare} renderers above the ankle without a collider" + (bare > 0 ? ": " + string.Join(", ", top.GetRange(0, Mathf.Min(8, top.Count))) : "."));

            // 2. the way: a body must fit along the route
            int blocked = 0, samples = 0; var where = new List<string>();
            int mask = ~((1 << 2) | (1 << ProjectSetup.InteractableLayer) | (1 << ProjectSetup.PlayerLayer));
            for (int i = 0; i + 1 < route.Length; i++)
            {
                float len = Vector3.Distance(route[i], route[i + 1]);
                for (float d = 0; d < len; d += 1f)
                {
                    var p = Vector3.Lerp(route[i], route[i + 1], d / Mathf.Max(len, 0.01f));
                    if (!Physics.Raycast(new Vector3(p.x, p.y + 30f, p.z), Vector3.down, out var hit, 60f, mask, QueryTriggerInteraction.Ignore)) continue;
                    samples++;
                    var a = hit.point + Vector3.up * 0.4f; var b = hit.point + Vector3.up * 1.45f;
                    if (Physics.CheckCapsule(a, b, 0.35f, mask, QueryTriggerInteraction.Ignore)) { blocked++; if (where.Count < 6) where.Add($"({p.x:0},{p.z:0})"); }
                }
            }
            SceneBuilders.Notes.Add($"Audit {scene}: the way is clear at {samples - blocked} of {samples} one-metre samples" + (blocked > 0 ? "; blocked near " + string.Join(" ", where) : "."));

            // 3. NavMesh legs
            int legs = 0, whole = 0; var path = new NavMeshPath();
            for (int i = 0; i + 1 < route.Length; i++)
            {
                if (!NavMesh.SamplePosition(route[i], out var s0, 3f, NavMesh.AllAreas) || !NavMesh.SamplePosition(route[i + 1], out var s1, 3f, NavMesh.AllAreas)) { legs++; continue; }
                legs++;
                if (NavMesh.CalculatePath(s0.position, s1.position, NavMesh.AllAreas, path) && path.status == NavMeshPathStatus.PathComplete) whole++;
            }
            SceneBuilders.Notes.Add($"Audit {scene}: {whole} of {legs} legs of the guide's route have a complete NavMesh path (the rest fall back to straight legs).");
        }
    }
}
