# GUM's review of the first Unity build (Sun 18 Oct 2026, 15:07 IST)

Source: `reference/feedback/2026-10-18_GUM_review_of_unity_build.pdf` (11 pages: her screenshots of our build, INSIDE stills, and Marek Bogdan's "The Lighting of INSIDE"). **Read the PDF pages yourself before working; look at the images.** This file outranks everything in PLAN.md and PROGRESS.md until every item below is fixed and verified.

## Her words (verbatim, condensed only where repeated)
- "In browser you made game look visually much better, did I not tell you to make it like INSIDE." "Look at how underwater light looks like, you made it like Subnautica. You got the ambiance of the Lost Continent right but really messed up the Unity version."
- "There are so many bugs, fishes are glitching through the submarine, and the doors and rooms look nothing like how Jules Verne describes it… the details are terrible, it's like Roblox, where are the intense tiny details. In the browser one you could see what individual painting used to tell, now you can't, and the submarine interior looks like cubes stuck together."
- "The water physics and lighting looks bad too, nothing like INSIDE, and the flora and fauna at sea bed looks as if a kid drew something. The Lost Continent was a nightmare to look at, the lighting looks so bad, and what are those trees, they look like land trees."
- "The door ways get blocked by some models and the panels and light levers are out of place. In the browser you had proper animation and fade in light and fade out, because it's incandescent not freaking LED."
- "What was that engine room, the RPM or crank and gear were so off. Everything is too smooth. When you are looking at the painting make it so that we can see the painting next to our message when you see its details, so we can see the painting better, same with artifacts."
- "REFER TO THE BOOK FOR EVERY MODEL AND DETAIL, it should be as if you are playing the book, not an adaptation." "Redesign everything, every detail, kitchen, bathroom and everything should be 1:1 to the book."
- "Animations need to get better, feet are reversed and more." "Optimise the game and make the visuals more cinematic and get the details on point this time." "It should be the book as the game, not a fan parody."
- Also (11:17): "I don't think it will run in Unity, too much load for my laptop. Export the game as .exe."

## What this means, as a checklist (tick only after verifying with a render/screenshot next to the reference)
### F1 · Look: INSIDE, not Subnautica (top priority)
- [ ] Grade: cold desaturated teal-grey to near-black; no warm brown haze (her Mission I/II shots are brown-orange fog). Darkness is the default; light is the event.
- [ ] Light model per the PDF stills: one strong cone (diver lamp / Nautilus lantern) with visible volumetric beam and hard falloff; faint top-down shaft from the surface; everything else silhouette. Fog density rises with distance into black, not into beige.
- [ ] Hand-placed decal layers à la Bogdan: bounce, rim, AO, shadow decals that follow the lamp (already have LampShadow/LampBounce: make them visible and correct), light cookies on walls.
- [ ] Water: surface seen from below, caustics only near shallow depth; particles (marine snow) lit only inside the cone.
- [ ] Compare every scene against the PDF INSIDE stills and the browser prototype (`reference/web-prototype`), which she says looked much better. Port its look, not invent a new one.
### F2 · Bugs
- [ ] Fish pass through the Nautilus hull: fish schools must avoid the hull (sphere/capsule avoidance against Hull layer colliders) and the window view.
- [ ] Doorways blocked by models (RouteAudit already flags: Mission I blocked near (0,95)–(-2,101); Mission II 98/163 clear, blocked (0,38)–(0,43)). Every doorway in the Nautilus clear and walkable.
- [ ] Panels and light levers out of place: re-seat on their walls.
- [ ] Lights fade like incandescent filament (warm-up ~0.3–0.6 s with slight overshoot/flicker, cool-down glow), as in the browser prototype. No instant LED switching.
- [ ] Diver animation: feet reversed. Fix the rig/forward axis; heavy, slow, weighted walk in lead-soled boots (book: Rouquayrol apparatus, Ruhmkorff lamp, heavy boots).
### F3 · Faithfulness to the book (every model)
- [ ] Nautilus interior room-by-room from Part One ch. 10–13 (dining room, library, saloon/museum, Nemo's room, Aronnax's room, engine room, galley/kitchen, bathroom, crew quarters, robing room), with the book's furniture, materials and dimensions. No box rooms. Real mouldings, panelling, rivets, brass, glass cases, the organ, the fountain/tridacna, the cases of shells and pearls.
- [ ] Engine room per ch. 12–13: Bunsen elements, Ruhmkorff coils, the great electro-magnets, the cranks/connecting rods and the screw shaft at the correct ~120 rpm visual rate; gear ratios that look mechanically plausible.
- [ ] Paintings and artifacts: on inspect, show the painting/artifact image large beside the caption text (split view), legible.
- [ ] Flora/fauna of the seabed per ch. 16–17 and 22–24 (Crespo forest: plants rising vertically, no flexibility, coloured stems, "the animals flowered and the plants did not"; coral kingdom). Replace the kid-drawn look.
- [ ] Atlantis (Part Two ch. 9): petrified trees, mineralised, black, leafless, NOT land trees; ruins, the volcano glow as the only light.
- [ ] Divers: real 1860s diving dress silhouettes (copper helmet with grilles, Rouquayrol tank on the back, Ruhmkorff lamp at the belt), not box bodies.
### F4 · Ship it to her laptop
- [ ] Windows .exe build she can run without opening the Unity editor (Ryzen 3 5300U, integrated Radeon). Use `Verne → Build Windows Game` or `Build_Game.bat` (batch mode, editor closed). Default quality: Light.
- [ ] 30 fps on Light at 1080p×0.7 with FSR.
