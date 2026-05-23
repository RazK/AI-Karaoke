from __future__ import annotations
import json
import re
from dataclasses import dataclass
from .syllable import split_syllables


@dataclass
class AnnotatedLine:
    start_ms: int
    text: str
    original: list[list[str]]

    @property
    def syllable_count(self) -> int:
        return sum(len(word) for word in self.original)


def tokenize_line(text: str) -> list[str]:
    tokens = []
    for raw in text.split():
        parts = re.split(r"(?<=[a-zA-Z])-(?=[a-zA-Z])", raw)
        tokens.extend(parts)
    return [t for t in tokens if t.strip()]


def load_lrc(lrc_data: dict) -> list[AnnotatedLine]:
    lines = []
    for line in lrc_data.get("lines", []):
        text = line["text"]
        words = tokenize_line(text)
        original = [split_syllables(w) for w in words if split_syllables(w)]
        lines.append(AnnotatedLine(start_ms=line["startMs"], text=text, original=original))
    return lines


def load_lrc_file(path: str) -> tuple[dict, list[AnnotatedLine]]:
    with open(path) as f:
        data = json.load(f)
    return data, load_lrc(data)
