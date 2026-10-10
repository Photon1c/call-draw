"""Main pipeline for call-draw analysis."""

from pathlib import Path
from call_draw.parser import parse_call_log, write_calls_csv
from call_draw.normalizer import normalize_calls
from call_draw.dashboard import (
    generate_summary,
    write_summary_csv,
    print_top_organizations,
)


def main(
    raw_calls_path: Path = Path("data/raw/calls_raw.txt"),
    processed_path: Path = Path("data/processed/calls.csv"),
    summary_path: Path = Path("data/processed/summary.csv"),
    orgs_path: Path = Path("data/orgs.csv"),
    contacts_path: Path = None,
) -> None:
    """
    Run the full call-draw pipeline.

    Args:
        raw_calls_path: Path to raw Android call log export
        processed_path: Path to write processed calls CSV
        summary_path: Path to write organization summary CSV
        orgs_path: Path to organization mapping CSV
        contacts_path: Optional path to contacts exclusion CSV
    """
    # Step 1: Parse raw calls
    print(f"Parsing {raw_calls_path}...")
    calls, skipped = parse_call_log(raw_calls_path)
    print(f"  Parsed {len(calls)} calls, skipped {skipped} lines")

    # Step 2: Normalize and filter
    print(f"Normalizing and filtering calls...")
    if contacts_path is None:
        # Try to find contacts.csv if not specified
        contacts_check = Path("data/contacts.csv")
        if contacts_check.exists():
            contacts_path = contacts_check

    normalized_calls = normalize_calls(calls, contacts_path)
    print(f"  After filtering: {len(normalized_calls)} calls remain")

    # Step 3: Write processed CSV
    print(f"Writing processed calls to {processed_path}...")
    write_calls_csv(normalized_calls, processed_path)

    # Step 4: Generate summary
    print(f"Generating organization summary...")
    summary = generate_summary(normalized_calls, orgs_path)

    # Step 5: Write summary CSV
    print(f"Writing summary to {summary_path}...")
    write_summary_csv(summary, summary_path)

    # Step 6: Print top 25 to terminal
    print_top_organizations(summary, top_n=25)


if __name__ == "__main__":
    main()
