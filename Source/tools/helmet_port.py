"""The copper helmet's front port as a screen overlay (I.XIV: "three holes, protected by thick glass"):
a round port a little taller than the screen, the copper rim catching the light at its edge, the
helmet's dark inside beyond it, a faint smear on the glass; and the breath fog that blooms on the lower
glass with each exhalation (driven in Unity). Writes helmet_port.png and helmet_fog.png (RGBA)."""
import numpy as np, sys
from PIL import Image, ImageFilter
out = sys.argv[1] if len(sys.argv) > 1 else '.'
W, H = 1024, 576
y, x = np.mgrid[0:H, 0:W].astype(float)
cx, cy = W / 2, H / 2 + 10
R = H * 0.8
r = np.hypot((x - cx) / 1.22, (y - cy)) / R          # a wide port: the corners only
rim0, rim1 = 1.0, 1.06
inside = np.clip((r - rim0) / (rim1 - rim0), 0, 1)
a = np.clip((r - 0.86) / 0.16, 0, 1) ** 1.6 * 0.55 + inside * 0.45      # soft vignette into the glass edge, opaque helmet beyond
col = np.zeros((H, W, 3))
# copper rim: a lit band just outside the glass, brighter at the top-left (the lamp side)
band = np.exp(-((r - 1.02) / 0.02) ** 2)
ang = np.arctan2(y - cy, x - cx)
lit = 0.5 + 0.5 * np.cos(ang + 2.3)
col += band[..., None] * np.array([0.30, 0.16, 0.08]) * (0.25 + 0.75 * lit[..., None])
col += (1 - band[..., None]) * np.array([0.03, 0.025, 0.022]) * inside[..., None]
a = np.maximum(a, band * 0.9)
# a faint smear across the glass
rng = np.random.default_rng(2)
sm = np.zeros((H, W))
for _ in range(6):
    px, py, s = rng.uniform(0.25, 0.75) * W, rng.uniform(0.2, 0.8) * H, rng.uniform(40, 120)
    sm += np.exp(-(((x - px) / (s * 2.2)) ** 2 + ((y - py) / s) ** 2))
sm = np.clip(sm, 0, 1) * (r < 1)
col += sm[..., None] * np.array([0.5, 0.55, 0.55]) * 0.25
a = np.maximum(a, sm * 0.05)
img = np.dstack([np.clip(col, 0, 1) ** (1 / 2.2), a])
Image.fromarray((img * 255).astype(np.uint8), 'RGBA').save(f'{out}/helmet_port.png')
# breath fog: a soft bloom on the lower glass, mottled
fog = np.clip(1 - np.hypot((x - cx) / 520, (y - (H * 0.95)) / 260), 0, 1) ** 1.5
noise = Image.fromarray((rng.uniform(0, 255, (H // 8, W // 8))).astype(np.uint8)).resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(6))
fog *= 0.6 + 0.4 * np.asarray(noise) / 255.0
fimg = np.dstack([np.full((H, W), 0.82), np.full((H, W), 0.86), np.full((H, W), 0.88), np.clip(fog * 0.55, 0, 1)])
Image.fromarray((fimg * 255).astype(np.uint8), 'RGBA').save(f'{out}/helmet_fog.png')
print('ok')
