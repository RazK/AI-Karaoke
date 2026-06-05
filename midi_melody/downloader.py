"""MidiDownloader — fetches MIDI files from the Hugging Face Lyrics-MIDI-Dataset.

Uses the corpus index pickle (70 MB, downloaded once) for title/artist search, then
extracts individual MIDI files from the dataset ZIP via HTTP range requests — no
full-archive download required.
"""

from __future__ import annotations

import logging
import pickle
import struct
import zlib
from pathlib import Path

import requests
from tqdm import tqdm

from midi_melody import DownloadError

logger = logging.getLogger(__name__)

_CORPUS_URL = (
    "https://huggingface.co/datasets/asigalov61/Lyrics-MIDI-Dataset"
    "/resolve/main/Lyrics_MIDI_Dataset_Processed_Corpus_CC_BY_NC_SA.pickle"
)
_GENIUS_ZIP_URL = (
    "https://huggingface.co/datasets/asigalov61/Lyrics-MIDI-Dataset"
    "/resolve/main/Lyrics-MIDI-Genius-Cleaned-Subset-CC-BY-NC-SA.zip"
)
_FULL_ZIP_URL = (
    "https://huggingface.co/datasets/asigalov61/Lyrics-MIDI-Dataset"
    "/resolve/main/Lyrics-MIDI-Dataset-CC-BY-NC-SA.zip"
)


