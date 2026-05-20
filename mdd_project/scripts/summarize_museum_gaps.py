"""Summarize museum prefix gaps for human review."""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path

REVIEW = Path(__file__).resolve().parents[1] / "data" / "review"
METADATA = Path(__file__).resolve().parents[2] / "TypeSpecimenMetadata_v2.4.csv"

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
    "BUFFON'S",
    "LINNMUS",
}

ZERO_MATCH_ALIAS_OVERRIDES = {
    "E. O. Wilson Biodiversity Laboratory Collection": ["JAG"],
    "IADIZA": ["CMI"],
    "MCNM": ["MSNM"],
    "PNM": ["PBS"],
    "SGMT": ["GNMT"],
    "ZIUZ": ["UZDZ"],
    "ZMZ": ["ZMUZ"],
}

STANDALONE_ZERO_MATCH_POLICY = {
    "ACUNHC": (
        "retain",
        "Valid institution metadata for Abilene Christian University; retained for external alignment "
        "even though no MDD v2.4 voucher currently uses ACUNHC.",
    ),
    "CUMV": (
        "retain",
        "Cornell University Museum of Vertebrates is a standard vertebrate collection code; retained "
        "for future voucher matches and cross-database use.",
    ),
    "DZSJRP": (
        "retain",
        "Universidade Estadual Paulista campus/repository prefix; retained for future Brazilian type "
        "vouchers that may enter MDD.",
    ),
    "GEC": (
        "retain",
        "Historical Cuban scientific group code already present in metadata; retained pending future "
        "voucher matches rather than removed speculatively.",
    ),
    "MNHNC": (
        "retain",
        "National Museum of Natural History of Cuba; retained separately from MNHN Paris and other "
        "MNHN* variants for geographic clarity.",
    ),
    "NMSL": (
        "retain",
        "National Museum of Sri Lanka code; retained for future South Asian type vouchers.",
    ),
    "SNMB": (
        "retain",
        "Staatliches Naturhistorisches Museum Braunschweig; retained as a valid European museum code.",
    ),
}


