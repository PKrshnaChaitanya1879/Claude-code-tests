"""Local web server the Grvty window talks to. Only listens on 127.0.0.1."""
import hashlib
import json
import os
import re
import tempfile
import threading
import traceback
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import numpy as np

from . import engine, fit, loader, looks, xmp
from .ai import GradeAI
from .params import merge
from .params import DEFAULTS, RANGES, HUES

UI_DIR = Path(__file__).resolve().parent.parent / "ui"
DATA_DIR = Path(os.environ.get("APPDATA") or Path.home() / ".config") / "Grvty"
DATA_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS = DATA_DIR / "settings.json"
TASTE = looks.Taste(DATA_DIR)
AI = GradeAI()


def render_look(lin, params, is_raw, cache=None):
    """The engine, then the AI colour cube on top when the look has one."""
    img = engine.render(lin, params, is_raw, cache)
    w = (params or {}).get("ai")
    if w and AI.available():
        img = AI.apply(AI.cube(np.asarray(w, dtype=np.float32)), img)
    return img
GRID_EDGE = 560
PREVIEW_EDGE = 1600
DRAG_EDGE = 800
THUMB_EDGE = 320


KEEP_FULL = 4   # photos that keep their big previews in memory (most recently used)


class Photo:
    def __init__(self, pid, path, name):
        self.id = pid
        self.path = Path(path)
        self.name = name
        self.raw = loader.is_raw(path)
        self.lock = threading.Lock()
        self.preview = None   # linear float, PREVIEW_EDGE (only for recent photos)
        self.drag = None      # linear float, DRAG_EDGE (only for recent photos)
        self.grid = None      # linear float, GRID_EDGE (always kept; small)
        self.cache = {"preview": {}, "drag": {}, "grid": {}}
        self.info = None
        self.size = None

    def ensure(self, need="full"):
        """need='grid' for thumbnails and look grids; 'full' for the editor."""
        with self.lock:
            if self.grid is None or (need == "full" and self.preview is None):
                lin, _ = loader.load_linear(self.path, half=True)
                self.size = (lin.shape[1] * (2 if self.raw else 1), lin.shape[0] * (2 if self.raw else 1))
                prev = loader.resize_long(lin, PREVIEW_EDGE)
                del lin
                drag = loader.resize_long(prev, DRAG_EDGE)
                if self.grid is None:
                    self.grid = loader.resize_long(drag, GRID_EDGE)
                if need == "full":
                    self.preview, self.drag = prev, drag
        if need == "full":
            STATE.touch(self)
        return self

    def drop_big(self):
        with self.lock:
            self.preview = self.drag = None
            self.cache["preview"] = {}
            self.cache["drag"] = {}


def read_info(path):
    """Camera, lens and exposure for the little info line under the histogram."""
    out = {}
    try:
        import logging
        import exifread
        logging.getLogger("exifread").setLevel(logging.CRITICAL)
        with open(path, "rb") as f:
            t = exifread.process_file(f, details=False, stop_tag="EXIF MakerNote")
        if not t and loader.is_raw(path):  # e.g. Fuji RAF: read the JPEG preview inside the RAW
            import io
            import rawpy
            with rawpy.imread(str(path)) as r:
                th = r.extract_thumb()
            if th.format == rawpy.ThumbFormat.JPEG:
                t = exifread.process_file(io.BytesIO(th.data), details=False, stop_tag="EXIF MakerNote")
        def g(*keys):
            for k in keys:
                if k in t:
                    return str(t[k]).strip()
            return ""
        make, model = g("Image Make"), g("Image Model")
        make = make.title() if make.isupper() else make
        model = " ".join(w.title() if w.isupper() and len(w) > 2 else w for w in model.split())
        out["camera"] = model if make.split(" ")[0].lower() in model.lower() else f"{make.split(' ')[0].capitalize()} {model}".strip()
        out["lens"] = g("EXIF LensModel")
        fl = g("EXIF FocalLength")
        if fl:
            try:
                n, d = (fl.split("/") + ["1"])[:2]; out["focal"] = f"{round(float(n) / float(d))}mm"
            except ValueError:
                out["focal"] = fl + "mm"
        fn = g("EXIF FNumber")
        if fn:
            try:
                n, d = (fn.split("/") + ["1"])[:2]; out["aperture"] = f"f/{float(n) / float(d):.1f}".replace(".0", "")
            except ValueError:
                pass
        ex = g("EXIF ExposureTime")
        if ex:
            out["shutter"] = ex if "/" in ex else f"{ex}s"
        iso = g("EXIF ISOSpeedRatings", "EXIF PhotographicSensitivity")
        if iso:
            out["iso"] = f"ISO {iso}"
    except Exception:
        pass
    return {k: v for k, v in out.items() if v}


