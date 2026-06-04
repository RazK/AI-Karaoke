"""Allows running the CLI as: python -m midi_melody <artist> <title>."""
from midi_melody.cli import main
import sys

sys.exit(main())
