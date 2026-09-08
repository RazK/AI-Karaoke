# Prior art for HOLLOW

*Survey date: September 2026. Grounded in `hollow/format.py` and `hollow/prosody.py`.*

## Verdict

**HOLLOW is about 70% a re-derivation, but there was nothing you could have adopted whole.**

Two things already exist that you rebuilt:

1. **UltraStar `.txt`** is HOLLOW's data model with the text column still attached. A note line is `note-type start-beat duration pitch text`, one syllable per note, plus explicit `-` line-break markers for phrase grouping ([spec v2](https://github.com/UltraStar-Deluxe/format/blob/main/The%20UltraStar%20File%20Format%20(v2).md)). That is `Slot.t`, `Slot.sustain`, `Slot.pitch`, and `Hollow.groups`. You should have *serialised* to it — see the recommendation below.
2. **REFFLY's "pseudo music constraint"** ([arXiv:2409.00292](https://arxiv.org/html/2409.00292), NAACL 2025) is HOLLOW's semantic content, built for exactly your task: revising arbitrary draft text into singable lyrics. It gives the model syllable count per phrase, **binary prominent-note markers** (derived from downbeats, syncopation and pitch leaps), tie/melisma positions, and per-note pitch/duration/offset — **explicitly independent of the original lyrics**. That is `Slot.stress`, `Slot.hold`, `Slot.pitch` and the group structure, with the same word-free justification.

