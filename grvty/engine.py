"""Grvty's grading engine.

render(linear_image, params, is_raw) -> display-ready sRGB float image.

Order (close to Lightroom's):
  white balance -> exposure -> base tone (RAW only) -> highlights/shadows ->
  whites/blacks -> contrast -> point curve -> texture/clarity ->
  vibrance/saturation -> colour mixer OR black & white -> colour grading ->
  vignette -> grain

Every control is an exact no-op at its default value, so a JPEG with all
sliders at zero comes out unchanged.
"""
import cv2
import numpy as np

from .loader import linear_to_srgb
from .params import HUE_CENTRES, HUES, merge

LUMA = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
RAW_BASELINE_EV = 0.35


# ---------------------------------------------------------------- helpers

def luma(x):
    return x @ LUMA


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / max(e1 - e0, 1e-6), 0, 1)
    return t * t * (3 - 2 * t)


def blur(img, sigma_frac):
    """Gaussian blur with sigma given as a fraction of the long edge, done at
    reduced resolution so it's fast and looks the same at any image size."""
    h, w = img.shape[:2]
    long_edge = max(h, w)
    work = 512 if sigma_frac > 0.004 else 1600
    s = min(1.0, work / long_edge)
    small = cv2.resize(img, (max(1, int(w * s)), max(1, int(h * s))), interpolation=cv2.INTER_AREA) if s < 1 else img
    sig = max(0.5, sigma_frac * max(small.shape[:2]))
    out = cv2.GaussianBlur(small, (0, 0), sig)
    if s < 1:
        out = cv2.resize(out, (w, h), interpolation=cv2.INTER_LINEAR)
    return out


def monotone_curve_lut(points, n=1024):
    """Fritsch-Carlson monotone cubic through curve points (0..255)."""
    pts = np.array(points, dtype=np.float64) / 255.0
    x, y = pts[:, 0], pts[:, 1]
    keep = np.concatenate([[True], np.diff(x) > 1e-6])
    x, y = x[keep], y[keep]
    xs = np.linspace(0, 1, n)
    if len(x) == 2:
        return np.interp(xs, x, y).astype(np.float32)
    d = np.diff(y) / np.diff(x)
    m = np.zeros_like(y)
    m[1:-1] = (d[:-1] + d[1:]) / 2
    m[0], m[-1] = d[0], d[-1]
    for i in range(len(d)):
        if abs(d[i]) < 1e-9:
            m[i] = m[i + 1] = 0
        else:
            a, b = m[i] / d[i], m[i + 1] / d[i]
            s = a * a + b * b
            if s > 9:
                t = 3 / np.sqrt(s)
                m[i], m[i + 1] = t * a * d[i], t * b * d[i]
    idx = np.clip(np.searchsorted(x, xs) - 1, 0, len(x) - 2)
    h = x[idx + 1] - x[idx]
    t = (xs - x[idx]) / h
    h00, h10 = 2 * t**3 - 3 * t**2 + 1, t**3 - 2 * t**2 + t
    h01, h11 = -2 * t**3 + 3 * t**2, t**3 - t**2
    out = h00 * y[idx] + h10 * h * m[idx] + h01 * y[idx + 1] + h11 * h * m[idx + 1]
    out = np.where(xs < x[0], y[0], np.where(xs > x[-1], y[-1], out))
    return np.clip(out, 0, 1).astype(np.float32)


def apply_lut(x, lut, hi=1.0):
    """Look up every value of x in a table covering [0, hi] (nearest entry)."""
    n = len(lut) - 1
    idx = (x * (n / hi) + 0.5)
    np.clip(idx, 0, n, out=idx)
    return lut[idx.astype(np.int32)]


def hue_value_lut(values):
    """Table of a per-hue-band setting at every 0.1 degree, interpolated
    between Lightroom's band centres (wrapping round)."""
    xs = np.array(HUE_CENTRES + [360], dtype=np.float32)
    vs = np.array([values[h] for h in HUES] + [values[HUES[0]]], dtype=np.float32)
    return np.interp(np.arange(3601, dtype=np.float32) / 10, xs, vs).astype(np.float32)


def per_hue(hue_deg, values):
    return apply_lut(hue_deg, hue_value_lut(values), hi=360.0)


_PRE_CACHE = {}
PRE_HI = 8.0


def pre_lut(is_raw):
    """Linear light -> display values, as one table (RAW gets the base look)."""
    if is_raw not in _PRE_CACHE:
        xs = np.linspace(0, PRE_HI, 65537, dtype=np.float32)
        _PRE_CACHE[is_raw] = (_base_tone_raw_math(xs) if is_raw else linear_to_srgb(xs)).astype(np.float32)
    return _PRE_CACHE[is_raw]


def hue_vector(hue_deg):
    """A luminance-neutral RGB direction for a hue."""
    hsv = np.array([[[hue_deg % 360, 1.0, 1.0]]], dtype=np.float32)
    rgb = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)[0, 0]
    return rgb - float(rgb @ LUMA)


def soft_clip(x, knee=0.8):
    over = x > knee
    if not np.any(over):
        return x
    k = 1 - knee
    return np.where(over, knee + k * np.tanh((x - knee) / k), x).astype(np.float32)


