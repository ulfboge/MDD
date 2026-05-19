#!/usr/bin/env python3
"""Build wave-4 museum prefix investigation backlog for manual review."""

from __future__ import annotations

import csv
import re
from pathlib import Path

import duckdb

DB = Path(__file__).resolve().parents[1] / "data" / "processed" / "mdd.duckdb"
REVIEW = Path(__file__).resolve().parents[1] / "data" / "review"
GAP = REVIEW / "museum_prefix_gap_summary.csv"
OUT_CSV = REVIEW / "museum_prefix_wave4_backlog.csv"
OUT_MD = REVIEW / "museum_prefix_wave4_backlog.md"

MUSEUM_MATCH = """
    s.type_voucher IS NOT NULL
    AND TRIM(s.type_voucher) <> ''
    AND UPPER(TRIM(s.type_voucher)) LIKE UPPER(tsi.abbreviation) || '%'
"""

SKIP = {"UNTRACED", "LOST", "PHOTOGRAPHED", "SPECIMEN", "BUFFON'S", "LINNMUS", "PENNANT'S"}

PRIORITY_NOTES = {
    "CMI": "BLOCKER: CM in metadata = Carnegie Museum (Pittsburgh). Vouchers look South American — likely Canadian Museum of Nature (CMN) or other. Do not alias to CM without verifying institution.",
    "CMN": "BLOCKER: same as CMI — CM is Carnegie in metadata, but CMN usually = Canadian Museum of Nature (Ottawa). May need new CMN row, not CM alias.",
    "MNK": "BLOCKER: MN now matches Museu Nacional (Rio). MNK vouchers currently mis-match to MN. Add dedicated MNK row after identifying holding museum.",
    "NU": "Likely alias for NUPECCE (Jaboticabal, Brazil). 2 Nannospalax species; vouchers NU 45 / NU 675.",
    "KURODA": "Likely alias for KU (University of Kansas). Japanese/E Asian types collected by Kuroda.",
    "UFMG": "Likely Universidade Federal de Minas Gerais — do not alias to UF (Florida). Needs new UFMG row.",
    "UFRGS": "Likely Universidade Federal do Rio Grande do Sul — do not alias to UF (Florida). Needs new UFRGS row.",
    "TTU-M": "Likely alias for TTU (Texas Tech) mammal sub-collection.",
    "ZSIS": "Likely alias for ZSI (Zoological Survey of India).",
    "MNHN-ZM-MO-1867-146": "Long Paris MNHN catalog string — add alias or normalize matching.",
    "AHNU": "Anhui Normal University (China). Related AHUB already in metadata with zero matches.",
    "SCNU": "South China Normal University (China).",
    "GNMT": "Possibly Georgian National Museum (Tbilisi)? Metadata has SGMT (State Georgian Museum).",
    "MMUS": "Metadata lists MMUS as synonym on MAMU (Macleay Museum, Sydney). Vouchers still unmatched — verify prefix.",
}


def voucher_prefix(voucher: str) -> str:
    v = voucher.strip()
    m = re.match(r"^([A-Za-z][A-Za-z0-9./:\-]{0,24}?)(?:\s|\(|$)", v)
    if m:
        return m.group(1).upper().rstrip("./-")
    return v.split()[0].upper() if v.split() else v.upper()


def wave_priority(issue_type: str, prefix: str, related: str, count: int) -> str:
    if prefix in {"CMI", "CMN", "MNK"}:
        return "P4-risky"
    if issue_type == "alias_prefix_missing":
        if count >= 2 and prefix not in {"BMNH:PV:M"} and not prefix.startswith("BMNH:"):
            return "P4b-easy-alias"
        return "P4b-variant"
    if count >= 4:
        return "P4c-orphan-high"
    if count >= 3:
        return "P4c-orphan-medium"
    return "P4d-orphan-low"


