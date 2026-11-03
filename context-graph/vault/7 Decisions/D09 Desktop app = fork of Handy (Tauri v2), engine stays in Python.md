---
id: decision:D09
type: "decision"
why: "The user asked for Handy's UI and features (dictation, history, overlay, tray, onboarding, themes) with our pipeline. Rewriting Qwen3 + NLLB + vocabulary + styles in Rust would have duplicated tested code; a local helper process keeps one pipeline for OBS, the window and dictation"
revisit_when: "if the Python install becomes the main support problem"
---
# Desktop app = fork of Handy (Tauri v2), engine stays in Python

**why:** The user asked for Handy's UI and features (dictation, history, overlay, tray, onboarding, themes) with our pipeline. Rewriting Qwen3 + NLLB + vocabulary + styles in Rust would have duplicated tested code; a local helper process keeps one pipeline for OBS, the window and dictation

**revisit when:** if the Python install becomes the main support problem

## Links
- about [[Caption overlay]] *(keyword match)*
- about [[App window and OBS dock]] *(keyword match)*
- about [[OBS setup]] *(keyword match)*
- about [[Speech to text]] *(keyword match)*
- about [[Translation]] *(keyword match)*
- about [[Caption style]] *(keyword match)*
- about [[Vocabulary terms]] *(keyword match)*
- about [[Desktop app]] *(keyword match)*
- about [[Dictation]] *(keyword match)*