def main() -> None:
    missing = list(csv.DictReader((REVIEW / "museum_voucher_prefixes_missing_from_metadata.csv").open(encoding="utf-8")))
    zero = list(csv.DictReader((REVIEW / "museum_metadata_zero_matches.csv").open(encoding="utf-8")))
    matched = list(csv.DictReader((REVIEW / "museum_coverage_matched.csv").open(encoding="utf-8")))
    metadata_rows = list(csv.DictReader(METADATA.open(encoding="utf-8-sig")))
    metadata_by_abbr = {row["ABBREVIATION"]: row for row in metadata_rows}
    matched_abbreviations = {row["matched_abbreviation"] for row in matched}
    worklist_path = REVIEW / "museum_completely_excluded_worklist.csv"
    worklist_by_prefix = defaultdict(set)
    if worklist_path.exists():
        for row in csv.DictReader(worklist_path.open(encoding="utf-8")):
            worklist_by_prefix[row["extracted_voucher_prefix"]].add(row["review_category"])

    alias_gaps = []
    orphan_prefixes = []
    for row in missing:
        prefix = row["voucher_prefix"]
        count = int(row["species_count"])
        if prefix in SKIP_PREFIXES or count < 2:
            continue
        categories = worklist_by_prefix.get(prefix, set())
        if categories and not categories.intersection(
            {"possible_collection_prefix", "needs_primary_literature", "repository_prefix_number_unknown"}
        ):
            continue
        related = row["related_metadata_abbreviations"].strip()
        if related:
            alias_gaps.append({**row, "species_count": count})
        elif len(prefix) <= 12 and prefix.isascii() and any(c.isalpha() for c in prefix):
            orphan_prefixes.append({**row, "species_count": count})

    alias_gaps.sort(key=lambda r: -r["species_count"])
    orphan_prefixes.sort(key=lambda r: -r["species_count"])

    matched_by_name = defaultdict(list)
    for row in matched:
        matched_by_name[row["matched_name"]].append(row["matched_abbreviation"])

    def mentions_abbreviation(text: str, abbreviation: str) -> bool:
        return bool(re.search(rf"(?<![A-Z0-9-]){re.escape(abbreviation)}(?![A-Z0-9-])", text.upper()))

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

    zero_review_path = REVIEW / "museum_zero_match_metadata_review.csv"
    zero_review_rows = []
    for row in zero:
        matched_aliases = set(matched_by_name.get(row["full_name"], []))
        metadata_row = metadata_by_abbr.get(row["abbreviation"], {})
        zero_alias_text = " ".join(
            [
                row["abbreviation"],
                metadata_row.get("Synonyms/Notes", ""),
            ]
        )
        for abbr in matched_abbreviations:
            if mentions_abbreviation(zero_alias_text, abbr):
                matched_aliases.add(abbr)
        for abbr in ZERO_MATCH_ALIAS_OVERRIDES.get(row["abbreviation"], []):
            if abbr in matched_abbreviations:
                matched_aliases.add(abbr)
        matched_aliases = sorted(matched_aliases)
        if matched_aliases:
            category = "expected_alias_no_direct_voucher"
            notes = "Same institution has matched voucher prefixes; this abbreviation is retained as an alias/canonical row."
        else:
            category = "standalone_zero_match"
            notes = "No vouchers currently match this abbreviation or same-name/same-city metadata row."
        zero_review_rows.append(
            {
                "abbreviation": row["abbreviation"],
                "full_name": row["full_name"],
                "city_and_country": row["city_and_country"],
                "review_category": category,
                "matched_aliases": "; ".join(matched_aliases),
                "notes": notes,
            }
        )
    zero_review_rows.sort(key=lambda r: (r["review_category"], r["abbreviation"]))
    with zero_review_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "abbreviation",
                "full_name",
                "city_and_country",
                "review_category",
                "matched_aliases",
                "notes",
            ],
        )
        writer.writeheader()
        writer.writerows(zero_review_rows)

    unresolved_path = REVIEW / "museum_research_unresolved.csv"
    unresolved_rows = []
    if unresolved_path.exists():
        unresolved_rows = list(csv.DictReader(unresolved_path.open(encoding="utf-8")))

    action_path = REVIEW / "museum_remaining_action_items.csv"
    action_rows = []
    for row in unresolved_rows:
        action_rows.append(
            {
                "priority": "1",
                "source": "unresolved_prefix",
                "item": row["extracted_voucher_prefix"],
                "species_count": row["prefix_species_count"],
                "example_species": row["sci_name"],
                "type_voucher": row["type_voucher"],
                "current_status": row["review_category"],
                "recommended_action": row["likely_action"],
            }
        )
    for row in zero_review_rows:
        if row["review_category"] != "standalone_zero_match":
            continue
        policy_decision, policy_rationale = STANDALONE_ZERO_MATCH_POLICY.get(
            row["abbreviation"],
            (
                "review",
                "No explicit retention policy recorded; decide whether metadata should contain only "
                "MDD-matched institutions.",
            ),
        )
        action_rows.append(
            {
                "priority": "2",
                "source": "standalone_zero_match_metadata",
                "item": row["abbreviation"],
                "species_count": "0",
                "example_species": "",
                "type_voucher": "",
                "current_status": row["review_category"],
                "recommended_action": (
                    f"{policy_decision}: {policy_rationale}"
                    if policy_decision == "retain"
                    else policy_rationale
                ),
            }
        )
    action_rows.sort(key=lambda r: (r["priority"], r["source"], r["item"]))
    with action_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "priority",
                "source",
                "item",
                "species_count",
                "example_species",
                "type_voucher",
                "current_status",
                "recommended_action",
            ],
        )
        writer.writeheader()
        writer.writerows(action_rows)

    policy_path = REVIEW / "museum_standalone_zero_match_policy.csv"
    policy_rows = []
    for row in zero_review_rows:
        if row["review_category"] != "standalone_zero_match":
            continue
        policy_decision, policy_rationale = STANDALONE_ZERO_MATCH_POLICY.get(
            row["abbreviation"],
            ("review", "No explicit retention policy recorded."),
        )
        policy_rows.append(
            {
                "abbreviation": row["abbreviation"],
                "full_name": row["full_name"],
                "city_and_country": row["city_and_country"],
                "policy_decision": policy_decision,
                "policy_rationale": policy_rationale,
            }
        )
    with policy_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "abbreviation",
                "full_name",
                "city_and_country",
                "policy_decision",
                "policy_rationale",
            ],
        )
        writer.writeheader()
        writer.writerows(policy_rows)

    # Zero-match metadata entries that look like they should have alias rows
    zero_by_country = defaultdict(list)
    for row in zero:
        zero_by_country[row.get("city_and_country", "")].append(row)

    print(f"Matched museums in app: {len(matched)}")
    print(f"Metadata institutions with 0 matches: {len(zero)}")
    print(
        "Zero-match metadata review: "
        f"{sum(1 for row in zero_review_rows if row['review_category'] == 'expected_alias_no_direct_voucher')} expected aliases, "
        f"{sum(1 for row in zero_review_rows if row['review_category'] == 'standalone_zero_match')} standalone"
    )
    print(f"Alias-style prefix gaps (count>=2): {len(alias_gaps)}")
    print(f"Orphan voucher prefixes (count>=2): {len(orphan_prefixes)}")
    print("\nTop alias-style gaps:")
    for row in alias_gaps[:15]:
        print(
            f"  {row['voucher_prefix']:12} {row['species_count']:3} sp  -> related: {row['related_metadata_abbreviations']}"
        )
    print(f"\nWrote {out}")
    print(f"Wrote {zero_review_path}")
    print(f"Wrote {action_path}")
    print(f"Wrote {policy_path}")


if __name__ == "__main__":
    main()
