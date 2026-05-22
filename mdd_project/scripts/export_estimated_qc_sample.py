#!/usr/bin/env python3
"""
Export a review sample of proposed estimated type localities for manual QC.

Example:
  python mdd_project/scripts/export_estimated_qc_sample.py --family Galagidae --limit 30
  python mdd_project/scripts/export_estimated_qc_sample.py --confidence high,medium --limit 50
  python mdd_project/scripts/export_estimated_qc_sample.py --museum NHRM --limit 20
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "mdd_project" / "data" / "review" / "estimated_type_localities.csv"
DEFAULT_OUTPUT = ROOT / "mdd_project" / "data" / "review" / "estimated_qc_sample.csv"

QC_FIELDS = [
    "species_id",
    "sci_name",
    "sci_name_space",
    "family",
    "order",
    "type_locality",
    "type_voucher",
    "museum_abbreviation",
    "geocode_query",
    "type_lat_suggested",
    "type_lon_suggested",
    "coordinate_uncertainty_m",
    "geocode_method",
    "geocode_confidence",
    "geocode_notes",
    "review_status",
    "qc_decision",
    "qc_notes",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--family", help="Filter by MDD family (e.g. Galagidae)")
    parser.add_argument("--order", help="Filter by MDD order (e.g. Primates)")
    parser.add_argument("--museum", help="Filter by museum abbreviation prefix match")
    parser.add_argument(
        "--confidence",
        help="Comma-separated confidence levels to include (high, medium, low)",
    )
    parser.add_argument("--limit", type=int, default=50, help="Max rows to export (default: 50)")
    parser.add_argument(
        "--exclude-reviewed",
        action="store_true",
        help="Skip rows that already have qc_reviewed set in the main CSV.",
    )
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(f"Input not found: {args.input}")

    conf_filter = None
    if args.confidence:
        conf_filter = {c.strip().lower() for c in args.confidence.split(",") if c.strip()}

    rows: list[dict[str, str]] = []
    with args.input.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("review_status") != "proposed":
                continue
            if not row.get("type_lat_suggested") or not row.get("type_lon_suggested"):
                continue
            if args.family and row.get("family", "").lower() != args.family.lower():
                continue
            if args.order and row.get("order", "").lower() != args.order.lower():
                continue
            if args.museum and not (row.get("museum_abbreviation") or "").upper().startswith(
                args.museum.upper()
            ):
                continue
            if conf_filter and row.get("geocode_confidence", "").lower() not in conf_filter:
                continue
            if args.exclude_reviewed and (row.get("qc_reviewed") or "").strip():
                continue
            rows.append(row)

    # Prefer higher confidence first, then alphabetical
    rank = {"high": 0, "medium": 1, "low": 2}
    rows.sort(
        key=lambda r: (
            rank.get(r.get("geocode_confidence", "").lower(), 9),
            r.get("family", ""),
            r.get("sci_name", ""),
        )
    )
    sample = rows[: max(args.limit, 0)]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=QC_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in sample:
            out = {k: row.get(k, "") for k in QC_FIELDS if k not in ("qc_decision", "qc_notes")}
            out["qc_decision"] = ""
            out["qc_notes"] = ""
            writer.writerows([out])

    print(f"Exported {len(sample)} / {len(rows)} matching proposed rows -> {args.output}")
    if sample:
        from collections import Counter

        print("Confidence:", Counter(r.get("geocode_confidence", "") for r in sample))


if __name__ == "__main__":
    main()
