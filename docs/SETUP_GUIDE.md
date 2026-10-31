# Live Captions: step-by-step setup on any computer

This guide gets Live Captions running on a new computer. Pick **one** path.
Want to know how the project is built? See [ARCHITECTURE.md](ARCHITECTURE.md).

| Path | For | Time | You need |
|---|---|---|---|
| **A. Installer** (recommended) | everyone who just wants to use it | 5 min + one-time download | nothing extra |
| **B. Cursor + GitHub** | setting it up from the code, changing the vocabulary/code, or when the installer won't run | 15 min + one-time download | [Cursor](https://cursor.com), Git, Python 3.11 |

Project page: **https://github.com/vivekarya2026/live-captions-obs**

---

## Step 0. Know your computer

| Computer | How to check | Installer file |
|---|---|---|
| **Mac with Apple Silicon** (M1, M2, M3, M4…) | Apple menu → **About This Mac** → *Chip: Apple M…* | `LiveCaptions-…-macOS-arm64.pkg` |
| **Mac with Intel** | Apple menu → **About This Mac** → *Processor: … Intel …* | `LiveCaptions-…-macOS-x86_64.pkg` |
| **Windows 10 / 11 (64-bit)** | Settings → System → About → *System type: 64-bit* | `LiveCaptions-…-Windows-x64-Setup.exe` |

Every computer needs: **macOS 12+ or Windows 10/11**, about **8 GB free space**, and internet for the
first start only (about 4 GB downloads once). After that it works offline.

| Speed | What to expect |
|---|---|
| Mac Apple Silicon | fast; both speech models (0.6B and 1.7B) work |
| Windows with NVIDIA graphics | fast |
| Mac Intel / Windows without NVIDIA | works on the processor; use the **0.6B** speech model (2019+ i5/i7/i9 or Ryzen 5+ recommended) |

