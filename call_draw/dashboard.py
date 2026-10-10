"""Summary dashboard: organize calls by organization."""

import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple


def load_organization_map(orgs_path: Path) -> Dict[str, str]:
    """
    Load organization mapping from CSV.

    Expected columns: number, organization

    Args:
        orgs_path: Path to orgs.csv file

    Returns:
        Dictionary mapping phone number to organization label
    """
    org_map = {}

    if not orgs_path.exists():
        return org_map

    try:
        with open(orgs_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if "number" in row and "organization" in row:
                    number = row["number"].strip()
                    org = row["organization"].strip()
                    if number and org:
                        org_map[number] = org
    except Exception:
        pass

    return org_map


def generate_summary(
    calls: List[Dict],
    orgs_path: Path,
) -> List[Dict]:
    """
    Generate organization-level summary of call activity.

    Groups calls by organization (or caller ID / number prefix if unlabeled).

    Args:
        calls: List of call records (assumed already normalized and filtered)
        orgs_path: Path to orgs.csv file

    Returns:
        List of summary records with: organization, call_count, unique_numbers,
        first_seen, last_seen
    """
    org_map = load_organization_map(orgs_path)

    # Group calls by organization
    org_data = defaultdict(
        lambda: {
            "numbers": set(),
            "timestamps": [],
        }
    )

    for call in calls:
        number = call.get("number", "")
        timestamp = call.get("timestamp", "")
        caller_id = call.get("caller_id_name", "")

        # Determine organization label
        if number in org_map:
            org_label = org_map[number]
        elif caller_id:
            org_label = caller_id
        else:
            # Group by number prefix (country code + area code)
            prefix = number[:6] if len(number) >= 6 else number[:3]
            org_label = f"Unknown ({prefix}...)"

        org_data[org_label]["numbers"].add(number)
        if timestamp:
            org_data[org_label]["timestamps"].append(timestamp)

    # Build summary records
    summary = []
    for org_label, data in org_data.items():
        call_count = sum(
            1
            for call in calls
            if (
                call.get("number") in org_map
                and org_map[call.get("number")] == org_label
            )
            or (
                call.get("number") not in org_map
                and (
                    call.get("caller_id_name") == org_label
                    or org_label.startswith("Unknown")
                    and org_label in _get_org_label(call, org_map)
                )
            )
        )

        # Recount more accurately
        call_count = 0
        for call in calls:
            call_org = _get_org_label(call, org_map)
            if call_org == org_label:
                call_count += 1

        unique_numbers = len(data["numbers"])

        # Find first and last seen
        if data["timestamps"]:
            sorted_times = sorted(data["timestamps"])
            first_seen = sorted_times[0]
            last_seen = sorted_times[-1]
        else:
            first_seen = ""
            last_seen = ""

        summary.append(
            {
                "organization": org_label,
                "call_count": call_count,
                "unique_numbers": unique_numbers,
                "first_seen": first_seen,
                "last_seen": last_seen,
            }
        )

    return summary


def _get_org_label(call: Dict, org_map: Dict[str, str]) -> str:
    """Helper to get organization label for a single call."""
    number = call.get("number", "")
    caller_id = call.get("caller_id_name", "")

    if number in org_map:
        return org_map[number]
    elif caller_id:
        return caller_id
    else:
        prefix = number[:6] if len(number) >= 6 else number[:3]
        return f"Unknown ({prefix}...)"


def write_summary_csv(summary: List[Dict], output_path: Path) -> None:
    """
    Write summary to CSV file.

    Args:
        summary: List of summary record dictionaries
        output_path: Path to output CSV file
    """
    columns = [
        "organization",
        "call_count",
        "unique_numbers",
        "first_seen",
        "last_seen",
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(summary)


def print_top_organizations(summary: List[Dict], top_n: int = 25) -> None:
    """
    Print top organizations by call count to terminal.

    Args:
        summary: List of summary record dictionaries
        top_n: Number of top organizations to display
    """
    # Sort by call count descending
    sorted_summary = sorted(summary, key=lambda x: x.get("call_count", 0), reverse=True)

    # Print header
    print(
        f"\n{'Organization':<40} {'Calls':<8} {'Numbers':<10} {'First Seen':<30} {'Last Seen':<30}"
    )
    print("-" * 118)

    # Print top N
    for record in sorted_summary[:top_n]:
        org = record.get("organization", "")[:40]
        calls = str(record.get("call_count", 0))
        numbers = str(record.get("unique_numbers", 0))
        first = record.get("first_seen", "")[:30]
        last = record.get("last_seen", "")[:30]

        print(f"{org:<40} {calls:<8} {numbers:<10} {first:<30} {last:<30}")
