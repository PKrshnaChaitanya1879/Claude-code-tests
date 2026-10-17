"""One riveted hull plate of the Nautilus as a tile (UV 0..1 per plate, see nautilus_exterior.py):
rows of round rivet heads along the four edges (double row on the overlapping aft edge, as in the
plate rows of ill-011), a faint hammered unevenness and a bevel at the seams. Writes hull_c.jpg
(base colour with grime in the seams) and hull_n.jpg (tangent-space normal, OpenGL / Unity +Y)."""
import numpy as np, sys
from PIL import Image
N = 512
out = sys.argv[1] if len(sys.argv) > 1 else '.'
u, v = np.meshgrid((np.arange(N) + 0.5) / N, (np.arange(N) + 0.5) / N)   # u around the hull (1.05 m), v along it (1.75 m)
su, sv = 1.05, 1.75                                                      # metres per tile, to keep rivets round
x, y = u * su, v * sv
h = np.zeros((N, N))
rng = np.random.default_rng(3)
# hammered unevenness
for f, a in ((3, 0.0005), (7, 0.00025), (17, 0.00012)):
    ph = rng.uniform(0, 6.28, 4)
    h += a * (np.sin(2 * np.pi * f * u + ph[0]) * np.sin(2 * np.pi * f * v * 1.4 + ph[1]) + np.sin(2 * np.pi * f * 1.3 * u + ph[2] + 2 * np.pi * f * v))
# seam bevels: the plate rounds down into its edges
d_edge = np.minimum.reduce([x, su - x, y, sv - y])
h -= 0.004 * np.clip(1 - d_edge / 0.02, 0, 1) ** 2
def rivets(px, py, r=0.011, hgt=0.006):
    global h
    for (cx, cy) in zip(px, py):
        dd = ((x - cx) ** 2 + (y - cy) ** 2) / (r * r)
        h += hgt * np.sqrt(np.clip(1 - dd, 0, 1))
inset = 0.045
for cy in (inset, sv - inset, sv - inset - 0.04):          # double row on the aft (proud) edge
    xs = np.arange(0.05, su - 0.02, 0.085)
    rivets(xs, np.full_like(xs, cy))
for cx in (inset, su - inset):
    ys = np.arange(0.09, sv - 0.08, 0.09)
    rivets(np.full_like(ys, cx), ys)
# normals from height (in metres per pixel)
px_u, px_v = su / N, sv / N
dhdx = np.gradient(h, axis=1) / px_u
dhdy = np.gradient(h, axis=0) / px_v
n = np.dstack([-dhdx, -dhdy, np.ones_like(h)])
n /= np.linalg.norm(n, axis=2, keepdims=True)
img = ((n * 0.5 + 0.5) * 255).astype(np.uint8)
Image.fromarray(img[::-1]).save(f'{out}/hull_n.jpg', quality=95)      # flip rows: image top = v 1
# base colour: dark iron-grey with greenish sea patina, darker grime around rivets and seams
base = np.array([0.14, 0.16, 0.16])
grime = np.clip(1 - d_edge / 0.05, 0, 1) * 0.35 + np.clip(h / 0.006, 0, 1) * -0.1
streak = 0.06 * np.sin(2 * np.pi * (u * 3 + rng.uniform())) * np.clip(np.sin(2 * np.pi * v * 2), 0, 1)
col = base[None, None] * (1 - grime[..., None]) * (1 + streak[..., None]) + np.array([0.0, 0.015, 0.01])
Image.fromarray((np.clip(col, 0, 1) ** (1 / 2.2) * 255).astype(np.uint8)[::-1]).save(f'{out}/hull_c.jpg', quality=92)
print('ok', h.min(), h.max())
