# INSIDE rendering notes, and how we adapt them

**Legend:** **[V]** is verified from a source opened on 2026-10-17. **[I]** is our inference or our engineering choice. Unmarked lines are plain implementation detail.

## Sources

| Source | Opened? | What it gave |
|---|---|---|
| Playdead blog, "The Lighting of INSIDE" (Marek Bogdan): https://blog.playdead.com/articles/the_lighting_of_inside/lighting_of_inside.html | Yes | Hand-placed decals, cookies, torch shadow decals, detail by distance |
| GDC Vault session page, "Low Complexity, High Fidelity – INSIDE Rendering" (Mikkel Gjøl, Mikkel Svendsen, GDC 2016): https://gdcvault.com/play/1023002/Low-Complexity-High-Fidelity-INSIDE | Yes | Topic list |
| GDC Vault, "Temporal Reprojection Anti-Aliasing in INSIDE" (Lasse Jon Fuglsang Pedersen, GDC 2016): https://www.gdcvault.com/play/1022970/Temporal-Reprojection-Anti-Aliasing-in | Search result only | — |
| Playdead's open-sourced Unity TRAA (github.com/playdead/temporal), reported by https://mcvuk.com/?p=64045 | Search result only | — |
| 80.lv republishing of the talk: https://80.lv/articles/the-rendering-of-inside-low-complexity-high-fidelity/ | Yes | Video only; no extractable detail |
| Demofox, "Ray marching fog with blue noise": https://blog.demofox.org/2020/05/10/ray-marching-fog-with-blue-noise/ | Yes | Blue-noise jitter and the step-count/banding relation |

## What INSIDE does

### Lighting by hand **[V]**

- "There is no global illumination or even automated AO at play here." (Playdead blog)
- Bounce light, specular, rim light, AO and cast shadows are hand-placed decals.
- In the corridor before the Cargo Hall, "Bounce light, subtle specular on the pipes and ambient occlusion effects are all accomplished using hand-placed decals."
- A cube-map reflection was hand-positioned to match where the bright area is.
- **Cookies** came late and were used "more and more" to texture simple scenes and suggest richer shadowing.
- **Torch shadows:**
  - The boy's foot shadows are decals that follow the torch, rotate around the feet and scale with the torch's height.
  - "casting from a point light would have been much too expensive."
- **Detail budget:** modelling and lighting detail are "controlled very precisely depending on distance from the camera," and by gameplay and narrative focus. The fixed side-on camera made that tractable.

### The GDC talk's topics **[V]**

- Local shadowed volumetrics.
- A water-rendering system.
- Lighting split into separate diffuse, specular and bounce components.
- Analytic, primitive-based AO (artist-friendly).
- Screen-space reflections.
- **Dithering** so banding doesn't eat the subtle artwork.

### Volumetric technique as widely described for INSIDE **[I]**

These are from memory of the talk and the general state of the art; we could not open the slides today.

