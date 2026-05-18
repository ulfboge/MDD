-- =============================================================================
-- create_views.sql  —  GIS & harmonization views for MDD DuckDB
-- Run after import_mdd.sql via setup_database.py
--
-- Two namespaces are maintained deliberately:
--   • Default schema (no prefix):  snake_case, optimised column names
--     → used internally by export scripts and the FastAPI layer
--   • taxonomy schema:             original MDD camelCase column names
--     → used for user-facing queries that mirror the official MDD spec
-- =============================================================================

-- ---------------------------------------------------------------------------
-- TAXONOMY SCHEMA  (authoritative per MDD spec; §§3-5 of setup guide)
-- ---------------------------------------------------------------------------

CREATE SCHEMA IF NOT EXISTS taxonomy;

-- taxonomy.mdd_species
-- Exposes the species table using original MDD camelCase column names so that
-- queries written against the published MDD column spec work without change.
CREATE OR REPLACE VIEW taxonomy.mdd_species AS
SELECT
    species_id,
    sci_name                            AS sciName,
    "order"                             AS orderName,
    suborder,
    family,
    subfamily,
    tribe,
    genus,
    subgenus,
    specific_epithet                    AS specificEpithet,
    authority_author                    AS authoritySpeciesAuthor,
    authority_year                      AS authoritySpeciesYear,
    authority_parentheses               AS authorityParentheses,
    main_common_name                    AS mainCommonName,
    other_common_names                  AS otherCommonNames,
    iucn_status                         AS iucnStatus,
    extinct,
    domestic,
    flagged,
    type_locality                       AS typeLocality,
    type_lat                            AS typeLocalityLatitude,
    type_lon                            AS typeLocalityLongitude,
    country_distribution                AS countryDistribution,
    continent_distribution              AS continentDistribution,
    biogeographic_realm                 AS biogeographicRealm,
    subregion_distribution              AS subregionDistribution
FROM species;

-- taxonomy.mdd_synonyms  (pass-through; synonym table already has good names)
CREATE OR REPLACE VIEW taxonomy.mdd_synonyms AS
SELECT * FROM synonyms;

-- taxonomy.mdd_type_specimens
CREATE OR REPLACE VIEW taxonomy.mdd_type_specimens AS
SELECT * FROM type_specimen_institutions;

-- taxonomy.mdd_meta
CREATE OR REPLACE VIEW taxonomy.mdd_meta AS
SELECT * FROM meta;

-- taxonomy.mdd_version_diff
CREATE OR REPLACE VIEW taxonomy.mdd_version_diff AS
SELECT * FROM version_diff;

-- ---------------------------------------------------------------------------
-- taxonomy.primates  — all 418 primate species
-- ORDER value: 'Primates' (title case, verified against MDD v2.4)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW taxonomy.primates AS
SELECT * FROM taxonomy.mdd_species
WHERE orderName = 'Primates';

-- ---------------------------------------------------------------------------
-- taxonomy.galagos  — Family Galagidae (bushbabies / galagos)
-- Family exact value: 'Galagidae' (verified against MDD v2.4)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW taxonomy.galagos AS
SELECT * FROM taxonomy.mdd_species
WHERE family ILIKE '%Galagidae%';

-- ---------------------------------------------------------------------------
-- taxonomy.species_lookup  — compact lookup table for name resolution
-- Mirrors columns named in §5 of the setup guide.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW taxonomy.species_lookup AS
SELECT
    sciName,
    species_id                          AS id,
    orderName,
    family,
    genus,
    specificEpithet,
    authoritySpeciesAuthor,
    authoritySpeciesYear
FROM taxonomy.mdd_species;

-- Summary for taxonomy schema
SELECT
    (SELECT COUNT(*) FROM taxonomy.mdd_species)  AS taxonomy_species,
    (SELECT COUNT(*) FROM taxonomy.primates)      AS primates,
    (SELECT COUNT(*) FROM taxonomy.galagos)       AS galagos,
    (SELECT COUNT(*) FROM taxonomy.species_lookup) AS species_lookup_rows;


-- ---------------------------------------------------------------------------
-- v_species_current
-- Canonical, accepted, extant species names with key taxonomy and coordinates.
-- Primary target for joining external occurrence / observation tables.
--
-- JOIN key:  sci_name  (e.g. 'Ursus_arctos')  or  species_id (integer)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_species_current AS
SELECT
    species_id,
    sci_name,
    REPLACE(sci_name, '_', ' ')     AS sci_name_space,    -- for plain-text matching
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
    type_lat,
    type_lon                                               -- WGS84 (EPSG:4326)
