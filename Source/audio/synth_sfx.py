#!/usr/bin/env python3
"""Procedural sound effects for the M1 build (footsteps, controls, flooding cell).
Physically motivated recipes: modal resonances for struck iron, filtered noise for sand,
Minnaert-frequency bubbles for the gurgle. Writes OGG Vorbis into the Unity Resources folder.
Run: python3 synth_sfx.py <out_dir>   (default: the project's Assets/Verne/Resources/VerneAudio)"""
import os, sys
import numpy as np
import soundfile as sf
from scipy import signal

SR = 44100
rng = np.random.default_rng(1871)
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), '../../Unity/TwentyThousandLeagues/Assets/Verne/Resources/VerneAudio')

def t(d): return np.arange(int(SR * d)) / SR
def env(n, a=0.002, d=0.2):
    x = np.arange(n) / SR
    return np.minimum(1, x / a) * np.exp(-x / d)
def bp(x, lo, hi, order=2):
    sos = signal.butter(order, [lo, hi], 'bandpass', fs=SR, output='sos'); return signal.sosfilt(sos, x)
def lp(x, f, order=2):
    sos = signal.butter(order, f, 'lowpass', fs=SR, output='sos'); return signal.sosfilt(sos, x)
def hp(x, f, order=2):
    sos = signal.butter(order, f, 'highpass', fs=SR, output='sos'); return signal.sosfilt(sos, x)
def norm(x, peak=0.8):
    m = np.max(np.abs(x)) + 1e-9; return (x / m * peak).astype(np.float32)
def save(name, x, peak=0.8):
    p = os.path.join(OUT, name + '.ogg'); os.makedirs(os.path.dirname(p), exist_ok=True)
    sf.write(p, norm(x, peak), SR, format='OGG', subtype='VORBIS'); return p

def modal(freqs, decays, amps, dur):
    tt = t(dur); y = np.zeros_like(tt)
    for f, d, a in zip(freqs, decays, amps):
        y += a * np.sin(2 * np.pi * f * tt + rng.uniform(0, 6.28)) * np.exp(-tt / d)
    return y

def step(kind, i):
    dur = 0.45
    n = int(SR * dur)
    if kind == 'iron':        # boot on riveted plate: thump + ringing plate modes
        thump = lp(rng.normal(0, 1, n), 180) * env(n, 0.002, 0.03) * 3
        base = rng.uniform(310, 360)
        ring = modal([base, base * 1.59, base * 2.14, base * 2.9, base * 3.7], [0.12, 0.08, 0.06, 0.04, 0.03], [0.5, 0.35, 0.25, 0.15, 0.1], dur)
        click = hp(rng.normal(0, 1, n), 2500) * env(n, 0.0005, 0.006) * 0.4
        y = thump + ring * 0.35 + click
    elif kind == 'wood':
        thump = lp(rng.normal(0, 1, n), 300) * env(n, 0.002, 0.035) * 3
        body = modal([rng.uniform(140, 170), rng.uniform(410, 470)], [0.05, 0.03], [0.5, 0.3], dur)
        y = thump + body * 0.6 + hp(rng.normal(0, 1, n), 1500) * env(n, 0.001, 0.01) * 0.3
    elif kind == 'carpet':
        y = lp(rng.normal(0, 1, n), 400) * env(n, 0.006, 0.05) * 2 + bp(rng.normal(0, 1, n), 800, 3000) * env(n, 0.01, 0.04) * 0.25
    elif kind == 'marble':
        y = lp(rng.normal(0, 1, n), 250) * env(n, 0.002, 0.03) * 2 + hp(rng.normal(0, 1, n), 3000) * env(n, 0.0005, 0.008) * 0.6
    elif kind == 'sand':      # lead sole on sand under water: dull pressure thud felt more than heard, a short hiss of grains
        thud = lp(rng.normal(0, 1, n), 120, 4) * env(n, 0.012, 0.09) * 4
        grains = bp(rng.normal(0, 1, n), 600, 2400) * env(n, 0.03, 0.12) * 0.25
        y = thud + lp(grains, 1800)
    elif kind == 'rock':
        thud = lp(rng.normal(0, 1, n), 160, 4) * env(n, 0.006, 0.07) * 4
        scrape = bp(rng.normal(0, 1, n), 300, 1500) * env(n, 0.01, 0.05) * 0.4
        y = thud + scrape
    elif kind == 'weed':
        y = lp(rng.normal(0, 1, n), 140, 4) * env(n, 0.02, 0.1) * 3 + bp(rng.normal(0, 1, n), 200, 800) * env(n, 0.04, 0.15) * 0.3
    elif kind == 'ladder':
        base = rng.uniform(600, 700)
        y = modal([base, base * 2.7, base * 5.1], [0.15, 0.08, 0.04], [0.6, 0.3, 0.15], dur) * env(n, 0.001, 0.2) + lp(rng.normal(0, 1, n), 300) * env(n, 0.002, 0.02) * 2
    return y

