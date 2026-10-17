#!/usr/bin/env python3
"""Compile-check Unity C# outside the Unity editor.

Unity cannot run in the cloud workspace, so this script reproduces the part of Unity's
script compilation that matters for catching errors: it reads every .asmdef in the given
package roots, orders them by their references, and compiles each one with Roslyn (csc
from the .NET SDK) against the managed assemblies of a real Unity 6 editor install
(Editor/Data/Managed) and the C# packages the project uses (URP, core RP, Input System,
Cinemachine, ...), with Unity-like scripting defines.

Usage:
  python3 unity_compile_check.py --unity /opt/unityref/Editor/Data \
      --pkg /opt/unityref/Editor/Data/Resources/PackageManager/BuiltInPackages/com.unity.render-pipelines.core \
      --pkg ... --project Unity/TwentyThousandLeagues/Assets --out /tmp/ucc [--player]

--player compiles without UNITY_EDITOR and skips editor-only assemblies, the way a player
build does, which catches UnityEditor calls that leak into runtime code.

Assets/ scripts that are not under an .asmdef are compiled into Assembly-CSharp (and
Assembly-CSharp-Editor for files under an Editor/ folder), referencing every package
assembly that is not marked autoReferenced: false, exactly like Unity.
"""
import argparse, glob, json, os, re, subprocess, sys

UNITY_VERSION_DEFINES = [
    "UNITY_6000_0_OR_NEWER", "UNITY_6000_0", "UNITY_6000",
    "UNITY_2023_3_OR_NEWER", "UNITY_2023_2_OR_NEWER", "UNITY_2023_1_OR_NEWER",
    "UNITY_2022_3_OR_NEWER", "UNITY_2022_2_OR_NEWER", "UNITY_2022_1_OR_NEWER",
    "UNITY_2021_3_OR_NEWER", "UNITY_2021_2_OR_NEWER", "UNITY_2021_1_OR_NEWER",
    "UNITY_2020_3_OR_NEWER", "UNITY_2020_2_OR_NEWER", "UNITY_2020_1_OR_NEWER",
    "UNITY_2019_4_OR_NEWER", "UNITY_2019_3_OR_NEWER", "UNITY_2019_2_OR_NEWER", "UNITY_2019_1_OR_NEWER",
    "UNITY_2018_4_OR_NEWER", "UNITY_2018_3_OR_NEWER", "UNITY_2018_2_OR_NEWER", "UNITY_2018_1_OR_NEWER",
    "UNITY_2017_4_OR_NEWER", "UNITY_2017_3_OR_NEWER", "UNITY_2017_2_OR_NEWER", "UNITY_2017_1_OR_NEWER",
    "UNITY_5_6_OR_NEWER", "UNITY_5_5_OR_NEWER", "UNITY_5_4_OR_NEWER", "UNITY_5_3_OR_NEWER",
    "UNITY_STANDALONE_WIN", "UNITY_STANDALONE", "PLATFORM_STANDALONE_WIN", "PLATFORM_STANDALONE",
    "UNITY_64", "UNITY_INCLUDE_TESTS", "ENABLE_MONO", "NET_STANDARD_2_0", "NET_STANDARD_2_1", "NET_STANDARD",
    "NETSTANDARD2_1", "NETSTANDARD", "CSHARP_7_3_OR_NEWER", "CSHARP_7_OR_LATER",
    "ENABLE_INPUT_SYSTEM", "ENABLE_LEGACY_INPUT_MANAGER", "ENABLE_PHYSICS", "ENABLE_AUDIO",
    "ENABLE_UNITYWEBREQUEST", "ENABLE_CLOTH", "ENABLE_DIRECTOR", "ENABLE_PROFILER",
    "UNITY_ASSERTIONS", "ENABLE_UNITY_COLLECTIONS_CHECKS", "ENABLE_BURST_AOT",
]
EDITOR_DEFINES = ["UNITY_EDITOR", "UNITY_EDITOR_WIN", "UNITY_EDITOR_64", "DEBUG", "TRACE"]


ALIASES = {"Unity.ugui": ["UnityEngine.UI", "Unity.TextMeshPro"], "Unity.ugui.Editor": ["UnityEditor.UI", "Unity.TextMeshPro.Editor"]}


def load_asmdefs(roots):
    asms = {}
    for root in roots:
        for path in glob.glob(os.path.join(root, "**", "*.asmdef"), recursive=True):
            low = path.lower()
            if "~" in path or any(s in low for s in ("/tests/", "/test/", "testing", "codegen", "tests.asmdef", "burstcompatibilitygen")):
                continue
            try:
                d = json.load(open(path, encoding="utf-8-sig"))
            except Exception as e:
                print("bad asmdef", path, e); continue
            guid = None
            meta = path + ".meta"
            if os.path.exists(meta):
                m = re.search(r"guid:\s*([0-9a-f]+)", open(meta).read())
                guid = m.group(1) if m else None
            d["_path"] = path; d["_dir"] = os.path.dirname(path); d["_guid"] = guid
            d["_pkgroot"] = root
            asms[d["name"]] = d
    return asms


