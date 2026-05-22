#!/usr/bin/env python3
"""
Apply manual QC decisions from a QC sample CSV to estimated_type_localities.csv.

Reads qc_reviewed (preferred) or qc_decision from the QC file.
Accepted rows stay proposed; rejected rows become no_estimate with coords cleared;
needs_curated_override rows stay proposed with QC notes appended.

Example:
  python mdd_project/scripts/apply_estimated_qc_decisions.py --dry-run
  python mdd_project/scripts/apply_estimated_qc_decisions.py \\
    --qc mdd_project/data/review/estimated_qc_sample_reviewed.csv
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_QC = ROOT / "mdd_project" / "data" / "review" / "estimated_qc_sample_reviewed.csv"
FALLBACK_QC = ROOT / "mdd_project" / "data" / "review" / "estimated_qc_sample.csv"
DEFAULT_MAIN = ROOT / "mdd_project" / "data" / "review" / "estimated_type_localities.csv"

QC_COLUMNS = ("qc_reviewed", "qc_review_notes")


def resolve_decision(row: dict[str, str]) -> tuple[str, str]:
    """Return (decision, note) from a QC row."""
    decision = (row.get("qc_reviewed") or row.get("qc_decision") or "").strip().lower()
    note = (row.get("qc_review_notes") or row.get("qc_notes") or "").strip()
    return decision, note


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qc", type=Path, default=None, help="QC CSV (default: reviewed sample if present)")
    parser.add_argument("--main", type=Path, default=DEFAULT_MAIN)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    qc_path = args.qc
    if qc_path is None:
        qc_path = DEFAULT_QC if DEFAULT_QC.exists() else FALLBACK_QC

    if not qc_path.exists():
        raise SystemExit(f"QC file not found: {qc_path}")
    if not args.main.exists():
        raise SystemExit(f"Main CSV not found: {args.main}")

    decisions: dict[int, dict[str, str]] = {}
    pending = 0
    with qc_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            decision, _ = resolve_decision(row)
            if not decision:
                pending += 1
                continue
            decisions[int(row["species_id"])] = row

    if pending:
        print(f"Warning: {pending} QC rows have no decision — skipped.")

    main_rows: list[dict[str, str]] = []
    stats = {
        "accept": 0,
        "reject": 0,
        "needs_curated_override": 0,
        "review": 0,
        "other": 0,
    }
    with args.main.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        for col in QC_COLUMNS:
            if col not in fieldnames:
                fieldnames.append(col)

        for row in reader:
            sid = int(row["species_id"])
            qc = decisions.get(sid)
            if not qc:
                main_rows.append(row)
                continue

            decision, note = resolve_decision(qc)
            row["qc_reviewed"] = decision
            if note:
                row["qc_review_notes"] = note

            if decision in {"accept", "accepted", "ok"}:
                row["review_status"] = "proposed"
                if not row.get("type_lat_suggested", "").strip() and qc.get("type_lat_suggested", "").strip():
                    row["type_lat_suggested"] = qc["type_lat_suggested"]
                    row["type_lon_suggested"] = qc.get("type_lon_suggested", "")
                    row["coordinate_uncertainty_m"] = qc.get("coordinate_uncertainty_m", "")
                    row["geocode_method"] = qc.get("geocode_method", row.get("geocode_method", ""))
                    row["geocode_confidence"] = qc.get("geocode_confidence", row.get("geocode_confidence", ""))
                    orig_notes = qc.get("geocode_notes", "").strip()
                    row["geocode_notes"] = (
                        f"{orig_notes}; QC accept: {note}".strip("; ")
                        if orig_notes and note
                        else orig_notes or f"QC accept: {note}"
                    )
                elif note:
                    row["geocode_notes"] = f"{row.get('geocode_notes', '')}; QC accept: {note}".strip("; ")
                stats["accept"] += 1
            elif decision in {"reject", "rejected", "no"}:
                row["review_status"] = "no_estimate"
                row["type_lat_suggested"] = ""
                row["type_lon_suggested"] = ""
                row["coordinate_uncertainty_m"] = ""
                row["geocode_confidence"] = "none"
                row["geocode_method"] = row.get("geocode_method", "") or "nominatim"
                row["geocode_notes"] = f"QC rejected: {note}".strip()
                stats["reject"] += 1
            elif decision in {"needs_curated_override", "override"}:
                row["review_status"] = "proposed"
                if note:
                    row["geocode_notes"] = (
                        f"{row.get('geocode_notes', '')}; QC needs curated override: {note}"
                    ).strip("; ")
                stats["needs_curated_override"] += 1
            elif decision == "review":
                stats["review"] += 1
            else:
                stats["other"] += 1
            main_rows.append(row)

    print(f"QC source: {qc_path}")
    print("Would apply:" if args.dry_run else "Applied:")
    for key, val in stats.items():
        if val:
            print(f"  {key}: {val}")

    if not args.dry_run:
        with args.main.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(main_rows)
        print(f"Wrote {args.main}")


if __name__ == "__main__":
    main()
