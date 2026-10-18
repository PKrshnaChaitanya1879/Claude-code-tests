# For GUM, Monday morning: what changed on Sunday evening (18 Oct, 18:45 to 21:30)

Everything below is already in your Fathom folder and in the repo. Open Fathom in Unity: it rebuilds itself
(about 3 minutes, "17 OK, 0 failed" in Logs/verne_setup_report.txt), then open Assets/Verne/Generated/Scenes/Title and press Play.

## How I worked this time
I built a capture tool (menu **Verne → Capture Tour**) that plays each scene on *your* laptop, walks the player to
fixed viewpoints and saves the real game frames in `Fathom/Logs/tour`. I tuned the lighting from those frames over
five rounds instead of guessing. Run it yourself any time to see the same shots.

## Your PDFs, point by point
| You said | What I did |
|---|---|
| Levers are boxes | Turned-brass lever with ebony knob in a slotted quadrant on a riveted brass board; ivory push-button switch on a brass rose. Spring-weighted movement. |
| Saloon window looks like an mp4 | No crossbars ("two crystal panes"); dark water with the saloon's light spilling out as a soft cone; fish schools now pass close to the glass. Open it with the panel lever. |
| Paintings pirated/low quality, bad ratio | Proper scans of all 21 from the Met's open archive (1024 px); close-up shows them at their true ratio in a gilt frame, centred in the left half. |
| Faceless sculpture, the "vase" | A real 3D-scanned marble bust (Poly Haven, CC0) on fluted ebony pedestals, facing into the room. |
| Papers glitching | Every sheet sits clear of the table and of the one under it. |
| Books | Gilt bands and tooled title panels on every spine, morocco/oxblood/olive/vellum bindings (note: Verne says "uniformly bound", so they stay a family of colours). |
| Dining room has no life | Rebuilt from I.X: open oak-and-ebony sideboards with china, porcelain and glass on show; table laid with silver, goblets, wine glasses, covered dishes, carafes; carved high-backed chairs. |
| "Where are the things Verne talks about" | The china was buried inside solid boxes before; it is visible now. |
| Kitchen | Rebuilt from I.XI: electric range with platina hobs, copper hood, the still with its glass condenser and water tank, a dresser of china, rail of copper pans, preserve jars, marble work table. |
| Washroom | Roll-top bath on brass feet, hot/cold taps with red/blue enamel, mahogany wash-stand with basin and ewer, looking-glass, towel rail, black-and-white tiled floor. |
| Robing room feels odd | The dresses now hang in an oak wardrobe with a panelled back, uprights and cornice. |
| Doors work on binary | A heavy leaf on hinges: inertia, friction and a soft knock against the stop. |
| Textures off; "you don't make textures" | All from the internet now, CC0: Poly Haven woods, leather, marble, plaster and the bust; ambientCG woven carpet; the Met paintings. Sources in reference/assets/textures_sources/SOURCES.txt. |
| 1860s, no LEDs, no pure white, no glossy | Every lamp and the luminous ceilings are filament-warm; the Ruhmkorff lamp is a warm white; brass, ebony, marble, china and silver are satin; the aboard grade is a hand-coloured engraving (umber shadows, ivory lights). |
| Lost Continent: blue things, trunk, lighting | Sea-pens dimmed to a faint glimmer; the trunk is a straight walk from ground to ground; the volcano and crags are black basalt rimmed red; the volcano light is turned down so it only just shows the way. |
| Fish through the submarine | They steer round the hull and glance off it. |
| Divers' feet | The walk cycle was a moonwalk (knees bent on the wrong stroke); fixed, ankles keep the lead soles flat. |
| A grey smear in the missions | It was the helmet's breath fog stuck at full strength (my bug). Now a faint mist on exhales. |

## Also done after the first draft of this report
- **Engine room**: the cog now turns by its teeth (40:16) and the machinery runs at a slow cruise you can see (Verne's 120 revolutions a second would only be a blur).
- **Mission I**: deeper contrast; the near forest goes to silhouette and the light shafts carry the image; the Ruhmkorff lamps reach further, so colour comes back where they land.
- **Mission II**: the faint fill light is now the volcano's ember (warm) instead of blue-grey.
- **Coral gallery and arches**: you can walk through now. The route check finds the way clear at 105 of 106 one-metre steps; the last one is a single plant to step around.
- **Ruhmkorff lamp**: a typo had left it at a fraction of its power. It now throws a warm-white pool that brings colour back where it lands (`Source/previews/tour/round6_mission1.jpg`).

## Honest list of what is still not right
- **The coral kingdom** still reads mostly as kelp; the reds and purples of Verne's coral need more coral and less forest in that stretch.
- **Mission II**: a faint grey haze in the middle of the dark at 150 fathoms; I haven't found its source yet.
- **Mission I**: much closer to INSIDE (depth falls into darkness) but still hazier than INSIDE's underwater chapter, and the coral colours under the lamp need another pass. Check the frame `Logs/tour/Mission1_m1_coral.png`.
- **Divers** are still simple low-poly figures; the gait is fixed but the bodies could be closer to the engravings.
- **Flora and Atlantis's petrified forest** were not touched this evening; the engine room only got the gear/speed fix.
- **Saloon ceiling**: the design is the same as the browser's; only the colour changed. Tell me what you'd like different.

Send me your bug list and I'll start there.
