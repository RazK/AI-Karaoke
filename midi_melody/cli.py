"""CLI entry point: python -m midi_melody <artist> <title> [--output PATH]."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from midi_melody.pipeline import Pipeline


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m midi_melody",
        description="Extract the melody singability spec from an LMD MIDI file.",
    )
    parser.add_argument("artist", help='Artist name, e.g. "John Lennon"')
    parser.add_argument("title", help='Song title, e.g. "Imagine"')
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help='Output JSON path (default: "<title>.json" in current directory)',
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path(".midi_cache"),
        help="Directory for caching the LMD index and MIDI files (default: .midi_cache)",
    )
    parser.add_argument(
        "--gap",
        type=float,
        default=1.0,
        help="Phrase-break gap threshold in beats (default: 1.0)",
    )
    parser.add_argument(
        "--midi",
        type=Path,
        default=None,
        help="Provide a local .mid file directly (skips LMD download)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable debug logging",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.  Returns an exit code (0 = success)."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )

    output_path: Path = args.output or Path(f"{args.title}.json")

    pipeline = Pipeline(
        cache_dir=args.cache_dir,
        gap_threshold_beats=args.gap,
    )

    try:
        spec = pipeline.run(
            artist=args.artist,
            title=args.title,
            output_path=output_path,
            midi_path=args.midi,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Spec written to: {output_path}")
    print()
    print(spec.to_llm_prompt_block())
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
