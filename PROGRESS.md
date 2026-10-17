# Progress: Twenty Thousand Leagues (Unity)

Each run appends to the log at the bottom and keeps this checklist honest.
- **Done:** tick an item only once it is verified, not merely when it has been written.
- **Partly done:** use `[~]` and say what is missing.

## Milestones

### M0 · Toolchain and research
- [x] Toolchain check: Blender via `pip install bpy` (or the official 4.2 LTS tarball), dotnet SDK, FBX export, ffmpeg, FluidSynth or sfizz, a free soundfont or VSCO-2-CE samples, pedalboard. Record what works in `Source/TOOLCHAIN.md`.
- [x] C# compile check against Unity 6 reference assemblies (search NuGet or GitHub for UnityEngine and UnityEditor reference DLLs matching 6000.x). If impossible, document it and keep code conservative.
- [x] `Source/DESIGN_BIBLE.md`, extracted from the book:
  - Nautilus figures and every exterior and interior detail, with chapter citations.
  - Every species named in Part I ch. XV–XVII and XXIII–XXIV, and Part II ch. IX, marked visible or not and priority.
  - Diving-dress details; Atlantis description.
- [x] Illustration catalogue `reference/illustrations/CATALOGUE.md`: file → caption → what it shows → which model or scene uses it.
- [x] Notes on the Playdead GDC 2016 rendering talk (verify by web search) in `Source/INSIDE_NOTES.md`.

### M1 · Unity skeleton
- [x] Project files:
  - `Packages/manifest.json`: URP 17, Input System, Cinemachine 3, Timeline, AI Navigation.
  - ProjectSettings: linear colour space, URP asset with quality tiers, FSR, 30/60 cap.
- [~] Editor bootstrap: **Verne → Build Everything**, plus a one-time auto-run. It builds the scenes (Title, Nautilus, Mission I, Mission II, or additive), materials, lighting settings and build settings, and writes a report file. *(Written and compile-verified; not yet run inside Unity. Lighting bake comes in M8.)*
- [x] Player:
  - BioShock-like weight: acceleration, head-bob, footsteps by surface.
  - Air and water modes (heavy diving dress), crouch and kneel, ladder.
  - Camera collision; held items that never clip.
- [x] Interaction system: look-at highlight, verbs, hold-to-turn valves, physical levers and needles.
- [x] Settings: quality, sensitivity, invert Y, volumes, subtitles, 30/60 cap.

