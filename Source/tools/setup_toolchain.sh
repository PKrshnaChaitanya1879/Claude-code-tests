#!/usr/bin/env bash
# Re-creates the cloud toolchain described in Source/TOOLCHAIN.md. Safe to re-run.
set -e
pip install -q --break-system-packages bpy soundfile pyloudnorm mido pedalboard || true
if [ ! -x /opt/dotnet/dotnet ]; then
  curl -sSL https://dot.net/v1/dotnet-install.sh -o /tmp/dotnet-install.sh
  bash /tmp/dotnet-install.sh --channel 8.0 --install-dir /opt/dotnet >/dev/null
fi
if [ ! -d /opt/unityref/Editor/Data/Managed ]; then
  mkdir -p /opt/unityref && cd /opt/unityref
  curl -sS https://download.unity3d.com/download_unity/ee7790f1426a/LinuxEditorInstaller/Unity-6000.0.85f1.tar.xz | xz -dc | \
    tar -x --wildcards 'Editor/Data/Managed/*' 'Editor/Data/NetStandard/ref/*' 'Editor/Data/NetStandard/compat/*' \
      'Editor/Data/Resources/PackageManager/BuiltInPackages/*' 'Editor/Data/CGIncludes/*'
  rm -rf Editor/Data/Resources/PackageManager/BuiltInPackages/com.unity.render-pipelines.high-definition*
fi
mkdir -p /opt/upkg && cd /opt/upkg
for pv in com.unity.mathematics@1.3.2 com.unity.burst@1.8.20 com.unity.collections@2.4.3 com.unity.inputsystem@1.11.2 \
          com.unity.cinemachine@3.1.2 com.unity.splines@2.6.1 com.unity.settings-manager@2.0.1 com.unity.timeline@1.8.7 \
          com.unity.ai.navigation@2.0.5; do
  p=${pv%@*}; v=${pv#*@}
  [ -f $p/package.json ] || { mkdir -p $p; curl -sSL "https://download.packages.unity.com/$p/-/$p-$v.tgz" | tar -xz -C $p --strip-components=1; }
done
(apt-get update -q && apt-get install -y -q fluidsynth sox) >/dev/null 2>&1 || true
echo "toolchain ready"
