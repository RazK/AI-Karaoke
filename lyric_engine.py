#!/usr/bin/env python3
"""Generate lyrics by fitting corpus text to a song's lyric structure.

Usage:
    python lyric_engine.py <title> <corpus_name> [artist]

Results are cached — re-running the same song+corpus skips the API call.
"""
from __future__ import annotations

import hashlib
import json
import os
import pickle
import re
import sys
from pathlib import Path

import pronouncing
import anthropic

_CACHE_DIR     = Path(".lyric_cache")
_CORPUS_PICKLE = Path(".midi_cache/lmd_corpus.pickle")
_COL           = 32
_SEP           = "  │  "


# ── syllable + stress ──────────────────────────────────────────────────────────

def line_stress(text: str) -> list[bool]:
    """Return per-syllable stress booleans derived from CMU pronouncing dict."""
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


# ── song loading ───────────────────────────────────────────────────────────────

def find_artists(title: str) -> list[str]:
    """Return all artists for a title found in the lyrics corpus."""
    if not _CORPUS_PICKLE.exists():
        return []
    corpus = pickle.loads(_CORPUS_PICKLE.read_bytes())
    seen, artists = set(), []
    for key in corpus:
        parts = key.split(" --- ")
        if len(parts) >= 2 and parts[0].lower() == title.lower():
            a = parts[1]
            if a not in seen:
                seen.add(a); artists.append(a)
    return artists


def load_sections(title: str, artist: str) -> list[tuple[str, list[str]]]:
    """Load original lyrics, strip section headers, split into sections."""
    if not _CORPUS_PICKLE.exists():
        return []
    corpus = pickle.loads(_CORPUS_PICKLE.read_bytes())
    raw = ""
    for key, val in corpus.items():
        parts = key.split(" --- ")
        if (len(parts) >= 2
                and parts[0].lower() == title.lower()
                and parts[1].lower() == artist.lower()):
            raw = val.get("lyrics", "")
            break
    if not raw:
        return []
    sections = []
    for i, block in enumerate(re.split(r"\n{2,}", raw.strip()), 1):
        lines = [l.strip() for l in block.splitlines()
                 if l.strip()
                 and not re.match(r"^\[.*\]$", l.strip())
                 and not re.match(r"^[\w\s,&/()\-]+\s:\s", l.strip())
                 and not l.strip().lower().startswith("recorded at")]
        if lines:
            sections.append((f"SECTION {i}", lines))
    return sections


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


# ── prompt + generation ────────────────────────────────────────────────────────

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


def generate(client: anthropic.Anthropic, structure: str, n: int) -> list[str]:
    resp  = client.messages.create(
        model      = "claude-opus-4-6",
        max_tokens = 2500,
        messages   = [{"role": "user", "content": build_prompt(structure, n)}],
    )
    lines = [l.strip() for l in resp.content[0].text.strip().splitlines() if l.strip()]
    return (lines + ["…"] * n)[:n]


# ── cache ──────────────────────────────────────────────────────────────────────

def cache_path(title: str, artist: str, corpus_name: str) -> Path:
    key = f"{title}|{artist}|{corpus_name}".lower()
    return _CACHE_DIR / f"{hashlib.md5(key.encode()).hexdigest()[:8]}.json"


# ── display ────────────────────────────────────────────────────────────────────

def display(
    title: str,
    artist: str,
    corpus_name: str,
    sections: list[tuple[str, list[str]]],
    generated: list[str],
) -> None:
    bar      = "─" * _COL + _SEP + "─" * _COL
    gen_iter = iter(generated)
    width    = _COL * 2 + len(_SEP)

    print()
    print(f"  {'═' * width}")
    print(f"  {artist.upper()} — {title.upper()}")
    print(f"  corpus: {corpus_name}")
    print(f"  {'═' * width}")

    for section_name, sec_lines in sections:
        filler = max(0, width - len(section_name) - 5)
        print(f"\n  ── {section_name} {'─' * filler}")
        print(f"  {'ORIGINAL':<{_COL}}{_SEP}SING THIS")
        print(f"  {bar}")
        for orig in sec_lines:
            gen   = next(gen_iter, "…")
            words = gen.split()
            rows, cur, cur_len = [], [], 0
            for w in words:
                if cur_len + len(w) + 1 > _COL and cur:
                    rows.append(" ".join(cur)); cur, cur_len = [], 0
                cur.append(w); cur_len += len(w) + 1
            if cur:
                rows.append(" ".join(cur))
            for i, row in enumerate(rows or [""]):
                print(f"  {(orig if i == 0 else ''):<{_COL}}{_SEP}{row}")
    print()


