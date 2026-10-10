"""Normalize and filter phone numbers."""

import csv
from pathlib import Path
from typing import List, Dict, Set, Optional


def normalize_number(number: str) -> str:
    """
    Normalize a phone number by stripping non-digits, keeping leading +.

    Args:
        number: Raw phone number string

    Returns:
        Normalized number (digits only, with optional leading +)
    """
    if not number:
        return ""

    # Check for leading +
    has_plus = number.lstrip().startswith("+")

    # Strip all non-digits
    digits_only = "".join(c for c in number if c.isdigit())

    # Reconstruct with leading + if present
    if has_plus:
        return "+" + digits_only
    return digits_only


def load_contacts_exclusion(contacts_path: Optional[Path]) -> Set[str]:
    """
    Load contact phone numbers to exclude from analysis.

    Args:
        contacts_path: Path to contacts CSV file (optional)

    Returns:
        Set of normalized phone numbers to exclude
    """
    excluded = set()

    if not contacts_path or not contacts_path.exists():
        return excluded

    try:
        with open(contacts_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if "number" in row:
                    number = row["number"].strip()
                    normalized = normalize_number(number)
                    if normalized:
                        excluded.add(normalized)
    except Exception:
        pass

    return excluded


def normalize_calls(
    calls: List[Dict],
    contacts_path: Optional[Path] = None,
) -> List[Dict]:
    """
    Normalize phone numbers and filter out known contacts.

    Args:
        calls: List of call record dictionaries
        contacts_path: Optional path to contacts CSV for exclusion

    Returns:
        List of filtered and normalized call records
    """
    excluded_contacts = load_contacts_exclusion(contacts_path)
    normalized_calls = []

    for call in calls:
        # Normalize the number
        original_number = call.get("number", "")
        normalized = normalize_number(original_number)

        # Skip if number normalizes to empty
        if not normalized:
            continue

        # Skip if in excluded contacts
        if normalized in excluded_contacts:
            continue

        # Update the call record with normalized number
        call_copy = call.copy()
        call_copy["number"] = normalized
        normalized_calls.append(call_copy)

    return normalized_calls
