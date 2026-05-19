"""
MDD FastAPI — lightweight REST API over mdd.duckdb

Run:
    cd mdd_project
    uvicorn web.api.main:app --reload --port 8000

Docs: http://localhost:8000/docs
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

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


# ---------------------------------------------------------------------------
# GET /species
# List and filter species from the taxonomy schema
# ---------------------------------------------------------------------------
@app.get("/species", summary="List or search species")
def list_species(
    order: str | None = Query(None, description="Filter by order (e.g. 'Primates')"),
    family: str | None = Query(None, description="Filter by family (e.g. 'Galagidae')"),
    limit: int = Query(100, ge=1, le=5000, description="Max rows to return"),
) -> list[dict[str, Any]]:
    """Return accepted MDD species, optionally filtered by taxonomic rank."""
    conditions: list[str] = []
    params: list[Any] = []

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
# GET /type-localities
# Export type localities as GeoJSON FeatureCollection for the web map
# ---------------------------------------------------------------------------
@app.get("/type-localities", summary="Get type locality points for web map")
def get_type_localities(
    order: str | None = Query(None, description="Filter by order"),
    family: str | None = Query(None, description="Filter by family"),
    genus: str | None = Query(None, description="Filter by genus"),
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

    where = "WHERE " + " AND ".join(conditions)
    # Note: the species table has no type_country column (that column lives on
    # the synonyms table).  Use country_distribution as the closest proxy.
    sql = f"""
        SELECT
            species_id,
            sci_name,
            REPLACE(sci_name, '_', ' ') AS sci_name_space,
            main_common_name,
            "order",
            family,
            iucn_status,
            extinct,
            type_lat,
            type_lon,
            type_locality,
            country_distribution AS type_country
        FROM species
        {where}
        ORDER BY "order", family, sci_name
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


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------
@app.get("/health", include_in_schema=False)
def health() -> dict[str, str]:
    """Quick liveness probe."""
    return {"status": "ok", "db": str(DB_PATH), "db_exists": str(DB_PATH.exists())}
