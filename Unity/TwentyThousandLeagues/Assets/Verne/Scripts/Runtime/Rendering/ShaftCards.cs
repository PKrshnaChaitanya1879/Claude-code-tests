using UnityEngine;

namespace Verne
{
    /// <summary>
    /// Fallback sun shafts (M3, "Light" safety net): a handful of soft additive cards hanging from the surface,
    /// leaning with the sun, shown only while the ray-marched water pass is NOT drawing (unsupported GPU, or the
    /// feature switched off). When the pass runs, the cards hide, so the two never double up.
    /// The cards are built at play time around the visitor and drift with them.
    /// </summary>
    public class ShaftCards : MonoBehaviour
    {
        public Material material;
        public int count = 10;
        public float radius = 22f;
        public float width = 2.2f;
        Transform[] m_Cards;
        Vector3[] m_Anchor;     // where each shaft enters the water, at the surface
        bool m_Shown = true;
        System.Random m_R = new System.Random(9);

        void Start()
        {
            if (material == null) { enabled = false; return; }
            var mesh = BuildQuad();
            m_Cards = new Transform[count]; m_Anchor = new Vector3[count];
            for (int i = 0; i < count; i++)
            {
                var go = new GameObject("Shaft card " + i);
                go.transform.SetParent(transform, false);
                go.AddComponent<MeshFilter>().sharedMesh = mesh;
                var mr = go.AddComponent<MeshRenderer>();
                mr.sharedMaterial = material;
                mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
                mr.receiveShadows = false;
                m_Cards[i] = go.transform;
                Place(i, Vector3.zero, true);
            }
        }

        static Mesh BuildQuad()
        {
            var m = new Mesh { name = "shaft card" };
            m.vertices = new[] { new Vector3(-0.5f, 0, 0), new Vector3(0.5f, 0, 0), new Vector3(-0.5f, 1, 0), new Vector3(0.5f, 1, 0) };
            m.uv = new[] { new Vector2(0, 0), new Vector2(1, 0), new Vector2(0, 1), new Vector2(1, 1) };
            m.normals = new[] { Vector3.back, Vector3.back, Vector3.back, Vector3.back };
            m.triangles = new[] { 0, 2, 1, 1, 2, 3 };
            m.bounds = new Bounds(new Vector3(0, 0.5f, 0), new Vector3(1, 1, 1));
            return m;
        }

        void Place(int i, Vector3 around, bool anywhere)
        {
            var w = VerneWater.Active;
            float top = w != null ? w.surfaceY : 9f;
            float a = (float)m_R.NextDouble() * Mathf.PI * 2f;
            float r = anywhere ? Mathf.Sqrt((float)m_R.NextDouble()) * radius : radius * (0.8f + 0.2f * (float)m_R.NextDouble());
            var p = around + new Vector3(Mathf.Cos(a) * r, 0, Mathf.Sin(a) * r);
            float h = Mathf.Max(4f, top - (around.y - 2f));
            var t = m_Cards[i];
            m_Anchor[i] = new Vector3(p.x, top, p.z);
            // hang down from the surface, leaning along the sun; face the eye about the vertical axis in LateUpdate
            t.localScale = new Vector3(width * (0.6f + (float)m_R.NextDouble() * 0.8f), h, 1f);
        }

        void LateUpdate()
        {
            if (m_Cards == null) return;
            bool show = !VerneUnderwaterFeature.RanRecently;
            if (show != m_Shown) { m_Shown = show; foreach (var c in m_Cards) c.gameObject.SetActive(show); }
            if (!show) return;
            var cam = Camera.main;
            if (cam == null) return;
            Vector3 eye = cam.transform.position;
            var sun = RenderSettings.sun;
            Vector3 down = sun != null ? sun.transform.forward : Vector3.down;
            if (down.y > -0.2f) down = Vector3.down;
            for (int i = 0; i < m_Cards.Length; i++)
            {
                var t = m_Cards[i];
                var d = m_Anchor[i] - eye; d.y = 0f;
                if (d.magnitude > radius * 1.15f) Place(i, eye, false);
                // the card's local +Y points up along the shaft (against the light's travel), its face toward the eye
                Vector3 up = -down;
                Vector3 mid = m_Anchor[i] - up * t.localScale.y * 0.5f;
                Vector3 toEye = eye - mid; toEye -= Vector3.Project(toEye, up);
                if (toEye.sqrMagnitude < 1e-4f) continue;
                t.rotation = Quaternion.LookRotation(-toEye.normalized, up);
                // hang from the surface: the pivot is at the bottom of the quad, so drop it by the height along the shaft
                t.position = m_Anchor[i] - up * t.localScale.y;
            }
        }
    }
}
