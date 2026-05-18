-- =============================================================================
-- export_for_postgres.sql  —  PostgreSQL/PostGIS migration guide
-- Run via DuckDB after importing MDD data into mdd.duckdb.
--
-- Two approaches:
--   A) DuckDB postgres extension  (direct write, no dump needed)
--   B) CSV dump + psql COPY       (universal, no extension required)
-- =============================================================================

-- =============================================================================
-- APPROACH A: DuckDB → PostgreSQL directly (requires postgres extension)
-- =============================================================================
-- Run from DuckDB CLI or Python:
--
--   INSTALL postgres; LOAD postgres;
--   ATTACH 'dbname=mdd_db user=postgres host=localhost' AS pgdb (TYPE POSTGRES);
--
--   -- Copy tables
--   CREATE TABLE pgdb.species           AS SELECT * FROM species;
--   CREATE TABLE pgdb.synonyms          AS SELECT * FROM synonyms;
--   CREATE TABLE pgdb.type_specimen_institutions AS SELECT * FROM type_specimen_institutions;
--   CREATE TABLE pgdb.meta              AS SELECT * FROM meta;
--   CREATE TABLE pgdb.version_diff      AS SELECT * FROM version_diff;
--
-- Then in PostgreSQL add PostGIS geometry column to species:
--   ALTER TABLE species ADD COLUMN geom geometry(Point, 4326);
--   UPDATE species
--   SET geom = ST_SetSRID(ST_MakePoint(type_lon, type_lat), 4326)
--   WHERE type_lat IS NOT NULL AND type_lon IS NOT NULL;
--   CREATE INDEX idx_species_geom ON species USING GIST (geom);
--
-- And to synonyms:
--   ALTER TABLE synonyms ADD COLUMN geom geometry(Point, 4326);
--   UPDATE synonyms
--   SET geom = ST_SetSRID(ST_MakePoint(type_lon, type_lat), 4326)
--   WHERE type_lat IS NOT NULL AND type_lon IS NOT NULL;
--   CREATE INDEX idx_synonyms_geom ON synonyms USING GIST (geom);

-- =============================================================================
-- APPROACH B: CSV export from DuckDB → psql COPY
-- =============================================================================
-- Step 1: Export from DuckDB (run this file from setup_database.py or CLI):

COPY (SELECT * FROM species)
TO 'data/processed/exports/pg_species.csv' WITH (HEADER, DELIMITER ',');

COPY (SELECT * FROM synonyms)
TO 'data/processed/exports/pg_synonyms.csv' WITH (HEADER, DELIMITER ',');

COPY (SELECT * FROM type_specimen_institutions)
TO 'data/processed/exports/pg_type_specimen_institutions.csv' WITH (HEADER, DELIMITER ',');

COPY (SELECT * FROM meta)
TO 'data/processed/exports/pg_meta.csv' WITH (HEADER, DELIMITER ',');

COPY (SELECT * FROM version_diff)
TO 'data/processed/exports/pg_version_diff.csv' WITH (HEADER, DELIMITER ',');

-- Step 2: Create PostgreSQL schema (run in psql):
--
--   CREATE EXTENSION IF NOT EXISTS postgis;
--
--   CREATE TABLE species (
--       species_id           INTEGER PRIMARY KEY,
--       sci_name             TEXT NOT NULL,
--       sci_name_space       TEXT GENERATED ALWAYS AS (REPLACE(sci_name, '_', ' ')) STORED,
--       main_common_name     TEXT,
--       "order"              TEXT,
--       family               TEXT,
--       genus                TEXT,
--       specific_epithet     TEXT,
--       authority_author     TEXT,
--       authority_year       INTEGER,
--       iucn_status          TEXT,
--       extinct              BOOLEAN,
--       domestic             BOOLEAN,
--       flagged              BOOLEAN,
--       country_distribution TEXT,
--       continent_distribution TEXT,
--       biogeographic_realm  TEXT,
--       type_locality        TEXT,
--       type_lat             DOUBLE PRECISION,
--       type_lon             DOUBLE PRECISION,
--       geom                 geometry(Point, 4326)
--   );
--
--   \COPY species (species_id, sci_name, main_common_name, ...) FROM 'pg_species.csv' CSV HEADER;
--
--   UPDATE species
--   SET geom = ST_SetSRID(ST_MakePoint(type_lon, type_lat), 4326)
--   WHERE type_lat IS NOT NULL AND type_lon IS NOT NULL;
--
--   CREATE UNIQUE INDEX ON species (sci_name);
--   CREATE UNIQUE INDEX ON species (species_id);
--   CREATE INDEX ON species USING GIST (geom);

SELECT 'See comments above for PostgreSQL migration steps.' AS info;
