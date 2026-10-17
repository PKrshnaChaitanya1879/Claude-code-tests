"""M6 beds and breathing (first pass), synthesised so they loop seamlessly:
- hull_hum.ogg: inside the Nautilus. The electric hum of Bunsen's piles (50/100/150 Hz, slowly beating), the screw's
  thrum (about two beats a second, felt more than heard), and the sea sliding along the plates, heard through iron.
- underwater_bed.ogg: outside, heard through the copper helmet: deep rumble, a slow swell, distant creaks of the
  bottom, and now and then a cloud of tiny bubbles (Minnaert: f = 3.26 / r).
- breath_in_0..2 / breath_out_0..2: the Rouquayrol regulator, a valve's hiss drawing in, and the exhalation leaving
  the helmet as a burst of bubbles.
Loudness: beds at -24 LUFS, breaths at -22 LUFS (they sit under the score). Writes OGG Vorbis into Resources/VerneAudio."""
import numpy as np, soundfile as sf, pyloudnorm as pyln, os, sys
from scipy.signal import butter, sosfilt, sosfiltfilt
SR = 44100
OUT = sys.argv[1] if len(sys.argv) > 1 else 'Unity/TwentyThousandLeagues/Assets/Verne/Resources/VerneAudio'
os.makedirs(OUT + '/loops', exist_ok=True); os.makedirs(OUT + '/breath', exist_ok=True)
rng = np.random.default_rng(1870)
meter = pyln.Meter(SR)
def bp(x, lo, hi, o=2): return sosfiltfilt(butter(o, [lo, hi], 'bandpass', fs=SR, output='sos'), x, axis=0)
def lp(x, f, o=2): return sosfiltfilt(butter(o, f, 'lowpass', fs=SR, output='sos'), x, axis=0)
def hp(x, f, o=2): return sosfiltfilt(butter(o, f, 'highpass', fs=SR, output='sos'), x, axis=0)
def loudness(x, lufs):
    l = meter.integrated_loudness(x)
    return pyln.normalize.loudness(x, l, lufs) if np.isfinite(l) else x
def loopify(x, xf=2.0):
    """Crossfade the tail into the head so the loop is seamless."""
    n = int(xf * SR); a = np.linspace(0, 1, n)[:, None] if x.ndim > 1 else np.linspace(0, 1, n)
    y = x[:-n].copy(); y[:n] = y[:n] * a + x[-n:] * (1 - a)
    return y
def save(path, x, lufs):
    x = loudness(x, lufs); x = np.clip(x, -0.95, 0.95)
    sf.write(path, x.astype(np.float32), SR, format='OGG', subtype='VORBIS'); return x
def stereo(m, w=0.002):
    return np.stack([m, np.roll(m, int(w * SR))], 1)

# ---- hull hum (32 s + 2 s crossfade)
D = 34.0; t = np.arange(int(D * SR)) / SR
hum = sum(a * np.sin(2 * np.pi * f * t + p) for f, a, p in ((50, 1.0, 0), (100, 0.45, 1), (150, 0.18, 2), (200.6, 0.06, 0.5)))
hum *= 1 + 0.15 * np.sin(2 * np.pi * 0.07 * t)
thrum = np.sin(2 * np.pi * 31 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 2.0 * t)) ** 3
sea = lp(rng.normal(size=len(t)), 420) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.11 * t + 1)) * 6
hull = 0.25 * hum + 0.5 * thrum + sea
save(OUT + '/loops/hull_hum.ogg', loopify(stereo(hull)), -24)
# ---- underwater bed (40 s + 2 s)
D = 42.0; t = np.arange(int(D * SR)) / SR
rumble = lp(rng.normal(size=len(t)), 160, 4) * 9
swell = (0.55 + 0.45 * np.sin(2 * np.pi * 0.08 * t)) * lp(rng.normal(size=len(t)), 700) * 2.5
bed = rumble + swell
for k in range(14):                                  # distant creaks: low modal knocks
    t0 = rng.uniform(0, D - 2); i = int(t0 * SR); n = int(1.2 * SR)
    tt = np.arange(n) / SR; f = rng.uniform(70, 190)
    bed[i:i + n] += 0.25 * np.sin(2 * np.pi * f * tt * (1 + 0.04 * tt)) * np.exp(-tt * 3.5) * rng.uniform(0.3, 1)
