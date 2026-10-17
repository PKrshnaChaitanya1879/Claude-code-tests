# Performance budget (estimates until GUM's laptop measures them)

Target: **30 fps or better** on a Ryzen 3 5300U with integrated Radeon (Vega 6, ~1.1 TFLOPS, shared DDR4), 1920×1080 output. M8 replaces these estimates with Profiler numbers.

## Quality tiers

| Tier | Render scale | Upscale | Water march | Steps | Marine snow | Shadows |
|---|---|---|---|---|---|---|
| Light (default on integrated GPUs) | 0.7 | FSR 1 | 1/4 width × 1/4 height | 6 | 180 motes | sun only, 1 cascade |
| Balanced | 0.8 | FSR 1 | 1/2 × 1/2 | 10 | 350 | sun only |
| Full | 1.0 | — | 1/2 × 1/2 | 16 | 350 | sun |

## The water pass (M3, `VerneUnderwaterFeature`)

Per frame: march at reduced resolution (one shadow-map tap and up to four lamp terms per step), temporal resolve (6 taps), one full-screen copy, and the composite (4 upsample taps, analytic far field).

| Tier | March pixels | Samples (pixels × steps) | Estimate on Vega 6 |
|---|---|---|---|
| Light | 336 × 189 = 64 k | 0.38 M | march ≈ 0.3 ms, copy + composite at 1344×756 ≈ 0.6 ms, **≈ 1 ms** |
| Balanced | 768 × 432 = 332 k | 3.3 M | **≈ 2.5 ms** |
| Full | 960 × 540 = 518 k | 8.3 M | **≈ 5 ms** |

At 30 fps the frame budget is 33 ms, so on Light the water costs about 3% of it. It never runs in the Nautilus interior (no `VerneWater` there) and never for scene-view cameras.

## Geometry (Nautilus interior)

| Block | Triangles | Notes |
|---|---|---|
| Fore (saloon, library, Nemo, Aronnax, dining) | 37.0 k | 1,439 books, 24 canvases and the specimens included |
| Aft (well, corridor, cabins, kitchen, bath, crew, robing-room, cell, engine-room) | 23.2 k | three turning machine parts are not static |
| Exterior hull LOD0 / LOD1 / LOD2 | 7.3 k / 3.7 k / 1.6 k | |

Everything static is marked for static batching and occlusion. Expected draw calls aboard: roughly 150–250 after batching (under the 500 budget). One unshadowed point light per room; the engine-room has three.

## Saloon window

Fish and medusae are GPU-instanced: **6 draw calls** for 153 creatures, skipped entirely while the iron panels are shut.
