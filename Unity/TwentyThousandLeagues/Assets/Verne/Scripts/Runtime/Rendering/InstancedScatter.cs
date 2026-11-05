using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace Verne
{
    /// <summary>
    /// The small things of the sea floor (pebbles, shells, gravel, coral crumbs, fine granules) drawn with GPU instancing
    /// (Graphics.RenderMeshInstanced), so thousands cost a handful of draw calls (Docs/RESEARCH_underwater.md §2.3).
    /// They are below ankle height, so they have no colliders and cast no shadows. Instances live in cells; each cell is
    /// drawn only when it is in front of the camera and inside the tier's distance (Light 0.45×, Balanced 0.75×, Full 1×),
    /// and on Light only every other instance of the finest classes is drawn.
    /// SeabedDetail (editor) fills it when the excursions are built.
    /// </summary>
    [ExecuteAlways]
    public class InstancedScatter : MonoBehaviour
    {
        [Serializable]
        public class Cell
        {
            public Mesh mesh;
            public Material material;
            public Vector3 center;
            public float radius = 8f;
            [Tooltip("Metres at which this cell stops drawing on Full (the water has it by then).")]
            public float drawDistance = 30f;
            [Tooltip("Fine classes (granules) are thinned on Light quality.")]
            public bool fine;
            public Matrix4x4[] matrices = new Matrix4x4[0];
        }

        public List<Cell> cells = new List<Cell>();
        static readonly Plane[] s_Planes = new Plane[6];
        Matrix4x4[] m_Half = new Matrix4x4[0];

        public int InstanceCount { get { int n = 0; foreach (var c in cells) n += c.matrices != null ? c.matrices.Length : 0; return n; } }

        void LateUpdate()
        {
            var cam = Camera.main;
#if UNITY_EDITOR
            if (!Application.isPlaying && UnityEditor.SceneView.lastActiveSceneView != null) cam = UnityEditor.SceneView.lastActiveSceneView.camera;
#endif
            if (cam == null) return;
            int q = QualitySettings.GetQualityLevel();
            float distScale = q <= 0 ? 0.45f : (q == 1 ? 0.75f : 1f);
            GeometryUtility.CalculateFrustumPlanes(cam, s_Planes);
            var camPos = cam.transform.position;
            foreach (var c in cells)
            {
                if (c.mesh == null || c.material == null || c.matrices == null || c.matrices.Length == 0) continue;
                float maxD = c.drawDistance * distScale + c.radius;
                if ((c.center - camPos).sqrMagnitude > maxD * maxD) continue;
                var b = new Bounds(c.center, Vector3.one * (c.radius * 2f + 1f));
                if (!GeometryUtility.TestPlanesAABB(s_Planes, b)) continue;
                var rp = new RenderParams(c.material)
                {
                    worldBounds = b,
                    shadowCastingMode = ShadowCastingMode.Off,
                    receiveShadows = true,
                    layer = gameObject.layer,
                    lightProbeUsage = LightProbeUsage.Off,
                };
                var mats = c.matrices;
                int count = mats.Length;
                if (q <= 0 && c.fine)
                {
                    int half = (count + 1) / 2;
                    if (m_Half.Length < half) m_Half = new Matrix4x4[half];
                    for (int i = 0, j = 0; i < count; i += 2, j++) m_Half[j] = mats[i];
                    mats = m_Half; count = half;
                }
                for (int start = 0; start < count; start += 1023)
                    Graphics.RenderMeshInstanced(rp, c.mesh, 0, mats, Mathf.Min(1023, count - start), start);
            }
        }
    }
}
