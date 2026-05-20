# Museum matching review data

Generated review files for MDD type-specimen museum prefix matching.

Current post-audit status:

- Matched museums in app: 273
- Prefix mismatch / alias cases: 0
- Alias-style prefix gaps with count >= 2: 0
- Orphan voucher prefixes with count >= 2: 0
- Remaining actionable items: 9 (`museum_remaining_action_items.csv`)
- Unmatched-voucher QC flags: 18 (`museum_unmatched_qc_flags.csv`)
- QC review closures: 16 closed / 2 open (`museum_unmatched_qc_review.csv`)
- Standalone zero-match metadata: 7 retained (`museum_standalone_zero_match_policy.csv`)

## Files

| File | Description |
|------|-------------|
| `mn_vouchers_for_review.csv` | **54 species** with `MN` / `MN-UFRJ` voucher prefix (review input). |
| `mn_vouchers_for_review_enriched.csv` | Same 54 rows with museum identification columns (Museu Nacional UFRJ). |
| `deep-research-report.md` | Initial MN prefix research report. |
| `deep-research-report_2.md` | Updated report with longest-prefix rationale and enriched CSV plan. |
| `deep-research-report_3.md` | Städad v3 (varning om felaktigt auto-CSV; Pavan 2015 / SiBBr-källor). |
| `museum_prefix_wave4_backlog.csv` | **Wave 4 backlog** — next prefix gaps to research (risky aliases + orphans). |
| `museum_prefix_wave4_backlog.md` | Human-readable wave 4 investigation guide with priorities and notes. |
| `nhrm_type_specimens_missing_coords_geocoded.csv` | Proposed coordinates for 18 NHRM specimens (pending NRM review; not imported to MDD). |
| `museum_coverage_matched.csv` | Museums that appear in the web app filter (≥1 matched type voucher). |
| `museum_metadata_zero_matches.csv` | Institutions listed in `TypeSpecimenMetadata_v2.4.csv` but with **zero** voucher matches. |
| `museum_prefix_gap_summary.csv` | Voucher prefixes missing from metadata (alias-style and orphan cases, count ≥ 2). |
| `museum_completely_excluded_from_app.csv` | Species whose `type_voucher` prefix matches no institution abbreviation. |
| `museum_completely_excluded_prefix_counts.csv` | Prefix frequency for excluded vouchers. |
| `museum_completely_excluded_detail.csv` | Detailed per-species list for all excluded vouchers, including taxonomy, type locality, URI, and parsed prefix. |
| `museum_completely_excluded_worklist.csv` | Classified worklist for excluded vouchers (`lost_or_untraced`, `field_or_sequence_number`, `needs_primary_literature`, etc.). |
| `museum_research_candidates.csv` | Verifiable museum-prefix candidates remaining after classification. Should normally be empty when the current batch is resolved. |
| `museum_research_unresolved.csv` | Prefixes that require primary literature or direct repository confirmation; currently `ASRU` and `LSNSAU`. |
| `museum_unmatched_qc_flags.csv` | Final sanity-check flags among otherwise closed unmatched vouchers: unresolved prefixes, voucher URI signals, named collections, and person/locality labels with numbers. |
| `museum_unmatched_qc_review.csv` | Manual-review closure recommendations for each QC flag (`closed` vs `open`). |
| `museum_zero_match_metadata_review.csv` | Metadata rows with zero direct voucher matches, split into expected alias rows vs standalone zero-match rows. |
| `museum_standalone_zero_match_policy.csv` | Retention policy for metadata rows with zero current voucher matches. |
| `museum_remaining_action_items.csv` | Compact final action list: unresolved prefixes plus standalone zero-match metadata rows. Start here for follow-up work. |
| `museum_vouchers_unmatched.csv` | Unmatched voucher list. |
| `museum_prefix_mismatch_cases.csv` | Cases where parsed voucher prefix ≠ matched metadata abbreviation. |

## Regenerate

```bash
python mdd_project/scripts/setup_database.py --skip-exports
python mdd_project/scripts/audit_museum_matching.py
python mdd_project/scripts/audit_museum_excluded.py
python mdd_project/scripts/summarize_museum_gaps.py
python mdd_project/scripts/export_mn_vouchers_for_review.py
python mdd_project/scripts/build_museum_prefix_wave4_backlog.py
```

`summarize_museum_gaps.py` reads the classified excluded-voucher worklist, so run
`audit_museum_excluded.py` before it.

## Remaining manual checks

`museum_remaining_action_items.csv` is the preferred follow-up list.

- `ASRU`: MDD confirms `Scarturus_heptneri` type material as `ASRU 424`. The correct original source is Pavlenko & Denisenko (1976), *Allactaga elater heptneri*, `Zoologicheskii Zhurnal` 55(7):1073-1077. GRSciColl registers the Institute of Zoology mammal collection in Tashkent as `TASZ`/`TASZM`, and `ASRU` plausibly abbreviates Academy of Sciences Republic Uzbekistan, but open sources did not expand `ASRU` or tie `ASRU 424` to that repository.
- `LSNSAU`: Known from Aimi & Bakar (1992), *Primates* 33:191-206, as `Presbytis melalophos bicolor` holotype `LSNSAU SD 16`. Authorship links Kyoto University and Andalas University, but accessible sources did not expand `LSNSAU`; likely requires the full article/PDF or contact with Andalas University Museum Zoologi or Kyoto PRI.
- Standalone zero-match metadata rows (`ACUNHC`, `CUMV`, `DZSJRP`, `GEC`, `MNHNC`, `NMSL`, `SNMB`) are retained in `TypeSpecimenMetadata_v2.4.csv` per `museum_standalone_zero_match_policy.csv`. Remove them only if metadata should strictly contain institutions that match current MDD v2.4 vouchers.
- `museum_unmatched_qc_flags.csv` is not a prefix-add backlog. It highlights residual sanity-check cases, including lost vouchers with catalog URIs (possible future URI-based museum matching), named collection labels such as Bohmann, and locality/person labels with specimen-like numbers. Closure recommendations are in `museum_unmatched_qc_review.csv`.

## Matching rule (web app)

Institution is matched when `UPPER(type_voucher) LIKE UPPER(abbreviation) || '%'`, longest abbreviation wins.  
Example: `NHRM` does **not** match metadata codes `NR` or `RNHM` in DuckDB — a dedicated `NHRM` row was required for Naturhistoriska riksmuseet.

Example: `MN` matches `MN 31910` and `MN-UFRJ 23075`; longer codes `MNCN`, `MNHN`, and `MNZ` still win for their own vouchers.

P3 alias rows (BMNH, NMPR, MACN-MA, NSMT-M, NMNZ, OUM, CNM, etc.) point to the same institution as the shorter code but match the voucher prefix used in MDD.
