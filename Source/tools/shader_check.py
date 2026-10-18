"""Compile-check our URP .shader passes with Microsoft DXC against Unity's real URP/Core RP HLSL includes.
Not Unity's compiler, but it catches syntax, type and missing-symbol errors per pass and keyword variant.
Usage: python3 shader_check.py <file.shader> [...]   (needs /opt/dxc and /opt/unityref, see TOOLCHAIN.md)"""
import os, re, subprocess, sys, itertools, tempfile
B = '/opt/unityref/Editor/Data/Resources/PackageManager/BuiltInPackages'
INC = '/tmp/verne_shinc'
os.makedirs(INC + '/Packages', exist_ok=True)
for p in ('com.unity.render-pipelines.core', 'com.unity.render-pipelines.universal', 'com.unity.render-pipelines.universal-config'):
    dst = f'{INC}/Packages/{p}'
    if not os.path.exists(dst): os.symlink(f'{B}/{p}', dst)
DXC = '/opt/dxc/bin/dxc'
BASE = ['-HV', '2018', '-Wno-ignored-attributes', '-Wno-unknown-pragmas', '-D', 'SHADER_API_D3D11=1', '-D', 'UNITY_VERSION=6000',
        '-D', 'SHADER_TARGET=45', '-D', 'UNITY_COMPILER_DXC=1', '-I', INC, '-Wno-conversion', '-Wno-parentheses-equality']

def blocks(src):
    inc = ''.join(re.findall(r'HLSLINCLUDE(.*?)ENDHLSL', src, re.S))
    for m in re.finditer(r'HLSLPROGRAM(.*?)ENDHLSL', src, re.S):
        yield inc + '\n' + m.group(1), m.group(1)

def variants(prog):
    sets = []
    for line in prog.splitlines():
        line = line.strip()
        if line.startswith('#pragma multi_compile') and 'instancing' not in line and 'fog' not in line:
            kws = line.split()[2:]
            sets.append([k for k in kws if k != '_'] + [None])
        # INSTANCING_ON is not checked: outside Unity's compiler the instancing macros don't expand
        # (a minimal URP-style instanced shader fails the same way), so only the plain variant is compiled.
    if not sets: return [[]]
    n = 1
    for st in sets: n *= len(st)
    if n <= 64: return [list(filter(None, c)) for c in itertools.product(*sets)]
    # too many to compile all (URP lit-style shaders): every keyword alone, plus the "all first" and "all last" combinations
    out = [[]] + [[k] for st in sets for k in st if k]
    out.append([st[0] for st in sets if st[0]])
    out.append([[k for k in st if k][-1] for st in sets if any(st)])
    return out

ok = True
for path in sys.argv[1:]:
    src = open(path).read()
    for bi, (code, prog) in enumerate(blocks(src)):
        vs = re.search(r'#pragma\s+vertex\s+(\w+)', prog).group(1)
        fs = re.search(r'#pragma\s+fragment\s+(\w+)', prog).group(1)
        with tempfile.NamedTemporaryFile('w', suffix='.hlsl', delete=False) as f:
            f.write(code); tmp = f.name
        for kw in variants(prog):
            for stage, entry, prof, sdef in (('vs', vs, 'vs_6_0', 'SHADER_STAGE_VERTEX'), ('ps', fs, 'ps_6_0', 'SHADER_STAGE_FRAGMENT')):
                args = [DXC, '-E', entry, '-T', prof, *BASE, '-D', sdef + '=1'] + sum([['-D', k + '=1'] for k in kw], []) + [tmp]
                r = subprocess.run(args, capture_output=True, text=True)
                errs = [l for l in r.stderr.splitlines() if 'error' in l]
                tag = f'{os.path.basename(path)} pass {bi} {stage} {entry} {"+".join(kw) or "-"}'
                if r.returncode != 0:
                    ok = False
                    print('FAIL', tag); print('\n'.join(errs[:12]) or r.stderr[:2000])
                else:
                    print('OK  ', tag)
sys.exit(0 if ok else 1)
