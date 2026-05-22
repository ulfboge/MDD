#!/usr/bin/env python3
"""Apply qc curated geocode overrides to estimated_type_localities.csv."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = ROOT / "mdd_project" / "data" / "review" / "estimated_type_localities.csv"


def main() -> None:
    from geocode_curated_overrides import get_curated_geocodes
    from geocode_type_localities import result_to_output

    curated = get_curated_geocodes("qc")
    rows: list[dict[str, str]] = []
    updated = 0
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        for row in reader:
            sci = row.get("sci_name", "")
            if sci in curated:
                out = result_to_output(curated[sci])
                row.update(out)
                row["qc_reviewed"] = "needs_curated_override"
                updated += 1
            rows.append(row)

    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Applied {updated} qc curated overrides -> {CSV_PATH}")


if __name__ == "__main__":
    main()
