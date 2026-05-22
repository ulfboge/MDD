"""Audit museum abbreviation matching in MDD type vouchers."""

from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

import duckdb

DB = Path(__file__).resolve().parents[1] / "data" / "processed" / "mdd.duckdb"
META = Path(__file__).resolve().parents[2] / "TypeSpecimenMetadata_v2.4.csv"
OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "review" / "museum"

MUSEUM_MATCH = """
    s.type_voucher IS NOT NULL
    AND TRIM(s.type_voucher) <> ''
    AND UPPER(TRIM(s.type_voucher)) LIKE UPPER(tsi.abbreviation) || '%'
"""

SPECIES_WITH_MUSEUM_CTE = f"""
species_with_museum AS (
    SELECT
        s.sci_name,
        s.type_voucher,
        s.type_lat,
        s.type_lon,
        (
            SELECT tsi.abbreviation
            FROM type_specimen_institutions tsi
            WHERE {MUSEUM_MATCH}
            ORDER BY LENGTH(tsi.abbreviation) DESC
            LIMIT 1
        ) AS matched_abbreviation,
        (
            SELECT tsi.full_name
            FROM type_specimen_institutions tsi
            WHERE {MUSEUM_MATCH}
            ORDER BY LENGTH(tsi.abbreviation) DESC
            LIMIT 1
        ) AS matched_name
    FROM species s
    WHERE s.type_voucher IS NOT NULL AND TRIM(s.type_voucher) <> ''
)
"""


CATALOG_SEPARATORS = {":", ".", "-", "/", " ", "("}