**Using OBS?** Install [OBS Studio](https://obsproject.com/) **before** Live Captions and quit it
before installing. OBS is optional.

---

## Path A. Installer (recommended)

### A1. Download

1. Open **https://github.com/vivekarya2026/live-captions-obs/releases/latest**
2. Under **Assets**, click the file for your computer from the Step 0 table.

### A2. Mac (Apple Silicon or Intel)

1. Quit OBS if it is open.
2. Double-click the downloaded `.pkg`.
3. If macOS says *“can't be opened because Apple cannot check it”*:
   1. press **Done**;
   2. open **System Settings → Privacy & Security**;
   3. scroll down and press **Open Anyway** next to *“LiveCaptions… was blocked”*;
   4. confirm with your password, and double-click the `.pkg` again.
4. Click **Continue → Agree → Install**, enter your Mac password.
5. The **Live Captions** window opens in your browser and starts the one-time download
   (progress bar, 10–30 minutes). Keep the computer awake and online.
6. When macOS asks to use the **microphone**, click **Allow**.

Next time: **Applications → Live Captions** (or just open OBS).

### A3. Windows

1. Close OBS if it is open.
2. Double-click `LiveCaptions-…-Setup.exe`.
3. If Windows says *“Windows protected your PC”*: click **More info → Run anyway**.
4. Click **Next** through the setup. Keep **Install the LocalVocal OBS plugin** ticked if you use OBS
   (Windows asks for permission to add it).
5. The **Live Captions** window opens in your browser and downloads the models once.
6. If Windows asks about the microphone: **Settings → Privacy & security → Microphone** → turn on
   *Let desktop apps access your microphone*.

Next time: **Start menu → Live Captions** (or just open OBS).

Now go to **[Step C. First use](#step-c-first-use-every-computer)**.

---

## Path B. Set it up with Cursor from GitHub

Cursor is a code editor with a built-in AI helper (the *agent*). You open the project from GitHub in
Cursor, give the agent one prompt, and it does the setup for you. You can also type the commands
yourself (B5).

### B1. Install the tools (once per computer)

| | Mac (Apple Silicon or Intel) | Windows |
|---|---|---|
| **Cursor** | download from [cursor.com](https://cursor.com), drag to Applications | download from [cursor.com](https://cursor.com), run the installer |
| **Git** | open Terminal, run `xcode-select --install`, click **Install** | install from [git-scm.com](https://git-scm.com/download/win) (all defaults) |
| **Python 3.11** | [python.org 3.11 macOS installer](https://www.python.org/downloads/macos/) (choose a 3.11.x *universal2* installer) or `brew install python@3.11` | [python.org 3.11 Windows installer (64-bit)](https://www.python.org/downloads/windows/); tick **Add python.exe to PATH** |

Use Python **3.11** exactly (not 3.12/3.13): the speech engine is tested with 3.11.

### B2. Get the project into Cursor

1. Open **Cursor** and sign in.
2. On the welcome screen click **Clone repo**
   (or press `Cmd+Shift+P` / `Ctrl+Shift+P`, type **Git: Clone**, press Enter).
3. Paste the address and press Enter:
   ```
   https://github.com/vivekarya2026/live-captions-obs.git
   ```
4. Choose a folder (e.g. *Documents*), then click **Open** when Cursor asks.

You now see the project files on the left (`app`, `docs`, `obs`, `installer`…).

### B3. Let the Cursor agent do everything

The project has a file called [`AGENTS.md`](../AGENTS.md). It is a full instruction sheet for
coding agents: how to check your computer, install, test, connect OBS, fix problems and release.
Cursor's agent reads it by itself. So one prompt is enough, on any computer.

1. Open the agent chat: `Cmd+L` (Mac) or `Ctrl+L` (Windows). Make sure the mode is **Agent**.
2. Paste this prompt and press Enter:

```
Set up Live Captions on this computer by yourself. Follow AGENTS.md, Task A, from step 1 to step 9.
First check what computer this is (Apple Silicon Mac, Intel Mac or Windows) and use the matching
commands. Install from source in this folder, download the models, run the self-test, and start the
app. If OBS is installed, ask me to quit it, then connect it. Don't skip any check. After each step,
tell me in one or two plain sentences what you did and what happened. Ask me before anything that
needs my password, deletes data, or changes OBS. At the end, tell me how to start it next time and
anything you couldn't check.
```

3. When the agent wants to run a command, click **Run** (or **Accept**). Answer its questions.
4. The model download takes 10–30 minutes. You can leave it running.

Other prompts that work the same way:

| You want to… | Paste this |
|---|---|
| Just install the ready-made app | `Follow AGENTS.md Task A, but use the installer path: download the right installer for this computer from the latest GitHub release and help me install it.` |
| Fix a problem | `Live Captions isn't working: <what you see>. Follow AGENTS.md Task B.` |
| Change something | `<the change you want>. Follow AGENTS.md Task C and run the tests.` |
| Publish a new version | `Release a new version of Live Captions. Follow AGENTS.md Task D.` |

**Using a different coding agent** (Claude Code, Codex, Copilot…)? Most of them read `AGENTS.md` too.
If yours doesn't, start the prompt with: *Read AGENTS.md in this folder first.*

**Or: build an installer on this computer** (to copy to other computers without internet to GitHub)

```
Build the Live Captions installer for this computer following README.md
(Mac: installer/macos/build.sh, add ARCH=x86_64 for an Intel Mac package;
Windows: installer\windows\build.ps1, needs Inno Setup 6). Tell me where the finished file is.
```

### B4. Using Cursor to change things later

Ask the agent in plain words, for example:

- *“Add the term ‘Sangat’ to the vocabulary so it is always spelled that way in captions.”*
  (The vocabulary sheet is `app/livecaptions/data/vocabulary/Vocabulary_for_Live_Translations.xlsx`;
  you can also edit it in Excel, changes apply live.)
- *“Update to the newest version from GitHub.”* (the agent runs `git pull`)
- *“Captions stopped; check ~/.livecaptions/translator.log and fix it.”*

### B5. The same steps by hand (Cursor terminal)

Open the terminal in Cursor: **Terminal → New Terminal** (`` Ctrl+` ``). It opens in the project folder.

**Mac with Apple Silicon**

```bash
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
cd app
../.venv/bin/python -m livecaptions --download # one-time download (speech engine + models, ~4 GB)
../.venv/bin/python -m livecaptions --test     # self-test: translates sample sentences
../.venv/bin/python -m livecaptions            # opens the window
```

**Mac with Intel processor**

```bash
python3.11 -c "import platform; print(platform.machine())"   # must say x86_64
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt "numpy<2" --only-binary=:all:
cd app
../.venv/bin/python -m livecaptions --download
../.venv/bin/python -m livecaptions --test
../.venv/bin/python -m livecaptions
```

During `--download` the app installs PyTorch 2.2.2 (the last version for Intel Macs) by itself.

**Windows (PowerShell)**

```powershell
py -3.11 -m venv .venv
.venv\Scripts\pip install -r requirements.txt
cd app
..\.venv\Scripts\python -m livecaptions --download
..\.venv\Scripts\python -m livecaptions --test
..\.venv\Scripts\python -m livecaptions
```

**Connect to OBS (any computer, optional).** Quit OBS first, then from the `app` folder:

```bash
../.venv/bin/python -m livecaptions.obs_setup          # Mac
../.venv/bin/python -m livecaptions.install_localvocal # Mac: adds the LocalVocal plugin
```

```powershell
..\.venv\Scripts\python -m livecaptions.obs_setup           # Windows
..\.venv\Scripts\python -m livecaptions.install_localvocal  # Windows
```

OBS then starts Live Captions by itself from the project's `.venv`. Don't move or delete the project
folder afterwards (OBS points to it).

**Next time (without OBS):** open the project in Cursor, open a terminal, and run the last line
(`cd app` then `../.venv/bin/python -m livecaptions`, or `..\.venv\Scripts\python -m livecaptions`
on Windows). Or ask the agent: *“Start Live Captions.”*

---

## Step C. First use (every computer)

1. Wait until the download in the window says it is ready (only the first time).
2. **Language**: choose who speaks which language, e.g. **Hindi → English**.
3. **Microphone**: pick the mic and check the level moves when you speak.
4. **Speech model**: **0.6B** on Intel Macs and PCs without NVIDIA; **1.7B** is more accurate on fast computers.
5. Switch **Captions ON**. Speak a sentence; the original and translation appear.
6. **Mic on/off**: turning listening off releases the microphone completely (the orange mic dot on
   Mac goes away).
7. Sessions are saved in **Documents → Live Captions** (transcript, translation, `.srt`, `.csv`).
8. **Quit** (top right) when you are done.

**With OBS:** just open OBS. The captions overlay is added to your scene; the panel is under
**Docks → Live Captions** (OBS 30+: **View → Docks**).

### Google Docs (optional, once per document)

Short version (full guide with every screen explained: [GOOGLE_DOCS.md](GOOGLE_DOCS.md)):

1. Open the Google Doc → **Extensions → Apps Script**.
2. Replace the code with the script from the Live Captions window (**Google Docs → Copy script**), **Save**.
3. **Deploy → New deployment → Web app**, *Execute as: Me*, *Who has access: Anyone* → **Deploy** →
   **Authorize** (→ *Advanced → Go to … (unsafe) → Allow*).
4. Reload the doc → **Live Captions → Open sidebar** → **Copy connection link**.
5. Paste the link into the Live Captions window (**Google Docs → Connect**).
6. Each time: sidebar → **Start writing** … **Stop writing**.

The Google Docs part is per document, not per computer: on a new computer, only step 5 is needed
(paste the same connection link).

---

## Setting up several computers

| Task | How |
|---|---|
| Same version everywhere | download the installers from the same release page (the version is in the file name) |
| Computers without fast internet | copy the models instead of downloading: copy the folder `~/.livecaptions/models` (Mac) or `%USERPROFILE%\.livecaptions\models` (Windows) from a set-up computer to the same place on the new one, *then* install |
| Same Google Doc from two computers | paste the same connection link in both; only start writing on one at a time |
| Update | install the newer release over the old one (settings and models stay), or in Cursor: *“Update to the newest version from GitHub”* |

## Uninstall

| Computer | How |
|---|---|
| Mac (installer) | quit OBS, then in Terminal: `"/Applications/Live Captions.app/Contents/Resources/uninstall.sh"` (add ` --all` to also delete models) |
| Windows (installer) | Settings → Apps → Live Captions → Uninstall |
| Cursor / source | run `python -m livecaptions.obs_setup --remove` from `app` (if you used OBS), then delete the project folder and `~/.livecaptions` |

## Problems

| Problem | Fix |
|---|---|
| Mac: *can't be opened because Apple cannot check it* | System Settings → Privacy & Security → **Open Anyway** (A2 step 3) |
| Mac installer refuses to install on this computer | you downloaded the wrong Mac file; check Step 0 (Apple Silicon = `arm64`, Intel = `x86_64`) |
| Windows: *Windows protected your PC* | **More info → Run anyway** |
| Window says *Live Captions is not running* | start it again (Applications / Start menu / `python -m livecaptions`) |
| No captions | correct mic chosen and not muted? Mac: System Settings → Privacy & Security → Microphone → allow *Live Captions* (or *OBS*, or *Cursor* when run from Cursor) |
| Download stopped | press **Try again** in the window; it continues where it stopped |
| Captions come late (Intel Mac / PC without NVIDIA) | choose the **0.6B** speech model; close other heavy apps |
| `python3.11: command not found` / `py -3.11` not found | install Python 3.11 (B1) and open a new terminal |
| Intel Mac: *A module compiled with NumPy 1.x cannot run in NumPy 2* | `.venv/bin/pip install "numpy<2" --only-binary=:all:` |
| OBS has no Live Captions panel | quit OBS, start Live Captions once, then open OBS |

Log file for reports: `~/.livecaptions/translator.log` (Mac) · `%USERPROFILE%\.livecaptions\translator.log` (Windows).
Report problems at https://github.com/vivekarya2026/live-captions-obs/issues (attach the log).
