# Working protocol for build runs on this branch

This branch (`twenty-thousand-leagues`) is built by scheduled runs that each start fresh. Follow this protocol every run.

1. **Lock.**
   - If `.verne/LOCK` exists and its timestamp is less than 5 hours old, another run is working. Write nothing, report that in one line, and stop.
   - Otherwise write `.verne/LOCK` with the current UTC time, commit and push it before doing anything else.
2. **Read.** Read `BRIEF.md` (the vision and constraints) and `PROGRESS.md` (the checklist and the log). Continue from the first unticked item, or from what the last log entry names as next.
3. **Work in order:** M0 → M9.
   - Don't skip ahead to polish while a foundation is missing.
   - Within a milestone, finish and verify one piece before the next.
4. **Commit and push.**
   - Commit and push at least every 45 minutes, with small, descriptive commits.
   - `git fetch origin twenty-thousand-leagues` and rebase before each push.
   - Commit as `Claude <noreply@anthropic.com>`. Never put GUM's email or personal details in any file, commit, header or URL.
   - Keep every file under 50 MB: OGG for audio, JPG/PNG at 1024 px or less unless it truly shows.
5. **Verify before ticking.**
   - **C#:** compiles against the Unity reference assemblies when available.
   - **Blender models:** render a preview next to the reference engraving into `Source/previews/` and look at it.
   - **Music:** check loudness and listen-check via spectrogram images.
   - **Scenes:** the bootstrap must create the objects without missing references.
6. **Finish.**
   - Append a dated entry to the `PROGRESS.md` log: what was done, what was verified, what is next, and any blocker.
   - Delete `.verne/LOCK`, commit, push.
   - Then give GUM a short, warm report: what changed, what she can try, and the download link `https://github.com/PKrshnaChaitanya1879/claude-code-tests/archive/refs/heads/twenty-thousand-leagues.zip`.
7. **Stop when done.** When every milestone is ticked, run a final review against `BRIEF.md`. If the scheduling tools are available, disable this scheduled task (`update_trigger` / `delete_trigger` on the task named "Twenty Thousand Leagues — Unity build"). Otherwise tell GUM she can turn it off.

## Skills to load when relevant

- `anthropic-skills:model-3d-finish`: Blender work.
- `anthropic-skills:creative-toolkit`: GUM's toolkit repo `PKrshnaChaitanya1879/creative-toolkit`, with tested Blender, audio and render code.
- `anthropic-skills:game-finish`: Unity finishing and her laptop budget. GUM explicitly asked for INSIDE-style ray-marched volumetrics here, so build them cheaply (quarter res, few steps, temporal), with a fallback on "Light" quality, rather than skipping them.
- `anthropic-skills:premium-design`: menus and cards.
