#!/usr/bin/env python3
"""Infer museum signals from type_voucher_uris for excluded vouchers (review-only)."""

from __future__ import annotations

import csv
import re
from pathlib import Path
from urllib.parse import urlparse

import duckdb

DB = Path(__file__).resolve().parents[1] / "data" / "processed" / "mdd.duckdb"
REVIEW = Path(__file__).resolve().parents[1] / "data" / "review" / "museum"
OUT = REVIEW / "museum_voucher_uri_inferred.csv"

# Domain (or substring) -> inferred institution metadata abbreviation.
URI_DOMAIN_HINTS: list[tuple[str, str, str]] = [
    ("coldb.mnhn.fr", "MNHN", "Muséum national d'Histoire naturelle (Paris) catalog URI"),
    ("data.nhm.ac.uk", "BM", "Natural History Museum London data portal URI"),
    ("collections.nhm.org", "LACM", "Natural History Museum of Los Angeles County URI"),
    ("collections.museum.wa.gov.au", "WAM", "Western Australian Museum URI"),
    ("collections.ala.org.au", "ANIC", "Atlas of Living Australia / Australian collections URI"),
    ("idigbio.org", "IDIGBIO", "iDigBio aggregator URI; resolve to holding institution in source record"),
    ("gbif.org", "GBIF", "GBIF occurrence URI; resolve to publishing institution in source record"),
    ("scan-bugs.org", "SCAN", "Symbiota SCAN portal URI; resolve to holding institution in source record"),
]


def split_uris(raw: str | None) -> list[str]:
    if not raw or not raw.strip():
        return []
    return [part.strip() for part in re.split(r"[;,]\s*", raw.strip()) if part.strip()]


def infer_from_uri(uri: str) -> tuple[str, str, str] | None:
    host = (urlparse(uri).netloc or "").lower().removeprefix("www.")
    for domain, abbr, note in URI_DOMAIN_HINTS:
        if domain in host or domain in uri.lower():
            return abbr, domain, note
    return None


def main() -> None:
    conn = duckdb.connect(str(DB), read_only=True)
    inst = {
        r[0].upper()
        for r in conn.execute("SELECT abbreviation FROM type_specimen_institutions").fetchall()
    }

    rows = conn.execute(
        """
        SELECT
            species_id,
            sci_name,
            type_voucher,
            type_voucher_uris,
            type_kind
        FROM species
        WHERE type_voucher IS NOT NULL
          AND TRIM(type_voucher) <> ''
          AND type_voucher_uris IS NOT NULL
          AND TRIM(type_voucher_uris) <> ''
        """
    ).fetchall()

    out_rows: list[dict[str, str]] = []
    for species_id, sci_name, voucher, uris_raw, type_kind in rows:
        assert voucher is not None
        v = voucher.strip().upper()
        matched = any(v.startswith(a) for a in inst)
        for uri in split_uris(uris_raw):
            inferred = infer_from_uri(uri)
            if not inferred:
                continue
            abbr, domain, note = inferred
            out_rows.append(
                {
                    "species_id": str(species_id),
                    "sci_name": sci_name,
                    "type_kind": type_kind or "",
                    "type_voucher": voucher,
                    "voucher_matches_metadata": "yes" if matched else "no",
                    "type_voucher_uri": uri,
                    "uri_domain": domain,
                    "inferred_institution_abbreviation": abbr,
                    "inference_note": note,
                    "review_action": (
                        "Review-only signal; does not override voucher-prefix matching."
                        if not matched
                        else "Supplementary URI signal for already matched voucher."
                    ),
                }
            )

    out_rows.sort(key=lambda r: (r["voucher_matches_metadata"], r["inferred_institution_abbreviation"], r["sci_name"]))
    REVIEW.mkdir(parents=True, exist_ok=True)
    fields = [
        "species_id",
        "sci_name",
        "type_kind",
        "type_voucher",
        "voucher_matches_metadata",
        "type_voucher_uri",
        "uri_domain",
        "inferred_institution_abbreviation",
        "inference_note",
        "review_action",
    ]
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out_rows)

    unmatched = [r for r in out_rows if r["voucher_matches_metadata"] == "no"]
    print(f"Wrote {len(out_rows)} URI inference rows to {OUT}")
    print(f"Unmatched vouchers with URI signals: {len(unmatched)}")
    for abbr in sorted({r["inferred_institution_abbreviation"] for r in unmatched}):
        count = sum(1 for r in unmatched if r["inferred_institution_abbreviation"] == abbr)
        print(f"  {abbr}: {count}")


if __name__ == "__main__":
    main()
