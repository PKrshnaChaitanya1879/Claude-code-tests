#!/usr/bin/env bash
# Compile-check the Unity project's C# (editor pass, then player pass). Run setup_toolchain.sh first.
export PATH=/opt/dotnet:$PATH DOTNET_CLI_TELEMETRY_OPTOUT=1
B=/opt/unityref/Editor/Data/Resources/PackageManager/BuiltInPackages
U=/opt/upkg
HERE=$(cd "$(dirname "$0")" && pwd)
PROJ=$HERE/../../Unity/TwentyThousandLeagues/Assets
PKGS="--pkg $U/com.unity.mathematics --pkg $U/com.unity.burst --pkg $U/com.unity.collections --pkg $B/com.unity.ugui \
 --pkg $B/com.unity.rendering.light-transport --pkg $B/com.unity.render-pipelines.core --pkg $B/com.unity.shadergraph \
 --pkg $B/com.unity.render-pipelines.universal-config --pkg $B/com.unity.render-pipelines.universal --pkg $U/com.unity.inputsystem \
 --pkg $U/com.unity.settings-manager --pkg $U/com.unity.splines --pkg $U/com.unity.cinemachine --pkg $U/com.unity.timeline \
 --pkg $U/com.unity.ai.navigation"
echo "== editor pass"; python3 $HERE/unity_compile_check.py --unity /opt/unityref/Editor/Data $PKGS --project $PROJ --out /tmp/ucc_editor --reuse "$@" | grep -v "^OK" ; e=${PIPESTATUS[0]}
echo "== player pass"; python3 $HERE/unity_compile_check.py --unity /opt/unityref/Editor/Data $PKGS --project $PROJ --out /tmp/ucc_player --reuse --player "$@" | grep -v "^OK"; p=${PIPESTATUS[0]}
exit $((e|p))
