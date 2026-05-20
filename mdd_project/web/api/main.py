"""
MDD FastAPI — lightweight REST API over mdd.duckdb

Run:
    cd mdd_project
    uvicorn web.api.main:app --reload --port 8000

Docs: http://localhost:8000/docs
"""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any

import duckdb
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, Response

# ---------------------------------------------------------------------------
# Database path (resolved relative to this file's location)
# ---------------------------------------------------------------------------
_API_DIR = Path(__file__).resolve().parent
DB_PATH = _API_DIR.parent.parent / "data" / "processed" / "mdd.duckdb"

app = FastAPI(
    title="Mammal Diversity Database API",
    description=(
        "Query MDD v2.4 taxonomy, synonyms, and type localities. "
        "Data source: https://www.mammaldiversity.org/"
    ),
    version="0.1.0",
)


def _get_conn() -> duckdb.DuckDBPyConnection:
    """Return a read-only DuckDB connection. Raises 503 if DB is missing."""
    if not DB_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail=(
                f"Database not found at {DB_PATH}. "
                "Run: python mdd_project/scripts/setup_database.py"
            ),
        )
    return duckdb.connect(str(DB_PATH), read_only=True)


def _rows_to_dicts(conn: duckdb.DuckDBPyConnection, sql: str, params: list | None = None) -> list[dict]:
    """Execute SQL and return list of row dicts using column names from cursor."""
    cur = conn.execute(sql, params or [])
    columns = [d[0] for d in cur.description]
    return [dict(zip(columns, row)) for row in cur.fetchall()]


# Match type_voucher catalog numbers to institution abbreviations (longest prefix wins).
_MUSEUM_MATCH = """
    s.type_voucher IS NOT NULL
    AND TRIM(s.type_voucher) <> ''
    AND UPPER(TRIM(s.type_voucher)) LIKE UPPER(tsi.abbreviation) || '%'
"""

_SPECIES_WITH_MUSEUM_CTE = f"""
species_with_museum AS (
    SELECT
        s.species_id,
        s.sci_name,
        REPLACE(s.sci_name, '_', ' ') AS sci_name_space,
        s.main_common_name,
        s."order",
        s.family,
        s.genus,
        s.type_voucher,
        s.type_kind,
        s.type_locality,
        s.type_lat,
        s.type_lon,
        (
            SELECT tsi.abbreviation
            FROM type_specimen_institutions tsi
            WHERE {_MUSEUM_MATCH}
            ORDER BY LENGTH(tsi.abbreviation) DESC
            LIMIT 1
        ) AS museum_abbreviation,
        (
            SELECT tsi.full_name
            FROM type_specimen_institutions tsi
            WHERE {_MUSEUM_MATCH}
            ORDER BY LENGTH(tsi.abbreviation) DESC
            LIMIT 1
        ) AS museum_name,
        (
            SELECT tsi.city_and_country
            FROM type_specimen_institutions tsi
            WHERE {_MUSEUM_MATCH}
            ORDER BY LENGTH(tsi.abbreviation) DESC
            LIMIT 1
        ) AS museum_location,
        (
            SELECT TRIM(regexp_extract(tsi.city_and_country, '[^,]+$', 0))
            FROM type_specimen_institutions tsi
            WHERE {_MUSEUM_MATCH}
              AND tsi.city_and_country IS NOT NULL
              AND TRIM(tsi.city_and_country) <> ''
              AND UPPER(TRIM(tsi.city_and_country)) <> 'NA'
            ORDER BY LENGTH(tsi.abbreviation) DESC
            LIMIT 1
        ) AS museum_country
    FROM species s
    WHERE s.type_voucher IS NOT NULL AND TRIM(s.type_voucher) <> ''
)
"""

_MUSEUM_ABBREV_SUBQUERY = f"""(
    SELECT tsi.abbreviation
    FROM type_specimen_institutions tsi
    WHERE {_MUSEUM_MATCH}
    ORDER BY LENGTH(tsi.abbreviation) DESC
    LIMIT 1
)"""

