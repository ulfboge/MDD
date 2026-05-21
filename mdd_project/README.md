# Mammal Diversity Database (MDD) — Project Setup

> **Data source:** [Mammal Diversity Database v2.4](https://www.mammaldiversity.org/)
> (Zenodo: <https://doi.org/10.5281/zenodo.18135819>)
> 6,871 species · Released 2026-01-02

---

## Quick Start

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Build the DuckDB database (CSV files must be in repo root or data/raw/MDD/)
python mdd_project/scripts/setup_database.py

# 3. Query interactively
duckdb mdd_project/data/processed/mdd.duckdb

# 4. (Optional) Import GBIF occurrences for a species
python mdd_project/scripts/gbif_import.py --species "Ursus arctos" --limit 500

# 5. (Optional) Start web map
#    Terminal A — API
uvicorn mdd_project.web.api.main:app --reload --port 8000
#    Terminal B — Frontend
cd mdd_project/web/frontend && npm install && npm run dev
# → http://localhost:5173
```

---

## Troubleshooting

### "Database not found" / `[ERROR] Database not found at …mdd.duckdb`

`mdd.duckdb` is a generated artifact — it is gitignored and must be built before any
script or API call will work. Run from the **repo root**:

```bash
python mdd_project/scripts/setup_database.py
```

This reads the five raw CSV files at the repo root (or `data/raw/MDD/`) and
produces `mdd_project/data/processed/mdd.duckdb` plus initial GeoParquet exports.
It takes about 15–30 seconds. You only need to run it once per machine (or after
deleting the DB file).

**Required order to get everything working:**

```bash
# Step 1 — build the taxonomy DB (run once)
python mdd_project/scripts/setup_database.py

# Step 2 — import GBIF occurrences for a species (run as needed)
python mdd_project/scripts/gbif_import.py --species "Ursus arctos" --limit 200

# Step 3 — start the API (optional)
uvicorn mdd_project.web.api.main:app --reload --port 8000
```

### FastAPI returns HTTP 503 `"Database not found"`

Same root cause as above — the DB file does not exist.
Stop the API, run `setup_database.py`, then restart the server.

### `GET /occurrences/{species}` returns an empty FeatureCollection

The `observations` table is **not** created by `setup_database.py`. It is created
automatically the first time you run `gbif_import.py` for any species. Until then,
the API returns an empty collection with a `meta.message` hint:

```json
{
  "meta": {
    "message": "observations table not found — run the GBIF import pipeline first: ..."
  }
}
```

Fix: run `gbif_import.py` for the species you want, then re-query the endpoint.

### DuckDB `IO Error: Could not set lock on file` (file lock conflict)

DuckDB allows only one writer at a time. If the FastAPI server has the DB open in
read-only mode while you simultaneously run `setup_database.py` or `gbif_import.py`,
you may see a lock error.

- The FastAPI API opens connections with `read_only=True` — it does not block writers.
- Two concurrent *writers* (two `gbif_import.py` processes, or import + setup) will conflict.
- If you hit this, stop any running import, wait a few seconds, and retry.

### `requests` / `duckdb` / `pandas` not found

Install all Python dependencies from the repo root:

```bash
pip install -r requirements.txt
```

### GBIF API network errors (`requests.exceptions.ConnectionError`)

`gbif_import.py` calls `https://api.gbif.org` — no API key required but a network
connection is needed. If you are behind a firewall or proxy:

- Set `HTTPS_PROXY` / `HTTP_PROXY` environment variables before running the script.
- All GBIF calls use `requests` with a 30-second timeout; transient failures are
  logged as `[WARN]` and the script continues.

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | ≥ 3.11 | Run setup scripts |
| duckdb (Python) | ≥ 1.2 | Database engine |
| pyarrow | ≥ 18 | Parquet I/O |
| QGIS | ≥ 3.32 | Native GeoParquet support |
| DuckDB CLI | ≥ 1.2 | Ad-hoc queries |
| Node.js | ≥ 18 | Web map frontend |

Install Python packages: `pip install -r requirements.txt`

### DuckDB CLI installation

```bash
# Windows (winget) — installs v1.5.2
winget install DuckDB.cli

# Verify (restart shell first, or refresh PATH)
duckdb --version
# v1.5.2 (Variegata)
```

---

## Folder Layout

```
MDD/                                  ← repo root (CSV files live here)
├── MDD_v2.4_6871species.csv
├── Species_Syn_v2.4.csv
├── TypeSpecimenMetadata_v2.4.csv
├── META_v2.4.csv
├── Diff_v2.3-v2.4.csv
├── release.toml
├── requirements.txt
├── .gitignore
└── mdd_project/
    ├── README.md                     ← this file
    ├── data/
    │   ├── raw/MDD/                  ← place CSVs here OR keep in repo root
    │   ├── processed/
    │   │   ├── mdd.duckdb            ← built by setup_database.py (gitignored)
    │   │   ├── exports/              ← CSVs for QGIS (gitignored)
    │   │   └── geoparquet/           ← GeoParquet layers (gitignored)
    │   └── external/occurrence_data/ ← place GBIF/iNat exports here
    ├── scripts/
    │   ├── setup_database.py         ← main entry point
    │   ├── import_mdd.sql            ← schema + CSV ingestion
    │   ├── create_views.sql          ← analytical views (default + taxonomy schema)
    │   ├── export_for_qgis.sql       ← GeoParquet + CSV exports
    │   ├── export_geoparquet.sql     ← type locality + observation GeoParquet templates
    │   ├── export_for_postgres.sql   ← PostgreSQL/PostGIS migration guide
    │   ├── harmonize_names.py        ← CLI: resolve CSV name column → MDD accepted names
    │   └── gbif_import.py            ← GBIF occurrence download + DuckDB ingest
    ├── qgis/
    │   └── QGIS_CONNECTION.md        ← step-by-step QGIS connection guide
    └── web/
        ├── api/
        │   ├── main.py               ← FastAPI application (working)
        │   └── README.md             ← API docs + uvicorn quickstart
        └── frontend/README.md        ← planned React + MapLibre scaffold
```

---

## Database Tables

| Table | Rows | Description |
|-------|------|-------------|
| `species` | 6,871 | Main MDD checklist (all species) |
| `synonyms` | ~100k | All nomenclatural synonyms (Species_Syn) |
| `type_specimen_institutions` | ~600 | Institution codes for type specimens |
| `meta` | ~50 | Column documentation |
| `version_diff` | varies | Changes from v2.3 → v2.4 |

### Key join columns

| Column | Tables | Purpose |
|--------|--------|---------|
| `species_id` | species, synonyms | Integer primary key join |
| `sci_name` | species | Underscore-separated accepted name (`Ursus_arctos`) |
| `sci_name_space` | views | Space-separated name (`Ursus arctos`) |
| `accepted_sci_name` | synonyms | Points back to `species.sci_name` |
| `original_combination` | synonyms | Historical/variant name for harmonization |

---

## Views

| View | Description |
|------|-------------|
| `v_species_current` | Extant, wild, unflagged species with coordinates |
| `v_species_all` | All species including extinct and domestic |
| `v_synonyms` | Synonym → accepted name mapping |
| `v_species_with_synonyms` | One row per synonym, annotated with accepted species info |
| `v_type_localities` | Species with valid lat/lon type locality (WGS84) |
| `v_type_localities_synonyms` | Synonym type localities with coordinates |

---

## Coordinates

> **⚠️ Data quality note:** `type_lat` / `type_lon` are **type specimen collection
> localities** — where the name-bearing specimen was collected. They are NOT species
> range centroids or occurrence records. Many species (especially widespread ones)
> have type localities far from their current range centroid.

- CRS: WGS84 / EPSG:4326
- ~XX% of species have numeric coordinates (check `v_type_localities` count after build)
- For species range / occurrence data, join to GBIF or iNaturalist exports via `sci_name_space`

---

## Harmonization: Synonym Lookup

Resolve any incoming species name (from GBIF, a field dataset, or literature) to the
current MDD accepted name:

```sql
-- Example: resolve "Ursus arctos horribilis" or any variant
SELECT
    vws.synonym_name,
    vws.accepted_sci_name,
    vws.accepted_sci_name_space,
    vws.main_common_name,
    vws."order",
    vws.family,
    vws.iucn_status
FROM v_species_with_synonyms vws
WHERE vws.synonym_name ILIKE '%Ursus arctos%'
ORDER BY vws.validity;
```

**Bulk harmonization (join your observation table):**

```sql
-- Assuming your table: observations(obs_id, reported_name, ...)
-- Reported names may use spaces or underscores; normalize first:

SELECT
    o.obs_id,
    o.reported_name,
    sp.species_id,
    sp.sci_name           AS mdd_accepted_name,
    sp.sci_name_space     AS mdd_accepted_name_space,
    sp.main_common_name,
    sp.family,
    sp.iucn_status
FROM observations o
LEFT JOIN v_species_with_synonyms vws
    ON REPLACE(o.reported_name, ' ', '_') = vws.synonym_name
   OR o.reported_name = vws.synonym_name
LEFT JOIN v_species_current sp
    ON vws.species_id = sp.species_id
ORDER BY o.obs_id;
```

**Direct species name match (when names are already in MDD format):**

```sql
SELECT *
FROM v_species_current
WHERE sci_name = 'Ursus_arctos'
   OR sci_name_space = 'Ursus arctos';
```

---

## QGIS Connection

See [qgis/QGIS_CONNECTION.md](qgis/QGIS_CONNECTION.md) for full instructions.

**TL;DR — fastest path:**
1. Run `setup_database.py` to generate `geoparquet/type_localities.parquet`
2. In QGIS: Layer → Add Layer → Add Vector Layer → browse to the `.parquet` file
3. Done — 4,000+ georeferenced type localities load as point layer (EPSG:4326)

---

## DuckDB CLI — Quick Reference

```bash
# Open database
duckdb mdd_project/data/processed/mdd.duckdb

# List all tables and views
.tables

# Count species by IUCN status
SELECT iucn_status, COUNT(*) AS n
FROM v_species_current
GROUP BY iucn_status ORDER BY n DESC;

# Species per order
SELECT "order", COUNT(*) AS n
FROM v_species_current
GROUP BY "order" ORDER BY n DESC;

# Export a view to CSV on the fly
COPY (SELECT * FROM v_type_localities) TO 'type_localities.csv' WITH (HEADER);
```

---

## PostgreSQL / PostGIS Migration

See `scripts/export_for_postgres.sql` for:
- **Approach A**: DuckDB `postgres` extension (direct write, zero CSV export)
- **Approach B**: CSV dump + `psql COPY` (universal, no extension needed)

Both approaches add a PostGIS `geometry(Point, 4326)` column on `type_lat`/`type_lon`.

---

## Reproducibility

| Step | Command |
|------|---------|
| Build DB | `python mdd_project/scripts/setup_database.py` |
| Rebuild only DB (skip exports) | `python mdd_project/scripts/setup_database.py --skip-exports` |
| Custom CSV dir | `python mdd_project/scripts/setup_database.py --raw-dir /path/to/csvs` |
| Custom DB path | `python mdd_project/scripts/setup_database.py --db /path/to/output.duckdb` |

All processed outputs (`mdd.duckdb`, Parquet, CSV exports) are gitignored and
fully reproducible by re-running `setup_database.py`.

---

## Design Principle — MDD as Taxonomy Backbone

MDD is the **taxonomy backbone**, not a spatial or occurrence database.

| Data | Role in this project | Source |
|------|----------------------|--------|
| Taxonomy, synonyms, type localities | Core map layers | [MDD v2.4](https://www.mammaldiversity.org/) |
| IUCN status colours | Per-species field in MDD; links to Red List | MDD → [IUCN Red List](https://www.iucnredlist.org/) |
| GBIF occurrences | Separate orange layer per selected species | [GBIF API](https://www.gbif.org/) |
| Estimated type localities | Review-only geocoding fallback | Local pipeline (`geocode_type_localities.py`) |
| Voucher catalogue links | Popup links when MDD has URIs (VertNet, iDigBio, GBIF specimen pages) | MDD `type_voucher_uris` — not full museum catalogues |

Recommended batch import for galago work:

```bash
python mdd_project/scripts/gbif_import.py --from-mdd --family Galagidae --limit-per-species 100 --no-export
```

- Every species, synonym, and name has a stable `species_id` integer key
- All external datasets (GBIF, IUCN, iNaturalist, camera trap CSVs) should be
  **joined to MDD**, not the other way around
- The `synonyms` table is the bridge: resolve any incoming name variant to the
  current accepted `sci_name` before any spatial or statistical analysis
- Coordinates in MDD (`type_lat` / `type_lon`) are **type specimen localities** —
  where the name-bearing specimen was collected, not species range centroids

```
External data (GBIF, IUCN, field CSVs)
         ↓  harmonize via synonyms table
MDD taxonomy backbone  →  join on species_id or sci_name
         ↓
Analysis, maps, species profiles
```

---

## Example Queries (§11)

### Galagos (family Galagidae) — via taxonomy schema

```sql
-- All galago species with conservation status
SELECT sciName, mainCommonName, iucnStatus, countryDistribution
FROM taxonomy.galagos
ORDER BY iucnStatus, sciName;
```

### Synonym lookup — resolve any name to accepted MDD name

```sql
-- What is the current accepted name for 'Galago moholi'?
SELECT
    original_combination    AS synonym_name,
    accepted_sci_name,
    validity,
    nomenclature_status
FROM synonyms
WHERE original_combination ILIKE '%Galago moholi%'
ORDER BY validity;
```

### Version diff — what changed from MDD v2.3 to v2.4?

```sql
-- New species added in v2.4
SELECT name_v23, name_v24, category, comment
FROM taxonomy.mdd_version_diff
WHERE name_v23 IS NULL OR name_v23 = ''
ORDER BY name_v24;

-- Species synonymised in v2.4
SELECT name_v23, name_v24, category, comment
FROM taxonomy.mdd_version_diff
WHERE category ILIKE '%synonym%'
ORDER BY name_v23;
```

### Primates with type localities

```sql
SELECT
    p.sciName,
    p.mainCommonName,
    p.family,
    p.typeLocality,
    p.typeLocalityLatitude  AS lat,
    p.typeLocalityLongitude AS lon
FROM taxonomy.primates p
WHERE p.typeLocalityLatitude IS NOT NULL
ORDER BY p.family, p.sciName;
```

---

## Taxonomy Schema Reference (§§3-5)

The `taxonomy` schema exposes the MDD data with original camelCase column names,
matching the official MDD publication column names.

| View | Maps to | Description |
|------|---------|-------------|
| `taxonomy.mdd_species` | `species` | All 6,871 species, original MDD column names |
| `taxonomy.mdd_synonyms` | `synonyms` | All ~65k synonyms |
| `taxonomy.mdd_type_specimens` | `type_specimen_institutions` | Institution codes |
| `taxonomy.mdd_meta` | `meta` | Column documentation |
| `taxonomy.mdd_version_diff` | `version_diff` | v2.3 → v2.4 changes |
| `taxonomy.primates` | filter on `mdd_species` | 418 primate species |
| `taxonomy.galagos` | filter on `mdd_species` | Galagidae (bushbabies) |
| `taxonomy.species_lookup` | select from `mdd_species` | Compact name resolution table |

The default schema (no prefix) uses snake_case column names and is used internally
by export scripts and the FastAPI layer.

---

## GBIF Occurrence Import

The `scripts/gbif_import.py` pipeline fetches occurrence records from the
[GBIF occurrence API](https://api.gbif.org/v1/occurrence/search) (no API key
required), harmonizes reported species names to MDD accepted names, and stores
records in the `observations` table in DuckDB.

```bash
# Single species, 50 records (test run)
python mdd_project/scripts/gbif_import.py --species "Galago moholi" --limit 50

# Single species, up to 500 records
python mdd_project/scripts/gbif_import.py --species "Ursus arctos" --limit 500

# By GBIF taxon key
python mdd_project/scripts/gbif_import.py --taxon-key 2433459 --limit 200

# Entire family (batch mode, 100 records per species)
python mdd_project/scripts/gbif_import.py --from-mdd --family Galagidae --limit-per-species 100

# Force replace existing records
python mdd_project/scripts/gbif_import.py --species "Ursus arctos" --limit 500 --replace

# Skip GeoParquet export (faster, do separately later)
python mdd_project/scripts/gbif_import.py --species "Ursus arctos" --limit 500 --no-export
```

Outputs:
- `observations` table in `mdd.duckdb` with MDD name harmonization
- `data/processed/geoparquet/observations.parquet` (GeoParquet, EPSG:4326)

### Observations table schema

| Column | Type | Description |
|--------|------|-------------|
| `obs_id` | BIGINT PK | GBIF occurrence key |
| `reported_name` | VARCHAR | Name as reported by GBIF |
| `mdd_species_id` | INTEGER | FK → `species.species_id` |
| `mdd_sci_name` | VARCHAR | MDD accepted name (underscore) |
| `mdd_match_type` | VARCHAR | `exact`, `synonym`, or `unmatched` |
| `latitude`, `longitude` | DOUBLE | WGS84 coordinates |
| `geom` | GEOMETRY | `ST_Point(longitude, latitude)` |
| `event_date` | DATE | Observation date |
| `dataset_name` | VARCHAR | GBIF dataset name |
| `country_code` | VARCHAR | ISO 2-letter country code |
| `coordinate_uncertainty_m` | DOUBLE | metres (from GBIF) |

---

## Web Map

React + MapLibre GL JS app at `web/frontend/`.

```bash
# Start FastAPI (Terminal 1)
uvicorn mdd_project.web.api.main:app --reload --port 8000

# Start Vite dev server (Terminal 2)
cd mdd_project/web/frontend
npm install   # first time only
npm run dev
# → http://localhost:5173
```

**Layers:**
- **Type localities** — 4,000+ MDD type specimens, coloured by IUCN status
- **GBIF occurrences** — loaded per-species when you search and select a species

**API endpoints used by the map:**

| Endpoint | Purpose |
|----------|---------|
| `GET /type-localities` | GeoJSON FeatureCollection for the type locality layer |
| `GET /species?limit=N` | Species autocomplete |
| `GET /species/{name}` | Single species lookup |
| `GET /occurrences/{species}` | GeoJSON FeatureCollection of GBIF records |

---

## Web API

A minimal FastAPI application is available at `web/api/main.py`.

```bash
pip install fastapi "uvicorn[standard]"
uvicorn mdd_project.web.api.main:app --reload --port 8000
# → http://localhost:8000/docs
```

See [`web/api/README.md`](web/api/README.md) for full endpoint documentation.

---

## Long-Term PostgreSQL / PostGIS Path

DuckDB is the primary working database for local analysis. When you need:
- Multi-user concurrent write access
- Integration with an existing PostGIS stack
- Server-side spatial queries at scale

Use `scripts/export_for_postgres.sql` for two migration approaches:
- **Approach A**: DuckDB `postgres` extension (direct write, no CSV export)
- **Approach B**: CSV dump + `psql COPY` (universal, no extension required)

Both approaches add a `geometry(Point, 4326)` PostGIS column on `type_lat`/`type_lon`.

---

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `scripts/setup_database.py` | Build `mdd.duckdb` from raw CSVs (main entry point) |
| `scripts/import_mdd.sql` | Schema creation + CSV ingestion |
| `scripts/create_views.sql` | Analytical views (default schema + `taxonomy` schema) |
| `scripts/export_for_qgis.sql` | GeoParquet + CSV exports for QGIS |
| `scripts/export_geoparquet.sql` | Type locality + occurrence GeoParquet templates |
| `scripts/export_for_postgres.sql` | PostgreSQL/PostGIS migration guide |
| `scripts/harmonize_names.py` | CLI: resolve a CSV column of names to MDD accepted names |
| `scripts/gbif_import.py` | GBIF occurrence download + DuckDB ingest + GeoParquet export |

---

## Future Upgrades

- **GBIF / IUCN / Wikidata IDs**: Add `gbif_taxon_key`, `iucn_taxon_id`, and
  `wikidata_qid` columns to the species table for direct cross-reference
- **Spatial layers**: Country/biome polygon layers from IUCN, WWF, or GADM joined
  on `countryDistribution` and `biogeographicRealm`
- **Species range maps**: IUCN range polygon download + DuckDB spatial join
- **Observation explorer**: GBIF occurrence data loaded via `gbif_import.py`
- **Synonym search API**: `/synonyms/resolve?name=X` endpoint
- **Species profiles**: `/species/{name}/profile` with IUCN link, Wikidata image,
  common names, GBIF occurrence count
- **MapLibre map**: Interactive web map of type localities + occurrence heat map
  (see `web/frontend/README.md`)
- **PMTiles export**: Pre-tiled vector layer for fast browser rendering

---

## Recommended Next Steps

1. **Harmonization tools** — test `harmonize_names.py` with a real observation CSV
   (`python mdd_project/scripts/harmonize_names.py my_obs.csv --col species`)
2. **GBIF import pipeline** — implement `scripts/gbif_import.py` for Primates or
   a single family; use the occurrence template in `export_geoparquet.sql`
3. **QGIS templates** — create a `.qgz` project with styled layers and save the
   colour-by-IUCN symbology as a QGIS layer style file (`.qml`)
4. **MapLibre map** — scaffold the React + MapLibre app in `web/frontend/` to
   display type localities from the GeoParquet file
5. **Synonym search** — implement `/synonyms/resolve?name=X` in the FastAPI app
6. **Species profiles** — add a `/species/{name}/profile` endpoint combining MDD
   data with GBIF and IUCN links
7. **Observation explorer** — GBIF occurrence table + spatial join to MDD taxonomy

---

## Citation

```
Mammal Diversity Database. (2026). Mammal Diversity Database (Version 2.4) [Data set].
Zenodo. https://doi.org/10.5281/zenodo.18135819
```