FROM species
WHERE extinct = false
  AND domestic = false
  AND flagged  = false;

-- ---------------------------------------------------------------------------
-- v_species_all
-- All species including extinct and domestic; useful for full-taxonomy work.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_species_all AS
SELECT
    species_id,
    sci_name,
    REPLACE(sci_name, '_', ' ')     AS sci_name_space,
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
    flagged,
    country_distribution,
    continent_distribution,
    biogeographic_realm,
    type_locality,
    type_lat,
    type_lon
FROM species;

-- ---------------------------------------------------------------------------
-- v_synonyms
-- Synonym → accepted name mapping for taxonomy harmonization.
-- Use this to resolve any name variant to the current MDD accepted sci_name.
--
-- JOIN pattern (harmonization):
--   SELECT s.accepted_sci_name
--   FROM v_synonyms s
--   WHERE s.original_combination = '<incoming_name>'
--      OR s.normalized_original_combination = '<incoming_name>';
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_synonyms AS
SELECT
    syn_id,
    accepted_sci_name,                               -- current MDD name (use to join species table)
    REPLACE(accepted_sci_name, '_', ' ')
                            AS accepted_sci_name_space,
    species_id,
    original_combination,
    normalized_original_combination,
    root_name,
    author,
    year,
    nomenclature_status,
    validity,
    original_rank,
    type_lat,
    type_lon,
    type_country,
    authority_citation,
    authority_link
FROM synonyms;

-- ---------------------------------------------------------------------------
-- v_species_with_synonyms
-- Flat lookup table: one row per synonym, annotated with accepted species info.
-- Ideal for fuzzy-matching / LIKE queries or bulk name reconciliation.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_species_with_synonyms AS
SELECT
    syn.syn_id,
    syn.original_combination        AS synonym_name,
    syn.normalized_original_combination AS synonym_name_normalized,
    syn.validity,
    syn.nomenclature_status,
    sp.species_id,
    sp.sci_name                     AS accepted_sci_name,
    REPLACE(sp.sci_name, '_', ' ')  AS accepted_sci_name_space,
    sp.main_common_name,
    sp."order",
    sp.family,
    sp.genus,
    sp.iucn_status,
    sp.extinct,
    sp.domestic
FROM synonyms syn
LEFT JOIN species sp
    ON syn.species_id = sp.species_id;

-- ---------------------------------------------------------------------------
-- v_type_localities
-- Species that have numeric lat/lon in the type locality field.
-- Coordinates are from type specimen collection locality (WGS84).
-- Use for: mapping type localities in QGIS, range comparisons, etc.
--
-- ⚠️ Note: these are type specimen localities, NOT species range centroids.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_type_localities AS
SELECT
    species_id,
    sci_name,
    REPLACE(sci_name, '_', ' ')     AS sci_name_space,
    main_common_name,
    "order",
    family,
    type_locality,
    type_lat                        AS latitude,    -- WGS84 decimal degrees
    type_lon                        AS longitude,   -- WGS84 decimal degrees
    authority_author,
    authority_year,
    iucn_status,
    extinct,
    biogeographic_realm,
    country_distribution
FROM species
WHERE type_lat  IS NOT NULL
  AND type_lon  IS NOT NULL
  AND type_lat  BETWEEN -90  AND 90
  AND type_lon  BETWEEN -180 AND 180;

-- ---------------------------------------------------------------------------
-- v_type_localities_synonyms
-- Type localities from the synonyms table (each synonym may have its own
-- type specimen locality, distinct from the accepted species).
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_type_localities_synonyms AS
SELECT
    syn.syn_id,
    syn.original_combination        AS synonym_name,
    syn.accepted_sci_name,
    syn.validity,
    syn.type_lat                    AS latitude,
    syn.type_lon                    AS longitude,
    syn.type_country,
    syn.type_subregion,
    syn.holotype,
    syn.authority_citation
FROM synonyms syn
WHERE syn.type_lat IS NOT NULL
  AND syn.type_lon IS NOT NULL
  AND syn.type_lat  BETWEEN -90  AND 90
  AND syn.type_lon  BETWEEN -180 AND 180;

-- Summary
SELECT
    (SELECT COUNT(*) FROM v_species_current)          AS extant_wild_species,
    (SELECT COUNT(*) FROM v_species_all)              AS total_species,
    (SELECT COUNT(*) FROM v_synonyms)                 AS total_synonyms,
    (SELECT COUNT(*) FROM v_type_localities)          AS species_with_coordinates,
    (SELECT COUNT(*) FROM v_type_localities_synonyms) AS synonym_type_localities;
