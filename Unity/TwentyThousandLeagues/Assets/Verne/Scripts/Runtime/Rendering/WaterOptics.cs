using UnityEngine;

namespace Verne
{
    /// <summary>
    /// Sea-water optics from what is in the water (Docs/RESEARCH_underwater.md §1). Pure water after Pope & Fry (1997),
    /// dissolved organic matter (CDOM) falling exponentially from 440 nm, phytoplankton absorption and particle
    /// scattering scaled by chlorophyll, and mineral silt (scatters, nearly grey). Averaged over three bands
    /// (R 600–680, G 500–570, B 430–490 nm), it gives per-channel extinction σt = a + b, the single-scattering
    /// albedo b / σt, and the diffuse attenuation of daylight Kd ≈ 1.08 (a + b_b).
    /// Red is absorbed (albedo 0.1–0.3), green and blue are scattered (0.5–0.8): far water glows blue-green and red
    /// simply disappears, as in real underwater photographs.
    /// </summary>
    public static class WaterOptics
    {
        // wavelengths (nm) and Pope & Fry (1997) pure-water absorption (m⁻¹) at them (NASA protocols, Table 1.1)
        static readonly float[] WL = { 400, 420, 440, 460, 480, 500, 520, 540, 560, 580, 600, 620, 640, 660, 680, 700 };
        static readonly float[] AW = { 0.00663f, 0.00454f, 0.00635f, 0.00922f, 0.01169f, 0.0204f, 0.0474f, 0.0558f, 0.0619f, 0.0896f, 0.2224f, 0.2755f, 0.3112f, 0.41f, 0.465f, 0.624f };

        static float PhytoShape(float wl)
        {
            // chlorophyll-specific absorption shape, normalised to 1 at 440 nm (blue peak, red peak near 675)
            float[] x = { 400, 440, 490, 550, 600, 675, 700 };
            float[] y = { 0.7f, 1.0f, 0.7f, 0.3f, 0.25f, 0.45f, 0.1f };
            if (wl <= x[0]) return y[0];
            for (int i = 1; i < x.Length; i++)
                if (wl <= x[i]) return Mathf.Lerp(y[i - 1], y[i], (wl - x[i - 1]) / (x[i] - x[i - 1]));
            return y[y.Length - 1];
        }

        public struct Result
        {
            public Color absorption, scattering, extinction, albedo, kd;
            /// <summary>Distance at which a black object vanishes in green light (≈ 4.8 / σt), metres.</summary>
            public float visibilityGreen;
        }

        /// <param name="chlorophyll">mg m⁻³: 0.02 clearest ocean, 0.1–0.3 clear, 1+ green coastal</param>
        /// <param name="cdom">CDOM absorption at 440 nm (m⁻¹): 0.005 ocean, 0.03 coastal, 0.2 river plume</param>
        /// <param name="silt">mineral scattering (m⁻¹) added flat across the bands: 0 clear, 0.05 hazy, 0.3 murky</param>
        public static Result Compute(float chlorophyll, float cdom, float silt)
        {
            chlorophyll = Mathf.Max(0.005f, chlorophyll); cdom = Mathf.Max(0f, cdom); silt = Mathf.Max(0f, silt);
            Vector3 a = Vector3.zero, b = Vector3.zero, bb = Vector3.zero; Vector3 n = Vector3.zero;
            float chlA = 0.06f * Mathf.Pow(chlorophyll, 0.65f);
            float chlB = 0.3f * Mathf.Pow(chlorophyll, 0.62f);
            for (int i = 0; i < WL.Length; i++)
            {
                float wl = WL[i];
                float ai = AW[i] + cdom * Mathf.Exp(-0.014f * (wl - 440f)) + chlA * PhytoShape(wl);
                float bw = 0.0022f * Mathf.Pow(wl / 500f, -4.32f);
                float bp = chlB * (550f / wl) + silt;
                float bi = bw + bp;
                float bbi = 0.5f * bw + 0.012f * chlB * (550f / wl) + 0.02f * silt;
                int band = wl >= 600 && wl <= 680 ? 0 : (wl >= 500 && wl <= 570 ? 1 : (wl >= 430 && wl <= 490 ? 2 : -1));
                if (band < 0) continue;
                a[band] += ai; b[band] += bi; bb[band] += bbi; n[band] += 1f;
            }
            var r = new Result();
            Vector3 c = Vector3.zero, alb = Vector3.zero, kd = Vector3.zero;
            for (int k = 0; k < 3; k++)
            {
                a[k] /= n[k]; b[k] /= n[k]; bb[k] /= n[k];
                c[k] = a[k] + b[k];
                alb[k] = b[k] / c[k];
                kd[k] = 1.08f * (a[k] + bb[k]);
            }
            r.absorption = new Color(a.x, a.y, a.z);
            r.scattering = new Color(b.x, b.y, b.z);
            r.extinction = new Color(c.x, c.y, c.z);
            r.albedo = new Color(alb.x, alb.y, alb.z);
            r.kd = new Color(kd.x, kd.y, kd.z);
            r.visibilityGreen = 4.8f / Mathf.Max(c.y, 1e-4f);
            return r;
        }

        /// <summary>Per-channel transmittance over d metres.</summary>
        public static Color Transmit(Color sigmaT, float d)
            => new Color(Mathf.Exp(-sigmaT.r * d), Mathf.Exp(-sigmaT.g * d), Mathf.Exp(-sigmaT.b * d), 1f);
    }
}