_MUSEUM_COUNTRY_SUBQUERY = f"""(
    SELECT TRIM(regexp_extract(tsi.city_and_country, '[^,]+$', 0))
    FROM type_specimen_institutions tsi
    WHERE {_MUSEUM_MATCH}
      AND tsi.city_and_country IS NOT NULL
      AND TRIM(tsi.city_and_country) <> ''
      AND UPPER(TRIM(tsi.city_and_country)) <> 'NA'
    ORDER BY LENGTH(tsi.abbreviation) DESC
    LIMIT 1
)"""


# ---------------------------------------------------------------------------
# GET /species
# List and filter species from the taxonomy schema
# ---------------------------------------------------------------------------
@app.get("/species", summary="List or search species")
def list_species(
    q: str | None = Query(None, description="Search scientific or common name (partial, case-insensitive)"),
    order: str | None = Query(None, description="Filter by order (e.g. 'Primates')"),
    family: str | None = Query(None, description="Filter by family (e.g. 'Galagidae')"),
    limit: int = Query(100, ge=1, le=5000, description="Max rows to return"),
) -> list[dict[str, Any]]:
    """Return accepted MDD species, optionally filtered by taxonomic rank."""
    conditions: list[str] = []
    params: list[Any] = []

    if q:
        needle = f"%{q.strip()}%"
        conditions.append(
            "(sci_name ILIKE ? OR REPLACE(sci_name, '_', ' ') ILIKE ? OR main_common_name ILIKE ?)"
        )
        params.extend([needle, needle, needle])
    if order:
        conditions.append('"order" ILIKE ?')
        params.append(f"%{order}%")
    if family:
        conditions.append("family ILIKE ?")
        params.append(f"%{family}%")

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = f"""
        SELECT
            species_id,
            sci_name,
            REPLACE(sci_name, '_', ' ')   AS sci_name_space,
            main_common_name,
            "order",
            family,
            genus,
            specific_epithet,
            authority_author,
            authority_year,
            iucn_status,
            extinct,
            domestic,
            country_distribution,
            continent_distribution,
            biogeographic_realm,
            type_lat,
            type_lon
        FROM species
        {where}
        ORDER BY "order", family, sci_name
        LIMIT ?
    """
    params.append(limit)

    with _get_conn() as conn:
        return _rows_to_dicts(conn, sql, params)


# ---------------------------------------------------------------------------
# GET /species/{name}
# Single species record — accepts "Ursus_arctos" or "Ursus arctos"
# ---------------------------------------------------------------------------
@app.get("/species/{name}", summary="Get species by scientific name")
def get_species(name: str) -> dict[str, Any]:
    """
    Fetch a single species record. Accepts the scientific name with either
    underscores or spaces (e.g. ``Ursus_arctos`` or ``Ursus arctos``).

    Returns ``sci_name_space`` (computed) in addition to all stored columns
    so the frontend can display and use the space-separated name directly.
    """
    normalised = name.replace(" ", "_")
    sql = """
        SELECT
            *,
            REPLACE(sci_name, '_', ' ') AS sci_name_space
        FROM species
        WHERE sci_name = ?
           OR sci_name = ?
        LIMIT 1
    """
    with _get_conn() as conn:
        rows = _rows_to_dicts(conn, sql, [normalised, name.replace("_", " ")])
    if not rows:
        raise HTTPException(status_code=404, detail=f"Species '{name}' not found in MDD v2.4")
    return rows[0]


