#!/usr/bin/env python3
"""Generate a new corpus file for lyric generation.

Usage:
    python demo/generate_corpus.py <id> "<label>" "<description>" "<style>"

Example:
    python demo/generate_corpus.py wine-reviews "Wine Reviews" \
        "Pretentious wine tasting notes" \
        "pretentious sommelier tasting notes for obscure wines"
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import anthropic

_DATASETS_DIR  = Path("data/datasets")
_DATASETS_JSON = Path("data/datasets.json")

_PROMPT = """\
Write a corpus of text in the style of: {style}

Requirements:
- Write 10 separate entries, each 3-5 sentences long
- Separate entries with a blank line
- Each entry should be self-contained and vivid
- Vary the content across entries — no repetition of the same scenario
- Write in plain mixed case — no ALL CAPS emphasis
- No headers, no numbering, no labels — just the entries separated by blank lines

Write all 10 entries now.
"""


def main() -> int:
    if len(sys.argv) < 5:
        print("Usage: python demo/generate_corpus.py <id> <label> <description> <style>")
        print('Example: python demo/generate_corpus.py wine-reviews "Wine Reviews" '
              '"Pretentious tasting notes" "pretentious sommelier reviewing obscure wines"')
        return 1

    corpus_id   = sys.argv[1]
    label       = sys.argv[2]
    description = sys.argv[3]
    style       = sys.argv[4]

    out_path = _DATASETS_DIR / f"{corpus_id}.txt"
    if out_path.exists():
        print(f"Already exists: {out_path}. Delete it first to regenerate.")
        return 1

    print(f"Generating corpus: {label}")
    print(f"Style: {style}")
    print("Calling Claude...", end=" ", flush=True)

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    resp   = client.messages.create(
        model      = "claude-opus-4-6",
        max_tokens = 2000,
        messages   = [{"role": "user", "content": _PROMPT.format(style=style)}],
    )
    text = resp.content[0].text.strip()
    print("done")

    _DATASETS_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    print(f"Saved → {out_path} ({len(text)} chars)")

    # Update datasets.json
    datasets = json.loads(_DATASETS_JSON.read_text()) if _DATASETS_JSON.exists() else []
    if not any(d["id"] == corpus_id for d in datasets):
        datasets.append({"id": corpus_id, "label": label, "description": description, "free": True})
        _DATASETS_JSON.write_text(json.dumps(datasets, indent=2))
        print(f"Added to datasets.json")

    # Preview
    lines = text.splitlines()
    print("\nPreview (first 10 lines):")
    for line in lines[:10]:
        print(f"  {line}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
