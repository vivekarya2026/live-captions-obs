# Live Captions for OBS

Live captions and translation, **English ↔ Hindi / Hinglish**, for satsang, meetings and
live streams, using the Nirankari vocabulary (Sewa, Simran, Satguru, Nirankar… spelled
exactly as in the vocabulary sheet).

- **With OBS**: captions on your stream, a *Live Captions* panel in OBS to choose the language and mic.
- **Without OBS**: its own window.
- **Google Docs**: writes the speech and its translation into a document as people speak.
- Saves every session (transcript, translation, `.srt` subtitles, `.csv`) in *Documents → Live Captions*.
- Polite captions: abusive words are removed.
- Runs **offline on your own computer** after a one-time model download. Audio never leaves it.

**[Download and install →](docs/INSTALL.md)** · [Google Docs setup](docs/GOOGLE_DOCS.md)

| Caption mode | Speaker uses | Captions in |
|---|---|---|
| Hindi → English | Hindi / Hinglish | English |
| English → Hinglish | English | Hindi in Roman letters |
| English → हिंदी | English | Hindi (Devanagari) |
| Auto | either | the other language |

## How it works

```
microphone ─► Qwen3-ASR (speech → text, with the vocabulary as context)
            ─► spelling + vocabulary fixes ─► NLLB-200 translation ─► vocabulary terms restored
            ─► OBS caption overlay · app window · Google Doc · session files
```

| Part | What it is |
|---|---|
| `app/livecaptions/` | the app (Python): speech, translation, vocabulary, window, Google Docs link |
| `app/livecaptions/data/vocabulary/` | the vocabulary sheet (`Vocabulary_for_Live_Translations.xlsx`), Hindi terms, blocked words. Edit the sheet; changes apply live |
| `app/livecaptions/data/google-docs/LiveCaptions.gs` | the Google Docs sidebar script |
| `obs/live_captions.lua` | OBS script: starts the app with OBS, adds the caption overlay |
| `installer/` | Mac `.pkg` and Windows `.exe` builders (GitHub Actions builds both on a `v*` tag) |

### Run from source (developers)

```bash
python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt
cd app && ../.venv/bin/python -m livecaptions            # opens the window, downloads models
../.venv/bin/python -m livecaptions --test               # translate sample sentences
../.venv/bin/python ../tests/test_vocabulary.py          # every vocabulary term, every mode
```

Build the Mac installer: `installer/macos/build.sh` → `dist/`.
Release: `git tag v1.0.1 && git push --tags` (Actions builds Mac + Windows and publishes them).

## Licence

Free for **non-commercial** use: [PolyForm Noncommercial 1.0.0](LICENSE).
The translation model (NLLB-200) is also non-commercial only. Other parts: [THIRD_PARTY.md](THIRD_PARTY.md).