# ---------------------------------------------------------------------------
# GET /synonyms/{name}
# All synonyms for a given accepted species name
# ---------------------------------------------------------------------------
@app.get("/synonyms/{name}", summary="Get synonyms for a species")
def get_synonyms(name: str) -> list[dict[str, Any]]:
    """
    Return all nomenclatural synonyms associated with an accepted MDD species name.
    Accepts underscore or space format.
    """
    normalised = name.replace(" ", "_")
    sql = """
        SELECT
            syn_id,
            accepted_sci_name,
            original_combination,
            normalized_original_combination,
            root_name,
            author,
            year,
            nomenclature_status,
            validity,
            type_lat,
            type_lon,
            type_country,
            authority_citation
        FROM synonyms
        WHERE accepted_sci_name = ?
           OR accepted_sci_name = ?
        ORDER BY validity, year
    """
    with _get_conn() as conn:
        return _rows_to_dicts(conn, sql, [normalised, name.replace("_", " ")])


# ---------------------------------------------------------------------------
# GET /occurrences/{species}
# Query the observations table (populated by scripts/gbif_import.py)
# ---------------------------------------------------------------------------
@app.get("/occurrences/{species}", summary="Get GBIF occurrence records for a species")
def get_occurrences(
    species: str,
    limit: int = Query(500, ge=1, le=5000, description="Max records to return"),
    matched_only: bool = Query(False, description="Return only MDD-matched records"),
) -> JSONResponse:
    """
    Return occurrence records from the ``observations`` table for a species.

    The ``observations`` table is populated by running::

        python mdd_project/scripts/gbif_import.py --species "Ursus arctos" --limit 500

    Accepts species name with underscores or spaces.
    Returns GeoJSON-compatible feature collection.
    """
    normalised = species.replace(" ", "_")

    # Check whether observations table exists
    with _get_conn() as conn:
        try:
            table_exists = conn.execute(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_name = 'observations'"
            ).fetchone()[0]
        except Exception:
            table_exists = 0

        if not table_exists:
            return JSONResponse(
                status_code=200,
                content={
                    "species": species,
                    "type": "FeatureCollection",
                    "features": [],
                    "meta": {
                        "message": (
                            "observations table not found — run the GBIF import pipeline first: "
                            "python mdd_project/scripts/gbif_import.py "
                            f'--species "{species.replace("_", " ")}" --limit 500'
                        )
                    },
                },
            )

        matched_filter = " AND mdd_match_type != 'unmatched'" if matched_only else ""
        sql = f"""
            SELECT
                obs_id,
                gbif_id,
                reported_name,
                mdd_species_id,
                mdd_sci_name,
                mdd_match_type,
                latitude,
                longitude,
                event_date::VARCHAR AS event_date,
                dataset_name,
                occurrence_status,
                basis_of_record,
                country_code,
                coordinate_uncertainty_m,
                issues,
                source
            FROM observations
            WHERE (
                mdd_sci_name = ?
                OR mdd_sci_name = ?
                OR reported_name ILIKE ?
            )
            {matched_filter}
            ORDER BY event_date DESC NULLS LAST
            LIMIT ?
        """
        rows = _rows_to_dicts(
            conn, sql,
            [normalised, species.replace("_", " "), f"%{species.replace('_', ' ')}%", limit]
        )

    # Build minimal GeoJSON FeatureCollection
    features = [
        {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [row["longitude"], row["latitude"]],
            },
            "properties": {k: v for k, v in row.items() if k not in ("latitude", "longitude")},
        }
        for row in rows
        if row.get("latitude") is not None and row.get("longitude") is not None
    ]

    return JSONResponse(
        status_code=200,
        content={
            "species": species,
            "type": "FeatureCollection",
            "features": features,
            "meta": {"count": len(features), "limit": limit},
        },
    )


