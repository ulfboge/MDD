-- =============================================================================
-- export_for_qgis.sql  —  Export MDD views to GeoParquet and CSV/Parquet
-- Run via setup_database.py after views are created.
-- Paths are substituted at runtime by the Python script.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1. Type localities  →  GeoParquet  (has lat/lon → geometry possible)
--    DuckDB's spatial extension writes GeoParquet natively.
-- ---------------------------------------------------------------------------

-- Install spatial extension if not already present (run once)
-- INSTALL spatial; LOAD spatial;

LOAD spatial;

-- Species type localities as GeoParquet (EPSG:4326, WGS84)
COPY (
    SELECT
        species_id,
        sci_name,
        sci_name_space,
        main_common_name,
        "order",
        family,
        type_locality,
        latitude,
        longitude,
        authority_author,
        authority_year,
        iucn_status,
        extinct,
        biogeographic_realm,
        country_distribution,
        ST_Point(longitude, latitude) AS geometry
    FROM v_type_localities
) TO :type_localities_geoparquet
WITH (FORMAT PARQUET, CODEC 'ZSTD');

SELECT 'Exported type localities GeoParquet: ' || COUNT(*) || ' rows'
FROM v_type_localities;

-- ---------------------------------------------------------------------------
-- 2. Species current  →  Parquet (no geometry; QGIS can load as table layer)
-- ---------------------------------------------------------------------------
COPY (SELECT * FROM v_species_current)
TO :species_current_parquet
WITH (FORMAT PARQUET, CODEC 'ZSTD');

SELECT 'Exported species_current Parquet: ' || COUNT(*) || ' rows'
FROM v_species_current;

-- ---------------------------------------------------------------------------
-- 3. Synonyms  →  Parquet (for lookup / harmonization outside DuckDB)
-- ---------------------------------------------------------------------------
COPY (SELECT * FROM v_synonyms)
TO :synonyms_parquet
WITH (FORMAT PARQUET, CODEC 'ZSTD');

SELECT 'Exported synonyms Parquet: ' || COUNT(*) || ' rows'
FROM v_synonyms;

-- ---------------------------------------------------------------------------
-- 4. Full species list  →  CSV (universal QGIS / spreadsheet fallback)
-- ---------------------------------------------------------------------------
COPY (
    SELECT
        species_id,
        sci_name,
        sci_name_space,
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
        type_locality,
        type_lat  AS latitude,
        type_lon  AS longitude
    FROM v_species_all
) TO :species_all_csv
WITH (HEADER, DELIMITER ',');

SELECT 'Exported species_all CSV: ' || COUNT(*) || ' rows'
FROM v_species_all;

SELECT 'QGIS exports complete.' AS status;