def main() -> None:
    conn = duckdb.connect(str(DB), read_only=True)
    gap_rows = list(csv.DictReader(GAP.open(encoding="utf-8")))

    species_rows = conn.execute(
        f"""
        WITH species_with_museum AS (
            SELECT
                s.sci_name,
                s.type_voucher,
                s.type_locality,
                s.type_lat,
                s.type_lon,
                (
                    SELECT tsi.abbreviation
                    FROM type_specimen_institutions tsi
                    WHERE {MUSEUM_MATCH}
                    ORDER BY LENGTH(tsi.abbreviation) DESC
                    LIMIT 1
                ) AS matched_abbreviation
            FROM species s
            WHERE s.type_voucher IS NOT NULL AND TRIM(s.type_voucher) <> ''
        )
        SELECT * FROM species_with_museum
        """
    ).fetchdf()

    by_prefix: dict[str, list[dict]] = {}
    for row in species_rows.to_dict("records"):
        p = voucher_prefix(str(row["type_voucher"]))
        if p in SKIP:
            continue
        by_prefix.setdefault(p, []).append(row)

    backlog: list[dict] = []
    for gap in gap_rows:
        prefix = gap["voucher_prefix"]
        if prefix in SKIP:
            continue
        issue_type = gap["issue_type"]
        related = gap["related_metadata_abbreviations"]
        count = int(gap["species_count"])
        priority = wave_priority(issue_type, prefix, related, count)
        examples = gap["example_species"].split("; ")
        species_detail = by_prefix.get(prefix, [])
        on_map = sum(1 for s in species_detail if s["matched_abbreviation"])
        unmatched = len(species_detail) - on_map
        backlog.append(
            {
                "wave_priority": priority,
                "issue_type": issue_type.replace("alias_prefix_missing", "alias").replace(
                    "prefix_not_in_metadata", "orphan"
                ),
                "voucher_prefix": prefix,
                "species_count": count,
                "on_map_via_shorter_code": on_map,
                "completely_unmatched": unmatched,
                "related_metadata": related,
                "example_species": gap["example_species"],
                "example_vouchers": "; ".join(
                    f"{s['sci_name']}={s['type_voucher'][:60]}"
                    for s in species_detail[:3]
                ),
                "investigation_notes": PRIORITY_NOTES.get(prefix, gap["notes"]),
                "suggested_action": _suggested_action(priority, prefix, related, issue_type),
            }
        )

    backlog.sort(key=lambda r: (r["wave_priority"], -r["species_count"], r["voucher_prefix"]))

    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(backlog[0].keys()))
        writer.writeheader()
        writer.writerows(backlog)

    unmatched_total = conn.execute(
        """
        SELECT COUNT(*) FROM species s
        WHERE s.type_voucher IS NOT NULL AND TRIM(s.type_voucher) <> ''
          AND NOT EXISTS (
            SELECT 1 FROM type_specimen_institutions tsi
            WHERE UPPER(TRIM(s.type_voucher)) LIKE UPPER(tsi.abbreviation) || '%'
          )
        """
    ).fetchone()[0]

    lines = [
        "# Museum prefix wave 4 — investigation backlog",
        "",
        "Generated after P3 alias fixes (BMNH, NMPR, MACN-MA, NSMT-M, NMNZ, OUM, CNM, …).",
        "Use this file to research and resolve remaining prefix gaps before updating `TypeSpecimenMetadata_v2.4.csv`.",
        "",
        "## Current snapshot",
        "",
        f"- **Completely unmatched vouchers:** {unmatched_total} species",
        f"- **Prefix gaps in this backlog:** {len(backlog)} rows",
        f"- **Not fixable via metadata:** `UNTRACED` (234) + `LOST` (136) = 370 species",
        "",
        "## Priority legend",
        "",
        "| Priority | Meaning |",
        "|----------|---------|",
        "| **P4-risky** | Wrong alias would mis-assign museum (CMI/CMN→CM, MNK→MN) |",
        "| **P4b-easy-alias** | Likely alias to existing institution; verify then add row |",
        "| **P4b-variant** | Odd BMNH catalog strings; may need parser or extra alias |",
        "| **P4c-orphan-high/medium** | No related metadata code; needs institution research (≥3 sp.) |",
        "| **P4d-orphan-low** | Same, 2 species |",
        "",
        "## P4-risky — resolve first",
        "",
    ]

    for row in backlog:
        if row["wave_priority"] != "P4-risky":
            continue
        lines += _md_row(row)

    lines += [
        "",
        "## P4b — likely aliases (verify institution, then add metadata row)",
        "",
    ]
    for row in backlog:
        if not row["wave_priority"].startswith("P4b"):
            continue
        lines += _md_row(row)

    lines += [
        "",
        "## P4c — orphan prefixes (≥3 species, needs new institution row)",
        "",
    ]
    for row in backlog:
        if not row["wave_priority"].startswith("P4c"):
            continue
        lines += _md_row(row)

    lines += [
        "",
        "## P4d — orphan prefixes (2 species)",
        "",
        "See `museum_prefix_wave4_backlog.csv` for the full list.",
        "",
        "## Workflow",
        "",
        "1. Pick a prefix from **P4-risky** or **P4c-orphan-high**.",
        "2. Confirm institution from original publication / collection database.",
        "3. Add row to `TypeSpecimenMetadata_v2.4.csv` (or alias if same institution).",
        "4. Rebuild: `python mdd_project/scripts/setup_database.py --skip-exports`",
        "5. Regenerate audits: `python mdd_project/scripts/audit_museum_matching.py`",
        "",
        "## Regenerate this file",
        "",
        "```bash",
        "python mdd_project/scripts/build_museum_prefix_wave4_backlog.py",
        "```",
        "",
    ]

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {len(backlog)} rows to {OUT_CSV}")
    print(f"Wrote {OUT_MD}")


def _suggested_action(priority: str, prefix: str, related: str, issue_type: str) -> str:
    if priority == "P4-risky":
        if prefix in {"CMI", "CMN"}:
            return "Identify institution per voucher; add CMN (Canadian Museum of Nature) or fix CM row — do NOT alias to Carnegie CM."
        if prefix == "MNK":
            return "Add MNK row for correct museum; prevents false match to Museu Nacional (MN)."
    if issue_type == "alias_prefix_missing" and related and priority == "P4b-easy-alias":
        return f"Add {prefix} alias row pointing to same institution as {related.split(';')[0].strip()}."
    if issue_type == "prefix_not_in_metadata":
        return f"Research institution for {prefix}; add new metadata row if confirmed."
    if prefix.startswith("BMNH:"):
        return "BMNH alias exists; these colon-suffix variants may still match BM/BMNH — low priority."
    return "Manual review required."


def _md_row(row: dict) -> list[str]:
    return [
        f"### `{row['voucher_prefix']}` ({row['species_count']} sp.)",
        "",
        f"- **Priority:** {row['wave_priority']}",
        f"- **Issue:** {row['issue_type']}",
        f"- **On map via shorter code:** {row['on_map_via_shorter_code']}",
        f"- **Completely unmatched:** {row['completely_unmatched']}",
        f"- **Related metadata:** {row['related_metadata'] or '—'}",
        f"- **Examples:** {row['example_species']}",
        f"- **Suggested action:** {row['suggested_action']}",
        f"- **Notes:** {row['investigation_notes']}",
        "",
    ]


if __name__ == "__main__":
    main()
