#!/usr/bin/env python3
"""Print summary stats for estimated_type_localities.csv."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / "mdd_project" / "data" / "review" / "estimated_type_localities.csv"


def main() -> None:
    path = DEFAULT
    if not path.exists():
        print(f"No file at {path}")
        return
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    proposed = [r for r in rows if r.get("type_lat_suggested")]
    print(f"Rows: {len(rows)}")
    print(f"Proposed: {len(proposed)}")
    print("Review status:", Counter(r.get("review_status", "") for r in rows))
    if proposed:
        print("Phase:", Counter(r.get("geocode_phase", "") for r in proposed))
        print("Confidence:", Counter(r.get("geocode_confidence", "") for r in proposed))


if __name__ == "__main__":
    main()