So the claim that "a deliberately word-free shape-of-the-song format is the unusual part" is **half wrong**. Word-free melodic constraint representations exist in the melody-to-lyrics literature (REFFLY; [Joint Learning of Wording and Formatting, arXiv:2307.02146](https://arxiv.org/abs/2307.02146); [Songs Across Borders, ACL 2023](https://aclanthology.org/2023.acl-long.27/), which controls syllable count, end-rhyme and word-boundary position by prompt). Hymn **metrical indexes** are the same idea in its crudest form — `8.7.8.7` plus "trochaic" is a word-free singable template, and hymnals have shipped them for centuries ([Metre (hymn)](https://en.wikipedia.org/wiki/Metre_(hymn))).

What is genuinely yours, and worth keeping:

- **`sustain` as measured voiced duration, not gap-to-next-note.** Every score format encodes notated duration; every subtitle format encodes display windows. Neither tells a writer whether a syllable is actually *held*.
- **`hold` as a phonotactic demand on the writer** ("this slot needs an open vowel"). No surveyed format carries a constraint aimed at the person supplying words. `prosody.Syl.can_hold` (no schwa, no stop coda) is the matching test and I found no equivalent in tooling.
- **Per-line `confidence`.** Not one of the twenty-odd formats below carries alignment uncertainty. This is a real gap in the ecosystem.
- **`format.leaks()`** — word-freeness as a *machine-checked invariant* rather than a convention. That is the actual novel artefact, and it is what makes the copyright position defensible. REFFLY's representation is word-free by construction but nobody audits it.

**What you should do:** keep HOLLOW as the internal/LLM-facing artefact, and add an UltraStar `.txt` export (sentinel text per note, `-` for group boundaries) as a lossy interchange path. That buys you every existing karaoke editor and Ultrastar-based aligner for ~50 lines, without weakening the no-words rule for the LLM path.

## Comparison

✓ carried · ~ partial/by convention · ✗ absent

| Format | Syllable slots (onset+dur) | Stress | Pitch | Phrase grouping | Rhyme | Confidence | Word-free |
|---|---|---|---|---|---|---|---|
| [MusicXML](https://usermanuals.musicxml.com/MusicXML/Content/EL-MusicXML-lyric.htm) `<lyric>`/`<syllabic>`/`<extend>` | ~ (notated, not measured) | ✗ (`<syllabic>` is word position, not stress) | ✓ | ~ (slurs/measures) | ✗ | ✗ | ✗ |
| MEI `<verse>/<syl>` | ~ | ✗ | ✓ | ~ | ✗ | ✗ | ✗ |
| Humdrum `**kern` + `**text` | ~ | ✗ | ✓ | ~ | ✗ | ✗ | ✗ |
| ABC `w:` | ~ | ✗ | ✓ | ~ | ✗ | ✗ | ✗ |
| [LilyPond `\lyricmode`](https://lilypond.org/doc/v2.25/Documentation/notation/common-notation-for-vocal-music) | ~ | ✗ | ✓ | ~ | ✗ | ✗ | ✗ |
| LRC (line) | ✗ | ✗ | ✗ | ~ | ✗ | ✗ | ✗ |
| Enhanced LRC (`<mm:ss.xx>` per word) | ~ (onset only) | ✗ | ✗ | ~ | ✗ | ✗ | ✗ |
| [`.kar` / MIDI lyric meta](https://www.mixagesoftware.com/en/midikit/help/HTML/karaoke_formats.html) (0x05 lyric, 0x01 text; `\`=clear, `/`=newline) | ✓ (note on/off) | ✗ | ✓ | ~ (`/`,`\`) | ✗ | ✗ | ✗ |
| [Apple Music TTML](https://github.com/amll-dev/amll-ttml-db/blob/main/instructions/ttml-specification-en.md) (`itunes:timing="Word"`) | ✓ (syllable spans) | ✗ | ✗ | ✓ (div/p) | ✗ | ✗ | ✗ |
| SRT / WebVTT | ✗ | ✗ | ✗ | ~ | ✗ | ✗ | ✗ |
| **[UltraStar `.txt`](https://github.com/UltraStar-Deluxe/format/blob/main/The%20UltraStar%20File%20Format%20(v2).md)** | ✓ | ✗ | ✓ | ✓ (`-`) | ✗ | ✗ | ✗ (text ≥1 char, required) |
| CD+G / KaraFun | ✗ (bitmap/paint timing) | ✗ | ✗ | ~ | ✗ | ✗ | ✗ |
| UTAU `.ust` / OpenUtau `.ustx` | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ (lyric per note) |
| VOCALOID `.vsqx`/`.vpr`, Synth V `.svp`, ACE Studio | ✓ | ✗ | ✓ | ~ | ✗ | ✗ | ✗ |
| [HTS full-context labels](https://www.isca-archive.org/ssw_2010/oura10_ssw.pdf) (Sinsy/NNSVS) | ✓ (phone-level) | ~ (lexical stress as a context feature) | ✓ | ✓ (note/phrase contexts) | ✗ | ✗ | ✗ (phone identity is the first field) |
| [DiffSinger / OpenCPOP](https://github.com/MoonInTheRiver/DiffSinger/blob/master/docs/README-SVS-opencpop-e2e.md) (`ph_seq`, `ph_dur`, f0) | ✓ | ✗ | ✓ (f0) | ✗ | ✗ | ✗ |
| Praat [TextGrid](https://www.fon.hum.uva.nl/praat/manual/TextGrid_file_formats.html) | ✓ (interval tier) | ~ (if you add a tier) | ~ (point tier) | ~ | ✗ | ✗ | ✗ in practice (labels are text) |
| MFA / HTK label files | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| ToBI | ✗ | ✓ (pitch accents) | ~ (tones) | ✓ (break indices) | ✗ | ✗ | ✓ (it *is* an abstract prosodic tier) |
| Hymn metrical index (`8.7.8.7`) | ~ (counts only) | ~ (trochaic/iambic) | ✗ | ✓ | ~ | ✗ | ✓ |
| **REFFLY pseudo-constraint** | ✓ | ✓ (binary prominence) | ✓ | ✓ | ✗ | ✗ | ✓ |
| **HOLLOW** | ✓ (measured sustain) | ✓ | ✓ (rel. + `ref_hz`) | ✓ | ✓ | ✓ | ✓ (enforced) |

Two honest reads of that table: **rhyme classes and alignment confidence are unique to HOLLOW**, and **ToBI + a metrical index is the closest thing to a *standard* that is word-free** — but ToBI has no timeline of singable slots and no melody, so it could not have replaced HOLLOW.

## Generative singing systems (as of 2026)

The input interface is the whole story: **none of the full-song systems exposes note-level control.** All of them take *prompt + free lyrics text*.

| System | Input interface | Melody-to-sing-to? | Weights | CPU-viable |
|---|---|---|---|---|
| Suno v5.5 | prompt + lyrics; audio upload for [Covers](https://suno.com/blog/covers) with a source-audio weight | Cover preserves the *source's own* melody; there is no "sing my words to this melody" mode | closed | n/a |
| Udio | prompt + lyrics, audio inpaint/extend | no | closed | n/a |
| Stable Audio Open | text prompt, no lyric conditioning | no | open (non-commercial community licence) | no |
| [YuE](https://github.com/multimodal-art-projection/YuE) | lyrics2song, `[verse]/[chorus]` sections + genre tags; optional audio prompt | no | Apache-2.0, 7B | **no** — ≥16 GB VRAM; ~360 s per 30 s audio on a 4090 |
| [ACE-Step](https://github.com/ace-step/ACE-Step) 1.0/[1.5](https://arxiv.org/abs/2602.00744) | prompt tags + structured lyrics + audio repaint/edit/extend; ControlNet "coming soon" | no (no MIDI/note input documented) | Apache-2.0, 3.5B | no — ~26 s/min on M2 Max, GPU assumed |
| DiffRhythm | lyrics + style, diffusion; good lyric alignment, weaker long-range structure ([ACE-Step paper](https://arxiv.org/abs/2506.00045)) | no | open | no |
| [SegTune](https://arxiv.org/html/2510.18416) | segment prompts + LLM-predicted **sentence-level LRC** timestamps | sentence-level only | open code | no |
| **[SoulX-Singer](https://arxiv.org/html/2602.07803)** (2026) | **phonemes (English) + discrete MIDI note sequence, or continuous F0 from reference audio**; note embeddings expanded by note duration | **yes** | code at [Soul-AILab/SoulX-Singer](https://github.com/Soul-AILab/SoulX-Singer); licence/weights not stated in the paper | unlikely (DiT) |
| [YingMusic-Singer](https://arxiv.org/html/2603.24589) (2026) | timbre ref + melody-providing clip + **modified lyrics** | **yes** — annotation-free melody guidance | research | unlikely |

The last two are your actual target interface: HOLLOW plus dressed lyrics is close to a valid SoulX-Singer input (note pitch, note duration, English phonemes). If you ever get a GPU, that's the adapter to write. On the full-song systems there is nothing to hook into — you'd be back to feeding them plain text and losing the melody entirely.

## Local synthesis on 4 cores / 15 GB / no GPU

Ranked by "will actually produce a vocal this week".

1. **piper-tts + pyworld or PSOLA re-shaping — do this.** `pip install piper-tts pyworld psola`. Piper is VITS exported to ONNX, runs on CPU with no GPU; voices are 21–28 MB (x_low), ~63 MB (low/medium), 63–137 MB (high) and comfortably sub-realtime on a Pi 4, so 4 cores is plenty ([piper](https://github.com/OHF-Voice/piper1-gpl), [notes](https://www.cekura.ai/discover/piper-tts)). Synthesise per syllable or per line, then force onset/`sustain`/`ref_hz`+`pitch` with [pyworld](https://github.com/JeremyCCHsu/Python-Wrapper-for-World-Vocoder) (DIO → StoneMask → CheapTrick → D4C → synthesize with a replaced f0 contour) or [maxrmorrison/psola](https://github.com/maxrmorrison/psola) (TD-PSOLA via Parselmouth, takes a target-pitch array directly). **Licence trap:** the maintained `OHF-Voice/piper1-gpl` is **GPL-3.0**; the archived `rhasspy/piper` (MIT, frozen Oct 2025) is the permissive fallback if you ever ship this.
2. **espeak-ng + PSOLA.** Uglier, ~a few MB, GPL-3.0, already a piper dependency. Perfect deterministic guide-vocal / CI fixture: it will never fail to produce audio on time.
3. **OpenUtau + a DiffSinger ONNX voicebank.** Best quality that is plausible on CPU, but three blockers: no supported headless render (still an [open request](https://github.com/openutau/OpenUtau/issues/1615) — you'd drive `Ustx.Load()` + `RenderToFiles()` from .NET yourself); diffusion acoustic + vocoder on 4 cores is minutes per line, not seconds; and **voicebank licensing is a minefield** — terms are per-bank with no standard, many English DiffSinger banks are CC BY-NC-ND + Commons Clause or require a **paid commercial licence** (e.g. TIGER, DANROU), redistribution is usually forbidden, and editing rendered audio into another voicebank is near-universally forbidden ([DiffSinger banks](https://diffsinger.miraheze.org/wiki/Category:DiffSinger_voicebanks), [UTAU ToU norms](https://utaforum.net/threads/voicebank-usage-terms.17864/)).
4. **NNSVS / Sinsy — dead end.** "Due to license issues, pre-trained models are not provided except the ones trained on NIT-song070 database. The use of pre-trained models are only permitted for research purpose" ([NNSVS](https://r9y9.github.io/projects/nnsvs/)), and that model is Japanese. You'd have to train, which needs a GPU and a licensed singing corpus.
5. **DiffSinger from source / YuE / ACE-Step on CPU — not viable** at 4 cores.

Route 1 is the only one that is pip-installable, licence-clean, and fast enough to iterate on. Build the HOLLOW → (syllable, onset, sustain, f0) → WORLD adapter once; it is also the exact tuple SoulX-Singer wants later.
