# One page, in my own words

## What I changed my mind about

**I thought the interesting problem was fitting syllables. It is stress.**
Getting the right number of syllables is a search problem and the corpus usually
has an answer. Getting them to land where the melody puts its weight is where
the corpus and the song actually meet or fail to. A nine-word corpus filled a
forty-five line song with the right syllable count on every line and declared no
bends at all, and the result was unsingable. That is what made me redefine a
bend: not "wrong length" but "we took the nearest phrase rather than one that
fits", which includes stress. The most honest output the system produces is that
list, and it was empty for the wrong reason for most of a day.

**I thought the format was the novel part. It mostly is not.** A research
representation called REFFLY had already published almost exactly this design —
syllable counts, binary prominence markers, melisma positions, independent of
the original lyric — and UltraStar's `.txt` karaoke format is HOLLOW's data
model with the text column still attached. What survived the survey as genuinely
ours is narrower: sustain measured as *voiced duration* rather than notated
length, per-line alignment confidence (which not one of about twenty surveyed
formats carries), and `leaks()` — word-freeness as a machine-checked invariant
rather than an assumption. That last one is what makes the copyright position
defensible. The schema is not.

**I did not expect making it sing to be the best critique of the format.**
Rendering a HOLLOW file back as a vocal produced thirteen things it had to
guess. Two of them matter: pitch is rounded to a whole semitone, which alone
accounts for 25 of the 29 cents of measured melodic error, and nothing records
whether a twelve-semitone jump is a real octave or the pitch tracker doubling.
Neither was visible from reading the spec. Both are cheap to fix and are the
first things I would add.

## Which of the nine I would show, and which I would not

**Show: The statement × IKEA manuals, licence 0.60.** Ninety per cent of lines
parse as English, three quarters of the wording is traceable to the manual, and
a fast rap meter forces the manual into short declarative bursts that sound like
someone furious about a bookshelf. "Lay out all the parts and check the parts
list twice" over that beat is the joke working exactly as intended.

**Show: Feel (Stripped) × 1-star reviews, licence 0.00.** A ballad carrying "Our
server rolled his eyes" and "Had so much grease it soaked through the bun" in
the corpus's own words, untouched. This is the recognisably-real end of the dial
and it is the funniest of the nine.

**Do not show: Feel (Stripped) × 1-star reviews to a stranger without warning.**
The same song scores 47% on lines-that-parse, the worst of the nine, because the
review corpus is full of usernames and the matcher will happily sing
"NeverComingBack Mark Let me set the scene". The melody is fine. The English is
not, and it is a corpus hygiene problem I did not solve.

**Do not show: anything at licence 1.00 as evidence of the pipeline.** Those
lines were written by me answering the word-free prompts by hand, because there
was no API key in the build environment. That is a genuine test of the format —
I had never heard these songs and 187 of 189 lines landed on the exact syllable
count — but it is not a demonstration that the automated inventive end works.

## Where it breaks next

**The register-gap number is measuring punctuation.** The rap scores 9.6–9.95
against 5.1–5.4 for the pop song, and most of that is the sentence-length
feature: rap lyrics are transcribed without full stops, so the whole song reads
as one sentence. The proxy is defensible for prose against prose and misleading
across transcription styles. It is the weakest number on the card and I would
replace it before trusting it.

**Line confidence is a single number doing two jobs.** It mixes "the aligner was
unsure of these words" with "this line sits over silence". They fail differently
and a song with lots of backing vocals trips the first constantly.

**A held note is capped at 2.5 seconds by fiat.** Demucs' vocal stem never drops
below the silence floor through a long non-lexical passage, so the extractor
cannot find the end of the note and the cap truncates rather than measures.

**The YouTube path is proved on one recording.** Not a limitation of the code —
this build environment's IP is bot-flagged by YouTube and 50-odd modern tracks
were refused. The one that worked is dense and heavily layered, which is the
property that matters, but "works on modern pop" rests on a sample of one.

**Whisper's line boundaries are not the song's.** On the YouTube path the lines
come from where the transcriber breathed, not from where the song does, so a
row can start mid-phrase: "We're no strangers to love You" and then "know the
rules and so you have". The rewrite maps onto whatever the timings use, which is
the correct behaviour and does not hurt the new words — each rewritten line is
self-contained — but it means the original column of the handover reads
strangely, and on a dense mix with no pauses to split at, the split lands
wherever. A musical phrase detector, or beat tracking, would fix it. Syllable
counts and stress would not change.

**Nothing has been in a room with ten people in it.** Everything above is
measured. The thing the brief actually asks for is not.
