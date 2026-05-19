# Museum matching review data

Generated review files for MDD type-specimen museum prefix matching.

## Files

| File | Description |
|------|-------------|
| `museum_prefix_priority_backlog.csv` | **Prioritized backlog** of museum prefixes to add/fix in metadata (P1–P4). |
| `nhrm_type_specimens_missing_coords_geocoded.csv` | Proposed coordinates for 18 NHRM specimens (pending NRM review; not imported to MDD). |
| `museum_coverage_matched.csv` | **108 museums** that appear in the web app filter (≥1 matched type voucher). |
| `museum_metadata_zero_matches.csv` | **31 institutions** listed in `TypeSpecimenMetadata_v2.4.csv` but with **zero** voucher matches. |
| `museum_prefix_gap_summary.csv` | Voucher prefixes missing from metadata (alias-style and orphan cases, count ≥ 2). |
| `museum_completely_excluded_from_app.csv` | **816 species** whose `type_voucher` prefix matches no institution abbreviation (NRM-style exclusion before alias fix). |
| `museum_completely_excluded_prefix_counts.csv` | Prefix frequency for excluded vouchers. |
| `museum_vouchers_unmatched.csv` | Same 816 species (unmatched list). |
| `museum_prefix_mismatch_cases.csv` | Cases where parsed voucher prefix ≠ matched metadata abbreviation. |

## Regenerate

```bash
python mdd_project/scripts/audit_museum_matching.py
python mdd_project/scripts/summarize_museum_gaps.py
python mdd_project/scripts/audit_museum_excluded.py
```

## Matching rule (web app)

Institution is matched when `UPPER(type_voucher) LIKE UPPER(abbreviation) || '%'`, longest abbreviation wins.  
Example: `NHRM` does **not** match metadata codes `NR` or `RNHM` in DuckDB — a dedicated `NHRM` row was required for Naturhistoriska riksmuseet.
