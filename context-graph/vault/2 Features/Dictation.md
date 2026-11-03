---
id: feature:dictation
type: "feature"
does: "Hold a shortcut, speak, the translated text is typed into any app (POST /dictate)"
---
# Dictation

**does:** Hold a shortcut, speak, the translated text is typed into any app (POST /dictate)

## Links
- must respect [[C1 Runs offline on the computer; only Google Docs uses the internet (text]]
- must respect [[C5 Never stall the captions- fall back instead of waiting]]
- built in [[desktop-src-tauri-src-actions.rs]]
- built in [[desktop-src-tauri-src-live_captions.rs]]
- built in [[app-livecaptions-translator.py]]
- built in [[app-livecaptions-qwen_engine.py]]

## Linked from
- [[R22 Deliver it with Handy's UI and features (dictation, history, overlay,]] (answered by)
- [[D09 Desktop app = fork of Handy (Tauri v2), engine stays in Python]] (about)
- [[D10 Dictation goes through -dictate, not Handy's Whisper]] (about)
- [[E14 Dictation endpoint]] (is evidence for)
- [[E15 Custom words apply to dictation]] (is evidence for)
- [[E16 Web pages can't post to the engine]] (is evidence for)
