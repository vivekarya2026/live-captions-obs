"""Adds Live Captions to OBS (run by the installer while OBS is closed):

  * registers obs/live_captions.lua in every scene collection
    (OBS -> Tools -> Scripts), and removes older copies of it
  * adds the "Live Captions" dock (View -> Docks) pointing at the translator

Usage: python -m livecaptions.obs_setup [--remove] [--script PATH]
"""
from __future__ import annotations

import argparse
import configparser
import io
import json
import shutil
import sys
import time
import uuid
from pathlib import Path

from . import paths

DOCK_TITLE = "Live Captions"
DOCK_URL = "http://127.0.0.1:8765/dock"
SCRIPT_NAMES = ("live_captions.lua", "caption_language.lua")  # current + the pre-package name


def default_script() -> Path:
    return paths.PACKAGE.parent.parent / "obs" / "live_captions.lua"


def _backup(p: Path) -> None:
    if p.exists():
        shutil.copy2(p, p.with_name(p.name + f".bak-livecaptions-{time.strftime('%Y%m%d%H%M%S')}"))


def _new_collection(script: Path) -> dict:
    """Minimal scene collection for a fresh OBS install (OBS fills in the rest)."""
    return {"name": "Untitled", "current_scene": "Scene", "current_program_scene": "Scene",
            "scene_order": [{"name": "Scene"}],
            "sources": [{"id": "scene", "versioned_id": "scene", "name": "Scene", "uuid": str(uuid.uuid4()),
                         "settings": {"items": [], "id_counter": 0}}],
            "modules": {"scripts-tool": [{"path": str(script), "settings": {}}]}}


def register_script(cfg: Path, script: Path, remove: bool) -> list[str]:
    scenes = cfg / "basic" / "scenes"
    scenes.mkdir(parents=True, exist_ok=True)
    files = [f for f in scenes.glob("*.json")]
    changed = []
    if not files and not remove:
        (scenes / "Untitled.json").write_text(json.dumps(_new_collection(script), indent=4), encoding="utf-8")
        return ["Untitled (new)"]
    for f in files:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except ValueError:
            continue
        scripts = d.setdefault("modules", {}).setdefault("scripts-tool", [])
        keep = [s for s in scripts if Path(s.get("path", "")).name not in SCRIPT_NAMES]
        if not remove:
            keep.append({"path": str(script), "settings": {}})
        if keep != scripts:
            _backup(f)
            d["modules"]["scripts-tool"] = keep
            f.write_text(json.dumps(d, indent=4, ensure_ascii=False), encoding="utf-8")
            changed.append(d.get("name", f.stem))
    return changed


def _read_ini(p: Path) -> configparser.ConfigParser:
    c = configparser.ConfigParser(interpolation=None, strict=False)
    c.optionxform = str  # keep key case
    if p.exists():
        raw = p.read_bytes().decode("utf-8-sig", errors="replace")
        c.read_file(io.StringIO(raw))
    return c


def add_dock(cfg: Path, remove: bool) -> Path:
    # OBS 30+: user.ini ; older versions: global.ini
    ini = cfg / "user.ini"
    if not ini.exists() and (cfg / "global.ini").exists():
        ini = cfg / "global.ini"
    c = _read_ini(ini)
    if not c.has_section("BasicWindow"):
        c.add_section("BasicWindow")
    try:
        docks = json.loads(c.get("BasicWindow", "ExtraBrowserDocks", fallback="[]") or "[]")
    except ValueError:
        docks = []
    docks = [d for d in docks if d.get("title") != DOCK_TITLE]
    if not remove:
        docks.append({"title": DOCK_TITLE, "url": DOCK_URL, "uuid": uuid.uuid4().hex})
    c.set("BasicWindow", "ExtraBrowserDocks", json.dumps(docks))
    _backup(ini)
    ini.parent.mkdir(parents=True, exist_ok=True)
    with open(ini, "w", encoding="utf-8") as f:
        c.write(f, space_around_delimiters=False)
    return ini


def obs_running() -> bool:
    import subprocess
    try:
        if paths.IS_WIN:
            out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq obs64.exe", "/NH"], capture_output=True,
                                 text=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
            return "obs64.exe" in out.lower()
        return subprocess.run(["pgrep", "-x", "OBS" if paths.IS_MAC else "obs"], capture_output=True).returncode == 0
    except OSError:
        return False


PENDING = paths.DATA / "obs_setup_pending"   # installer ran while OBS was open: finish later


def finish_pending() -> None:
    """Called when Live Captions starts: do the OBS setup the installer had to postpone."""
    if PENDING.exists() and not obs_running():
        try:
            main([])
            PENDING.unlink(missing_ok=True)
        except Exception:
            pass


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--script", type=Path, default=default_script())
    ap.add_argument("--remove", action="store_true", help="undo (used by the uninstaller)")
    ap.add_argument("--later-if-open", action="store_true",
                    help="if OBS is open, do it the next time Live Captions starts with OBS closed "
                         "(OBS overwrites its settings when it quits)")
    args = ap.parse_args(argv)
    if args.later_if_open and not args.remove and obs_running():
        PENDING.parent.mkdir(parents=True, exist_ok=True)
        PENDING.write_text("1")
        print("OBS is open: Live Captions will add itself to OBS after OBS is closed.")
        return 0
    cfg = paths.obs_config_dir()
    script = args.script.resolve()
    if not args.remove and not script.exists():
        print(f"OBS script not found: {script}", file=sys.stderr)
        return 1
    changed = register_script(cfg, script, args.remove)
    ini = add_dock(cfg, args.remove)
    print(("Removed from" if args.remove else "Added to") + f" OBS scene collections: {', '.join(changed) or '(no change)'}")
    print(f"Dock {'removed from' if args.remove else 'added to'}: {ini}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
