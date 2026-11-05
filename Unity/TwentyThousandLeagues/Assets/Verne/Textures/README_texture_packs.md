# Fathom texture packs (5 Nov 2026)

Real CC0 scans only, never procedurally generated (GUM's rule). Each pack has `<Pack>_albedo.jpg`, `<Pack>_normal.jpg` (OpenGL / Y+ convention, as Unity expects) and `<Pack>_rough.jpg` (metal packs also `_metal.jpg`).

**On import** (`Verne → Build Everything`, `TexturePacks.cs`): albedo sRGB, BC7; normal as Normal map, BC5; roughness and metalness linear, BC4; mipmaps on, trilinear, anisotropic 4. Max size 1024 (SeabedSand 2048, it fills half of every frame). About 2.7 MB of VRAM per 1K pack, 41 MB for all fourteen.

| Pack | Source | Asset | Author(s) | Licence | Size | Used for |
|---|---|---|---|---|---|---|
| SeabedSand | Poly Haven | [Coast Sand 01](https://polyhaven.com/a/coast_sand_01) | Rob Tuytel | CC0 1.0 | 2048² | Crespo sand plain: fine, even sand, "not wrinkled" (I.XV) |
| SandRipples | Poly Haven | [Damp Beach Sand](https://polyhaven.com/a/damp_beach_sand) | Dimitrios Savva | CC0 1.0 | 1024² | faint current ripples: forest edge, coral approach, Atlantis plain |
| Silt | Poly Haven | [Brown Mud 02](https://polyhaven.com/a/brown_mud_02) | Rob Tuytel | CC0 1.0 | 1024² | soft silt in hollows and under the forest |
| Gravel | Poly Haven | [Coral Gravel](https://polyhaven.com/a/coral_gravel) | Rob Tuytel | CC0 1.0 | 1024² | coral and shell gravel round the coral kingdom |
| Pebbles | Poly Haven | [River Small Rocks](https://polyhaven.com/a/river_small_rocks) | Rob Tuytel, Rico Cilliers | CC0 1.0 | 1024² | pebble beds between the rocks |
| Shells | Poly Haven | [Shell Floor 01](https://polyhaven.com/a/shell_floor_01) | Rob Tuytel | CC0 1.0 | 1024² | "the impalpable dust of shells" (I.XV) |
| Basalt | Poly Haven | [Dark Rock 02](https://polyhaven.com/a/dark_rock_02) | Amal Kumar | CC0 1.0 | 1024² | Atlantis basalt, the black rock of the chalk scene |
| LavaRock | ambientCG | [Rock048](https://ambientcg.com/view?id=Rock048) | ambientCG (Lennart Demes) | CC0 1.0 | 1024² | cooled, rough lava rock and scoria on the volcano |
| Lava | ambientCG | [Lava003](https://ambientcg.com/view?id=Lava003) | ambientCG (Lennart Demes) | CC0 1.0 | 1024² | glowing seams and flows (emission from the albedo) |
| Coral | Poly Haven | [Coral Ground 02](https://polyhaven.com/a/coral_ground_02) | Rob Tuytel | CC0 1.0 | 1024² | coral rock: the coral kingdom floor and coral encrustation |
| EncrustedRuins | Poly Haven | [Mossy Stone Wall](https://polyhaven.com/a/mossy_stone_wall) | Amal Kumar | CC0 1.0 | 1024² | Atlantis masonry under weed and zoophytes |
| RustedMetal | Poly Haven | [Rusty Metal 02](https://polyhaven.com/a/rusty_metal_02) | Rob Tuytel | CC0 1.0 | 1024² | iron of the Nautilus outside, anchors and fittings |
| Brass | ambientCG | [Metal048C](https://ambientcg.com/view?id=Metal048C) | ambientCG (Lennart Demes) | CC0 1.0 | 1024² | aged brass (impure, rough): fittings, the diving dress |
| Copper | ambientCG | [Metal058C](https://ambientcg.com/view?id=Metal058C) | ambientCG (Lennart Demes) | CC0 1.0 | 1024² | oxidised copper with verdigris: the diving bonnet after the sea |

Licence: CC0 1.0 Universal (public domain dedication) for every asset above: https://creativecommons.org/publicdomain/zero/1.0/ — Poly Haven: https://polyhaven.com/license — ambientCG: https://docs.ambientcg.com/license/

Paintings in `Textures/Paint` come from the Metropolitan Museum of Art Open Access collection (CC0), as before.
