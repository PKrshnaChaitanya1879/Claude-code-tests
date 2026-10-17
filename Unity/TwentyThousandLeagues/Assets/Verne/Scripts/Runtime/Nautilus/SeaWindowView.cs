using System.Collections.Generic;
using UnityEngine;

namespace Verne
{
    /// <summary>
    /// The sea outside the saloon's crystal windows, as a real view and not a video plane (I.XIII):
    /// "the sea was distinctly visible for a mile all round the Nautilus ... fishes of all kinds,
    /// attracted by the brilliant light". Schools of fish and drifting medusae swim past the hull,
    /// drawn with GPU instancing (one draw call per school) in the Verne/SeaLit water model, which
    /// the bootstrap also uses for the backdrop shell around the ship. Nothing is drawn while the
    /// iron panels are shut.
    /// </summary>
    public class SeaWindowView : MonoBehaviour
    {
        [Header("Water (per metre extinction; red dies first)")]
        // tuned with Source/tools/preview_sea_window.py (Source/previews/m2_saloon_window_mock.png)
        public Color sigma = new Color(0.11f, 0.045f, 0.04f);
        public Color water = new Color(0.004f, 0.032f, 0.040f);
        public Color ambient = new Color(0.004f, 0.010f, 0.013f);
        [Tooltip("The light pouring out of the crystal windows: a strip along each side (xyz in this object's space; x mirrored).")]
        public Vector3 lampLocal = new Vector3(3.8f, 2f, 15f);
        public Vector2 windowZ = new Vector2(12.9f, 17.1f);
        public Color lampColor = new Color(2.0f, 1.95f, 1.8f);
        public float lampRange = 7f;
        [Header("Life")]
        public Material fishMaterial, silverMaterial, goldMaterial, medusaMaterial;
        public SlidingPanels panels;
        [Tooltip("The Nautilus is under way: how fast the water streams aft past the windows (m/s).")]
        public float flow = 1.6f;

        class School
        {
            public Mesh mesh; public Material mat; public int count; public float scale, speed, spread;
            public Vector3 centre; public float side; public Vector3[] offsets; public float[] phase; public Matrix4x4[] m;
            public bool medusa;
        }
        readonly List<School> m_Schools = new List<School>();
        static Mesh s_Fish, s_Medusa;

        static readonly int ID_Sigma = Shader.PropertyToID("_VerneSigma"), ID_Water = Shader.PropertyToID("_VerneWater"),
            ID_Ambient = Shader.PropertyToID("_VerneAmbient"), ID_Mirror = Shader.PropertyToID("_VerneLampMirror"), ID_LampPos = Shader.PropertyToID("_VerneLampPos"), ID_LampColor = Shader.PropertyToID("_VerneLampColor");

        void OnEnable() { PushGlobals(); }

        void PushGlobals()
        {
            Shader.SetGlobalVector(ID_Sigma, (Vector4)sigma);
            Shader.SetGlobalVector(ID_Water, (Vector4)water);
            Shader.SetGlobalVector(ID_Ambient, (Vector4)ambient);
            var lp = transform.TransformPoint(lampLocal);
            Shader.SetGlobalVector(ID_LampPos, new Vector4(lp.x, lp.y, lp.z, lampRange));
            Shader.SetGlobalVector(ID_LampColor, (Vector4)lampColor);
            var c = transform.position;
            Shader.SetGlobalVector(ID_Mirror, new Vector4(1f, c.z + windowZ.x, c.z + windowZ.y, c.x));
        }

        void OnDisable() { Shader.SetGlobalVector(ID_Mirror, Vector4.zero); }

        void Start()
        {
            if (s_Fish == null) s_Fish = BuildFish();
            if (s_Medusa == null) s_Medusa = BuildMedusa();
            var rnd = new System.Random(20);
            // silver mackerel-like schools, a red-gold school, a pair of large slow fish, medusae
            Material Or(Material m) => m != null ? m : fishMaterial;
            for (int i = 0; i < 3; i++) Add(rnd, s_Fish, Or(silverMaterial), 40, 0.28f, 0.5f, 2.2f, false);
            Add(rnd, s_Fish, Or(goldMaterial), 24, 0.34f, 0.35f, 1.6f, false);
            Add(rnd, s_Fish, fishMaterial, 2, 1.9f, 0.15f, 2.5f, false);
            Add(rnd, s_Medusa, Or(medusaMaterial), 7, 0.6f, -0.05f, 5f, true);
        }

