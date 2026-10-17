"""CPU mock of VerneUnderwater (march + composite, same equations as the shader) on a Crespo-like
scene: sand sloping away, a stand of kelp stems casting real shadows into the shafts. Used to tune the
VerneWater colour scripts before Unity is available. Writes Source/previews/m3_water_mock_<preset>.png"""
import math, sys
import numpy as np
from PIL import Image

PRESETS = {
    'Mission1': dict(surfaceY=9.0, sig=(0.16, 0.06, 0.056), alb=(0.42, 0.5, 0.52), kd=(0.12, 0.045, 0.04), amb=(0.06, 0.11, 0.12), g=0.65, shafts=2.5, maxd=50.0, exposure=0.3, sat=1.12, sun=(58, 200)),
    'Title':    dict(surfaceY=24.0, sig=(0.28, 0.072, 0.062), alb=(0.5, 0.75, 0.8), kd=(0.3, 0.065, 0.05), amb=(0.28, 0.5, 0.52), g=0.6, shafts=1.3, maxd=60.0, exposure=0.2, sat=0.94),
}
name = sys.argv[1] if len(sys.argv) > 1 else 'Mission1'
P = PRESETS[name]
W, H = 640, 360
sig = np.array(P['sig']); alb = np.array(P['alb']); kd = np.array(P['kd']); amb = np.array(P['amb'])
pt, yw = [math.radians(a) for a in P.get('sun', (58, 30))]
fwd = np.array([math.sin(yw) * math.cos(pt), -math.sin(pt), math.cos(yw) * math.cos(pt)]); Lsun = -fwd / np.linalg.norm(fwd)
sunc = np.array([0.9, 0.97, 0.92]) * 1.8
skyamb = np.array([0.16, 0.34, 0.36])
rng = np.random.default_rng(23)
ang = rng.uniform(0, 2 * np.pi, 140); rad = 26 * np.sqrt(rng.uniform(0, 1, 140))
kx, kz = np.cos(ang) * rad, 70 + np.sin(ang) * rad
kh = rng.uniform(3.0, 4.6, 140)
def ground(x, z): return -np.clip((z - 40) / 160, 0, 1) * 18
cam = np.array([0.0, 1.6, 38.0]); pitch = math.radians(6)
f = 0.5 * W / math.tan(math.radians(60) / 2)
ys, xs = np.mgrid[0:H, 0:W]
d = np.stack([(xs - W / 2) / f, (H / 2 - ys) / f, np.ones_like(xs, float)], -1)
cp, sp = math.cos(pitch), math.sin(pitch)
d = np.stack([d[..., 0], d[..., 1] * cp + d[..., 2] * sp, -d[..., 1] * sp + d[..., 2] * cp], -1)
d /= np.linalg.norm(d, axis=-1, keepdims=True)
d = d.reshape(-1, 3); N = len(d)
# ground hit by marching coarse then refine
t_hit = np.full(N, 1e5); hitk = np.full(N, -1)
ts = np.linspace(0.2, 120, 600)
for t in ts:
    p = cam + d * t
    m = (t_hit > 1e4) & (p[:, 1] <= ground(p[:, 0], p[:, 2]))
    t_hit[m] = t
# kelp cylinders (vertical, radius 0.12)
for i in range(140):
    ox, oz = cam[0] - kx[i], cam[2] - kz[i]
    a = d[:, 0] ** 2 + d[:, 2] ** 2; b = 2 * (ox * d[:, 0] + oz * d[:, 2]); c = ox * ox + oz * oz - 0.12 ** 2
    disc = b * b - 4 * a * c
    ok = disc > 0
    t = np.where(ok, (-b - np.sqrt(np.maximum(disc, 0))) / (2 * a + 1e-9), 1e9)
    y = cam[1] + d[:, 1] * t
    gy = ground(kx[i], kz[i])
    m = ok & (t > 0) & (t < t_hit) & (y > gy) & (y < gy + kh[i])
    t_hit[m] = t[m]; hitk[m] = i
