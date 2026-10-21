"""Grvty — start here.  python app.py [photos or folders...]

Two processes:
  * this one draws the window and nothing else, so it never stops responding;
  * a background "engine" process decodes RAWs and renders looks (grvty.server).
"""
import multiprocessing
import os
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

NO_WINDOW = 0x08000000
DATA_DIR = Path(os.environ.get("APPDATA") or Path.home() / ".config") / "Grvty"
PHOTO_EXTS = ["*.jpg", "*.jpeg", "*.png", "*.tif", "*.tiff", "*.webp", "*.dng", "*.cr2", "*.cr3", "*.crw", "*.nef",
              "*.nrw", "*.arw", "*.srf", "*.sr2", "*.raf", "*.orf", "*.rw2", "*.pef", "*.srw", "*.3fr", "*.iiq", "*.rwl"]


def _powershell_dialog(script):
    """Run a Windows file dialog in its own little PowerShell process.

    Windows file dialogs need a special (STA) thread; opening them from the
    window library's background thread deadlocks both the dialog and the app.
    A separate process sidesteps that completely."""
    full = ("[Console]::OutputEncoding = [System.Text.Encoding]::UTF8\n"
            "Add-Type -AssemblyName System.Windows.Forms\n"
            "[System.Windows.Forms.Application]::EnableVisualStyles()\n"
            "$owner = New-Object System.Windows.Forms.Form -Property @{TopMost=$true; ShowInTaskbar=$false; "
            "StartPosition='CenterScreen'; Width=1; Height=1; Opacity=0}\n"
            "$owner.Show(); $owner.Activate()\n" + script + "\n$owner.Close()")
    r = subprocess.run(["powershell", "-STA", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", full],
                       capture_output=True, creationflags=NO_WINDOW)
    out = r.stdout.decode("utf-8", errors="replace").strip()
    return [l.strip() for l in out.splitlines() if l.strip()]


class Bridge:
    """Things the window can ask Windows to do. Runs off the window's thread."""

    def __init__(self):
        self._window = None
        self._last_dir = ""

    def pick_files(self):
        if sys.platform != "win32":
            return []
        start = self._last_dir or "[Environment]::GetFolderPath('MyPictures')"
        start = f"'{self._last_dir}'" if self._last_dir else start
        exts = ";".join(PHOTO_EXTS)
        files = _powershell_dialog(
            "$d = New-Object System.Windows.Forms.OpenFileDialog\n"
            "$d.Title = 'Choose photos'\n$d.Multiselect = $true\n"
            f"$d.Filter = 'Photos (RAW and JPEG)|{exts}|All files|*.*'\n"
            f"$d.InitialDirectory = {start}\n"
            "if ($d.ShowDialog($owner) -eq 'OK') { $d.FileNames }")
        if files:
            self._last_dir = str(Path(files[0]).parent).replace("'", "''")
        return files

    def pick_folder(self):
        if sys.platform != "win32":
            return None
        out = _powershell_dialog(
            "$d = New-Object System.Windows.Forms.FolderBrowserDialog\n"
            "$d.Description = 'Choose where Grvty saves your photos'\n$d.ShowNewFolderButton = $true\n"
            "$d.SelectedPath = [Environment]::GetFolderPath('MyPictures')\n"
            "if ($d.ShowDialog($owner) -eq 'OK') { $d.SelectedPath }")
        return out[0] if out else None

    def open_folder(self, path):
        if sys.platform == "win32":
            os.startfile(path)
        else:
            subprocess.Popen(["xdg-open", path])


def _log_to_file(name):
    """A windowed app has no console; send errors to a log file instead of crashing."""
    if sys.stderr is None or sys.stdout is None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        f = open(DATA_DIR / name, "a", encoding="utf-8", buffering=1)
        sys.stdout = sys.stdout or f
        sys.stderr = sys.stderr or f


def engine_process(port_q, files, parent_pid):
    """The background process: runs the local server that does all the photo work."""
    _log_to_file("engine.log")
    from grvty import server
    srv = server.start()
    for arg in files:
        p = Path(arg)
        if p.exists():
            for f in (sorted(p.iterdir()) if p.is_dir() else [p]):
                if f.suffix.lower() in server.loader.SUPPORTED:
                    server.STATE.add(f)
    port_q.put(srv.server_address[1])
    # quit by ourselves if the window process goes away
    while True:
        time.sleep(2)
        try:
            if os.getppid() != parent_pid:
                os._exit(0)
        except Exception:
            pass


def selftest():
    """Run by the Windows build to prove the packaged app really works."""
    import json
    import urllib.request
    import numpy as np
    from grvty import engine, looks, server, xmp
    img = np.random.default_rng(1).random((120, 180, 3)).astype("float32")
    out = engine.render(img, looks.generate("moody black and white, sepia", 4)[1]["params"], False)
    assert out.shape == img.shape and np.isfinite(out).all()
    assert "<x:xmpmeta" in xmp.preset_xml("test", {})
    from grvty.ai import GradeAI
    g = GradeAI()
    if g.available():
        graded, w = g.grade(np.clip(img, 0, 1))
        assert graded.shape == img.shape and np.isfinite(w).all()
    q = multiprocessing.Queue()
    p = multiprocessing.Process(target=engine_process, args=(q, [], os.getpid()), daemon=False)
    p.start()
    try:
        port = q.get(timeout=90)
        base = f"http://127.0.0.1:{port}"
        assert b"grvty" in urllib.request.urlopen(base + "/").read()
        assert json.loads(urllib.request.urlopen(base + "/api/schema").read())["hues"]
    finally:
        p.terminate()
    import rawpy, cv2, webview  # noqa: F401  (all bundled)


def main():
    if "--selftest" in sys.argv:
        i = sys.argv.index("--selftest")
        log = Path(sys.argv[i + 1]) if len(sys.argv) > i + 1 else None
        try:
            selftest()
            if log:
                log.write_text("SELFTEST OK")
        except Exception:
            import traceback
            if log:
                log.write_text(traceback.format_exc())
            sys.exit(1)
        return

    _log_to_file("window.log")
    q = multiprocessing.Queue()
    eng = multiprocessing.Process(target=engine_process, args=(q, sys.argv[1:], os.getpid()), daemon=False)
    eng.start()
    try:
        import webview
    except ImportError:
        url = f"http://127.0.0.1:{q.get(timeout=90)}/"
        print("Grvty is running at", url, "(pywebview not installed, using your browser)")
        webbrowser.open(url)
        eng.join()
        return

    bridge = Bridge()
    # open the window straight away on a tiny local "starting" page, then point it at the engine
    win = webview.create_window("Grvty", html=STARTING_HTML, js_api=bridge, width=1440, height=900,
                                min_size=(1100, 720), background_color="#F3E3EA", text_select=False)
    bridge._window = win

    def connect():
        try:
            port = q.get(timeout=120)
            win.load_url(f"http://127.0.0.1:{port}/")
        except Exception:
            win.load_html("<body style='font:16px system-ui;padding:40px'>Grvty's engine didn't start. "
                          "Close this window and open Grvty again.</body>")

    threading.Thread(target=connect, daemon=True).start()
    try:
        webview.start(private_mode=False, storage_path=str(DATA_DIR / "webview"))
    finally:
        eng.terminate()


STARTING_HTML = """<!doctype html><html><head><meta charset="utf-8"><style>
html,body{margin:0;height:100%;background:radial-gradient(700px 500px at 20% 10%,#f6c9d8,transparent 60%),
radial-gradient(700px 500px at 90% 90%,#d9c7f2,transparent 60%),#F3E3EA;display:grid;place-items:center;
font:600 15px 'Segoe UI Variable',system-ui,sans-serif;color:#6E5262}
svg{width:120px;height:120px;display:block;margin:0 auto 14px}.m{transform-origin:60px 60px;animation:s 1.4s linear infinite}
@keyframes s{to{transform:rotate(360deg)}}</style></head><body><div>
<svg viewBox="0 0 120 120"><circle cx="60" cy="60" r="44" fill="none" stroke="#c9adbb" stroke-dasharray="2 6"/>
<circle cx="60" cy="60" r="22" fill="#D23A66"/><g class="m"><circle cx="60" cy="16" r="7" fill="#2A1622"/></g></svg>
Opening Grvty…</div></body></html>"""


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
