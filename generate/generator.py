from __future__ import annotations
import json
import os
from typing import Callable
from .lrc import load_lrc_file
from .prompt import build_batch_prompt
from .validator import validate_batch

BATCH_SIZE = 10
MAX_RETRIES = 3


def generate(
    song_id: str,
    dataset_id: str,
    data_dir: str = "data",
    max_lines: int | None = None,
    _call_fn: Callable[[str], str] | None = None,
) -> dict:
    if _call_fn is None:
        from .client import call_claude
        _call_fn = call_claude

    lrc_path = os.path.join(data_dir, "lrc", f"{song_id}.json")
    lrc_data, lines = load_lrc_file(lrc_path)

    if max_lines is not None:
        lines = lines[:max_lines]

    corpus_path = os.path.join(data_dir, "datasets", f"{dataset_id}.txt")
    with open(corpus_path) as f:
        corpus = f.read()

    title = lrc_data.get("trackName", song_id)
    artist = lrc_data.get("artistName", "")

    result_lines: list[dict] = []
    for start in range(0, len(lines), BATCH_SIZE):
        batch = lines[start : start + BATCH_SIZE]
        result_lines.extend(_process_batch(title, artist, batch, corpus, _call_fn))

    return {"songId": song_id, "datasetId": dataset_id, "lines": result_lines}


def _process_batch(
    title: str,
    artist: str,
    batch: list,
    corpus: str,
    call_fn: Callable[[str], str],
) -> list[dict]:
    error_hint: str | None = None
    for _ in range(MAX_RETRIES):
        prompt = build_batch_prompt(title, artist, batch, corpus, error_hint=error_hint)
        raw = call_fn(prompt)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            error_hint = f"response was not valid JSON: {exc}"
            continue
        validated, err = validate_batch(batch, data)
        if validated is not None:
            return validated
        error_hint = err
    raise RuntimeError(
        f"Generation failed after {MAX_RETRIES} attempts — syllable counts could not be matched."
    )
