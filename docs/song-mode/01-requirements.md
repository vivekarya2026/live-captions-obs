# Song mode: requirements (Day 1, Define)

Status: **Approved** (Gate 1).
Marked **[you]** = you said it. **[me]** = my guess, please check.

## The problem in one line

When a bhajan or shabad is sung, the live captions today try to translate the singing word by word. That gives broken, wrong lines, and viewers lose the meaning. A song already has correct lyrics and a correct translation, so the app should show those instead. **[you]**

## Jobs to be done

Format: *When … I want to … so I can …*

**Viewer (main job)**
- *When* a song is sung on the stream, *I want to* read the real words and what they mean, *so I can* sing along and understand it.
- How they want to feel: included and moved, not confused. **[me]**
- In front of others: they can sing along correctly. **[me]**

**Operator (the sevadar at the laptop)**
- *When* the singer starts a song, *I want* the right lyrics to come up on their own, *so I can* keep my eyes on the stream, not on the app.
- How they want to feel: calm. A wrong line on a live stream is embarrassing. **[me]**
- In front of others: the stream looks well done. **[me]**

**Song librarian (who adds songs, may be the same person)**
- *When* I have songs in a Word file, PDF, Excel or plain text, *I want to* drop them in once, *so I can* stop retyping or formatting them. **[you]**

### Where today's tools fall short
| Today | Gap |
|---|---|
| Word-for-word captions of singing | Singing is hard to hear: long vowels, music, echo. The lines come out wrong |
| Operator types or pastes lyrics by hand | Too slow during a live song; they miss lines |
| Slides with lyrics (PowerPoint) | Someone must click every line; no translation under it; not in the document |

## People (personas)

These are my guesses from what we know about satsang streams; there were no interviews (plan option B wasn't chosen).

**1. Operator: "Harpreet", 35, sevadar, primary persona**
- Quote: *"I can't watch the singer and the laptop at the same time."*
- Tech comfort: medium. Uses OBS, but isn't technical.
- Goals: the right lyrics on screen with no typing, and a quick fix when the app is wrong.
- Frustrations: tiny buttons, unclear states, things that silently stop working.
- Design impact:
  - One big "Wrong song" / "Next line" control.
  - The app never shows a line it isn't sure about.
  - The status is always visible.
- Why primary: if the operator doesn't trust it, it gets turned off, and the viewer gets nothing.

**2. Viewer: "Kamla", 62, watches from home**
- Quote: *"I know the tune, I want the words."*
- Some viewers hear poorly; some don't read Hindi, or don't know Punjabi.
- Design impact:
  - Big, steady text, at most two lines.
  - The original line first, then the translation.
  - No flicker or jumping back and forth.

**3. Song librarian: "Anil", 28**
- Has hundreds of songs in mixed files, with Hindi and Punjabi written in Devanagari or Roman letters. **[you]**
- Design impact:
  - Accept any file, and split it into songs and lines on its own.
  - Show what it understood and let Anil fix it.
  - Never lose the original file.

## Journey: one song, operator's view

| Stage | Operator does | Feels | Pain today | Opportunity |
|---|---|---|---|---|
| 1. Before satsang | Makes sure the songs are in the library | ok | Lyrics are scattered in files | Upload once; the app keeps a library |
| 2. Song starts | Hears the first line | tense | Captions show nonsense | The app listens and says *"Sounds like: Tu Hi Nirankar"* |
| 3. Song is found | Glances, confirms or not | relief | n/a | One tap to confirm or say "wrong song" **(moment of truth)** |
| 4. Song goes on | Watches the stream | calm | n/a | The app follows line by line, and the translation shows under each line |
| 5. Singer repeats or skips | Nothing, unless it's wrong | small worry | Slides get out of step | The app follows repeats; "back" and "next" are one tap |
| 6. Song ends | Nothing | good | Old lyrics stay on screen | The app goes back to normal captions on its own |
| 7. After | Opens the document | proud | The document has broken lines | The document has the clean lyric and translation, marked as a song |

**Moments of truth:** stage 3 (the first guess must be right or easy to reject) and stage 6 (it must let go when the song ends).

**Top opportunities, by impact × ease:**
1. Recognize the song from the first lines.
2. Show the lyric plus translation on the stream.
3. One-tap corrections.
4. Upload anything.
5. Clean lyrics in the document.

## Requirements (MoSCoW)

### Must
1. **Upload songs in any file**: .docx, .pdf, .xlsx/.csv, .txt, or pasted text. **[you]** One file can hold one song or many. The original file is kept.
2. **Own song library**: the app keeps songs in its own database. **[you]** Each song has a title, language (Hindi, English or Punjabi **[you]**) and lines; each line has its original text and its translations.
3. **Mixed scripts**: Punjabi or Hindi in Devanagari or Roman letters must match what the singer sings. **[you]**
4. **Recognize the song while it's sung**: from what the app hears. **[you]**
5. **Follow line by line**: show the current line plus its translation. **[you]**
6. **Operator can correct it**: confirm, wrong song, back, next, stop. **[you]**
7. **Never stall**: when unsure or lost, fall back to normal captions (rule C5). Never show a line the app isn't sure about.
8. **Same output targets**: the overlay on the stream and the document / transcript (Google Docs, saved sessions). **[you]**
9. **Offline**: everything runs on the computer (rule C1). **[me]**
10. **Use only the given translations**: no machine translation of lyrics. **[me]** (If a line has no translation, show only the original line.)

### Should
11. Show which translation the viewer gets, following the caption language already chosen (for example Hindi to English → English under the line).
12. Operator can search for a song and start it by hand.
13. Show the next line greyed in the app (not on the stream), so the operator sees what's coming.
14. After upload, preview what was understood (songs, lines, translations) and allow fixing before saving.
15. Repeated lines (chorus) are followed correctly.

### Could
16. Show two lines on the stream (current plus next) as a setting.
17. Mark songs as favourites, or set a song list for today's satsang, so the matching is faster and more accurate.
18. Export the library, to share with another computer.

### Won't (this time)
- Recognize a song from the music alone, with no words (like Shazam).
- Write new translations with AI.
- Punjabi in Gurmukhi script (you chose Devanagari and Roman). It's easy to add later.

## Success measures (HEART: task success first)

| Measure | How measured | Target (first version) |
|---|---|---|
| Time to find the song | Lines sung before the right song is shown | within **2 lines** for songs in the library |
| Wrong lines on stream | Wrong lyric lines shown ÷ all lyric lines shown | under **2%** |
| Lost place | Times it falls back to normal captions in the middle of a song | at most 1 per song |
| Operator fixes | Taps needed per song | 0 most of the time, never more than 1 to fix a wrong song |
| Upload works | Songs read right from a file without manual fixing | 9 of 10 |
| Operator feeling | Ask after a satsang: "Would you leave it on?" | yes |

Baseline: today, 0 songs show correct lyrics. The test set is the 3–5 recordings for the feasibility test.

## Decisions (Gate 1, approved 2026-11-03)
- Requirements approved as written.
- **Q1:** while a song plays, the lyric line **replaces** the normal captions.
- **Q2:** the translation under a line **follows the caption language already chosen** (Hindi → English shows English).
- **Q3:** real recordings will come later. For now, the feasibility test uses recordings made on this computer.
