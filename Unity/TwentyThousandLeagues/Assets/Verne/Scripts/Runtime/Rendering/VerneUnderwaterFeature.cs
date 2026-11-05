using UnityEngine;
using UnityEngine.Experimental.Rendering;
using UnityEngine.Rendering;
using UnityEngine.Rendering.RenderGraphModule;
using UnityEngine.Rendering.Universal;

namespace Verne
{
    /// <summary>
    /// M3: INSIDE-style water as one URP renderer feature (RenderGraph, Unity 6):
    ///  1. March (reduced resolution): from the eye to the scene depth, a few steps jittered by interleaved
    ///     gradient noise; daylight falling from the surface with Kd, sampled against the main light's shadow
    ///     map (real shafts, not cards), Henyey-Greenstein forward scattering, and up to four hero lights
    ///     (spot or point). Energy-conserving integration per channel.
    ///  2. Temporal: reprojects last frame's result (depth-based), clamps it to this frame's neighbourhood
    ///     and blends, so a handful of steps reads as smooth light.
    ///  3. Composite (full resolution): scene colour × per-channel transmittance + depth-aware upsampled
    ///     in-scattering + the analytic far field, dithered against banding.
    /// Quality (5 Nov 2026, retuned for the RTX 3050 laptop): Light = 1/4 res, 12 steps, single scattering, mono caustics;
    /// Balanced = 1/2 res, 20 steps; Full = 1/2 res, 48 steps, multiple scattering, chromatic caustics, history 0.92.
    /// Only runs where a VerneWater exists and only for game cameras.
    /// </summary>
    public class VerneUnderwaterFeature : ScriptableRendererFeature
    {
        public Shader shader;
        public static bool Installed { get; private set; }
        static int s_LastFrame = -100;
        /// <summary>True when the water pass was queued in the last couple of frames (else scenes fall back to built-in fog).</summary>
        public static bool RanRecently => Time.frameCount - s_LastFrame <= 2;
        Material m_Mat;
        UnderwaterPass m_Pass;

        public override void Create()
        {
            m_Pass = new UnderwaterPass { renderPassEvent = RenderPassEvent.BeforeRenderingTransparents, requiresIntermediateTexture = true };
            Installed = true;
        }

        public override void AddRenderPasses(ScriptableRenderer renderer, ref RenderingData renderingData)
        {
            var water = VerneWater.Active;
            if (water == null || !water.isActiveAndEnabled) return;
            if (renderingData.cameraData.cameraType != CameraType.Game) return;
            if (m_Mat == null)
            {
                if (shader == null) shader = Shader.Find("Hidden/Verne/Underwater");
                if (shader == null || !shader.isSupported) return;
                m_Mat = CoreUtils.CreateEngineMaterial(shader);
            }
            m_Pass.Setup(m_Mat, water);
            m_Pass.ConfigureInput(ScriptableRenderPassInput.Depth);
            renderer.EnqueuePass(m_Pass);
        }

        protected override void Dispose(bool disposing)
        {
            m_Pass?.Dispose();
            CoreUtils.Destroy(m_Mat);
            Installed = false;
        }

        class UnderwaterPass : ScriptableRenderPass
        {
            Material m_Mat;
            VerneWater m_Water;
            readonly RTHandle[] m_Hist = new RTHandle[2];
            int m_Cur;
            Matrix4x4 m_PrevVP;
            bool m_HasPrev;
            static readonly MaterialPropertyBlock s_Mpb = new MaterialPropertyBlock();

