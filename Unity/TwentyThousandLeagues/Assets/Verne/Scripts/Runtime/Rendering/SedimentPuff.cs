using UnityEngine;

namespace Verne
{
    /// <summary>
    /// A boot on the sea floor kicks up what it stands on (Docs/RESEARCH_underwater.md §3.3). Settling speed goes with
    /// grain size squared: fine sand falls back at ~1 cm/s (a quick puff gone in a second or two), coarse silt at
    /// ~0.6 mm/s and fine silt slower still (a soft cloud that hangs, drifts with the current and thins for many seconds),
    /// rock gives almost nothing. One pooled particle system for the whole scene; particles take the floor's tint and,
    /// like the marine snow, are only visible where light reaches them (dark outside the lamp, INSIDE's lit water dust).
    /// Called by PlayerMotor (each footstep in Water mode), DiverPuppet (each footfall) and BurialRite (the digging).
    /// </summary>
    public class SedimentPuff : MonoBehaviour
    {
        static SedimentPuff s_Inst;
        ParticleSystem m_PS;
        ParticleSystem.Particle[] m_P;
        static Material s_Mat;

        /// <summary>Kick up the floor at pos. kind: the Surface kind under the boot ("sand", "silt", "rock", "coral" ...). strength 0..1.</summary>
        public static void Kick(Vector3 pos, string kind, float strength)
        {
            if (VerneWater.Active == null) return;            // only under water
            if (s_Inst == null)
            {
                var go = new GameObject("Sediment puffs");
                s_Inst = go.AddComponent<SedimentPuff>();
                s_Inst.Init();
            }
            s_Inst.Emit(pos, kind, Mathf.Clamp01(strength));
        }

        void Init()
        {
            m_PS = gameObject.AddComponent<ParticleSystem>();
            m_PS.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            var main = m_PS.main;
            main.loop = false; main.playOnAwake = false;
            main.maxParticles = QualitySettings.GetQualityLevel() <= 0 ? 400 : 1200;
            main.simulationSpace = ParticleSystemSimulationSpace.World;
            main.startSpeed = 0f; main.gravityModifier = 0f;
            var em = m_PS.emission; em.enabled = false;
            var sh = m_PS.shape; sh.enabled = false;
            // water drag: a puff thrown out by the boot slows within a fraction of a second
            var lim = m_PS.limitVelocityOverLifetime; lim.enabled = true; lim.dampen = 0.12f; lim.limit = 0.05f; lim.drag = 2.5f; lim.multiplyDragByParticleSize = false;
            var sz = m_PS.sizeOverLifetime; sz.enabled = true;
            sz.size = new ParticleSystem.MinMaxCurve(1f, new AnimationCurve(new Keyframe(0f, 0.4f), new Keyframe(0.25f, 1f), new Keyframe(1f, 1.6f)));   // clouds spread as they settle
            var col = m_PS.colorOverLifetime; col.enabled = true;
            var g = new Gradient();
            g.SetKeys(new[] { new GradientColorKey(Color.white, 0f), new GradientColorKey(Color.white, 1f) },
                      new[] { new GradientAlphaKey(0f, 0f), new GradientAlphaKey(1f, 0.08f), new GradientAlphaKey(0.6f, 0.5f), new GradientAlphaKey(0f, 1f) });
            col.color = g;
            var r = GetComponent<ParticleSystemRenderer>();
            r.sharedMaterial = Material();
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; r.receiveShadows = false;
            r.renderMode = ParticleSystemRenderMode.Billboard;
            r.sortMode = ParticleSystemSortMode.Distance;
            m_PS.Play();
        }

