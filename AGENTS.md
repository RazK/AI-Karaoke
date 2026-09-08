# AI Karaoke — agent guide

## What this is

A song is stripped to **HOLLOW**, a word-free description of how it is sung. A
body of unrelated text is then dressed onto that, and the result plays back as
karaoke. Read `README.md` first; this file is the working rules.

## The rule that is not negotiable

**Complete lyrics of a copyrighted song are never sent to a language model** —
not to transcribe, not to align, not to check. Extraction runs on the machine:
Demucs for the stems, a local Whisper for the words, CMU for syllables. The only
thing that ever leaves is the word-free HOLLOW rendering plus the corpus the
user supplied.

`hollow/format.py:leaks()` checks the file holds no free text, and
`tests/test_representation.py` asserts no word of the original appears in it. If
you add a field to the format, make sure both still pass.

## Where things live

- `hollow/` is the core and has no web, no CLI and no I/O beyond files.
- `app/` is the stage. `app/static/index.html` and `app.js` are served as-is —
  no build step, no CDN, so the app comes up without a network.
- `tools/` are scripts: seeders, the nine, and `check.py` for whoever is writing
  lines by hand.
- `sing/` renders a HOLLOW file back as a vocal. Optional; nothing depends on it.
- `library/`, `.work/` and `out/` are generated and not committed. `library/`
  holds original lyrics, which stay on the machine that extracted them.

## Working rules

1. **Do not weaken a test to make it pass.** The four calibration cases are an
   acceptance test for the *format*, not for the scorer. When the exam cannot
   separate two cases it should, add what the format is missing rather than
   tuning the weights until the numbers look right. That has already happened
   three times and each was a real hole.
2. **Docs ↔ code.** Update `README.md` when behaviour or layout changes.
3. `pytest tests/ -q` must be green before committing. The first run separates
   audio and takes a few minutes; later runs take seconds.
4. Never commit `.env.local`, `library/`, `.work/`, `out/` or `__pycache__`.

## Things that will surprise you

- `Slot.hold` is not derived from duration. A slot is a held note only if the
  performance actually sustains an open vowel there; a schwa or a stop-closed
  syllable that measures long is the aligner running past the end of the note.
- `prosody.syllables_for` deliberately ignores its `n_slots` argument and reads
  each word one way. Letting a line be re-pronounced until it fitted let random
  text score.
- Rhyme labels run A..Z, AA, AB and never repeat. They used to wrap at Z, which
  told the writer to rhyme lines that had nothing in common.
- A line is capped at 12 syllables on both ingest paths. Some karaoke files
  phrase a whole rapped verse as one thirty-one syllable line.
- The offset estimator has two stages, and its fine stage is worth understanding
  before you touch it: refining against detected note onsets looks right and is
  inert, because there are three onsets per word.
