"""Parser for Android call log exports."""

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Tuple


# Mapping of Android call type codes to direction labels
# type=1: incoming, type=2: outgoing, type=3: missed
CALL_TYPE_MAP = {
    "1": "incoming",
    "2": "outgoing",
    "3": "missed",
}


def parse_call_log(input_path: Path) -> Tuple[List[Dict], int]:
    """
    Parse Android call log export from adb shell content query.

    Input format: one row per line, "Row: N key=value, key=value, ..."
    Output: list of parsed call records and count of skipped lines.

    Args:
        input_path: Path to calls_raw.txt file

    Returns:
        Tuple of (list of call dicts, count of skipped lines)
    """
    calls = []
    skipped = 0

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                line = line.strip()

                # Skip empty lines
                if not line:
                    skipped += 1
                    continue

                # Parse "Row: N key=value, key=value, ..."
                if not line.startswith("Row:"):
                    skipped += 1
                    continue

                try:
                    # Extract the key=value pairs part
                    row_content = line.split(" ", 2)  # ["Row:", "N", "key=value, ..."]
                    if len(row_content) < 3:
                        skipped += 1
                        continue

                    kv_string = row_content[2]

                    # Parse key=value pairs, handling commas inside quoted values
                    parsed = _parse_key_values(kv_string)

                    # Extract required fields
                    number = parsed.get("number", "").strip()
                    date_str = parsed.get("date", "").strip()
                    duration_str = parsed.get("duration", "").strip()
                    call_type = parsed.get("type", "").strip()
                    caller_id_name = parsed.get("name", "").strip()

                    # Skip if missing critical fields
                    if not number or not date_str:
                        skipped += 1
                        continue

                    # Convert date from epoch milliseconds to ISO 8601
                    try:
                        timestamp_ms = int(date_str)
                        timestamp = datetime.fromtimestamp(
                            timestamp_ms / 1000, tz=timezone.utc
                        ).isoformat()
                    except (ValueError, OSError):
                        skipped += 1
                        continue

                    # Convert duration to seconds (assume it's already in seconds)
                    try:
                        duration_sec = int(duration_str) if duration_str else 0
                    except ValueError:
                        duration_sec = 0

                    # Map call type to direction
                    direction = CALL_TYPE_MAP.get(call_type, "unknown")

                    # Handle NULL and empty caller ID names
                    if caller_id_name in ("NULL", ""):
                        caller_id_name = ""

                    call_record = {
                        "timestamp": timestamp,
                        "number": number,
                        "direction": direction,
                        "duration_sec": duration_sec,
                        "caller_id_name": caller_id_name,
                    }

                    calls.append(call_record)

                except Exception:
                    skipped += 1
                    continue

    except Exception:
        pass

    return calls, skipped


def _parse_key_values(kv_string: str) -> Dict[str, str]:
    """
    Parse key=value pairs from a comma-separated string.
    Handles NULL values and missing values gracefully.

    Args:
        kv_string: String like "key1=value1, key2=value2, ..."

    Returns:
        Dictionary of parsed key-value pairs
    """
    result = {}

    # Split by ", " but be careful about values containing commas
    # Use a simple state machine approach
    current_key = None
    current_value = []
    in_quotes = False

    i = 0
    while i < len(kv_string):
        char = kv_string[i]

        if char == "=" and current_key is None:
            # Found the = separator
            current_key = "".join(current_value).strip()
            current_value = []
            i += 1
            continue

        if char == "," and not in_quotes and current_key is not None:
            # End of this key-value pair
            value = "".join(current_value).strip()
            result[current_key] = value
            current_key = None
            current_value = []
            # Skip the comma and following space
            i += 1
            if i < len(kv_string) and kv_string[i] == " ":
                i += 1
            continue

        current_value.append(char)
        i += 1

    # Handle the last key-value pair
    if current_key is not None:
        value = "".join(current_value).strip()
        result[current_key] = value

    return result


def write_calls_csv(calls: List[Dict], output_path: Path) -> None:
    """
    Write parsed calls to CSV with standard columns.

    Args:
        calls: List of call record dictionaries
        output_path: Path to output CSV file
    """
    columns = ["timestamp", "number", "direction", "duration_sec", "caller_id_name"]

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(calls)
