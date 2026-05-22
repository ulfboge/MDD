# Review archive

Historical review exports and closed research notes. **Do not edit** — decisions are applied in the active files at `../`.

## `qc/`

Completed estimated-locality QC batches (2026-05). All decisions were merged into `../estimated_type_localities.csv`:

| Batch | Rows | Outcome (approx.) |
|-------|------|-------------------|
| `estimated_qc_sample*.csv` | 50 | First pilot batch |
| `estimated_qc_sample_batch2` … `batch7` | 50 each | Sequential QC |
| `estimated_qc_sample_batch_remaining*` | 691 | Final bulk pass |

Final map count: **961 proposed** (957 accept + 4 curated overrides). See `batch_remaining_summary.csv` for the last bulk counts.

Stale export removed from repo: `estimated_type_localities_qc_applied.csv` (reject coords not cleared — superseded by `apply_estimated_qc_decisions.py`).

## `museum_research/`

Closed prefix-research and snapshot docs:

- `deep-research-report*.md` — MN / Museu Nacional UFRJ investigation (implemented; see `../museum_mn_review_closure.csv`)
- `mn_vouchers_for_review*.csv` — MN review inputs (54 species)
- `museum_prefix_priority_backlog.csv` — resolved prefix additions (ZMUC, MTD, MN, …)
- `museum_prefix_wave4_backlog.*` — empty backlog snapshot (0 prefix gaps remaining)
- `museum_unmatched_compilation.md` — 2026-05-20 unmatched-voucher summary
- `Taxonomy_and_distribution_ofPresbytis_me.pdf` — local literature PDF (not in git)

Regenerating wave-4 backlog (if needed) writes fresh files to `../museum/`:

```bash
python mdd_project/scripts/build_museum_prefix_wave4_backlog.py
```
