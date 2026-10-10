"""Tests for the summary dashboard."""

import pytest
from pathlib import Path
from call_draw.dashboard import (
    load_organization_map,
    generate_summary,
    write_summary_csv,
    extract_unknown_callers,
    write_unknown_callers_csv,
)


class TestLoadOrganizationMap:
    """Tests for loading organization mapping."""

    def test_load_nonexistent_file(self):
        """Test loading from non-existent file returns empty dict."""
        result = load_organization_map(Path("/nonexistent/path.csv"))
        assert result == {}

    def test_load_organization_map(self, tmp_path):
        """Test loading organization CSV."""
        org_file = tmp_path / "orgs.csv"
        org_file.write_text(
            "number,organization\n+15550001111,Spam Co\n+15550002222,Bad Inc\n"
        )

        result = load_organization_map(org_file)

        assert result["+15550001111"] == "Spam Co"
        assert result["+15550002222"] == "Bad Inc"
        assert len(result) == 2


class TestGenerateSummary:
    """Tests for summary generation."""

    def test_generate_summary_with_org_labels(self, tmp_path):
        """Test summary generation with organization labels."""
        org_file = tmp_path / "orgs.csv"
        org_file.write_text("number,organization\n+15550001111,Spam Co\n")

        calls = [
            {
                "timestamp": "2026-10-09T23:16:00+00:00",
                "number": "+15550001111",
                "direction": "incoming",
                "duration_sec": 0,
                "caller_id_name": "",
            },
            {
                "timestamp": "2026-10-09T23:17:00+00:00",
                "number": "+15550001111",
                "direction": "incoming",
                "duration_sec": 0,
                "caller_id_name": "",
            },
        ]

        summary = generate_summary(calls, org_file)

        assert len(summary) == 1
        assert summary[0]["organization"] == "Spam Co"
        assert summary[0]["call_count"] == 2
        assert summary[0]["unique_numbers"] == 1

    def test_generate_summary_with_caller_id(self, tmp_path):
        """Test summary generation groups by caller ID when no org label."""
        org_file = tmp_path / "orgs.csv"
        org_file.write_text("number,organization\n")

        calls = [
            {
                "timestamp": "2026-10-09T23:16:00+00:00",
                "number": "+15550001111",
                "direction": "incoming",
                "duration_sec": 0,
                "caller_id_name": "Mom",
            },
            {
                "timestamp": "2026-10-09T23:17:00+00:00",
                "number": "+15550001112",
                "direction": "incoming",
                "duration_sec": 0,
                "caller_id_name": "Mom",
            },
        ]

        summary = generate_summary(calls, org_file)

        assert len(summary) == 1
        assert summary[0]["organization"] == "Mom"
        assert summary[0]["call_count"] == 2
        assert summary[0]["unique_numbers"] == 2

    def test_generate_summary_with_prefix_fallback(self, tmp_path):
        """Test summary groups unknown calls by number prefix."""
        org_file = tmp_path / "orgs.csv"
        org_file.write_text("number,organization\n")

        calls = [
            {
                "timestamp": "2026-10-09T23:16:00+00:00",
                "number": "+15550001111",
                "direction": "incoming",
                "duration_sec": 0,
                "caller_id_name": "",
            },
            {
                "timestamp": "2026-10-09T23:17:00+00:00",
                "number": "+15550001112",
                "direction": "incoming",
                "duration_sec": 0,
                "caller_id_name": "",
            },
        ]

        summary = generate_summary(calls, org_file)

        # Both should be in same group based on prefix
        assert len(summary) == 1
        assert "Unknown" in summary[0]["organization"]
        assert summary[0]["call_count"] == 2
        assert summary[0]["unique_numbers"] == 2

    def test_generate_summary_timestamps(self, tmp_path):
        """Test that first_seen and last_seen are correctly identified."""
        org_file = tmp_path / "orgs.csv"
        org_file.write_text("number,organization\n+15550001111,Test Org\n")

        calls = [
            {
                "timestamp": "2026-10-09T23:15:00+00:00",
                "number": "+15550001111",
                "direction": "incoming",
                "duration_sec": 0,
                "caller_id_name": "",
            },
            {
                "timestamp": "2026-10-09T23:20:00+00:00",
                "number": "+15550001111",
                "direction": "incoming",
                "duration_sec": 0,
                "caller_id_name": "",
            },
        ]

        summary = generate_summary(calls, org_file)

        assert summary[0]["first_seen"] == "2026-10-09T23:15:00+00:00"
        assert summary[0]["last_seen"] == "2026-10-09T23:20:00+00:00"


