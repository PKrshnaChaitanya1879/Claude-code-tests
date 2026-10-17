using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering.Universal;

namespace Verne.EditorTools
{
    /// <summary>
    /// Installs the renderer features on the shared Universal Renderer, idempotently.
    /// M1: URP Decals (hand-placed AO, contact shadows and bounce, as Playdead did).
    /// M3 adds the Verne underwater volumetrics feature here.
    /// </summary>
    public static class RendererFeatures
    {
        public static void Install(UniversalRendererData rd)
        {
            AddFeature<DecalRendererFeature>(rd, "Decals (hand-placed AO and shadows)");
        }

        public static T AddFeature<T>(UniversalRendererData rd, string name) where T : ScriptableRendererFeature
        {
            if (rd.TryGetRendererFeature<T>(out var existing)) return existing;
            var f = ScriptableObject.CreateInstance<T>();
            f.name = name;
            AssetDatabase.AddObjectToAsset(f, rd);
            AssetDatabase.TryGetGUIDAndLocalFileIdentifier(f, out string _, out long localId);

            var so = new SerializedObject(rd);
            var list = so.FindProperty("m_RendererFeatures");
            var map = so.FindProperty("m_RendererFeatureMap");
            list.arraySize++;
            list.GetArrayElementAtIndex(list.arraySize - 1).objectReferenceValue = f;
            map.arraySize++;
            map.GetArrayElementAtIndex(map.arraySize - 1).longValue = localId;
            so.ApplyModifiedPropertiesWithoutUndo();
            EditorUtility.SetDirty(rd);
            AssetDatabase.SaveAssets();
            VerneBootstrap.Note("Renderer feature added: " + name);
            return f;
        }
    }
}