class State:
    def __init__(self):
        self.photos = {}
        self.order = []
        self.tmp = Path(tempfile.mkdtemp(prefix="grvty_"))
        self.loader_pool = ThreadPoolExecutor(max_workers=2)
        self.export_jobs = {}
        self.recent = []
        self.recent_lock = threading.Lock()

    def touch(self, ph):
        with self.recent_lock:
            if ph.id in self.recent:
                self.recent.remove(ph.id)
            self.recent.append(ph.id)
            while len(self.recent) > KEEP_FULL:
                old = self.photos.get(self.recent.pop(0))
                if old:
                    old.drop_big()

    def add(self, path, name=None):
        path = Path(path)
        pid = hashlib.sha1(f"{path}:{path.stat().st_size}:{path.stat().st_mtime}".encode()).hexdigest()[:12]
        if pid not in self.photos:
            self.photos[pid] = Photo(pid, path, name or path.name)
            self.order.append(pid)
            self.loader_pool.submit(self.photos[pid].ensure, "grid")
        return self.photos[pid]


STATE = State()


def _export_one(args):
    """Full-resolution render, run in a separate process so batches use every core."""
    path, is_raw, params, out_path, quality = args
    lin, _ = loader.load_linear(path, half=False)
    out = render_look(lin, params, is_raw)
    loader.save_image(out, out_path, quality)
    return str(out_path)


def unique_path(folder, stem, ext):
    p = Path(folder) / f"{stem}{ext}"
    i = 2
    while p.exists():
        p = Path(folder) / f"{stem} ({i}){ext}"
        i += 1
    return p


