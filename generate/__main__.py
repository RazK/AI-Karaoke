import argparse
import json
import sys
from .generator import generate


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate syllable-matched karaoke lyrics")
    parser.add_argument("--song", required=True, help="Song ID (e.g. africa)")
    parser.add_argument("--dataset", required=True, help="Dataset ID (e.g. ikea-manuals)")
    parser.add_argument("--data-dir", default="data", help="Path to data/ directory")
    parser.add_argument("--output", help="Write JSON to this file instead of stdout")
    parser.add_argument("--lines", type=int, help="Limit to first N lines")
    args = parser.parse_args()

    result = generate(args.song, args.dataset, data_dir=args.data_dir, max_lines=args.lines)
    output = json.dumps(result, indent=2, ensure_ascii=False)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Written to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
