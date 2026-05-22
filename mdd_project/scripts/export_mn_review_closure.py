#!/usr/bin/env python3
"""Write MN voucher review closure report after prefix matching audit."""

from __future__ import annotations

from pathlib import Path

import duckdb

DB = Path(__file__).resolve().parents[1] / "data" / "processed" / "mdd.duckdb"
REVIEW = Path(__file__).resolve().parents[1] / "data" / "review" / "museum"
OUT = REVIEW / "museum_mn_review_closure.csv"

MUSEUM_MATCH = """
    s.type_voucher IS NOT NULL
    AND TRIM(s.type_voucher) <> ''
    AND UPPER(TRIM(s.type_voucher)) LIKE UPPER(tsi.abbreviation) || '%'
"""


def main() -> None:
    conn = duckdb.connect(str(DB), read_only=True)
    df = conn.execute(
        f"""
        SELECT
            s.sci_name,
            s.type_voucher,
            s.type_kind,
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
        WHERE s.type_voucher IS NOT NULL
          AND TRIM(s.type_voucher) <> ''
          AND (
            UPPER(TRIM(s.type_voucher)) LIKE 'MN %'
            OR UPPER(TRIM(s.type_voucher)) LIKE 'MN-%'
            OR UPPER(TRIM(s.type_voucher)) LIKE 'MN/%'
          )
        ORDER BY s.sci_name
        """
    ).fetchdf()

    df["review_date"] = "2026-05-20"
    df["review_outcome"] = df["matched_abbreviation"].apply(
        lambda abbr: "closed_match_mn" if abbr == "MN" else "needs_follow_up"
    )
    df["review_note"] = df.apply(
        lambda row: (
            "MN prefix matches Museu Nacional UFRJ metadata; no metadata change required."
            if row["matched_abbreviation"] == "MN"
            else f"Unexpected match {row['matched_abbreviation']}; inspect longest-prefix rule."
        ),
        axis=1,
    )

    REVIEW.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    closed = int((df["review_outcome"] == "closed_match_mn").sum())
    print(f"Wrote {len(df)} rows to {OUT}")
    print(f"Closed MN matches: {closed}/{len(df)}")


if __name__ == "__main__":
    main()
