"""CPU mock of the Verne/SeaLit water model through the saloon window (same equations as the shader),
to tune the water constants before Unity is available. Writes Source/previews/m2_saloon_window_mock.png."""
import math, random, sys
import numpy as np
from PIL import Image, ImageDraw

W, H = 960, 540
sigma = np.array([0.11, 0.045, 0.04]); water = np.array([0.004, 0.032, 0.040]); amb = np.array([0.004, 0.010, 0.013])
lamp = np.array([3.8, 2.0, 15.0]); lampc = np.array([2.0, 1.95, 1.8]); rng_ = 7.0
cam = np.array([-1.2, 1.7, 15.0]); fwd = np.array([1.0, 0.05, 0.0]); fwd /= np.linalg.norm(fwd)
right = np.cross(np.array([0, 1.0, 0]), fwd); right /= np.linalg.norm(right); up = np.cross(fwd, right)
f = 0.5 * W / math.tan(math.radians(62) / 2)
def tonemap(c): return np.clip((c / (1 + c)) ** (1 / 2.2), 0, 1)
img = np.zeros((H, W, 3))
ys, xs = np.mgrid[0:H, 0:W]
d = (fwd[None, None] * f + right[None, None] * (xs - W / 2)[..., None] + up[None, None] * (H / 2 - ys)[..., None]); d /= np.linalg.norm(d, axis=2, keepdims=True)
tl = (lamp - cam); tl /= np.linalg.norm(tl)
toward = np.clip((d @ tl) * 0.5 + 0.5, 0, 1); upk = np.clip(d[..., 1] * 0.5 + 0.5, 0, 1)
img[:] = water[None, None] * (0.12 + 1.6 * upk[..., None] ** 3 + 0.9 * toward[..., None] ** 4)
random.seed(3)
splats = []
def school(n, scale, col, sheen, centre, spread):
    for _ in range(n):
        p = np.array(centre) + np.array([random.uniform(-.5, .5) * spread, random.uniform(-.25, .25) * spread, random.uniform(-1, 1) * spread])
        splats.append((p, scale, np.array(col), sheen))
school(40, 0.28, (0.62, 0.7, 0.74), 1.0, (7, 2.3, 15), 2.2)
school(24, 0.34, (0.95, 0.42, 0.16), 0.6, (5.6, 1.2, 13), 1.6)
school(40, 0.28, (0.62, 0.7, 0.74), 1.0, (12, 3.5, 19), 2.2)
school(2, 1.9, (0.32, 0.36, 0.4), 0.35, (11, 1.0, 12), 2.5)
im = Image.fromarray((tonemap(img) * 255).astype(np.uint8)); dr = ImageDraw.Draw(im)
for p, s, col, sheen in sorted(splats, key=lambda q: -np.linalg.norm(q[0] - cam)):
    v = p - cam; z = v @ fwd
    if z < 0.5: continue
    sx, sy = W / 2 + f * (v @ right) / z, H / 2 - f * (v @ up) / z
    lp = np.array([math.copysign(abs(lamp[0]), p[0]), lamp[1], min(max(p[2], 12.9), 17.1)]); L = lp - p; ld = np.linalg.norm(L); L /= ld; N = -(v / np.linalg.norm(v)) * 0.5 + np.array([0, 0.6, 0]); N /= np.linalg.norm(N)
    fall = 1 / (1 + ld * ld / (rng_ * rng_) * 4)
    la = lampc * np.exp(-sigma * ld) * fall
    wrap = max(0, (N @ L + 0.35) / 1.35)
    Hh = L - v / np.linalg.norm(v); Hh /= np.linalg.norm(Hh); spec = max(0, N @ Hh) ** 24 * sheen * 1.5
    lit = col * (la * wrap + amb * (0.6 + 0.4 * N[1])) + la * spec
    T = np.exp(-sigma * np.linalg.norm(v)); c = lit * T + water * (1 - T)
    r = f * s * 0.5 / z
    dr.ellipse([sx - r, sy - r * 0.4, sx + r, sy + r * 0.4], fill=tuple((tonemap(c) * 255).astype(int)))
# window frame (the embrasure) so it reads as seen from the saloon
m = Image.new('L', (W, H), 0); ImageDraw.Draw(m).rounded_rectangle([110, 70, W - 110, H - 40], 60, fill=255)
bg = Image.new('RGB', (W, H), (34, 26, 20)); out = Image.composite(im, bg, m)
dd = ImageDraw.Draw(out)
for k in (1, 2): x = 110 + (W - 220) * k / 3; dd.rectangle([x - 4, 70, x + 4, H - 40], fill=(120, 72, 40))
dd.rectangle([110, (70 + H - 40) / 2 - 4, W - 110, (70 + H - 40) / 2 + 4], fill=(120, 72, 40))
out.save(sys.argv[1] if len(sys.argv) > 1 else 'Source/previews/m2_saloon_window_mock.png')
