#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

CMD="${1:-help}"
shift || true

case "$CMD" in
  install)
    pip install -r requirements.txt
    ;;
  generate)
    SONG="${1:?Usage: ./run.sh generate <song-id> <dataset-id> [--lines N] [--output file.json]}"
    DATASET="${2:?Usage: ./run.sh generate <song-id> <dataset-id>}"
    shift 2
    python3 -m generate --song "$SONG" --dataset "$DATASET" "$@"
    ;;
  test)
    pytest tests/ "$@"
    ;;
  help|*)
    cat <<'EOF'
AI Karaoke — lyric generator

USAGE
  ./run.sh install                              install Python dependencies
  ./run.sh generate <song-id> <dataset-id>     generate lyrics (stdout JSON)
  ./run.sh generate <song-id> <dataset-id> --lines 3          first 3 lines only
  ./run.sh generate <song-id> <dataset-id> --output out.json  write to file
  ./run.sh test                                run unit tests  (no API calls)
  ./run.sh test --smoke                        smoke test: 1 combo, 3 lines (uses API)
  ./run.sh test --full --yes                   full acceptance matrix (uses API, ~$)

SONG IDs
  bohemian-rhapsody   never-gonna-give-you-up   africa
  someone-like-you    dont-stop-believin

DATASET IDs
  ikea-manuals   yelp-reviews-1star   craigslist-ads
  horoscopes     legal-disclaimers

ENVIRONMENT
  export ANTHROPIC_API_KEY=sk-...    required for generate and smoke/full tests

EXAMPLES
  ./run.sh install
  export ANTHROPIC_API_KEY=sk-...
  ./run.sh generate africa ikea-manuals
  ./run.sh generate bohemian-rhapsody yelp-reviews-1star --lines 5
  ./run.sh test
  ./run.sh test --smoke
EOF
    ;;
esac