            static readonly int ID_Blit = Shader.PropertyToID("_BlitTexture"), ID_BlitSB = Shader.PropertyToID("_BlitScaleBias"),
                ID_History = Shader.PropertyToID("_VerneHistory"), ID_Scatter = Shader.PropertyToID("_VerneScatterTex"),
                ID_PrevVP = Shader.PropertyToID("_VernePrevVP"), ID_Params = Shader.PropertyToID("_VerneMarch"),
                ID_Water0 = Shader.PropertyToID("_VerneSigmaT"), ID_Albedo = Shader.PropertyToID("_VerneAlbedo"), ID_Kd = Shader.PropertyToID("_VerneKd"),
                ID_Surface = Shader.PropertyToID("_VerneSurface"), ID_LampPos = Shader.PropertyToID("_VerneLampPosArr"),
                ID_LampDir = Shader.PropertyToID("_VerneLampDirArr"), ID_LampCol = Shader.PropertyToID("_VerneLampColArr"),
                ID_LowSize = Shader.PropertyToID("_VerneLowSize");
            readonly Vector4[] m_LP = new Vector4[4], m_LD = new Vector4[4], m_LC = new Vector4[4];

            public UnderwaterPass() { profilingSampler = new ProfilingSampler("Verne underwater"); }

            public void Setup(Material mat, VerneWater water) { m_Mat = mat; m_Water = water; }

            public void Dispose() { for (int i = 0; i < 2; i++) { m_Hist[i]?.Release(); m_Hist[i] = null; } }

            static void Quality(out int down, out int steps, out float history, out float multi, out float chroma)
            {
                int q = QualitySettings.GetQualityLevel();
                if (q <= 0) { down = 4; steps = 12; history = 0.9f; multi = 0f; chroma = 0f; }             // integrated GPUs (Ryzen 3 5300U class)
                else if (q == 1) { down = 2; steps = 20; history = 0.9f; multi = 0.6f; chroma = 0f; }
                else { down = 2; steps = 48; history = 0.92f; multi = 1f; chroma = 1f; }                  // RTX 3050: enough samples for crisp ray edges
            }

            void Ensure(int w, int h)
            {
                for (int i = 0; i < 2; i++)
                {
                    if (m_Hist[i] != null && m_Hist[i].rt != null && m_Hist[i].rt.width == w && m_Hist[i].rt.height == h) continue;
                    m_Hist[i]?.Release();
                    m_Hist[i] = RTHandles.Alloc(w, h, colorFormat: GraphicsFormat.R16G16B16A16_SFloat, filterMode: FilterMode.Bilinear,
                        wrapMode: TextureWrapMode.Clamp, name: "_VerneScatterHistory" + i);
                    m_HasPrev = false;
                }
            }

