"""Tests for phone number normalization and filtering."""

import pytest
from pathlib import Path
from call_draw.normalizer import (
    normalize_number,
    load_contacts_exclusion,
    normalize_calls,
)


class TestNormalizeNumber:
    """Tests for phone number normalization."""

    def test_normalize_with_plus(self):
        """Test normalization preserves leading plus."""
        assert normalize_number("+1 555 000 1111") == "+15550001111"
        assert normalize_number("+1-555-000-1111") == "+15550001111"

    def test_normalize_without_plus(self):
        """Test normalization of numbers without plus."""
        assert normalize_number("15550001111") == "15550001111"
        assert normalize_number("1 555 000 1111") == "15550001111"
        assert normalize_number("1-555-000-1111") == "15550001111"

    def test_normalize_empty(self):
        """Test normalization of empty strings."""
        assert normalize_number("") == ""
        assert normalize_number("   ") == ""

    def test_normalize_non_digits(self):
        """Test that only digits and leading plus are kept."""
        assert normalize_number("+1 (555) 000-1111 ext. 123") == "+15550001111123"
        assert normalize_number("555-ABC-1111") == "5551111"

    def test_normalize_plus_in_middle(self):
        """Test that plus in the middle is treated as non-digit."""
        # Plus only matters if leading
        assert normalize_number("1+555+000+1111") == "15550001111"


class TestLoadContactsExclusion:
    """Tests for loading contact exclusion list."""

    def test_load_nonexistent_file(self):
        """Test loading from non-existent file returns empty set."""
        result = load_contacts_exclusion(Path("/nonexistent/path.csv"))
        assert result == set()

    def test_load_none_path(self):
        """Test loading with None path returns empty set."""
        result = load_contacts_exclusion(None)
        assert result == set()

    def test_load_contacts_csv(self, tmp_path):
        """Test loading actual contacts CSV."""
        contacts_file = tmp_path / "contacts.csv"
        contacts_file.write_text("number\n+1 555 000 1111\n1-555-000-2222\n")

        result = load_contacts_exclusion(contacts_file)

        assert "+15550001111" in result
        assert "15550002222" in result
        assert len(result) == 2

    def test_load_contacts_normalizes(self, tmp_path):
        """Test that contacts are normalized during load."""
        contacts_file = tmp_path / "contacts.csv"
        contacts_file.write_text("number\n+1 (555) 000-1111\n555.000.2222\n")

        result = load_contacts_exclusion(contacts_file)

        assert "+15550001111" in result
        assert "5550002222" in result


class TestNormalizeCalls:
    """Tests for normalizing and filtering call records."""

    def test_normalize_calls_basic(self):
        """Test basic call normalization."""
        calls = [
            {
                "timestamp": "2026-10-09T23:16:05Z",
                "number": "+1 555 000 1111",
                "direction": "incoming",
                "duration_sec": 123,
                "caller_id_name": "Test",
            },
        ]

        result = normalize_calls(calls)

        assert len(result) == 1
        assert result[0]["number"] == "+15550001111"

    def test_normalize_calls_exclude_contacts(self, tmp_path):
        """Test filtering out known contacts."""
        contacts_file = tmp_path / "contacts.csv"
        contacts_file.write_text("number\n+1 555 000 1111\n")

        calls = [
            {
                "timestamp": "2026-10-09T23:16:05Z",
                "number": "+1 555 000 1111",
                "direction": "incoming",
                "duration_sec": 123,
                "caller_id_name": "Known",
            },
            {
                "timestamp": "2026-10-09T23:16:05Z",
                "number": "+1 555 000 2222",
                "direction": "incoming",
                "duration_sec": 45,
                "caller_id_name": "Unknown",
            },
        ]

        result = normalize_calls(calls, contacts_file)

        # Should only have the unknown contact
        assert len(result) == 1
        assert result[0]["number"] == "+15550002222"

    def test_normalize_calls_empty_number(self):
        """Test filtering out calls with empty numbers."""
        calls = [
            {
                "timestamp": "2026-10-09T23:16:05Z",
                "number": "",
                "direction": "incoming",
                "duration_sec": 123,
                "caller_id_name": "Test",
            },
        ]

        result = normalize_calls(calls)

        assert len(result) == 0

    def test_normalize_calls_non_digits_only(self):
        """Test filtering out calls with no digits in number."""
        calls = [
            {
                "timestamp": "2026-10-09T23:16:05Z",
                "number": "no-digits-here",
                "direction": "incoming",
                "duration_sec": 123,
                "caller_id_name": "Test",
            },
        ]

        result = normalize_calls(calls)

        assert len(result) == 0

    def test_normalize_calls_preserves_other_fields(self):
        """Test that normalization preserves other fields."""
        calls = [
            {
                "timestamp": "2026-10-09T23:16:05Z",
                "number": "+1 555 000 1111",
                "direction": "outgoing",
                "duration_sec": 999,
                "caller_id_name": "Important Info",
            },
        ]

        result = normalize_calls(calls)

        assert result[0]["timestamp"] == "2026-10-09T23:16:05Z"
        assert result[0]["direction"] == "outgoing"
        assert result[0]["duration_sec"] == 999
        assert result[0]["caller_id_name"] == "Important Info"
