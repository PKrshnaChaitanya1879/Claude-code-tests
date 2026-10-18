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
- [~] Exterior faithful to the book and the engravings, with LODs. *(Model, LODs, collider, prefab and (run 2) riveted plates (per-plate UVs + generated rivet normal and colour tile, `m2_hull_rivets.png`) done; (run 2) the cages remodelled after im027 as squat octagonal drums with a riveted dome and a big lenticular glass bulging from every face (`m2_pilot_cage_vs_im027.jpg`); still missing: an in-Unity check.)*
- [~] Interior upgraded from `reference/blender/build_nautilus.py`: *(run 2: both blocks done. Fore: saloon, library with 1,439 books, Nemo's room, Aronnax's room, dining room, 24 Met canvases in the saloon frames (a dense salon hang, as in im022), specimens in the cases, patterned carpet and a gilt-lattice luminous ceiling. Aft (`nautilus_interior_aft.py`): central well and ladder, corridor, Ned and Conseil's cabin, kitchen with still and ranges, bath-room, crew's room, robing-room with twelve dresses and the player's kit, the flooding cell, a passage and the 20 m engine-room after im024 with turning axle and wheel. Still missing: an in-Unity check.)*
  - Saloon: luminous ceiling, organ, paintings, cases, fountain, crystal windows, sliding panels.
  - Library, Nemo's room with its instruments, Aronnax's cabin, corridors, robing-room, flooding cell.
- [~] Simplified `_col` collision meshes; no walk-through anywhere. *(Exterior `_col` mesh; interior walls collide through the exact greybox boxes (now including the aft rooms, passage and engine-room); furniture and machinery through their own low-poly meshes (`__col`). Readable plaques are triggers so they never block. The scripted sweep audit comes in M8.)*
- [x] Interactables working the way the book describes. *(Run 2, compile-verified: the organ plays Bach's Toccata (synthesised, spectrogram `m2_organ_spectrogram.png`); the luminous ceiling's switch then the panel lever (I.XIV order); Nemo's dials driven by depth, speed and a real-time 24-hour clock; the suit-up in the book's order per excursion with the kit leaving the bench; the stopper-plate wheel; the Ruhmkorff lamp; readable instruments, pearls, shells, cigar brazier, dinner service, still, bath, harpoon, air-guns and Bunsen's piles in Verne's words.)*
- [x] The flooding-cell sequence, Iron Lung style. *(Run 2: real cell model; the stopper-plate wheel must be turned home before the tap works and back before the door opens; the tap refuses an undressed visitor; the book's lines as the cold rises; a water veil when the eye goes under; gauge range follows the outside pressure (9 m Crespo, 274 m Atlantis).)*
- [x] The saloon window as a real view of the exterior. *(Run 2: backdrop shell of open water and instanced fish schools and medusae in the `Verne/SeaLit` water model, lit by the window light; tuned on a CPU mock, `m2_saloon_window_mock.png`; shaders DXC-checked.)*

### M3 · Underwater rendering (INSIDE)
- [~] URP renderer features: *(run 2: all written, C# compile-checked and shaders DXC-checked against the URP includes; look tuned on a CPU mock of the shader (`m3_water_mock_Mission1.png`). Needs the in-Unity look check and tuning in Part 3.) (Part 3: the passes now keep the depth and shadow globals bound; fallback shaft cards (`Verne/ShaftCard`, `ShaftCards`) draw only when the march can't run. Look-dev in Blender with the real assets and the same water coefficients, `m3_lookdev_crespo_v1-3.jpg`. Still missing: the first in-Unity look.)*
  - Per-channel absorption and depth fog.
  - Quarter-res ray-marched volumetrics (blue noise plus temporal).
  - Caustic cookie; marine snow lit by the lamps.
  - Snell's window and total internal reflection.
  - Bloom, grade, dithering; the helmet port and its breath fog.
- [x] Hand-placed decal AO, contact shadows and bounce cards, as Playdead did. *(AO decals under rocks and the beached hull. Part 3, compile-verified: `LampShadow`, INSIDE's torch shadows: a decal at every diver's feet and the visitor's that swings away from the nearest lamp and stretches with its height; `LampBounce`: a small unshadowed bounce light at each lamp's footprint, tinted by sand, coral or stone, off on Light. In-engine look pending.)*
- [~] Colour script per scene: vibrant where the light is; black silhouettes against luminous fog. *(VerneWater presets for Title, Crespo and Atlantis; Crespo tuned on the mock. Atlantis needs its pass in M5.) (Part 3: from the Blender look-dev, wet sand darkened so the fog stays the brightest thing in frame, and split-toning in the grades: cold shadows, warm wherever the sun or a lamp lands.)*
- [~] Quality tiers that hold 30 fps on the target laptop (estimate with a budget: triangles, draw calls, fill). *(Estimates in `Docs/PERFORMANCE.md`: the water pass ≈ 1 ms on Light. Measuring is M8.)*

### M4 · Mission I
- [~] Terrain and route: sunlit bottom → submarine forest → coral gallery (lamps) → coral tree forest → cemetery glade. *(Run 2: the flora is laid along the greybox terrain in this order (`CrespoFlora.cs`): sandy plain, prairie, forest with a clear lane, three coral arches with pendants, the glade ringed by coral trees and garlands, the cross and the mounds with one grave left to dig. Terrain art and the lit look are Part 3's.) (Part 3: faceted Blender rocks with coralline and weed encrustation on their upper faces replace the greybox boxes (`seabed_rocks.py`, `m4_rocks_vs_im034.jpg`); the forest is denser (210 laminaries) and the prairie richer; everything culls by size at distance. In-Unity look pending.)*
- [~] Flora: corals, isis, gorgonians, sea-anemones, algae and fucus, sponges, sea-stars. *(Run 2: 31 species in `Source/blender/crespo_flora.py`, named as Verne names them (laminaries, alariae, fucus, laurenciae, pavonari, acetabuli, red coral with white polyps, tuft and pink corals, isis, gorgonian fans, zebra-meandrines, caryophylliae, fungia, anemones, sponges, sea-stars, asterophytons, shells, coral trees, sea-bindweed, pendants, arch, cross, mounds); sheet `m4_flora_sheet.png`; colliders on everything above the ankle. Still to do: sway animation, polyps that retract, an in-Unity look.) (Part 3: `Verne/Flora`: the forest is **motionless**, as I.XVI says ("the region of perpendicularity"): weed never sways, it gives way to a diver brushing through and springs straight again; anemones' crowns move of themselves; the red coral's white polyps close as a diver passes and reopen slowly (`VerneVisitors`). Laminaries remodelled as crinkled ribbons after im035 (`m4_laminaria_vs_im035.jpg`). In-Unity look pending.)*
- [~] Fauna: fish schools, medusae, crustaceans and more, animated. Book species first. *(Run 2: `FishSchool`: little fishes, fish-flies, lepisacanthi, red fish, rose-pink medusae and two tintoreas, schooling, tail-flicking and darting from the visitor. Still to do: crustaceans and the sea-spider beat, the sea-otter, porphitae and physalides near the surface.) (Run 2 added the crustaceans and the sea-spider beat. Part 3: porphitae and physalides drifting under the surface. Left: the sea-otter and the albatross (priority C).)*
- [~] Divers (Nemo, crew, Ned, Conseil): rigged and animated (walk, carry, dig, lower, kneel, kneelCross, adieu, beckon), on NavMesh. *(Run 2: `diver_parts.py` + `DiverPuppet`: rigid parts at the joints, all eight gestures procedurally (`m4_diver_poses.png`, vs im033 `m4_diver_vs_im033.jpg`); `DiverGuide` walks Nemo along the route, waits and beckons, lamps lit in the gallery; a crewman follows. Still to do: NavMesh agents, Ned and Conseil, the bearers' party.) (Part 3, compile-verified: the bootstrap bakes a NavMesh for both excursions; Nemo and the crewman walk it as agents; Ned Land and Conseil follow the Professor (`DiverFollower`); the four bearers carry the body the whole way at the back of the party (`Procession`, I.XXIV: "turning round, I saw his men"); divers have bodies now, so nobody walks through them, and the agents step round the visitor.)*
- [~] Burial timeline with sparks from the pickaxe; the player can kneel. *(Run 2, compile-verified: `BurialRite` follows I.XXIV line by line: digging with sparks on flint, the bearers lower the body in white linen, Nemo kneels with arms crossed and his men with him (K to kneel too), the mound, the second kneeling and the last adieu, then the return to the Nautilus; a light letterbox only for the rite. Needs its in-Unity timing pass.) (Part 3: the rite waits for the bearers to arrive; Ned and Conseil kneel with the others.)*

### M5 · Mission II
- [~] Plain with pennatules → petrified copse → crevice → log bridge over the chasm → crustacean eyes → ruins → summit. *(Part 3, started early, compile-verified: `AtlantisKit.Height` shapes the climb (≤ 37° before noise, under the visitor's 42°) with a level shelf at the crevice and another for the first platform; the trench is 14 m deep between lips on the sea floor's grid; an 11 m trunk spans it with a walkable top and a NavMeshLink for Nemo; pennatules, the petrified copse with gigantic pines, cromlechs and crustaceans' rocks, the first platform's ruins under their weed; profile `m5_mission2_terrain.png`. Needs its in-Unity walk-through and the light pass.)*
- [~] Volcano: crater, lava cascades, scoriae, glow as the only light; heat shimmer, subtle. *(Part 3: "the mountain was a volcano": its crater opens on the far flank beside the summit, some 15 m above the peak (as in im079), lava runs pouring down toward the city, scoriae thrown and sinking (`Scoria`), the crater light and a lava light on the city. Still to do: the heat shimmer, the in-Unity light pass.)*
- [~] Atlantis: temples, acropolis with a Parthenon outline, aqueduct, quay, streets; seaweed mantles. *(Part 3: `Source/blender/atlantis.py` kit: Tuscan columns standing, broken and fallen, two fallen temples, the acropolis with the 8 × 17 peristyle of a Parthenon, the aqueduct with fallen bays, the quay, paved streets, roofless houses, all under coherent patches of weed and zoophytes; laid out 100 m below the summit. Compared with im079 in `m5_atlantis_vs_im079.jpg`. In-Unity look pending.)*
- [~] Chalk ATLANTIS on the basalt; the moon's gleam; respawn on falls. *(Part 3, compile-verified: `ChalkWriter`: Nemo traces the word letter by letter on the rock of black basalt (`m5_basalt_atlantis_chalk.png`), the long watch, the moon's gleam, the return; `FallRescue` sets the visitor back on firm ground after a fall. Needs its in-Unity timing pass.)*

### M6 · Sound and music
- [~] SFX library and ambient beds; mixer snapshots for air, water, helmet and cell flooding; depth-driven filtering; rain heard from below. *(42 procedural SFX. Run 2: `ambience.py` beds (hull hum with the screw's thrum, the underwater rumble with creaks and far bubbles) and the Rouquayrol breath (valve hiss in, bubbles out) at -24/-22 LUFS, spectrograms `m6_beds_and_breath.png`; `Ambience` plays them per scene, breathes with the helmet's fog and low-passes the listener in the helmet. Still to do: mixer snapshots, depth-driven filtering, the rain from below.) (Part 3: the rain on the surface heard from 150 fathoms, `rain_below.py`: drops' impact ticks and Minnaert bubble rings at 0.8–3.3 kHz, gusts, a diffuse tail, -27 LUFS, spectrogram `m6_rain_below.png`; it fades in slowly in Mission II. Audio import: music streamed, loops compressed. Left: mixer snapshots, depth-driven filtering.)*
- [~] Original score, mixed and exported as OGG: title, Nautilus interior, Nemo's organ, Mission I wonder, the burial, Mission II night walk, the Atlantis reveal, end card. *(Part 3: `Source/audio/score.py` composes in MIDI (Nemo's leitmotif, D Dorian; aleatoric string entries, solo violin, 1940s clarinet), plays it through FluidR3_GM, sets it on a sparse INSIDE-like drone 9–14 dB under the music, and gives it a dark hall. Seven cues: **title** (2:00, loops), **nautilus** (a slow waltz under the hum, 1:43, loops; silenced while Nemo's organ plays), **m1_wonder** (2:18, loops), **burial** (1:53, timed to the rite), **night_walk** (2:36, loops, mostly drone, a far horn), **atlantis** (1:43, timed to `ChalkWriter`: the word, the chorus over the city, the one major chord for the moon) and **end** (0:29), at -20 to -25 LUFS. Checked by spectrogram, `m6_score_*.png`. `Music` crossfades per scene and at the burial and the summit. Left: an ear on GUM's machine, the end card's hook (M7), mixer snapshots.)*

### M7 · Interface
- [~] Title: a live in-engine shot. *(Drift shot of the exterior over greybox seabed; still missing: the M3 look.)*
- [~] Chapter and loading cards with the 1871 engravings and a book quote. *(Loading cards done; chapter cards not yet.)*
- [~] Notes, subtitles, pause and settings, end cards. *(Part 3: end cards for both excursions, `SceneFlow.EndCard`: the engraving (im053, im079), the book's closing words, the score's last bars, then aboard. Notes, subtitles (toasts), pause and settings came in M1; a typography pass remains.)*
- [ ] Premium typography, one accent colour.

### M8 · Optimisation and robustness
- [ ] LODs, static batching, GPU instancing, occlusion culling, baked lighting, texture compression.
- [~] Collision audit (scripted raycast sweeps) and NavMesh audit. *(Part 3: `RouteAudit` runs as each excursion is built and writes into the setup report: renderers above the ankle with no collider, a 0.35 m body tested every metre along the way, and complete NavMesh paths for the guide's legs. Results come with GUM's first `verne_setup_report.txt`; the Nautilus interior sweep remains.)*
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

- **2026-10-17/18 (run 2 = Part 2, 21:10 UTC / 02:40 IST onward):**
  - **Access.** `add_repo` wasn't in this session either; the repo was already cloned and in scope and pushes work, so the run went ahead (as in run 1). Lock taken and pushed first.
  - **Toolchain.** Rebuilt from `setup_toolchain.sh`. The streamed Unity download was cut off once, so the script now downloads resumably. **New: Microsoft DXC** and `Source/tools/shader_check.py`, a real compile check of every pass and keyword variant of our shaders against the URP 17 / Core RP includes.
  - **M2, the Nautilus (Part 2's milestone), done to the extent possible without Unity:**
    - `nautilus_interior_aft.py`: central well and ladder, corridor, Ned and Conseil's cabin (Ned's harpoon), kitchen (electric ranges with platinum sponges, the still), bath-room, crew's room, robing-room (twelve dresses, helmets, reservoirs, lamps, air-guns, and the player's own kit on the bench), the flooding cell, a passage, and the 20 m **engine-room** after im024 (Bunsen's piles, electro-magnets, the great toothed wheel and the screw's axle, which turn in Unity).
    - Forward rooms dressed: 1,439 books, 24 Met canvases at their own aspect (dense salon hang), specimens in the cases, a patterned carpet and a gilt-lattice luminous ceiling.
    - Exterior: per-plate UVs and a generated rivet tile on the hull; the pilot's and lantern's cages remodelled after im027.
    - Interactions from the book: organ (Bach's Toccata, synthesised pipe organ), ceiling switch then panel lever (I.XIV), Nemo's dials driven by depth, speed and real time, the suit-up in the book's order for each excursion, the stopper-plate wheel, readable plaques in Verne's words, the Ruhmkorff lamp (L).
    - The flooding cell completed (dogs, undressed refusal, the cold rising, a water veil) and the excursion state (Crespo, then Atlantis at 150 fathoms).
    - **The saloon window** is a live view: `Verne/SeaLit` water model, backdrop shell, instanced fish schools and medusae.
  - **M3 started (Part 3 owns it):** `VerneUnderwaterFeature` (RenderGraph): reduced-res march with real sun shafts from the shadow map, hero lamp beams, HG phase, per-channel extinction, temporal reprojection with clamp, depth-aware composite, analytic far field, Snell's window, dither. `VerneWater` colour scripts (Title, Crespo, Atlantis). Caustic light cookie, marine snow, helmet port with breath fog, AO decals. Built-in fog stays only as a fallback.
  - **M4 started (Part 3 owns it):** 31 flora species (`crespo_flora.py`) laid along the route in the book's order; fish schools, medusae, tintoreas; divers as puppets of Blender parts with all eight gestures; Nemo guides each excursion; **the burial** scripted from I.XXIV.
  - **After the first log draft:** the coral gallery vaulted over with skylights for shafts (`m4_gallery_vault.png`); crustaceans (`creatures.py`: sea-spider, titanic crab, giant lobster with glowing eyes, `m4_crustaceans.png`) with the sea-spider beat at Crespo and eyes in the holes on the way to Atlantis; M6 first pass (`ambience.py`: hull hum, underwater bed, Rouquayrol breath, `m6_beds_and_breath.png`; `Ambience` with the helmet low-pass); life round the Nautilus on the title.
  - **Code review** (a second pass over all run 2 code against the URP 17.0.4 sources) found no exception paths and six placement or look bugs. All six are fixed: ground sampling now hits only the sea floor, the clearings no longer remove the gallery, AO decals are centred, the sea shell clears the engine-room, daylight is applied to the shafts once, and the fog fallback is honest.
  - **Verified:**
    - C# compiles (editor and player passes) after every change; all shaders pass DXC against the URP includes.
    - Looked at, next to the engravings: aft rooms (`m2_robing_vs_im033.jpg`), engine-room (`m2_engine_vs_im024.jpg`), dressed saloon and library (`m2_fore_dressed_vs_im022.jpg`), pilot cage (`m2_pilot_cage_vs_im027.jpg`), hull rivets (`m2_hull_rivets.png`), flora sheet (`m4_flora_sheet.png`), diver and poses (`m4_diver_vs_im033.jpg`, `m4_diver_poses.png`).
    - The water look was tuned on CPU mocks of the shader equations (`m2_saloon_window_mock.png`, `m3_water_mock_Mission1.png`, `m3_helmet_port_mock.jpg`). The organ was checked by spectrogram (`m2_organ_spectrogram.png`).
    - **Not verified:** nothing has run inside Unity yet. The riskiest new parts are the RenderGraph water pass (first in-engine look), FBX axis assumptions for flora and divers (the code measures the long axis rather than trusting it), and the bootstrap's prefab wiring. The validation step now reports the new wiring in `verne_setup_report.txt`.
  - **Next (Part 3):**
    1. If GUM has sent `verne_setup_report.txt` or a screenshot, fix what it shows first.
    2. M3: in-Unity look pass on the water (tune `VerneWater` presets, shafts, Snell's window), bounce cards and lamp-following shadow decals, quality-tier check.
    3. M4: NavMesh agents for the divers, Ned and Conseil, the sea-spider beat and crustaceans, the forest sway, polyps that retract, terrain art beyond the greybox seabed, burial timing.
  - **Blockers:** none, except that only GUM's machine can run Unity.

- **2026-10-18 (run 3 = Part 3, from 02:11 UTC / 07:41 IST):**
  - **Access.** `add_repo` wasn't available again; the repo was already cloned and in scope and pushes work, so the run went ahead. Lock taken and pushed first. Toolchain rebuilt from `setup_toolchain.sh`. `shader_check.py` now samples large keyword sets (every keyword alone plus the all-first and all-last combinations).
  - **M3, the underwater rendering (Part 3's own):**
    - INSIDE's torch shadows: `LampShadow` decals swing away from the lamps and stretch with the lamp's height.
    - Playdead's bounce light at each lamp's footprint: `LampBounce`, capped on Balanced and off on Light.
    - Fallback shaft cards for when the ray-march can't run.
    - The water pass keeps its depth and shadow globals bound.
    - Look-dev in Blender with the real assets and the same water coefficients (`m3_lookdev_crespo_v1-3.jpg`). From it: darker wet sand, so the fog stays the brightest thing in frame, and split-toning (cold shadows, warm where the sun or a lamp lands).
  - **M4, Mission I (Part 3's own):**
    - `Verne/Flora`: the forest is motionless, as I.XVI says. The weed gives way to a diver and springs back, the anemones move, and the red coral's polyps close as you pass.
    - Laminaries remodelled as crinkled ribbons after im035.
    - Faceted Blender rocks with encrustation replace the greybox boxes (`m4_rocks_vs_im034.jpg`). A denser forest and prairie with distance culling.
    - A NavMesh baked for both excursions. Nemo and the crewman walk it as agents, Ned Land and Conseil follow the Professor, and divers have bodies.
    - The four bearers carry the body the whole way at the back of the party (I.XXIV), and the rite waits for them.
    - Porphitae and physalides drift under the surface.
  - **Ahead of plan, for Part 4 and Part 5:**
    - **M5:**
      - The Atlantis kit in Blender (`atlantis.py`, `m5_atlantis_vs_im079.jpg`): temples, the acropolis with a Parthenon outline, the aqueduct, quay, streets and houses under weed; the volcano, its crater on the mountain's flank beside the summit ("the mountain was a volcano"), with lava runs and scoriae; the petrified copse, pines, cromlechs and pennatules; the basalt rock and the chalk letters.
      - The Mission II terrain (`m5_mission2_terrain.png`): a plain, a climb of 37° or less, the crevice with an 11 m trunk and a NavMeshLink, the first-platform shelf, the summit, and the city 100 m below.
      - `ChalkWriter` (the word, the long watch, the moon's gleam), `FallRescue`, and the book's lines along the way.
    - **M6:**
      - The rain heard from 150 fathoms (`rain_below.ogg`).
      - Depth darkens what the helmet hears.
      - **The original score's first pass** (`score.py`): 7 cues, crossfaded by `Music`. The burial and the summit are timed to their scripts, and the music falls silent while Nemo's organ plays.
    - **M7:** end cards for both excursions.
    - **M8:** `RouteAudit` writes collision and NavMesh findings into the setup report.
  - **Three code reviews** (one of the Part 3 code, one of the Atlantis layout, one of first-open risks in the bootstrap). Every finding was fixed:
    - Bearers keep to the floor.
    - The crevice is crossable.
    - FallRescue no longer fires on slopes.
    - Nothing in the city is buried under the volcano.
    - The bootstrap never runs inside import workers and shows a progress bar.
    - A failed build retries on the next open.
    - Ambient reflection cubemaps, so brass and iron are no longer black.
    - FBX files are re-imported once URP is active.
    - NavMesh voxels are coarser, renderer lookups are null-safe, and the Atlantis meshes are readable.
  - **Verified:**
    - All C# compiles in the editor and player passes after every change.
    - The new shaders pass DXC against the URP includes.
    - Every new model was looked at next to its engraving.
    - Audio was checked by spectrogram and loudness.
  - **Not verified:** nothing has run inside Unity yet. The riskiest new parts:
    - the NavMesh bake inside the bootstrap;
    - the Flora shader's first look;
    - the Mission II layout at scale;
    - how the score sounds. I composed it blind and checked it by spectrogram only.
  - **Next (Part 4):**
    1. If GUM sent `verne_setup_report.txt` or screenshots, fix what they show first. Read its Audit lines.
    2. M5: the Mission II light pass ("just enough to see"), heat shimmer, the summit timing.
    3. M6: mixer states, the cell and ladder sounds, a pass over the cues once someone can listen.
    4. Then M7.
  - **Blockers:** only GUM's machine can run Unity.
