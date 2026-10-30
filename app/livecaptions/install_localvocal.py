"""Installs the LocalVocal OBS plugin (Whisper speech recognition inside OBS),
used for captions in OBS until Qwen3-ASR has finished downloading.
Run by the installers; does nothing if OBS isn't installed or LocalVocal is.

Usage: python -m livecaptions.install_localvocal
"""
from __future__ import annotations

import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

from . import paths

VERSION = "0.6.2"
BASE = f"https://github.com/royshil/obs-localvocal/releases/download/{VERSION}/obs-localvocal-{VERSION}-"


def _download(url: str, dest: Path) -> None:
    import ssl
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        ctx = ssl.create_default_context()
    with urllib.request.urlopen(url, timeout=120, context=ctx) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f)


def mac() -> str:
    if not Path("/Applications/OBS.app").exists():
        return "OBS is not installed: skipped LocalVocal"
    user_plugins = paths.HOME / "Library/Application Support/obs-studio/plugins"
    for d in (user_plugins, Path("/Library/Application Support/obs-studio/plugins")):
        if (d / "obs-localvocal.plugin").exists():
            return "LocalVocal is already installed"
    major = int(platform.mac_ver()[0].split(".")[0] or 14)
    flavour = str(min(max(major, 12), 15))  # builds exist for macOS 12-15; newer use the 15 build
    arch = "arm64" if platform.machine() == "arm64" else "x86_64"
    with tempfile.TemporaryDirectory() as tmp:
        pkg = Path(tmp) / "localvocal.pkg"
        _download(f"{BASE}macos-{flavour}-{arch}.pkg", pkg)
        out = Path(tmp) / "x"
        subprocess.run(["pkgutil", "--expand-full", str(pkg), str(out)], check=True, capture_output=True)
        found = next(out.rglob("obs-localvocal.plugin"), None)
        if found is None:
            return "LocalVocal package layout changed: skipped"
        user_plugins.mkdir(parents=True, exist_ok=True)
        dest = user_plugins / "obs-localvocal.plugin"
        subprocess.run(["ditto", str(found), str(dest)], check=True)
        subprocess.run(["xattr", "-dr", "com.apple.quarantine", str(dest)], capture_output=True)
    return f"LocalVocal {VERSION} installed"


def windows() -> str:
    import os
    pf = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "obs-studio"
    if not (pf / "bin/64bit/obs64.exe").exists():
        return "OBS is not installed: skipped LocalVocal"
    if (pf / "obs-plugins/64bit/obs-localvocal.dll").exists() or \
            (Path(os.environ.get("ProgramData", r"C:\ProgramData")) / "obs-studio/plugins/obs-localvocal").exists():
        return "LocalVocal is already installed"
    from .models import has_nvidia
    flavour = "nvidia" if has_nvidia() else "generic"
    exe = Path(tempfile.gettempdir()) / f"obs-localvocal-{VERSION}-{flavour}-Installer.exe"
    _download(f"{BASE}windows-x64-{flavour}-Installer.exe", exe)
    # Its own setup (asks Windows for permission to install into OBS's folder)
    import ctypes
    r = ctypes.windll.shell32.ShellExecuteW(None, "runas", str(exe), "/SILENT", None, 1)
    return f"LocalVocal {VERSION} ({flavour}) installer started" if r > 32 else "LocalVocal install was cancelled"


def main() -> int:
    try:
        print(windows() if paths.IS_WIN else mac() if paths.IS_MAC else "not supported on this system")
    except Exception as e:  # never fail the Live Captions install because of this
        print(f"Could not install LocalVocal ({e}); captions will start when Qwen3 has downloaded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
