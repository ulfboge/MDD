-- =============================================================================
-- export_geoparquet.sql  —  GeoParquet export templates for MDD data
--
-- Run via DuckDB CLI or setup_database.py.
-- Paths can be adjusted or substituted at runtime.
--
-- Requires: LOAD spatial; (DuckDB spatial extension)
-- CRS: all geometries are WGS84 / EPSG:4326
-- =============================================================================

LOAD spatial;

-- ---------------------------------------------------------------------------
-- 1. Type localities  →  GeoParquet
-- Source: species table (typeLocalityLatitude / typeLocalityLongitude columns)
-- One point per species name-bearing type specimen.
--
-- ⚠️ These are type SPECIMEN localities, not species range centroids.
-- ---------------------------------------------------------------------------
COPY (
    SELECT
        species_id,
        sci_name,
        REPLACE(sci_name, '_', ' ')         AS sci_name_space,
        main_common_name,
        "order",
        family,
        genus,
        type_locality,
        type_lat                            AS latitude,
        type_lon                            AS longitude,
        authority_author,
        authority_year,
        iucn_status,
        extinct,
        biogeographic_realm,
        country_distribution,
        ST_Point(type_lon, type_lat)        AS geometry   -- EPSG:4326, lon first
    FROM v_type_localities                               -- only rows with valid coords
) TO 'data/processed/geoparquet/type_localities.parquet'
WITH (FORMAT PARQUET, CODEC 'ZSTD');

SELECT
    'type_localities.parquet written: ' || COUNT(*) || ' species with coordinates' AS status
FROM v_type_localities;


-- ---------------------------------------------------------------------------
-- 2. Synonym type localities  →  GeoParquet
-- Each synonym can have its own type specimen locality.
-- ---------------------------------------------------------------------------
COPY (
    SELECT
        syn.syn_id,
        syn.original_combination            AS synonym_name,
        syn.accepted_sci_name,
        syn.validity,
        syn.type_lat                        AS latitude,
        syn.type_lon                        AS longitude,
        syn.type_country,
        syn.type_subregion,
        syn.holotype,
        syn.authority_citation,
        ST_Point(syn.type_lon, syn.type_lat) AS geometry  -- EPSG:4326
    FROM v_type_localities_synonyms syn
) TO 'data/processed/geoparquet/synonym_type_localities.parquet'
WITH (FORMAT PARQUET, CODEC 'ZSTD');

SELECT
    'synonym_type_localities.parquet written: ' || COUNT(*) || ' synonyms with coordinates' AS status
FROM v_type_localities_synonyms;


-- ---------------------------------------------------------------------------
-- 3. TEMPLATE: Occurrence / observation export  →  GeoParquet
--
-- Replace the FROM clause with your actual occurrences table once loaded.
-- Expected columns: occurrence_id, sci_name (or species), decimal_lat, decimal_lon,
--                   event_date, dataset_name, occurrence_status
--
-- Example loading GBIF CSV:
--   CREATE TABLE occurrences AS
--   SELECT * FROM read_csv_auto('data/external/occurrence_data/gbif_export.csv');
--
-- Then run this block:
-- ---------------------------------------------------------------------------

-- UNCOMMENT after occurrences table is loaded:
--
-- COPY (
--     SELECT
--         o.occurrence_id,
--         o.sci_name,
--         sp.main_common_name,
--         sp."order",
--         sp.family,
--         o.decimal_lat                        AS latitude,
--         o.decimal_lon                        AS longitude,
--         o.event_date,
--         o.dataset_name,
--         o.occurrence_status,
--         sp.iucn_status,
--         ST_Point(o.decimal_lon, o.decimal_lat) AS geometry  -- EPSG:4326
--     FROM occurrences o
--     LEFT JOIN v_species_current sp
--         ON REPLACE(o.sci_name, ' ', '_') = sp.sci_name
--         OR o.sci_name = sp.sci_name_space
--     WHERE o.decimal_lat  BETWEEN -90  AND 90
--       AND o.decimal_lon  BETWEEN -180 AND 180
-- ) TO 'data/processed/geoparquet/occurrences.parquet'
-- WITH (FORMAT PARQUET, CODEC 'ZSTD');


-- ---------------------------------------------------------------------------
-- 4. TEMPLATE: Export taxonomy view to GeoPackage (QGIS-ready vector layer)
--
-- GeoPackage is a universal fallback when GeoParquet is not available.
-- Requires: GDAL driver 'GPKG' (bundled with DuckDB spatial)
-- ---------------------------------------------------------------------------

-- UNCOMMENT to export as GeoPackage:
--
-- COPY (
--     SELECT
--         species_id, sci_name, REPLACE(sci_name, '_', ' ') AS sci_name_space,
--         main_common_name, "order", family,
--         type_locality, latitude, longitude, iucn_status, biogeographic_realm,
--         ST_Point(longitude, latitude) AS geom
--     FROM v_type_localities
-- ) TO 'data/processed/exports/type_localities.gpkg'
-- WITH (FORMAT GDAL, DRIVER 'GPKG', LAYER_CREATION_OPTIONS 'GEOMETRY_NAME=geom');

SELECT 'GeoParquet export complete.' AS status;