def extract_voucher_prefix(voucher: str, inst_abbr: set[str] | None = None) -> str:
    """Best-effort catalog prefix from type_voucher text."""
    v = voucher.strip()
    if not v:
        return ""
    if inst_abbr:
        upper_v = v.upper()
        for abbr in sorted(inst_abbr, key=len, reverse=True):
            next_char = upper_v[len(abbr) : len(abbr) + 1]
            if upper_v == abbr or (
                upper_v.startswith(abbr)
                and (
                    next_char in CATALOG_SEPARATORS
                    or ("-" in abbr and next_char.isdigit())
                    or next_char.isdigit()
                )
            ):
                return abbr
    # e.g. "NHRM A63 3316", "USNM 123", "BMNH 1918.3.1.1"
    m = re.match(r"^([A-Za-z][A-Za-z0-9./\-]{0,15}?)(?:\s|\(|$)", v)
    if m:
        return m.group(1).upper().rstrip("./-")
    return v.split()[0].upper() if v.split() else v.upper()


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(DB), read_only=True)

    institutions = conn.execute(
        "SELECT abbreviation, full_name, city_and_country FROM type_specimen_institutions ORDER BY abbreviation"
    ).fetchdf()
    inst_abbr = {row["abbreviation"].upper() for row in institutions.to_dict("records")}

    matched_museums = conn.execute(
        f"""
        WITH {SPECIES_WITH_MUSEUM_CTE}
        SELECT matched_abbreviation, matched_name,
               COUNT(*) AS vouchers,
               COUNT(*) FILTER (WHERE type_lat IS NOT NULL AND type_lon IS NOT NULL) AS geocoded
        FROM species_with_museum
        WHERE matched_abbreviation IS NOT NULL
        GROUP BY matched_abbreviation, matched_name
        ORDER BY matched_name, matched_abbreviation
        """
    ).fetchdf()

    unmatched_rows = conn.execute(
        f"""
        WITH {SPECIES_WITH_MUSEUM_CTE}
        SELECT sci_name, type_voucher
        FROM species_with_museum
        WHERE matched_abbreviation IS NULL
        ORDER BY type_voucher, sci_name
        """
    ).fetchdf()

    voucher_rows = conn.execute(
        """
        SELECT sci_name, type_voucher, type_lat, type_lon
        FROM species
        WHERE type_voucher IS NOT NULL AND TRIM(type_voucher) <> ''
        ORDER BY type_voucher
        """
    ).fetchdf()

    # Prefixes used in vouchers vs metadata
    prefix_counts: Counter[str] = Counter()
    prefix_species: dict[str, list[str]] = defaultdict(list)
    prefix_mismatch: list[dict[str, str]] = []

    for row in voucher_rows.to_dict("records"):
        prefix = extract_voucher_prefix(row["type_voucher"], inst_abbr)
        if not prefix:
            continue
        prefix_counts[prefix] += 1
        prefix_species[prefix].append(row["sci_name"])

    for row in conn.execute(
        f"""
        WITH {SPECIES_WITH_MUSEUM_CTE}
        SELECT sci_name, type_voucher, matched_abbreviation
        FROM species_with_museum
        WHERE matched_abbreviation IS NOT NULL
        """
    ).fetchall():
        sci_name, voucher, matched_abbr_row = row
        prefix = extract_voucher_prefix(voucher, inst_abbr)
        if prefix and prefix != matched_abbr_row.upper() and prefix not in inst_abbr:
            prefix_mismatch.append(
                {
                    "sci_name": sci_name,
                    "type_voucher": voucher,
                    "voucher_prefix": prefix,
                    "matched_abbreviation": matched_abbr_row,
                    "issue": "prefix_missing_from_metadata",
                }
            )
        elif prefix and prefix != matched_abbr_row.upper() and prefix in inst_abbr:
            prefix_mismatch.append(
                {
                    "sci_name": sci_name,
                    "type_voucher": voucher,
                    "voucher_prefix": prefix,
                    "matched_abbreviation": matched_abbr_row,
                    "issue": "longer_shorter_abbreviation_conflict",
                }
            )

    # Prefixes in vouchers but not in institution metadata
    missing_prefixes = []
    for prefix, count in prefix_counts.most_common():
        if prefix not in inst_abbr:
            # check if any institution abbreviation is a strict prefix (would cause wrong match)
            matching_inst = [
                abbr
                for abbr in inst_abbr
                if prefix.startswith(abbr) or abbr.startswith(prefix)
            ]
            missing_prefixes.append(
                {
                    "voucher_prefix": prefix,
                    "species_count": count,
                    "in_metadata": "no",
                    "related_metadata_abbreviations": "; ".join(sorted(matching_inst)[:10]),
                    "example_species": "; ".join(prefix_species[prefix][:3]),
                }
            )

    # Institutions in metadata with zero matched vouchers
    matched_abbr = {str(a).upper() for a in matched_museums["matched_abbreviation"].tolist()}
    zero_match_inst = []
    for row in institutions.to_dict("records"):
        abbr = row["abbreviation"]
        if abbr.upper() not in matched_abbr:
            zero_match_inst.append(row)

    # Write reports
    matched_path = OUT_DIR / "museum_coverage_matched.csv"
    matched_museums.to_csv(matched_path, index=False)

    missing_path = OUT_DIR / "museum_voucher_prefixes_missing_from_metadata.csv"
    with missing_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "voucher_prefix",
                "species_count",
                "in_metadata",
                "related_metadata_abbreviations",
                "example_species",
            ],
        )
        writer.writeheader()
        writer.writerows(missing_prefixes)

    zero_path = OUT_DIR / "museum_metadata_zero_matches.csv"
    with zero_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["abbreviation", "full_name", "city_and_country"])
        writer.writeheader()
        writer.writerows(zero_match_inst)

    mismatch_path = OUT_DIR / "museum_prefix_mismatch_cases.csv"
    with mismatch_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "sci_name",
                "type_voucher",
                "voucher_prefix",
                "matched_abbreviation",
                "issue",
            ],
        )
        writer.writeheader()
        writer.writerows(prefix_mismatch)

    unmatched_path = OUT_DIR / "museum_vouchers_unmatched.csv"
    unmatched_rows.to_csv(unmatched_path, index=False)

    print(f"Matched museums in app: {len(matched_museums)}")
    print(f"Metadata institutions with zero matches: {len(zero_match_inst)}")
    print(f"Voucher prefixes missing from metadata: {len(missing_prefixes)}")
    print(f"Prefix mismatch / alias cases: {len(prefix_mismatch)}")
    print(f"Completely unmatched vouchers: {len(unmatched_rows)}")
    print(f"Reports written to {OUT_DIR}")


if __name__ == "__main__":
    main()
