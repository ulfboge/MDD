#!/usr/bin/env python3
"""
Pre-fill qc_decision / qc_notes on an estimated QC sample CSV.

Uses country-hint validation (same rules as geocode_type_localities.py).

Example:
  python mdd_project/scripts/suggest_estimated_qc.py
  python mdd_project/scripts/suggest_estimated_qc.py --overwrite
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

from review_paths import QC_SAMPLE_CSV

DEFAULT_INPUT = QC_SAMPLE_CSV


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing qc_decision values (default: only fill blanks).",
    )
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(f"Input not found: {args.input}")

    from geocode_country_validate import suggest_qc_decision

    rows: list[dict[str, str]] = []
    with args.input.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        for row in reader:
            if not args.overwrite and row.get("qc_decision", "").strip():
                rows.append(row)
                continue
            decision, note, uncertain = suggest_qc_decision(row)
            if uncertain and decision == "accept":
                row["qc_decision"] = "review"
            else:
                row["qc_decision"] = decision
            prefix = "[auto] "
            existing = row.get("qc_notes", "").strip()
            row["qc_notes"] = f"{prefix}{note}" + (f"; {existing}" if existing else "")
            rows.append(row)

    with args.input.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    counts = Counter(r.get("qc_decision", "") for r in rows)
    print(f"Updated {args.input}")
    print("Decisions:", dict(counts))


if __name__ == "__main__":
    main()