for k in range(9):                                   # clouds of tiny bubbles far off
    t0 = rng.uniform(0, D - 3); i = int(t0 * SR)
    for b in range(rng.integers(6, 18)):
        r = rng.uniform(0.0008, 0.004); f = 3.26 / r
        n = int(0.08 * SR); tt = np.arange(n) / SR; j = i + int(rng.uniform(0, 1.2) * SR)
        if j + n < len(bed): bed[j:j + n] += 0.04 * np.sin(2 * np.pi * f * tt * (1 + 0.3 * tt)) * np.exp(-tt * 60)
bed = lp(bed, 2500)                                  # through the copper and the glass
save(OUT + '/loops/underwater_bed.ogg', loopify(stereo(bed, 0.004)), -24)
# ---- breathing: the regulator's hiss in, bubbles out
for k in range(3):
    d = 1.5 + 0.2 * k; t = np.arange(int(d * SR)) / SR
    e = np.clip(t / 0.25, 0, 1) * np.clip((d - t) / 0.35, 0, 1)
    hiss = bp(rng.normal(size=len(t)), 1100 + 200 * k, 4200) * e * (0.7 + 0.3 * np.sin(2 * np.pi * (3 + k) * t))
    valve = np.sin(2 * np.pi * (420 + 40 * k) * t) * np.exp(-t * 30) * 0.3
    save(OUT + f'/breath/breath_in_{k}.ogg', stereo(hiss + valve, 0.0003), -22)
    d = 1.8 + 0.2 * k; n = int(d * SR); x = np.zeros(n)
    rush = bp(rng.normal(size=n), 120, 900) * np.clip(np.arange(n) / (0.1 * SR), 0, 1) * np.exp(-np.arange(n) / (0.6 * SR)) * 0.8
    x += rush
    for b in range(70 + 10 * k):                     # the exhalation leaving the helmet: a burst of bubbles
        r = rng.uniform(0.0015, 0.008); f = 3.26 / r
        m = int(0.06 * SR); tt = np.arange(m) / SR; j = int(rng.uniform(0, 0.9) ** 1.6 * (n - m))
        x[j:j + m] += 0.18 * np.sin(2 * np.pi * f * tt * (1 + 0.6 * tt)) * np.exp(-tt * (40 + 400 * r))
    save(OUT + f'/breath/breath_out_{k}.ogg', stereo(lp(x, 4000), 0.0004), -22)
print('ok')
if len(sys.argv) > 2:
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    fig, axs = plt.subplots(2, 2, figsize=(11, 5), facecolor='#0e0e10')
    for ax, (f, title) in zip(axs.ravel(), [('loops/hull_hum.ogg', 'hull hum (Nautilus)'), ('loops/underwater_bed.ogg', 'underwater bed (helmet)'),
                                           ('breath/breath_in_0.ogg', 'Rouquayrol: in'), ('breath/breath_out_0.ogg', 'exhalation: bubbles')]):
        y, _ = sf.read(OUT + '/' + f); y = y[:, 0] if y.ndim > 1 else y
        ax.set_facecolor('#0e0e10'); ax.specgram(y + 1e-9, NFFT=2048, Fs=SR, noverlap=1536, cmap='magma', vmin=-120)
        ax.set_ylim(0, 8000 if 'breath' in f else 2000); ax.set_title(f'{title} · {meter.integrated_loudness(sf.read(OUT + "/" + f)[0]):.1f} LUFS', color='#ddd', fontsize=9); ax.tick_params(colors='#999')
    fig.tight_layout(); fig.savefig(sys.argv[2], dpi=100)