def main():
    for kind in ['iron', 'wood', 'carpet', 'marble', 'sand', 'rock', 'weed', 'ladder']:
        for i in range(4):
            save(f'steps/{kind}_{i}', step(kind, i), 0.7)
    # controls
    n = int(SR * 0.6)
    clunk = lp(rng.normal(0, 1, n), 220) * env(n, 0.002, 0.05) * 3 + modal([180, 410, 870, 1430], [0.2, 0.1, 0.06, 0.04], [0.6, 0.4, 0.2, 0.1], 0.6) * 0.5
    save('sfx/lever_clunk', clunk, 0.75)
    n = int(SR * 0.5)
    tt = t(0.5); f = 900 + 500 * np.sin(2 * np.pi * 3 * tt)
    squeak = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.05, 0.25) * (0.5 + 0.5 * np.sin(2 * np.pi * 37 * tt))
    save('sfx/valve_squeak', bp(squeak + 0.05 * rng.normal(0, 1, n), 500, 3000), 0.4)
    n = int(SR * 0.12)
    save('sfx/button_click', hp(rng.normal(0, 1, n), 2000) * env(n, 0.0005, 0.01) + modal([2400, 3900], [0.02, 0.01], [0.4, 0.2], 0.12), 0.5)
    n = int(SR * 0.08)
    save('ui/tick', modal([1800], [0.012], [1], 0.08) * env(n, 0.0005, 0.02) + hp(rng.normal(0, 1, n), 4000) * env(n, 0.0002, 0.004) * 0.3, 0.35)
    # door open/close (heavy, hermetic)
    n = int(SR * 1.2)
    door = lp(rng.normal(0, 1, n), 200) * env(n, 0.003, 0.08) * 3 + modal([95, 230, 515], [0.5, 0.25, 0.12], [0.7, 0.4, 0.2], 1.2) * 0.6
    save('sfx/door_close', door, 0.8)
    n = int(SR * 0.9)
    creak = bp(rng.normal(0, 1, n), 200, 900) * (0.5 + 0.5 * np.sin(2 * np.pi * 11 * t(0.9))) * env(n, 0.1, 0.4)
    save('sfx/door_open', creak, 0.5)
    save('sfx/door_locked', modal([140, 330], [0.08, 0.05], [0.6, 0.3], 0.4) + lp(rng.normal(0, 1, int(SR * 0.4)), 300) * env(int(SR * 0.4), 0.001, 0.03), 0.6)
    # flooding cell loops (seamless: crossfade the tail into the head)
    def loop(x, xf=0.25):
        k = int(SR * xf); a = x[:k]; b = x[-k:]; w = np.linspace(0, 1, k)
        y = x[k:-k].copy(); y = np.concatenate([b * (1 - w) + a * w, y]); return y
    d = 6.0; n = int(SR * d)
    hiss = hp(rng.normal(0, 1, n), 1800) * 0.6 + bp(rng.normal(0, 1, n), 300, 1200) * 0.4
    hiss *= 1 + 0.15 * lp(rng.normal(0, 1, n), 3)
    save('loops/cell_hiss', loop(hiss), 0.5)
    # gurgle: Minnaert bubbles f = 3.26 / r (r in m) → 1–5 mm bubbles ring at 650 Hz – 3.3 kHz
    g = np.zeros(n)
    for _ in range(420):
        r = rng.uniform(0.001, 0.006); f0 = 3.26 / r
        s = int(rng.uniform(0, n - SR * 0.1)); L = int(SR * 0.08); tt = np.arange(L) / SR
        chirp = np.sin(2 * np.pi * f0 * tt * (1 + 0.8 * tt / 0.08)) * np.exp(-tt / (0.01 + r * 3))
        g[s:s + L] += chirp * rng.uniform(0.2, 1)
    g = lp(g, 3500) + lp(rng.normal(0, 1, n), 200) * 0.3
    save('loops/cell_gurgle', loop(g), 0.6)
    n = int(SR * 4)
    rumble = lp(rng.normal(0, 1, n), 90, 4) * 3 + bp(rng.normal(0, 1, n), 150, 400) * 0.2
    save('loops/panel_rumble', loop(rumble), 0.6)
    print('written to', os.path.abspath(OUT))

if __name__ == '__main__':
    main()
