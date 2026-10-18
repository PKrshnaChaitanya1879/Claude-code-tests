"""M6 (started in Part 3): the original score. Inspired by BioShock (Garry Schyman: aleatoric strings, a solo violin,
1940s-50s colour) and INSIDE (Martin Stig Andersen: sparse drones, processed textures); no melody is borrowed.
Every cue is composed here as MIDI (mido), played by FluidR3_GM through FluidSynth, then blended with a synthesised
INSIDE-like bed (filtered noise and slow sine drones), given a large dark hall (pedalboard), and normalised.
Material: one leitmotif for Nemo, D Dorian/Aeolian, rising a fifth and falling back by step (written for this game).
Cues (OGG, Resources/VerneAudio/music):
  title        - the Nautilus at rest in blue twilight: low drone, harp and celesta, the solo violin states Nemo's motif
  m1_wonder    - the forest and the coral kingdom: warm divided strings, slow harp, clarinet, light (loops)
  burial       - I.XXIV: a string chorale with low choir, the motif in the cellos, the adieu (one shot, ~1:40)
Usage: python3 score.py [cue ...]   (default: all). Writes Source/previews/m6_score_<cue>.png spectrograms."""
import os, sys, subprocess, tempfile, numpy as np, soundfile as sf, pyloudnorm as pyln
import mido
from pedalboard import Pedalboard, Reverb, LowShelfFilter, HighShelfFilter, Compressor, Gain
from scipy.signal import butter, sosfiltfilt

SR = 44100
SF2 = '/usr/share/sounds/sf2/FluidR3_GM.sf2'
OUT = 'Unity/TwentyThousandLeagues/Assets/Verne/Resources/VerneAudio/music'
PREV = 'Source/previews'
os.makedirs(OUT, exist_ok=True)
TPB = 480
GM = dict(strings=48, slow_strings=49, tremolo=44, violin=40, cello=42, contrabass=43, harp=46, celesta=8, clarinet=71,
          choir=52, pad_bowed=92, pad_warm=89, french_horn=60, glock=9, vibes=11)

# Nemo's motif (scale degrees in D: D=0): up a fifth, hold, fall by step, a turn at the end
NEMO = [(0, 1.0), (7, 2.0), (5, 0.5), (3, 0.5), (2, 1.0), (3, 0.5), (0, 2.5)]
D_DORIAN = [0, 2, 3, 5, 7, 9, 10]

class Song:
    def __init__(self, bpm):
        self.bpm = bpm; self.tracks = {}; self.ch = 0
    def track(self, name, program):
        if name not in self.tracks:
            ch = self.ch if self.ch < 9 else self.ch + 1; self.ch += 1
            self.tracks[name] = dict(ch=ch, prog=program, ev=[])
        return self.tracks[name]
    def note(self, name, program, beat, dur, pitch, vel):
        t = self.track(name, program)
        t['ev'].append((beat, 'on', pitch, vel)); t['ev'].append((beat + dur, 'off', pitch, 0))
    def cc(self, name, program, beat, num, val):
        self.track(name, program)['ev'].append((beat, 'cc', num, int(max(0, min(127, val)))))
    def swell(self, name, program, b0, b1, v0, v1, num=11, steps=24):
        for k in range(steps + 1):
            self.cc(name, program, b0 + (b1 - b0) * k / steps, num, v0 + (v1 - v0) * k / steps)
    def save(self, path):
        mid = mido.MidiFile(ticks_per_beat=TPB)
        meta = mido.MidiTrack(); mid.tracks.append(meta)
        meta.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(self.bpm), time=0))
        for name, t in self.tracks.items():
            tr = mido.MidiTrack(); mid.tracks.append(tr)
            tr.append(mido.Message('program_change', channel=t['ch'], program=t['prog'], time=0))
            tr.append(mido.Message('control_change', channel=t['ch'], control=91, value=40, time=0))   # some of the synth's own reverb
            order = {'off': 0, 'cc': 1, 'on': 2}
            ev = sorted(t['ev'], key=lambda e: (e[0], order[e[1]]))
            last = 0
            for b, kind, a, v in ev:
                tick = int(round(b * TPB)); dt = max(0, tick - last); last = max(last, tick)
                if kind == 'on': tr.append(mido.Message('note_on', channel=t['ch'], note=int(a), velocity=int(v), time=dt))
                elif kind == 'off': tr.append(mido.Message('note_off', channel=t['ch'], note=int(a), velocity=0, time=dt))
                else: tr.append(mido.Message('control_change', channel=t['ch'], control=int(a), value=int(v), time=dt))
        mid.save(path)

