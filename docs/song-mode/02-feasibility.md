# Song mode: feasibility test (Day 1–2)

Status: **Approved** (Gate 2, 2026-11-03): suggest and confirm; the 1.7B speech model is used while Song mode is on, if it's downloaded (otherwise the selected model).

## The question

Can the app tell **which song** is being sung, and **which line**, from what the speech model hears? Singing is harder to hear than speech.

## How it was tested

- 6 test songs, written for this test so there are no copyright issues:
  - Hindi in Devanagari, Hindi in Roman letters;
  - Punjabi in Roman letters, Punjabi in Devanagari;
  - English;
  - plus one song that shares words with another on purpose (a decoy).
- One song **not** in the library, which must never be shown.
- 9 situations:
  - from the start, starting mid-song, the chorus repeated, the singer jumping back to verse 1;
  - the decoy, the unknown song;
  - each script and language.
- Three levels:
  1. **Text, exact words:** does the matching logic work?
  2. **Text, misheard words** (about 1 in 4 words missing or wrong): does it survive mistakes?
  3. **Audio through the real speech model:** the Mac's Hindi or English voice, slowed down, with a harmonium-like drone and hall echo under it. Then run through Qwen3-ASR, the model the app uses.
- Run it yourself: `cd app && ../.venv/bin/python ../tests/test_songs.py --audio qwen-1.7b`

## Results

| | Song found within 2 lines | Lines shown (of 44) | **Wrong lines shown** | Unknown song shown |
|---|---|---|---|---|
| Text, exact | 8 of 8 songs | 44 (100%) | **0** | 0 |
| Text, misheard | 8 of 8 | 42 (95%) | **0** | 0 |
| Audio, Qwen3 0.6B | 8 of 8 | 38 (86%) | **0** | 0 |
| Audio, Qwen3 1.7B | 8 of 8 | 43 (98%) | **0** | 0 |

What the numbers mean:
- **It never showed a wrong line, and never showed the unknown song.** When unsure, it shows nothing, and normal captions stay. That's the rule we agreed: never show a line it isn't sure about.
- **The song is found from the first or second line**, every time.
- **The weak spot is Punjabi in Devanagari with the small model:** only 1 of 5 lines followed, because the 0.6B model misheard the Punjabi badly (for example "नाम दा रंग" → Korean letters). With 1.7B it followed 4 of 5.
- **The decoy didn't fool it:** two songs with the same words ("तेरा नाम", "सहारा", "हर पल") were never mixed up.
- **Misheard words are fine:** "शुकर" → "शुक्र", "दाता" → "डाटा" and "प्रेम" → "frame" still matched, because Devanagari and Roman letters are compared in one loose spelling.

## How sure are we? (FPF: evidence and its limits)

| Claim | Evidence | How reliable |
|---|---|---|
| The matching logic is right | text tests, exact and misheard | **high** |
| It works on the speech model's real mistakes | audio through Qwen3, both sizes | **medium** |
| It works on **real singing** | none yet: a computer voice is not a singer (no melody, no held notes, no tabla, no crowd) | **unknown** |

Real singing will be harder: held notes, music louder than the voice, the sangat singing along. Expect fewer lines followed than in this test. The design must keep working when that happens, and it does: when unsure it shows normal captions, and the operator can step lines.

## Decision proposed

**Go with "suggest and confirm" (concept B) as the default, using the 1.7B model for songs.**
- Auto-follow is safe in this test: there were 0 wrong lines. But real singing isn't tested, so for now the operator confirms the song once with one tap, then the app follows on its own.
- Manual stepping is always there as the fallback (concept C), so a song with poor audio still works.
- When the real recordings come (Q3), rerun this test with them. If wrong lines stay at 0, auto-follow can become the default.

The concept round (next stage) checks this against the other two concepts.