class TestWriteSummaryCsv:
    """Tests for writing summary CSV."""

    def test_write_summary_csv(self, tmp_path):
        """Test writing summary to CSV file."""
        output_path = tmp_path / "summary.csv"

        summary = [
            {
                "organization": "Spam Co",
                "call_count": 5,
                "unique_numbers": 2,
                "first_seen": "2026-10-09T23:15:00+00:00",
                "last_seen": "2026-10-09T23:20:00+00:00",
            },
            {
                "organization": "Bad Inc",
                "call_count": 3,
                "unique_numbers": 1,
                "first_seen": "2026-10-09T23:10:00+00:00",
                "last_seen": "2026-10-09T23:25:00+00:00",
            },
        ]

        write_summary_csv(summary, output_path)

        assert output_path.exists()

        content = output_path.read_text()
        lines = content.strip().split("\n")

        assert len(lines) == 3  # header + 2 records
        assert "organization,call_count,unique_numbers,first_seen,last_seen" in lines[0]
        assert "Spam Co" in content
        assert "Bad Inc" in content


class TestExtractUnknownCallers:
    """Tests for unknown callers extraction."""

    def test_extract_unknown_callers_basic(self, tmp_path):
        """Test extracting unknown callers (no org, no caller_id)."""
        org_file = tmp_path / "orgs.csv"
        org_file.write_text("number,organization\n+15550001111,Spam Co\n")

        calls = [
            {
                "timestamp": "2026-10-09T23:16:00+00:00",
                "number": "+15550001111",
                "direction": "incoming",
                "duration_sec": 0,
                "caller_id_name": "",
            },
            {
                "timestamp": "2026-10-09T23:17:00+00:00",
                "number": "+15550002222",
                "direction": "incoming",
                "duration_sec": 0,
                "caller_id_name": "",
            },
            {
                "timestamp": "2026-10-09T23:18:00+00:00",
                "number": "+15550003333",
                "direction": "incoming",
                "duration_sec": 0,
                "caller_id_name": "Mom",
            },
        ]

        unknown = extract_unknown_callers(calls, org_file)

        # Should only have +15550002222, not +15550001111 (org) or +15550003333 (caller_id)
        assert len(unknown) == 1
        assert unknown[0]["call_count"] == 1
        assert unknown[0]["unique_numbers"] == 1

    def test_extract_unknown_callers_grouping_by_prefix(self, tmp_path):
        """Test that unknown callers are grouped by prefix."""
        org_file = tmp_path / "orgs.csv"
        org_file.write_text("number,organization\n")

        calls = [
            {
                "timestamp": "2026-10-09T23:16:00+00:00",
                "number": "+15550001111",
                "direction": "incoming",
                "duration_sec": 0,
                "caller_id_name": "",
            },
            {
                "timestamp": "2026-10-09T23:17:00+00:00",
                "number": "+15550001112",
                "direction": "incoming",
                "duration_sec": 0,
                "caller_id_name": "",
            },
            {
                "timestamp": "2026-10-09T23:18:00+00:00",
                "number": "+12060001111",
                "direction": "incoming",
                "duration_sec": 0,
                "caller_id_name": "",
            },
        ]

        unknown = extract_unknown_callers(calls, org_file)

        # Should have 2 prefixes: +15550 and +12060
        assert len(unknown) == 2

        # Find the +15550 prefix (should have 2 calls)
        prefix_15550 = [u for u in unknown if u["prefix"] == "+15550"][0]
        assert prefix_15550["call_count"] == 2
        assert prefix_15550["unique_numbers"] == 2

    def test_extract_unknown_callers_sample_numbers(self, tmp_path):
        """Test that sample numbers are included."""
        org_file = tmp_path / "orgs.csv"
        org_file.write_text("number,organization\n")

        calls = [
            {
                "timestamp": "2026-10-09T23:16:00+00:00",
                "number": "+15550001111",
                "direction": "incoming",
                "duration_sec": 0,
                "caller_id_name": "",
            },
            {
                "timestamp": "2026-10-09T23:17:00+00:00",
                "number": "+15550001112",
                "direction": "incoming",
                "duration_sec": 0,
                "caller_id_name": "",
            },
        ]

        unknown = extract_unknown_callers(calls, org_file)

        assert len(unknown) == 1
        assert "+15550001111" in unknown[0]["sample_numbers"]
        assert "+15550001112" in unknown[0]["sample_numbers"]

    def test_extract_unknown_callers_sorted_by_count(self, tmp_path):
        """Test that unknown callers are sorted by call count descending."""
        org_file = tmp_path / "orgs.csv"
        org_file.write_text("number,organization\n")

        calls = [
            # Prefix +155500: 5 calls
            {
                "timestamp": "2026-10-09T23:16:00+00:00",
                "number": "+15550001111",
                "direction": "incoming",
                "duration_sec": 0,
                "caller_id_name": "",
            },
            {
                "timestamp": "2026-10-09T23:17:00+00:00",
                "number": "+15550001111",
                "direction": "incoming",
                "duration_sec": 0,
                "caller_id_name": "",
            },
            {
                "timestamp": "2026-10-09T23:18:00+00:00",
                "number": "+15550001111",
                "direction": "incoming",
                "duration_sec": 0,
                "caller_id_name": "",
            },
            {
                "timestamp": "2026-10-09T23:19:00+00:00",
                "number": "+15550001111",
                "direction": "incoming",
                "duration_sec": 0,
                "caller_id_name": "",
            },
            {
                "timestamp": "2026-10-09T23:20:00+00:00",
                "number": "+15550001111",
                "direction": "incoming",
                "duration_sec": 0,
                "caller_id_name": "",
            },
            # Prefix +120600: 2 calls
            {
                "timestamp": "2026-10-09T23:16:00+00:00",
                "number": "+12060001111",
                "direction": "incoming",
                "duration_sec": 0,
                "caller_id_name": "",
            },
            {
                "timestamp": "2026-10-09T23:17:00+00:00",
                "number": "+12060001111",
                "direction": "incoming",
                "duration_sec": 0,
                "caller_id_name": "",
            },
        ]

        unknown = extract_unknown_callers(calls, org_file)

        assert len(unknown) == 2
        assert unknown[0]["call_count"] == 5  # +155500
        assert unknown[1]["call_count"] == 2  # +120600


class TestWriteUnknownCallersCsv:
    """Tests for writing unknown callers CSV."""

    def test_write_unknown_callers_csv(self, tmp_path):
        """Test writing unknown callers to CSV file."""
        output_path = tmp_path / "unknown.csv"

        unknown = [
            {
                "prefix": "+155500",
                "call_count": 5,
                "unique_numbers": 2,
                "sample_numbers": "+15550001111, +15550001112",
                "first_seen": "2026-10-09T23:15:00+00:00",
                "last_seen": "2026-10-09T23:20:00+00:00",
            },
        ]

        write_unknown_callers_csv(unknown, output_path)

        assert output_path.exists()

        content = output_path.read_text()
        lines = content.strip().split("\n")

        assert len(lines) == 2  # header + 1 record
        assert (
            "prefix,call_count,unique_numbers,sample_numbers,first_seen,last_seen"
            in lines[0]
        )
        assert "+155500" in content
