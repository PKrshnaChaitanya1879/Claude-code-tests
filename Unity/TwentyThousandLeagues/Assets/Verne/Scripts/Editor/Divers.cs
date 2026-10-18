using UnityEditor;
using UnityEngine;

namespace Verne.EditorTools
{
    /// <summary>Assembles a diver puppet (DiverPuppet) from the Blender parts in Models/Divers/Diver_Parts.fbx.</summary>
    public static class Divers
    {
        const string Fbx = VerneBootstrap.Root + "/Models/Divers/Diver_Parts.fbx";

        static GameObject Part(GameObject fbx, string name, Transform parent, Vector3 local)
        {
            Transform src = null;
            foreach (var t in fbx.GetComponentsInChildren<Transform>(true)) if (t.name == name) { src = t; break; }
            if (src == null) return null;
            var go = Object.Instantiate(src.gameObject, parent);
            go.name = name;
            go.transform.localPosition = local;
            go.transform.localRotation = src.localRotation;
            go.transform.localScale = Vector3.one;
            return go;
        }

        static Transform Joint(string name, Transform parent, Vector3 local)
        {
            var t = new GameObject(name).transform;
            t.SetParent(parent, false);
            t.localPosition = local;
            return t;
        }

        /// <summary>The body "enveloped in a tissue of white linen", lying along the bearers' shoulders (long axis along +Z).</summary>
        public static Transform Shroud(Transform parent, Vector3 pos)
        {
            var fbx = AssetDatabase.LoadAssetAtPath<GameObject>(Fbx);
            if (fbx == null) return null;
            var go = Part(fbx, "shroud", parent, Vector3.zero);
            if (go == null) return null;
            go.transform.position = pos;
            go.name = "The body in white linen";
            return go.transform;
        }

        /// <summary>Builds a diver standing at pos, facing yaw. Returns null if the FBX is missing.</summary>
        public static DiverPuppet Build(Transform parent, string name, Vector3 pos, float yaw, bool lamp, bool stick, bool gun, bool pickaxe = false)
        {
            var fbx = AssetDatabase.LoadAssetAtPath<GameObject>(Fbx);
            if (fbx == null) return null;
            var root = new GameObject(name).transform;
            root.SetParent(parent, false);
            root.position = pos; root.rotation = Quaternion.Euler(0, yaw, 0);
            var hips = Joint("Hips", root, new Vector3(0, 1.04f, 0));
            Part(fbx, "diver_hips", hips, Vector3.zero);
            var torso = Joint("Torso", hips, Vector3.zero);
            Part(fbx, "diver_torso", torso, Vector3.zero);
            Part(fbx, "diver_tank", torso, new Vector3(0, 0.27f, -0.1f));
            var head = Joint("Head", torso, new Vector3(0, 0.77f, 0));
            Part(fbx, "diver_helmet", head, Vector3.zero);
            foreach (var (side, x) in new[] { ("L", -0.22f), ("R", 0.22f) })
            {
                var sh = Joint("Shoulder." + side, torso, new Vector3(x, 0.48f, 0));
                Part(fbx, "diver_upperarm", sh, Vector3.zero);
                var el = Joint("Elbow." + side, sh, new Vector3(0, -0.3f, 0));
                Part(fbx, "diver_forearm", el, Vector3.zero);
                if (side == "R")
                {
                    var hand = Joint("Hand.R", el, new Vector3(0, -0.36f, 0.02f));
                    if (stick) Part(fbx, "diver_stick", hand, Vector3.zero);
                    else if (gun) Part(fbx, "diver_gun", hand, Vector3.zero);
                    else if (pickaxe) Part(fbx, "pickaxe", hand, Vector3.zero);
                }
            }
            foreach (var (side, x) in new[] { ("L", -0.09f), ("R", 0.09f) })
            {
                var hip = Joint("Hip." + side, hips, new Vector3(x, -0.12f, 0));
                Part(fbx, "diver_thigh", hip, Vector3.zero);
                var kn = Joint("Knee." + side, hip, new Vector3(0, -0.42f, 0));
                Part(fbx, "diver_shin", kn, Vector3.zero);
                var an = Joint("Ankle." + side, kn, new Vector3(0, -0.4f, 0));
                Part(fbx, "diver_boot", an, Vector3.zero);
            }
            if (lamp)
            {
                var l = Part(fbx, "diver_lamp", hips, new Vector3(0.14f, 0.06f, 0.15f));
                if (l != null)
                {
                    var lg = new GameObject("Ruhmkorff lamp light"); lg.transform.SetParent(l.transform, false);
                    lg.transform.localPosition = new Vector3(0, -0.1f, 0.08f); lg.transform.localRotation = Quaternion.Euler(12f, 0f, 0f);
                    var li = lg.AddComponent<Light>(); li.type = LightType.Spot; li.range = 16f; li.spotAngle = 60f; li.innerSpotAngle = 30f;
                    li.color = new Color(0.86f, 0.94f, 1f); li.intensity = 5f; li.shadows = LightShadows.None; li.enabled = false;
                }
            }
            foreach (var r in root.GetComponentsInChildren<Renderer>(true)) r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.On;
            // a body: the visitor can't walk through a diver (no clipping), on Ignore Raycast so ground probes skip it
            var cap = root.gameObject.AddComponent<CapsuleCollider>();
            cap.radius = 0.32f; cap.height = 1.9f; cap.center = new Vector3(0, 0.95f, 0); cap.direction = 1;
            var rb = root.gameObject.AddComponent<Rigidbody>(); rb.isKinematic = true; rb.useGravity = false;
            root.gameObject.layer = 2;
            return root.gameObject.AddComponent<DiverPuppet>();
        }
    }
}
