"""Turning words into looks, and looks into variations.

Words are understood with two hand-made tables (no model, offline, instant):
  * VOCAB below: photographers' words (moody, faded, split tone...), added together;
  * library.LOOKS: ~200 named looks (films, Indian cinema, photographers, film
    stocks, Instagram aesthetics, moods), matched by name, alias or keyword.
Typos are forgiven ("ghotam" finds Gotham), and when nothing matches exactly the
closest look is used rather than nothing.
"""
import copy
import difflib
import json
import random
import re
import unicodedata
from pathlib import Path

from . import library
from .params import HUES, defaults, merge

# ------------------------------------------------------------------ vocabulary
# Each entry: list of trigger phrases -> partial settings. Settings are added
# together, so "moody warm faded" combines three entries.
VOCAB = [
    (["black and white", "black & white", "b&w", "bnw", "monochrome", "mono", "noir", "greyscale", "grayscale"],
     {"bw": True}),
    (["moody", "dark", "low key", "low-key", "lowkey", "brooding", "shadowy"],
     {"exposure": -0.3, "contrast": 25, "blacks": -30, "shadows": -15, "vignette": -25}),
    (["bright", "airy", "high key", "high-key", "light and airy", "clean"],
     {"exposure": 0.4, "shadows": 30, "contrast": -10, "blacks": 10, "highlights": -10}),
    (["warm", "golden", "sunset", "amber", "golden hour", "sunlit", "honey"],
     {"temp": 35, "grade": {"highlights": {"hue": 42, "sat": 25}}}),
    (["cool", "cold", "icy", "blue hour", "winter", "night"],
     {"temp": -30, "grade": {"shadows": {"hue": 220, "sat": 22}}}),
    (["sepia", "brown tone", "toned", "antique", "old photo"],
     {"grade": {"highlights": {"hue": 36, "sat": 40}, "shadows": {"hue": 28, "sat": 22}}, "saturation": -30}),
    (["split tone", "split-tone", "split toned", "split"],
     {"grade": {"highlights": {"hue": 40, "sat": 30}, "shadows": {"hue": 215, "sat": 25}}}),
    (["teal and orange", "teal & orange", "teal orange", "cinematic", "blockbuster"],
     {"contrast": 20, "grade": {"shadows": {"hue": 190, "sat": 38}, "highlights": {"hue": 32, "sat": 32}}, "vibrance": 10}),
    (["faded", "matte", "washed", "film", "vintage", "retro", "analog", "analogue", "kodak", "portra"],
     {"curve": [[0, 34], [64, 70], [192, 196], [255, 242]], "contrast": -8, "saturation": -15, "grain": 18}),
    (["grain", "grainy", "gritty", "texture", "noise"], {"grain": 35, "grain_size": 35}),
    (["crushed blacks", "crushed", "deep blacks", "inky", "ink", "rich blacks"], {"blacks": -55, "shadows": -10}),
    (["contrast", "contrasty", "punchy", "bold", "dramatic", "hard"], {"contrast": 40, "clarity": 18}),
    (["soft", "dreamy", "gentle", "hazy", "pastel", "delicate"],
     {"contrast": -22, "clarity": -20, "highlights": -20, "texture": -10}),
    (["red", "crimson", "red light", "red room"],
     {"hsl_sat": {"red": 35, "orange": 15}, "grade": {"global": {"hue": 4, "sat": 28}}}),
    (["green", "forest", "emerald"], {"hsl_sat": {"green": 20}, "hsl_hue": {"yellow": 15}}),
    (["muted", "desaturated", "subdued", "earthy", "understated"], {"saturation": -30, "vibrance": -15}),
    (["vibrant", "saturated", "colourful", "colorful", "vivid", "pop"], {"vibrance": 30, "saturation": 10}),
    (["vignette", "dark corners", "tunnel"], {"vignette": -40}),
    (["portrait", "skin", "face", "skin tones"],
     {"hsl_lum": {"orange": 15}, "hsl_sat": {"orange": -8}, "texture": -8}),
    (["clarity", "crisp", "sharp", "detailed", "structure"], {"clarity": 30, "texture": 20}),
    (["highlights soft", "protect highlights", "recover highlights", "save highlights"], {"highlights": -50}),
    (["open shadows", "lift shadows", "lifted shadows", "shadow detail"], {"shadows": 40}),
    (["lifted blacks", "lift blacks", "faded blacks"], {"curve": [[0, 32], [255, 255]]}),
    (["street", "documentary", "gritty street"], {"contrast": 30, "clarity": 25, "saturation": -20, "grain": 20}),
    (["magenta", "pink", "rose"], {"tint": 18, "grade": {"highlights": {"hue": 330, "sat": 18}}}),
    (["purple", "violet", "plum"], {"grade": {"shadows": {"hue": 280, "sat": 25}}}),
    (["cyan", "cyanotype"], {"grade": {"global": {"hue": 200, "sat": 22}}}),
    (["festival", "festive", "celebration"], {"vibrance": 25, "temp": 10, "contrast": 15}),
    (["product", "commercial", "studio"], {"contrast": 18, "clarity": 12, "blacks": -15, "whites": 15}),
]
# "a little moody" halves it, "very moody" makes it stronger
SOFTEN = ["a little", "a bit", "slightly", "subtle", "subtly", "touch of", "hint of", "light", "mild", "gently", "some"]
STRONG = ["very", "extremely", "really", "super", "heavy", "heavily", "strong", "intense", "deep", "lots of", "so"]
NEGATE = ["no ", "not ", "without ", "less "]