# ---------------------------------------------------------------------------
# GET /taxonomy/search
# Autocomplete search for genera or families (returns name + species count)
# ---------------------------------------------------------------------------
@app.get("/taxonomy/search", summary="Search genera or families")
def taxonomy_search(
    q: str = Query(..., min_length=1, description="Partial name (case-insensitive)"),
    rank: str = Query("genus", description="Taxonomic rank: 'genus' or 'family'"),
    limit: int = Query(15, ge=1, le=100),
) -> list[dict[str, Any]]:
    """
    Return distinct genera or families whose name contains ``q`` (ILIKE),
    together with the count of accepted species in each.

    Example::

        GET /taxonomy/search?q=gala&rank=genus
        GET /taxonomy/search?q=ursid&rank=family
    """
    if rank not in ("genus", "family"):
        from fastapi import HTTPException as _HTTPException
        raise _HTTPException(status_code=422, detail="rank must be 'genus' or 'family'")

    col = "genus" if rank == "genus" else "family"
    sql = f"""
        SELECT
            {col} AS name,
            COUNT(*) AS species_count
        FROM species
        WHERE {col} ILIKE ?
        GROUP BY {col}
        ORDER BY {col}
        LIMIT ?
    """
    with _get_conn() as conn:
        rows = _rows_to_dicts(conn, sql, [f"%{q}%", limit])
    return [{"rank": rank, "name": r["name"], "species_count": r["species_count"]} for r in rows]


# ---------------------------------------------------------------------------
# Type locality coverage (museum / country statistics & export)
# ---------------------------------------------------------------------------
def _table_exists(conn: duckdb.DuckDBPyConnection, name: str) -> bool:
    count = conn.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
        [name],
    ).fetchone()[0]
    return count > 0


@app.get("/type-localities/coverage/summary", summary="Global type specimen coverage summary")
def type_locality_coverage_summary() -> dict[str, Any]:
    """Counts for comparing type vouchers, geocoded localities, and museum matches."""
    sql = f"""
        WITH {_SPECIES_WITH_MUSEUM_CTE}
        SELECT
            (SELECT COUNT(*) FROM species) AS total_species,
            (SELECT COUNT(*) FROM species
             WHERE type_voucher IS NOT NULL AND TRIM(type_voucher) <> '') AS with_type_voucher,
            (SELECT COUNT(*) FROM species
             WHERE type_locality IS NOT NULL AND TRIM(type_locality) <> '') AS with_type_locality_text,
            (SELECT COUNT(*) FROM species
             WHERE type_lat IS NOT NULL AND type_lon IS NOT NULL) AS geocoded,
            (SELECT COUNT(*) FROM species_with_museum) AS voucher_with_museum_match,
            (SELECT COUNT(*) FROM species_with_museum
             WHERE museum_abbreviation IS NULL) AS voucher_unmatched_museum,
            (SELECT COUNT(*) FROM species_with_museum
             WHERE type_lat IS NOT NULL AND type_lon IS NOT NULL) AS voucher_geocoded,
            (SELECT COUNT(*) FROM species_with_museum
             WHERE type_lat IS NULL OR type_lon IS NULL) AS voucher_missing_geolocation
    """
    with _get_conn() as conn:
        row = _rows_to_dicts(conn, sql)[0]
        if _table_exists(conn, "estimated_type_localities"):
            est = conn.execute(
                """
                SELECT COUNT(*) FROM estimated_type_localities e
                JOIN species s ON s.species_id = e.species_id
                WHERE (s.type_lat IS NULL OR s.type_lon IS NULL)
                """
            ).fetchone()[0]
            row["estimated_on_map"] = int(est)
        else:
            row["estimated_on_map"] = 0
    return row


@app.get("/type-localities/coverage/countries", summary="Type voucher counts by museum country")
def type_locality_coverage_countries() -> list[dict[str, Any]]:
    """Aggregate species with type vouchers by country of the holding museum."""
    sql = f"""
        WITH {_SPECIES_WITH_MUSEUM_CTE}
        SELECT
            museum_country AS country,
            COUNT(DISTINCT museum_abbreviation) AS museum_count,
            COUNT(*) AS with_type_voucher,
            COUNT(*) FILTER (
                WHERE type_lat IS NOT NULL AND type_lon IS NOT NULL
            ) AS geocoded,
            COUNT(*) FILTER (
                WHERE type_lat IS NULL OR type_lon IS NULL
            ) AS missing_geolocation
        FROM species_with_museum
        WHERE museum_country IS NOT NULL AND TRIM(museum_country) <> ''
        GROUP BY museum_country
        ORDER BY country
    """
    with _get_conn() as conn:
        return _rows_to_dicts(conn, sql)


