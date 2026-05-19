#!/usr/bin/env python3
"""Export MN-prefixed type vouchers (Museu Nacional UFRJ) for review archives."""

from __future__ import annotations

from pathlib import Path

import duckdb

DB = Path(__file__).resolve().parents[1] / "data" / "processed" / "mdd.duckdb"
REVIEW_DIR = Path(__file__).resolve().parents[1] / "data" / "review"
OUT = REVIEW_DIR / "mn_vouchers_for_review.csv"
OUT_ENRICHED = REVIEW_DIR / "mn_vouchers_for_review_enriched.csv"

MUSEUM_FULL_NAME = "Museu Nacional, Universidade Federal do Rio de Janeiro"
MUSEUM_CITY = "Rio de Janeiro"
MUSEUM_COUNTRY = "Brazil"
INSTITUTION_CODE = "MN (MNRJ)"
CONFIDENCE = "Hög"
SOURCE_URL = (
    "https://digitallibrary.amnh.org/server/api/core/bitstreams/"
    "9864b9ec-11a5-4018-819e-59f4053bc3ab/content; "
    "https://obis.org/institute/13167"
)


def main() -> None:
    conn = duckdb.connect(str(DB), read_only=True)
    df = conn.execute(
        """
        SELECT
            sci_name,
            REPLACE(sci_name, '_', ' ') AS sci_name_space,
            main_common_name,
            "order",
            family,
            genus,
            type_voucher,
            type_kind,
            type_locality,
            type_lat,
            type_lon
        FROM species
        WHERE type_voucher IS NOT NULL
          AND TRIM(type_voucher) <> ''
          AND (
            UPPER(TRIM(type_voucher)) LIKE 'MN %'
            OR UPPER(TRIM(type_voucher)) LIKE 'MN-%'
            OR UPPER(TRIM(type_voucher)) LIKE 'MN/%'
          )
        ORDER BY sci_name
        """
    ).fetchdf()
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f"Wrote {len(df)} rows to {OUT}")

    enriched = df.copy()
    enriched["museum_full_name"] = MUSEUM_FULL_NAME
    enriched["museum_city"] = MUSEUM_CITY
    enriched["museum_country"] = MUSEUM_COUNTRY
    enriched["institution_code"] = INSTITUTION_CODE
    enriched["confidence"] = CONFIDENCE
    enriched["source_url"] = SOURCE_URL
    enriched.to_csv(OUT_ENRICHED, index=False)
    print(f"Wrote {len(enriched)} rows to {OUT_ENRICHED}")


if __name__ == "__main__":
    main()
