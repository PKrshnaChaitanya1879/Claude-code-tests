# How to open the game

The Unity project builds itself the first time you open it. It is early: the Nautilus and the two excursions are walkable **greybox** at the book's true dimensions, with working controls. The real models, the underwater look and the music arrive milestone by milestone (see `PROGRESS.md`).

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
| Pause and settings | Esc | Start |

- **Levers and wheels:** hold E on one, then move the mouse up or down to throw a lever. Hold E on a wheel to turn it.

## What to try now

1. In **Aronnax's cabin**, read Captain Nemo's note on the dressing-table.
2. Walk aft:
   - Nemo's room has the instrument wall.
   - In the **saloon**, throw the brass lever by the port divan and the iron panels slide off the crystal windows.
   - Then go through the library, the dining room and the central staircase.
3. Go down the port corridor to the **robing room** and put on the diving dress (four steps, in the book's order). You will feel the lead soles.
4. In the **flooding cell**:
   1. Close the inner door.
   2. Hold the sea tap: hear it hiss and watch the gauge climb to the outside pressure.
   3. When the cell is full, open the outer door and step out onto the sea floor.
5. The title menu can also jump straight to either excursion.

**Settings:** Esc → Settings has quality (Light / Balanced / Full), 30/60 fps cap, field of view, sensitivity, invert look, head movement, subtitles and volumes. On your laptop the game starts on **Light** automatically.