# ---------------------------------------------------------------- stages

def white_balance(lin, temp, tint):
    if not temp and not tint:
        return lin
    t, g = temp / 100.0, tint / 100.0
    gains = np.array([2 ** (0.45 * t), 2 ** (-0.32 * g), 2 ** (-0.55 * t)], dtype=np.float32)
    gains /= float(gains @ LUMA)  # keep overall brightness steady
    return lin * gains


def _base_tone_raw_math(lin):
    """Turn scene-linear RAW data into a pleasant starting picture, similar in
    spirit to Lightroom's default rendering: highlight roll-off + mild S."""
    x = linear_to_srgb(soft_clip(lin, 0.7))
    s = 0.5 - 0.5 * np.cos(np.pi * x)
    return (x + 0.22 * (s - x)).astype(np.float32)


def tone_local(x, p):
    hl, sh = p["highlights"], p["shadows"]
    if hl or sh:
        y = luma(x)
        ym = 0.6 * blur(y, 0.02) + 0.4 * y
        g = np.zeros_like(y)
        if sh:
            g += (sh / 100.0) * 0.9 * (1 - smoothstep(0.0, 0.55, ym)) ** 1.5
        if hl:
            g += (hl / 100.0) * 0.75 * smoothstep(0.35, 1.0, ym) ** 1.5
        x = x * np.exp2(g)[..., None]
    return x


def point_lut(p, n=4096):
    """Whites, blacks, contrast and the point curve, folded into one table
    over [0, 1.5] (values above 1 come from highlight/shadow boosts)."""
    x = np.linspace(0, 1.5, n, dtype=np.float32)
    x = soft_clip(x, 0.85) if (p["highlights"] or p["shadows"]) else np.clip(x, 0, 1)
    return _point_math(x, p)


def _point_math(x, p):
    wh, bk, ct = p["whites"], p["blacks"], p["contrast"]
    if bk:
        k = bk / 100.0 * 0.10
        x = x + k * (1 - np.clip(x, 0, 1)) ** 4
    if wh:
        k = wh / 100.0 * 0.18
        x = x + k * np.clip(x, 0, 1) ** 4
    if wh or bk:
        x = soft_clip(np.maximum(x, 0), 0.9)
    if ct:
        c = ct / 100.0
        xc = np.clip(x, 0, 1)
        if c > 0:
            s = 0.5 - 0.5 * np.cos(np.pi * xc)
            x = xc + c * 0.75 * (s - xc)
        else:
            x = 0.5 + (xc - 0.5) * (1 + c * 0.5)
    x = np.clip(x, 0, 1).astype(np.float32)
    if p["curve"] != [[0, 0], [255, 255]]:
        cl = monotone_curve_lut(p["curve"], 4096)
        x = cl[(x * 4095 + 0.5).astype(np.int32)]
    return x


def presence(x, p):
    tx, cl = p["texture"], p["clarity"]
    if not tx and not cl:
        return x
    y = luma(x)
    mid = 4 * y * (1 - y)
    d = np.zeros_like(y)
    if cl:
        d += (cl / 100.0) * 0.9 * (y - blur(y, 0.015))
    if tx:
        d += (tx / 100.0) * 0.8 * (y - blur(y, 0.0025))
    return np.clip(x + (d * (0.35 + 0.65 * mid))[..., None], 0, 1).astype(np.float32)


def vib_sat(x, p):
    vib, sat = p["vibrance"], p["saturation"]
    if not vib and not sat:
        return x
    y = luma(x)[..., None]
    chroma = x - y
    f = np.full(y.shape, 1 + sat / 100.0, dtype=np.float32)
    if vib:
        r_, g_, b_ = x[..., 0], x[..., 1], x[..., 2]
        s = (np.maximum(np.maximum(r_, g_), b_) - np.minimum(np.minimum(r_, g_), b_))[..., None]
        w = 1 - np.clip(s, 0, 1)
        w = w * np.sqrt(w)
        if vib > 0:  # protect skin tones (orange-ish hues)
            hsv = cv2.cvtColor(np.clip(x, 0, 1), cv2.COLOR_RGB2HSV)
            skin = apply_lut(hsv[..., 0], np.exp(-((np.arange(3601) / 10 - 28) / 18) ** 2).astype(np.float32), 360.0)[..., None]
            w = w * (1 - 0.6 * skin)
        f = f * (1 + vib / 100.0 * 1.2 * w)
    return np.clip(y + chroma * f, 0, 1).astype(np.float32)


def colour_mixer(x, p):
    hh, ss, ll = p["hsl_hue"], p["hsl_sat"], p["hsl_lum"]
    if not any(hh.values()) and not any(ss.values()) and not any(ll.values()):
        return x
    hsv = cv2.cvtColor(np.clip(x, 0, 1), cv2.COLOR_RGB2HSV)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    h2, s2, v2 = h, s, v
    if any(hh.values()):
        h2 = np.mod(h + per_hue(h, hh) * 0.3, 360)
    if any(ss.values()):
        s2 = np.clip(s * (1 + per_hue(h, ss) / 100.0), 0, 1)
    if any(ll.values()):
        v2 = np.clip(v * np.exp2(per_hue(h, ll) / 100.0 * 0.9 * s), 0, 1)
    out = cv2.cvtColor(np.stack([h2, s2, v2], -1).astype(np.float32), cv2.COLOR_HSV2RGB)
    return out


