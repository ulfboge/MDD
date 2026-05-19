# Museum matching review data

Generated review files for MDD type-specimen museum prefix matching.

## Files

| File | Description |
|------|-------------|
| `mn_vouchers_for_review.csv` | **54 species** with `MN` / `MN-UFRJ` voucher prefix (review input). |
| `mn_vouchers_for_review_enriched.csv` | Same 54 rows with museum identification columns (Museu Nacional UFRJ). |
| `deep-research-report.md` | Initial MN prefix research report. |
| `deep-research-report_2.md` | Updated report with longest-prefix rationale and enriched CSV plan. |
| `museum_prefix_wave4_backlog.csv` | **Wave 4 backlog** — next prefix gaps to research (risky aliases + orphans). |
| `museum_prefix_wave4_backlog.md` | Human-readable wave 4 investigation guide with priorities and notes. |
| `nhrm_type_specimens_missing_coords_geocoded.csv` | Proposed coordinates for 18 NHRM specimens (pending NRM review; not imported to MDD). |
| `museum_coverage_matched.csv` | Museums that appear in the web app filter (≥1 matched type voucher). |
| `museum_metadata_zero_matches.csv` | Institutions listed in `TypeSpecimenMetadata_v2.4.csv` but with **zero** voucher matches. |
| `museum_prefix_gap_summary.csv` | Voucher prefixes missing from metadata (alias-style and orphan cases, count ≥ 2). |
| `museum_completely_excluded_from_app.csv` | Species whose `type_voucher` prefix matches no institution abbreviation. |
| `museum_completely_excluded_prefix_counts.csv` | Prefix frequency for excluded vouchers. |
| `museum_vouchers_unmatched.csv` | Unmatched voucher list. |
| `museum_prefix_mismatch_cases.csv` | Cases where parsed voucher prefix ≠ matched metadata abbreviation. |

## Regenerate

```bash
python mdd_project/scripts/setup_database.py --skip-exports
python mdd_project/scripts/audit_museum_matching.py
python mdd_project/scripts/summarize_museum_gaps.py
python mdd_project/scripts/audit_museum_excluded.py
python mdd_project/scripts/export_mn_vouchers_for_review.py
python mdd_project/scripts/build_museum_prefix_wave4_backlog.py
```

## Matching rule (web app)

Institution is matched when `UPPER(type_voucher) LIKE UPPER(abbreviation) || '%'`, longest abbreviation wins.  
Example: `NHRM` does **not** match metadata codes `NR` or `RNHM` in DuckDB — a dedicated `NHRM` row was required for Naturhistoriska riksmuseet.

Example: `MN` matches `MN 31910` and `MN-UFRJ 23075`; longer codes `MNCN`, `MNHN`, and `MNZ` still win for their own vouchers.

P3 alias rows (BMNH, NMPR, MACN-MA, NSMT-M, NMNZ, OUM, CNM, etc.) point to the same institution as the shorter code but match the voucher prefix used in MDD.
