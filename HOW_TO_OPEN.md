# How to open the game

The Unity project builds itself the first time you open it. The **Nautilus is modelled inside and out** (Blender, at the book's dimensions); the two excursions are still greybox ground with the **first version of the underwater look**. Creatures, divers, the excursions' art and the music arrive milestone by milestone (see `PROGRESS.md`).

If you opened an earlier download, open this one fresh: the build re-runs by itself once (or use **Verne → Build Everything**).

1. **Download.** Get the branch as a ZIP: https://github.com/PKrshnaChaitanya1879/claude-code-tests/archive/refs/heads/twenty-thousand-leagues.zip
2. **Unzip.** Unzip it somewhere with a short path, e.g. `C:\Games\TwentyThousandLeagues`. Long paths break Unity.
3. **Add the project.** In Unity Hub, choose **Add → Add project from disk** and pick the `Unity\TwentyThousandLeagues` folder inside it.
   - The project asks for **Unity 6000.0.85f1**. If you have another **Unity 6 (6000.0.x)**, choose it when Hub asks.
   - Don't use Unity 6.1 or later; stay on 6000.0 LTS.
4. **First open.**
   - Unity imports the packages, then builds everything automatically. It takes a few minutes, and the Console shows `[Verne] Build Everything: … OK`.
   - If it doesn't run, use the menu **Verne → Build Everything**. It is safe to run again any time.
   - The result is written to `Logs/verne_setup_report.txt` (also under **Verne → Open Setup Report**). If anything says FAIL, send that file and it gets fixed next run.
5. **Play.** Open `Assets/Verne/Generated/Scenes/Title.unity` and press **Play**.

## Controls

| Action | Keyboard and mouse | Controller |
|---|---|---|
| Walk | WASD | Left stick |
| Walk faster | Shift | Left stick click |
| Look | Mouse | Right stick |
| Use, or hold to operate | E or left click | A |
| Crouch | C or Ctrl | B |
| Kneel | K | Y |
| Small hop | Space | X |
| Ruhmkorff lamp (first excursion) | L | Right shoulder |
| Pause and settings | Esc | Start |

- **Levers and wheels:** hold E on one, then move the mouse up or down to throw a lever. Hold E on a wheel to turn it.

## What to try now

1. In **Aronnax's cabin**, read Captain Nemo's note on the writing-table.
2. **Nemo's room:** look at the instrument wall (E to read what Nemo says of it). The 24-hour electric clock keeps your own time.
3. **The saloon:**
   - Play Nemo's **organ** (E at the keyboard): Bach's Toccata in D minor.
   - Press the small **ceiling switch** on the brass plate by the library door, then **throw the lever** beside it: the luminous ceiling goes dark and the iron panels slide off the crystal windows onto the live sea, fish and medusae drifting past in the Nautilus' light. That's the book's order (I.XIV).
   - Sixteen canvases by the masters Verne names (Met open-access scans) hang on the walls; the pearls and shells in the cases can be examined.
4. **Library:** twelve thousand volumes, and a cigar from the bronze brazier.
5. **Aft**, down the port corridor: Ned and Conseil's cabin (Ned's harpoon), the kitchen with its still, the bath-room, then the **robing-room**.
6. **Dress** at the bench, one piece at a time in the book's order. Each piece leaves the bench; once the helmet is on you see through its glass port, and your breath fogs it.
7. Through the small door beside the cell: the **engine-room**, after the 1871 engraving, with Bunsen's piles and the great wheel turning on the screw's axle.
8. **The flooding cell** (Iron Lung style, everything by hand):
   1. Close the inner door, then **turn the stopper-plate wheel** on it until the plates are home.
   2. Hold the sea tap: hiss, the cold rising, the gauge climbing to the outside pressure.
   3. When the cell is full, open the outer door and step out onto the sea floor.
9. After the first excursion, the Nautilus prepares the second: midnight, no lamps, an iron-pointed stick, and the door opens 150 fathoms down.
10. The title menu can also jump straight to either excursion.

**Settings:** Esc → Settings has quality (Light / Balanced / Full), 30/60 fps cap, field of view, sensitivity, invert look, head movement, subtitles and volumes. On your laptop the game starts on **Light** automatically.