# Starting points when the prompt is empty, chosen to match a moody
# mono/toned portrait photographer.
SIGNATURES = {
    "Ink mono": {"bw": True, "contrast": 60, "blacks": -55, "shadows": -15, "clarity": 30, "vignette": -40, "grain": 30},
    "Sepia split": {"bw": True, "contrast": 35, "grade": {"shadows": {"hue": 215, "sat": 22}, "highlights": {"hue": 38, "sat": 50}, "balance": 10},
                    "curve": [[0, 22], [64, 52], [192, 205], [255, 245]]},
    "Golden hour": {"temp": 50, "tint": 8, "vibrance": 25, "grade": {"highlights": {"hue": 45, "sat": 40}, "shadows": {"hue": 20, "sat": 20}}, "hsl_sat": {"blue": -45}, "vignette": -25},
    "Red room": {"exposure": -0.5, "contrast": 50, "blacks": -60, "hsl_sat": {"red": 40, "orange": 30}, "hsl_hue": {"orange": -40}, "grade": {"global": {"hue": 5, "sat": 35}}, "saturation": -20},
    "Faded film": {"contrast": -15, "saturation": -25, "curve": [[0, 40], [128, 128], [255, 230]], "grade": {"shadows": {"hue": 180, "sat": 15}, "highlights": {"hue": 40, "sat": 15}}, "grain": 25},
    "Teal & orange": {"contrast": 30, "temp": 10, "grade": {"shadows": {"hue": 190, "sat": 40}, "highlights": {"hue": 30, "sat": 35}}, "vibrance": 15},
    "High-key mono": {"bw": True, "exposure": 0.5, "contrast": 20, "highlights": 40, "shadows": 40, "blacks": 20},
    "Blue hour": {"temp": -40, "tint": 5, "contrast": 25, "exposure": -0.3, "saturation": -15, "grade": {"shadows": {"hue": 225, "sat": 30}}},
    "Hard mono": {"bw": True, "contrast": 70, "blacks": -80, "whites": 30, "clarity": 55, "vignette": -60},
    "Soft matte": {"temp": 30, "contrast": 20, "highlights": -40, "shadows": 25, "vibrance": -20, "curve": [[0, 18], [255, 250]], "grain": 15},
    "Brown tone": {"bw": True, "contrast": 40, "grade": {"global": {"hue": 28, "sat": 30}}, "grain": 20},
    "Muted moody": {"exposure": -0.2, "contrast": 45, "hsl_sat": {"green": -60, "blue": -40, "aqua": -50}, "hsl_lum": {"orange": 20}, "temp": 15},
    "Cyanotype": {"bw": True, "contrast": 50, "grade": {"shadows": {"hue": 200, "sat": 30}, "highlights": {"hue": 200, "sat": 10}}, "vignette": -30},
    "Punchy": {"temp": 15, "contrast": 55, "saturation": 20, "blacks": -30, "clarity": 20},
    "Pale": {"exposure": 0.3, "contrast": -20, "saturation": -40, "temp": -10, "curve": [[0, 30], [255, 240]]},
    "Plum split": {"bw": True, "contrast": 30, "grade": {"highlights": {"hue": 20, "sat": 35}, "shadows": {"hue": 280, "sat": 20}}, "grain": 40},
}

