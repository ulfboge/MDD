-- =============================================================================
-- import_mdd.sql  —  MDD v2.4 DuckDB schema & CSV ingestion
-- Run via: setup_database.py (which substitutes :raw_dir at runtime)
-- All tables use VARCHAR for taxonomy strings; numerics cast explicitly.
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS taxonomy;

-- ---------------------------------------------------------------------------
-- 1. SPECIES  (main MDD checklist, 6 871 species)
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS species;
CREATE TABLE species AS
SELECT
    sciName                                        AS sci_name,
    CAST(id AS INTEGER)                            AS species_id,
    CAST(phylosort AS INTEGER)                     AS phylosort,
    mainCommonName                                 AS main_common_name,
    otherCommonNames                               AS other_common_names,
    subclass, infraclass, magnorder, superorder,
    "order",
    suborder, infraorder, parvorder, superfamily,
    family, subfamily, tribe, subtribe,
    genus, subgenus,
    specificEpithet                                AS specific_epithet,
    authoritySpeciesAuthor                         AS authority_author,
    CAST(TRY_CAST(authoritySpeciesYear AS INTEGER) AS INTEGER)
                                                   AS authority_year,
    CAST(authorityParentheses AS BOOLEAN)          AS authority_parentheses,
    originalNameCombination                        AS original_name_combination,
    authoritySpeciesCitation                       AS authority_citation,
    authoritySpeciesLink                           AS authority_link,
    typeVoucher                                    AS type_voucher,
    typeKind                                       AS type_kind,
    typeVoucherURIs                                AS type_voucher_uris,
    typeLocality                                   AS type_locality,
    TRY_CAST(typeLocalityLatitude  AS DOUBLE)      AS type_lat,
    TRY_CAST(typeLocalityLongitude AS DOUBLE)      AS type_lon,
    nominalNames                                   AS nominal_names,
    subspecies,
    taxonomyNotes                                  AS taxonomy_notes,
    taxonomyNotesCitation                          AS taxonomy_notes_citation,
    distributionNotes                              AS distribution_notes,
    distributionNotesCitation                      AS distribution_notes_citation,
    subregionDistribution                          AS subregion_distribution,
    countryDistribution                            AS country_distribution,
    continentDistribution                          AS continent_distribution,
    biogeographicRealm                             AS biogeographic_realm,
    iucnStatus                                     AS iucn_status,
    CAST(extinct  AS BOOLEAN)                      AS extinct,
    CAST(domestic AS BOOLEAN)                      AS domestic,
    CAST(flagged  AS BOOLEAN)                      AS flagged,
    CMW_sciName                                    AS cmw_sci_name,
    CAST(TRY_CAST(diffSinceCMW AS INTEGER) AS INTEGER)
                                                   AS diff_since_cmw,
    MSW3_matchtype                                 AS msw3_matchtype,
    MSW3_sciName                                   AS msw3_sci_name,
    CAST(TRY_CAST(diffSinceMSW3 AS INTEGER) AS INTEGER)
                                                   AS diff_since_msw3
FROM read_csv(
    :species_csv,
    header = true,
    encoding = 'utf-8',
    ignore_errors = true,
    quote = '"',
    escape = '"'
);

-- Validate row count (run after table creation)
SELECT 'species rows loaded: ' || COUNT(*) AS check FROM species;

-- ---------------------------------------------------------------------------
-- 2. SYNONYMS  (Species_Syn_v2.4.csv)
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS synonyms;
CREATE TABLE synonyms AS
SELECT
    CAST(MDD_syn_ID AS BIGINT)                     AS syn_id,
    MDD_species                                    AS accepted_sci_name,
    MDD_root_name                                  AS root_name,
    MDD_author                                     AS author,
    CAST(TRY_CAST(MDD_year AS INTEGER) AS INTEGER) AS year,
    CAST(TRY_CAST(MDD_authority_parentheses AS BOOLEAN) AS BOOLEAN)
                                                   AS authority_parentheses,
    MDD_nomenclature_status                        AS nomenclature_status,
    MDD_validity                                   AS validity,
    MDD_original_combination                       AS original_combination,
    MDD_normalized_original_combination            AS normalized_original_combination,
    MDD_original_rank                              AS original_rank,
    MDD_authority_citation                         AS authority_citation,
    MDD_authority_link                             AS authority_link,
    MDD_authority_page_link                        AS authority_page_link,
    MDD_old_type_locality                          AS old_type_locality,
    MDD_original_type_locality                     AS original_type_locality,
    MDD_emended_type_locality                      AS emended_type_locality,
    TRY_CAST(MDD_type_latitude  AS DOUBLE)         AS type_lat,
    TRY_CAST(MDD_type_longitude AS DOUBLE)         AS type_lon,
    MDD_type_country                               AS type_country,
    MDD_type_subregion                             AS type_subregion,
    MDD_holotype                                   AS holotype,
    MDD_type_kind                                  AS type_kind,
    MDD_type_specimen_link                         AS type_specimen_link,
    MDD_order                                      AS "order",
    MDD_family                                     AS family,
    MDD_genus                                      AS genus,
    MDD_specificEpithet                            AS specific_epithet,
    MDD_subspecificEpithet                         AS subspecific_epithet,
    MDD_variant_of                                 AS variant_of,
    MDD_senior_homonym                             AS senior_homonym,
    CAST(TRY_CAST(Hesp_id AS BIGINT) AS BIGINT)   AS hesp_id,
    CAST(TRY_CAST(MDD_species_id AS INTEGER) AS INTEGER)
                                                   AS species_id,
    MDD_name_usages                                AS name_usages,
    MDD_comments                                   AS comments