def package_versions(roots):
    vers = {"com.unity.modules.physics": "1.0.0", "com.unity.modules.animation": "1.0.0",
            "com.unity.modules.audio": "1.0.0", "com.unity.modules.ai": "1.0.0",
            "com.unity.modules.physics2d": "1.0.0", "com.unity.modules.terrain": "1.0.0",
            "com.unity.modules.imgui": "1.0.0", "com.unity.modules.jsonserialize": "1.0.0",
            "com.unity.modules.particlesystem": "1.0.0", "com.unity.modules.uielements": "1.0.0",
            "com.unity.modules.director": "1.0.0", "com.unity.modules.ui": "1.0.0",
            "com.unity.modules.unitywebrequest": "1.0.0", "com.unity.modules.video": "1.0.0",
            "com.unity.ugui": "2.0.0", "Unity": "6000.0.85"}
    for r in roots:
        pj = os.path.join(r, "package.json")
        if os.path.exists(pj):
            d = json.load(open(pj)); vers[d["name"]] = d["version"]
    return vers


def ver_tuple(v):
    return tuple(int(x) for x in re.findall(r"\d+", v.split("-")[0])[:3]) or (0,)


def expr_ok(expr, have):
    """Very small subset of Unity's version-define expressions: '1.2.3', '[1.0,2.0)', ''."""
    if not expr:
        return True
    expr = expr.strip()
    if expr[0] in "[(":
        lo, hi = expr[1:-1].split(",") if "," in expr else (expr[1:-1], expr[1:-1])
        h = ver_tuple(have)
        if lo.strip() and (h < ver_tuple(lo) or (expr[0] == "(" and h == ver_tuple(lo))):
            return False
        if hi.strip() and (h > ver_tuple(hi) or (expr[-1] == ")" and h == ver_tuple(hi))):
            return False
        return True
    return ver_tuple(have) >= ver_tuple(expr)