# Directions to explore when making variations: (name for more, name for less, change)
AXES = [
    ("Warmer", "Cooler", {"temp": 18}),
    ("More contrast", "Softer contrast", {"contrast": 18}),
    ("Deeper blacks", "Lifted blacks", {"blacks": -20}),
    ("Brighter", "Darker", {"exposure": 0.25}),
    ("More faded", "Less faded", {"curve_lift": 18}),
    ("More grain", "Cleaner", {"grain": 15}),
    ("Richer colour", "More muted", {"saturation": 14, "vibrance": 8}),
    ("Stronger toning", "Lighter toning", {"tone_sat": 12}),
    ("Open shadows", "Darker shadows", {"shadows": 20}),
    ("Heavier vignette", "Lighter vignette", {"vignette": -18}),
    ("Crisper", "Smoother", {"clarity": 15}),
    ("Rosier", "Greener", {"tint": 10}),
]
COLOUR_ONLY = {"Richer colour", "Rosier"}
# extra directions that only make sense in black & white
AXES_BW = [
    ("Warm toning", "Cool toning", {"tone_warm": 1}),
    ("Brighter skin", "Darker skin", {"bw_mix.orange": 18}),
    ("Darker skies", "Lighter skies", {"bw_mix.blue": -22}),
    ("Glowing greens", "Darker greens", {"bw_mix.green": 18}),
]


def _add(dst, src, scale=1.0):
    for k, v in src.items():
        if k == "bw":
            dst["bw"] = bool(v) if scale > 0 else False
        elif k == "curve":
            # keep the strongest lift / roll-off
            if scale > 0:
                dst["curve"] = _blend_curves(dst["curve"], v, min(1.0, scale))
        elif isinstance(v, dict):
            _add(dst[k], v, scale)
        elif k == "hue":
            dst[k] = v
        else:
            dst[k] = dst.get(k, 0) + v * scale


def _blend_curves(a, b, t):
    if a == [[0, 0], [255, 255]]:
        a = [[x, x] for x, _ in b]
    xs = sorted({p[0] for p in a} | {p[0] for p in b})
    def at(c, x):
        for (x0, y0), (x1, y1) in zip(c, c[1:]):
            if x0 <= x <= x1:
                return y0 + (y1 - y0) * (x - x0) / max(1e-6, x1 - x0)
        return c[-1][1]
    return [[x, round(at(a, x) * (1 - t) + at(b, x) * t)] for x in xs]


def norm(text):
    """Lower case, accents removed, punctuation to spaces ("Amélie" -> "amelie")."""
    t = unicodedata.normalize("NFKD", text.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9&]+", " ", t)).strip()


def _skeleton(word):
    """A rough sound-alike key so common misspellings collide: gotham/ghotam -> gotam."""
    w = re.sub(r"[^a-z]", "", word)
    if not w:
        return ""
    w = w[0] + re.sub(r"(?<=[^aeiou])h", "", w[1:])           # drop h after a consonant
    w = w[0] + re.sub(r"h(?=[^aeiou]|$)", "", w[1:])           # and before one
    w = w.replace("c", "k").replace("z", "s").replace("v", "w").replace("ph", "f")
    w = w[0] + w[1:].replace("y", "i")
    return re.sub(r"(.)\1+", r"\1", w)                         # collapse doubles


