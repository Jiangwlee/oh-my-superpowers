"""Download capture and range serving.

Chrome is put in ``allowAndName`` download mode against ``DOWNLOAD_DIR``: each
download is written to ``{DOWNLOAD_DIR}/{guid}`` and reported via
``Browser.downloadWillBegin`` (suggested filename) and ``Browser.downloadProgress``
(bytes + terminal state). We keep one record per guid and serve its bytes by
range so mindora can pull large files in bounded-memory chunks.

Capture is browser-level (single-user, one browser), not per page target: the
single-focus-tab invariant recycles targets (session.reconcile_focus), so a
per-target hook would lose downloads. The container only stores and serves raw
bytes — unzip / pdf / office extraction is mindora's job (ADR 0056).
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from typing import Any

# tmpfs, deterministic, transient. Retention is the container's concern (ADR
# 0056): mindora fetches then optionally DELETEs; nothing here is a mindora SoT.
DOWNLOAD_DIR = os.environ.get("OMP_DOWNLOAD_DIR", "/data/downloads")


class DownloadNotFound(Exception):
    """No download with this guid is known to the registry."""


class DownloadNotReady(Exception):
    """The download exists but has not completed (bytes not fully on disk)."""


@dataclass
class DownloadRecord:
    guid: str
    filename: str = ""
    total_bytes: int = 0
    received_bytes: int = 0
    # inProgress | completed | canceled — mirrors Browser.downloadProgress.state
    state: str = "inProgress"
    _sha256: str | None = field(default=None, repr=False)


class DownloadRegistry:
    """In-memory index of downloads captured from the Browser domain."""

    def __init__(self, download_dir: str = DOWNLOAD_DIR) -> None:
        # The dir is created by entrypoint.sh and written by Chrome, not here —
        # the registry only indexes and serves. No eager mkdir at construction.
        self._dir = download_dir
        self._records: dict[str, DownloadRecord] = {}

    # -- CDP event sinks (run inside the reader loop; must not block) --------

    def on_will_begin(self, params: dict[str, Any]) -> None:
        """Browser.downloadWillBegin: {guid, url, suggestedFilename, frameId}."""
        guid = params.get("guid")
        if not guid:
            return
        rec = self._records.get(guid) or DownloadRecord(guid=guid)
        rec.filename = params.get("suggestedFilename") or rec.filename
        self._records[guid] = rec

    def on_progress(self, params: dict[str, Any]) -> None:
        """Browser.downloadProgress: {guid, totalBytes, receivedBytes, state}."""
        guid = params.get("guid")
        if not guid:
            return
        rec = self._records.get(guid) or DownloadRecord(guid=guid)
        rec.total_bytes = int(params.get("totalBytes") or rec.total_bytes)
        rec.received_bytes = int(params.get("receivedBytes") or rec.received_bytes)
        rec.state = params.get("state") or rec.state
        # A new terminal state invalidates any cached hash.
        rec._sha256 = None
        self._records[guid] = rec

    # -- REST consumption ----------------------------------------------------

    def list(self) -> list[DownloadRecord]:
        return list(self._records.values())

    def get(self, guid: str) -> DownloadRecord:
        rec = self._records.get(guid)
        if rec is None:
            raise DownloadNotFound(guid)
        return rec

    def path(self, guid: str) -> str:
        """On-disk path of a download's bytes ({dir}/{guid}, allowAndName)."""
        return os.path.join(self._dir, self.get(guid).guid)

    def read_range(self, guid: str, offset: int = 0, length: int | None = None) -> bytes:
        """Read ``length`` bytes from ``offset`` of the download's file.

        Bounded memory: seeks and reads only the requested window, never the
        whole file. ``length=None`` reads to EOF.
        """
        if self.get(guid).state != "completed":
            raise DownloadNotReady(guid)
        with open(self.path(guid), "rb") as f:
            f.seek(max(0, offset))
            return f.read(length if (length is not None and length >= 0) else -1)

    def sha256(self, guid: str) -> str:
        """Content hash of a completed download, computed once and cached."""
        rec = self.get(guid)
        if rec.state != "completed":
            raise DownloadNotReady(guid)
        if rec._sha256 is None:
            h = hashlib.sha256()
            with open(self.path(guid), "rb") as f:
                for block in iter(lambda: f.read(1 << 20), b""):
                    h.update(block)
            rec._sha256 = h.hexdigest()
        return rec._sha256

    def size_on_disk(self, guid: str) -> int:
        try:
            return os.path.getsize(self.path(guid))
        except OSError:
            return 0

    def delete(self, guid: str) -> None:
        if guid not in self._records:
            raise DownloadNotFound(guid)
        target = self.path(guid)
        self._records.pop(guid, None)
        try:
            os.remove(target)
        except OSError:
            pass