# ── artist resolution ──────────────────────────────────────────────────────────

def resolve_artist(title: str, artist: str | None) -> str:
    matches = find_artists(title)
    if not matches:
        raise SystemExit(f"No song titled '{title}' found in lyrics corpus.")
    if artist:
        if artist.lower() not in [m.lower() for m in matches]:
            print(f"Artist '{artist}' not found. Available: {', '.join(matches)}")
            raise SystemExit(1)
        return next(m for m in matches if m.lower() == artist.lower())
    if len(matches) == 1:
        return matches[0]
    print(f"Multiple artists for '{title}':")
    for i, a in enumerate(matches, 1):
        print(f"  {i}. {a}")
    print(f'\nRe-run with: python demo/generate_lyrics.py "{title}" <corpus> "{matches[0]}"')
    raise SystemExit(1)


# ── main ───────────────────────────────────────────────────────────────────────

def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: python demo/generate_lyrics.py <title> <corpus_name> [artist]")
        return 1

    title       = sys.argv[1]
    corpus_name = sys.argv[2].removesuffix(".txt")
    artist      = sys.argv[3] if len(sys.argv) > 3 else None
    corpus_path = Path("data/datasets") / f"{corpus_name}.txt"

    if not corpus_path.exists():
        print(f"Corpus not found: {corpus_path}")
        return 1

    artist = resolve_artist(title, artist)
    cp     = cache_path(title, artist, corpus_name)

    if cp.exists():
        print(f"Loaded from cache ({cp})")
        cached    = json.loads(cp.read_text())
        sections  = [(s[0], s[1]) for s in cached["sections"]]
        generated = cached["generated_lines"]
    else:
        print(f"{artist} — {title}  |  corpus: {corpus_name}")

        # 1. Load sections from original lyrics
        sections = load_sections(title, artist)
        if not sections:
            raise SystemExit(f"No lyrics found for '{title}' by {artist}.")

        # 2. Split corpus into paragraphs, assign one chunk per section proportionally
        all_paragraphs = [
            p.strip() for p in
            corpus_path.read_text(encoding="utf-8").split("\n\n")
            if len(p.strip()) > 60
        ]
        section_sizes = [len(ls) for _, ls in sections]
        total_lines   = sum(section_sizes)
        n_paras       = len(all_paragraphs)

        corpus_chunks: list[str] = []
        para_idx = 0
        for i, size in enumerate(section_sizes):
            if i == len(section_sizes) - 1:
                chunk = "\n\n".join(all_paragraphs[para_idx:]) or all_paragraphs[-1]
            else:
                n_p      = max(1, round(size / total_lines * n_paras))
                chunk    = "\n\n".join(all_paragraphs[para_idx:para_idx + n_p])
                para_idx = min(para_idx + n_p, n_paras - (len(sections) - i - 1))
            corpus_chunks.append(chunk)

        # 3. Build structure from lyrics + CMU stress
        structure, n_lines = build_structure(sections, corpus_chunks)
        print(f"Structure: {n_lines} lines | {len(all_paragraphs)} corpus paragraphs")

        # 4. Generate
        print(f"Generating {n_lines} lines…", end=" ", flush=True)
        client    = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        generated = generate(client, structure, n_lines)
        print("done")

        # 5. Cache
        cp.parent.mkdir(parents=True, exist_ok=True)
        cp.write_text(json.dumps({
            "title": title, "artist": artist, "corpus": corpus_name,
            "sections": [[name, lines] for name, lines in sections],
            "generated_lines": generated,
        }, indent=2))
        print(f"Saved → {cp}")

    display(title, artist, corpus_name, sections, generated)
    return 0


if __name__ == "__main__":
    sys.exit(main())