        void Add(System.Random rnd, Mesh mesh, Material mat, int count, float scale, float speed, float spread, bool medusa)
        {
            if (mesh == null || mat == null) return;
            mat.enableInstancing = true;
            var s = new School { mesh = mesh, mat = mat, count = count, scale = scale, speed = speed, spread = spread, medusa = medusa,
                offsets = new Vector3[count], phase = new float[count], m = new Matrix4x4[count] };
            for (int i = 0; i < count; i++)
            {
                s.offsets[i] = new Vector3((float)(rnd.NextDouble() - 0.5) * spread, (float)(rnd.NextDouble() - 0.5) * spread * 0.5f, (float)(rnd.NextDouble() - 0.5) * spread * 2f);
                s.phase[i] = (float)rnd.NextDouble() * 6.28f;
            }
            Respawn(s, rnd, true);
            m_Schools.Add(s);
        }

        static readonly System.Random s_Rnd = new System.Random(7);
        void Respawn(School s, System.Random rnd, bool anywhere)
        {
            s.side = rnd.NextDouble() < 0.5 ? -1f : 1f;
            float dist = s.medusa ? Mathf.Lerp(4.6f, 9f, (float)rnd.NextDouble()) : Mathf.Lerp(5.2f, 13f, (float)rnd.NextDouble());
            float y = s.medusa ? Mathf.Lerp(-1f, 5f, (float)rnd.NextDouble()) : Mathf.Lerp(-0.5f, 4.5f, (float)rnd.NextDouble());
            float z = anywhere ? Mathf.Lerp(-25f, 55f, (float)rnd.NextDouble()) : 55f + (float)rnd.NextDouble() * 20f;
            s.centre = new Vector3(s.side * dist, y, z);
        }

        void Update()
        {
            PushGlobals();
            bool visible = panels == null || panels.Openness > 0.01f;
            float t = Time.time, dt = Time.deltaTime;
            foreach (var s in m_Schools)
            {
                // relative to the ship the water streams aft; the fish swim forward against it, slower
                s.centre.z -= (flow - s.speed * 2.5f) * dt;
                s.centre.x += Mathf.Sin(t * 0.13f + s.centre.z * 0.05f) * 0.15f * dt;
                if (s.centre.z < -30f) Respawn(s, s_Rnd, false);
                if (!visible) continue;
                for (int i = 0; i < s.count; i++)
                {
                    float ph = s.phase[i];
                    Vector3 o = s.offsets[i] + new Vector3(Mathf.Sin(t * 0.7f + ph) * 0.25f, Mathf.Sin(t * 0.5f + ph * 1.3f) * 0.15f, Mathf.Sin(t * 0.4f + ph * 0.7f) * 0.3f);
                    Vector3 p = transform.TransformPoint(s.centre + o);
                    Quaternion r = s.medusa ? Quaternion.Euler(Mathf.Sin(t * 0.3f + ph) * 12f, ph * 57f, Mathf.Cos(t * 0.27f + ph) * 10f)
                                            : transform.rotation * Quaternion.Euler(Mathf.Sin(t * 0.6f + ph) * 6f, Mathf.Sin(t * 0.8f + ph) * 14f, 0f);
                    s.m[i] = Matrix4x4.TRS(p, r, Vector3.one * s.scale * (0.85f + 0.3f * Mathf.Repeat(ph * 0.37f, 1f)));
                }
                var rp = new RenderParams(s.mat) { shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off, receiveShadows = false };
                Graphics.RenderMeshInstanced(rp, s.mesh, 0, s.m, s.count);
            }
        }