        static Material Material()
        {
            if (s_Mat != null) return s_Mat;
            var sh = Shader.Find("Universal Render Pipeline/Particles/Unlit");
            if (sh == null) return null;
            s_Mat = new Material(sh) { name = "Sediment puff (runtime)" };
            var tex = Resources.Load<Texture2D>("VerneUI/helmet_fog");       // a soft round blob (re-used; no new procedural texture)
            if (tex != null) s_Mat.SetTexture("_BaseMap", tex);
            s_Mat.SetFloat("_Surface", 1f); s_Mat.SetFloat("_Blend", 0f);   // transparent, alpha
            s_Mat.SetFloat("_SrcBlend", (float)UnityEngine.Rendering.BlendMode.SrcAlpha);
            s_Mat.SetFloat("_DstBlend", (float)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
            s_Mat.SetFloat("_ZWrite", 0f);
            s_Mat.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
            s_Mat.renderQueue = (int)UnityEngine.Rendering.RenderQueue.Transparent;
            s_Mat.SetOverrideTag("RenderType", "Transparent");
            return s_Mat;
        }

        struct Grain { public float settle, life, size, count, spread; public Color tint; }

        static Grain For(string kind)
        {
            kind = (kind ?? "sand").ToLowerInvariant();
            if (kind.Contains("silt") || kind.Contains("mud") || kind.Contains("weed"))
                return new Grain { settle = 0.0008f, life = 12f, size = 0.35f, count = 26, spread = 0.35f, tint = new Color(0.55f, 0.52f, 0.44f) };
            if (kind.Contains("rock") || kind.Contains("basalt") || kind.Contains("lava") || kind.Contains("stone") || kind.Contains("coral"))
                return new Grain { settle = 0.006f, life = 2.5f, size = 0.12f, count = 5, spread = 0.2f, tint = new Color(0.4f, 0.4f, 0.38f) };
            // sand (default): quick puff, falls back at ~1 cm/s
            return new Grain { settle = 0.01f, life = 2.2f, size = 0.16f, count = 18, spread = 0.28f, tint = new Color(0.72f, 0.68f, 0.58f) };
        }

        void Emit(Vector3 pos, string kind, float strength)
        {
            var gr = For(kind);
            int n = Mathf.RoundToInt(gr.count * Mathf.Lerp(0.4f, 1f, strength));
            if (QualitySettings.GetQualityLevel() <= 0) n = Mathf.Max(1, n / 2);
            var ep = new ParticleSystem.EmitParams();
            for (int i = 0; i < n; i++)
            {
                var dir = Random.insideUnitCircle.normalized;
                float up = Random.Range(0.06f, 0.22f);
                ep.position = pos + new Vector3(dir.x, 0f, dir.y) * Random.Range(0.05f, 0.18f) + Vector3.up * 0.03f;
                ep.velocity = new Vector3(dir.x * gr.spread, up, dir.y * gr.spread) * Mathf.Lerp(0.5f, 1.2f, strength) * Random.Range(0.6f, 1.2f);
                ep.startLifetime = gr.life * Random.Range(0.7f, 1.3f);
                ep.startSize = gr.size * Random.Range(0.6f, 1.4f);
                ep.startColor = new Color(gr.tint.r, gr.tint.g, gr.tint.b, 0.5f);
                ep.rotation = Random.Range(0f, 360f);
                m_PS.Emit(ep, 1);
            }
            m_Settle = gr.settle; m_Tint = gr.tint;   // the latest kind sets settling and tint (mixed floors are rare within a few seconds)
        }

        float m_Settle = 0.01f;
        Color m_Tint = new Color(0.72f, 0.68f, 0.58f);

        void LateUpdate()
        {
            if (m_PS == null) return;
            int max = m_PS.main.maxParticles;
            if (m_P == null || m_P.Length < max) m_P = new ParticleSystem.Particle[max];
            int n = m_PS.GetParticles(m_P);
            if (n == 0) return;
            var w = VerneWater.Active;
            float dt = Time.deltaTime, t = Time.time;
            Color ext = w != null ? w.Extinction : new Color(0.3f, 0.06f, 0.05f);
            for (int i = 0; i < n; i++)
            {
                var p = m_P[i];
                // settle (terminal velocity reached at once in water) and drift with the slow current
                var v = p.velocity;
                v.y = Mathf.MoveTowards(v.y, -m_Settle, dt * 0.4f);
                v.x += Mathf.Sin(t * 0.13f + i * 0.7f) * 0.004f * dt; v.z += Mathf.Cos(t * 0.11f + i) * 0.004f * dt;
                p.velocity = v;
                // lit only by the light that reaches it (same model as MarineSnow)
                Color light = MarineSnow.LightAt(w, p.position, ext);
                float a = Mathf.Clamp01((light.r + light.g + light.b) * 0.8f);
                p.startColor = new Color(Mathf.Clamp01(light.r * m_Tint.r * 2f), Mathf.Clamp01(light.g * m_Tint.g * 2f), Mathf.Clamp01(light.b * m_Tint.b * 2f), Mathf.Lerp(0.12f, 0.8f, a));
                m_P[i] = p;
            }
            m_PS.SetParticles(m_P, n);
        }
    }
}