def sources_for(asm, all_dirs):
    own = asm["_dir"]
    files = []
    for f in glob.glob(os.path.join(own, "**", "*.cs"), recursive=True):
        d = os.path.dirname(f)
        # belongs to the nearest asmdef directory above it
        best = max((x for x in all_dirs if (d + "/").startswith(x + "/")), key=len, default=None)
        if best == own and "~" not in f[len(own):]:
            files.append(f)
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--unity", required=True)
    ap.add_argument("--pkg", action="append", default=[])
    ap.add_argument("--project", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--player", action="store_true")
    ap.add_argument("--reuse", action="store_true", help="reuse package DLLs already in --out")
    ap.add_argument("--csc", default=glob.glob("/opt/dotnet/sdk/*/Roslyn/bincore/csc.dll")[0])
    ap.add_argument("--only", default=None, help="regex of assembly names whose errors to print in full")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    managed = os.path.join(a.unity, "Managed")
    engine = sorted(glob.glob(os.path.join(managed, "UnityEngine", "UnityEngine*.dll")))
    editor_mods = sorted(glob.glob(os.path.join(managed, "UnityEngine", "UnityEditor*.dll")))
    base_refs = [os.path.join(a.unity, "NetStandard", "ref", "2.1.0", "netstandard.dll")]
    base_refs += sorted(glob.glob(os.path.join(a.unity, "NetStandard", "compat", "2.1.0", "shims", "netstandard", "*.dll")))
    base_refs += [p for p in engine if not p.endswith("UnityEngine.dll")]
    if not a.player:
        base_refs += editor_mods + [os.path.join(managed, "UnityEditor.Graphs.dll")]

    if not a.player:
        ALIASES["Unity.ugui"] = ALIASES["Unity.ugui"] + ["UnityEditor.UI"]
    roots = a.pkg[:]
    asms = load_asmdefs(roots)
    vers = package_versions(roots)
    # precompiled dlls shipped inside packages
    precompiled = {}
    for r in roots:
        for p in glob.glob(os.path.join(r, "**", "*.dll"), recursive=True):
            low = p.lower()
            if ".runtime" in low or "tests" in low or "~" in p:
                continue
            precompiled[os.path.basename(p)] = p

    project_asm = []
    if a.project:
        proj_asms = load_asmdefs([a.project])
        asms.update(proj_asms)
        project_asm = list(proj_asms)

    by_guid = {d["_guid"]: n for n, d in asms.items() if d["_guid"]}
    all_dirs = [d["_dir"] for d in asms.values()]

    def is_editor(d):
        inc = d.get("includePlatforms") or []
        return inc == ["Editor"]

    def wanted(d):
        if a.player and is_editor(d):
            return False
        excl = d.get("excludePlatforms") or []
        if "Editor" in excl and not a.player:
            return False
        return True

    defines_base = UNITY_VERSION_DEFINES + ([] if a.player else EDITOR_DEFINES)

    def refs_of(d):
        out = []
        for r in d.get("references", []):
            n = by_guid.get(r[5:]) if r.startswith("GUID:") else ALIASES.get(r, r)
            for x in (n if isinstance(n, list) else [n]):
                if x and x in asms:
                    out.append(x)
        # In Unity 6 the ugui package is a core package that every assembly can see.
        if not d["_pkgroot"].endswith("com.unity.ugui"):
            for m in ("UnityEngine.UI", "Unity.TextMeshPro") + (() if a.player else ("UnityEditor.UI",)):
                if m in asms and m not in out:
                    out.append(m)
        # Unity 6 compiles the ugui package (UGUI + TextMeshPro) together: siblings see each other.
        if d["_pkgroot"].endswith("com.unity.ugui"):
            for m, e in asms.items():
                if m != d["name"] and e["_pkgroot"] == d["_pkgroot"] and m in ("UnityEngine.UI",) + (("UnityEditor.UI",) if "Editor" in d["name"] else ()):
                    out.append(m)
        return out

    order, state = [], {}
    def visit(n):
        if state.get(n) == 2: return
        if state.get(n) == 1: return
        state[n] = 1
        for r in refs_of(asms[n]): visit(r)
        state[n] = 2; order.append(n)
    for n in asms: visit(n)

    built = {}
    failed = {}
    for n in order:
        d = asms[n]
        if not wanted(d):
            continue
        defines = list(defines_base)
        for vd in d.get("versionDefines", []):
            have = vers.get(vd["name"])
            if have and expr_ok(vd.get("expression", ""), have):
                defines.append(vd["define"])
        cons = d.get("defineConstraints") or []
        ok = True
        for c in cons:
            neg = c.startswith("!")
            sym = c.lstrip("!")
            present = sym in defines
            if neg == present:
                ok = False
        if not ok:
            continue
        srcs = sources_for(d, all_dirs)
        if not srcs:
            continue
        refs = list(base_refs)
        missing = []
        for r in refs_of(d):
            if r in built: refs.append(built[r])
            elif r in failed: missing.append(r)
        if d.get("overrideReferences"):
            for p in d.get("precompiledReferences", []):
                if p in precompiled: refs.append(precompiled[p])
        else:
            refs += list(precompiled.values())
        if missing:
            failed[n] = "dependency failed: " + ", ".join(missing)
            print(f"SKIP {n}: {failed[n]}")
            continue
        outdll = os.path.join(a.out, n + ".dll")
        if a.reuse and n not in project_asm and os.path.exists(outdll):
            built[n] = outdll
            continue
        rsp = os.path.join(a.out, n + ".rsp")
        with open(rsp, "w") as f:
            f.write("-target:library\n-nologo\n-nostdlib+\n-langversion:9.0\n-nowarn:0618,0649,0414,0169,0219,1701,1702,0067,0108,0162,0168,0612,0672,0809,1591,1573,8632,8618\n")
            f.write(f"-out:{outdll}\n")
            if d.get("allowUnsafeCode"): f.write("-unsafe\n")
            f.write("-define:" + ";".join(defines) + "\n")
            # csc.rsp in the asmdef folder (Unity honours it)
            crsp = os.path.join(d["_dir"], "csc.rsp")
            if os.path.exists(crsp):
                for line in open(crsp):
                    line = line.strip()
                    if line.startswith("-define:") or line.startswith("-nowarn:"):
                        f.write(line + "\n")
            for r in dict.fromkeys(refs):
                f.write(f'-reference:"{r}"\n')
            for s in srcs:
                f.write(f'"{s}"\n')
        res = subprocess.run(["dotnet", a.csc, "@" + rsp], capture_output=True, text=True)
        errs = [l for l in res.stdout.splitlines() if ": error " in l]
        if res.returncode == 0:
            built[n] = outdll
            print(f"OK   {n} ({len(srcs)} files)")
        else:
            failed[n] = f"{len(errs)} errors"
            print(f"FAIL {n}: {len(errs)} errors")
            show = errs if (a.only and re.search(a.only, n)) else errs[:8]
            for e in show: print("     " + e[-400:])
    print(f"\nbuilt {len(built)}, failed {len(failed)}")
    if a.project:
        bad = [n for n in project_asm if n in failed]
        print("PROJECT:", "FAILED " + ", ".join(bad) if bad else "all project assemblies compiled")
        sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
