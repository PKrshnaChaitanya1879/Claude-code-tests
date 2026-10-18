"""M6 (started in Part 3): the rain on the surface, heard from 150 fathoms down (II.IX): "I heard a kind of pattering
above my head. The noise redoubling, sometimes producing a continual shower ... It was rain falling violently, and
crisping the surface of the waves."
Physics, then art direction:
- every drop that strikes the surface rings: an impact tick, and for large drops a bubble entrained under it that rings at
  its Minnaert frequency f = 3.26 / r (r in metres): heavy-rain drops trap 1-4 mm bubbles, 0.8-3.3 kHz;
  light rain's tiny bubbles sing near 15 kHz (Medwin's rain peak), kept quiet here and cut by the helmet anyway;
- heard far below, the pattering smears into a soft roof of sound, so each ping is low-passed and slightly
  reverberated, and the rate swells and slackens in gusts ("the noise redoubling, sometimes ... a continual shower").
Loudness -27 LUFS (under the bed). Seamless 40 s loop. Writes loops/rain_below.ogg and a spectrogram preview."""
import numpy as np, soundfile as sf, pyloudnorm as pyln, os, sys
from scipy.signal import butter, sosfiltfilt, fftconvolve
SR = 44100
OUT = sys.argv[1] if len(sys.argv) > 1 else 'Unity/TwentyThousandLeagues/Assets/Verne/Resources/VerneAudio'
PREV = sys.argv[2] if len(sys.argv) > 2 else 'Source/previews/m6_rain_below.png'
os.makedirs(OUT + '/loops', exist_ok=True)
rng = np.random.default_rng(9)
def lp(x, f, o=2): return sosfiltfilt(butter(o, f, 'lowpass', fs=SR, output='sos'), x, axis=0)
def hp(x, f, o=2): return sosfiltfilt(butter(o, f, 'highpass', fs=SR, output='sos'), x, axis=0)

D = 42.0; N = int(D * SR); t = np.arange(N) / SR
x = np.zeros(N)
# gusts: the rate of drops wanders between a patter and a downpour
gust = 0.55 + 0.45 * np.sin(2 * np.pi * t / 14.0) * np.sin(2 * np.pi * t / 5.3 + 1.0) ** 2
rate = 900 * gust                                         # drops per second within earshot
n = int(np.sum(rate) / SR)
cdf = np.cumsum(rate); cdf /= cdf[-1]
times = np.searchsorted(cdf, rng.uniform(0, 1, n))
L = int(0.03 * SR); tl = np.arange(L) / SR
for i in times:
    if i + L >= N: continue
    a = rng.lognormal(-1.2, 0.6)
    # impact tick
    x[i:i + 40] += a * 0.25 * rng.normal(size=40) * np.exp(-np.arange(40) / 8)
    if rng.random() < 0.55:                               # a bubble rings under the large drops
        r = rng.uniform(1.0e-3, 4.0e-3); f = 3.26 / r
        dec = 25 + f * 0.012
        x[i:i + L] += a * np.sin(2 * np.pi * f * tl * (1 + 0.15 * tl)) * np.exp(-dec * tl)
    elif rng.random() < 0.3:                              # the small ones near 15 kHz
        x[i:i + L // 3] += a * 0.2 * np.sin(2 * np.pi * rng.uniform(13e3, 16e3) * tl[:L // 3]) * np.exp(-160 * tl[:L // 3])
# far below: soften, smear in a short diffuse tail, keep a little air
x = lp(x, 5200, 3)
ir = rng.normal(size=int(0.35 * SR)) * np.exp(-np.arange(int(0.35 * SR)) / (0.08 * SR))
x = 0.6 * x + 0.4 * fftconvolve(x, ir, mode='full')[:N] / np.sqrt(np.sum(ir ** 2))
x = hp(x, 180)
# seamless loop
xf = int(2.0 * SR); a = np.linspace(0, 1, xf)
y = x[:-xf].copy(); y[:xf] = y[:xf] * a + x[-xf:] * (1 - a)
st = np.stack([y, np.roll(y, int(0.011 * SR)) * 0.9 + y * 0.1], 1)
meter = pyln.Meter(SR)
st = pyln.normalize.loudness(st, meter.integrated_loudness(st), -27.0)
st = np.clip(st, -0.95, 0.95)
sf.write(OUT + '/loops/rain_below.ogg', st.astype(np.float32), SR, format='OGG', subtype='VORBIS')
print('rain_below', round(meter.integrated_loudness(st), 1), 'LUFS', round(len(st) / SR, 1), 's')
try:
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(2, 1, figsize=(10, 5.5))
    ax[0].specgram(st[:, 0], NFFT=2048, Fs=SR, noverlap=1024, cmap='magma'); ax[0].set_ylim(0, 18000)
    ax[0].set_title('rain on the surface, heard from 150 fathoms (rain_below.ogg): bubble rings 0.8-3.3 kHz, faint 15 kHz')
    ax[1].plot(np.arange(len(st)) / SR, st[:, 0], lw=0.3, color='#334'); ax[1].set_xlabel('s'); ax[1].set_title('gusts: the patter redoubling')
    plt.tight_layout(); plt.savefig(PREV, dpi=80)
except Exception as e:
    print('no preview', e)
