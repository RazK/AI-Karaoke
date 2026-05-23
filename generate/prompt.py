from __future__ import annotations
import json
from .lrc import AnnotatedLine

CORPUS_MAX_CHARS = 3000

_TEMPLATE = """\
You are rewriting the lyrics to "{title}" by {artist} using only words and \
phrases from the provided text corpus.

RULES — read all before writing anything:
1. Every generated line MUST have EXACTLY the same syllable count as the original.
   Count syllables as the length of each word's syllable array; line total = sum of those lengths.
2. Write NEW lines from the corpus — do NOT copy the original sentence and swap a word or two.
   BAD (fill-in-the-blank): original "Is this just fantasy?" → "Is this just panel A?"
   GOOD (corpus rewrite): original "Is this just fantasy?" → "Check the diagram now"
   Both match syllables; the good line reads like the dataset, not like edited song lyrics.
3. Words and phrases must come from the corpus below. Light edits OK; unrelated invention is not.
4. Preserve end-rhymes where possible, but NEVER at the cost of rules 1-2.
5. Return ONLY a JSON array. No commentary, no markdown, no code fences.

SYLLABLE VERIFICATION EXAMPLE:
  original: [["No"], ["es", "cape"], ["from"], ["re", "al", "i", "ty"]] → 8 syllables
  generated MUST total 8 — corpus-style rewrite, e.g.:
  [["In", "sert"], ["screw"], ["type"], ["A"], ["care", "ful", "ly"]] → 2+1+1+1+3 = 8 ✓
  BAD: an array that sums to anything other than 8 ✗

Output format (generated only — one object per line in the batch):
[
  {{ "generated": [["Fix"], ["the"], ["shelf"], ["right"], ["now"]] }},
  ...
]

Each word MUST be a JSON array of syllable strings, even single-syllable words: ["Fix"] not "Fix".

--- ORIGINAL LYRICS WITH SYLLABLE COUNTS ---
{annotated_lyrics}

--- CORPUS ---
{corpus}\
"""


def _format_line(i: int, line: AnnotatedLine) -> str:
    return f"Line {i + 1} [{line.syllable_count} syllables]: {json.dumps(line.original)}"


def build_batch_prompt(
    title: str,
    artist: str,
    batch: list[AnnotatedLine],
    corpus: str,
    error_hint: str | None = None,
) -> str:
    annotated = "\n".join(_format_line(i, line) for i, line in enumerate(batch))
    corpus_excerpt = corpus[:CORPUS_MAX_CHARS]
    prompt = _TEMPLATE.format(
        title=title,
        artist=artist,
        annotated_lyrics=annotated,
        corpus=corpus_excerpt,
    )
    if error_hint:
        prompt += f"\n\nPREVIOUS ATTEMPT FAILED: {error_hint}\nFix all syllable counts and return valid JSON."
    return prompt