class MidiDownloader:
    """Search by title/artist and download individual MIDI files on demand.

    The corpus index is downloaded once (~70 MB) and cached locally.  Each
    MIDI is then fetched with a targeted HTTP range request into the ZIP —
    no full-archive download required.

    Parameters
    ----------
    cache_dir:
        Directory for caching the index and MIDI files.
    """

    def __init__(self, cache_dir: Path = Path(".midi_cache")) -> None:
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._title_index: dict[str, list[tuple[str, str, str]]] | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search_by_title(self, title: str) -> list[str]:
        """Return artist names that have a song matching *title* (case-insensitive)."""
        index = self._load_index()
        return [artist for _, artist, _ in index.get(title.lower().strip(), [])]

    def download(self, artist: str, title: str) -> Path:
        """Download the MIDI for *artist* / *title* and return the local path.

        The file is cached by md5; subsequent calls return immediately.
        """
        index = self._load_index()
        matches = index.get(title.lower().strip(), [])

        match = next((m for m in matches if m[1].lower() == artist.lower()), None)
        if match is None:
            raise DownloadError(f"'{title}' by '{artist}' not found in index.")

        title_orig, artist_orig, md5 = match
        cached = self._cache_dir / f"{md5}.mid"
        if cached.exists():
            logger.info("MIDI already cached: %s", cached)
            return cached

        genius_entry = f"MIDIs/{title_orig} --- {artist_orig}.mid"
        full_entry = f"MIDIs and Lyrics/Normalized/{title_orig} --- {artist_orig} --- {md5}.mid"

        for zip_url, zip_entry in [
            (_GENIUS_ZIP_URL, genius_entry),
            (_FULL_ZIP_URL, full_entry),
        ]:
            try:
                midi_bytes = self._extract_from_zip(zip_url, zip_entry)
                cached.write_bytes(midi_bytes)
                logger.info("MIDI saved to %s", cached)
                return cached
            except DownloadError as exc:
                logger.debug("Not in %s: %s", zip_url.split("/")[-1], exc)

        raise DownloadError(f"MIDI not found for '{title}' by '{artist}'.")

    # ------------------------------------------------------------------
    # Index
    # ------------------------------------------------------------------

    def _load_index(self) -> dict[str, list[tuple[str, str, str]]]:
        if self._title_index is not None:
            return self._title_index

        corpus_path = self._cache_dir / "lmd_corpus.pickle"
        if not corpus_path.exists():
            logger.info("Downloading corpus index (~70 MB) — one-time setup …")
            r = requests.get(_CORPUS_URL, stream=True, timeout=300)
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            buf = bytearray()
            with tqdm(total=total or None, unit="B", unit_scale=True, desc="corpus index") as pbar:
                for chunk in r.iter_content(65536):
                    buf.extend(chunk)
                    pbar.update(len(chunk))
            corpus_path.write_bytes(bytes(buf))

        corpus: dict = pickle.loads(corpus_path.read_bytes())
        index: dict[str, list[tuple[str, str, str]]] = {}
        for key in corpus:
            parts = key.split(" --- ")
            if len(parts) < 3:
                continue
            title, artist, md5 = parts[0], parts[1], parts[2]
            index.setdefault(title.lower().strip(), []).append((title, artist, md5))
        self._title_index = index
        logger.debug("Index loaded: %d titles", len(index))
        return index

    # ------------------------------------------------------------------
    # ZIP extraction via HTTP range requests
    # ------------------------------------------------------------------

    def _get_zip_cd(self, zip_url: str) -> dict[str, tuple[int, int, int, int]]:
        """Fetch and cache the central directory of a remote ZIP.

        Returns a mapping of filename → (local_offset, comp_size, uncomp_size, compress).
        """
        url_hash = abs(hash(zip_url)) & 0xFFFFFF
        cd_cache = self._cache_dir / f"zipcd_{url_hash}.pickle"
        if cd_cache.exists():
            return pickle.loads(cd_cache.read_bytes())

        logger.info("Fetching ZIP central directory from %s …", zip_url.split("/")[-1])

        r = requests.head(zip_url, allow_redirects=True, timeout=30)
        r.raise_for_status()
        total = int(r.headers["content-length"])

        tail_size = min(65536, total)
        r = requests.get(
            zip_url,
            headers={"Range": f"bytes={total - tail_size}-{total - 1}"},
            allow_redirects=True,
            timeout=60,
        )
        r.raise_for_status()
        tail = r.content

        pos = tail.rfind(b"PK\x05\x06")
        if pos < 0:
            raise DownloadError("EOCD not found in ZIP")
        eocd = tail[pos:]
        cd_size = struct.unpack_from("<I", eocd, 12)[0]
        cd_offset = struct.unpack_from("<I", eocd, 16)[0]

        # ZIP64 support
        if cd_offset == 0xFFFFFFFF:
            loc_pos = tail.rfind(b"PK\x06\x07")
            if loc_pos < 0:
                raise DownloadError("ZIP64 locator not found")
            z64_offset = struct.unpack_from("<Q", tail, loc_pos + 8)[0]
            r = requests.get(
                zip_url,
                headers={"Range": f"bytes={z64_offset}-{z64_offset + 55}"},
                allow_redirects=True,
                timeout=60,
            )
            z64 = r.content
            cd_size = struct.unpack_from("<Q", z64, 40)[0]
            cd_offset = struct.unpack_from("<Q", z64, 48)[0]

        r = requests.get(
            zip_url,
            headers={"Range": f"bytes={cd_offset}-{cd_offset + cd_size - 1}"},
            allow_redirects=True,
            timeout=120,
        )
        r.raise_for_status()
        cd = r.content

        entries: dict[str, tuple[int, int, int, int]] = {}
        i = 0
        while i < len(cd):
            if cd[i : i + 4] != b"PK\x01\x02":
                break
            compress = struct.unpack_from("<H", cd, i + 10)[0]
            comp_size = struct.unpack_from("<I", cd, i + 20)[0]
            uncomp_size = struct.unpack_from("<I", cd, i + 24)[0]
            fname_len, extra_len, comment_len = struct.unpack_from("<HHH", cd, i + 28)
            local_offset = struct.unpack_from("<I", cd, i + 42)[0]
            fname = cd[i + 46 : i + 46 + fname_len].decode("utf-8", errors="replace")

            # Resolve ZIP64 extended info
            if local_offset == 0xFFFFFFFF or comp_size == 0xFFFFFFFF:
                extra = cd[i + 46 + fname_len : i + 46 + fname_len + extra_len]
                ei = 0
                while ei + 4 <= len(extra):
                    tag, sz = struct.unpack_from("<HH", extra, ei)
                    if tag == 0x0001:
                        vi, vals = 0, []
                        for off in range(0, sz, 8):
                            if ei + 4 + off + 8 <= len(extra):
                                vals.append(struct.unpack_from("<Q", extra, ei + 4 + off)[0])
                        if uncomp_size == 0xFFFFFFFF and vi < len(vals):
                            uncomp_size = vals[vi]; vi += 1
                        if comp_size == 0xFFFFFFFF and vi < len(vals):
                            comp_size = vals[vi]; vi += 1
                        if local_offset == 0xFFFFFFFF and vi < len(vals):
                            local_offset = vals[vi]
                        break
                    ei += 4 + sz

            entries[fname] = (local_offset, comp_size, uncomp_size, compress)
            i += 46 + fname_len + extra_len + comment_len

        cd_cache.write_bytes(pickle.dumps(entries))
        logger.info("Cached ZIP directory: %d entries", len(entries))
        return entries

    def _extract_from_zip(self, zip_url: str, zip_path: str) -> bytes:
        """Range-request and decompress a single file from a remote ZIP."""
        entries = self._get_zip_cd(zip_url)
        if zip_path not in entries:
            raise DownloadError(f"'{zip_path}' not found in {zip_url.split('/')[-1]}")

        local_offset, comp_size, uncomp_size, compress = entries[zip_path]

        # Read local file header to find exact data start
        r = requests.get(
            zip_url,
            headers={"Range": f"bytes={local_offset}-{local_offset + 29}"},
            allow_redirects=True,
            timeout=30,
        )
        r.raise_for_status()
        lh = r.content
        if len(lh) < 30 or lh[:4] != b"PK\x03\x04":
            raise DownloadError("Invalid local file header")
        fname_len, extra_len = struct.unpack_from("<HH", lh, 26)
        data_start = local_offset + 30 + fname_len + extra_len

        logger.info("Downloading MIDI (%d KB) …", comp_size // 1024)
        r = requests.get(
            zip_url,
            headers={"Range": f"bytes={data_start}-{data_start + comp_size - 1}"},
            allow_redirects=True,
            timeout=120,
        )
        r.raise_for_status()
        compressed = r.content

        if compress == 0:
            return compressed
        if compress == 8:
            return zlib.decompress(compressed, -15)
        raise DownloadError(f"Unsupported ZIP compression method: {compress}")


# Backward-compat alias
LakhDownloader = MidiDownloader
