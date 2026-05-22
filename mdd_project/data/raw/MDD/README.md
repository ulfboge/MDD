# MDD v2.4 raw data

Official [Mammal Diversity Database v2.4](https://www.mammaldiversity.org/) CSV exports used by `setup_database.py`.

| File | Role |
|------|------|
| `MDD_v2.4_6871species.csv` | Species taxonomy (6,871 rows) |
| `Species_Syn_v2.4.csv` | Nomenclatural synonyms |
| `TypeSpecimenMetadata_v2.4.csv` | Museum abbreviations + type specimen metadata |
| `META_v2.4.csv` | Column documentation |
| `Diff_v2.3-v2.4.csv` | Changes since v2.3 |
| `Diff-AllChanges_v2.3-2.4.csv` | Extended diff export (not imported to DuckDB) |
| `release.toml` | Release metadata (version, Zenodo citation) |

Download: [Zenodo 10.5281/zenodo.18135819](https://doi.org/10.5281/zenodo.18135819)

Path constants: `mdd_project/scripts/data_paths.py`.
