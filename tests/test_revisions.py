import pytest
from pydantic import ValidationError

from joseph_api import RevisionFile, RevisionRecord, RevisionWindow


def _record(root_independent: bool = True) -> RevisionRecord:
    files = (
        RevisionFile(path="part-0.parquet", digest="a" * 64, size=10),
        RevisionFile(path="part-1.parquet", digest="b" * 64, size=20),
    )
    return RevisionRecord(
        capability_id="futures_bars",
        schema_version="1",
        source="cnequity@0.25.0",
        revision_id="2024Q1",
        content_digest=RevisionRecord.compute_content_digest(
            "futures_bars", "1", "cnequity@0.25.0", files
        ),
        files=files,
        window=RevisionWindow(start="2024-01-01", end="2024-03-31"),
    )


def test_round_trip_is_byte_identical():
    r = _record()
    assert RevisionRecord.from_json(r.to_json()).to_json() == r.to_json()


def test_unknown_field_is_rejected():
    with pytest.raises(ValidationError):
        RevisionRecord.from_json(
            '{"capability_id":"x","schema_version":"1","source":"s",'
            '"revision_id":"r","content_digest":"d","files":[],"extra":1}'
        )


def test_absolute_path_is_rejected():
    with pytest.raises(ValidationError):
        RevisionFile(path="/etc/passwd", digest="a" * 64, size=1)


def test_digest_is_root_independent():
    files = (RevisionFile(path="a.parquet", digest="a" * 64, size=1),)
    d1 = RevisionRecord.compute_content_digest("c", "1", "s", files)
    d2 = RevisionRecord.compute_content_digest("c", "1", "s", list(files))
    assert d1 == d2 and len(d1) == 64
