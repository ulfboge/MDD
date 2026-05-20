#!/usr/bin/env python3
"""Geocode NHRM type specimens missing coordinates (wrapper around geocode_type_localities)."""

from __future__ import annotations

import argparse
from pathlib import Path

from geocode_curated_overrides import build_nhrm_geocodes
from geocode_type_localities import (
    REVIEW_DIR,
    load_rows_from_csv,
    load_rows_from_duckdb,
    run_geocoder,
    summarize,
    write_geocoded_csv,
)

DEFAULT_OUTPUT = REVIEW_DIR / "nhrm_type_specimens_missing_coords_geocoded.csv"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-csv",
        type=Path,
        help="Optional coverage export CSV. Default: load NHRM rows from DuckDB.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output CSV (default: {DEFAULT_OUTPUT}).",
    )
    args = parser.parse_args()

    if args.input_csv:
        rows = load_rows_from_csv(args.input_csv)
    else:
        rows = load_rows_from_duckdb(museum="NHRM", missing_geolocation=True)

    curated = build_nhrm_geocodes()
    phases = ["curated", "explicit"]
    out_rows = run_geocoder(rows, phases=phases, curated=curated)
    write_geocoded_csv(out_rows, args.output)

    stats = summarize(out_rows)
    proposed = stats.get("proposed", 0)
    print(f"Wrote {args.output}")
    print(f"Geocoded {proposed}/{len(out_rows)} rows")


if __name__ == "__main__":
    main()
