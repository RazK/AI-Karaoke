# AI Karaoke

Take a song everyone knows. Take a body of text that has nothing to do with it —
an IKEA assembly manual, a page of 1-star restaurant reviews, a terms-of-service
agreement. Rewrite every line of the song out of that text so it still fits the
melody. Same tune, same timing, absurd words. Everyone sings along from one
laptop.

## Set it up

```bash
./setup.sh                       # a few minutes; installs a separator and a speech model
.venv/bin/python app/server.py   # then open http://localhost:8000
```

`./setup.sh --full` also seeds the three songs the nine handover examples use.

An Anthropic API key goes in `.env.local` and is only needed for the inventive
end of the licence dial. Nothing else needs one — at licence 0 the system uses
phrases the corpus already contains and never calls a model at all.

## The three parts

### 1. HOLLOW — a song with its words hollowed out

`hollow/format.py`

A HOLLOW file says how a song is sung and nothing about what it says. Per line:
syllable **slots** with an onset and a measured **sustain**, a **stress** demand
per slot, a **hold** flag where the performance sustains an open vowel, the
melody as semitones from the line's first note plus an absolute `ref_hz`, phrase
grouping, rhyme classes, and how confident the aligner was.

It contains no words, letters, phonemes or word boundaries. Title and artist
live in a library sidecar rather than the file, because plenty of songs are
named after one of their own lines. `format.leaks()` checks this rather than
assuming it, and a test asserts no word of the original appears anywhere in the
serialised file.

This is what a writer — or a language model — actually sees:

```
GROUP 1
  L00 [A]  5  ● ● ● ● ○              pitch +0 +12 +10 +9 +8
  L01 [B]  9  ○ ● ○ ○ ●_ ○ ●_ ● ●_   pitch +0 +9 +10 +9 +9 +9 +7 +7 +6
 ?L12 [L]  2  ● ●
```

Extraction happens on this machine — Demucs for the stems, a local Whisper for
the words, CMU for syllables and stress. **Complete lyrics of a copyrighted song
are never sent to a language model.** Only the word-free representation leaves.

`sing/` renders a HOLLOW file back as a sung vocal from the representation
alone, which is the sharpest test of whether it carries enough.

### 2. Dressing a corpus onto it

`hollow/dress.py`

One control: **licence**, 0 to 1.

At 0 the system searches the corpus's own word runs for phrases whose syllable
count and stress pattern already fit a line, trims them lightly, and never calls
a model — recognisably IKEA, stilted, funny because it is real. At 1 it hands
every line to the writer, which may paraphrase, pad, pun and coin words. In
between, the bar a lifted phrase has to clear rises with the dial.

Across the nine handover songs that moves corpus fidelity 98–100% at licence
0.00, 54–79% at 0.60, 31–56% at 1.00.

Fitting the melody is not on the dial. It is a hard constraint with one escape
hatch: a line that cannot be filled falls back to the closest phrase the corpus
has and is **declared as a bend**. At the faithful end that list is the most
interesting output the system produces.

### 3. The stage

`app/server.py`, `app/static/`

Pick a song, pick or paste a text, turn the dial, play it. Words highlight as
they are sung, the original line sits above the rewrite, and a nudge control
pulls the lyrics earlier or later without stopping the music. One HTML file and
one script, no dependencies, so it comes up in a room with bad wifi.

Songs come in two ways and end at the same file: **import a karaoke file** with
the recording it belongs to (`.lrc`, plain or word-level), or **give it a
YouTube URL**. The instrumental is always separated out of the recording
actually loaded.

## The singability exam

`hollow/exam.py`

```
score = 8 × (mean over lines of fit) + 2 × form
fit(line) = e^(−2.5 × |syllables written − slots in the line|)
form = (1.0×stress + 0.5×rhyme + 0.5×vowel) / 2.0
```

Four calibration cases run over every song in the library on every build:

| case | required | actual (5 songs) |
|---|---|---|
| the song's own words back on it | 10 | **10.00** |
| same syllable counts, ignoring all else | ≥ 8 | 8.03 – 8.35 |
| random syllable counts | 0 | 0.10 – 0.91 |
| every other line one syllable too many | 5–6 | 5.15 – 5.76 |

Cases 1 and 2 differ only in stress, rhyme and vowel quality — the timing is
identical. The gap between them is the evidence that the format records those
things at all. `pytest tests/` asserts every band.

## The card

Above a gate of 7/10, four things are reported side by side and none is averaged
into another: how much of the wording is really the corpus's, how far its
register sits from the song's, whether each line parses as English on its own,
and whether the bend list was honest.

When a human rating and the exam disagree by more than two points the song is
flagged. Nothing is refitted automatically — the weights are a starting point.

## Layout

```
hollow/          the core
  format.py      HOLLOW: the representation, its text rendering, and leaks()
  prosody.py     syllables, stress, rhyme, whether a syllable can be held
  audio.py       separation, voicing, pitch
  extract.py     timed words -> HOLLOW, then the words are discarded
  offset.py      where the lyric sits against this recording
  ingest.py      karaoke file or YouTube URL; both end at the same file
  exam.py        the singability exam and its four calibration cases
  dress.py       corpus -> lines, the licence dial, declared bends
  grade.py       the card
  library.py     songs, dressings and ratings on disk
app/             the stage
sing/            renders a HOLLOW file back as a sung vocal
tools/           seeders, the nine, and a checker for whoever writes lines
tests/           49 tests, including the acceptance tests
docs/            prior art, and one page on what this turned out to be
```

## Song in, karaoke file out

The smallest thing this repo does, and the easiest one to check. No player, no
server — a recording and a body of text go in, a word-level `.lrc` of the
rewritten song comes out, and you open it in any karaoke player to see whether
it lands.

```bash
.venv/bin/python tools/lrc.py https://youtu.be/VIDEO ikea.txt --licence 0.6
.venv/bin/python tools/lrc.py song.mp3 reviews.txt -o out.lrc
```

The first argument is either a YouTube URL or a path to an audio file you
already have. Use the file when YouTube refuses — it does that to anything that
looks like a server, and the rest of the pipeline is identical either way.

`--licence 0` (the default) keeps to phrases already in your text and never
calls a model, so it needs no key. Above 0 it needs `ANTHROPIC_API_KEY` in
`.env.local`, and it says so before the slow part rather than after it.

Expect four to six minutes on a first run: separating the recording and
transcribing its vocal both happen on your machine.

## A page you can send someone

The app needs Demucs, a speech model and a few gigabytes of weights. Nobody is
installing that to see whether the joke lands. So one song can be built into a
single self-contained HTML file — every line, every take of it, and the backing
track as a data URI — which opens in any browser with no server behind it.

```bash
.venv/bin/python tools/standalone.py "Feel (Stripped)" -o out/karaoke.html
```

It plays; it does not ingest. Separating a recording and transcribing its vocal
are minutes of local CPU, and neither happens in a browser tab.

It refuses to build a song whose licence forbids derivatives, rather than
leaving that to memory — a karaoke rendition is a derivative, and two of the
seeded songs are CC BY-ND.

## Licensing

The seeded songs are freely licensed but not identically: two are **CC BY-ND**,
so a karaoke rendition of them is fine on your own machine and must not be
published. `LICENSING.md` has the table and what the handover archive does and
does not contain.

## What is not committed

`library/` holds extracted songs — audio, stems and the original lyric. The
original lyric stays on the machine that extracted it. `out/` holds the nine
handover texts, which print the original line beside each rewrite so the fit can
be judged on the page; they are produced locally by `tools/handover.py`.
