"""
setup_database.py — Build mdd.duckdb from MDD v2.4 CSV files.

Usage:
    python mdd_project/scripts/setup_database.py [--raw-dir PATH] [--db PATH] [--skip-exports]

The script:
  1. Locates raw CSV files (defaults: repo root → mdd_project/data/raw/MDD/)
  2. Creates data/processed/ directories
  3. Imports all MDD tables and creates indexes (import_mdd.sql)
  4. Creates analytical views (create_views.sql)
  5. Exports GeoParquet + CSV for QGIS (export_for_qgis.sql)
  6. Prints summary statistics
"""

from __future__ import annotations

import argparse
import sys
import textwrap
import time
from pathlib import Path

import duckdb

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------
SCRIPT_DIR  = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent                          # mdd_project/
REPO_ROOT   = PROJECT_DIR.parent                         # repo root

SQL_DIR          = SCRIPT_DIR
PROCESSED_DIR    = PROJECT_DIR / "data" / "processed"
EXPORTS_DIR      = PROCESSED_DIR / "exports"
GEOPARQUET_DIR   = PROCESSED_DIR / "geoparquet"

DB_PATH          = PROCESSED_DIR / "mdd.duckdb"

# ---------------------------------------------------------------------------
# CSV file names (MDD v2.4)
# ---------------------------------------------------------------------------
CSV_FILES = {
    "species_csv":       "MDD_v2.4_6871species.csv",
    "synonyms_csv":      "Species_Syn_v2.4.csv",
    "type_specimen_csv": "TypeSpecimenMetadata_v2.4.csv",
    "meta_csv":          "META_v2.4.csv",
    "diff_csv":          "Diff_v2.3-v2.4.csv",
}


def find_raw_dir(hint: Path | None) -> Path:
    """Return the directory containing all MDD CSV files, or raise."""
    candidates = []
    if hint:
        candidates.append(Path(hint))
    candidates += [
        REPO_ROOT,                                    # files live at repo root
        PROJECT_DIR / "data" / "raw" / "MDD",
    ]
    for d in candidates:
        if all((d / name).exists() for name in CSV_FILES.values()):
            return d.resolve()
    missing = [name for name in CSV_FILES.values()
               if not any((d / name).exists() for d in candidates)]
    print(
        "\n[ERROR] Could not find all MDD CSV files.\n"
        f"  Missing: {missing}\n"
        "  Looked in:\n" +
        "\n".join(f"    {d}" for d in candidates) +
        "\n\n  Download MDD v2.4 from:\n"
        "    https://www.mammaldiversity.org/\n"
        "  or Zenodo: https://doi.org/10.5281/zenodo.18135819\n"
        "  Place all CSV files in one of the candidate directories above.",
        file=sys.stderr,
    )
    sys.exit(1)


def run_sql_file(con: duckdb.DuckDBPyConnection, path: Path, params: dict) -> None:
    """Execute a SQL file, substituting named :params with quoted string literals."""
    sql = path.read_text(encoding="utf-8")
    for key, value in params.items():
        sql = sql.replace(f":{key}", f"'{value}'")
    # Execute statement-by-statement (split on ';' keeping context)
    for stmt in _split_statements(sql):
        if stmt.strip():
            try:
                result = con.execute(stmt)
                # Print any check/status messages returned by SELECT statements
                if result and stmt.strip().upper().startswith("SELECT"):
                    rows = result.fetchall()
                    for row in rows:
                        print("  " + " | ".join(str(c) for c in row))
            except Exception as exc:
                print(f"  [WARN] Statement failed: {exc}\n  SQL: {stmt[:120]}...")


def _split_statements(sql: str) -> list[str]:
    """Naïve semicolon split that skips comment-only blocks."""
    stmts = []
    buf: list[str] = []
    for line in sql.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            buf.append(line)
            continue
        buf.append(line)
        if stripped.endswith(";"):
            stmts.append("\n".join(buf))
            buf = []
    if buf:
        stmts.append("\n".join(buf))
    return stmts


