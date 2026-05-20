#!/usr/bin/env python3
"""Import review CSV estimated coordinates into mdd.duckdb (separate from official MDD coords)."""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "mdd_project" / "data" / "processed" / "mdd.duckdb"
DEFAULT_CSV = ROOT / "mdd_project" / "data" / "review" / "estimated_type_localities.csv"


def import_estimated_csv(con: duckdb.DuckDBPyConnection, csv_path: Path) -> int:
    csv_sql = str(csv_path.resolve()).replace("\\", "/")
    con.execute("DROP TABLE IF EXISTS estimated_type_localities")
    con.execute(
        f"""
        CREATE TABLE estimated_type_localities AS
        SELECT
            TRY_CAST(species_id AS INTEGER) AS species_id,
            sci_name,
            sci_name_space,
            main_common_name,
            "order",
            family,
            genus,
            type_voucher,
            type_kind,
            type_locality,
            museum_abbreviation,
            museum_name,
            museum_location,
            museum_country,
            geocode_phase,
            geocode_query,
            TRY_CAST(type_lat_suggested AS DOUBLE) AS estimated_lat,
            TRY_CAST(type_lon_suggested AS DOUBLE) AS estimated_lon,
            TRY_CAST(coordinate_uncertainty_m AS INTEGER) AS coordinate_uncertainty_m,
            geocode_method,
            geocode_confidence,
            geocode_notes,
            review_status,
            CURRENT_TIMESTAMP AS imported_at
        FROM read_csv_auto('{csv_sql}', header=true, sample_size=-1)
        WHERE review_status = 'proposed'
          AND type_lat_suggested IS NOT NULL
          AND TRIM(CAST(type_lat_suggested AS VARCHAR)) <> ''
          AND type_lon_suggested IS NOT NULL
          AND TRIM(CAST(type_lon_suggested AS VARCHAR)) <> ''
        """
    )
    count = con.execute("SELECT COUNT(*) FROM estimated_type_localities").fetchone()[0]
    return int(count)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="Estimated localities CSV.")
    parser.add_argument("--db", type=Path, default=DB, help="DuckDB path.")
    args = parser.parse_args()

    if not args.csv.exists():
        print(f"[SKIP] No CSV at {args.csv}")
        return
    if not args.db.parent.exists():
        args.db.parent.mkdir(parents=True, exist_ok=True)

    with duckdb.connect(str(args.db)) as con:
        count = import_estimated_csv(con, args.csv)
    print(f"Imported {count} estimated type localities into {args.db}")


if __name__ == "__main__":
    main()
