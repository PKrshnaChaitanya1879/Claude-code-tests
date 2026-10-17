"""Captain Nemo's organ: the opening of J. S. Bach's Toccata in D minor, BWV 565 (public domain),
performed here by additive synthesis of a pipe organ (16', 8', 4', 2 2/3', 2' ranks, wind noise on
the attack, slow chorus) in a large stone-and-iron reverb. The brief allows pre-1929 works for Nemo.
Writes Unity/.../Resources/VerneAudio/music/organ_bwv565.ogg and a spectrogram for the listen-check."""
import numpy as np, soundfile as sf, pyloudnorm as pyln, sys, os
from pedalboard import Pedalboard, Reverb, LowShelfFilter, HighShelfFilter, Compressor

SR = 44100
OUT = sys.argv[1] if len(sys.argv) > 1 else 'organ_bwv565.ogg'
def hz(n): return 440.0 * 2 ** ((n - 69) / 12)
N = {'C': 0, 'C#': 1, 'D': 2, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'Ab': 8, 'A': 9, 'Bb': 10, 'B': 11}
def m(name):  # 'A5' -> midi
    return 12 * (int(name[-1]) + 1) + N[name[:-1]]

def pipe(f, dur, vel=1.0, low=False):
    t = np.arange(int((dur + 0.6) * SR)) / SR
    ranks = [(1.0, 1.0), (2.0, 0.45), (3.0, 0.18), (4.0, 0.22), (6.0, 0.06), (8.0, 0.05)]
    if low: ranks += [(0.5, 0.55)]
    y = np.zeros_like(t)
    for k, a in ranks:
        if f * k > 9000: continue
        det = 1 + 0.0009 * np.sin(2 * np.pi * 0.31 * t + k)   # slow chorus between ranks
        y += a * np.sin(2 * np.pi * f * k * det * t + k * 1.3)
    att = np.clip(t / 0.035, 0, 1)
    rel = np.clip((dur + 0.18 - t) / 0.18, 0, 1)
    env = att * rel
    # wind "chiff" on the attack
    chiff = np.random.default_rng(int(f)).normal(0, 1, len(t)) * np.exp(-t / 0.03) * 0.12
    return (y * env + chiff * att) * vel

score = []  # (start, midi, dur)
def phrase(t0, octave_shift):
    s = 12 * octave_shift
    seq = [('A5', 0.11), ('G5', 0.11), ('A5', 1.1), (None, 0.3), ('G5', 0.16), ('F5', 0.16), ('E5', 0.16), ('D5', 0.16), ('C#5', 0.75), ('D5', 1.5)]
    t = t0
    for n, d in seq:
        if n: score.append((t, m(n) + s, d))
        t += d
    return t
t = phrase(0.3, 0) + 0.5
t = phrase(t, -1) + 0.5
t = phrase(t, -2)
for (st, n, d) in list(score):
    if n < m('C4'): score.append((st, n - 12, d))      # the pedal doubles the low statement
t += 0.6
score.append((t, m('D2'), 4.4)); score.append((t, m('D3'), 4.4))
for i, n in enumerate(['C#3', 'E3', 'G3', 'Bb3', 'C#4', 'E4']):
    score.append((t + 0.13 * (i + 1), m(n), 2.2 - 0.13 * (i + 1)))
t2 = t + 2.3
for n in ['D3', 'F3', 'A3', 'D4', 'F4']:
    score.append((t2, m(n), 2.6))
total = t2 + 2.6 + 3.5
y = np.zeros(int(total * SR))
for (st, n, d) in score:
    p = pipe(hz(n), d, 0.55 if n > m('C5') else 0.7, low=n < m('C3'))
    i = int(st * SR); y[i:i + len(p)] += p[:len(y) - i]
y = np.stack([y, np.roll(y, 37)], 1).astype(np.float32)
board = Pedalboard([LowShelfFilter(cutoff_frequency_hz=180, gain_db=2.5), HighShelfFilter(cutoff_frequency_hz=5000, gain_db=-4),
                    Compressor(threshold_db=-14, ratio=2.0), Reverb(room_size=0.92, damping=0.45, wet_level=0.42, dry_level=0.62, width=1.0)])
y = board(y, SR)
meter = pyln.Meter(SR)
y = pyln.normalize.loudness(y, meter.integrated_loudness(y), -18.0)
y = np.clip(y, -0.98, 0.98)
sf.write(OUT, y, SR, format='OGG', subtype='VORBIS')
print('written', OUT, round(len(y) / SR, 1), 's, LUFS', round(meter.integrated_loudness(y), 1))
if len(sys.argv) > 2:
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(10, 3.2), facecolor='#0e0e10'); ax.set_facecolor('#0e0e10')
    ax.specgram(y[:, 0], NFFT=2048, Fs=SR, noverlap=1536, cmap='magma', vmin=-110)
    ax.set_ylim(0, 4000); ax.set_title("Nemo's organ: BWV 565 opening (synthesised) · spectrogram", color='#ddd', fontsize=10)
    ax.tick_params(colors='#999'); fig.tight_layout(); fig.savefig(sys.argv[2], dpi=110)
