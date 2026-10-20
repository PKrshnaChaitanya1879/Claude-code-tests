"""Grvty — start here.  python app.py [photos or folders...]"""
import multiprocessing
import sys
import webbrowser
from pathlib import Path


class Bridge:
    """Things the window can ask Windows to do (file pickers etc.)."""

    def __init__(self):
        self.window = None

    def pick_files(self):
        import webview
        from grvty.loader import SUPPORTED
        pats = ";".join(f"*{e}" for e in sorted(SUPPORTED))
        res = self.window.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=True,
                                             file_types=(f"Photos ({pats})", "All files (*.*)"))
        return list(res or [])

    def pick_folder(self):
        import webview
        res = self.window.create_file_dialog(webview.FOLDER_DIALOG)
        return res[0] if res else None

    def open_folder(self, path):
        import os
        import subprocess
        if sys.platform == "win32":
            os.startfile(path)
        else:
            subprocess.Popen(["xdg-open", path])


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
    srv = server.start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    assert b"grvty" in urllib.request.urlopen(base + "/").read()
    assert json.loads(urllib.request.urlopen(base + "/api/schema").read())["hues"]
    import rawpy, cv2, webview  # noqa: F401  (all bundled)


def main():
    if "--selftest" in sys.argv:
        log = Path(sys.argv[sys.argv.index("--selftest") + 1]) if len(sys.argv) > sys.argv.index("--selftest") + 1 else None
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
    from grvty import server
    srv = server.start()
    url = f"http://127.0.0.1:{srv.server_address[1]}/"
    for arg in sys.argv[1:]:
        p = Path(arg)
        if p.exists():
            files = sorted(p.iterdir()) if p.is_dir() else [p]
            for f in files:
                if f.suffix.lower() in server.loader.SUPPORTED:
                    server.STATE.add(f)
    try:
        import webview
    except ImportError:
        print("Grvty is running at", url, "(pywebview not installed, using your browser)")
        webbrowser.open(url)
        import time
        while True:
            time.sleep(3600)
    bridge = Bridge()
    win = webview.create_window("Grvty", url, js_api=bridge, width=1440, height=900,
                                min_size=(1100, 720), background_color="#F3E3EA", text_select=False)
    bridge.window = win
    webview.start(private_mode=False, storage_path=str(server.DATA_DIR / "webview"))


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