FROM read_csv(
    :synonyms_csv,
    header = true,
    encoding = 'utf-8',
    ignore_errors = true,
    quote = '"',
    escape = '"'
);

SELECT 'synonyms rows loaded: ' || COUNT(*) AS check FROM synonyms;

-- ---------------------------------------------------------------------------
-- 3. TYPE SPECIMENS  (TypeSpecimenMetadata_v2.4.csv)
--    This file contains institution abbreviations + full names, not per-species
--    type specimen records, so we import it as-is.
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS type_specimen_institutions;
CREATE TABLE type_specimen_institutions AS
SELECT
    ABBREVIATION                                   AS abbreviation,
    "FULL NAME"                                    AS full_name,
    "City and Country"                             AS city_and_country,
    "Synonyms/Notes"                               AS synonyms_notes,
    "ONLINE WEBSITE/DATABASE IF AVAILABLE"         AS website
FROM read_csv(
    :type_specimen_csv,
    header = true,
    encoding = 'utf-8',
    ignore_errors = true,
    quote = '"',
    escape = '"'
);

SELECT 'type_specimen_institutions rows loaded: ' || COUNT(*) AS check FROM type_specimen_institutions;

-- ---------------------------------------------------------------------------
-- 4. META  (META_v2.4.csv — column documentation)
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS meta;
CREATE TABLE meta AS
SELECT
    Tabs                                           AS tab_name,
    Columns                                        AS column_name,
    Explanation                                    AS explanation
FROM read_csv(
    :meta_csv,
    header = true,
    encoding = 'utf-8',
    ignore_errors = true,
    quote = '"',
    escape = '"'
);

SELECT 'meta rows loaded: ' || COUNT(*) AS check FROM meta;

-- ---------------------------------------------------------------------------
-- 5. DIFF  (Diff_v2.3-v2.4.csv — changes between MDD versions)
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS version_diff;
CREATE TABLE version_diff AS
SELECT
    "MDDv2.3_Name"                                 AS name_v23,
    "MDDv2.4_Name"                                 AS name_v24,
    Comment                                        AS comment,
    Category                                       AS category,
    Reference                                      AS reference
FROM read_csv(
    :diff_csv,
    header = true,
    encoding = 'utf-8',
    ignore_errors = true,
    quote = '"',
    escape = '"'
);

SELECT 'version_diff rows loaded: ' || COUNT(*) AS check FROM version_diff;

-- ---------------------------------------------------------------------------
-- 6. INDEXES on join keys
-- ---------------------------------------------------------------------------
CREATE UNIQUE INDEX IF NOT EXISTS idx_species_sci_name   ON species (sci_name);
CREATE UNIQUE INDEX IF NOT EXISTS idx_species_id         ON species (species_id);
CREATE INDEX IF NOT EXISTS idx_synonyms_accepted         ON synonyms (accepted_sci_name);
CREATE INDEX IF NOT EXISTS idx_synonyms_orig             ON synonyms (original_combination);
CREATE INDEX IF NOT EXISTS idx_synonyms_species_id       ON synonyms (species_id);
CREATE INDEX IF NOT EXISTS idx_synonyms_validity         ON synonyms (validity);
CREATE INDEX IF NOT EXISTS idx_type_inst_abbr            ON type_specimen_institutions (abbreviation);

SELECT 'Schema and indexes complete.' AS status;
