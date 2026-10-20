"""Grvty Setup: a one-button installer (and uninstaller) with a glass window.

Installs for the current user only (no admin prompt) into
%LOCALAPPDATA%\\Programs\\Grvty, adds Desktop + Start menu shortcuts and an
entry in Windows' "Installed apps" list.
"""
import os
import shutil
import subprocess
import sys
import threading
import time
import zipfile
from pathlib import Path

APP = "Grvty"
HERE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
PAYLOAD = HERE / "payload.zip"
VERSION = (HERE / "VERSION").read_text().strip() if (HERE / "VERSION").exists() else "dev"
INSTALL_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "Programs" / APP
EXE = INSTALL_DIR / f"{APP}.exe"
UNINSTALLER = INSTALL_DIR / f"Uninstall {APP}.exe"
REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\Grvty"
NO_WINDOW = 0x08000000


def _ps(script):
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script],
                   creationflags=NO_WINDOW, capture_output=True)


def _shortcut_paths():
    desktop = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"
    try:  # the real Desktop (it can live in OneDrive)
        out = subprocess.run(["powershell", "-NoProfile", "-Command", "[Environment]::GetFolderPath('Desktop')"],
                             creationflags=NO_WINDOW, capture_output=True, text=True, timeout=15).stdout.strip()
        if out:
            desktop = Path(out)
    except Exception:
        pass
    start = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    return [desktop / f"{APP}.lnk", start / f"{APP}.lnk"]


class Api:
    def __init__(self, mode):
        self.mode = mode
        self._window = None
        self.state = {"phase": "idle", "progress": 0.0, "message": "", "error": ""}

    # ---------- info for the page
    def info(self):
        size = 0
        if PAYLOAD.exists():
            with zipfile.ZipFile(PAYLOAD) as z:
                size = sum(i.file_size for i in z.infolist())
        return {"mode": self.mode, "installed": EXE.exists(), "version": VERSION, "size_mb": round(size / 1e6)}

    def status(self):
        return self.state

    # ---------- install
    def install(self):
        if self.state["phase"] == "working":
            return False
        self.state = {"phase": "working", "progress": 0.0, "message": "Getting ready", "error": ""}
        threading.Thread(target=self._install, daemon=True).start()
        return True

    def _install(self):
        try:
            # close a running copy so its files can be replaced
            subprocess.run(["taskkill", "/IM", f"{APP}.exe", "/F"], creationflags=NO_WINDOW, capture_output=True)
            time.sleep(0.4)
            if INSTALL_DIR.exists():
                for child in INSTALL_DIR.iterdir():
                    if child.name.lower().startswith("uninstall"):
                        continue
                    shutil.rmtree(child, ignore_errors=True) if child.is_dir() else child.unlink(missing_ok=True)
            INSTALL_DIR.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(PAYLOAD) as z:
                items = z.infolist()
                total = sum(i.file_size for i in items) or 1
                done = 0
                for i in items:
                    z.extract(i, INSTALL_DIR)
                    done += i.file_size
                    self.state["progress"] = 0.9 * done / total
                    self.state["message"] = "Copying Grvty"
            self.state["message"] = "Adding shortcuts"
            if getattr(sys, "frozen", False):
                shutil.copy2(sys.executable, UNINSTALLER)
            for lnk in _shortcut_paths():
                lnk.parent.mkdir(parents=True, exist_ok=True)
                _ps(f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{lnk}');"
                    f"$s.TargetPath='{EXE}';$s.WorkingDirectory='{INSTALL_DIR}';$s.IconLocation='{EXE},0';"
                    f"$s.Description='Grvty photo grading';$s.Save()")
            self.state["progress"] = 0.96
            self._register()
            self.state.update(progress=1.0, phase="done", message="Grvty is ready")
        except Exception as e:
            self.state.update(phase="error", error=str(e))

    def _register(self):
        try:
            import winreg
            size_kb = sum(f.stat().st_size for f in INSTALL_DIR.rglob("*") if f.is_file()) // 1024
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_KEY) as k:
                for name, val in (("DisplayName", APP), ("DisplayVersion", VERSION), ("Publisher", APP),
                                  ("DisplayIcon", str(EXE)), ("InstallLocation", str(INSTALL_DIR)),
                                  ("UninstallString", f'"{UNINSTALLER}" --uninstall')):
                    winreg.SetValueEx(k, name, 0, winreg.REG_SZ, val)
                winreg.SetValueEx(k, "EstimatedSize", 0, winreg.REG_DWORD, int(size_kb))
                winreg.SetValueEx(k, "NoModify", 0, winreg.REG_DWORD, 1)
                winreg.SetValueEx(k, "NoRepair", 0, winreg.REG_DWORD, 1)
        except Exception:
            pass

    # ---------- uninstall
    def uninstall(self):
        self.state = {"phase": "working", "progress": 0.2, "message": "Removing Grvty", "error": ""}
        threading.Thread(target=self._uninstall, daemon=True).start()
        return True

    def _uninstall(self):
        try:
            subprocess.run(["taskkill", "/IM", f"{APP}.exe", "/F"], creationflags=NO_WINDOW, capture_output=True)
            for lnk in _shortcut_paths():
                lnk.unlink(missing_ok=True)
            self.state["progress"] = 0.5
            try:
                import winreg
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, REG_KEY)
            except Exception:
                pass
            for child in INSTALL_DIR.iterdir() if INSTALL_DIR.exists() else []:
                if Path(sys.executable).resolve() == child.resolve():
                    continue
                shutil.rmtree(child, ignore_errors=True) if child.is_dir() else child.unlink(missing_ok=True)
            self.state.update(progress=1.0, phase="done", message="Grvty has been removed")
        except Exception as e:
            self.state.update(phase="error", error=str(e))

    # ---------- window
    def launch(self):
        if EXE.exists():
            subprocess.Popen([str(EXE)], cwd=str(INSTALL_DIR), creationflags=0x00000008)  # DETACHED_PROCESS
        self.close()

    def close(self):
        if self.mode == "uninstall" and self.state["phase"] == "done" and getattr(sys, "frozen", False):
            # remove the uninstaller itself and the folder once this window has closed
            subprocess.Popen(f'cmd /c ping 127.0.0.1 -n 3 > nul & rmdir /s /q "{INSTALL_DIR}"',
                             creationflags=NO_WINDOW | 0x00000008, shell=False)
        if self._window:
            self._window.destroy()

    def minimize(self):
        if self._window:
            self._window.minimize()


def main():
    try:  # close the "opening" splash PyInstaller shows while unpacking
        import pyi_splash
        pyi_splash.close()
    except Exception:
        pass
    import webview
    mode = "uninstall" if ("--uninstall" in sys.argv or "uninstall" in Path(sys.executable).name.lower()) else "install"
    api = Api(mode)
    win = webview.create_window("Grvty Setup", str(HERE / "ui" / "setup.html"), js_api=api, width=560, height=640,
                                resizable=False, frameless=True, easy_drag=True, background_color="#F3E3EA")
    api._window = win
    webview.start()


if __name__ == "__main__":
    main()
