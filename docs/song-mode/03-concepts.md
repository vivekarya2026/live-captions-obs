# Song mode: concepts and choice (Day 2, Ideate)

Status: **Approved** (Gate 3, 2026-11-03): concept B, suggest and confirm.

## The question these concepts answer

**Who decides that a song has started, and which line is on screen: the app, the operator, or both?** That's the dimension the three concepts differ on: who does what. All three use the same library, the same overlay look and the same matcher.

## Criteria (fixed before comparing)

From the approved requirements and the feasibility evidence.

| # | Criterion | Type |
|---|---|---|
| K1 | Never shows a wrong song on the stream | **threshold** (fail = out) |
| K2 | Works when hearing is poor (real singing isn't tested yet) | **threshold** |
| K3 | Operator taps per song: 0–1 normally | trade-off |
| K4 | Operator can look away from the laptop | trade-off |
| K5 | Lyrics appear by the 2nd line | trade-off |

## Concept A: Auto-follow

- **Who decides:** the app does everything. When it's sure of the song, the lyric goes on the stream; when it's lost, normal captions come back.
- **The operator:** does nothing, but can press "Wrong song" or "Stop" afterwards.
- **Sketch, on the stream:**

  ```
  मन में तेरा नाम बसा है
  Your name lives in my heart
  ```
- **What it tests:** whether the app alone is trustworthy enough.

## Concept B: Suggest and confirm (proposed in Gate 2)

- **Who decides:** the app proposes, the operator confirms the song once, then the app follows the lines.
- **Before confirming:** normal captions continue, and the app shows a card: *"Sounds like **Man Mein Tera Naam** · line 1 · [Show lyrics] [Not this]"*.
- **Saying nothing for 1 line:** the card stays; nothing goes on the stream without the tap.
- **After the tap:** the app follows line by line. "Back", "Next" and "Stop" are always there.
- **What it tests:** whether one human tap is the right price for safety.

## Concept C: Operator-led

- **Who decides:** the operator searches for and starts the song.
- **Lines:** the app follows the lines if it can hear them; otherwise the operator presses "Next" (space bar).
- **What it tests:** whether listening is even needed.

## Scoring

| | A Auto | B Suggest + confirm | C Operator-led |
|---|---|---|---|
| K1 no wrong song | **at risk:** 0 wrong in tests, but real singing is unknown | **pass:** a human confirms | **pass** |
| K2 poor hearing | pass: falls back to captions | pass: falls back, and the operator can step | **pass**, best |
| K3 taps per song | **0** | 1 | 1 search + up to 1 per line |
| K4 look away | **yes** | after 1 glance | no |
| K5 by line 2 | **yes** | yes, if the operator taps fast | depends on the operator |

## Decision

**B, suggest and confirm.**
- **Why:** it's the only concept that passes both thresholds *and* keeps operator work near zero.
  - A fails K1 until there's evidence from real singing.
  - C passes everything, but makes the operator work every line, which is the thing the operator persona told us they can't do.
- **What B costs:** one tap per song, and a short delay. The first line of the song may show as normal captions before the tap.
- **What would change this decision:** when real recordings show **0 wrong songs**, offer a setting, *"Show songs without asking"*, which is Concept A. This is a setting, not a new design, because B already contains A's following.

## The rejected concepts, kept for later

| Concept | What it tested | Lost on | Brings it back |
|---|---|---|---|
| A Auto-follow | Can the app be trusted alone? | K1, unproven with real singing | Real recordings: 0 wrong songs over ~20 songs → "Show songs without asking" setting |
| C Operator-led | Is listening needed? | K3/K4: too much work during a live song | If real singing is followed under ~50% of lines. Its search + Next is kept in B as the manual fallback, which is B's own, not a graft |