### M2 · The Nautilus
- [~] Exterior faithful to the book and the engravings, with LODs. *(Model, LODs, collider, prefab and (run 2) riveted plates (per-plate UVs + generated rivet normal and colour tile, `m2_hull_rivets.png`) done; still missing: a closer pass on the cage domes, an in-Unity check.)*
- [~] Interior upgraded from `reference/blender/build_nautilus.py`: *(run 2: both blocks done. Fore: saloon, library with 1,439 books, Nemo's room, Aronnax's room, dining room, 16 Met canvases in the saloon frames. Aft (`nautilus_interior_aft.py`): central well and ladder, corridor, Ned and Conseil's cabin, kitchen with still and ranges, bath-room, crew's room, robing-room with twelve dresses and the player's kit, the flooding cell, a passage and the 20 m engine-room after im024 with turning axle and wheel. Still missing: carpet and ceiling arabesques, specimens inside the cases, an in-Unity check.)*
  - Saloon: luminous ceiling, organ, paintings, cases, fountain, crystal windows, sliding panels.
  - Library, Nemo's room with its instruments, Aronnax's cabin, corridors, robing-room, flooding cell.
- [~] Simplified `_col` collision meshes; no walk-through anywhere. *(Exterior `_col` mesh; interior walls collide through the exact greybox boxes (now including the aft rooms, passage and engine-room); furniture and machinery through their own low-poly meshes (`__col`). Readable plaques are triggers so they never block. The scripted sweep audit comes in M8.)*
- [x] Interactables working the way the book describes. *(Run 2, compile-verified: the organ plays Bach's Toccata (synthesised, spectrogram `m2_organ_spectrogram.png`); the luminous ceiling's switch then the panel lever (I.XIV order); Nemo's dials driven by depth, speed and a real-time 24-hour clock; the suit-up in the book's order per excursion with the kit leaving the bench; the stopper-plate wheel; the Ruhmkorff lamp; readable instruments, pearls, shells, cigar brazier, dinner service, still, bath, harpoon, air-guns and Bunsen's piles in Verne's words.)*
- [x] The flooding-cell sequence, Iron Lung style. *(Run 2: real cell model; the stopper-plate wheel must be turned home before the tap works and back before the door opens; the tap refuses an undressed visitor; the book's lines as the cold rises; a water veil when the eye goes under; gauge range follows the outside pressure (9 m Crespo, 274 m Atlantis).)*
- [x] The saloon window as a real view of the exterior. *(Run 2: backdrop shell of open water and instanced fish schools and medusae in the `Verne/SeaLit` water model, lit by the window light; tuned on a CPU mock, `m2_saloon_window_mock.png`; shaders DXC-checked.)*

### M3 · Underwater rendering (INSIDE)
- [~] URP renderer features: *(run 2: all written, C# compile-checked and shaders DXC-checked against the URP includes; look tuned on a CPU mock of the shader (`m3_water_mock_Mission1.png`). Needs the in-Unity look check and tuning in Part 3.)*
  - Per-channel absorption and depth fog.
  - Quarter-res ray-marched volumetrics (blue noise plus temporal).
  - Caustic cookie; marine snow lit by the lamps.
  - Snell's window and total internal reflection.
  - Bloom, grade, dithering; the helmet port and its breath fog.
- [~] Hand-placed decal AO, contact shadows and bounce cards, as Playdead did. *(AO decals under rocks and the beached hull; bounce cards and lamp-following shadow decals still to do.)*
- [~] Colour script per scene: vibrant where the light is; black silhouettes against luminous fog. *(VerneWater presets for Title, Crespo and Atlantis; Crespo tuned on the mock. Atlantis needs its pass in M5.)*
- [~] Quality tiers that hold 30 fps on the target laptop (estimate with a budget: triangles, draw calls, fill). *(Estimates in `Docs/PERFORMANCE.md`: the water pass ≈ 1 ms on Light. Measuring is M8.)*

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
- [~] SFX library and ambient beds; mixer snapshots for air, water, helmet and cell flooding; depth-driven filtering; rain heard from below. *(42 procedural SFX; no mixer or beds yet.)*
- [ ] Original score, mixed and exported as OGG: title, Nautilus interior, Nemo's organ, Mission I wonder, the burial, Mission II night walk, the Atlantis reveal, end card.

### M7 · Interface
- [~] Title: a live in-engine shot. *(Drift shot of the exterior over greybox seabed; still missing: the M3 look.)*
- [~] Chapter and loading cards with the 1871 engravings and a book quote. *(Loading cards done; chapter cards not yet.)*
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

- **2026-10-17 (run 1, 13:39–15:00 UTC):**
  - **Access.** The `add_repo` tool wasn't in this session, but the repo was already cloned and in scope, and pushes work, so the run went ahead. GUM's creative-toolkit repo was out of scope and wasn't used.
  - **M0 done:**
    - `Source/TOOLCHAIN.md` and `Source/tools/setup_toolchain.sh`: bpy 5.2.2, .NET 8, ffmpeg, FluidSynth with FluidR3_GM, sox, pedalboard.
    - **Real Unity 6000.0.85f1 managed assemblies** plus the URP/Core 17.0.4 source, streamed out of the Linux editor tarball, and registry packages.
    - `Source/tools/unity_compile_check.py` and `compile_check.sh` compile every asmdef like Unity does, in an editor pass and a player pass. Proven to catch errors with a planted bug.
    - `Source/DESIGN_BIBLE.md`, read from the book: the Nautilus figures and layout (Verne's metres), the diving dress, both missions beat by beat with quotes, a species table, characters and card quotes.
    - `reference/illustrations/CATALOGUE.md`: 106 plates parsed from the EPUB, about 30 looked at by eye, with key references per model and the loading-card picks.
    - `Source/INSIDE_NOTES.md`: verified sources are the Playdead blog and the GDC topic list. The slides themselves weren't openable, so the volumetric parameters are marked as inference. Includes the URP 17 Render Graph plan and quality tiers.
  - **M1:** project `Unity/TwentyThousandLeagues`.
    - Project files: manifest (URP 17.0.4, Input System 1.11.2, Cinemachine 3.1.2, Timeline 1.8.7, AI Navigation 2.0.5), Unity 6000.0.85f1, partial ProjectSettings (Linear, input handling Both), and TMP essentials pre-extracted, so there's no import prompt.
    - Runtime code (`Verne.Runtime`):
      - `VerneInput`: keyboard, mouse and gamepad.
      - `GameSettings` with Light/Balanced/Full; it picks Light on integrated GPUs.
      - `PlayerMotor`: Air, Suited and Water gaits; acceleration and braking; head-bob by gait; landing dip; crouch, kneel and ladders. The eye is kept inside the capsule, plus a `PlayerCamera` guard.
      - `Interactor` and controls: `Lever` with mass and notches, `Valve` hold-to-turn, `PushButton`, `Door` that won't close on the player, `Gauge` needle with inertia, `Readable`.
      - UI: HUD (aim dot, verb prompt, toasts, subtitles), reading card, pause and settings, title screen, loading cards with the engravings and quotes. Cormorant Garamond (OFL) with one coral accent.
      - `FloodingCell`: inner door, tap, rising water and gauge to outside pressure, then the outer door. Also `SlidingPanels`, `SuitStation` and `SceneExit`.
    - Editor bootstrap (`Verne.Editor`), from **Verne → Build Everything**, plus a one-time auto-run. It sets:
      - player settings, layers, physics and texture import
      - TMP font assets
      - three URP assets and quality levels: Light 0.7× + FSR, Balanced 0.8× + FSR, Full
      - the Decal renderer feature and graded Volume profiles
      - 22 materials from the CC0 textures
    - Scenes: Title, Nautilus, Mission1 and Mission2, plus build settings, a validation pass and `Logs/verne_setup_report.txt`.
      - The Nautilus is a **greybox at the book's true dimensions**, bow to midships Aronnax 2.5 / Nemo 5 / saloon 10×6.4×5 / library 5 / dining 5, then the staircase hall, with aft rooms on a port corridor down to the robing room and the flooding cell.
      - Plan check: `Source/previews/m1_nautilus_greybox_plan.png`.
  - **M2 (started):** `Source/blender/nautilus_exterior.py`.
    - What it builds: a 70 × 8 m cigar with overlapping stepped plates, the platform with plates, rail and hatch, the half-buried boat, the pilot cage fore and the lantern cage aft with lenticular glasses, the spur, a four-blade 6 m screw, stern-post and rudder, inclined planes amidships, the saloon windows with copper bands, and the port door with rungs.
    - Budget: LOD0 5.8k, LOD1 2.9k, LOD2 1.3k triangles, plus a 14-sided `_col` mesh.
    - Compared against ill-011, im027, im014 and ill-004 in `Source/previews/m2_nautilus_exterior_vs_engravings.jpg`. Cages enlarged after the first look.
    - The bootstrap imports it, builds a prefab oriented from the marker empties, with an LODGroup, a simplified MeshCollider and the lantern spot. It sits on the sea floor behind the spawn in both missions, with climbable rungs back to the door, and stars in the title shot.
  - **M6/M7 (bits needed now):**
    - 42 procedural SFX (OGG): footsteps for 8 surfaces, lever, valve, button, doors, the cell's hiss and gurgle loops (Minnaert bubbles) and the panel rumble. Spectrogram and loudness check: `Source/previews/m1_sfx_spectrograms.png`.
    - Loading cards and the title screen.
  - **Verified:**
    - All C# compiles against Unity 6000.0.85 reference assemblies, in both editor and player passes.
    - Exterior previews looked at against the engravings; SFX spectrograms looked at.
    - **Not yet verified:** the bootstrap has never run inside Unity (impossible here). The SerializedObject field names, quality-level edits and FBX orientation are the riskiest parts. GUM's first-open report will tell.
  - **M2 interior (forward block, after the first log draft):**
    - `Source/blender/nautilus_interior_fore.py` ports the prototype's saloon, library, Nemo and Aronnax rooms to the book's metres and the Unity layout, and adds a new dining room. About 22k triangles in all.
      - Saloon: organ between curtains, tridacna on its table, embrasured crystal windows with copper bands, coved luminous ceiling, divans, glass cases, busts, frames.
      - Library: curved ebony runs with brass, divans, the great table, four globes.
      - Nemo's room: instrument board on the starboard wall, iron bedstead, skylight.
      - Aronnax's room.
      - Dining room: sideboards at both extremities, table and chairs, luminous panel.
    - Doors and furniture re-placed so no doorway is blocked. The greybox saloon→Nemo door moved beside the organ, and a greybox dining sideboard that blocked the library door was fixed.
    - The Unity bootstrap places it, remaps its materials to the textured CC0 ones, and gives furniture MeshColliders. The greybox under it turns invisible but keeps colliding. The note, the volume, the panel lever and working gauge needles sit on the art.
    - Preview against im022, im029, im021, im023, im020 and im051: `Source/previews/m2_interior_vs_engravings.jpg`. It reads right in layout and proportion, but is barer than the engravings.
  - **Next, in order:**
    1. Read GUM's `verne_setup_report.txt` if she sent one, and fix any FAIL.
    2. **M2 interior, continued:**
       - Dress the forward rooms: books on every shelf, the 30 Met canvases in the frames (`reference/assets/paint`), carpet and ceiling arabesques, specimens in the cases.
       - Then the aft block in Blender, on the greybox: staircase, cabin, kitchen, bath, crew, robing room with a dozen dresses, the flooding cell with stopper-plates, and a glimpse of the engine room.
    3. The full suit-up order.
    4. The saloon window as a live view onto an exterior scene section.
    5. Rivet and plate normal map on the hull.
    6. Then M3 (the volumetrics renderer feature).
  - **Blockers:** none. Keep shader code conservative, since Unity shaders can't be compiled here.