# words that carry no look of their own
FILLER = set("""vibe vibes vibey vibing aesthetic aesthetics style styled look looks looking like feel feels feeling
type kind of the a an and with in on at to for but or more less some make made it its give me my please grade
graded edit edited photo photos picture pictures pic pics image images colour color colours colors tone tones
mood moody-ish movie movies film-like inspired version want something bit lot just please this that these those
from as is be very really super so too much little slightly shadows highlights midtones blacks whites""".split())

# every phrase we can match: (phrase, kind, payload); kind is "look" (index into LOOKS) or "vocab" (settings)
_ENTRIES = []
for _i, _look in enumerate(library.LOOKS):
    for _a in {norm(_look["name"]), *(norm(a) for a in _look["aliases"])}:
        if _a:
            _ENTRIES.append((_a, "look", _i))
for _words, _settings in VOCAB:
    for _w in _words:
        _ENTRIES.append((norm(_w), "vocab", _settings))
_ENTRIES.sort(key=lambda e: -len(e[0]))  # longest first so "golden hour" beats "golden"
# one regex per phrase, compiled once ("warm" also catches "warmer", "warms")
_RX = [re.compile(r"(?<![a-z0-9])" + re.escape(e[0]) + (r"(?:s|es|er|est|ish|y)?" if len(e[0]) >= 4 else "")
                  + r"(?![a-z0-9])") for e in _ENTRIES]
_BY_LEN = {}
for _e in _ENTRIES:
    _BY_LEN.setdefault(len(_e[0].split()), []).append(_e)
_SKEL = {}
for _e in _ENTRIES:
    _SKEL.setdefault(" ".join(_skeleton(w) for w in _e[0].split()), _e)


def _strength(text, start):
    """'a little' halves a match, 'very' strengthens it, 'no'/'less' reverses it."""
    before = text[max(0, start - 14):start]
    scale = 1.0
    if any(w in before for w in SOFTEN):
        scale = 0.5
    if any(w in before for w in STRONG):
        scale = 1.6
    if any(before.endswith(w) or (" " + w) in before[-8:] for w in NEGATE):
        scale = -0.6
    return scale


_KNOWN = {e[0] for e in _ENTRIES if " " not in e[0]}


def _known(word):
    return word in _KNOWN or any(word.endswith(x) and word[:-len(x)] in _KNOWN for x in ("s", "es", "er", "est", "ish", "y"))


# multi-word names written as one word: "bladerunner", "darkacademia", "oldmoney"
_NOSPACE = {}
for _e in _ENTRIES:
    if " " in _e[0]:
        _NOSPACE.setdefault(_e[0].replace(" ", ""), _e)


def _fuzzy(phrase):
    """Best entry for a possibly misspelt phrase, or None."""
    if " " not in phrase and len(phrase) >= 5:
        if phrase in _NOSPACE:
            return _NOSPACE[phrase]
        close = difflib.get_close_matches(phrase, list(_NOSPACE), n=1, cutoff=0.86)
        if close:
            return _NOSPACE[close[0]]
    best = _fuzzy_raw(phrase)
    if best and " " in phrase:
        # a correctly spelt word we already know must stay itself ("sepia highlights" is not "save highlights")
        for w, c in zip(phrase.split(), best[0].split()):
            if w != c and _known(w):
                return None
    return best


def _fuzzy_raw(phrase):
    n = len(phrase.split())
    sk = " ".join(_skeleton(w) for w in phrase.split())
    if sk in _SKEL and len(_SKEL[sk][0].split()) == n and len(phrase.replace(" ", "")) >= 4:
        return _SKEL[sk]
    if len(phrase.replace(" ", "")) < 5:
        return None
    best, best_r = None, 0.0
    for e in _BY_LEN.get(n, []):
        if abs(len(e[0]) - len(phrase)) > 3:
            continue
        m = difflib.SequenceMatcher(None, phrase, e[0])
        if m.real_quick_ratio() < 0.82 or m.quick_ratio() < 0.82:
            continue
        r = m.ratio()
        if r > best_r:
            best, best_r = e, r
    return best if best_r >= 0.82 else None