@app.get("/type-localities/coverage/museums", summary="Type voucher counts by museum")
def type_locality_coverage_museums(
    country: str | None = Query(None, description="Filter by museum country (from institution metadata)"),
) -> list[dict[str, Any]]:
    """Per-museum counts of type vouchers and how many have geocoded type localities in MDD."""
    conditions = ["museum_abbreviation IS NOT NULL"]
    params: list[Any] = []
    if country:
        conditions.append("museum_country ILIKE ?")
        params.append(country)

    where = "WHERE " + " AND ".join(conditions)
    sql = f"""
        WITH {_SPECIES_WITH_MUSEUM_CTE}
        SELECT
            museum_abbreviation AS abbreviation,
            MAX(museum_name) AS full_name,
            MAX(museum_location) AS city_and_country,
            MAX(museum_country) AS country,
            COUNT(*) AS with_type_voucher,
            COUNT(*) FILTER (
                WHERE type_lat IS NOT NULL AND type_lon IS NOT NULL
            ) AS geocoded,
            COUNT(*) FILTER (
                WHERE type_lat IS NULL OR type_lon IS NULL
            ) AS missing_geolocation
        FROM species_with_museum
        {where}
        GROUP BY museum_abbreviation
        ORDER BY full_name, abbreviation
    """
    with _get_conn() as conn:
        return _rows_to_dicts(conn, sql, params)