def black_white(x, p):
    mix = p["bw_mix"]
    y = luma(x)
    if any(mix.values()):
        hsv = cv2.cvtColor(np.clip(x, 0, 1), cv2.COLOR_RGB2HSV)
        m = per_hue(hsv[..., 0], mix) / 100.0
        y = y * np.exp2(m * 1.4 * hsv[..., 1])
    y = np.clip(y, 0, 1)
    return np.repeat(y[..., None], 3, axis=-1).astype(np.float32)


def colour_grade(x, p):
    g = p["grade"]
    zones = ("shadows", "midtones", "highlights", "global")
    if not any(g[z]["sat"] or g[z]["lum"] for z in zones):
        return x
    y = luma(x)
    piv = 0.5 - 0.25 * g["balance"] / 100.0
    gam = 1.6 - 1.1 * g["blending"] / 100.0
    ws = np.clip(1 - y / piv, 0, 1) ** gam
    wh = np.clip((y - piv) / (1 - piv), 0, 1) ** gam
    wm = np.clip(1 - ws - wh, 0, 1) * (1 - np.abs(y - piv) * 0.8)
    W = np.stack([ws, wm, wh, np.ones_like(y)], -1)          # (H, W, 4)
    vecs = np.stack([hue_vector(g[z]["hue"]) * (g[z]["sat"] / 100.0) * 0.45 for z in zones])
    lums = np.array([g[z]["lum"] / 100.0 * 0.7 for z in zones], dtype=np.float32)
    if any(g[z]["sat"] for z in zones):
        x = x + W @ vecs.astype(np.float32)
    if lums.any():
        x = x * np.exp2(W @ lums)[..., None]
    return np.clip(x, 0, 1).astype(np.float32)


def vignette(x, p):
    amt = p["vignette"]
    if not amt:
        return x
    m = _vignette_mask(x.shape[0], x.shape[1], p["vignette_mid"], p["vignette_feather"])
    a = amt / 100.0
    if a < 0:
        x = x * (1 + a * 0.9 * m)
    else:
        x = x + (1 - x) * a * 0.85 * m
    return np.clip(x, 0, 1).astype(np.float32)


_VIG = {}


def _vignette_mask(h, w, mid, feather):
    key = (h, w, mid, feather)
    if key not in _VIG:
        if len(_VIG) > 8:
            _VIG.clear()
        nx = (np.arange(w, dtype=np.float32) - w / 2) / (w / 2)
        ny = (np.arange(h, dtype=np.float32) - h / 2) / (h / 2)
        r = np.sqrt((nx[None, :] ** 2 + ny[:, None] ** 2) / 2)  # 0 centre, 1 corner
        fea = 0.05 + 0.9 * feather / 100.0
        r0 = 0.15 + 0.65 * mid / 100.0
        _VIG[key] = smoothstep(r0 - fea * 0.3, r0 + fea * 0.7, r)[..., None].astype(np.float32)
    return _VIG[key]


def grain(x, p, seed=7):
    amt = p["grain"]
    if not amt:
        return x
    h, w = x.shape[:2]
    # grain size is relative to the image, so preview and export match
    cell = (0.0006 + 0.0024 * p["grain_size"] / 100.0) * max(h, w)
    gh, gw = max(2, int(h / cell)), max(2, int(w / cell))
    rng = np.random.default_rng(seed)
    n = rng.standard_normal((gh, gw)).astype(np.float32)
    n = cv2.resize(n, (w, h), interpolation=cv2.INTER_CUBIC)
    y = luma(x)
    strength = amt / 100.0 * 0.075 * np.sqrt(np.clip(1 - np.abs(2 * y - 1), 0, 1) + 0.05)
    return np.clip(x + (n * strength)[..., None], 0, 1).astype(np.float32)


# ---------------------------------------------------------------- main

def render(lin, params, is_raw=False):
    p = merge(params)
    x = white_balance(lin, p["temp"], p["tint"])
    ev = p["exposure"] + (RAW_BASELINE_EV if is_raw else 0)
    if ev:
        x = x * (2 ** ev)
    x = apply_lut(np.maximum(x, 0), pre_lut(is_raw), PRE_HI)
    x = tone_local(x, p)
    if any(p[k] for k in ("highlights", "shadows", "whites", "blacks", "contrast")) \
            or p["curve"] != [[0, 0], [255, 255]]:
        x = apply_lut(np.maximum(x, 0), point_lut(p), 1.5)
    x = presence(x, p)
    if p["bw"]:
        x = black_white(x, p)
    else:
        x = vib_sat(x, p)
        x = colour_mixer(x, p)
    x = colour_grade(x, p)
    x = vignette(x, p)
    x = grain(x, p)
    return np.clip(x, 0, 1).astype(np.float32)
