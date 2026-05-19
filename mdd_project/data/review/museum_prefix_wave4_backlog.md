# Museum prefix wave 4 — investigation backlog

Generated after P3 alias fixes (BMNH, NMPR, MACN-MA, NSMT-M, NMNZ, OUM, CNM, …).
Use this file to research and resolve remaining prefix gaps before updating `TypeSpecimenMetadata_v2.4.csv`.

## Current snapshot

- **Completely unmatched vouchers:** 480 species
- **Prefix gaps in this backlog:** 1 rows
- **Not fixable via metadata:** `UNTRACED` (234) + `LOST` (136) = 370 species

## Priority legend

| Priority | Meaning |
|----------|---------|
| **P4-risky** | Wrong alias would mis-assign museum |
| **P4b-easy-alias** | Likely alias to existing institution; verify then add row |
| **P4b-variant** | Odd BMNH catalog strings; may need parser or extra alias |
| **P4c-orphan-high/medium** | No related metadata code; needs institution research (≥3 sp.) |
| **P4d-orphan-low** | Same, 2 species |

## P4-risky — resolve first

No current P4-risky prefixes after the latest metadata fixes.


## P4b — likely aliases (verify institution, then add metadata row)


## P4c — orphan prefixes (≥3 species, needs new institution row)


## P4d — orphan prefixes (2 species)

See `museum_prefix_wave4_backlog.csv` for the full list.

## Workflow

1. Pick a prefix from **P4-risky** or **P4c-orphan-high**.
2. Confirm institution from original publication / collection database.
3. Add row to `TypeSpecimenMetadata_v2.4.csv` (or alias if same institution).
4. Rebuild: `python mdd_project/scripts/setup_database.py --skip-exports`
5. Regenerate audits: `python mdd_project/scripts/audit_museum_matching.py`

## Regenerate this file

```bash
python mdd_project/scripts/build_museum_prefix_wave4_backlog.py
```
