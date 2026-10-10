*Upstream repo to push this first run to is Photon1c/call-draw

Project: call-draw
Analyze Android call logs to map spam call activity at the organization level. Defensive use only, for protecting the owner from unwanted calls. The tool is offline: no calling, texting, TTS/STT, network lookups of callers, or OSINT on individuals.

Repo layout

data/raw/ holds the raw adb export (calls_raw.txt). Gitignored, never committed.
data/orgs.csv is a manual mapping of number to organization label, owned by the user.
call_draw/ contains the package code.
tests/ uses synthetic fixtures only (555-range numbers, fake timestamps).

Task 1: Parser

Input: adb shell content query --uri content://call_log/calls output. Format is one row per line, Row: N key=value, key=value, ....
Inspect a synthetic sample before writing the parser. Don’t assume a fixed set of keys, since fields vary by Android version and OEM.
Handle missing values, commas inside values, and blank or error lines by skipping them and counting skips.
Convert date from epoch milliseconds to ISO 8601. Map type codes to incoming, outgoing, or missed, and document the mapping as an assumption to verify.
Output: data/processed/calls.csv with columns timestamp, number, direction, duration_sec, caller_id_name.

Task 2: Normalize and filter

Strip non-digits from numbers, keeping a leading + where present.
Exclude numbers present in an optional contacts file, so known contacts never reach the output.

Task 3: First dashboard (summary)

Join calls with data/orgs.csv by number. Unlabeled calls group under the caller ID name, then a number prefix.
Output a per-organization table: call count, unique numbers, first seen, last seen.
Write it as a CSV and print the top 25 to the terminal.

Constraints

Keep dependencies to pandas and pytest.
Write tests for the parser and the normalizer before the summary.
No output file should include anything beyond the columns listed above.

Done when

Tests pass on synthetic fixtures.
The parser runs on the real calls_raw.txt locally and produces the processed CSV and summary.
Nothing from data/raw/ or data/processed/ shows up in git status.
