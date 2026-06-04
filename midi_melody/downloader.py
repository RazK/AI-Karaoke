"""LakhDownloader — downloads MIDI files from the Lakh MIDI Dataset (LMD)."""

from __future__ import annotations

import csv
import io
import logging
import tarfile
from pathlib import Path
from typing import Iterator
from urllib.parse import urljoin

import requests
from tqdm import tqdm

from midi_melody import DownloadError

logger = logging.getLogger(__name__)

# LMD matched subset — the index maps MD5 hash -> (artist, title) metadata
# and the tar archive contains files organised as <first_char>/<md5>.mid
_LMD_MATCHED_URL = "http://hog.ee.columbia.edu/craffel/lmd/lmd_matched.tar.gz"
_LMD_INDEX_URL = "http://hog.ee.columbia.edu/craffel/lmd/lmd_matched_h5.tar.gz"

# Lightweight metadata CSV produced by Colin Raffel that lists
# md5, artist, title — available as a plain text companion to the dataset.
# We use the metadata CSV instead of the full H5 index for simplicity.
_METADATA_CSV_URL = "http://hog.ee.columbia.edu/craffel/lmd/lmd_matched_metadata.tar.gz"

# Fallback: direct path template inside the tar archive
_MIDI_PATH_TEMPLATE = "{first}/{md5}.mid"


