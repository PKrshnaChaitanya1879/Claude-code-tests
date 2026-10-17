using UnityEditor;
using UnityEngine;

namespace Verne.EditorTools
{
    /// <summary>Spawns crustaceans from Models/Creatures/Creatures.fbx (Source/blender/creatures.py).</summary>
    public static class Creatures
    {
        const string Fbx = VerneBootstrap.Root + "/Models/Creatures/Creatures.fbx";

        public static GameObject Spawn(Transform parent, string name, Vector3 pos, float yaw, float scale = 1f, bool collider = true)
        {
            var fbx = AssetDatabase.LoadAssetAtPath<GameObject>(Fbx);
            if (fbx == null) return null;
            Transform src = null;
            foreach (var t in fbx.GetComponentsInChildren<Transform>(true)) if (t.name == name) { src = t; break; }
            if (src == null) return null;
            var go = Object.Instantiate(src.gameObject, parent);
            go.name = name;
            go.transform.SetPositionAndRotation(pos, Quaternion.Euler(0f, yaw, 0f) * src.rotation);
            go.transform.localScale = Vector3.one * scale;
            if (collider)
            {
                var b = go.GetComponent<MeshRenderer>().bounds;
                var c = go.AddComponent<BoxCollider>();
                c.center = go.transform.InverseTransformPoint(b.center);
                var ls = go.transform.lossyScale;
                c.size = new Vector3(b.size.x / ls.x, b.size.y / ls.y, b.size.z / ls.z) * 0.7f;
            }
            return go;
        }
    }
}
