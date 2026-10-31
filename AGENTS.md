# Instructions for coding agents

You are setting up, running, fixing or changing **Live Captions**: offline live captions and
translation (English ↔ Hindi / Hinglish), with OBS, its own window, and Google Docs.
Read this whole file before doing anything. The project map is in `docs/ARCHITECTURE.md`;
the user guide is `docs/SETUP_GUIDE.md`.

## How to work

1. **Look before you act.** Check the computer first (step 1). Read the files you will touch.
2. **Do the smallest thing that works.** Reuse code that is already here. Don't add packages,
   files or settings unless the task needs them.
3. **Fix the cause, not the symptom.** Read `~/.livecaptions/translator.log` before changing code.
4. **Prove it.** Every step below ends with a check. Don't say "done" until the check passes.
   If a check can't run (no mic, no OBS), say so plainly.
5. **Talk simply.** The user may not be technical. After each step, one or two plain sentences:
   what you did, what happened, what's next. Ask before anything that deletes data, needs a
   password, or changes OBS while it's open.
6. **Keep the map true.** If you change how things work, update `docs/ARCHITECTURE.md`
   (and add a row to its "What has been tested" table when you test something new).

## Task A: set up on this computer (do it all yourself)

### 1. Check the computer

Run and report:

| Check | Mac | Windows (PowerShell) |
|---|---|---|
| chip | `uname -m` → `arm64` = Apple Silicon, `x86_64` = Intel | `$env:PROCESSOR_ARCHITECTURE` → must be `AMD64` |
| OS | `sw_vers -productVersion` (needs 12+) | `[Environment]::OSVersion` (Windows 10/11) |
| free space | `df -h ~` (needs ~10 GB) | `Get-PSDrive C` |
| Python 3.11 | `python3.11 --version` | `py -3.11 --version` |
| NVIDIA GPU | (none on Mac) | `nvidia-smi` |
| OBS | `ls /Applications/OBS.app` | `Test-Path "$env:ProgramFiles\obs-studio"` |

Stop and tell the user if: OS too old, under 10 GB free, or 32-bit Windows.
If Python 3.11 is missing, install it: Mac `brew install python@3.11` (or the python.org 3.11
installer); Windows `winget install Python.Python.3.11`. Then open a new terminal.
On an Intel Mac, `python3.11 -c "import platform; print(platform.machine())"` must print `x86_64`.

### 2. Choose the path

- **User just wants to use it** → installer (Path A in `docs/SETUP_GUIDE.md`). Download the right
  file from the latest release (`gh release download -R vivekarya2026/live-captions-obs -p '*arm64.pkg'`
  / `'*x86_64.pkg'` / `'*Setup.exe'`) and open it for the user. The installer needs the user's
  password and clicks; guide them. Then skip to step 6.
- **User works in Cursor / wants to change things** → from source, steps 3–6.

### 3. Get the code

If this folder isn't the repo yet:
`git clone https://github.com/vivekarya2026/live-captions-obs.git && cd live-captions-obs`

### 4. Install (from the project folder)

| Computer | Commands |
|---|---|
| Mac Apple Silicon | `python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt` |
| Mac Intel | `python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt "numpy<2" --only-binary=:all:` |
| Windows | `py -3.11 -m venv .venv; .venv\Scripts\pip install -r requirements.txt` |

**Check:** `pip` ends without errors.

### 5. Download the models and self-test (from the `app` folder)

```
cd app
../.venv/bin/python -m livecaptions --download    # Windows: ..\.venv\Scripts\python
../.venv/bin/python -m livecaptions --test
```

`--download` takes 10–30 minutes (~5 GB; the 1.7B model only downloads when chosen) and also installs PyTorch (Intel Mac: 2.2.2; NVIDIA PC:
the GPU build). Run it in the background and report progress now and then.
**Check:** `--test` prints `IN:`/`OUT:` lines, and Hindi lines come out as English
(e.g. `आज हम सब मिलकर सत्संग में सेवा करेंगे।` → `Today we will all do sewa (selfless service) in satsang…`).
Optional full check: `../.venv/bin/python ../tests/test_vocabulary.py` must end with `ALL TERMS EXACT` (~1 min).

