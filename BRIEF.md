# Twenty Thousand Leagues Under the Sea: the Unity game

Owner: GUM. This brief is the source of truth for every scheduled build run. Read it all before working.

## 1. What GUM asked for (verbatim)

**First request (the vision):**

> I need the visuals like INSIDE by playdead, and the gameplay needs to be like iron lung, and I want the game to occur in submarine and can we have that 2 scenes from the book where he and the team goes out to that underwater forest and the colors vibrant and they venture into the deep side of the forest to see their underwater graveyard, then the another scene is when they go out in the night when its raining and they get to that mountain to see the light behind it, and then they climb it to see atlantis and it being illuminated by the underwater volcano. make the game like we have the submarine like how the book details it, and make it fully interactable, and the first chapter in the game has 2 missions where we get to do the above explorations. The game visuals need to be like INSIDE, like its a must, cause the 2 scenes are underwater, take inspo from that underwater chapter from INSIDE game, and the submarine needs to be interactable like iron lung game, and it need not be gritty but it should be as elegant as how captain nemo tells in his book, and the submarine needs to be fully detailed, and interactable like he interacts in the book. keeping visuals and lighting and color palate like INSIDE but game art style like Iron lung and ultrakill in the sense low poly, but not as low poly as roblox, render the models from blender, textures and color palate from internet, it needs I MEAN NEEDS to look like INSIDE. sound design needs to so good like as if you are in the sub, water needs to be heard like water. take real physics and depending upon depth do the needful, and in that scene where they go to the volcano and atlantis, make sure the only thing illuminating everything is the glow from volcano, but just enough to see not bright like a sun, and in the book its raining in the surface, but the characters are underwater so again, physics of water heard underwater. lighting should react like in inside, cause you can see the dust and other particles cause light to be like like not a 2d ray mesh. the submaine window, in the saloon should be like a 2d video playing, but like an actual window that we can see what is happening outside. Make sure it really looks like inside, and make it first person game, It should be adventure so movemnt should be like bioshock cause I am not superman, and please really take into account of book and its details, if you want refrence, take the illustrations from wikimedia on this book.

**Second request (move to Unity, scheduled):**

> make it a scheduled task and make the game in unity, take music inspiration from Bioshock and INSIDE make the music too, also here is the blog from developers from inside https://blog.playdead.com/articles/the_lighting_of_inside/lighting_of_inside.html
>
> adapt and enhance the lighting learning from the blog and animations, use blender to make models and animations and every model you do, refer to the illustrations and the book to get it as close as to the book as possible, and I mean for every creature, every detail of nautilus, make nautilus look like the nautilus from outside too, also make flora and fauna of the ocean look better, our aim is to make game do justice for the book, think of yourself as Jules Verne himself, how would he wanted to make book into game, water should look more real, it looks like subnautica now, but we want it like inside, can get better, and make ocean look like ocean, things look little bleak.
>
> Do the best you can, like squeeze every inch of work you can think of, lock in.
>
> Optimise the game when its done in unity, I dont want models to glitch through walls and etc, do justice to the game.
>
> it should be playable at least 30 fps, game should feel cinematic, but do not over do it.
>
> I love the loading screen idea to use original illustrations, keep that.

## 2. Hard constraints

- **Engine:** Unity 6 (6000.0 LTS line), Universal Render Pipeline (URP). She has only Unity, no Unreal.
- **Her laptop:** Windows 11, 1920×1080. AMD Ryzen 3 5300U (4 cores), integrated Radeon (Vega 6), ~15 GB RAM, often ~75% used at idle.
  - **Target:** at least 30 fps there. Use render scale ~0.7 with FSR upscaling, and quality tiers (Light / Balanced / Full).
  - **Budgets:** draw calls under ~500, one shadowed realtime light per area where possible, textures 1024 max (2048 only where it truly shows), and a lean memory footprint.
- **No clipping:**
  - Proper collision meshes (simplified `_col` meshes from Blender), CharacterController with a sensible skin width, camera collision so the view never enters walls, and held items or arms drawn so they never poke through geometry.
  - NPCs on NavMesh, with obstacles, so they never walk through props or the player.
- **Faithful to the book:** every model, creature and detail of the Nautilus, inside and out, should come from the text and the 1871 Hetzel engravings (Neuville and Riou) in `reference/illustrations/`.
  - The full Lewis Mercier translation is in `reference/book/`.
  - Think like Jules Verne adapting his own book into a game: wonder, precision, elegance, scientific curiosity.
- **Look:** INSIDE (Playdead), especially its underwater chapter. Dark, contrasty, silhouettes against luminous fog, volumetric light through particles (real ray-marched, not 2D ray meshes), and restrained colour with accents.
  - The forest and coral scenes must be **vibrant**. Colour comes alive where light reaches: near the surface, and inside the lamps' beams.
  - GUM's critiques of the prototype: water looked like Subnautica (uniform cyan haze), things looked bleak, and the ocean should look like the ocean.