def _closest_look(words):
    """Nothing matched at all: choose the named look whose keywords fit best."""
    words = [w for w in words if w not in FILLER and len(w) >= 3]
    if not words:
        return None
    best, best_s = None, 0.0
    for i, look in enumerate(library.LOOKS):
        keys = look["keys"]
        s = 0.0
        for w in words:
            if w in keys or w.rstrip("sy") in keys:
                s += 1.0
            else:
                r = max((difflib.SequenceMatcher(None, w, k).ratio() for k in keys), default=0)
                if r >= 0.8:
                    s += 0.8
        if s > best_s:
            best, best_s = i, s
    return best if best_s >= 0.8 else None


def parse_full(prompt):
    """Words -> (settings, matched words, names of the named looks found)."""
    text = norm(prompt)
    text = " " + re.sub(r"\b([a-z]{3,})i(?:er|est)\b", r"\1y", text) + " "   # moodier -> moody
    p = defaults()
    hits, names = [], []
    used = [False] * len(text)

    def apply(kind, payload, scale, label):
        if kind == "look":
            look = library.LOOKS[payload]
            _add(p, look["params"], scale)
            if scale > 0 and look["name"] not in names:
                names.append(look["name"])
        else:
            _add(p, payload, scale)
        hits.append(label)

    def exact(multi):
        for (phrase, kind, payload), rx in zip(_ENTRIES, _RX):
            if (" " in phrase) != multi or phrase not in text:
                continue
            for m in rx.finditer(text):
                if any(used[m.start():m.end()]):
                    continue
                for i in range(m.start(), m.end()):
                    used[i] = True
                apply(kind, payload, _strength(text, m.start()), phrase)

    def free_words():
        mods = {w.strip() for w in SOFTEN + STRONG + NEGATE}
        return [(m.group(), m.start(), m.end()) for m in re.finditer(r"[a-z0-9&]+", text)
                if not any(used[m.start():m.end()]) and m.group() not in FILLER and m.group() not in mods]

    def fuzzy(sizes):
        free = free_words()
        for n in sizes:
            for j in range(len(free) - n + 1):
                group = free[j:j + n]
                if any(used[g[1]] for g in group):
                    continue
                if any(text[a[2]:b[1]].strip() for a, b in zip(group, group[1:])):
                    continue  # only words that sit next to each other
                e = _fuzzy(" ".join(g[0] for g in group))
                if e and e[1] == "look":
                    # "bladerunner 2049": 2049 already found Blade Runner 2049, don't add the neon one too
                    found = {w for nm in names for w in norm(nm).split() if len(w) >= 4}
                    if found & {w for w in norm(library.LOOKS[e[2]]["name"]).split() if len(w) >= 4}:
                        for g in group:
                            for i in range(g[1], g[2]):
                                used[i] = True
                        continue
                if e:
                    for g in group:
                        for i in range(g[1], g[2]):
                            used[i] = True
                    apply(e[1], e[2], _strength(text, group[0][1]), e[0])

    exact(True)        # 1. names of two or more words ("dark academia", "golden hour")
    fuzzy((3, 2))      # 2. misspelt names of two or more words ("dark acadamia")
    exact(False)       # 3. single words ("gotham", "moody")
    fuzzy((1,))        # 4. misspelt single words ("ghotam", "bansali")
    if not hits:       # 5. still nothing: the closest named look by its keywords
        i = _closest_look([m.group() for m in re.finditer(r"[a-z0-9&]+", text)])
        if i is not None:
            apply("look", i, 1.0, library.LOOKS[i]["name"].lower())
    return merge(p), hits, names


def parse(prompt):
    """Words -> (settings, list of matched words)."""
    params, hits, _ = parse_full(prompt)
    return params, hits


# ------------------------------------------------------------------ variations

