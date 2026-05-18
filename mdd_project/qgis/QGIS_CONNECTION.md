# QGIS Connection Guide — MDD Project

The `mdd_project.qgz` QGIS project file is created manually after running the database setup.
Follow the steps below to connect QGIS to MDD data.

---

## Option A — Direct DuckDB Connection (QGIS 3.38+ with DuckDB provider)

QGIS 3.38+ includes a native DuckDB data provider that lets you browse tables and
views directly — no ODBC driver, no export step needed.

1. Open **Browser panel** (View → Panels → Browser)
2. Right-click **DuckDB** → **New Connection…**
3. **Name**: `MDD`
4. **Database file**: browse to `mdd_project/data/processed/mdd.duckdb`  
   (use absolute path; relative paths are resolved from QGIS project folder)
5. Click **OK** → expand the connection in the browser tree
6. You will see all tables and views, including:
   - `v_type_localities` — 4,000+ georeferenced type specimen localities
   - `taxonomy.primates`, `taxonomy.galagos` — pre-built taxon group views
   - `species`, `synonyms`, etc.
7. **Drag** `v_type_localities` onto the canvas → geometry is auto-detected as
   Point (WGS84 / EPSG:4326) via the `ST_Point` geometry column

> **Note:** If the DuckDB provider is not available in your QGIS version, use
> Option B (GeoParquet) or Option C (ODBC) below.

---

## Option B — Load GeoParquet directly (QGIS 3.32+)

QGIS 3.32+ reads GeoParquet natively via GDAL/Arrow.

1. **Layer → Add Layer → Add Vector Layer**
2. Source type: **File**
3. Browse to: `mdd_project/data/processed/geoparquet/type_localities.parquet`
4. Click **Add** — points appear immediately (WGS84 / EPSG:4326)

> For non-spatial Parquet tables (e.g. `species_current.parquet`), load as a
> **delimited text** or use the DB Manager with DuckDB ODBC.

---

## Option B — DuckDB via ODBC (Windows/Linux/macOS)

### Prerequisites
1. Install DuckDB ODBC driver: <https://duckdb.org/docs/api/odbc/overview>
2. Register DSN:
   - Windows: ODBC Data Source Administrator → System DSN → Add → DuckDB Driver
   - DSN Name: `MDD_DuckDB`
   - Database: `<absolute path to mdd_project/data/processed/mdd.duckdb>`

### In QGIS
1. **Layer → Add Layer → Add Vector Layer**
2. Source type: **Database**
3. Connection: ODBC → select `MDD_DuckDB`
4. Table/Query: choose `v_type_localities` or write a custom SQL query

---

## Option C — Export to GeoPackage (universal fallback)

Run this from the DuckDB CLI or a Python script:

```sql
-- In DuckDB CLI: duckdb mdd_project/data/processed/mdd.duckdb
LOAD spatial;

COPY (
    SELECT
        species_id, sci_name, main_common_name, "order", family,
        type_locality, latitude, longitude, iucn_status, biogeographic_realm,
        ST_Point(longitude, latitude) AS geom
    FROM v_type_localities
) TO 'mdd_project/data/processed/exports/type_localities.gpkg'
WITH (FORMAT GDAL, DRIVER 'GPKG', LAYER_CREATION_OPTIONS 'GEOMETRY_NAME=geom');
```

Then in QGIS: **Layer → Add Layer → Add Vector Layer** → browse to `type_localities.gpkg`.

---

## Recommended layer style

- **Point colour**: by `iucn_status` (CR=red, EN=orange, VU=yellow, LC=green, EX=black)
- **Label**: `sci_name_space`
- **Tooltip**: `main_common_name`, `family`, `country_distribution`

---

## Joining occurrence data in QGIS

1. Load your occurrence layer (e.g. GBIF CSV)
2. Load `species_current.parquet` as a non-spatial table layer
3. Use **Processing → Join attributes by field value**:
   - Input: occurrence layer field `species` or `scientificName`
   - Join: `species_current` field `sci_name_space`
   - If name variants exist, first resolve via `v_species_with_synonyms`

---

## Creating the .qgz project

After loading layers:
1. Set project CRS to **EPSG:4326** (Project → Properties → CRS)
2. Save as: `mdd_project/qgis/mdd_project.qgz`

> The `.qgz` binary is excluded from git by default (`.gitignore`).
> Commit only the layer sources (Parquet/GeoPackage) which are reproducible.
