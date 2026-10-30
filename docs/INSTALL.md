# Installing Live Captions

Live Captions writes live captions and translations (**English ↔ Hindi / Hinglish**,
with the Nirankari vocabulary). You can use it:

- **with OBS**: captions on your stream or recording, and a *Live Captions* panel inside OBS;
- **without OBS**: its own window, for meetings or satsang notes;
- **with Google Docs**: the speech and its translation are written into a document
  as people speak (see [GOOGLE_DOCS.md](GOOGLE_DOCS.md)).

Everything runs on your own computer. Audio never leaves it.

## What you need

| | Mac | Windows |
|---|---|---|
| Computer | Apple Silicon (M1 or newer) or Intel, macOS 12 or newer | Windows 10 or 11, 64-bit |
| Space | about 8 GB free | about 8 GB free |
| Internet | only for the first start (downloads about 4 GB once) | same |
| Speed | fast on Apple Silicon; Intel Macs work on the processor alone (a 2019+ Intel i5/i7/i9 keeps up; use the 0.6B speech model) | fast with an NVIDIA graphics card; slower without one (uses the smaller speech model) |

Not sure which Mac you have? Apple menu → **About This Mac**: “Chip: Apple M…” = Apple Silicon,
“Processor: … Intel …” = Intel.

OBS is optional. If you use it, install [OBS Studio](https://obsproject.com/) **first**.

## Download

Open the [latest release](https://github.com/vivekarya2026/live-captions-obs/releases/latest) and download:

- **Mac with Apple Silicon (M1 or newer)**: `LiveCaptions-…-macOS-arm64.pkg`
- **Mac with Intel processor**: `LiveCaptions-…-macOS-x86_64.pkg`
- **Windows**: `LiveCaptions-…-Windows-x64-Setup.exe`

## Mac

1. **Quit OBS** if it is open.
2. Double-click the `.pkg`. If macOS says it *can't be opened because Apple cannot check it*:
   press **Done**, open **System Settings → Privacy & Security**, scroll down and press
   **Open Anyway** next to “LiveCaptions… was blocked”. (This happens because the
   installer isn't paid-signed by Apple.)
3. Click **Continue → Agree → Install** and enter your Mac password.
4. The **Live Captions** window opens in your web browser and downloads the models
   (progress bar; 10–30 minutes once). Allow the **microphone** when macOS asks.

Later, start it from **Applications → Live Captions** (or just open OBS).

**Uninstall:** quit OBS, then in Terminal run
`"/Applications/Live Captions.app/Contents/Resources/uninstall.sh"`
(add ` --all` to also delete the downloaded models).

## Windows

1. **Close OBS** if it is open.
2. Double-click `LiveCaptions-…-Setup.exe`. If Windows says *Windows protected your PC*:
   click **More info → Run anyway**. (The installer isn't paid-signed by Microsoft.)
3. Click through the setup. Keep **Install the LocalVocal OBS plugin** ticked if you use OBS;
   Windows then asks for permission to add it to OBS.
4. The **Live Captions** window opens in your web browser and downloads the models once.

Later, start it from the **Start menu → Live Captions** (or just open OBS).

**Uninstall:** Settings → Apps → Live Captions → Uninstall.

## Using it

**With OBS:** open OBS. Captions start on their own; the panel is under
**Docks → Live Captions** (OBS 30+: **View → Docks**). Choose the language there.

**Without OBS:** open **Live Captions**. In its window:

- **Language**: who is speaking which language (e.g. *Hindi → English*).
- **Microphone**: pick the mic, volume, mute.
- **Captions ON/OFF**: the big switch.
- Every session is saved in **Documents → Live Captions** (transcript, translation,
  subtitles `.srt`, spreadsheet `.csv`).
- **Quit** (top right) stops listening. If you just close the window, Live Captions
  stops by itself after 3 minutes, unless it is writing into a Google Doc or OBS is open.

## Something isn't working

| Problem | Fix |
|---|---|
| Window says *Live Captions is not running* | Start Live Captions again from Applications / Start menu. |
| No captions | Check the mic in the window (Microphone → Mic), and that it isn't muted. On Mac: System Settings → Privacy & Security → Microphone → allow *Live Captions* (or *OBS*). |
| Download stopped | Press **Try again** in the window (it continues where it stopped). |
| OBS has no Live Captions panel | Quit OBS, start Live Captions once (it finishes adding itself to OBS), then open OBS. |

The log file is `~/.livecaptions/translator.log` (Mac) or
`%USERPROFILE%\.livecaptions\translator.log` (Windows); send it along when you report a problem.
