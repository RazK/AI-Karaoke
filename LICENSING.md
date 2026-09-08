# Licensing, and what you may do with the output

## The songs this repository uses

They come from [JamendoLyrics](https://github.com/f90/jamendolyrics), which is a
research dataset of freely licensed music with hand-checked word timings. Freely
licensed is not the same as unrestricted, and two of them are stricter than the
rest:

| song | artist | licence | what that allows |
|---|---|---|---|
| Feel (Stripped) | Cortez | **CC BY** | anything, with attribution |
| Embers | Avercage | **CC BY-NC-SA** | derivatives, non-commercially, shared alike, with attribution |
| The statement | Wordsmith | **CC BY-ND** | verbatim redistribution with attribution — **no derivatives** |
| Fire Inside | Ridgway | **CC BY-ND** | verbatim redistribution with attribution — **no derivatives** |

A karaoke rendition is a derivative: it plays a separated instrumental, which is
an edit of the recording. So for the two **BY-ND** tracks, playing them on your
own machine is fine, and **publishing or handing on the separated instrumental,
or a recording of the karaoke, is not.**

`tools/jamendo.py` prints the licence of each song as it seeds it, so this is
visible at the point it matters rather than only here.

## What is in the handover archive

No song audio at all, and no separated stems. `setup.sh` fetches the freely
licensed recordings itself, and anything copyrighted is fetched from the URL it
came from, on the machine that runs it. That is deliberate: the archive can be
passed around, the audio cannot.

Two exceptions, both derivatives of **Embers by Avercage (CC BY-NC-SA 3.0)**:

- `demo/original.mp3` — a synthetic voice singing the song's own words
- `demo/dressed.mp3` — the same voice singing an IKEA assembly manual

Both are over that recording's own separated instrumental. Under BY-NC-SA they
may be shared non-commercially, with attribution to Avercage, under the same
licence. They are marked here so that stays true if they travel.

The demo video uses a commercially released recording fetched from YouTube. It
is a demonstration of a tool, not a release; do not publish it.

## The nine handover texts

`out/nine/` prints each rewritten line beside the original it replaces, because
that is the only way to judge the fit on the page. For the songs above, the
original column is redistribution, which every one of these licences permits
with attribution. For the song fetched from YouTube it is a copyrighted lyric
quoted for review on one person's machine — which is why `out/` is not committed
and not published.

## The rewritten lyrics

Ours, and yours. They are generated from a body of text you supply and a
word-free description of a melody. They contain no words from the original song
— that is the whole point of the HOLLOW format, and `hollow/format.py:leaks()`
checks it rather than assuming it.