class LakhDownloader:
    """Downloads MIDI files from the Lakh MIDI Dataset matched subset.

    The downloader caches the LMD index locally and avoids re-downloading
    MIDI files that are already present in *cache_dir*.

    Parameters
    ----------
    cache_dir:
        Directory where the index and downloaded MIDI files are stored.
        Created automatically if it does not exist.
    """

    _INDEX_FILENAME = "lmd_index.tsv"

    def __init__(self, cache_dir: Path = Path(".midi_cache")) -> None:
        self._cache_dir = cache_dir
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._index: dict[tuple[str, str], str] | None = None  # (artist, title) -> md5

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def download(self, artist: str, title: str) -> Path:
        """Download the MIDI file for *artist* / *title* and return its local path.

        The file is cached in *cache_dir*; subsequent calls for the same
        song return immediately without hitting the network.

        Parameters
        ----------
        artist:
            Artist name as it appears in the LMD matched metadata (case-insensitive).
        title:
            Song title as it appears in the LMD matched metadata (case-insensitive).

        Returns
        -------
        Path
            Absolute path to the cached ``.mid`` file.

        Raises
        ------
        DownloadError
            If the song cannot be found in the index or the download fails.
        """
        index = self._load_index()
        md5 = self._lookup(index, artist, title)
        if md5 is None:
            raise DownloadError(
                f"Could not find '{title}' by '{artist}' in the LMD matched index."
            )
        return self._fetch_midi(md5, artist, title)

    # ------------------------------------------------------------------
    # Index management
    # ------------------------------------------------------------------

    def _index_path(self) -> Path:
        return self._cache_dir / self._INDEX_FILENAME

    def _load_index(self) -> dict[tuple[str, str], str]:
        """Return (artist, title) -> md5 mapping, building it on first call."""
        if self._index is not None:
            return self._index

        cached = self._index_path()
        if cached.exists():
            logger.debug("Loading LMD index from cache: %s", cached)
            self._index = self._parse_tsv(cached.read_text(encoding="utf-8"))
            return self._index

        logger.info("Downloading LMD matched metadata index …")
        self._index = self._download_index()
        return self._index

    def _download_index(self) -> dict[tuple[str, str], str]:
        """Download the LMD metadata tar.gz, extract the TSV, cache and return it."""
        try:
            data = self._http_get_bytes(_METADATA_CSV_URL, desc="LMD metadata index")
        except requests.RequestException as exc:
            raise DownloadError(f"Failed to download LMD index: {exc}") from exc

        # The archive contains a single CSV/TSV with columns:
        # md5, artist, title  (no header)
        tsv_content = self._extract_tsv_from_tar(data)
        cached = self._index_path()
        cached.write_text(tsv_content, encoding="utf-8")
        logger.info("LMD index cached to %s", cached)
        return self._parse_tsv(tsv_content)

    def _extract_tsv_from_tar(self, tar_bytes: bytes) -> str:
        """Extract the first text file from a tar.gz and return its content."""
        with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:gz") as tf:
            for member in tf.getmembers():
                if member.isfile():
                    f = tf.extractfile(member)
                    if f is not None:
                        return f.read().decode("utf-8", errors="replace")
        raise DownloadError("LMD metadata archive contained no readable files.")

    @staticmethod
    def _parse_tsv(text: str) -> dict[tuple[str, str], str]:
        """Parse a TSV/CSV of (md5, artist, title) rows into a lookup dict.

        Keys are normalised (stripped, lower-cased) for fuzzy matching.
        """
        index: dict[tuple[str, str], str] = {}
        reader = csv.reader(io.StringIO(text), delimiter="\t")
        for row in reader:
            if len(row) < 3:
                continue
            md5, artist, title = row[0].strip(), row[1].strip(), row[2].strip()
            if md5 and artist and title:
                key = (artist.lower(), title.lower())
                index[key] = md5
        logger.debug("LMD index loaded: %d entries", len(index))
        return index

    @staticmethod
    def _lookup(
        index: dict[tuple[str, str], str], artist: str, title: str
    ) -> str | None:
        """Look up the md5 for *artist* / *title* (case-insensitive)."""
        return index.get((artist.lower().strip(), title.lower().strip()))

    # ------------------------------------------------------------------
    # MIDI download
    # ------------------------------------------------------------------

    def _midi_cache_path(self, md5: str) -> Path:
        return self._cache_dir / f"{md5}.mid"

    def _fetch_midi(self, md5: str, artist: str, title: str) -> Path:
        """Return cached MIDI or download it from the LMD archive."""
        local = self._midi_cache_path(md5)
        if local.exists():
            logger.info("MIDI already cached: %s", local)
            return local

        logger.info("Downloading MIDI for '%s' – '%s' (md5=%s) …", artist, title, md5)
        midi_bytes = self._download_midi_from_archive(md5)
        local.write_bytes(midi_bytes)
        logger.info("MIDI saved to %s", local)
        return local

    def _download_midi_from_archive(self, md5: str) -> bytes:
        """Download the full LMD matched tar.gz and extract the MIDI for *md5*."""
        # LMD stores files as lmd_matched/<A>/<md5>.mid inside the archive
        target_suffix = f"/{md5}.mid"
        try:
            resp = requests.get(_LMD_MATCHED_URL, stream=True, timeout=60)
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            buf = io.BytesIO()
            with tqdm(
                total=total or None,
                unit="B",
                unit_scale=True,
                desc="LMD archive",
                leave=False,
            ) as pbar:
                for chunk in resp.iter_content(chunk_size=65536):
                    buf.write(chunk)
                    pbar.update(len(chunk))
        except requests.RequestException as exc:
            raise DownloadError(f"Failed to download LMD archive: {exc}") from exc

        buf.seek(0)
        with tarfile.open(fileobj=buf, mode="r:gz") as tf:
            for member in tf.getmembers():
                if member.name.endswith(target_suffix) and member.isfile():
                    f = tf.extractfile(member)
                    if f is not None:
                        return f.read()

        raise DownloadError(
            f"MIDI for md5={md5} not found inside LMD matched archive."
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _http_get_bytes(url: str, desc: str = "") -> bytes:
        """Download *url* and return raw bytes with a tqdm progress bar."""
        resp = requests.get(url, stream=True, timeout=60)
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        buf = io.BytesIO()
        with tqdm(
            total=total or None, unit="B", unit_scale=True, desc=desc, leave=False
        ) as pbar:
            for chunk in resp.iter_content(chunk_size=65536):
                buf.write(chunk)
                pbar.update(len(chunk))
        return buf.getvalue()
