"""Every adjustment Grvty knows about.

Names and ranges follow Lightroom's own controls, so a set of values here
maps 1:1 onto a Lightroom preset later (stage 3).
"""
import copy

HUES = ["red", "orange", "yellow", "green", "aqua", "blue", "purple", "magenta"]
# Lightroom's colour-band centres, in degrees
HUE_CENTRES = [0, 30, 60, 120, 180, 240, 270, 300]

DEFAULTS = {
    # Light
    "exposure": 0.0,      # EV, -5..5
    "contrast": 0,        # -100..100
    "highlights": 0,
    "shadows": 0,
    "whites": 0,
    "blacks": 0,
    # Colour
    "temp": 0,            # -100 (cool) .. 100 (warm)
    "tint": 0,            # -100 (green) .. 100 (magenta)
    "vibrance": 0,
    "saturation": 0,
    # Presence
    "texture": 0,
    "clarity": 0,
    # Colour mixer (HSL), one value per hue band, -100..100
    "hsl_hue": {h: 0 for h in HUES},
    "hsl_sat": {h: 0 for h in HUES},
    "hsl_lum": {h: 0 for h in HUES},
    # Black & white
    "bw": False,
    "bw_mix": {h: 0 for h in HUES},
    # Colour grading: hue 0..360, sat 0..100, lum -100..100
    "grade": {
        "shadows": {"hue": 0, "sat": 0, "lum": 0},
        "midtones": {"hue": 0, "sat": 0, "lum": 0},
        "highlights": {"hue": 0, "sat": 0, "lum": 0},
        "global": {"hue": 0, "sat": 0, "lum": 0},
        "blending": 50,   # 0..100
        "balance": 0,     # -100..100
    },
    # Point curve, (input, output) pairs 0..255
    "curve": [[0, 0], [255, 255]],
    # Effects
    "vignette": 0,        # -100..100
    "vignette_mid": 50,   # 0..100
    "vignette_feather": 50,
    "grain": 0,           # 0..100
    "grain_size": 25,     # 0..100
}

# Slider ranges (used by the UI and to clamp values coming from the AI later)
RANGES = {
    "exposure": (-5, 5), "contrast": (-100, 100), "highlights": (-100, 100),
    "shadows": (-100, 100), "whites": (-100, 100), "blacks": (-100, 100),
    "temp": (-100, 100), "tint": (-100, 100), "vibrance": (-100, 100),
    "saturation": (-100, 100), "texture": (-100, 100), "clarity": (-100, 100),
    "vignette": (-100, 100), "vignette_mid": (0, 100), "vignette_feather": (0, 100),
    "grain": (0, 100), "grain_size": (0, 100),
}


def defaults():
    return copy.deepcopy(DEFAULTS)


def merge(params):
    """Fill in anything missing with defaults and clamp to valid ranges."""
    out = defaults()

    def _merge(dst, src):
        for k, v in (src or {}).items():
            if k not in dst:
                continue
            if isinstance(dst[k], dict) and isinstance(v, dict):
                _merge(dst[k], v)
            else:
                dst[k] = v

    _merge(out, params)
    for k, (lo, hi) in RANGES.items():
        try:
            out[k] = max(lo, min(hi, float(out[k])))
        except (TypeError, ValueError):
            out[k] = DEFAULTS[k]
    for group in ("hsl_hue", "hsl_sat", "hsl_lum", "bw_mix"):
        for h in HUES:
            out[group][h] = max(-100, min(100, float(out[group][h])))
    out["bw"] = bool(out["bw"])
    pts = sorted((max(0, min(255, float(a))), max(0, min(255, float(b))))
                 for a, b in out["curve"] or [[0, 0], [255, 255]])
    out["curve"] = [list(p) for p in pts] if len(pts) >= 2 else [[0, 0], [255, 255]]
    return out


def is_default(params):
    return merge(params) == DEFAULTS