class Handler(BaseHTTPRequestHandler):
    server_version = "Grvty"

    def log_message(self, *a):
        pass

    # ---------- helpers
    def _send(self, code, body, ctype="application/json", cache=False):
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode()
        elif isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "max-age=31536000" if cache else "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def _photo(self, pid, need="full"):
        ph = STATE.photos.get(pid)
        if not ph:
            raise KeyError("photo not found")
        return ph.ensure(need)

    # ---------- routes
    def do_GET(self):
        try:
            u = urlparse(self.path)
            q = parse_qs(u.query)
            if u.path == "/" or u.path == "/index.html":
                return self._static("index.html")
            if u.path.startswith("/api/"):
                return self._api_get(u.path[5:], q)
            return self._static(unquote(u.path.lstrip("/")))
        except Exception as e:
            traceback.print_exc()
            self._send(500, {"error": str(e)})

    def do_POST(self):
        try:
            u = urlparse(self.path)
            return self._api_post(u.path[5:], parse_qs(u.query))
        except Exception as e:
            traceback.print_exc()
            self._send(500, {"error": str(e)})

    def _static(self, rel):
        p = (UI_DIR / rel).resolve()
        if UI_DIR not in p.parents and p != UI_DIR / "index.html" or not p.is_file():
            return self._send(404, "not found", "text/plain")
        ctype = {".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "text/javascript",
                 ".woff2": "font/woff2", ".svg": "image/svg+xml", ".png": "image/png",
                 ".ico": "image/x-icon"}.get(p.suffix, "application/octet-stream")
        self._send(200, p.read_bytes(), ctype, cache=p.suffix == ".woff2")

    def _api_get(self, route, q):
        if route == "schema":
            return self._send(200, {"defaults": DEFAULTS, "ranges": RANGES, "hues": HUES,
                                    "formats": sorted(loader.SUPPORTED), "ai": AI.available()})
        if route == "settings":
            try:
                return self._send(200, json.loads(SETTINGS.read_text(encoding="utf-8")))
            except Exception:
                return self._send(200, {})
        if route == "photos":
            return self._send(200, [{"id": p, "name": STATE.photos[p].name, "raw": STATE.photos[p].raw}
                                    for p in STATE.order])
        m = re.match(r"thumb/(\w+)$", route)
        if m:
            ph = self._photo(m.group(1), "grid")
            img = engine.render(loader.resize_long(ph.grid, THUMB_EDGE), {}, ph.raw)
            return self._send(200, loader.to_jpeg_bytes(img, 82), "image/jpeg")
        m = re.match(r"info/(\w+)$", route)
        if m:
            ph = STATE.photos.get(m.group(1))
            if not ph:
                return self._send(404, {})
            if ph.info is None:
                ph.info = read_info(ph.path)
            return self._send(200, ph.info)
        m = re.match(r"original/(\w+)$", route)
        if m:
            ph = self._photo(m.group(1))
            img = engine.render(ph.preview, {}, ph.raw, ph.cache["preview"])
            return self._send(200, loader.to_jpeg_bytes(img, 90), "image/jpeg")
        m = re.match(r"export/(\w+)$", route)
        if m:
            job = STATE.export_jobs.get(m.group(1))
            if not job:
                return self._send(404, {"error": "no such job"})
            return self._send(200, {k: v for k, v in job.items() if k != "futures"})
        self._send(404, {"error": "unknown"})

    def _api_post(self, route, q):
        if route == "upload":
            # raw file bytes in the body; name in a header
            name = Path(unquote(self.headers.get("X-Filename", "photo.jpg"))).name
            n = int(self.headers.get("Content-Length") or 0)
            dest = STATE.tmp / f"{hashlib.sha1(os.urandom(8)).hexdigest()[:8]}_{name}"
            with open(dest, "wb") as f:
                remaining = n
                while remaining:
                    chunk = self.rfile.read(min(remaining, 1 << 20))
                    if not chunk:
                        break
                    f.write(chunk)
                    remaining -= len(chunk)
            if dest.suffix.lower() not in loader.SUPPORTED:
                dest.unlink(missing_ok=True)
                return self._send(400, {"error": f"{name}: not a photo Grvty can open"})
            ph = STATE.add(dest, name)
            return self._send(200, {"id": ph.id, "name": ph.name, "raw": ph.raw})
        if route == "open":
            body = self._json()
            added = []
            for p in body.get("paths", []):
                pth = Path(p)
                if pth.is_dir():
                    files = sorted(f for f in pth.iterdir() if f.suffix.lower() in loader.SUPPORTED)
                else:
                    files = [pth] if pth.suffix.lower() in loader.SUPPORTED else []
                for f in files:
                    ph = STATE.add(f)
                    added.append({"id": ph.id, "name": ph.name, "raw": ph.raw})
            return self._send(200, added)
        if route == "render":
            body = self._json()
            size = body.get("size") or ("drag" if body.get("fast") else "preview")
            ph = self._photo(body["id"], "grid" if size == "grid" else "full")
            src = {"grid": ph.grid, "drag": ph.drag, "preview": ph.preview}[size]
            if src is None:  # evicted between ensure() and here: load again
                ph = self._photo(body["id"], "full")
                src = {"grid": ph.grid, "drag": ph.drag, "preview": ph.preview}[size]
            img = render_look(src, body.get("params", {}), ph.raw, ph.cache[size])
            return self._send(200, loader.to_jpeg_bytes(img, 90 if size == "preview" else 84), "image/jpeg")
        if route == "looks":
            body = self._json()
            n = max(1, min(24, int(body.get("count", 12))))
            if body.get("engine") == "ai" and AI.available():
                ph = self._photo(body["id"], "grid")
                return self._send(200, ai_looks(ph, body, n))
            if body.get("around"):
                out = looks.more_like(body["around"], n, TASTE)
            else:
                out = looks.generate(body.get("prompt", ""), n, TASTE)
            return self._send(200, out)
        if route == "pick":
            body = self._json()
            TASTE.record(body.get("prompt", ""), body.get("params", {}), [None] * max(0, int(body.get("shown", 1)) - 1))
            return self._send(200, {"ok": True})
        if route == "preset":
            body = self._json()
            params = merge(body.get("params", {}))
            approx = False
            if params.get("ai") and body.get("id") in STATE.photos:
                ph = self._photo(body["id"], "grid")
                small = loader.resize_long(ph.grid, 192)
                target = render_look(small, params, ph.raw)
                params, _ = fit.fit(small, target, ph.raw, start=dict(params, ai=None))
                approx = True
            files = xmp.save_preset(body.get("name") or "Grvty look", params,
                                    Path.home() / "Pictures" / "Grvty" / "Presets")
            return self._send(200, {"files": files, "approximated": approx})
        if route == "settings":
            SETTINGS.write_text(json.dumps(self._json(), indent=1), encoding="utf-8")
            return self._send(200, {"ok": True})
        if route == "remove":
            pid = self._json().get("id")
            if pid in STATE.photos:
                STATE.order.remove(pid)
                del STATE.photos[pid]
            return self._send(200, {"ok": True})
        if route == "export":
            body = self._json()
            folder = Path(body.get("folder") or Path.home() / "Pictures" / "Grvty")
            folder.mkdir(parents=True, exist_ok=True)
            quality = int(body.get("quality", 95))
            items = body.get("items", [])  # [{id, params}]
            job_id = hashlib.sha1(os.urandom(8)).hexdigest()[:10]
            job = {"total": len(items), "done": 0, "failed": [], "files": [], "folder": str(folder), "finished": False}
            STATE.export_jobs[job_id] = job
            threading.Thread(target=run_export, args=(job, items, folder, quality), daemon=True).start()
            return self._send(200, {"job": job_id})
        self._send(404, {"error": "unknown"})