@app.get("/type-localities/coverage/export", summary="Export species missing type locality coordinates")
def type_locality_coverage_export(
    museum: str | None = Query(None, description="Museum abbreviation (e.g. USNM, BMNH)"),
    country: str | None = Query(None, description="Museum country (holding institution)"),
    missing_geolocation: bool = Query(
        True,
        description="If true, only species without type_lat/type_lon in MDD",
    ),
) -> Response:
    """
    Download CSV of species with type vouchers, optionally filtered by museum or country.

    Intended for museums to review specimens that lack geocoded type localities in MDD.
    """
    if not museum and not country:
        raise HTTPException(
            status_code=422,
            detail="Provide museum (abbreviation) or country to export.",
        )

    conditions = ["1=1"]
    params: list[Any] = []
    if museum:
        conditions.append("museum_abbreviation ILIKE ?")
        params.append(museum.strip())
    if country:
        conditions.append("museum_country ILIKE ?")
        params.append(country.strip())
    if missing_geolocation:
        conditions.append("(type_lat IS NULL OR type_lon IS NULL)")

    where = " AND ".join(conditions)
    sql = f"""
        WITH {_SPECIES_WITH_MUSEUM_CTE}
        SELECT
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
            museum_country
        FROM species_with_museum
        WHERE {where}
        ORDER BY museum_abbreviation, family, sci_name
    """
    with _get_conn() as conn:
        rows = _rows_to_dicts(conn, sql, params)

    if not rows:
        raise HTTPException(status_code=404, detail="No matching species for export.")

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)

    label = (museum or country or "export").replace(" ", "_")
    filename = f"mdd_type_specimens_missing_coords_{label}.csv"
    return Response(
        content=buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# GET /type-localities
# Export type localities as GeoJSON FeatureCollection for the web map
# ---------------------------------------------------------------------------
@app.get("/type-localities", summary="Get type locality points for web map")
def get_type_localities(
    order: str | None = Query(None, description="Filter by order"),
    family: str | None = Query(None, description="Filter by family"),
    genus: str | None = Query(None, description="Filter by genus"),
    museum: str | None = Query(
        None, description="Filter by holding museum abbreviation (e.g. USNM, BMNH)"
    ),
    country: str | None = Query(
        None, description="Filter by holding museum country (from institution metadata)"
    ),
    species: str | None = Query(
        None,
        description=(
            "Filter to a single accepted species by scientific name "
            "(spaces or underscores accepted). Returns 0–1 features."
        ),
    ),
    limit: int = Query(2000, ge=1, le=10000),
) -> JSONResponse:
    """
    Return type localities as a GeoJSON FeatureCollection.

    These are the collection localities of the name-bearing type specimens —
    NOT occurrence records or range centroids.

    Pass ``species`` to retrieve only the type locality for a single accepted
    species (at most one point per species in MDD).
    """
    conditions = ["type_lat IS NOT NULL", "type_lon IS NOT NULL"]
    params: list[Any] = []

    if species:
        # Accept both "Genus species" and "Genus_species" spellings
        normalised = species.replace(" ", "_")
        space_form = species.replace("_", " ")
        conditions.append("(sci_name = ? OR sci_name = ?)")
        params.extend([normalised, space_form])
    if order:
        conditions.append('"order" ILIKE ?')
        params.append(f"%{order}%")
    if family:
        conditions.append("family ILIKE ?")
        params.append(f"%{family}%")
    if genus:
        conditions.append("genus ILIKE ?")
        params.append(f"%{genus}%")
    if museum:
        conditions.append(f"{_MUSEUM_ABBREV_SUBQUERY} ILIKE ?")
        params.append(museum.strip())
    if country:
        conditions.append(f"{_MUSEUM_COUNTRY_SUBQUERY} ILIKE ?")
        params.append(country.strip())

    where = "WHERE " + " AND ".join(conditions)
    sql = f"""
        SELECT
            s.species_id,
            s.sci_name,
            REPLACE(s.sci_name, '_', ' ') AS sci_name_space,
            s.main_common_name,
            s."order",
            s.family,
            s.iucn_status,
            s.extinct,
            s.type_lat,
            s.type_lon,
            s.type_locality,
            s.type_voucher,
            s.type_kind,
            s.type_voucher_uris,
            s.country_distribution AS type_country,
            (
                SELECT tsi.full_name
                FROM type_specimen_institutions tsi
                WHERE {_MUSEUM_MATCH}
                ORDER BY LENGTH(tsi.abbreviation) DESC
                LIMIT 1
            ) AS museum_name,
            (
                SELECT tsi.abbreviation
                FROM type_specimen_institutions tsi
                WHERE {_MUSEUM_MATCH}
                ORDER BY LENGTH(tsi.abbreviation) DESC
                LIMIT 1
            ) AS museum_abbreviation,
            (
                SELECT tsi.city_and_country
                FROM type_specimen_institutions tsi
                WHERE {_MUSEUM_MATCH}
                ORDER BY LENGTH(tsi.abbreviation) DESC
                LIMIT 1
            ) AS museum_location
        FROM species s
        {where}
        ORDER BY s."order", s.family, s.sci_name
        LIMIT ?
    """
    params.append(limit)

    with _get_conn() as conn:
        rows = _rows_to_dicts(conn, sql, params)

    features = [
        {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [row["type_lon"], row["type_lat"]],
            },
            "properties": {k: v for k, v in row.items() if k not in ("type_lat", "type_lon")},
        }
        for row in rows
    ]

    return JSONResponse(
        status_code=200,
        content={
            "type": "FeatureCollection",
            "features": features,
            "meta": {"count": len(features), "limit": limit},
        },
    )


