"""Pattern tiles for the Nautilus' soft furnishings, after plate im022 (patterned carpet, carved ceiling):
- carpet_c.jpg: an all-over Persian lattice (lozenges with rosettes, a deep red ground, indigo and gold),
  multiplied with the CC0 carpet weave so it keeps its fibre; repeats every metre.
- ceiling_c.jpg: the luminous ceiling's glass in a gilt arabesque lattice (quatrefoils), used as both the base
  and the emission map, so the light comes through the pattern. Repeats every metre.
Run from the repo root; overwrites the two textures in Unity/.../Textures (the CC0 originals are kept as carpet0_c.jpg and ceiling0_c.jpg)."""
import numpy as np, os, shutil
from PIL import Image, ImageFilter
T = 'Unity/TwentyThousandLeagues/Assets/Verne/Textures'
N = 512
y, x = (np.mgrid[0:N, 0:N] + 0.5) / N
def keep(name):
    src, dst = f'{T}/{name}.jpg', f'{T}/{name[:-2]}0_c.jpg'     # the CC0 originals are kept as carpet0_c.jpg / ceiling0_c.jpg
    if not os.path.exists(dst): shutil.copy(src, dst)
    return np.asarray(Image.open(dst).convert('RGB')).astype(float) / 255
# ---- carpet: diagonal lattice of lozenges, rosettes at the centres and corners
weave = keep('carpet_c')
lum = weave.mean(2, keepdims=True); lum = 0.75 + 0.5 * (lum - lum.mean())
u, v = (x + y), (x - y)                       # 45° lattice
fu, fv = np.abs((u * 2) % 1 - 0.5), np.abs((v * 2) % 1 - 0.5)
lozenge = np.minimum(fu, fv)
red = np.array([0.42, 0.06, 0.05]); indigo = np.array([0.07, 0.08, 0.2]); gold = np.array([0.62, 0.45, 0.16]); ivory = np.array([0.75, 0.68, 0.52])
col = np.broadcast_to(red, (N, N, 3)).copy()
col[lozenge < 0.035] = indigo                                   # the lattice lines
col[(lozenge > 0.035) & (lozenge < 0.05)] = gold
for (cx, cy) in ((0.5, 0.5), (0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (1.0, 1.0)):
    dx, dy = x - cx, y - cy
    r = np.hypot(dx, dy); a = np.arctan2(dy, dx)
    petal = r < 0.07 + 0.03 * np.cos(8 * a)
    col[petal] = ivory
    col[r < 0.035] = gold
    col[(r < 0.018)] = indigo
for (cx, cy) in ((0.5, 0.0), (0.0, 0.5), (1.0, 0.5), (0.5, 1.0)):
    r = np.hypot(x - cx, y - cy); a = np.arctan2(y - cy, x - cx)
    col[r < 0.045 + 0.015 * np.cos(4 * a)] = gold
    col[r < 0.02] = red * 0.7
out = np.clip(col * lum, 0, 1)
Image.fromarray((out ** (1 / 1.0) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6)).save(f'{T}/carpet_c.jpg', quality=92)
# ---- ceiling: warm glass in a gilt quatrefoil lattice
keep('ceiling_c')
cx, cy = (x % 0.5) - 0.25, (y % 0.5) - 0.25
r = np.hypot(cx, cy); a = np.arctan2(cy, cx)
quat = r - (0.17 + 0.05 * np.cos(4 * a))
line = np.exp(-(quat / 0.012) ** 2)
grid = np.exp(-((np.minimum(np.abs(cx), np.abs(cy))) / 0.006) ** 2) * (r > 0.2)
glass = np.array([1.0, 0.95, 0.84]) * (0.9 + 0.1 * np.clip(1 - r / 0.35, 0, 1)[..., None])
gilt = np.array([0.45, 0.33, 0.14])
m = np.clip(line + grid, 0, 1)[..., None]
c = glass * (1 - m) + gilt * m
Image.fromarray((np.clip(c, 0, 1) * 255).astype(np.uint8)).save(f'{T}/ceiling_c.jpg', quality=92)
print('ok')