def print_summary(con: duckdb.DuckDBPyConnection) -> None:
    """Print key statistics from the loaded database."""
    print("\n" + "=" * 60)
    print("  MDD DATABASE SUMMARY")
    print("=" * 60)
    queries = {
        "Total species":             "SELECT COUNT(*) FROM species",
        "Extant wild species":       "SELECT COUNT(*) FROM v_species_current",
        "Extinct species":           "SELECT COUNT(*) FROM species WHERE extinct = true",
        "Domestic species":          "SELECT COUNT(*) FROM species WHERE domestic = true",
        "Total synonyms":            "SELECT COUNT(*) FROM synonyms",
        "Species with coordinates":  "SELECT COUNT(*) FROM v_type_localities",
        "Synonym type localities":   "SELECT COUNT(*) FROM v_type_localities_synonyms",
        "Orders":                    'SELECT COUNT(DISTINCT "order") FROM species',
        "Families":                  "SELECT COUNT(DISTINCT family) FROM species",
    }
    for label, q in queries.items():
        try:
            val = con.execute(q).fetchone()[0]
            print(f"  {label:<35} {val:>8,}")
        except Exception as exc:
            print(f"  {label:<35} ERROR: {exc}")
    print("=" * 60 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir",      type=Path, default=None,
                        help="Directory containing MDD CSV files")
    parser.add_argument("--db",           type=Path, default=DB_PATH,
                        help=f"Output DuckDB path (default: {DB_PATH})")
    parser.add_argument("--skip-exports", action="store_true",
                        help="Skip GeoParquet/CSV export step")
    args = parser.parse_args()

    t0 = time.perf_counter()

    # Locate raw data
    raw_dir = find_raw_dir(args.raw_dir)
    print(f"[INFO] Raw CSV directory : {raw_dir}")

    # Ensure output dirs exist
    db_path = Path(args.db).resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    GEOPARQUET_DIR.mkdir(parents=True, exist_ok=True)

    # CSV paths for SQL substitution
    csv_params = {key: str(raw_dir / name) for key, name in CSV_FILES.items()}
    # Use forward slashes for DuckDB on Windows
    csv_params = {k: v.replace("\\", "/") for k, v in csv_params.items()}

    print(f"[INFO] Database path     : {db_path}")
    print("[INFO] Connecting to DuckDB …")

    with duckdb.connect(str(db_path)) as con:
        # Install / load extensions
        print("[INFO] Loading DuckDB extensions …")
        con.execute("INSTALL spatial; LOAD spatial;")

        # Step 1: Import tables
        print("\n[STEP 1] Importing MDD tables …")
        run_sql_file(con, SQL_DIR / "import_mdd.sql", csv_params)

        # Step 2: Create views
        print("\n[STEP 2] Creating analytical views …")
        run_sql_file(con, SQL_DIR / "create_views.sql", {})

        # Step 3: Exports (optional)
        if not args.skip_exports:
            print("\n[STEP 3] Exporting for QGIS …")
            export_params = {
                "type_localities_geoparquet": str(GEOPARQUET_DIR / "type_localities.parquet").replace("\\", "/"),
                "species_current_parquet":    str(GEOPARQUET_DIR / "species_current.parquet").replace("\\", "/"),
                "synonyms_parquet":           str(GEOPARQUET_DIR / "synonyms.parquet").replace("\\", "/"),
                "species_all_csv":            str(EXPORTS_DIR / "species_all.csv").replace("\\", "/"),
            }
            run_sql_file(con, SQL_DIR / "export_for_qgis.sql", export_params)
        else:
            print("\n[STEP 3] Skipped (--skip-exports).")

        # Summary
        print_summary(con)

    elapsed = time.perf_counter() - t0
    print(f"[INFO] Done in {elapsed:.1f}s")
    print(f"[INFO] Database: {db_path}")
    print(f"[INFO] GeoParquet: {GEOPARQUET_DIR}")
    print(f"[INFO] Exports:    {EXPORTS_DIR}")


if __name__ == "__main__":
    main()
