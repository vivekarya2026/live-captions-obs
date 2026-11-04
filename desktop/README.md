# Live Captions desktop app

The menu bar / system tray app: Live Captions, Vocabulary, Documents, Dictation, History, Models.
Tauri v2 (Rust in `src-tauri/`, React in `src/`). It starts the Python engine in `../app` and talks
to it on 127.0.0.1:8765.

- Project map: [../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md)
- Agent instructions (build, checks): [../AGENTS.md](../AGENTS.md)

```
bun install
bun run tauri dev            # run from source (uses ../.venv)
bun run tauri build          # Live Captions.app (installers: ../installer/)
```

Checks: `npx tsc --noEmit && bun run lint`, `cd src-tauri && cargo test --lib`.

Built on [Handy](https://github.com/cjpais/Handy) by CJ Pais and contributors (MIT, see `LICENSE`).
