# Song mode: test (Day 4)

Status: **Approved** (Gate 5, 2026-11-03).

## Part 1. Expert review of the prototype (heuristic evaluation)

One evaluator (me), walking through the flows in [04-prototype.md](04-prototype.md):
- as a first-time librarian;
- as an operator during a song;
- as an operator who has used it before.

Severity: 0 none, 1 cosmetic, 2 minor, 3 major, 4 must fix.

| # | Heuristic | Problem | Where | Sev | Fix (goes into the build) |
|---|---|---|---|---|---|
| H1 | Visibility of status | The operator can't tell whether the app is listening for songs, or whether the song library is empty, from the Live Captions page | Live Captions page | 3 | Show a small status chip: *"Songs: listening (24 songs)"*, *"Songs: off"* or *"Songs: no songs yet"*. Clicking it opens Songs |
| H2 | User control | After *Not this*, the right song can't be picked fast | card | 3 | Under the card's buttons, add *"Pick the song…"*, which opens the search in place, with the best 3 guesses on top |
| H3 | Error prevention | Deleting a song that's playing now | Songs list | 3 | The delete button is off for the song that's playing. Its tooltip says *"Stop the song first"* |
| H4 | Visibility of status | The card stays 45 s. If the operator misses it, the moment is gone | card | 2 | When the operator hasn't tapped, a gentle pulse after 10 s, and the footer chip shows ♪ |
| H5 | Recognition over recall | Keyboard keys aren't shown | bar | 2 | Show key hints on the buttons: ← Back, Next →, Esc Stop |
| H6 | Match real world | "Line 3 of 8" is fine, but a chorus repeated makes it jump back (3 → 1) and look broken | bar | 2 | When the singer goes back to a repeated line, write *"chorus"* next to the line number |
| H7 | Error recovery | The Check page can't fix a translation that's put under the wrong line (shifted by one) | Check page | 3 | In edit, add *"Translation is one line off"* with ↑ and ↓ to shift the translations |
| H8 | Consistency | The Songs page needs the same table look as Vocabulary and Models | Songs page | 1 | Use the same row grid and buttons |
| H9 | Help | No sample of a good file | Add songs | 2 | Add a link, *"Download an example file"*, an Excel file with 2 songs |
| H10 | Minimalist | The "heard:" line on the card adds noise once you trust it | card | 1 | Keep it. It's what lets the operator say *"Not this"* with confidence |

All severity 3 and 2 fixes go into the build.

## Part 2. Test scenarios for a live run

You approve these before they're run (HITL). They're run with the built app, from recordings or a real singer, in the order below.

Each scenario lists success criteria; what to watch is in the note.

**S0. Warm-up.** *"You've been given a Word file of bhajans for Sunday. Get them into the app."*
- Success: songs saved within 3 minutes, with no help.
- Watch: does the person find Songs? Do they trust the Check page?

**S1. A known song from the start.** *"The singer is about to start Man Mein Tera Naam. Get the lyrics on the stream."*
- Success: the card shows by line 2; 1 tap; the stream shows the right lines; 0 wrong lines.
- Watch: how long until they see the card.

**S2. Starting mid-song.** *"You were away. The song is already at the third line."*
- Success: suggested within 2 lines, at the right line.

**S3. Chorus repeated.** *"The singer repeats the chorus three times."*
- Success: no wrong line; the bar shows "chorus".

**S4. Wrong guess.** *"The app suggests the wrong song."*
- Success: the operator presses *Not this* and finds the right one within 10 s (H2).

**S5. Song not in the library.** *"A new bhajan nobody uploaded."*
- Success: no card; normal captions throughout.

**S6. Hard to hear.** *"The tabla is loud and the singer is far from the mic."*
- Success: no wrong line. Either it follows or it says *"Can't hear the song"*. The operator can use Next.
- Watch: does the operator understand the amber bar?

**S7. Song ends, talk starts.** *"The song ends and the speaker begins."*
- Success: normal captions are back within 10 s of the last line, and the speech is captioned.

**S8. Punjabi in Roman letters, with 1.7B downloaded.**
- Success: like S1.
- Note: check the log shows the switch to 1.7B, and back after.

**S9. The document.** *"After the satsang, open the Google Doc."*
- Success: the song appears as one block, with its title, lines and translation; only the lines that were shown.

### What I can run now, without a singer

All of these, run by `tests/test_songs.py` and the build's checks:
- the matcher, on text and on audio through the model, for S1, S2, S3, S5;
- splitting files: Word, Excel, CSV, text and PDF;
- the state machine, simulated: S4, S6 and S7 timing.

S0, S4 with a person, S6 with real music, S8 and S9 need you or a real satsang. They're marked **for you** in the results.

## Fix list for the build

H1, H2, H3, H4, H5, H6, H7, H9 (above), plus from the feasibility test: switch to 1.7B while following.