def _effect_name(base, img):
    """Describe what an AI variation does, compared with the photo as it was."""
    def stats(x):
        y = x @ engine.LUMA
        return y.mean(), (x.max(-1) - x.min(-1)).mean(), (x[..., 0] - x[..., 2]).mean(), y.std()
    b, v = stats(base), stats(img)
    words = []
    if v[0] - b[0] > .03: words.append("brighter")
    if v[0] - b[0] < -.03: words.append("darker")
    if v[2] - b[2] > .02: words.append("warmer")
    if v[2] - b[2] < -.02: words.append("cooler")
    if v[1] - b[1] > .02: words.append("richer")
    if v[1] - b[1] < -.02: words.append("softer colour")
    if v[3] - b[3] > .015: words.append("more contrast")
    if v[3] - b[3] < -.015: words.append("gentler contrast")
    return words


def ai_looks(ph, body, n):
    """AI grades for one photo: the network's own reading first, then variations
    around it in the space of its learned colour cubes."""
    rng = np.random.default_rng()
    base_params = merge(body.get("around") or {})
    prompt = (body.get("prompt") or "").strip()
    if not body.get("around") and prompt:
        base_params, _ = looks.parse(prompt)
    tiny = loader.resize_long(ph.grid, 96)
    # name each variation by how it differs from what's on screen now: the pick, or the plain photo
    shown = render_look(tiny, base_params, ph.raw) if body.get("around") else engine.render(tiny, dict(base_params, ai=None), ph.raw)
    if body.get("around") and base_params.get("ai"):
        w0, spread = np.asarray(base_params["ai"], dtype=np.float32), 0.10
    else:
        w0, spread = AI.weights(engine.render(ph.grid, {}, ph.raw)), 0.28
    e0 = np.zeros_like(w0); e0[0] = 1
    out = []
    for k in range(n):
        if k == 0:
            w, name = w0, ("Your pick" if body.get("around") else "AI pick")
        else:
            strength = rng.uniform(0.6, 1.5) if not body.get("around") else rng.uniform(0.85, 1.15)
            w = e0 + (w0 - e0) * strength + rng.normal(0, spread, size=w0.shape).astype(np.float32) * (w0 != e0)
            w[0] = w0[0] + rng.normal(0, spread * 0.3)
            name = None
        p = dict(base_params, ai=[round(float(v), 4) for v in w])
        if name is None:
            words = _effect_name(shown, render_look(tiny, p, ph.raw))
            name = ("AI · " + ", ".join(words[:2])) if words else "AI variation"
        out.append({"name": name, "params": merge(p), "tags": ["AI grade"] + looks.describe(merge(p))})
    return out


def run_export(job, items, folder, quality):
    workers = max(1, min(len(items), (os.cpu_count() or 2) - 1))
    tasks = []
    for it in items:
        ph = STATE.photos.get(it["id"])
        if not ph:
            continue
        out = unique_path(folder, Path(ph.name).stem + "_grvty", ".jpg")
        out.touch()  # reserve the name
        tasks.append((str(ph.path), ph.raw, it.get("params", {}), str(out), quality))
    try:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            for t, fut in [(t, pool.submit(_export_one, t)) for t in tasks]:
                try:
                    job["files"].append(fut.result())
                except Exception as e:
                    job["failed"].append(f"{Path(t[0]).name}: {e}")
                    Path(t[3]).unlink(missing_ok=True)
                job["done"] += 1
    finally:
        job["finished"] = True


def start(port=0):
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv
