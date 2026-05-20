import csv
import re
from collections import Counter
from pathlib import Path

import duckdb

DB = Path("mdd_project/data/processed/mdd.duckdb")
REVIEW = Path("mdd_project/data/review")

NON_INSTITUTION_PREFIXES = {
    "UNTRACED",
    "LOST",
    "NONEXISTENT",
}

DESCRIPTION_PREFIXES = {
    "BOHMANN",
    "BUFFON'S",
    "FIGURED",
    "MALE",
    "MARCGRAVE'S",
    "PENNANT'S",
    "PHOTOGRAPHED",
    "SEBA",
    "SPECIMEN",
}

LOCALITY_OR_PERSON_PREFIXES = {
    "ABE",
    "CBK",
    "DULIC",
    "LAAYOUNE",
    "LARGER",
    "NEUHAUSER",
    "RUSCONI",
    "STILLWATER",
    "TASHKENT",
    "YEREVAN",
}

NEEDS_PRIMARY_LITERATURE_PREFIXES = {
    "ASRU": (
        "MDD confirms Scarturus heptneri type material as ASRU 424; original source is Pavlenko & "
        "Denisenko (1976), Allactaga elater heptneri, Zoologicheskii Zhurnal 55(7):1073-1077. "
        "Open sources support an Uzbek Academy of Sciences zoological/mammal collection, but a source "
        "expanding ASRU and tying ASRU 424 to that repository was not found."
    ),
    "LSNSAU": (
        "Known from Aimi & Bakar (1992), Primates 33:191-206, as Presbytis melalophos bicolor "
        "holotype LSNSAU SD 16. DOI/article page was found, but accessible sources did not expand "
        "LSNSAU; likely requires full article/PDF or contact with Andalas University/Kyoto PRI."
    ),
}


def candidate_prefix_to_research(prefix: str) -> str:
    """Suggest the shortest plausible code to look up in collection metadata."""
    prefix = prefix.strip().upper().rstrip("./-")
    for separator in ("/", "."):
        if separator in prefix:
            return prefix.split(separator, 1)[0]
    m = re.match(r"^([A-ZÄÖÜÅÆØĐ]+)[0-9-]", prefix)
    if m:
        return m.group(1)
    return prefix


def extract_voucher_token_prefix(voucher: str) -> str:
    """First catalog-like token, same heuristic as prefix counts (audit summary)."""
    v = voucher.strip()
    if not v:
        return ""
    m = re.match(r"^([A-Za-z][A-Za-z0-9./\-]{0,15}?)(?:\s|\(|$)", v)
    part = m.group(1) if m else v.split()[0]
    return part.upper().rstrip("./-")


def normalized_asciiish(value: str) -> str:
    """Normalize a few accented names used only for rule-of-thumb grouping."""
    return (
        value.upper()
        .replace("Â", "A")
        .replace("Ä", "A")
        .replace("Č", "C")
        .replace("Ć", "C")
        .replace("Ë", "E")
        .replace("É", "E")
        .replace("Ü", "U")
        .replace("Đ", "D")
    )


def classify_excluded_voucher(prefix: str, voucher: str, uri: str | None) -> dict[str, str]:
    """Classify excluded vouchers into a practical manual-review queue."""
    prefix_norm = normalized_asciiish(prefix)
    voucher_lower = voucher.lower()
    has_uri = bool(uri and uri.strip())

    if (
        "number not known" in voucher_lower
        and prefix_norm not in NON_INSTITUTION_PREFIXES
        and not voucher_lower.startswith(("lost", "untraced", "nonexistent"))
    ):
        return {
            "priority": "2_medium",
            "review_category": "repository_prefix_number_unknown",
            "likely_action": "Prefix may identify a repository but catalog number is unknown; research prefix before adding metadata.",
        }

    if "released" in voucher_lower:
        return {
            "priority": "3_low",
            "review_category": "released_or_unpreserved_specimen",
            "likely_action": "Specimen was released or not preserved; do not add museum metadata unless a repository is named.",
        }

    if prefix_norm in NON_INSTITUTION_PREFIXES or any(
        marker in voucher_lower for marker in ("untraced", "lost")
    ):
        return {
            "priority": "4_no_action",
            "review_category": "lost_or_untraced",
            "likely_action": "Do not add museum metadata unless primary literature identifies a repository.",
        }

    if prefix_norm in DESCRIPTION_PREFIXES or any(
        marker in voucher_lower
        for marker in ("figured", "photographed", "collected by", "described by")
    ):
        return {
            "priority": "3_low",
            "review_category": "non_institution_description",
            "likely_action": "Treat as historical figure/specimen wording; only research if a cited work names a repository.",
        }

    if prefix_norm in LOCALITY_OR_PERSON_PREFIXES:
        return {
            "priority": "3_low",
            "review_category": "locality_or_person_name",
            "likely_action": "Likely locality/person text rather than a museum code; verify manually before adding metadata.",
        }

    if prefix_norm in NEEDS_PRIMARY_LITERATURE_PREFIXES:
        return {
            "priority": "2_medium",
            "review_category": "needs_primary_literature",
            "likely_action": NEEDS_PRIMARY_LITERATURE_PREFIXES[prefix_norm],
        }

    if re.match(r"^(?:[0-9]|XZ[0-9]|TAFO[0-9]|K-EE-|VG-Q[0-9])", prefix_norm):
        return {
            "priority": "3_low",
            "review_category": "field_or_sequence_number",
            "likely_action": "Likely field/sample/site number; use original description to find the repository, not the token itself.",
        }

    # Codes with digits, slashes, or hyphens are often catalog identifiers; short all-caps
    # letter strings are also plausible collection prefixes.
    catalogish = bool(re.search(r"[A-Z]", prefix_norm)) and (
        bool(re.search(r"[0-9./-]", prefix_norm))
        or (prefix_norm.isalpha() and 2 <= len(prefix_norm) <= 10)
    )
    if catalogish:
        return {
            "priority": "1_high" if has_uri else "2_medium",
            "review_category": "possible_collection_prefix",
            "likely_action": "Research prefix and source; add to TypeSpecimenMetadata_v2.4.csv only if repository is confirmed.",
        }

    return {
        "priority": "3_low",
        "review_category": "needs_manual_review",
        "likely_action": "Unclear token; inspect voucher text and original description.",
    }


def qc_flags(row: dict[str, object]) -> list[dict[str, object]]:
    """Flag low-confidence excluded vouchers for a final human sanity check."""
    flags: list[dict[str, object]] = []
    category = str(row["review_category"])
    voucher = str(row["type_voucher"])
    voucher_lower = voucher.lower()

    if category == "needs_primary_literature":
        flags.append(
            {
                **row,
                "qc_flag": "unresolved_prefix",
                "qc_reason": "Institution-like prefix remains unresolved and requires primary literature or repository confirmation.",
            }
        )

    if str(row["type_voucher_uris"]).strip():
        flags.append(
            {
                **row,
                "qc_flag": "voucher_uri_present",
                "qc_reason": "Voucher text is excluded, but URI may identify a repository or catalog object.",
            }
        )

    if category == "non_institution_description" and "collection" in voucher_lower:
        flags.append(
            {
                **row,
                "qc_flag": "named_collection_label",
                "qc_reason": "Voucher is descriptive, but mentions a named collection; original literature may identify a repository.",
            }
        )

    if category == "locality_or_person_name" and re.search(r"\d", voucher):
        flags.append(
            {
                **row,
                "qc_flag": "name_or_locality_with_number",
                "qc_reason": "Looks like a person/locality label with a number; verify it is not a repository code before closing.",
            }
        )

    return flags


def main() -> None:
    c = duckdb.connect(str(DB), read_only=True)
    inst = {
        r[0].upper() for r in c.execute("SELECT abbreviation FROM type_specimen_institutions").fetchall()
    }

    rows = c.execute(
        """
        SELECT
            species_id,
            sci_name,
            main_common_name,
            "order",
            family,
            genus,
            specific_epithet,
            type_kind,
            type_voucher,
            type_voucher_uris,
            type_locality,
            extinct,
            domestic
        FROM species
        WHERE type_voucher IS NOT NULL AND TRIM(type_voucher) <> ''
        """
    ).fetchall()

    completely_excluded: list[tuple] = []
    for row in rows:
        voucher = row[8]
        assert voucher is not None
        v = voucher.strip().upper()
        if any(v.startswith(a) for a in inst):
            continue
        completely_excluded.append(row)

    prefix_counts: Counter[str] = Counter()
    for row in completely_excluded:
        voucher = row[8]
        assert voucher is not None
        prefix = extract_voucher_token_prefix(voucher)
        prefix_counts[prefix] += 1

    simple_path = REVIEW / "museum_completely_excluded_from_app.csv"
    detail_path = REVIEW / "museum_completely_excluded_detail.csv"
    worklist_path = REVIEW / "museum_completely_excluded_worklist.csv"
    candidates_path = REVIEW / "museum_research_candidates.csv"
    unresolved_path = REVIEW / "museum_research_unresolved.csv"
    qc_path = REVIEW / "museum_unmatched_qc_flags.csv"

    REVIEW.mkdir(parents=True, exist_ok=True)

    with simple_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["sci_name", "type_voucher"])
        for row in completely_excluded:
            w.writerow([row[1], row[8]])

    detail_fields = [
        "species_id",
        "sci_name",
        "main_common_name",
        "order",
        "family",
        "genus",
        "specific_epithet",
        "type_kind",
        "type_voucher",
        "extracted_voucher_prefix",
        "candidate_prefix_to_research",
        "type_locality",
        "type_voucher_uris",
        "extinct",
        "domestic",
    ]
    with detail_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=detail_fields, extrasaction="ignore")
        w.writeheader()
        for row in completely_excluded:
            voucher = row[8]
            assert voucher is not None
            w.writerow(
                {
                    "species_id": row[0],
                    "sci_name": row[1],
                    "main_common_name": row[2] or "",
                    "order": row[3] or "",
                    "family": row[4] or "",
                    "genus": row[5] or "",
                    "specific_epithet": row[6] or "",
                    "type_kind": row[7] or "",
                    "type_voucher": voucher,
                    "extracted_voucher_prefix": extract_voucher_token_prefix(voucher),
                    "candidate_prefix_to_research": candidate_prefix_to_research(
                        extract_voucher_token_prefix(voucher)
                    ),
                    "type_locality": row[10] or "",
                    "type_voucher_uris": row[9] or "",
                    "extinct": row[11],
                    "domestic": row[12],
                }
            )

    worklist_fields = [
        "priority",
        "review_category",
        "likely_action",
        "prefix_species_count",
        "species_id",
        "sci_name",
        "main_common_name",
        "order",
        "family",
        "type_kind",
        "type_voucher",
        "extracted_voucher_prefix",
        "candidate_prefix_to_research",
        "type_locality",
        "type_voucher_uris",
        "extinct",
        "domestic",
    ]
    worklist_rows: list[dict[str, object]] = []
    for row in completely_excluded:
        voucher = row[8]
        assert voucher is not None
        prefix = extract_voucher_token_prefix(voucher)
        classification = classify_excluded_voucher(prefix, voucher, row[9])
        worklist_rows.append(
            {
                **classification,
                "prefix_species_count": prefix_counts[prefix],
                "species_id": row[0],
                "sci_name": row[1],
                "main_common_name": row[2] or "",
                "order": row[3] or "",
                "family": row[4] or "",
                "type_kind": row[7] or "",
                "type_voucher": voucher,
                "extracted_voucher_prefix": prefix,
                "candidate_prefix_to_research": candidate_prefix_to_research(prefix),
                "type_locality": row[10] or "",
                "type_voucher_uris": row[9] or "",
                "extinct": row[11],
                "domestic": row[12],
            }
        )
    worklist_rows.sort(
        key=lambda r: (
            str(r["priority"]),
            str(r["review_category"]),
            -int(r["prefix_species_count"]),
            str(r["extracted_voucher_prefix"]),
            str(r["sci_name"]),
        )
    )
    with worklist_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=worklist_fields)
        w.writeheader()
        w.writerows(worklist_rows)

    with candidates_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=worklist_fields)
        w.writeheader()
        w.writerows(
            row
            for row in worklist_rows
            if row["review_category"] == "possible_collection_prefix"
        )

    with unresolved_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=worklist_fields)
        w.writeheader()
        w.writerows(
            row
            for row in worklist_rows
            if row["review_category"] == "needs_primary_literature"
        )

    qc_fields = [*worklist_fields, "qc_flag", "qc_reason"]
    qc_rows = [flag for row in worklist_rows for flag in qc_flags(row)]
    with qc_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=qc_fields)
        w.writeheader()
        w.writerows(qc_rows)

    summary_path = REVIEW / "museum_completely_excluded_prefix_counts.csv"
    with summary_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["voucher_prefix", "species_count"])
        for prefix, count in prefix_counts.most_common():
            w.writerow([prefix, count])

    print(f"Species with vouchers matching no institution prefix: {len(completely_excluded)}")
    print(f"Wrote {simple_path}")
    print(f"Wrote {detail_path}")
    print(f"Wrote {worklist_path}")
    print(f"Wrote {candidates_path}")
    print(f"Wrote {unresolved_path}")
    print(f"Wrote {qc_path}")
    print(f"QC flags for manual sanity check: {len(qc_rows)}")
    print("Review categories:")
    for category, count in Counter(str(row["review_category"]) for row in worklist_rows).most_common():
        print(f"  {category:30} {count}")
    print(f"Distinct voucher prefixes (excluded): {len(prefix_counts)}")
    print("Top excluded prefixes:")
    for prefix, count in prefix_counts.most_common(20):
        print(f"  {prefix:20} {count}")


if __name__ == "__main__":
    main()