        // ------------------------------------------------------------------ meshes (low-poly, Iron Lung / ULTRAKILL faceting)
        static Mesh BuildFish()
        {
            // fusiform, laterally compressed; head at +z. Rings: (z, half-width, half-height)
            var rings = new[] { (0.5f, 0f, 0f), (0.36f, 0.06f, 0.1f), (0.12f, 0.09f, 0.16f), (-0.15f, 0.07f, 0.12f), (-0.36f, 0.03f, 0.05f), (-0.45f, 0.012f, 0.02f) };
            const int seg = 6;
            var v = new List<Vector3>(); var tri = new List<int>();
            for (int r = 0; r < rings.Length; r++)
                for (int k = 0; k < seg; k++)
                {
                    float a = k * Mathf.PI * 2f / seg;
                    v.Add(new Vector3(Mathf.Sin(a) * rings[r].Item2, Mathf.Cos(a) * rings[r].Item3, rings[r].Item1));
                }
            for (int r = 0; r < rings.Length - 1; r++)
                for (int k = 0; k < seg; k++)
                {
                    int a = r * seg + k, b = r * seg + (k + 1) % seg, c = (r + 1) * seg + (k + 1) % seg, d = (r + 1) * seg + k;
                    tri.AddRange(new[] { a, d, c, a, c, b });
                }
            // the forked tail and a dorsal fin, both sides
            void Tri(Vector3 p0, Vector3 p1, Vector3 p2)
            {
                int b0 = v.Count; v.Add(p0); v.Add(p1); v.Add(p2); tri.AddRange(new[] { b0, b0 + 1, b0 + 2 });
                b0 = v.Count; v.Add(p0); v.Add(p2); v.Add(p1); tri.AddRange(new[] { b0, b0 + 1, b0 + 2 });
            }
            Tri(new Vector3(0, 0, -0.43f), new Vector3(0, 0.17f, -0.66f), new Vector3(0, 0.02f, -0.55f));
            Tri(new Vector3(0, 0, -0.43f), new Vector3(0, -0.02f, -0.55f), new Vector3(0, -0.17f, -0.66f));
            Tri(new Vector3(0, 0.15f, 0.12f), new Vector3(0, 0.25f, -0.05f), new Vector3(0, 0.12f, -0.12f));
            return Finish("Fish (procedural)", v, tri);
        }

        static Mesh BuildMedusa()
        {
            // a scalloped bell and four oral arms
            const int seg = 8;
            var prof = new[] { (0f, 0.3f), (0.16f, 0.27f), (0.27f, 0.17f), (0.32f, 0.04f), (0.28f, 0f) };
            var v = new List<Vector3>(); var tri = new List<int>();
            for (int r = 0; r < prof.Length; r++)
                for (int k = 0; k < seg; k++)
                {
                    float a = k * Mathf.PI * 2f / seg;
                    float scal = r == prof.Length - 1 && k % 2 == 1 ? 0.88f : 1f;
                    v.Add(new Vector3(Mathf.Cos(a) * prof[r].Item1 * scal, prof[r].Item2, Mathf.Sin(a) * prof[r].Item1 * scal));
                }
            for (int r = 0; r < prof.Length - 1; r++)
                for (int k = 0; k < seg; k++)
                {
                    int a = r * seg + k, b = r * seg + (k + 1) % seg, c = (r + 1) * seg + (k + 1) % seg, d = (r + 1) * seg + k;
                    tri.AddRange(new[] { a, b, c, a, c, d });   // outside
                    tri.AddRange(new[] { a, c, b, a, d, c });   // and the underside, seen from below
                }
            for (int k = 0; k < 4; k++)
            {
                float a = k * Mathf.PI / 2f + 0.4f;
                var dir = new Vector3(Mathf.Cos(a), 0, Mathf.Sin(a));
                var side = Vector3.Cross(dir, Vector3.up) * 0.03f;
                Vector3 p0 = dir * 0.05f, p1 = dir * 0.12f + Vector3.down * 0.7f;
                int b0 = v.Count; v.Add(p0 - side); v.Add(p0 + side); v.Add(p1 + side * 0.3f); v.Add(p1 - side * 0.3f);
                tri.AddRange(new[] { b0, b0 + 1, b0 + 2, b0, b0 + 2, b0 + 3, b0, b0 + 2, b0 + 1, b0, b0 + 3, b0 + 2 });
            }
            return Finish("Medusa (procedural)", v, tri);
        }

        static Mesh Finish(string name, List<Vector3> v, List<int> tri)
        {
            // flat shading: unweld so every face keeps its own normal (the faceted look)
            var fv = new List<Vector3>(tri.Count); var ft = new List<int>(tri.Count); var uv = new List<Vector2>(tri.Count);
            for (int i = 0; i < tri.Count; i++) { fv.Add(v[tri[i]]); ft.Add(i); uv.Add(new Vector2(v[tri[i]].z + 0.5f, v[tri[i]].y + 0.5f)); }
            var m = new Mesh { name = name };
            m.SetVertices(fv); m.SetTriangles(ft, 0); m.SetUVs(0, uv);
            m.RecalculateNormals(); m.RecalculateBounds();
            m.bounds = new Bounds(Vector3.zero, Vector3.one * 2f);
            return m;
        }
    }
}