            void PushMaterial(Camera cam, int steps, int w, int h, float history, float multi, float chroma)
            {
                var wtr = m_Water;
                wtr.RefreshOptics();
                m_Mat.SetVector(ID_Params, new Vector4(steps, wtr.maxDistance, Time.frameCount % 64, m_HasPrev ? history : 0f));
                m_Mat.SetVector(ID_Water0, (Vector4)wtr.Extinction);
                m_Mat.SetVector(ID_Albedo, (Vector4)wtr.Albedo);
                m_Mat.SetVector(ID_Kd, (Vector4)wtr.Kd);
                bool caust = CausticCookie.Texture != null && wtr.caustics > 0f;
                m_Mat.SetVector("_VerneExtra", new Vector4(wtr.multiScatter * multi, caust ? wtr.caustics : 0f, chroma, 1f));
                m_Mat.SetVector("_VerneSilt", new Vector4(wtr.floorSilt, wtr.siltLayer, 0f, 0f));
                var wb = wtr.WhiteBalance(cam.transform.position.y);
                m_Mat.SetVector("_VerneWhiteBalance", new Vector4(Mathf.Max(0.2f, wb.r), Mathf.Max(0.2f, wb.g), Mathf.Max(0.2f, wb.b), 1f));
                if (caust)
                {
                    m_Mat.SetTexture("_VerneCausticTex", CausticCookie.Texture);
                    var off = CausticCookie.Offset;
                    m_Mat.SetVector("_VerneCausticXform", new Vector4(1f / Mathf.Max(CausticCookie.TileSize, 0.5f), wtr.causticDepth, off.x, off.y));
                }
                var amb = wtr.SurfaceAmbient;
                m_Mat.SetVector(ID_Surface, new Vector4(wtr.surfaceY, wtr.forwardScatter, wtr.sunShafts, wtr.sampleSpread));
                m_Mat.SetColor("_VerneSurfaceAmbient", amb);
                m_Mat.SetColor("_VerneAmbientFloor", wtr.ambientFloor);
                m_Mat.SetVector("_VerneGlowPos", new Vector4(wtr.glowPosition.x, wtr.glowPosition.y, wtr.glowPosition.z, Mathf.Max(1f, wtr.glowRange)));
                m_Mat.SetColor("_VerneGlowCol", wtr.glowColor);
                m_Mat.SetVector(ID_LowSize, new Vector4(w, h, 1f / w, 1f / h));
                int n = 0;
                foreach (var l in wtr.heroLights)
                {
                    if (n >= 4) break;
                    if (l == null || !l.isActiveAndEnabled || l.intensity <= 0f) continue;
                    var t = l.transform;
                    bool spot = l.type == LightType.Spot;
                    float cosOuter = spot ? Mathf.Cos(l.spotAngle * 0.5f * Mathf.Deg2Rad) : -2f;
                    float cosInner = spot ? Mathf.Cos(l.innerSpotAngle * 0.5f * Mathf.Deg2Rad) : -1f;
                    var c = wtr.BaseColor(l).linear * l.intensity * wtr.heroGain;   // untinted: the march absorbs per sample
                    m_LP[n] = new Vector4(t.position.x, t.position.y, t.position.z, l.range);
                    m_LD[n] = new Vector4(t.forward.x, t.forward.y, t.forward.z, cosOuter);
                    m_LC[n] = new Vector4(c.r, c.g, c.b, cosInner);
                    n++;
                }
                for (int i = n; i < 4; i++) { m_LP[i] = Vector4.zero; m_LD[i] = Vector4.zero; m_LC[i] = Vector4.zero; }
                m_Mat.SetVectorArray(ID_LampPos, m_LP);
                m_Mat.SetVectorArray(ID_LampDir, m_LD);
                m_Mat.SetVectorArray(ID_LampCol, m_LC);
                m_Mat.SetInt("_VerneLampCount", n);
                m_Mat.SetMatrix(ID_PrevVP, m_PrevVP);
            }

            class PassData
            {
                internal Material mat; internal int pass;
                internal TextureHandle src, history, scatter;
            }

            static void Draw(RasterCommandBuffer cmd, PassData d)
            {
                s_Mpb.Clear();
                if (d.src.IsValid()) s_Mpb.SetTexture(ID_Blit, d.src);
                if (d.history.IsValid()) s_Mpb.SetTexture(ID_History, d.history);
                if (d.scatter.IsValid()) s_Mpb.SetTexture(ID_Scatter, d.scatter);
                s_Mpb.SetVector(ID_BlitSB, new Vector4(1, 1, 0, 0));
                cmd.DrawProcedural(Matrix4x4.identity, d.mat, d.pass, MeshTopology.Triangles, 3, 1, s_Mpb);
            }

