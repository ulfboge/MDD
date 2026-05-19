"""Summarize museum prefix gaps for human review."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

REVIEW = Path(__file__).resolve().parents[1] / "data" / "review"

SKIP_PREFIXES = {
    "UNTRACED",
    "LOST",
    "PHOTOGRAPHED",
    "SPECIMEN",
    "NOT",
    "UNKNOWN",
    "NONE",
    "NA",
    "NO",
    "TYPE",
    "HOLOTYPE",
    "PARATYPE",
    "SYNTYPE",
    "LECTOTYPE",
    "NEOTYPE",
}


def main() -> None:
    missing = list(csv.DictReader((REVIEW / "museum_voucher_prefixes_missing_from_metadata.csv").open(encoding="utf-8")))
    zero = list(csv.DictReader((REVIEW / "museum_metadata_zero_matches.csv").open(encoding="utf-8")))
    matched = list(csv.DictReader((REVIEW / "museum_coverage_matched.csv").open(encoding="utf-8")))

    alias_gaps = []
    orphan_prefixes = []
    for row in missing:
        prefix = row["voucher_prefix"]
        count = int(row["species_count"])
        if prefix in SKIP_PREFIXES or count < 2:
            continue
        related = row["related_metadata_abbreviations"].strip()
        if related:
            alias_gaps.append({**row, "species_count": count})
        elif len(prefix) <= 12 and prefix.isascii() and any(c.isalpha() for c in prefix):
            orphan_prefixes.append({**row, "species_count": count})

    alias_gaps.sort(key=lambda r: -r["species_count"])
    orphan_prefixes.sort(key=lambda r: -r["species_count"])

    out = REVIEW / "museum_prefix_gap_summary.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "issue_type",
                "voucher_prefix",
                "species_count",
                "related_metadata_abbreviations",
                "example_species",
                "notes",
            ],
        )
        writer.writeheader()
        for row in alias_gaps:
            writer.writerow(
                {
                    "issue_type": "alias_prefix_missing",
                    "voucher_prefix": row["voucher_prefix"],
                    "species_count": row["species_count"],
                    "related_metadata_abbreviations": row["related_metadata_abbreviations"],
                    "example_species": row["example_species"],
                    "notes": "Voucher prefix absent from metadata; shorter/longer related code exists (NRM-style mismatch).",
                }
            )
        for row in orphan_prefixes[:80]:
            writer.writerow(
                {
                    "issue_type": "prefix_not_in_metadata",
                    "voucher_prefix": row["voucher_prefix"],
                    "species_count": row["species_count"],
                    "related_metadata_abbreviations": "",
                    "example_species": row["example_species"],
                    "notes": "Voucher prefix not in metadata; no related abbreviation detected.",
                }
            )

    # Zero-match metadata entries that look like they should have alias rows
    zero_by_country = defaultdict(list)
    for row in zero:
        zero_by_country[row.get("city_and_country", "")].append(row)

    print(f"Matched museums in app: {len(matched)}")
    print(f"Metadata institutions with 0 matches: {len(zero)}")
    print(f"Alias-style prefix gaps (count>=2): {len(alias_gaps)}")
    print(f"Orphan voucher prefixes (count>=2): {len(orphan_prefixes)}")
    print("\nTop alias-style gaps:")
    for row in alias_gaps[:15]:
        print(
            f"  {row['voucher_prefix']:12} {row['species_count']:3} sp  -> related: {row['related_metadata_abbreviations']}"
        )
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
