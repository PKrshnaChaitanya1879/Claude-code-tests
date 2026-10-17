# Progress: Twenty Thousand Leagues (Unity)

Each run appends to the log at the bottom and keeps this checklist honest.
- **Done:** tick an item only once it is verified, not merely when it has been written.
- **Partly done:** use `[~]` and say what is missing.

## Milestones

### M0 · Toolchain and research
- [ ] Toolchain check: Blender via `pip install bpy` (or the official 4.2 LTS tarball), dotnet SDK, FBX export, ffmpeg, FluidSynth or sfizz, a free soundfont or VSCO-2-CE samples, pedalboard. Record what works in `Source/TOOLCHAIN.md`.
- [ ] C# compile check against Unity 6 reference assemblies (search NuGet or GitHub for UnityEngine and UnityEditor reference DLLs matching 6000.x). If impossible, document it and keep code conservative.
- [ ] `Source/DESIGN_BIBLE.md`, extracted from the book:
  - Nautilus figures and every exterior and interior detail, with chapter citations.
  - Every species named in Part I ch. XV–XVII and XXIII–XXIV, and Part II ch. IX, marked visible or not and priority.
  - Diving-dress details; Atlantis description.
- [ ] Illustration catalogue `reference/illustrations/CATALOGUE.md`: file → caption → what it shows → which model or scene uses it.
- [ ] Notes on the Playdead GDC 2016 rendering talk (verify by web search) in `Source/INSIDE_NOTES.md`.

### M1 · Unity skeleton
- [ ] Project files:
  - `Packages/manifest.json`: URP 17, Input System, Cinemachine 3, Timeline, AI Navigation.
  - ProjectSettings: linear colour space, URP asset with quality tiers, FSR, 30/60 cap.
- [ ] Editor bootstrap: **Verne → Build Everything**, plus a one-time auto-run. It builds the scenes (Title, Nautilus, Mission I, Mission II, or additive), materials, lighting settings and build settings, and writes a report file.
- [ ] Player:
  - BioShock-like weight: acceleration, head-bob, footsteps by surface.
  - Air and water modes (heavy diving dress), crouch and kneel, ladder.
  - Camera collision; held items that never clip.
- [ ] Interaction system: look-at highlight, verbs, hold-to-turn valves, physical levers and needles.
- [ ] Settings: quality, sensitivity, invert Y, volumes, subtitles, 30/60 cap.

### M2 · The Nautilus
- [ ] Exterior faithful to the book and the engravings, with LODs.
- [ ] Interior upgraded from `reference/blender/build_nautilus.py`:
  - Saloon: luminous ceiling, organ, paintings, cases, fountain, crystal windows, sliding panels.
  - Library, Nemo's room with its instruments, Aronnax's cabin, corridors, robing-room, flooding cell.
- [ ] Simplified `_col` collision meshes; no walk-through anywhere.
- [ ] Interactables working the way the book describes.
- [ ] The flooding-cell sequence, Iron Lung style.
- [ ] The saloon window as a real view of the exterior.

### M3 · Underwater rendering (INSIDE)
- [ ] URP renderer features:
  - Per-channel absorption and depth fog.
  - Quarter-res ray-marched volumetrics (blue noise plus temporal).
  - Caustic cookie; marine snow lit by the lamps.
  - Snell's window and total internal reflection.
  - Bloom, grade, dithering; the helmet port and its breath fog.
- [ ] Hand-placed decal AO, contact shadows and bounce cards, as Playdead did.
- [ ] Colour script per scene: vibrant where the light is; black silhouettes against luminous fog.
- [ ] Quality tiers that hold 30 fps on the target laptop (estimate with a budget: triangles, draw calls, fill).

### M4 · Mission I
- [ ] Terrain and route: sunlit bottom → submarine forest → coral gallery (lamps) → coral tree forest → cemetery glade.
- [ ] Flora: corals, isis, gorgonians, sea-anemones, algae and fucus, sponges, sea-stars.
- [ ] Fauna: fish schools, medusae, crustaceans and more, animated. Book species first.
- [ ] Divers (Nemo, crew, Ned, Conseil): rigged and animated (walk, carry, dig, lower, kneel, kneelCross, adieu, beckon), on NavMesh.
- [ ] Burial timeline with sparks from the pickaxe; the player can kneel.

### M5 · Mission II
- [ ] Plain with pennatules → petrified copse → crevice → log bridge over the chasm → crustacean eyes → ruins → summit.
- [ ] Volcano: crater, lava cascades, scoriae, glow as the only light; heat shimmer, subtle.
- [ ] Atlantis: temples, acropolis with a Parthenon outline, aqueduct, quay, streets; seaweed mantles.
- [ ] Chalk ATLANTIS on the basalt; the moon's gleam; respawn on falls.

### M6 · Sound and music
- [ ] SFX library and ambient beds; mixer snapshots for air, water, helmet and cell flooding; depth-driven filtering; rain heard from below.
- [ ] Original score, mixed and exported as OGG: title, Nautilus interior, Nemo's organ, Mission I wonder, the burial, Mission II night walk, the Atlantis reveal, end card.

### M7 · Interface
- [ ] Title: a live in-engine shot.
- [ ] Chapter and loading cards with the 1871 engravings and a book quote.
- [ ] Notes, subtitles, pause and settings, end cards.
- [ ] Premium typography, one accent colour.

### M8 · Optimisation and robustness
- [ ] LODs, static batching, GPU instancing, occlusion culling, baked lighting, texture compression.
- [ ] Collision audit (scripted raycast sweeps) and NavMesh audit.
- [ ] `Docs/PERFORMANCE.md` with budgets and measured or estimated numbers.

### M9 · Polish
- [ ] Cinematic beats (light letterbox at the burial and the Atlantis reveal), never long.
- [ ] Final pass against every reference engraving and against GUM's critiques: INSIDE look, not Subnautica; not bleak.
- [ ] `HOW_TO_OPEN.md` is accurate.

## Log

- **2026-10-17 (setup session):**
  - Created this branch with the reference material: web prototype, Blender scripts and models, book text, 1871 engravings, textures, paintings and screenshots.
  - Wrote `BRIEF.md` and `PROGRESS.md`.
  - No Unity work yet.