def _apply_axis(p, change, amount):
    q = copy.deepcopy(p)
    for k, v in change.items():
        if k == "curve_lift":
            pts = q["curve"]
            if pts == [[0, 0], [255, 255]]:
                pts = [[0, 0], [255, 255]]
            pts[0] = [0, max(0, min(80, pts[0][1] + v * amount))]
            pts[-1] = [255, max(180, min(255, pts[-1][1] - v * amount * 0.4))]
            q["curve"] = pts
        elif k.startswith("bw_mix."):
            h = k.split(".")[1]
            q["bw_mix"][h] = q["bw_mix"][h] + v * amount
        elif k == "tone_warm":
            g = q["grade"]
            if not any(g[z]["sat"] for z in ("shadows", "highlights", "global")):
                g["highlights"] = {"hue": 38 if amount > 0 else 210, "sat": 22 * abs(amount), "lum": 0}
            else:
                for z in ("shadows", "highlights", "global"):
                    if g[z]["sat"]:
                        g[z]["hue"] = (g[z]["hue"] + (-14 if amount > 0 else 14) * abs(amount)) % 360
        elif k == "tone_sat":
            for z in ("shadows", "highlights", "global"):
                if q["grade"][z]["sat"]:
                    q["grade"][z]["sat"] = max(0, min(100, q["grade"][z]["sat"] + v * amount))
        else:
            q[k] = q[k] + v * amount
    return merge(q)