- Per-light ray-marched volumes (spot and point, inside the light's cone or sphere) sampling the light's shadow map at each step.
- Very few steps per pixel, with the start offset jittered by a blue-noise or ordered pattern that changes each frame.
- Temporal reprojection (their TRAA) integrates the noise into smooth shafts.
- The reduced-resolution buffer is upsampled with depth awareness.
- Fog is analytic and gradient-driven, authored per scene.
- HDR bloom, then a final dither before quantisation.

## Fog and colour (our reading of the look) **[I]**

- **Luminance falloff, not hue haze.** INSIDE's water and fog read as **value gradients**: dark foreground silhouettes against a brighter, slightly desaturated far field.
  - The far field is lit, not tinted.
  - Our fog adds in-scattered light that grows with distance and fades with depth, and multiplies by transmittance per channel.
  - Avoid a constant cyan add (the "Subnautica" problem GUM called out).
- **Black is allowed.** Shadows near the camera go to near-black.
- **Accent colour** only where light lands: lamps, the sun shafts near the surface, the volcano. That is where saturation lives. The coral and forest are vibrant **in the beams**, muted out of them.
- **Per-scene colour scripts:**

| Scene | Far field | Shadows | Accents |
|---|---|---|---|
| Shallows | Pale aquamarine-green | Deep teal-blue | Prism fringes, sun-gold caustics |
| Forest | Dimmer jade | — | Reddish twilight at the edge (the book's "reddish twilight") |
| Coral gallery | Near-black blue | — | Warm-white lamp beams; coral red, isis gold |
| Atlantis | Black-violet | — | One warm red-orange source, the volcano; moonlight a cold silver gleam at the end |

## Dithering and banding

- **[V]** INSIDE dithered to stop banding over subtle gradients.
- We add a triangular-PDF blue-noise dither of ±1 LSB at the very end of the post stack, after tonemapping.
- The volumetric buffer is R16G16B16A16F, so it doesn't band internally.

## Bloom and tonemap

- Use URP's own Bloom: threshold ~1.0, intensity 0.6–0.9, scatter 0.65, high quality off on Light.
- Tonemap with URP **Neutral**. AgX isn't built into URP 17; our grade shader adds a gentle AgX-like shoulder in the custom pass when Full quality is on **[I]**.
- Use URP Color Adjustments and Lift/Gamma/Gain from per-scene Volume profiles.

## Decals and hand-placed light, for us

- **URP Decal Projector** (Renderer Feature "Decal", DBuffer off, screen-space technique for the integrated GPU), for:
  - AO blobs under divers, rocks, furniture.
  - Contact shadows at the feet: the Playdead torch trick, a decal that rotates away from the nearest lamp and scales with its height.
  - Wet sheens.
- **Bounce cards:** unlit additive quads with a soft radial texture, or very low-intensity non-shadowed point lights baked into probes.
- **Cookies:**
  - The sun gets an animated caustic cookie, two scrolling layers combined with min() as in the prototype.
  - Lamps get a soft-edged cookie with filament streaks.

## Water and underwater look **[I]**

- From the surface we see Snell's window: a bright disc of sky within ~48.6° of vertical.
- Outside the window, total internal reflection mirrors the seabed. The book describes the walkers seeing "our image clearly reflected, drawn inversely" near the surface (DESIGN_BIBLE §4).
- Marine snow is particles lit only by the same lights the volumetrics use, so it sparkles in beams and vanishes outside them. This is a key INSIDE-like cue.

## Implementation plan for URP 17 (Unity 6)

A `VerneVolumetricsFeature : ScriptableRendererFeature`, using the Render Graph API (`RecordRenderGraph`), with these passes.

**1. March pass**, at reduced resolution into an RGBA16F target.

Per pixel: read the full-res depth (point-sampled at the reduced texel centre). March from the camera, or from the "air box" exit for interiors, to min(depth, maxDistance). At each step:

- **Sun:**
  - The main-light shadow map via URP's `MainLightRealtimeShadow(TransformWorldToShadowCoord(p))`.
  - The caustic and shaft cookie, projected along the refracted sun direction.
  - Kd attenuation by depth.
- **Up to 4 local lights** (lamps, volcano, lantern): spot cones with distance and angle falloff. Shadowing is skipped for them on Balanced and Light, using a cookie instead.
- **Scattering:** Henyey–Greenstein phase g = 0.6–0.8 (water is strongly forward-scattering), σs per channel.
- **Transmittance** along the ray: exp(-σt·t), per channel.
- **Ray start** jittered by a 64×64 blue-noise tile, offset by the golden ratio each frame.

**2. Temporal pass**

- Reproject the previous accumulation with the camera's previous view-projection.
- Neighbourhood clamp in YCoCg (3×3 min/max).
- Blend 0.9 history (0.8 when the camera moves fast).
- Reset on camera cuts.

**3. Composite**

- A depth-aware (bilateral, 4-tap) upsample to full res.
- Composite: scene × transmittance + in-scatter. The analytic fog is in the same shader so both agree.

**Quality tiers:**

| Tier | Res | Steps | Local lights | Shadowed sun steps | Temporal |
|---|---|---|---|---|---|
| Light | 1/4 (e.g. 336×189 at 0.7 × 1080p) | 6 | 2, unshadowed | No (cookie only) | Yes, 0.92 |
| Balanced | 1/4 | 10 | 3, unshadowed | Yes | Yes, 0.9 |
| Full | 1/2 | 16 | 4 | Yes, plus lamp shadow if available | Yes, 0.88 |

**Fallback.** If the feature is disabled or compute support is absent: authored **shaft cards** (additive, depth-faded, soft-particle) plus the analytic fog only. These are cheap but still read as INSIDE-ish.

**Cost estimate for Vega 6** **[I]:**

- 1/4 res at render scale 0.7 is ~64k pixels × 6 steps ≈ 0.4 M samples. Each sample is a shadow lookup plus a cookie, roughly 0.3–0.5 ms.
- The temporal and composite passes are full-res fill, ~0.5–0.8 ms at 1344×756.
- **Budget for the whole feature: ≤ 1.5 ms** at Balanced.

## Pitfalls

- **TAA ghosting** on thin coral against bright fog. Clamp the history; disable history where depth differs by more than 10%.
- **Blue-noise flicker** when temporal is off. On Light, keep temporal on, as the cost is small.
- **Shadow cascades:** use one cascade, 40 m distance, to stay cheap. Shafts beyond 40 m use the cookie only.
- **Upsample halos** at silhouettes. Use a bilateral upsample with a depth threshold; this is what makes silhouettes crisp, the core INSIDE look.
- **Don't fog the interior.** The Nautilus uses an air box: the march starts where the ray leaves the hull glass (saloon windows).
- **URP 17 Render Graph:** don't use the legacy `Execute()` path. Compatibility Mode is off by default in Unity 6.