- **Art style:** low-poly in the sense of Iron Lung and ULTRAKILL, faceted but never Roblox-crude. Models are built in Blender; textures and palette come from the internet (CC0 sources such as ambientCG and Poly Haven).
- **Gameplay:** first person.
  - **Movement:** like BioShock, weighty and human ("I am not superman"). Heavier and slower in the diving dress underwater.
  - **The submarine:** interactive like Iron Lung, with physical levers, valves, gauges and panels. Everything works the way the book describes.
- **The saloon window:** a real window onto the live exterior scene, not a video plane.
- **Sound:** you are inside the sub. Water must sound like water, through the hull and through the helmet. Depth physics: pressure, light absorption per wavelength, and sound filtering. The rain on the surface during the Atlantis excursion is heard as it would be from underwater.
- **Atlantis lighting:** the volcano's glow is the only light. Just enough to see, never sun-bright. Moonlight touches the city briefly at the end, as in the book.
- **Music:** original score inspired by BioShock (Garry Schyman's aleatoric strings, solo violin, 1940s–50s colour) and INSIDE (Martin Stig Andersen's sparse drones and processed textures). Never copy their melodies.
  - Captain Nemo plays the organ in the book. Pre-1929 public-domain works (e.g. Bach) may be performed; otherwise compose originals.
- **Cinematic, not overdone:** brief letterbox and slow camera moments only at the burial and the Atlantis reveal; control returns quickly.
- **Loading screens:** keep the original 1871 engravings as loading and chapter cards, with a book quote.
- **Privacy:** never put GUM's email or personal details in any file, commit, request header or URL. Commit as `Claude <noreply@anthropic.com>`.

## 3. Chapter One: two missions (the structure the prototype proved)

### Aboard (both missions start here)

1. Aronnax's cabin.
2. A note from Nemo, the book's own words for each excursion.
3. Walk through the Nautilus: library, saloon, corridors.
4. Robing-room, with the book's suit-up order: dress → Rouquayrol reservoir → Ruhmkorff lamp (Mission I) or iron-pointed stick (Mission II) → copper helmet.
5. The flooding cell, Iron Lung style:
   1. Close the inner door.
   2. Hold the tap; the pressure gauge rises to the outside pressure as the water rises and gurgles.
   3. Open the sea door.
6. Step out onto the sea bottom.

### Mission I · The forest, the coral kingdom and the cemetery

**Book references:** Part I ch. XV–XVII (the walk, the forest of Crespo Island) and ch. XXIII–XXIV (the coral kingdom).

1. Sunlit sea bottom with vibrant colour and caustics.
2. The submarine forest.
3. The darker coral gallery, where the Ruhmkorff lamps come on and colour blooms in their beams.
4. The deep coral tree forest.
5. The glade: cemetery and coral cross.
6. The burial:
   1. Bearers carry the body in white linen.
   2. A sailor digs with a pickaxe, which sparks on flint.
   3. The body is lowered.
   4. Everyone kneels (the player can kneel).
   5. A last adieu.
7. Return. End card quoting the book.

### Mission II · Atlantis

**Book reference:** Part II ch. IX.

1. Midnight. Nemo's invitation note. No lamps ("they will be useless").
2. Rain heard pattering on the surface far above.
3. The stony plain with phosphorescent pennatules.
4. The reddish light, two miles off.
5. The petrified forest: black branches against the glow.
6. Crevice jump. A dead trunk bridging a chasm.
7. Giant crustacean eyes in holes.
8. Ruins on the first platform.
9. The summit:
   1. The volcano 50 ft above the peak, raining stones and scoriae; lava cascades.
   2. Atlantis below: temples, acropolis, aqueduct, quay.
   3. Nemo writes ATLANTIS in chalk on black basalt.
   4. The moon gleams through the water.
10. End card.

## 4. What the browser prototype taught (reuse it)

`reference/web-prototype/` is a working Three.js version with everything above.

- **Live:** https://claude.ai/artifact/6w7predbjzVK7sC3teEVtg (GUM's private link).
- **Screenshots:** `reference/shots/`.

Port the ideas, not the code style:

- **Underwater light model (`src/uw.js`):**
  - Per-channel absorption σa and scattering σs.
  - Diffuse attenuation Kd with depth.
  - Light travelling to surfaces attenuated by exp(-σt·d).
  - Depth-dependent ambient, and a depth mapping that stretches descents.
  - The game uses this for physics-correct colour loss: red dies first.
- **Pipeline (`src/pipeline.js`):**
  - Ray-marched volumetric light at reduced resolution with blue-noise jitter, temporal accumulation (reprojection plus neighbourhood clamp), and shadow maps sampled per step.
  - Analytic fog composite, Snell's window and total internal reflection looking up, an "air box" so fog starts where rays leave the hull.
  - Marine snow lit by the same lights, bloom, an AgX-style grade, and dithering against banding.