def render(song, seconds):
    with tempfile.TemporaryDirectory() as d:
        m = os.path.join(d, 'x.mid'); w = os.path.join(d, 'x.wav')
        song.save(m)
        subprocess.run(['fluidsynth', '-ni', '-g', '0.6', '-r', str(SR), '-F', w, SF2, m], check=True, capture_output=True)
        x, sr = sf.read(w, always_2d=True)
    n = int(seconds * SR)
    if len(x) < n: x = np.vstack([x, np.zeros((n - len(x), 2))])
    return x[:n]

def lp(x, f, o=2): return sosfiltfilt(butter(o, f, 'lowpass', fs=SR, output='sos'), x, axis=0)
def bp(x, lo, hi, o=2): return sosfiltfilt(butter(o, [lo, hi], 'bandpass', fs=SR, output='sos'), x, axis=0)

def bed(seconds, root_hz, seed, air=0.4, dark=1.0):
    """The INSIDE layer: a low sine drone that breathes, its fifth faintly, and filtered noise like distant water."""
    rng = np.random.default_rng(seed); n = int(seconds * SR); t = np.arange(n) / SR
    drone = (np.sin(2 * np.pi * root_hz * t + 0.3 * np.sin(2 * np.pi * 0.05 * t)) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.031 * t))
             + 0.35 * np.sin(2 * np.pi * root_hz * 1.5 * t + 1.0) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.023 * t + 2)) ** 2
             + 0.2 * np.sin(2 * np.pi * root_hz * 2.003 * t))
    noise = bp(rng.normal(size=n), 90, 500) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.07 * t + 1)) * 0.6
    hiss = bp(rng.normal(size=n), 2500, 7000) * air * 0.25 * (0.4 + 0.6 * np.sin(2 * np.pi * 0.019 * t) ** 2)
    m = dark * 0.5 * drone + 0.6 * noise + hiss
    return np.stack([m, np.roll(m, int(0.013 * SR))], 1) * 0.12

def mix(music, b, rel_db):
    """The bed sits rel_db under the music (RMS), never over it: the drone is felt, the strings are heard."""
    rm = np.sqrt(np.mean(music ** 2)) + 1e-9; rb = np.sqrt(np.mean(b ** 2)) + 1e-9
    return music + b * (rm / rb) * 10 ** (rel_db / 20)

def hall(x, room=0.92, wet=0.38, dark_db=-6.0):
    board = Pedalboard([LowShelfFilter(cutoff_frequency_hz=120, gain_db=1.5), HighShelfFilter(cutoff_frequency_hz=6000, gain_db=dark_db),
                        Reverb(room_size=room, damping=0.6, wet_level=wet, dry_level=0.7, width=1.0),
                        Compressor(threshold_db=-20, ratio=2.0, attack_ms=40, release_ms=400)])
    return board(x.T.astype(np.float32), SR).T

def finish(name, x, lufs=-20.0, loop=False, fade_in=1.5, fade_out=4.0):
    n = len(x)
    if loop:   # crossfade the tail into the head
        xf = int(4.0 * SR); a = np.linspace(0, 1, xf)[:, None]
        y = x[:-xf].copy(); y[:xf] = y[:xf] * a + x[-xf:] * (1 - a); x = y
    else:
        fi = int(fade_in * SR); fo = int(fade_out * SR)
        x[:fi] *= np.linspace(0, 1, fi)[:, None]; x[-fo:] *= np.linspace(1, 0, fo)[:, None]
    meter = pyln.Meter(SR)
    x = pyln.normalize.loudness(x, meter.integrated_loudness(x), lufs)
    peak = np.max(np.abs(x))
    if peak > 0.89: x *= 0.89 / peak
    # long OGG writes crash libsndfile here: write a WAV and let ffmpeg encode Vorbis
    with tempfile.TemporaryDirectory() as d:
        w = os.path.join(d, 'x.wav'); sf.write(w, x.astype(np.float32), SR, subtype='FLOAT')
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', w, '-c:a', 'libvorbis', '-q:a', '5', os.path.join(OUT, name + '.ogg')], check=True)
    print(name, round(len(x) / SR, 1), 's', round(meter.integrated_loudness(x), 1), 'LUFS', 'peak', round(float(np.max(np.abs(x))), 2))
    try:
        import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
        fig, ax = plt.subplots(2, 1, figsize=(11, 5))
        ax[0].specgram(x[:, 0], NFFT=4096, Fs=SR, noverlap=2048, cmap='magma'); ax[0].set_ylim(0, 6000); ax[0].set_title(name + ': spectrogram (0-6 kHz)')
        ax[1].plot(np.arange(len(x)) / SR, x[:, 0], lw=0.2, color='#334'); ax[1].set_xlabel('s'); ax[1].set_title('waveform')
        plt.tight_layout(); plt.savefig(os.path.join(PREV, 'm6_score_' + name + '.png'), dpi=70); plt.close(fig)
    except Exception as e: print('no preview', e)

