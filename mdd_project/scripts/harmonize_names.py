"""
harmonize_names.py — Resolve any species name column to the current MDD accepted name.

Usage:
    python mdd_project/scripts/harmonize_names.py INPUT.csv --col scientificName
    python mdd_project/scripts/harmonize_names.py INPUT.csv --col scientificName --out OUTPUT.csv

Given a CSV file with a column of species names (spaces or underscores, any combination
format), this script appends columns:
    mdd_accepted_name       — accepted sci_name in MDD underscore format
    mdd_accepted_name_space — space-separated form for display
    mdd_species_id          — MDD integer species ID
    mdd_family              — accepted family
    mdd_order               — accepted order
    mdd_iucn_status         — IUCN Red List status in MDD
    mdd_match_type          — how the match was made: 'exact', 'synonym', or 'unmatched'

Match logic (in priority order):
    1. Exact match on species.sci_name (underscore form)
    2. Exact match on species.sci_name_space (space form)
    3. Match via synonyms.original_combination
    4. Match via synonyms.normalized_original_combination
    5. Unmatched → all mdd_* columns are NULL

⚠️ Case-sensitive for exact matches; use --ilike flag for case-insensitive synonym lookup.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb
import pandas as pd

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_DIR = _SCRIPT_DIR.parent
DB_PATH = _PROJECT_DIR / "data" / "processed" / "mdd.duckdb"


def harmonize(
    input_path: Path,
    name_col: str,
    output_path: Path,
    db_path: Path,
    ilike: bool = False,
) -> None:
    if not db_path.exists():
        print(
            f"[ERROR] Database not found: {db_path}\n"
            "  Run: python mdd_project/scripts/setup_database.py",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"[INFO] Reading input: {input_path}")
    df = pd.read_csv(input_path, dtype=str, keep_default_na=False)

    if name_col not in df.columns:
        print(
            f"[ERROR] Column '{name_col}' not found in {input_path}.\n"
            f"  Available columns: {list(df.columns)}",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"[INFO] Connecting to DuckDB: {db_path}")
    con = duckdb.connect(str(db_path), read_only=True)

    # Build a lookup table in DuckDB using the input names
    # Register the pandas DataFrame as a DuckDB view for efficient in-process joining
    names_df = pd.DataFrame({"input_name": df[name_col].unique()})
    con.register("_input_names", names_df)

    cmp = "ILIKE" if ilike else "="

    lookup_sql = f"""
    WITH normalised AS (
        SELECT
            input_name,
            REPLACE(input_name, ' ', '_') AS name_us,  -- underscore form
            REPLACE(input_name, '_', ' ') AS name_sp   -- space form
        FROM _input_names
    ),
    direct_match AS (
        -- Priority 1 & 2: direct match against accepted species
        SELECT
            n.input_name,
            sp.sci_name             AS mdd_accepted_name,
            sp.species_id           AS mdd_species_id,
            sp.family               AS mdd_family,
            sp."order"              AS mdd_order,
            sp.iucn_status          AS mdd_iucn_status,
            'exact'                 AS mdd_match_type
        FROM normalised n
        JOIN species sp
          ON  sp.sci_name {cmp} n.name_us
           OR sp.sci_name {cmp} n.name_sp
           OR sp.sci_name {cmp} n.input_name
    ),
    synonym_match AS (
        -- Priority 3 & 4: match via synonyms
        SELECT
            n.input_name,
            sp.sci_name             AS mdd_accepted_name,
            sp.species_id           AS mdd_species_id,
            sp.family               AS mdd_family,
            sp."order"              AS mdd_order,
            sp.iucn_status          AS mdd_iucn_status,
            'synonym'               AS mdd_match_type
        FROM normalised n
        JOIN synonyms syn
          ON  syn.original_combination {cmp} n.name_us
           OR syn.original_combination {cmp} n.name_sp
           OR syn.original_combination {cmp} n.input_name
           OR syn.normalized_original_combination {cmp} n.name_us
           OR syn.normalized_original_combination {cmp} n.name_sp
        JOIN species sp ON syn.species_id = sp.species_id
    ),
    combined AS (
        SELECT * FROM direct_match
        UNION ALL
        -- Only use synonym match when no direct match was found
        SELECT sm.* FROM synonym_match sm
        WHERE sm.input_name NOT IN (SELECT input_name FROM direct_match)
    )
    SELECT DISTINCT ON (input_name)
        input_name,
        mdd_accepted_name,
        REPLACE(mdd_accepted_name, '_', ' ')  AS mdd_accepted_name_space,
        mdd_species_id,
        mdd_family,
        mdd_order,
        mdd_iucn_status,
        mdd_match_type
    FROM combined
    ORDER BY input_name, mdd_match_type   -- 'exact' sorts before 'synonym'
    """

    print("[INFO] Running name harmonization …")
    lookup = con.execute(lookup_sql).df()
    con.close()

    print(f"[INFO] Input names: {len(names_df):,}")
    matched = lookup[lookup["mdd_match_type"].notna()]
    exact = matched[matched["mdd_match_type"] == "exact"]
    syn = matched[matched["mdd_match_type"] == "synonym"]
    print(f"  Exact matches:   {len(exact):,}")
    print(f"  Synonym matches: {len(syn):,}")
    unmatched_n = len(names_df) - len(matched)
    print(f"  Unmatched:       {unmatched_n:,}")

    result = df.merge(lookup, left_on=name_col, right_on="input_name", how="left")

    # Mark unmatched rows explicitly
    result["mdd_match_type"] = result["mdd_match_type"].fillna("unmatched")
    result = result.drop(columns=["input_name"], errors="ignore")

    print(f"[INFO] Writing output: {output_path}")
    result.to_csv(output_path, index=False)
    print(f"[INFO] Done — {len(result):,} rows written to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input", type=Path, help="Input CSV file")
    parser.add_argument(
        "--col", required=True,
        help="Column name containing species names to harmonize",
    )
    parser.add_argument(
        "--out", type=Path, default=None,
        help="Output CSV path (default: INPUT_harmonized.csv)",
    )
    parser.add_argument(
        "--db", type=Path, default=DB_PATH,
        help=f"DuckDB path (default: {DB_PATH})",
    )
    parser.add_argument(
        "--ilike", action="store_true",
        help="Case-insensitive name matching (slower but catches capitalisation variants)",
    )
    args = parser.parse_args()

    output = args.out or args.input.with_stem(args.input.stem + "_harmonized")
    harmonize(args.input, args.col, output, args.db, ilike=args.ilike)


if __name__ == "__main__":
    main()