def describe(p):
    """A short, human list of what a look does."""
    tags = []
    if p["bw"]:
        tags.append("Black & white")
    g = p["grade"]
    hue_name = lambda h: ["red", "orange", "gold", "yellow", "green", "teal", "cyan", "blue", "violet", "plum", "magenta", "rose"][int(((h + 15) % 360) // 30)]
    for z, label in (("highlights", "highlights"), ("shadows", "shadows"), ("global", "tone")):
        if g[z]["sat"] >= 8:
            tags.append(f"{hue_name(g[z]['hue']).capitalize()} {label}")
    def sign(v):
        return f"+{round(v)}" if v > 0 else f"{round(v)}"
    if abs(p["exposure"]) >= 0.15:
        tags.append(("Brighter " if p["exposure"] > 0 else "Darker ") + f"{p['exposure']:+.1f}")
    for k, name in (("contrast", "Contrast"), ("temp", "Warmth"), ("blacks", "Blacks"), ("shadows", "Shadows"),
                    ("highlights", "Highlights"), ("clarity", "Clarity"), ("grain", "Grain"), ("vignette", "Vignette")):
        if abs(p[k]) >= 12:
            tags.append(f"{name} {sign(p[k])}")
    if not p["bw"] and abs(p["saturation"]) >= 12:
        tags.append("Muted" if p["saturation"] < 0 else "Saturated")
    if p["curve"] and p["curve"][0][1] >= 15:
        tags.append("Faded blacks")
    if p["bw"] and any(abs(v) >= 12 for v in p["bw_mix"].values()):
        tags.append("Custom grey mix")
    return tags[:7]


class Taste:
    """Remembers which looks she picks and leans new ones gently towards them."""

    KEYS = ["exposure", "contrast", "highlights", "shadows", "whites", "blacks", "temp", "tint",
            "vibrance", "saturation", "clarity", "grain", "vignette"]

    def __init__(self, data_dir):
        self.path = Path(data_dir) / "taste.json"
        self.picks_log = Path(data_dir) / "picks.jsonl"
        try:
            self.state = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            self.state = {"n": 0, "mean": {k: 0.0 for k in self.KEYS}, "bw": 0.0}

    def record(self, prompt, params, rejected=()):
        p = merge(params)
        n = self.state["n"] = self.state["n"] + 1
        w = 1 / min(n, 30)  # running mean that keeps adapting
        for k in self.KEYS:
            self.state["mean"][k] += (p[k] - self.state["mean"][k]) * w
        self.state["bw"] += ((1.0 if p["bw"] else 0.0) - self.state["bw"]) * w
        self.path.write_text(json.dumps(self.state, indent=1), encoding="utf-8")
        with open(self.picks_log, "a", encoding="utf-8") as f:
            f.write(json.dumps({"prompt": prompt, "picked": p, "shown": len(rejected) + 1}) + "\n")

    def lean(self, p, strength=0.18):
        """Nudge a look a little towards her average taste (only once she's picked a few)."""
        if self.state["n"] < 3:
            return p
        q = copy.deepcopy(p)
        s = strength * min(1.0, self.state["n"] / 15)
        for k in self.KEYS:
            q[k] = q[k] + (self.state["mean"][k] - q[k]) * s * 0.5
        return merge(q)


def _axes_for(p):
    if p["bw"]:
        return [a for a in AXES if a[0] not in COLOUR_ONLY] + AXES_BW
    return AXES[:]


def scale_look(p, f):
    """Make a look stronger (f > 1) or gentler (f < 1) relative to neutral."""
    d = defaults()
    q = copy.deepcopy(p)
    for k, v in d.items():
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            q[k] = v + (p[k] - v) * f
    for grp in ("hsl_hue", "hsl_sat", "hsl_lum", "bw_mix"):
        for h in HUES:
            q[grp][h] = p[grp][h] * f
    for z in ("shadows", "midtones", "highlights", "global"):
        q["grade"][z]["sat"] = p["grade"][z]["sat"] * f
        q["grade"][z]["lum"] = p["grade"][z]["lum"] * f
    q["curve"] = [[x, round(x + (y - x) * f)] for x, y in p["curve"]]
    return merge(q)


def _variations(base, count, rng, lo, hi, prefix=""):
    axes = _axes_for(base)
    out = []
    order = axes[:]
    rng.shuffle(order)
    i = 0
    while len(out) < count:
        a, b = order[i % len(order)], order[(i * 5 + 3) % len(order)]
        if a is b:
            b = order[(i + 1) % len(order)]
        ma, mb = rng.random() < 0.5, rng.random() < 0.5
        p = _apply_axis(base, a[2], rng.uniform(lo, hi) * (1 if ma else -1))
        p = _apply_axis(p, b[2], rng.uniform(lo, hi) * 0.8 * (1 if mb else -1))
        name = (a[0] if ma else a[1]) + " · " + (b[0] if mb else b[1]).lower()
        out.append({"name": prefix + name, "params": p})
        i += 1
    return out


def generate(prompt, count, taste=None, seed=None):
    """A grid of looks for a prompt: the closest reading, a bolder and a gentler
    one, then clearly different variations around it."""
    rng = random.Random(seed)
    prompt = (prompt or "").strip()
    if not prompt:
        names = list(SIGNATURES)
        if taste and taste.state["bw"] > 0.6:
            names.sort(key=lambda n: (not SIGNATURES[n].get("bw"), rng.random()))
        else:
            rng.shuffle(names)
        looks = []
        for n in names[:count]:
            p = merge(SIGNATURES[n])
            looks.append({"name": n, "params": taste.lean(p) if taste else p})
        while len(looks) < count:  # more than the signature set: vary them
            src = rng.choice(looks[:len(SIGNATURES)])
            looks += _variations(src["params"], 1, rng, 1.0, 1.8, src["name"] + ", ")
        return [dict(l, tags=describe(l["params"])) for l in looks]

    base, hits, names = parse_full(prompt)
    if not hits:  # nothing recognised: fall back to the signature looks
        return generate("", count, taste, seed)
    if taste:
        base = taste.lean(base)
    looks = [{"name": " + ".join(names) if names else "Closest match", "params": base}]
    if count >= 4:
        looks.append({"name": "Bolder", "params": scale_look(base, 1.55)})
    if count >= 6:
        looks.append({"name": "Gentler", "params": scale_look(base, 0.55)})
    looks += _variations(base, count - len(looks), rng, 1.1, 2.0)
    return [dict(l, tags=describe(l["params"])) for l in looks]


def more_like(params, count, taste=None, seed=None):
    """Variations around a chosen look (the pick stays first). Close enough to
    feel related, far enough apart to choose between."""
    rng = random.Random(seed)
    base = merge(params)
    looks = [{"name": "Your pick", "params": base}]
    looks += _variations(base, count - 1, rng, 0.6, 1.15, "A touch: ")
    for l in looks[1:]:
        l["name"] = l["name"].replace("A touch: ", "")
    return [dict(l, tags=describe(l["params"])) for l in looks]