- **Mission scripting:** `src/mission1.js`, `src/mission2.js` (routes, story beats along the path, the ceremony timeline, the summit sequence, respawn on falls with "Captain Nemo's strong hand hauled me back").
- **Audio design (`src/audio.js`):**
  - Hull hum and the screw; ventilation; the sea heard through the hull.
  - Helmet low-pass underwater, Rouquayrol breathing that varies with depth and exertion, Minnaert bubbles.
  - Airlock hiss and a gurgle that rises with the water; rain on the surface synthesised as bubble ringing.
- **Blender scripts:** `reference/blender/build_nautilus.py`, `build_props.py`, `blib.py` (bpy, headless).
  - They already build the full Nautilus interior and exterior to the book's layout: saloon, library, Nemo's room, Aronnax's room, corridors, wardrobe, flooding cell.
  - They also build the divers, corals, rocks, Atlantis ruins, fish and crustaceans.
  - Upgrade them rather than starting from zero. Exported GLBs are alongside.
- **Paintings in the saloon:** `reference/assets/paint/` (Met Open Access CC0; `met_source.json` has titles and artists that Verne names). Textures are in `reference/assets/tex/` (ambientCG CC0, 512 px; fetch higher resolution where it shows).

### What to do better than the prototype

- **Water:** INSIDE, not Subnautica.
  - Luminance and contrast falloff, not uniform cyan haze. Near-black shadows; silhouettes.
  - Warm lamps against cold water; local colour where light is.
  - God rays from the surface, plus caustics through a light cookie.
- **Colour:** vibrant reefs and forest near the surface and in the lamps. The book's colours: coral red, isis, sea-stars, medusae.
- **Exterior:** a real Nautilus exterior faithful to the book.
  - Cigar-shaped hull, 70 m long and 8 m in beam.
  - Plated hull, the platform, the pilot's cage with lenticular glasses, the lantern, the spur (ram), the screw, rudder and inclined planes.
  - The boat in its recess, and the saloon's panels and crystal windows.
- **Flora and fauna:** take every species the book names in those chapters and model the visible ones properly, with animation.
  - Fish schools, medusae, sea-stars, crustaceans, giant crabs and lobsters, the creatures Aronnax catalogues, sea-otter and turtles where the text has them.
- **Animation:** the divers (walk in heavy boots, kneel, dig, carry, lower, write in chalk, beckon), plus fish swim cycles, medusa pulsing and crab claws. Build them in Blender as FBX actions and drive them with Unity Animator.

## 5. INSIDE lighting notes

### From the Playdead blog GUM linked

- **Hand-placed light:** INSIDE's lighting is built from hand-placed effects. Bounce light, specular, rim, AO and cast-shadow **decals** are all placed by hand: "there is no global illumination or even automated AO at play here."
- **Torch shadows:** the shadows at the boy's feet are decals that track the torch, rotate around the feet and scale with the torch's height. Point-light shadows "would have been much too expensive."
- **Cookies:** added late; they give texture and the impression of richer shadowing.
- **Detail budget:** modelling and lighting detail are controlled by distance from the camera and by gameplay or narrative focus.
- **Painterly look:** the target was to match the concept art as closely as possible.

### From Playdead's GDC 2016 talk

The talk is "Low Complexity, High Fidelity: INSIDE Rendering" (Gjøl & Svendsen). Verify the details by searching.

- Ray-marched volumetric lights with dithered sampling and temporal filtering.
- Fog driven by gradients.
- Dithering everywhere against banding.
- HDR bloom.
- Carefully authored per-scene colour.

### Adapting it for this game

- Cheap, hand-authored lighting.
  - Decal AO, contact shadows and bounce cards around divers and props.
  - Cookies for caustics and the lamp beams.
  - Baked lighting in the Nautilus interior (Bakery is not available, so use Unity's progressive lightmapper, light probes and reflection probes).
- One quarter-resolution ray-marched volumetric pass (URP Renderer Feature) for the hero lights: the sun shafts, the Ruhmkorff lamps and the volcano. It uses blue noise and temporal accumulation.
- Give "Light" quality a fallback (fewer steps, or authored shaft cards with depth fade).

## 6. Delivery

- **Where it lives:** this repository, branch `twenty-thousand-leagues`.
  - The Unity project goes in `/Unity/TwentyThousandLeagues/` (Assets, Packages/manifest.json, ProjectSettings).
  - Generated sources (Blender scripts, music scores and render scripts) go in `/Source/`.
- **How GUM gets it:** she downloads the branch as a ZIP (or clones it) and opens `/Unity/TwentyThousandLeagues` with Unity 6 from Unity Hub.
  - A first-open editor bootstrap (menu **Verne → Build Everything**, also run automatically once) creates scenes, materials, URP assets, quality tiers and build settings from code.
  - It writes a report to `Unity/TwentyThousandLeagues/Logs/verne_setup_report.txt`.
- **Her guide:** `HOW_TO_OPEN.md` is a short, numbered guide for her. Keep it current.
- **If her computer is reachable:** if a run finds GUM's computer linked (device tools present and working) and she has connected a folder, it may also place the project there. Never require this.