@app.get("/type-localities/estimated", summary="Get estimated type locality points (review-only)")
def get_estimated_type_localities(
    order: str | None = Query(None, description="Filter by order"),
    family: str | None = Query(None, description="Filter by family"),
    genus: str | None = Query(None, description="Filter by genus"),
    museum: str | None = Query(None, description="Filter by holding museum abbreviation"),
    country: str | None = Query(None, description="Filter by holding museum country"),
    species: str | None = Query(None, description="Filter to a single accepted species"),
    min_confidence: str | None = Query(
        None,
        description="Optional minimum geocode_confidence: high, medium, or low",
    ),
    limit: int = Query(10000, ge=1, le=20000),
) -> JSONResponse:
    """
    Return review-only estimated type localities as GeoJSON.

    These are **not** official MDD coordinates. Points are shown only for species
    without official type_lat/type_lon in MDD v2.4.
    """
    with _get_conn() as conn:
        if not _table_exists(conn, "estimated_type_localities"):
            return JSONResponse(
                status_code=200,
                content={
                    "type": "FeatureCollection",
                    "features": [],
                    "meta": {"count": 0, "limit": limit, "coord_source": "estimated"},
                },
            )

        conditions = [
            "(s.type_lat IS NULL OR s.type_lon IS NULL)",
            "e.estimated_lat IS NOT NULL",
            "e.estimated_lon IS NOT NULL",
        ]
        params: list[Any] = []

        if species:
            normalised = species.replace(" ", "_")
            space_form = species.replace("_", " ")
            conditions.append("(e.sci_name = ? OR e.sci_name = ?)")
            params.extend([normalised, space_form])
        if order:
            conditions.append('e."order" ILIKE ?')
            params.append(f"%{order}%")
        if family:
            conditions.append("e.family ILIKE ?")
            params.append(f"%{family}%")
        if genus:
            conditions.append("e.genus ILIKE ?")
            params.append(f"%{genus}%")
        if museum:
            conditions.append("e.museum_abbreviation ILIKE ?")
            params.append(museum.strip())
        if country:
            conditions.append("e.museum_country ILIKE ?")
            params.append(country.strip())
        if min_confidence:
            rank = {"high": 3, "medium": 2, "low": 1}.get(min_confidence.strip().lower())
            if rank:
                conditions.append(
                    "CASE lower(e.geocode_confidence) "
                    "WHEN 'high' THEN 3 WHEN 'medium' THEN 2 WHEN 'low' THEN 1 ELSE 0 END >= ?"
                )
                params.append(rank)

        where = "WHERE " + " AND ".join(conditions)
        sql = f"""
            SELECT
                e.species_id,
                e.sci_name,
                e.sci_name_space,
                e.main_common_name,
                e."order",
                e.family,
                s.iucn_status,
                s.extinct,
                e.estimated_lat,
                e.estimated_lon,
                e.type_locality,
                e.type_voucher,
                e.type_kind,
                e.museum_name,
                e.museum_abbreviation,
                e.museum_location,
                e.museum_country,
                e.geocode_phase,
                e.geocode_method,
                e.geocode_confidence,
                e.coordinate_uncertainty_m,
                e.geocode_query,
                e.geocode_notes,
                e.review_status
            FROM estimated_type_localities e
            JOIN species s ON s.species_id = e.species_id
            {where}
            ORDER BY e."order", e.family, e.sci_name
            LIMIT ?
        """
        params.append(limit)
        rows = _rows_to_dicts(conn, sql, params)

    features = [
        {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [row["estimated_lon"], row["estimated_lat"]],
            },
            "properties": {
                **{k: v for k, v in row.items() if k not in ("estimated_lat", "estimated_lon")},
                "coord_source": "estimated",
            },
        }
        for row in rows
    ]

    return JSONResponse(
        status_code=200,
        content={
            "type": "FeatureCollection",
            "features": features,
            "meta": {
                "count": len(features),
                "limit": limit,
                "coord_source": "estimated",
            },
        },
    )


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------
@app.get("/health", include_in_schema=False)
def health() -> dict[str, str]:
    """Quick liveness probe."""
    return {"status": "ok", "db": str(DB_PATH), "db_exists": str(DB_PATH.exists())}
