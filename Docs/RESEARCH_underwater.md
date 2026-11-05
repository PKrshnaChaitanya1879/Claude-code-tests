# Research: the real ocean, for Fathom

*Written 5 Nov 2026 (live session on the RTX 3050 laptop), before any building. Each section gives what the sources say, then **→ Fathom:** what we change because of it. Sources are listed at the end and numbered in [brackets]. Where physics and Verne disagree, Verne wins and the note says so.*

---

## 1. How light behaves in sea water

### 1.1 Absorption by wavelength: red goes first
- Pure water absorbs weakly in the blue and strongly in the red. Pope and Fry's integrating-cavity measurements (the reference values oceanographers still use) put the absorption minimum near 418 nm, at about 0.0044 m⁻¹ [1]. NASA's ocean-optics protocol tabulates the same data: about 0.29 m⁻¹ at 630 nm and 0.62 m⁻¹ at 700 nm, against about 0.02 m⁻¹ at 500 nm [2].
- In practice that means red light is down to about 1/e after only **~3 m** of water, green after ~15–20 m, and blue after 50 m or more. A diver at 10 m sees a world with almost no red in it unless a lamp is near.
- Real sea water adds three things to pure water: phytoplankton (absorbs blue and red, scatters), dissolved organic matter ("CDOM", absorbs blue strongly, which is why coastal water turns green rather than blue), and mineral particles (scatter, little colour).
- We worked the numbers with a standard bio-optical model: Pope & Fry water, CDOM falling exponentially from 440 nm, chlorophyll-scaled phytoplankton absorption and particle scattering. Averaged over three bands (R 600–680, G 500–570, B 430–490 nm):

| Water | a R / G / B (m⁻¹) | c (extinction) R / G / B | single-scatter albedo R / G / B | Black-object visibility (≈4.8/c), green |
|---|---|---|---|---|
| Coastal, Crespo-like (chl 0.5, CDOM 0.03) | 0.35 / 0.07 / 0.07 | 0.52 / 0.28 / 0.30 | 0.32 / 0.74 / 0.78 | ~17 m |
| Clear coral water (chl 0.15, CDOM 0.01) | 0.34 / 0.06 / 0.03 | 0.42 / 0.16 / 0.15 | 0.19 / 0.63 / 0.78 | ~31 m |
| Deep ocean (chl 0.05, CDOM 0.005) | 0.34 / 0.05 / 0.02 | 0.38 / 0.10 / 0.08 | 0.11 / 0.49 / 0.74 | ~47 m |

- The key fact for rendering is that **the red channel is absorbed, not scattered** (albedo 0.1–0.3), while green and blue are mostly scattered (albedo 0.5–0.8). So distant water glows blue-green, and red simply vanishes; it doesn't turn into red haze.

