"""Shared fixtures.

The acceptance tests run over the library as it stands — every song in it, on
every build — rather than over a fixture song, because the thing being tested
is whether the extractor coped with real recordings.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from hollow.library import Library  # noqa: E402

LIBRARY = Library(ROOT / "library")


def pytest_generate_tests(metafunc):
    """Run any test that asks for `song` once per song in the library."""
    if "song" not in metafunc.fixturenames:
        return
    songs = LIBRARY.songs()
    metafunc.parametrize("song", songs, ids=[s.ref for s in songs])


@pytest.fixture(scope="session")
def library() -> Library:
    return LIBRARY
