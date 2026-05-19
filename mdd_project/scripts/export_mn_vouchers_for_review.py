#!/usr/bin/env python3
"""Export MN-prefixed type vouchers for manual museum identification."""

from __future__ import annotations

from pathlib import Path

import duckdb

DB = Path(__file__).resolve().parents[1] / "data" / "processed" / "mdd.duckdb"
OUT = Path(__file__).resolve().parents[1] / "data" / "review" / "mn_vouchers_for_review.csv"


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
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f"Wrote {len(df)} rows to {OUT}")


if __name__ == "__main__":
    main()