def deg(d, octave=4, scale=D_DORIAN):
    """Scale degree (may be negative or > 6) to a MIDI pitch in D."""
    o, k = divmod(d, 7)
    return 62 + 12 * (octave - 4 + o) + scale[k]
def semis(s, octave=4): return 62 + 12 * (octave - 4) + s

def motif(song, name, prog, beat, octave, vel, scale_steps=NEMO, stretch=1.0, chromatic=True):
    b = beat
    for s, d in scale_steps:
        p = semis(s, octave) if chromatic else deg(s, octave)
        song.note(name, prog, b, d * stretch * 0.98, p, vel); b += d * stretch
    return b

# --------------------------------------------------------------------------------------------- title
def cue_title():
    """The Nautilus at rest (title screen, ~2:00, loops): drone on D, harp and celesta like light on the water,
    the solo violin states Nemo's motif twice, aleatoric string clusters swell and fade beneath."""
    rng = np.random.default_rng(1); S = Song(54); L = 108
    for b in range(0, L, 12):                                  # bass pedal
        S.note('bass', GM['contrabass'], b, 11.5, semis(0, 2), 60)
    S.swell('bass', GM['contrabass'], 0, L, 70, 80)
    for b in np.arange(4, L - 4, 3.0):                         # harp: broken D Dorian figures, sparse
        if rng.random() < 0.6:
            for k, d in enumerate(rng.choice([[0, 4, 7, 9], [2, 4, 9, 11], [-2, 2, 4, 9]])):
                S.note('harp', GM['harp'], b + k * 0.33, 2.5, deg(int(d), 4), int(38 + rng.integers(0, 14)))
    for b in np.arange(8, L, 5.5):                             # celesta glints
        if rng.random() < 0.5: S.note('cel', GM['celesta'], b, 1.5, deg(int(rng.choice([7, 9, 11, 12, 14])), 5), int(30 + rng.integers(0, 12)))
    # aleatoric clusters: each player enters at their own time, quiet, a cluster around A
    for k in range(10):
        t0 = 20 + rng.uniform(0, 12); p = semis(7 + int(rng.integers(-3, 4)), 4 if k % 2 else 3)
        S.note('clus', GM['slow_strings'], t0, 26 - (t0 - 20), p, 40)
    S.swell('clus', GM['slow_strings'], 18, 34, 20, 85); S.swell('clus', GM['slow_strings'], 34, 46, 85, 0)
    motif(S, 'vln', GM['violin'], 46, 5, 70, stretch=1.6)
    S.swell('vln', GM['violin'], 46, 60, 60, 100)
    motif(S, 'vln', GM['violin'], 76, 5, 64, [(0, 1.0), (7, 2.0), (8, 0.5), (7, 0.5), (5, 1.0), (3, 1.0), (2, 3.0)], stretch=1.6)
    for b in (62, 74, 86):
        for p in (semis(0, 3), semis(7, 3), semis(3, 4), semis(10, 4)):
            S.note('pad', GM['pad_bowed'], b, 11.5, p, 34)
    x = render(S, L * 60 / S.bpm + 4)
    x = mix(x, bed(len(x) / SR, 73.42, 11), -9.0)
    finish('title', hall(x), -21.0, loop=True)