def shadow(p):
    """1 lit, 0 in a kelp stem's shadow (analytic, toward the sun)."""
    lit = np.ones(len(p))
    Lxz = np.array([Lsun[0], Lsun[2]]); Lxz_n = Lxz / np.linalg.norm(Lxz)
    for i in range(140):
        rx, rz = kx[i] - p[:, 0], kz[i] - p[:, 2]
        s = (rx * Lsun[0] + rz * Lsun[2]) / (Lsun[0] ** 2 + Lsun[2] ** 2)
        cx, cz = p[:, 0] + Lsun[0] * s - kx[i], p[:, 2] + Lsun[2] * s - kz[i]
        yat = p[:, 1] + Lsun[1] * s
        gy = ground(kx[i], kz[i])
        lit[(s > 0) & (cx * cx + cz * cz < 0.12 ** 2 * 1.0) & (yat < gy + kh[i]) & (yat > gy)] = 0
    return lit
def day(y): return np.exp(-kd[None] * np.maximum(0, P['surfaceY'] - y)[:, None])
print('kelp px', (hitk>=0).sum(), 'ground px', ((t_hit<1e4)&(hitk<0)).sum())
# surface colour
dist = t_hit.copy()
P_hit = cam + d * np.minimum(dist, 1e3)[:, None]
scene = np.zeros((N, 3))
hitg = (dist < 1e4) & (hitk < 0); hitc = hitk >= 0
for m, alb_s, nrm in ((hitg, np.array([0.52, 0.5, 0.45]), None), (hitc, np.array([0.28, 0.42, 0.18]), 'cyl')):
    if not m.any(): continue
    p = P_hit[m]
    if nrm is None: n = np.tile([0, 1.0, 0], (m.sum(), 1))
    else:
        n = np.stack([p[:, 0] - kx[hitk[m]], np.zeros(m.sum()), p[:, 2] - kz[hitk[m]]], -1); n /= np.linalg.norm(n, axis=1, keepdims=True)
    ndl = np.clip(n @ Lsun, 0, 1)
    sh = shadow(p + n * 0.02)
    scene[m] = alb_s * (sunc * day(p[:, 1]) * (ndl * sh)[:, None] + skyamb * (0.5 + 0.5 * n[:, 1:2]))
# march
def HG(c, g): return (1 - g * g) / (4 * np.pi * np.power(np.maximum(1e-3, 1 + g * g - 2 * g * c), 1.5))
steps = 16; tMax = np.minimum(dist, P['maxd']); dt = tMax / steps
jit = rng.uniform(0, 1, N)
T = np.ones((N, 3)); S = np.zeros((N, 3))
phase = HG(d @ Lsun, P['g']) * P['shafts']
sigS = sig * alb
for k in range(steps):
    t = (k + jit) * dt
    p = cam + d * t[:, None]
    dy = day(p[:, 1])
    Lin = amb * dy + sunc * dy * (shadow(p) * phase)[:, None]
    stepT = np.exp(-sig[None] * dt[:, None])
    S += T * Lin * sigS * (1 - stepT) / sig
    T *= stepT
Tm = np.exp(-sig[None] * tMax[:, None])
farP = cam + d * tMax[:, None]
Sfar = Tm * amb * day(farP[:, 1]) * alb * (1 - np.exp(-sig[None] * np.maximum(0, dist - tMax)[:, None]))
col = scene * np.exp(-sig[None] * dist[:, None]) + S + Sfar
col *= 2 ** P['exposure']
lum = col @ np.array([0.2126, 0.7152, 0.0722]); col = lum[:, None] + (col - lum[:, None]) * P['sat']
col = col / (1 + col)  # neutral-ish tonemap
img = np.clip(col, 0, 1) ** (1 / 2.2)
out = (img.reshape(H, W, 3) * 255).astype(np.uint8)
Image.fromarray(out).save(sys.argv[2] if len(sys.argv) > 2 else f'Source/previews/m3_water_mock_{name}.png')
print('done')
