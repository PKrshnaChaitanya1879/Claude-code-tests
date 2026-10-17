# Toolchain (cloud workspace)

Checked 2026-10-17 on Ubuntu 24.04 with Python 3.13, 2 CPUs and 7 GB RAM. Each run starts fresh, so re-install with `Source/tools/setup_toolchain.sh` (takes ~6–10 minutes, mostly the Unity download).

| Tool | How | Status |
|---|---|---|
| Blender | `pip install --break-system-packages bpy` → **bpy 5.2.2 LTS** | ✅ headless; FBX and glTF export tested |
| .NET SDK | `dotnet-install.sh --channel 8.0 --install-dir /opt/dotnet` → **8.0.426** (Roslyn csc) | ✅ |
| Unity 6 reference assemblies | Streamed `Unity-6000.0.85f1.tar.xz` (Linux editor, 4.5 GB) through `xz \| tar`, keeping only `Editor/Data/Managed`, `NetStandard`, `CGIncludes` and `Resources/PackageManager/BuiltInPackages` → `/opt/unityref` (~1.5 GB) | ✅ real UnityEngine/UnityEditor module DLLs, plus URP/Core RP **17.0.4** source |
| Registry packages | `https://download.packages.unity.com/<pkg>/-/<pkg>-<ver>.tgz` → `/opt/upkg`: mathematics 1.3.2, burst 1.8.20, collections 2.4.3, inputsystem 1.11.2, cinemachine 3.1.2, splines 2.6.1, settings-manager 2.0.1, timeline 1.8.7, ai.navigation 2.0.5 | ✅ |
| C# compile check | `Source/tools/unity_compile_check.py` compiles every asmdef in dependency order with Unity-like defines (editor pass, and `--player` pass without `UNITY_EDITOR`) | ✅ 39 package assemblies build, including URP Runtime, Core RP Runtime and Editor, Input System, Cinemachine runtime, Timeline, AI Navigation. ShaderGraph.Editor, URP.Editor and Cinemachine.Editor don't (they need com.unity.searcher and .NET Framework facades), so **our editor code must not use URP.Editor or Cinemachine.Editor APIs** |
| ffmpeg | preinstalled | ✅ |
| FluidSynth + soundfonts | `apt-get install fluidsynth` → FluidR3_GM.sf2, TimGM6mb.sf2 in `/usr/share/sounds/sf2` | ✅ |
| sox | apt | ✅ |
| pedalboard, soundfile, pyloudnorm, mido, numpy, scipy, pillow | pip | ✅ |
| Shader compile check | Not available: no Unity shader compiler and no DXC/FXC for Unity's include chain | ❌ Keep shaders conservative URP HLSL that includes only Core.hlsl, Lighting.hlsl, Shadows.hlsl and DeclareDepthTexture.hlsl, and mirror the patterns of URP's own shaders |
| Running Unity | Impossible: needs a licence login | ❌ The editor bootstrap builds everything on GUM's machine on first open |

GUM's own toolkit (creative-toolkit): this run had no `add_repo` tool to attach it, and it is outside the session's repository scope, so it wasn't used. Everything above is self-contained.