### 6. Connect OBS (only if OBS is installed and the user wants it)

Ask the user to **quit OBS**, then from `app`:

```
../.venv/bin/python -m livecaptions.obs_setup
../.venv/bin/python -m livecaptions.install_localvocal
```

**Check:** `obs_setup` prints *Added to OBS scene collections…* and *Dock added to…*;
`install_localvocal` prints that LocalVocal is installed (or already installed). Tell the user to open OBS and find **Docks → Live Captions**
(OBS 30+: View → Docks). Warn them not to move the project folder (OBS points to `.venv`).

### 7. Start it

`../.venv/bin/python -m livecaptions` opens the window at http://127.0.0.1:8765/.
**Check:** `curl -s http://127.0.0.1:8765/state` returns JSON. Ask the user to allow the
microphone, pick the language (e.g. Hindi → English), say a sentence and confirm captions appear.
Suggest the **0.6B** speech model on Intel Macs and PCs without NVIDIA.

### 8. Google Docs (only if asked)

Follow `docs/GOOGLE_DOCS.md`. The Google steps happen in the user's browser and account: walk
them through it; you can't do those clicks for them. On a second computer only the
**connection link** is needed (paste it in the window → Google Docs → Connect).

### 9. Finish

Tell the user in plain words: what's installed, how to start it next time, where sessions are
saved (`Documents/Live Captions`), and anything you couldn't check.

## Task B: something is broken

1. Read the end of `~/.livecaptions/translator.log` (Windows: `%USERPROFILE%\.livecaptions\translator.log`).
2. Match it to the problems table in `docs/SETUP_GUIDE.md`. Common causes:
   - *NumPy 1.x/2* error on Intel Mac → `pip install "numpy<2" --only-binary=:all:` (also into
     `~/.livecaptions/pylib` with `--target` if that's where it failed).
   - Download stopped → run `--download` again (it resumes).
   - No captions → wrong/muted mic, or mic permission (Mac: System Settings → Privacy & Security →
     Microphone; allow Live Captions / OBS / Cursor).
   - Port 8765 busy → an old copy is running: `curl -s http://127.0.0.1:8765/quit`.
3. Fix, restart, and run the step's check again.

## Task C: change the code

- Find the file in the table in `docs/ARCHITECTURE.md`. The pipeline hub is `app/livecaptions/translator.py`.
- **Vocabulary** words: edit `app/livecaptions/data/vocabulary/Vocabulary_for_Live_Translations.xlsx`
  (or `hindi_terms.csv`), not the code. Changes apply live.
- After any change run `--test` and `tests/test_vocabulary.py`. Both must pass.
- Keep it working on **all three**: Mac Apple Silicon, Mac Intel (PyTorch 2.2.2, NumPy < 2, CPU only)
  and Windows. Use `paths.py` for every folder; never hard-code a path.
- Never commit models, `.venv`, `build/`, `dist/` (see `.gitignore`).

## Task D: release a new version

1. Bump `app/livecaptions/__init__.py` (`__version__`).
2. Commit, then `git tag vX.Y.Z && git push origin main vX.Y.Z`.
3. Watch `gh run list -L 1` / `gh run watch`. GitHub Actions builds Mac arm64, Mac x86_64 and
   Windows, then publishes the release.
4. **Check:** `gh release view vX.Y.Z` lists three files.
   Local builds: `installer/macos/build.sh` (`ARCH=x86_64` for Intel, works on Apple Silicon via
   Rosetta) and `installer\windows\build.ps1` (needs Inno Setup 6).

## Never

- Never commit or print secrets: the Google Docs connection link (`?k=…`) is a password.
- Never delete `Documents/Live Captions` (the user's transcripts) or `~/.livecaptions/models`
  without asking.
- Never edit OBS settings while OBS is open.
- Never upgrade PyTorch or NumPy on Intel Macs.
- Commercial use is not allowed (PolyForm Noncommercial; NLLB-200 is non-commercial).
