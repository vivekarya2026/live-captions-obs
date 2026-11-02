# Third-party software and models

Live Captions downloads or bundles the following. Each keeps its own licence.

| Part | Used for | Licence |
|---|---|---|
| [Python](https://www.python.org/) via [python-build-standalone](https://github.com/astral-sh/python-build-standalone) | runs the app (bundled) | PSF License |
| [Qwen3-ASR](https://github.com/QwenLM/Qwen3-ASR) 0.6B / 1.7B | speech recognition (downloaded on first start) | Apache 2.0 |
| [NLLB-200 distilled 1.3B](https://huggingface.co/facebook/nllb-200-distilled-1.3B), [CTranslate2 int8 conversion](https://huggingface.co/OpenNMT/nllb-200-distilled-1.3B-ct2-int8) | translation (downloaded) | CC-BY-NC 4.0 (non-commercial) |
| [Qwen2.5-0.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct), our CTranslate2 int8 conversion (`LiveCaptions-model-meaning.zip`) | caption styles *Natural* / *Simple* (downloaded only when chosen) | Apache 2.0 |
| [CTranslate2](https://github.com/OpenNMT/CTranslate2) | runs the translation model (bundled) | MIT |
| [PyTorch](https://pytorch.org/) | runs the speech model (downloaded) | BSD-3-Clause |
| [Silero VAD](https://github.com/snakers4/silero-vad) | detects when someone is speaking (downloaded) | MIT |
| [sounddevice](https://github.com/spatialaudio/python-sounddevice) / PortAudio | microphone input (bundled) | MIT |
| [LocalVocal](https://github.com/royshil/obs-localvocal) | Whisper captions inside OBS until Qwen3 is downloaded (installed separately, unchanged) | GPL-2.0 |
| [FrequencyWords](https://github.com/hermitdave/FrequencyWords) (Hindi, OpenSubtitles 2018) | list of common Hindi words, `app/livecaptions/data/hindi_words.txt` | MIT (word list); data from OpenSubtitles |
| openpyxl, sentencepiece, tokenizers, huggingface_hub, numpy, certifi | vocabulary sheet, tokenizers, downloads | MIT / Apache 2.0 / BSD / MPL-2.0 |

The Nirankari vocabulary sheet (`app/livecaptions/data/vocabulary/`) is included with permission of its author.
