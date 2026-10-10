# call-draw

Analyze Android call logs to map spam call activity at the organization level.

## Overview

call-draw is a defensive tool for analyzing call logs on Android devices. It helps identify spam and unwanted call patterns by grouping calls by organization and displaying statistics about call frequency, unique numbers, and time ranges.

The tool is strictly offline: no calling, texting, TTS/STT, network lookups, or OSINT on individuals. All processing is local to your device.

## Project Layout

```
data/
  raw/              # Android ADB call log export (gitignored)
  orgs.csv          # Manual mapping of phone numbers to organizations
  processed/        # Output CSVs (gitignored)
  contacts.csv      # Optional contact exclusion list

call_draw/          # Main package code
  parser.py         # Android call log parser
  normalizer.py     # Phone number normalization and filtering
  dashboard.py      # Organization-level summary generation
  main.py           # Pipeline orchestration

tests/              # Pytest fixtures with synthetic test data
```

## Setup

### Requirements

- Python 3.8+
- pandas (optional, not currently required)
- pytest (for testing)

### Installation

```bash
pip install -r requirements.txt
```

### Prepare Input Data

1. Export your Android call log via adb:
   ```bash
   adb shell content query --uri content://call_log/calls > data/raw/calls_raw.txt
   ```

2. Create `data/orgs.csv` to map known spam or business numbers:
   ```csv
   number,organization
   +18005551234,Spam Co
   +18005555678,Marketing Inc
   ```

3. (Optional) Create `data/contacts.csv` to exclude known contacts from analysis:
   ```csv
   number
   +12065551234
   +15555554321
   ```

## Usage

Run the full pipeline:

```bash
python3 -m call_draw.main
```

This will:
1. Parse the raw call log from `data/raw/calls_raw.txt`
2. Normalize phone numbers and filter out known contacts
3. Write processed calls to `data/processed/calls.csv`
4. Generate an organization-level summary
5. Write summary to `data/processed/summary.csv`
6. Print the top 25 organizations to the terminal

## Output

### calls.csv

Processed call records with columns:
- `timestamp`: ISO 8601 timestamp (UTC)
- `number`: Normalized phone number (leading + preserved)
- `direction`: incoming, outgoing, or missed
- `duration_sec`: Duration in seconds
- `caller_id_name`: Caller ID name from contact list (if available)

### summary.csv

Organization-level statistics with columns:
- `organization`: Organization name or caller ID (grouped by number prefix if unknown)
- `call_count`: Total number of calls from this organization
- `unique_numbers`: Number of unique phone numbers associated with the organization
- `first_seen`: Timestamp of the earliest call from this organization
- `last_seen`: Timestamp of the most recent call from this organization

## Testing

Run tests:

```bash
python3 -m pytest tests/ -v
```

Tests use only synthetic fixtures (555-range numbers, fake timestamps).

## Design Notes

### Call Type Mapping

Android call_log stores call types as:
- `1`: Incoming
- `2`: Outgoing
- `3`: Missed

### Number Normalization

Phone numbers are normalized by:
1. Stripping all non-digits (except leading +)
2. Preserving leading + if present

Examples:
- `+1 (555) 000-1111` → `+15550001111`
- `1-555-000-1111` → `15550001111`

### Organization Grouping

Calls are grouped by:
1. Organization (if found in `orgs.csv`)
2. Caller ID name (if available)
3. Number prefix (country + area code) as fallback

## Privacy

All processing is local. No data is sent to external services. Raw call logs and processed outputs should be kept private and never committed to version control (see .gitignore).