**→ Fathom:**
- New `WaterOptics` model (C#): the scene sets chlorophyll, CDOM and silt, and the code derives per-channel absorption, scattering, extinction, albedo and Kd from the physics above, instead of hand-picked colours. `VerneWater` gets an `optics` switch (**Physical** / **Artistic**), so the old tuned look is one key away for comparison (F7 in play).
- The old Mission I water had red extinction 0.075 m⁻¹, about five times too low: red survived 13 m of water. With physical water, coral and weed lose their reds a few metres away and get them back only inside the lamp's reach, as in real underwater photographs.

### 1.2 Depth falloff of daylight (Kd)
- Downwelling daylight falls off exponentially with depth at the *diffuse attenuation coefficient* Kd. Jerlov's classic water types are defined by it: oceanic IA has Kd(490) ≈ 0.035–0.040 m⁻¹ and type III ≈ 0.115–0.14 m⁻¹, with 1% of surface light reaching 88 m (IA) or 34 m (III) [3].
- Kd differs per wavelength in the same way absorption does, and it can be predicted at every wavelength from its value at one wavelength [4]. So one "clarity" number is enough to drive all three channels.
- Kd is roughly the absorption plus a little backscatter, divided by the mean cosine of the light (~1.08 × (a + b_b) near the surface).

**→ Fathom:** Kd is now derived from the same optics (no separate hand-tuned value), so the sunlight that reaches the floor, the colour of the water and the shafts all agree. Surfaces lit by the sun get the light that is left at *their own* depth, per channel (already in `VerneWater.DaylightAt`, now fed by the physics).

### 1.3 Scattering and visibility
- Most underwater scattering is strongly forward-peaked (particles much bigger than the wavelength). Henyey–Greenstein with g ≈ 0.8–0.9 is the usual real-time fit; we already use it (g 0.82 in Mission I).
- A black object disappears at roughly 4–5 attenuation lengths (4.8/c). That is the "fog distance" a diver perceives.
- Light scattered once is not the whole story: in water with albedo 0.7+, multiply-scattered light fills shadows with a soft glow. Hillaire's Frostbite work handles participating media in a physically based way (extinction, scattering and phase decoupled from lighting) and shows that a single-scattering integral with energy-conserving steps matches a path tracer closely [5][6].
- Verne, 30 ft down off Crespo: objects were clearly visible "at a distance of a hundred and fifty yards" (≈137 m), fading through ultramarine into obscurity (I.XVI). That needs c(green) ≈ 0.035 m⁻¹, the clearest ocean water there is.

**→ Fathom:**
- Crespo uses very clear oceanic water (chl ≈ 0.04) so the book's long view survives, but with silt near the floor (see §3.3) so the INSIDE gradient (brighter above, darker below) stays.
- Cheap multiple scattering: the march adds an ambient in-scatter term weighted by albedo² (a two-octave approximation in the spirit of Wronski/Hillaire), so shadowed water isn't dead black where it shouldn't be.

### 1.4 Caustics
- Caustics are sunlight focused by the curved wave surface onto the floor. They are sharp just under the surface and blur out with depth, because each point on the floor sees a wider patch of surface the deeper it is [7]. Artists working from reference keep them crisp near the surface and soft deeper down [7].
- Water's dispersion splits the focused lines into faint colour fringes. Verne saw exactly this off Crespo: flowers, rocks and shells "shaded at the edges by the seven solar colours" (I.XVI, our design bible).
- Real-time options range from fully physical (photon or height-field tracing [8][9]) to an animated texture projected in world space, reconstructed from the depth buffer [10][11]. The GPU Gems chapter by Guardado and Sánchez-Crespo is still the classic aesthetic approach [11].

**→ Fathom:**
- Caustics move out of the URP light cookie (which lit every surface equally sharp at every depth) into the water pass. The composite pass reconstructs each pixel's world position and normal from depth, and adds the caustic web only on surfaces that face the sun, outside shadow, **sharp near the surface and blurring with depth**, fading out by ~20 m.
- On Full quality the web is sampled three times with tiny offsets per channel: Verne's prism fringes. Light quality samples it once.
- The same blurred caustic texture keeps driving the light shafts in the march, so the rays and the web on the floor come from one cause.

### 1.5 God rays / light shafts
- Shafts are single-scattered sunlight whose visibility is modulated by occluders (the shadow map) and by the surface caustics. They are only visible where the scattering is strong, looking toward the light (forward scattering).
- Our march already does exactly this: shadow-map occlusion plus a depth-blurred caustic cookie, Henyey–Greenstein phase, temporal accumulation (commit a773057, "no painted streaks").

**→ Fathom:** kept. On the 3050, Full gets more steps (48) at half resolution, so the edges of rays from kelp and the ridge resolve; plus the new physical extinction makes rays fade naturally with distance (they turn blue-green and dim, rather than staying white).

---

## 2. Volumetric lighting in URP on Unity 6.6, for an RTX 3050 laptop (4 GB)

### 2.1 What's available
- **URP has no built-in volumetric fog** (HDRP does). The options are a custom renderer feature (ours), or a package:
  - CristianQiu's *URP Volumetric Light* (open source): main, spot and point lights with shadows and cookies, integrated in URP's Volume system, Render Graph support in Unity 6, verified in DX11/12 and Vulkan; stated support only **up to Unity 6000.5** [12]. We're on 6000.6, so it's an unknown, and our network on the old laptop couldn't fetch packages anyway.
  - Commercial single-pass "height fog + shadow shafts" assets exist for Unity 6.3+ [13], but they are general fog, not water optics.
- **Frostbite-style froxels** (frustum-aligned 3D textures, one scattering sample per froxel, then integrated along the view ray [6]) would give us correct volumetric shadows for every lamp, but need compute shaders, several 3D textures (~50–100 MB at 160×90×128 RGBA16F) and a light-culling setup. It is the right tool for many local lights; we have one sun and at most four lamps.
- **INSIDE's approach** (GDC 2016): per light, march from the eye to the depth buffer, sampling the light's projected texture, shadow map and falloff texture at each step; very few samples, jittered with **blue noise**, then temporally accumulated. They also capped the fog's intensity so very bright lights still shine through [14][15]. Playdead's temporal reprojection anti-aliasing is what turns the few noisy samples into smooth shafts [16].

### 2.2 How our VerneWater raymarch compares
| | INSIDE | Ours today | After this session |
|---|---|---|---|
| March | Per light, to depth, few steps | One march for sun + 4 lamps, to depth, 14–32 steps | Same, 12 / 20 / 32 / **48** steps by tier |
| Jitter | Blue noise | Interleaved gradient noise | IGN + golden-ratio frame offset (blue-noise-like in time); IGN is what Jimenez's TAA uses and costs no texture |
| Temporal | TRAA | Reprojection + neighbourhood clamp | Same, history weight raised on Full (0.92) |
| Shadows | Per-light shadow maps | Sun shadow map only; lamps unshadowed | Same (see "not done") |
| Medium | Art-directed fog | Per-channel extinction, art colours | **Physical optics** (§1), plus albedo² multiple-scatter term |
| Caustics | n/a | URP cookie on the sun | In the water pass, depth-blurred, chromatic on Full |
| Lamp light on surfaces | n/a | URP spot, no water absorption on the way to the surface | Lamp colour filtered per channel by the water over its own reach (red dies with distance from the lamp too) |

### 2.3 Budget on the 3050 laptop
- An RTX 3050 laptop GPU has roughly 5–9 TFLOPS depending on its power limit: 5–8× our old target (Vega 6, ~1.1 TFLOPS).
- Full tier at 1080p: 960 × 540 × 48 steps ≈ 25 M samples (one shadow tap + 4 lamp terms each). Scaling our measured-on-paper estimate (Vega 6: 8.3 M samples ≈ 5 ms), that is ≈ 2–3 ms on the 3050. Composite with caustics adds ~0.5 ms. Well inside 33 ms.
- VRAM: the water pass needs three half-res RGBA16F targets (~4 MB). The 4 GB card's real pressure is textures, so the new texture packs are 1K (2K only for the seabed sand), BC7/DXT5 compressed with mipmaps (§5).
- Geometry: the **GPU Resident Drawer** (Unity 6) draws MeshRenderers with GPU instancing through the BatchRendererGroup API, if the renderer uses **Forward+**, the SRP Batcher is on, and the platform supports compute (not GLES) [17][18]. It works best when many objects share one mesh [18]. In 6000.6 the docs list LOD-group cross-fade among unsupported features [17]. That fits the density work exactly: many copies of few meshes.

**→ Fathom:**
- New quality tier **"High"** (between Full and the old tiers) is not needed: Full is retuned for the 3050, and auto-selected when the GPU is discrete with ≥ 3.5 GB VRAM. Light stays for integrated GPUs (Ryzen 3 5300U class): ¼ res, 12 steps, no chromatic caustics, no extra scatter.
- Full and Balanced switch the renderer to Forward+ and enable the GPU Resident Drawer; Light stays on Forward (integrated GPUs and old drivers).
- Small scatter (pebbles, shells, granules) is drawn with `Graphics.RenderMeshInstanced` from a single component per patch, culled by distance per tier, with no colliders (they are below ankle height); anything above the ankle is a normal MeshRenderer with a collider, so the GPU Resident Drawer instances it.

---

## 3. Physics of the underwater world

### 3.1 A diver in a weighted dress
- A 19th-century and later standard dress was heavy: lead chest and back weights of roughly 36–40 lb each and lead-soled boots of about 16 lb each are the figures in a 1909 manual [19]; a 1898 description gives 32 lb for the pair of boots [20]. The US Navy Mark V's air hat and breastplate weighed 54 lb, the weight belt 85 lb and the boots 35 lb a pair [21]. A complete dress could reach about 86 kg [22].
- Under water most of that weight is cancelled by buoyancy; what remains is a diver who is slightly negative, very massive (body + gear ≈ 150 kg to accelerate) and dragged by the water.
- **What that looks like:** short, deliberate steps, the boot lifted only a little, the body leaning forward into the drag, slow starts and slow stops (inertia), arms used for balance, turning the whole body (the helmet doesn't turn with the head). A modern hard-hat diver describes the first stand-up in ~65 kg of gear as a shock [23].

**→ Fathom:**
- Player suited gait: lower top speed (1.1 m/s), acceleration ~0.6 m/s² and braking ~0.9 m/s² (water drag gives a smooth exponential stop rather than a skid), head-bob slower and deeper, a slight forward lean when moving, and turning rate capped (the head turns inside a helmet, so look-yaw is limited to ±35° before the body follows).
- Divers (Nemo, crew): stride length shortened, boot lift lowered, step period lengthened in `DiverPuppet`, and a forward lean proportional to speed.
- Each footfall kicks up silt (§3.3).

### 3.2 Particles and marine snow
- Marine snow is >0.5 mm aggregates of organic detritus [24]. Measured sinking speeds range from about 5 to 200 m/day [25]; a field campaign saw averages rise from ~17 to almost 100 m/day as particles grew [24]. Single algal cells sink under a metre a day, aggregates 10–100 m/day [26]. Large fluffy aggregates (4–5 mm) can sink as slowly as ~1 m/day while compact 1–2.5 mm ones sink ~36 m/day [27].
- 100 m/day is about **1 mm/s**: on screen, marine snow is practically **suspended**. What you actually see it do is drift with the current and the wave surge, and swirl in the wake of moving things.

**→ Fathom:**
- `MarineSnow`: sinking speed 0.5–2 mm/s (size-dependent, larger = fluffier = slower), a slow horizontal current drift (2–5 cm/s), an oscillating wave surge in shallow water (period 8–12 s, amplitude falling with depth), and a wake push from the player and divers. Particles are lit only by the light that reaches them (sun with depth + lamp cone), as INSIDE's particles were lit only inside a light.

### 3.3 Sediment: kicking it up and letting it settle
- Settling speed scales with grain size squared (Stokes) for silt and very fine sand [28][29]. USGS gives settling velocities of about 0.06 cm/s for coarse silt, 0.26 cm/s for very fine sand and 1.0 cm/s for fine sand [30]; fine silt or flocculated clay settles at only ~0.02–0.03 cm/s [31].
- Very fine sand and finer is moved mainly in suspension once stirred; fine sand needs a noticeably stronger current to move at all [30].
- **What that looks like:** a boot on fine sand throws a small fast puff that falls back within 1–2 s (sand, ~1 cm/s); on silt it raises a soft cloud that hangs for many seconds to minutes (silt, < 1 mm/s), drifting with the current and slowly thinning.

**→ Fathom:**
- `SedimentPuff` on every footstep (player and divers): a burst of 30–60 soft particles whose behaviour depends on the floor: **sand** (fast fall, 1–2 s), **silt** (slow settle, 8–15 s, drifting, larger and softer), **rock** (almost none). Particles take the floor's colour and are lit like marine snow (dark outside the light).
- The burial's digging uses the same puff (silt clouds round the grave).

### 3.4 Plants and kelp in the current
- Flexible blades in waves follow the orbital motion of the water; how much they move depends on the ratio of hydrodynamic force to stiffness (the Cauchy number) and on the blade length relative to the wave's orbital excursion [32][33]. Wave orbital motion shrinks quickly with depth, becoming negligible below about half a wavelength [34]. Long-period surge makes a canopy closely mimic the surrounding water [34].
- **Verne disagrees for Crespo:** the forest is the "region of perpendicularity", plants rising straight and motionless (I.XVI). Our forest already obeys him (it gives way to a diver and springs back).

**→ Fathom:**
- Crespo forest and prairie stay motionless (the book), except a barely visible surge in the first 5 m below the surface.
- Giant kelp and the soft weeds elsewhere (sunlit plain edges, Atlantis's weed mantles) get a physically shaped sway in `Verne/Flora`: a slow surge (period 8–12 s) whose amplitude falls with depth below the surface as exp(−k·depth), bending more toward the tip (tip displacement ∝ height²), with a small per-plant phase so a field moves like a wave passing, not in unison.
- Coral, gorgonian fans and sponges are rigid: no sway (fans flutter only at their edges in the surge zone).

### 3.5 The Ruhmkorff lamp and the volcano
- The Ruhmkorff lamp was an early portable electric lamp: a Geissler tube excited by a battery-driven Ruhmkorff induction coil, first used in the 1860s for miners; early tubes filled with carbon dioxide gave white light, later ones used nitrogen (reddish) and uranium glass (green fluorescence) [35][36]. A Geissler tube's glow is quite dim in ambient light [37]. Verne himself calls the lantern's light "white and continuous" (I.XVI).
- **GUM's rule wins over the history here:** warm filament light, nothing white. We keep a warm, slightly greenish-amber lamp (as if seen through the lantern's thick glass and a few metres of water), not white.
- In water, a lamp's light falls off with inverse-square **and** per-channel absorption along the path, both lamp→object and object→eye. Red dies within a few metres, so the lamp's warm colour only survives on things close to it; further away its light turns yellow-green.
- **The volcano:** physically, light from a fire two miles away through ocean water would be absorbed to nothing (even green loses 1/e every ~10–20 m). Verne has a "reddish spot … about two miles" off that lights the way vaguely (II.IX). We keep Verne: the glow uses an artistic transmittance floor, documented in code, so it carries; near the crater, the physics applies and the lava's red only survives within ~10 m.

**→ Fathom:**
- Lamp in-scatter in the march keeps inverse-square × exp(−σt·d) per channel (already correct), now with the physical σt.
- New: hero lamps' **surface** light is filtered per channel by the water over its effective reach (`VerneWater` tints each URP lamp light by exp(−σt·r/3)), so the floor at the edge of the beam goes yellow-green, not orange.
- Lamp colour: 2,400 K filament amber, slight green from the glass; intensity stays modest (it's a Geissler lantern, not a searchlight).

---

## 4. INSIDE: water, fog and references

- **The GDC talk** (Gjøl and Svendsen, 2016) covered local shadowed volumetrics, a robust water-rendering system, lighting authored as separate diffuse, specular and bounce entities, analytic primitive-based AO, screen-space reflections and dithering against banding [14].
- From the talk transcript: a light-prepass renderer; fog intensity capped so bright light sources shine through; volumetrics marched to the depth buffer sampling the projected texture, shadow map and falloff texture; going from 24 samples to 3 with blue-noise jitter, because the eye forgives blue-noise far more than white noise [15].
- **Playdead's blog** (Marek Bogdan): fine environmental detail and technical touches throughout [38]; flicker curves on lights linked to sound, AO decals that follow falling debris, a cone emitter of red particles reading as lit water dust round a submerged button, a fog plane tied to the directional light [38]; and from "The Lighting of INSIDE" (in our INSIDE_NOTES): no GI, hand-placed bounce/spec/AO decals, cookies to texture simple scenes, torch shadows as decals [INSIDE_NOTES.md].
- **Temporal reprojection** (Pedersen, GDC 2016) is what made the stochastic volumetrics usable [16].
- **Other references:** Hillaire's Frostbite volumetrics [5][6]; GPU Gems ch. 2 caustics [11]; Alexander Ameye's world-space caustics from the depth buffer [10]; Timothy Cole's underwater caustics breakdown (keep caustics sharp near the surface, soft shadows underwater, particles in velocity fields) [7].

**→ Fathom:**
- Fog cap: the composite now limits the in-scattered light added over very bright pixels (lamps, lava) so they shine through the water, as INSIDE did.
- Dithering stays (±1 LSB, IGN) and is applied after the new caustics too.
- "Lit water dust" in the lamp cone: marine snow and sediment are lit only inside the light (§3.2–3.3).
- AO decals under the new scatter clusters (big rocks only, to keep draw calls down).

---

## 5. Materials and density (what research changed in the plan)
- **Textures:** real CC0 scans only (Poly Haven, ambientCG), at 1K (2K for the seabed sand, which fills half of every frame), BC7 (albedo) and BC5/DXT5nm (normal), roughness in its own channel, mipmaps on. At 1K, a full albedo/normal/roughness set is ~2.7 MB compressed, so ten packs stay under 40 MB of VRAM.
- **Verne's sand:** off Crespo the sand is "fine, even sand, not wrinkled" (I.XV) at 30 ft, i.e. **no ripples** on the sunlit plain. Ripples belong where the bottom shoals or a current runs: the forest edge, the coral kingdom's approach, the Atlantis plain. We put ripples there, not under the spawn.
- **Density:** clustered placement (a few dense groups with sparse scatter between, as real reefs and rubble fields look), never grids; the walking route is kept clear by a corridor test in the scatter code itself, then checked again by `RouteAudit` when the scene is built.

---

## What this session will not do (honest limits)
- **Lamp shadows in the water.** Each Ruhmkorff lamp's beam isn't shadowed in the march (rays from the lamp aren't blocked by rocks). Doing it needs the lamp's index in URP's additional-light shadow atlas, which our pass doesn't get from Render Graph. Possible later; not now.
- **True refractive caustics** (height-field or photon tracing [8][9]) are beyond a 4 GB laptop at 30 fps with everything else; we use the projected, depth-blurred caustic texture.
- **Froxel volumetrics** [6]: not needed for one sun and four lamps; our per-pixel march is cheaper here.
- Nothing here has run inside Unity in this session: GUM tests on her laptop.

---

## Sources
1. Pope, R. M. & Fry, E. S. (1997), *Absorption spectrum (380–700 nm) of pure water. II. Integrating cavity measurements*, Applied Optics 36, 8710–8723. Summary and data: https://omlc.org/spectra/water/abs/pope97.html
2. NASA Ocean Optics Protocols, vol. IV ch. 1, Table 1.1 (erratum 2003): https://oceancolor.gsfc.nasa.gov/files/resources/docs/technical/volivch1err1.pdf
3. Sarangi, Chauhan & Nayak (2002), *Vertical diffuse attenuation coefficient (Kd) based optical classification…*, J. Earth Syst. Sci. 111: https://repository.ias.ac.in/98963
4. Austin & Petzold (1986), *Spectral dependence of the diffuse attenuation coefficient of light in ocean waters*, Optical Engineering 25(3): https://doi.org/10.1117/12.7973845
5. Hillaire, S. (2015), *Physically Based and Unified Volumetric Rendering in Frostbite*, SIGGRAPH Advances in Real-Time Rendering: https://www.ea.com/frostbite/news/physically-based-unified-volumetric-rendering-in-frostbite
6. Slides of [5]: https://www.slideshare.net/DICEStudio/physically-based-and-unified-volumetric-rendering-in-frostbite
7. Cole, T., *Working with Underwater Caustics in Real-Time* (80.lv): https://80.lv/articles/working-with-underwater-caustics-in-real-time
8. Yuksel & Keyser, *Fast Real-time Caustics from Height Fields*: https://www.cemyuksel.com/research/heightfield_caustics/fastcaustics.pdf
9. Papadopoulos & Papaioannou (2009), *Realistic Real-time Underwater Caustics and Godrays*: https://graphicon.ru/html/2009/conference/se5/29/29_Paper.pdf
10. Ameye, A., *Rendering realtime caustics*: https://alexanderameye.github.io/notes/realtime-caustics/
11. Guardado & Sánchez-Crespo, *Rendering Water Caustics*, GPU Gems ch. 2: https://developer.nvidia.com/gpugems/gpugems/part-i-natural-effects/chapter-2-rendering-water-caustics
12. CristianQiu, *Unity URP Volumetric Light*: https://github.com/CristianQiu/Unity-URP-Volumetric-Light
13. *Volumetric Fog FX* (Unity 6.3+ URP asset docs): https://marmalade-denim-5a2.notion.site/Volumetric-Fog-FX-357c67e77ad18055b0bac47f04eb09ad
14. Gjøl & Svendsen (2016), *Low Complexity, High Fidelity – INSIDE Rendering*, GDC: https://gdcvault.com/play/1023002/Low-Complexity-High-Fidelity-INSIDE
15. Transcript notes of [14]: https://lilys.ai/notes/292926
16. Toft, Bowles & Zimmermann (2016), *Optimisations for Real-Time Volumetric Cloudscapes* (cites Pedersen's INSIDE TRAA and Gjøl & Svendsen): https://arxiv.org/pdf/1609.05344
17. Unity 6.6 manual, *GPU Resident Drawer*: https://docs.unity3d.com/6000.6/Documentation/Manual/urp/gpu-resident-drawer.html
18. Unity 6.3 LTS manual, *GPU Resident Drawer*: https://docs.unity3d.com/6000.3/Documentation/Manual/urp/gpu-resident-drawer.html
19. *Compressed Air Work and Diving* (1909), p. 41: https://tekniskkulturarv.dk/book/e57860c5-e186-4660-986f-87b5e33013d1?page=41
20. *The Kinston Free Press*, 30 Nov 1898, p. 3: https://newspapers.digitalnc.org/lccn/sn91068514/1898-11-30/ed-1/seq-3/
21. ScubaBoard history thread (US Navy Mark V component weights): https://scubaboard.com/community/goto/post?id=8109462
22. *Standard diving dress* (Wikiwand): https://www.wikiwand.com/en/Standard_diving_dress
23. ScubaBoard, a modern standard-dress dive: https://scubaboard.com/community/goto/post?id=9321945
24. Reinsel, M. (2026), *Marine snow grows faster and fluffier as it sinks*, Eos 107: https://eos.org/research-spotlights/marine-snow-grows-faster-and-fluffier-as-it-sinks
25. *Hidden Comet-Tails of Marine Snow Impede Ocean-based Carbon Sequestration* (arXiv 2310.01982): https://arxiv.org/pdf/2310.01982
26. UiT, *Living Ice*, p. 25: https://en.uit.no/ressurs/uit/mediebok/living_ice/files/basic-html/page25.html
27. Asper, V. L. (1985), *Accelerated settling of particulate matter by 'marine snow' aggregates*, MIT/WHOI thesis: https://darchive.mblwhoilibrary.org/entities/publication/eccf8d75-077d-5b67-b01f-15026131d2c9
28. *Fluid flow: Stokes Law and particle settling* (Geological Digressions): https://www.geological-digressions.com/fluid-flow-stokes-law-and-particle-settling/
29. Sylvester, Z., *Grain settling* notebook: https://nbviewer.jupyter.org/github/zsylvester/notebooks/blob/master/grain_settling.ipynb
30. Signell & Butman (1991), *Estimates of sediment movement and resuspension in the New York Bight*, USGS OFR 91-359: https://pubs.usgs.gov/of/1991/0359/report.pdf
31. Plymouth thesis (1998), resuspension and settling of fine sediment: https://pearl.plymouth.ac.uk/bms-theses/241
32. Luhar & Nepf, *Wave-induced dynamics of flexible blades*, J. Fluids & Structures 61: https://ar5iv.arxiv.org/html/1510.01237
33. Zhu, L. (2020), *Wave Attenuation Capacity of Suspended Aquaculture Structures with Sugar Kelp and Mussels*, U. Maine: https://digitalcommons.library.umaine.edu/etd/3222
34. Kelp-bed hydrodynamics report (eScholarship): https://escholarship.org/content/qt6tt6147f/qt6tt6147f.pdf
35. *Heinrich Daniel Ruhmkorff* (the "Ruhmkorff" lamp): https://ipfs.aleph.im/ipfs/QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco/wiki/Heinrich_Ruhmkorff.html
36. *Gas-discharge lamp* (the Ruhmkorff lamp section): https://en.wikipedia.org/wiki/Gas-discharge_lamp
37. Giangrandi, *Fun with Geissler tubes*: https://giangrandi.org/electronics/geissler/geissler.shtml
38. Bogdan, M. (2017), *The Weight of Detail*, Playdead blog: https://blog.playdead.com/articles/the_weight_of_detail/weight_of_detail.html
