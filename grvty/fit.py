"""Find ordinary slider values that recreate an AI grade as closely as possible,
so an AI look can be saved as a normal, editable Lightroom preset."""
import copy

import numpy as np

from . import engine
from .params import HUES, merge

# (path, step, lo, hi)
KNOBS = [("exposure", 0.4, -3, 3), ("contrast", 25, -100, 100), ("highlights", 30, -100, 100),
         ("shadows", 30, -100, 100), ("whites", 25, -100, 100), ("blacks", 25, -100, 100),
         ("temp", 25, -100, 100), ("tint", 20, -100, 100), ("saturation", 25, -100, 100),
         ("vibrance", 25, -100, 100)] + \
        [(f"hsl_sat.{h}", 30, -100, 100) for h in HUES] + [(f"hsl_lum.{h}", 30, -100, 100) for h in HUES]


def _get(p, path):
    a, *b = path.split(".")
    return p[a][b[0]] if b else p[a]


def _set(p, path, v):
    a, *b = path.split(".")
    if b:
        p[a][b[0]] = v
    else:
        p[a] = v


def fit(lin_small, target, is_raw, start=None, passes=5):
    """lin_small: small linear photo; target: the AI result for it (display 0..1)."""
    p = merge(start or {})
    p["ai"] = None
    def err(q):
        return float(((engine.render(lin_small, q, is_raw) - target) ** 2).mean())
    best = err(p)
    steps = {k[0]: k[1] for k in KNOBS}
    for _ in range(passes):
        improved = False
        for path, _, lo, hi in KNOBS:
            for sign in (1, -1):
                q = copy.deepcopy(p)
                v = max(lo, min(hi, _get(q, path) + sign * steps[path]))
                _set(q, path, round(v, 2) if path == "exposure" else round(v))
                e = err(q)
                if e < best - 1e-7:
                    p, best, improved = q, e, True
                    break
        for k in steps:
            steps[k] *= 0.6
        if not improved and max(steps.values()) < 2:
            break
    return p, best
