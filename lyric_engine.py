"""Core lyric engine: syllable analysis, stress patterns, prompt building.

Imported by server.py. Not a CLI — song loading and generation live in the server.
"""
from __future__ import annotations

import re
from pathlib import Path

import pronouncing


# ── syllable + stress ──────────────────────────────────────────────────────────

def line_stress(text: str) -> list[bool]:
    """Return per-syllable stress booleans via CMU pronouncing dict."""
    result = []
    for word in re.findall(r"[a-zA-Z']+", text):
        phones = pronouncing.phones_for_word(word.lower())
        if phones:
            for ph in phones[0].split():
                if ph[-1].isdigit():
                    result.append(ph[-1] in ("1", "2"))
        else:
            syls = max(1, len(re.findall(r"[aeiouy]+", word.lower())))
            result.extend(i % 2 == 0 for i in range(syls))
    return result or [False]


def count_syllables(text: str) -> int:
    return len(line_stress(text))


# ── rhyme detection ────────────────────────────────────────────────────────────

def rhyme_label(lines: list[str]) -> list[str]:
    labels, groups, next_ch = [], {}, ord("A")
    for line in lines:
        words = re.findall(r"[a-zA-Z']+", line)
        last  = words[-1].lower() if words else ""
        phones = pronouncing.phones_for_word(last)
        key   = pronouncing.rhyming_part(phones[0]) if phones else last[-2:]
        if key not in groups:
            groups[key] = chr(next_ch); next_ch += 1
        labels.append(groups[key])
    return labels


# ── structural representation ──────────────────────────────────────────────────

def build_structure(
    sections: list[tuple[str, list[str]]],
    corpus_chunks: list[str],
) -> tuple[str, int]:
    blocks = []
    for (section_name, sec_lines), chunk in zip(sections, corpus_chunks):
        labels = rhyme_label(sec_lines)
        block  = [f"[{section_name}]", f"Source: {chunk.strip()}", ""]
        for orig, label in zip(sec_lines, labels):
            stress  = line_stress(orig)
            sc      = len(stress)
            pattern = " ".join("●" if s else "○" for s in stress)
            end     = "  [close thought]" if orig.rstrip().endswith("...") else ""
            block.append(f"  {sc:2d} syl  {pattern}  ({label}){end}")
        blocks.append("\n".join(block))
    total = sum(len(ls) for _, ls in sections)
    return "\n\n".join(blocks), total


# ── prompt ─────────────────────────────────────────────────────────────────────

def build_prompt(structure: str, n: int) -> str:
    return f"""\
Below is a SONG STRUCTURE. Each section has its own Source text.

Your task: rewrite each section's Source into lyrics that fit that section's structure.
Use ONLY the Source text for that section — do not mix sources across sections.

STRUCTURE LEGEND:
  Each line shows:  <syllable count>  <stress pattern>  (<rhyme label>)
  ● = stressed syllable
  ○ = unstressed syllable
  Lines sharing a rhyme label should rhyme with each other.
  [close thought] = this line must end a complete sentence.

SONG STRUCTURE:
{structure}

OUTPUT RULES:
- Exactly {n} lines total, one per structure line, in order.
- No numbering, no section labels, no blank lines — just the lyrics.
- Match the syllable count of each line as closely as possible.
- Every line must be a grammatically complete phrase or natural fragment.
- Each section's final line must feel like a complete thought.
"""
