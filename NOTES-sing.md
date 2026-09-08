# Notes from the singing renderer (`sing/`, `out/sing/`)

## New pip packages (fold into requirements)

    pyworld==0.3.5      # WORLD vocoder: f0 / spectral envelope / aperiodicity
    piper-tts==1.8.0    # local CPU TTS (VITS ONNX); pulls in pathvalidate

Also an apt package: `espeak-ng` (1.51). Piper's phonemiser is bundled in the
wheel, but espeak-ng was installed while testing and is a useful fallback voice.

The voice model is a 63 MB download, kept out of the repo at
`.work/piper/en_US-lessac-medium.onnx` (MIT licence, Blizzard/lessac corpus).
Fetch it with:

    .venv/bin/python -m piper.download_voices en_US-lessac-medium --data-dir .work/piper

The renderer also writes `.work/piper/en_US-lessac-medium.takes.npz` (6.5 MB),
the synthesised syllables it has used. It exists because piper's VITS decoder
samples its own latent and the ONNX graph exposes no seed, so without it every
render is a different take. Both are under `.work/`, which is already ignored.

## Requests for files I do not own

1. **`hollow/format.py` — `Line.ref_hz` is still `null` in every library file.**
   The extractor does not write it yet. `sing/refhz.py` measures it locally from
   `mix.mp3 - instrumental.mp3` and caches it in `out/sing/.cache/`. When the
   extractor starts writing `ref_hz`, `sing.refhz.load_or_measure` prefers the
   value in the file automatically and the sidecar can be deleted.

2. **Slot pitch is an integer semitone.** Rounding is the single biggest source
   of melodic error in the rendered audio (median ~21 cents off the recording,
   which is exactly what rounding to the nearest semitone predicts). A float
   field, or a `pitch_cents`, would remove it at no cost to the writer's view,
   which can keep rounding for display.

3. **Nothing says whether `Slot.t` marks the consonant or the vowel.** Singers
   put the vowel on the beat and the consonant before it. The renderer places
   the consonant on `t` because that is what a word-start timestamp means, and
   it is very slightly late as a result.

4. **`Slot.sustain` is voiced length, not note length.** It is not said whether
   the gap to the next slot is a rest or a legato tail. The renderer treats it
   as a rest and gets a slightly detached delivery on lines that are actually
   slurred.