# --------------------------------------------------------------------------------------------- Mission I
def cue_m1_wonder():
    """The forest of Crespo and the coral kingdom (~2:20, loops): warm, slow, open fifths; the harp turning like light
    through the water; a 1940s clarinet answers the violin; colour where the light is (GUM: vibrant, not bleak)."""
    rng = np.random.default_rng(2); S = Song(66); L = 152
    chords = [[0, 7, 14, 16], [-4, 3, 10, 12], [-2, 5, 12, 14], [-5, 2, 9, 12]]   # Dm(add9)  Bb  C  G/D-ish, in semitones from D
    for i, b in enumerate(range(0, L, 8)):
        c = chords[(i // 1) % len(chords)]
        for k, s in enumerate(c):
            S.note('str', GM['strings'], b, 7.8, semis(s, 3 if k == 0 else 4), 52 if k else 58)
        S.note('cb', GM['contrabass'], b, 7.8, semis(c[0], 2), 58)
        for k in range(8):                                         # harp, rising and falling like a shimmer
            s = c[(k * 2 + (k // 4)) % len(c)] + (12 if k > 3 else 0)
            S.note('harp', GM['harp'], b + k * 0.5 + 0.25, 1.8, semis(s, 4), int(42 + 10 * np.sin(k)))
    S.swell('str', GM['strings'], 0, 16, 40, 90); S.swell('str', GM['strings'], 120, L, 90, 60)
    # the violin's line, the clarinet's answer (original)
    vl = [(9, 2), (7, 1), (5, 1), (7, 3), (2, 1), (5, 2), (4, 1), (2, 1), (0, 4)]
    cl = [(2, 1), (4, 1), (5, 2), (9, 2), (7, 4), (5, 1), (4, 1), (2, 4)]
    motif(S, 'vln', GM['violin'], 32, 5, 72, [(s, d) for s, d in vl], chromatic=False)
    motif(S, 'cl', GM['clarinet'], 50, 4, 66, [(s, d) for s, d in cl], chromatic=False)
    motif(S, 'vln', GM['violin'], 80, 5, 76, NEMO, stretch=1.4)
    motif(S, 'cl', GM['clarinet'], 100, 4, 62, [(s, d) for s, d in vl], chromatic=False)
    for b in np.arange(24, L - 8, 4.0):
        if rng.random() < 0.45: S.note('glk', GM['vibes'], b + rng.uniform(0, 1), 2, deg(int(rng.choice([7, 9, 11, 14])), 5), 34)
    x = render(S, L * 60 / S.bpm + 4)
    x = mix(x, bed(len(x) / SR, 73.42, 21, air=0.3), -14.0)
    finish('m1_wonder', hall(x, room=0.85, wet=0.33, dark_db=-4.0), -21.0, loop=True)

# --------------------------------------------------------------------------------------------- the burial
def cue_burial():
    """I.XXIV (~1:50, one shot, timed to BurialRite): the strokes of the pickaxe in silence, then a string chorale in
    D minor with a low choir, Nemo's motif in the cellos at the kneeling, and the adieu: the high strings alone."""
    S = Song(48)
    prog = [[0, 7, 15, 19], [-2, 5, 14, 17], [-4, 3, 12, 15], [-5, 2, 10, 14], [-7, 5, 12, 17], [-5, 2, 11, 14], [0, 7, 12, 15], [0, 7, 12, 15]]
    b = 8                                                       # 10 s of silence and drone for the digging
    for i, c in enumerate(prog * 2):
        for k, s in enumerate(c):
            S.note('ch', GM['slow_strings'], b, 3.9, semis(s, 3 if k == 0 else 4), 58)
            if i >= 4 and k > 0: S.note('choir', GM['choir'], b, 3.9, semis(s, 3), 46)
        S.note('cb', GM['contrabass'], b, 3.9, semis(c[0], 2), 54)
        b += 4
    S.swell('ch', GM['slow_strings'], 8, 24, 20, 90); S.swell('ch', GM['slow_strings'], 56, 72, 90, 55)
    S.swell('choir', GM['choir'], 24, 40, 30, 80)
    motif(S, 'vc', GM['cello'], 40, 3, 78, stretch=2.0)            # the kneeling
    # the adieu: high strings alone, a held D and A, then the motif's first three notes, unresolved
    for p in (semis(0, 5), semis(7, 5), semis(12, 5)):
        S.note('hi', GM['strings'], 74, 10, p, 50)
    motif(S, 'hi', GM['violin'], 76, 5, 58, NEMO[:3], stretch=2.2)
    S.swell('hi', GM['strings'], 74, 86, 70, 0)
    x = render(S, 86 * 60 / S.bpm + 6)
    x = mix(x, bed(len(x) / SR, 73.42 / 2, 31, air=0.1, dark=1.3), -10.0)
    finish('burial', hall(x, room=0.95, wet=0.42, dark_db=-7.0), -22.0, loop=False, fade_in=2.0, fade_out=8.0)

CUES = dict(title=cue_title, m1_wonder=cue_m1_wonder, burial=cue_burial)
if __name__ == '__main__':
    for name in (sys.argv[1:] or list(CUES)): CUES[name]()
