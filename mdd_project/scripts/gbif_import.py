"""
gbif_import.py — GBIF occurrence download and DuckDB ingestion pipeline.

PIPELINE:
    1. Search GBIF occurrence API for one or more species names
    2. Filter records with coordinate issues or missing lat/lon
    3. Harmonize reported names to MDD v2.4 accepted names via synonyms table
    4. Load into DuckDB: observations table with species_id FK to MDD species
    5. Create spatial geometry via DuckDB spatial extension (ST_Point)
    6. Export GeoParquet to data/processed/geoparquet/observations.parquet

GBIF API (no key required for occurrence search):
    https://api.gbif.org/v1/occurrence/search

USAGE:
    # Single species, limit 50 occurrences
    python mdd_project/scripts/gbif_import.py --species "Ursus arctos" --limit 50

    # By GBIF taxon key
    python mdd_project/scripts/gbif_import.py --taxon-key 2433459 --limit 200

    # All species in a family (batch mode, 100 per species)
    python mdd_project/scripts/gbif_import.py --from-mdd --family Galagidae --limit-per-species 100

    # Append to existing data (default behaviour); force full reload:
    python mdd_project/scripts/gbif_import.py --species "Ursus arctos" --limit 100 --replace

    # Skip GeoParquet export (faster for repeat imports)
    python mdd_project/scripts/gbif_import.py --species "Ursus arctos" --limit 100 --no-export
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

import duckdb
import requests

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_DIR = _SCRIPT_DIR.parent

DB_PATH = _PROJECT_DIR / "data" / "processed" / "mdd.duckdb"
GEOPARQUET_DIR = _PROJECT_DIR / "data" / "processed" / "geoparquet"
OCCURRENCE_DIR = _PROJECT_DIR / "data" / "external" / "occurrence_data"

# ---------------------------------------------------------------------------
# GBIF API constants
# ---------------------------------------------------------------------------
GBIF_OCCURRENCE_URL = "https://api.gbif.org/v1/occurrence/search"
GBIF_SPECIES_URL = "https://api.gbif.org/v1/species/match"
GBIF_PAGE_LIMIT = 300          # max records per GBIF page
REQUEST_SLEEP = 0.3            # seconds between requests (polite rate-limiting)
REQUEST_TIMEOUT = 30           # seconds per HTTP request

# GBIF coordinate issue flags that indicate unreliable spatial data
COORDINATE_ISSUES_FILTER = {
    "COORDINATE_INVALID",
    "ZERO_COORDINATE",
    "COORDINATE_OUT_OF_RANGE",
    "COUNTRY_COORDINATE_MISMATCH",
    "COORDINATE_ROUNDED",          # keep rounded if it's the only issue
}
# Issues that are disqualifying (must NOT appear)
DISQUALIFYING_ISSUES = {
    "COORDINATE_INVALID",
    "ZERO_COORDINATE",
    "COORDINATE_OUT_OF_RANGE",
    "COUNTRY_COORDINATE_MISMATCH",
}

# ---------------------------------------------------------------------------
# Observations table DDL — created in DuckDB alongside MDD tables
# ---------------------------------------------------------------------------
CREATE_OBSERVATIONS_SQL = """
CREATE TABLE IF NOT EXISTS observations (
    obs_id              BIGINT PRIMARY KEY,    -- GBIF occurrenceKey
    gbif_id             BIGINT,                -- same as obs_id for clarity
    reported_name       VARCHAR,               -- species name as reported by GBIF
    mdd_species_id      INTEGER,               -- FK → species.species_id (NULL if unmatched)
    mdd_sci_name        VARCHAR,               -- MDD accepted name (underscore form)
    mdd_match_type      VARCHAR,               -- 'exact', 'synonym', or 'unmatched'
    latitude            DOUBLE,
    longitude           DOUBLE,
    geom                GEOMETRY,              -- ST_Point(longitude, latitude)
    event_date          DATE,
    dataset_name        VARCHAR,
    dataset_key         VARCHAR,
    occurrence_status   VARCHAR,
    basis_of_record     VARCHAR,
    country_code        VARCHAR,
    state_province      VARCHAR,
    locality            VARCHAR,
    coordinate_uncertainty_m  DOUBLE,
    issues              VARCHAR,               -- semicolon-separated GBIF issue flags
    source              VARCHAR DEFAULT 'GBIF',
    imported_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_OBSERVATIONS_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_observations_species_id
    ON observations (mdd_species_id);
CREATE INDEX IF NOT EXISTS idx_observations_sci_name
    ON observations (mdd_sci_name);
"""


# ---------------------------------------------------------------------------
# GBIF fetching
# ---------------------------------------------------------------------------

def lookup_gbif_taxon_key(species_name: str) -> int | None:
    """
    Resolve a species name to a GBIF taxon key via the species/match endpoint.
    Returns the usageKey or None if no confident match is found.
    """
    try:
        resp = requests.get(
            GBIF_SPECIES_URL,
            params={"name": species_name, "kingdom": "Animalia", "class": "Mammalia"},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("matchType") in ("EXACT", "FUZZY") and "usageKey" in data:
            print(
                f"  [GBIF] Matched '{species_name}' -> "
                f"{data.get('canonicalName', species_name)} (key={data['usageKey']}, "
                f"match={data['matchType']})"
            )
            return data["usageKey"]
        print(f"  [WARN] No GBIF taxon key for '{species_name}' (matchType={data.get('matchType')})")
        return None
    except requests.RequestException as exc:
        print(f"  [WARN] GBIF species lookup failed for '{species_name}': {exc}")
        return None


def fetch_occurrences_by_taxon_key(
    taxon_key: int,
    limit: int = 500,
    species_name: str = "",
) -> list[dict[str, Any]]:
    """
    Page through the GBIF occurrence search API for a taxon key.

    Returns a list of raw occurrence dicts filtered to:
    - hasCoordinate=true
    - Records without disqualifying coordinate issues
    """
    records: list[dict[str, Any]] = []
    offset = 0
    fetched = 0
    label = species_name or f"taxonKey={taxon_key}"

    while fetched < limit:
        page_size = min(GBIF_PAGE_LIMIT, limit - fetched)
        params = {
            "taxonKey": taxon_key,
            "hasCoordinate": "true",
            "hasGeospatialIssue": "false",
            "limit": page_size,
            "offset": offset,
        }
        try:
            resp = requests.get(GBIF_OCCURRENCE_URL, params=params, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
        except requests.RequestException as exc:
            print(f"  [WARN] GBIF request failed (offset={offset}): {exc}")
            break

        data = resp.json()
        results = data.get("results", [])
        if not results:
            break

        for rec in results:
            lat = rec.get("decimalLatitude")
            lon = rec.get("decimalLongitude")
            if lat is None or lon is None:
                continue
            issues_raw = rec.get("issues", [])
            if isinstance(issues_raw, str):
                issues_raw = [i.strip() for i in issues_raw.split(",")]
            if DISQUALIFYING_ISSUES.intersection(issues_raw):
                continue
            records.append(rec)

        fetched += len(results)
        total = data.get("count", "?")
        print(f"  [GBIF] {label}: fetched {len(records)} / min({limit}, {total})")

        if data.get("endOfRecords", False) or len(results) < page_size:
            break
        offset += page_size
        time.sleep(REQUEST_SLEEP)

    return records


def fetch_occurrences_by_name(
    species_name: str,
    limit: int = 500,
) -> tuple[list[dict[str, Any]], int | None]:
    """
    Convenience wrapper: resolve name → taxon key, then fetch occurrences.

    Returns (records, taxon_key_or_None).
    """
    taxon_key = lookup_gbif_taxon_key(species_name)
    if taxon_key is None:
        return [], None
    time.sleep(REQUEST_SLEEP)
    records = fetch_occurrences_by_taxon_key(taxon_key, limit=limit, species_name=species_name)
    return records, taxon_key


# ---------------------------------------------------------------------------
# Name harmonization via DuckDB in-process join
# ---------------------------------------------------------------------------

def harmonize_names_in_db(
    con: duckdb.DuckDBPyConnection,
    reported_names: list[str],
) -> dict[str, dict[str, Any]]:
    """
    Join reported_names against species + synonyms tables in DuckDB.

    Returns a dict mapping each input name to:
        {mdd_species_id, mdd_sci_name, mdd_match_type}
    """
    if not reported_names:
        return {}

    import pandas as pd

    names_df = pd.DataFrame({"input_name": list(set(reported_names))})
    con.register("_harm_names", names_df)

    sql = """
    WITH normalised AS (
        SELECT
            input_name,
            REPLACE(input_name, ' ', '_') AS name_us,
            REPLACE(input_name, '_', ' ') AS name_sp
        FROM _harm_names
    ),
    direct_match AS (
        SELECT
            n.input_name,
            sp.species_id   AS mdd_species_id,
            sp.sci_name     AS mdd_sci_name,
            'exact'         AS mdd_match_type
        FROM normalised n
        JOIN species sp
          ON  sp.sci_name = n.name_us
           OR sp.sci_name = n.name_sp
           OR sp.sci_name = n.input_name
    ),
    synonym_match AS (
        SELECT
            n.input_name,
            sp.species_id   AS mdd_species_id,
            sp.sci_name     AS mdd_sci_name,
            'synonym'       AS mdd_match_type
        FROM normalised n
        JOIN synonyms syn
          ON  syn.original_combination = n.name_us
           OR syn.original_combination = n.name_sp
           OR syn.original_combination = n.input_name
           OR syn.normalized_original_combination = n.name_us
           OR syn.normalized_original_combination = n.name_sp
        JOIN species sp ON syn.species_id = sp.species_id
    ),
    combined AS (
        SELECT * FROM direct_match
        UNION ALL
        SELECT sm.* FROM synonym_match sm
        WHERE sm.input_name NOT IN (SELECT input_name FROM direct_match)
    )
    SELECT DISTINCT ON (input_name)
        input_name,
        mdd_species_id,
        mdd_sci_name,
        mdd_match_type
    FROM combined
    ORDER BY input_name, mdd_match_type
    """

    rows = con.execute(sql).fetchall()
    result: dict[str, dict[str, Any]] = {}
    for input_name, species_id, sci_name, match_type in rows:
        result[input_name] = {
            "mdd_species_id": species_id,
            "mdd_sci_name": sci_name,
            "mdd_match_type": match_type,
        }
    # Mark unmatched names explicitly
    for name in reported_names:
        if name not in result:
            result[name] = {
                "mdd_species_id": None,
                "mdd_sci_name": None,
                "mdd_match_type": "unmatched",
            }
    con.unregister("_harm_names")
    return result


# ---------------------------------------------------------------------------
# DuckDB ingestion
# ---------------------------------------------------------------------------

def ensure_observations_table(con: duckdb.DuckDBPyConnection) -> None:
    """Create observations table and spatial extension if not present."""
    con.execute("INSTALL spatial; LOAD spatial;")
    con.execute(CREATE_OBSERVATIONS_SQL)
    for stmt in CREATE_OBSERVATIONS_INDEX_SQL.strip().split(";"):
        stmt = stmt.strip()
        if stmt:
            try:
                con.execute(stmt)
            except Exception:
                pass  # index may already exist


def _safe_date(val: Any) -> str | None:
    """Return YYYY-MM-DD string or None from a GBIF eventDate value."""
    if not val:
        return None
    s = str(val)
    # GBIF dates can be YYYY, YYYY-MM, or YYYY-MM-DD
    parts = s.split("-")
    if len(parts) == 1 and len(parts[0]) == 4:
        return f"{parts[0]}-01-01"
    if len(parts) == 2:
        return f"{parts[0]}-{parts[1]}-01"
    return s[:10]  # truncate to YYYY-MM-DD


def records_to_rows(
    records: list[dict[str, Any]],
    harmonize_map: dict[str, dict[str, Any]],
) -> list[tuple]:
    """Convert GBIF raw records to tuples matching the observations schema."""
    rows = []
    for rec in records:
        obs_id = rec.get("key")
        if obs_id is None:
            continue
        lat = rec.get("decimalLatitude")
        lon = rec.get("decimalLongitude")
        if lat is None or lon is None:
            continue

        reported = rec.get("species") or rec.get("scientificName") or ""
        harm = harmonize_map.get(reported, {})

        issues_raw = rec.get("issues", [])
        if isinstance(issues_raw, list):
            issues_str = ";".join(issues_raw)
        else:
            issues_str = str(issues_raw)

        rows.append((
            int(obs_id),                          # obs_id
            int(obs_id),                          # gbif_id
            reported,                              # reported_name
            harm.get("mdd_species_id"),            # mdd_species_id
            harm.get("mdd_sci_name"),              # mdd_sci_name
            harm.get("mdd_match_type", "unmatched"),  # mdd_match_type
            float(lat),                            # latitude
            float(lon),                            # longitude
            _safe_date(rec.get("eventDate")),      # event_date
            rec.get("datasetName"),                # dataset_name
            rec.get("datasetKey"),                 # dataset_key
            rec.get("occurrenceStatus"),           # occurrence_status
            rec.get("basisOfRecord"),              # basis_of_record
            rec.get("countryCode"),                # country_code
            rec.get("stateProvince"),              # state_province
            rec.get("locality"),                   # locality
            rec.get("coordinateUncertaintyInMeters"),  # coordinate_uncertainty_m
            issues_str,                            # issues
            "GBIF",                                # source
        ))
    return rows


def load_records_into_db(
    con: duckdb.DuckDBPyConnection,
    rows: list[tuple],
    replace: bool = False,
) -> int:
    """
    Upsert observation rows into DuckDB observations table.

    Uses INSERT OR REPLACE (upsert by obs_id) so repeat imports are idempotent.
    Returns count of rows inserted/updated.
    """
    if not rows:
        return 0

    if replace:
        # Delete existing records for the affected obs_ids before inserting
        ids = [r[0] for r in rows]
        con.execute(
            f"DELETE FROM observations WHERE obs_id IN ({','.join(str(i) for i in ids)})"
        )

    import pandas as pd
    df = pd.DataFrame(rows, columns=[
        "obs_id", "gbif_id", "reported_name", "mdd_species_id", "mdd_sci_name",
        "mdd_match_type", "latitude", "longitude",
        "event_date", "dataset_name", "dataset_key", "occurrence_status",
        "basis_of_record", "country_code", "state_province", "locality",
        "coordinate_uncertainty_m", "issues", "source",
    ])

    # Remove duplicates within batch (keep last)
    df = df.drop_duplicates(subset=["obs_id"], keep="last")

    # Register as temp view for DuckDB
    con.register("_obs_batch", df)

    # Insert geometry via ST_Point; skip rows that already exist (idempotent)
    con.execute("""
        INSERT OR IGNORE INTO observations
        SELECT
            obs_id, gbif_id, reported_name,
            mdd_species_id, mdd_sci_name, mdd_match_type,
            latitude, longitude,
            ST_Point(longitude, latitude) AS geom,
            TRY_CAST(event_date AS DATE),
            dataset_name, dataset_key, occurrence_status,
            basis_of_record, country_code, state_province, locality,
            CAST(coordinate_uncertainty_m AS DOUBLE),
            issues, source,
            CURRENT_TIMESTAMP
        FROM _obs_batch
    """)
    con.unregister("_obs_batch")
    return len(df)


# ---------------------------------------------------------------------------
# GeoParquet export
# ---------------------------------------------------------------------------

def export_observations_geoparquet(
    con: duckdb.DuckDBPyConnection,
    output_path: Path,
    species_filter: str | None = None,
) -> int:
    """
    Export observations table (or subset) to GeoParquet.

    CRS: WGS84 / EPSG:4326
    Returns row count exported.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out_str = str(output_path).replace("\\", "/")

    where = ""
    if species_filter:
        norm = species_filter.replace(" ", "_")
        where = f"WHERE mdd_sci_name = '{norm}' OR reported_name ILIKE '%{species_filter}%'"

    sql = f"""
    COPY (
        SELECT
            obs_id,
            gbif_id,
            reported_name,
            mdd_species_id,
            mdd_sci_name,
            mdd_match_type,
            latitude,
            longitude,
            geom,
            event_date,
            dataset_name,
            occurrence_status,
            basis_of_record,
            country_code,
            coordinate_uncertainty_m,
            issues,
            source
        FROM observations
        {where}
        ORDER BY mdd_sci_name, event_date
    )
    TO '{out_str}'
    WITH (FORMAT PARQUET, COMPRESSION ZSTD);
    """
    con.execute(sql)
    count = con.execute(
        f"SELECT COUNT(*) FROM observations {where}"
    ).fetchone()[0]
    return count


# ---------------------------------------------------------------------------
# MDD batch mode helpers
# ---------------------------------------------------------------------------

def get_species_from_mdd(
    con: duckdb.DuckDBPyConnection,
    family: str | None = None,
    order: str | None = None,
) -> list[str]:
    """
    Query MDD species table for names to import from GBIF.

    Returns list of space-separated scientific names (GBIF expects spaces).
    """
    conditions = []
    params = []
    if family:
        conditions.append("family ILIKE ?")
        params.append(f"%{family}%")
    if order:
        conditions.append('"order" ILIKE ?')
        params.append(f"%{order}%")

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = f"""
        SELECT REPLACE(sci_name, '_', ' ') AS name
        FROM species
        {where}
        ORDER BY family, sci_name
    """
    rows = con.execute(sql, params).fetchall()
    return [r[0] for r in rows]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument(
        "--species", type=str,
        help='Species name to fetch (e.g. "Ursus arctos")',
    )
    source_group.add_argument(
        "--taxon-key", type=int,
        help="GBIF taxon key (e.g. 2433459 for Ursus arctos)",
    )
    source_group.add_argument(
        "--from-mdd", action="store_true",
        help="Batch mode: import species from MDD (use with --family or --order)",
    )

    parser.add_argument(
        "--family", type=str, default=None,
        help="Filter by MDD family (used with --from-mdd)",
    )
    parser.add_argument(
        "--order", type=str, default=None,
        help="Filter by MDD order (used with --from-mdd)",
    )
    parser.add_argument(
        "--limit", type=int, default=500,
        help="Max occurrences per species (default: 500)",
    )
    parser.add_argument(
        "--limit-per-species", type=int, default=100,
        help="Per-species limit in --from-mdd batch mode (default: 100)",
    )
    parser.add_argument(
        "--db", type=Path, default=DB_PATH,
        help=f"DuckDB path (default: {DB_PATH})",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=GEOPARQUET_DIR,
        help=f"GeoParquet output directory (default: {GEOPARQUET_DIR})",
    )
    parser.add_argument(
        "--replace", action="store_true",
        help="Replace existing records (default: skip duplicates)",
    )
    parser.add_argument(
        "--no-export", action="store_true",
        help="Skip GeoParquet export after import",
    )

    args = parser.parse_args()

    db_path = Path(args.db).resolve()
    if not db_path.exists():
        print(
            f"[ERROR] Database not found at {db_path}\n"
            "  Run: python mdd_project/scripts/setup_database.py",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"[INFO] Database : {db_path}")
    print(f"[INFO] Output   : {args.output_dir}")

    with duckdb.connect(str(db_path)) as con:
        # Ensure spatial extension and table exist
        ensure_observations_table(con)

        total_inserted = 0

        if args.from_mdd:
            # ---- Batch mode: import all species from a family/order ----
            names = get_species_from_mdd(con, family=args.family, order=args.order)
            if not names:
                print("[WARN] No species found in MDD for given --family/--order filter.")
                sys.exit(0)

            print(
                f"[INFO] Batch import: {len(names)} species "
                f"(family={args.family}, order={args.order}), "
                f"limit={args.limit_per_species} each"
            )
            for i, name in enumerate(names, 1):
                print(f"\n[{i}/{len(names)}] {name}")
                records, _key = fetch_occurrences_by_name(name, limit=args.limit_per_species)
                if not records:
                    print(f"  [INFO] No records returned for '{name}'")
                    continue

                reported_names = list({
                    r.get("species") or r.get("scientificName") or "" for r in records
                })
                harm_map = harmonize_names_in_db(con, reported_names)
                rows = records_to_rows(records, harm_map)
                n = load_records_into_db(con, rows, replace=args.replace)
                total_inserted += n
                print(f"  [DB] {n} rows upserted")
                time.sleep(REQUEST_SLEEP)

        elif args.taxon_key:
            # ---- Single taxon key mode ----
            print(f"[INFO] Fetching occurrences for taxonKey={args.taxon_key}, limit={args.limit}")
            records = fetch_occurrences_by_taxon_key(
                args.taxon_key, limit=args.limit, species_name=f"taxonKey={args.taxon_key}"
            )
            if not records:
                print("[INFO] No records returned.")
            else:
                reported_names = list({
                    r.get("species") or r.get("scientificName") or "" for r in records
                })
                harm_map = harmonize_names_in_db(con, reported_names)
                rows = records_to_rows(records, harm_map)
                total_inserted = load_records_into_db(con, rows, replace=args.replace)

        else:
            # ---- Single species by name ----
            species = args.species or ""
            if not species:
                parser.error("Provide one of --species, --taxon-key, or --from-mdd")

            print(f"[INFO] Fetching occurrences for '{species}', limit={args.limit}")
            records, taxon_key = fetch_occurrences_by_name(species, limit=args.limit)
            if not records:
                print("[INFO] No records returned.")
            else:
                reported_names = list({
                    r.get("species") or r.get("scientificName") or "" for r in records
                })
                harm_map = harmonize_names_in_db(con, reported_names)

                # Print harmonization summary
                match_types = [v["mdd_match_type"] for v in harm_map.values()]
                print(
                    f"[INFO] Name harmonization: "
                    f"{match_types.count('exact')} exact, "
                    f"{match_types.count('synonym')} synonym, "
                    f"{match_types.count('unmatched')} unmatched"
                )

                rows = records_to_rows(records, harm_map)
                total_inserted = load_records_into_db(con, rows, replace=args.replace)

        # ---- Summary ----
        total_in_db = con.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
        print(f"\n[INFO] Rows upserted this run : {total_inserted:,}")
        print(f"[INFO] Total rows in DB       : {total_in_db:,}")

        # ---- GeoParquet export ----
        if not args.no_export and total_in_db > 0:
            out_path = Path(args.output_dir) / "observations.parquet"
            print(f"\n[INFO] Exporting GeoParquet -> {out_path}")
            n_exported = export_observations_geoparquet(con, out_path)
            print(f"[INFO] GeoParquet rows exported: {n_exported:,}")
        else:
            print("[INFO] Skipping GeoParquet export.")

    print("\n[INFO] Done.")


if __name__ == "__main__":
    main()
