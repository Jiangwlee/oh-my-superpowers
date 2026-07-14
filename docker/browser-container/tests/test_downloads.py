# file: tests/test_downloads.py
# role: unit tests for DownloadRegistry (event sinks, range read, sha256, delete)
#       and the REST Range parser. Pure logic — no live browser/CDP.
from __future__ import annotations

import hashlib
import os

import pytest

from app.engine.downloads import (
    DownloadNotFound,
    DownloadNotReady,
    DownloadRegistry,
)
from app.rest.main import _content_disposition, _parse_range


@pytest.fixture()
def reg(tmp_path):
    return DownloadRegistry(download_dir=str(tmp_path))


def _complete_download(reg: DownloadRegistry, guid: str, data: bytes, filename="f.zip"):
    reg.on_will_begin({"guid": guid, "suggestedFilename": filename})
    # Chromium writes {downloadPath}/{guid}; simulate that on the registry's dir.
    with open(os.path.join(reg._dir, guid), "wb") as f:
        f.write(data)
    reg.on_progress(
        {"guid": guid, "totalBytes": len(data), "receivedBytes": len(data), "state": "completed"}
    )


def test_will_begin_then_progress_records_filename_and_state(reg):
    reg.on_will_begin({"guid": "g1", "suggestedFilename": "招标.zip"})
    reg.on_progress({"guid": "g1", "totalBytes": 100, "receivedBytes": 40, "state": "inProgress"})
    rec = reg.get("g1")
    assert rec.filename == "招标.zip"
    assert rec.state == "inProgress"
    assert rec.total_bytes == 100 and rec.received_bytes == 40


def test_progress_before_will_begin_still_creates_record(reg):
    # Event ordering is not guaranteed; progress alone must not drop the download.
    reg.on_progress({"guid": "g2", "totalBytes": 10, "receivedBytes": 10, "state": "completed"})
    assert reg.get("g2").state == "completed"


def test_read_range_is_bounded_window(reg):
    data = bytes(range(256)) * 8  # 2048 bytes
    _complete_download(reg, "g3", data)
    assert reg.read_range("g3", 0, 16) == data[0:16]
    assert reg.read_range("g3", 100, 50) == data[100:150]
    assert reg.read_range("g3", 0, None) == data  # full read


def test_read_range_rejects_incomplete(reg):
    reg.on_will_begin({"guid": "g4", "suggestedFilename": "x"})
    reg.on_progress({"guid": "g4", "totalBytes": 100, "receivedBytes": 10, "state": "inProgress"})
    with pytest.raises(DownloadNotReady):
        reg.read_range("g4", 0, 10)


def test_sha256_matches_and_is_cached(reg):
    data = b"hello world" * 1000
    _complete_download(reg, "g5", data)
    assert reg.sha256("g5") == hashlib.sha256(data).hexdigest()
    # Second call hits the cache and stays correct.
    assert reg.sha256("g5") == hashlib.sha256(data).hexdigest()


def test_new_progress_invalidates_hash_cache(reg):
    _complete_download(reg, "g6", b"aaaa")
    first = reg.sha256("g6")
    # Rewrite file + re-signal completion (e.g. a fresh download reusing guid).
    with open(os.path.join(reg._dir, "g6"), "wb") as f:
        f.write(b"bbbbbbbb")
    reg.on_progress({"guid": "g6", "totalBytes": 8, "receivedBytes": 8, "state": "completed"})
    assert reg.sha256("g6") != first


def test_delete_removes_file_and_record(reg):
    _complete_download(reg, "g7", b"data")
    path = reg.path("g7")
    assert os.path.exists(path)
    reg.delete("g7")
    assert not os.path.exists(path)
    with pytest.raises(DownloadNotFound):
        reg.get("g7")


def test_get_unknown_raises(reg):
    with pytest.raises(DownloadNotFound):
        reg.get("nope")


@pytest.mark.parametrize(
    "header,total,expected",
    [
        (None, 100, None),
        ("", 100, None),
        ("bytes=0-9", 100, (0, 9)),
        ("bytes=10-", 100, (10, 99)),
        ("bytes=-20", 100, (80, 99)),
        ("bytes=90-999", 100, (90, 99)),  # end clamped to total-1
        ("bytes=50-40", 100, None),        # start>end unsatisfiable
        ("items=0-9", 100, None),          # non-bytes unit
        ("bytes=0-9", 0, None),            # empty file
    ],
)
def test_parse_range(header, total, expected):
    assert _parse_range(header, total) == expected


def test_content_disposition_encodes_cjk_and_stays_latin1():
    # A CJK filename must survive latin-1 header encoding (regression: 500 on 招标 zip).
    cd = _content_disposition("招标公告附件（新系统）.zip")
    cd.encode("latin-1")  # must not raise
    assert cd.startswith("attachment; filename*=UTF-8''")
    assert "%E6%8B%9B" in cd  # 招 percent-encoded