            public override void RecordRenderGraph(RenderGraph renderGraph, ContextContainer frameData)
            {
                if (m_Mat == null || m_Water == null) return;
                var res = frameData.Get<UniversalResourceData>();
                var camData = frameData.Get<UniversalCameraData>();
                if (res.isActiveTargetBackBuffer || !res.cameraDepthTexture.IsValid()) return;
                s_LastFrame = Time.frameCount;     // the water really is drawn this frame (else scenes keep their fallback fog)

                Quality(out int down, out int steps, out float history, out float multi, out float chroma);
                var desc = camData.cameraTargetDescriptor;
                int w = Mathf.Max(8, desc.width / down), h = Mathf.Max(8, desc.height / down);
                Ensure(w, h);
                var cam = camData.camera;
                PushMaterial(cam, steps, w, h, history, multi, chroma);

                var raw = renderGraph.CreateTexture(new TextureDesc(w, h)
                    { colorFormat = GraphicsFormat.R16G16B16A16_SFloat, name = "_VerneScatterRaw", clearBuffer = false, filterMode = FilterMode.Bilinear, wrapMode = TextureWrapMode.Clamp });
                var prev = renderGraph.ImportTexture(m_Hist[m_Cur]);
                var next = renderGraph.ImportTexture(m_Hist[1 - m_Cur]);

                // 1. march
                using (var b = renderGraph.AddRasterRenderPass<PassData>("Verne water: march", out var d, profilingSampler))
                {
                    d.mat = m_Mat; d.pass = 0; d.src = TextureHandle.nullHandle; d.history = TextureHandle.nullHandle; d.scatter = TextureHandle.nullHandle;
                    b.UseTexture(res.cameraDepthTexture);
                    if (res.mainShadowsTexture.IsValid()) b.UseTexture(res.mainShadowsTexture);
                    b.UseAllGlobalTextures(true);     // the shader reads the depth and shadow-map globals: keep them bound and alive
                    b.SetRenderAttachment(raw, 0, AccessFlags.Write);
                    b.AllowPassCulling(false);
                    b.SetRenderFunc((PassData data, RasterGraphContext ctx) => Draw(ctx.cmd, data));
                }
                // 2. temporal
                using (var b = renderGraph.AddRasterRenderPass<PassData>("Verne water: temporal", out var d, profilingSampler))
                {
                    d.mat = m_Mat; d.pass = 1; d.src = raw; d.history = prev; d.scatter = TextureHandle.nullHandle;
                    b.UseTexture(raw); b.UseTexture(prev); b.UseTexture(res.cameraDepthTexture); b.UseAllGlobalTextures(true);
                    b.SetRenderAttachment(next, 0, AccessFlags.Write);
                    b.AllowPassCulling(false);
                    b.SetRenderFunc((PassData data, RasterGraphContext ctx) => Draw(ctx.cmd, data));
                }
                // 3. composite onto the camera colour (through a copy)
                var colorDesc = renderGraph.GetTextureDesc(res.activeColorTexture);
                colorDesc.name = "_VerneSceneCopy"; colorDesc.clearBuffer = false;
                colorDesc.msaaSamples = MSAASamples.None;      // sampled as a plain texture in the composite
                colorDesc.depthBufferBits = DepthBits.None;
                var copy = renderGraph.CreateTexture(colorDesc);
                using (var b = renderGraph.AddRasterRenderPass<PassData>("Verne water: copy", out var d, profilingSampler))
                {
                    d.src = res.activeColorTexture;
                    b.UseTexture(d.src);
                    b.SetRenderAttachment(copy, 0, AccessFlags.Write);
                    b.SetRenderFunc((PassData data, RasterGraphContext ctx) => Blitter.BlitTexture(ctx.cmd, data.src, new Vector4(1, 1, 0, 0), 0f, false));
                }
                using (var b = renderGraph.AddRasterRenderPass<PassData>("Verne water: composite", out var d, profilingSampler))
                {
                    d.mat = m_Mat; d.pass = 2; d.src = copy; d.history = TextureHandle.nullHandle; d.scatter = next;
                    b.UseTexture(copy); b.UseTexture(next); b.UseTexture(res.cameraDepthTexture); b.UseAllGlobalTextures(true);
                    b.SetRenderAttachment(res.activeColorTexture, 0, AccessFlags.Write);
                    b.SetRenderFunc((PassData data, RasterGraphContext ctx) => Draw(ctx.cmd, data));
                }

                m_PrevVP = GL.GetGPUProjectionMatrix(cam.projectionMatrix, true) * cam.worldToCameraMatrix;
                m_HasPrev = true;
                m_Cur = 1 - m_Cur;
            }
        }
    }
}
