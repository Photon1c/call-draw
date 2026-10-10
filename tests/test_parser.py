"""Tests for the call log parser."""

import pytest
from pathlib import Path
from datetime import datetime
from call_draw.parser import parse_call_log, CALL_TYPE_MAP, write_calls_csv


@pytest.fixture
def sample_calls_file(tmp_path):
    """Create a sample calls_raw.txt file for testing."""
    content = """Row: 0 number=+15550001111, duration=0, date=1791593765696, type=3, name=NULL
Row: 1 number=+15550002222, duration=123, date=1791590851296, type=1, name=Test Contact
Row: 2 number=+15550003333, duration=45, date=1791590846707, type=2, name=
Row: 3 
Row: 4 INVALID LINE
Row: 5 number=+15550004444, duration=999, date=INVALID_DATE, type=1, name=Bad Date
Row: 6 number=, duration=0, date=1791593765696, type=1, name=No Number
"""
    file_path = tmp_path / "calls_raw.txt"
    file_path.write_text(content)
    return file_path


def test_parse_call_log_basic(sample_calls_file):
    """Test basic parsing of call log."""
    calls, skipped = parse_call_log(sample_calls_file)

    # Should have 3 valid calls (rows 0, 1, 2)
    assert len(calls) == 3
    # Should skip 4 lines (rows 3, 4, 5, 6)
    assert skipped == 4


def test_parse_call_log_columns():
    """Test that parsed calls have correct columns."""
    content = (
        "Row: 0 number=+15550001111, duration=0, date=1791593765696, type=1, name=Test"
    )
    file_path = Path("/tmp/test_calls.txt")
    file_path.write_text(content)

    try:
        calls, _ = parse_call_log(file_path)
        assert len(calls) == 1

        call = calls[0]
        assert "timestamp" in call
        assert "number" in call
        assert "direction" in call
        assert "duration_sec" in call
        assert "caller_id_name" in call

        assert call["number"] == "+15550001111"
        assert call["direction"] == "incoming"
        assert call["duration_sec"] == 0
        assert call["caller_id_name"] == "Test"
    finally:
        file_path.unlink()


def test_parse_call_log_date_conversion():
    """Test epoch milliseconds to ISO 8601 conversion."""
    # 1791593765696 ms = 2026-10-09T23:16:05+00:00
    content = (
        "Row: 0 number=+15550001111, duration=0, date=1791593765696, type=1, name=Test"
    )
    file_path = Path("/tmp/test_date.txt")
    file_path.write_text(content)

    try:
        calls, _ = parse_call_log(file_path)
        assert len(calls) == 1

        timestamp = calls[0]["timestamp"]
        # Should contain timezone info (either +00:00 or Z)
        assert "+" in timestamp or "Z" in timestamp
        # Should be ISO format
        datetime.fromisoformat(timestamp)
    finally:
        file_path.unlink()


def test_parse_call_log_type_mapping():
    """Test call type to direction mapping."""
    content = """Row: 0 number=+15550001111, duration=0, date=1791593765696, type=1, name=Test
Row: 1 number=+15550002222, duration=0, date=1791593765696, type=2, name=Test
Row: 2 number=+15550003333, duration=0, date=1791593765696, type=3, name=Test
Row: 3 number=+15550004444, duration=0, date=1791593765696, type=99, name=Test
"""
    file_path = Path("/tmp/test_types.txt")
    file_path.write_text(content)

    try:
        calls, _ = parse_call_log(file_path)

        # type=1 should map to incoming
        assert calls[0]["direction"] == "incoming"
        # type=2 should map to outgoing
        assert calls[1]["direction"] == "outgoing"
        # type=3 should map to missed
        assert calls[2]["direction"] == "missed"
        # Unknown type should map to unknown
        assert calls[3]["direction"] == "unknown"
    finally:
        file_path.unlink()


def test_parse_call_log_null_names():
    """Test handling of NULL and empty caller ID names."""
    content = """Row: 0 number=+15550001111, duration=0, date=1791593765696, type=1, name=NULL
Row: 1 number=+15550002222, duration=0, date=1791593765696, type=1, name=
"""
    file_path = Path("/tmp/test_null.txt")
    file_path.write_text(content)

    try:
        calls, _ = parse_call_log(file_path)
        assert len(calls) == 2
        assert calls[0]["caller_id_name"] == ""
        assert calls[1]["caller_id_name"] == ""
    finally:
        file_path.unlink()


def test_write_calls_csv(tmp_path):
    """Test writing calls to CSV file."""
    output_path = tmp_path / "output.csv"

    calls = [
        {
            "timestamp": "2026-10-09T23:16:05Z",
            "number": "+15550001111",
            "direction": "incoming",
            "duration_sec": 123,
            "caller_id_name": "Test",
        },
        {
            "timestamp": "2026-10-09T23:15:00Z",
            "number": "+15550002222",
            "direction": "outgoing",
            "duration_sec": 45,
            "caller_id_name": "",
        },
    ]

    write_calls_csv(calls, output_path)

    assert output_path.exists()

    # Verify CSV content
    content = output_path.read_text()
    lines = content.strip().split("\n")

    assert len(lines) == 3  # header + 2 records
    assert "timestamp,number,direction,duration_sec,caller_id_name" in lines[0]
    assert "+15550001111" in content
    assert "+15550002222" in content
