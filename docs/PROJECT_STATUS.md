# MDD Project — Session Status Log

**Last updated:** 2026-05-20  
**Repo:** `c:\Users\galag\GitHub\MDD`  
**Remote:** https://github.com/ulfboge/MDD.git (`main`)  
**Live app:** https://mdd-map.onrender.com (Render free tier, service **mdd-map**)

Review data layout: `mdd_project/data/review/{geocoding,museum,qc,archive}/` — see `mdd_project/data/review/README.md`.

---

## Session 2026-05-20 (continued)

### Country-aware geocoding + QC automation
- New module: `mdd_project/scripts/geocode_country_validate.py` — country hints from type locality, embassy rejection, Nominatim match validation.
- `geocode_type_localities.py` now prefers locality country over museum country in queries and rejects bad Nominatim hits (`nominatim_rejected`).
- `suggest_estimated_qc.py` — auto-fills `qc_decision` / `qc_notes` on QC sample.
- `apply_estimated_qc_decisions.py` — applies QC decisions back to `estimated_type_localities.csv`.
- **QC sample pre-filled:** 31 accept, 19 reject in `estimated_qc_sample.csv` (review flagged rows before applying).

**Next:** skim auto-suggestions, adjust any `review`/`accept` you disagree with, then:
```bash
python mdd_project/scripts/apply_estimated_qc_decisions.py
python mdd_project/scripts/import_estimated_type_localities.py
```
Optional re-geocode pass on rejected rows with improved queries (no `--overwrite` on cache unless retrying).

---

## Where we are

The **MDD web map** is deployed and working on Render. The stack is a single Docker container (nginx + uvicorn + baked DuckDB). Users can search species, view official type localities (~1,941 geocoded), estimated review localities (~1,647 proposed), and GBIF occurrence dots for **Primates** (513 species, up to 100 records each, baked at build time).

**Local DuckDB** (`mdd.duckdb`) is ahead of what's in git: it includes extra GBIF imports (Galagidae batch + manual species imports). Git only tracks CSVs and scripts — not the database file.

**Estimated type-locality geocoding** has completed a full pass plus a retry. Output is in `mdd_project/data/review/estimated_type_localities.csv` (4,930 rows: 1,647 proposed, 2,249 no_estimate, 1,034 skipped). A 50-row QC sample was exported for manual review.

---

## Completed this session (2026-05-18 → 2026-05-20)

### GBIF occurrence layer (fixed)
- Species autocomplete now queries the API with `?q=` instead of filtering only the first 10 species client-side.
- Occurrences load per selected species; race condition with global type-locality prefetch fixed.
- API tightened: `GET /occurrences/{species}` matches `mdd_sci_name` only; `matched_only=True` by default.
- TypeScript build error on Render fixed (`setData` typing).
- Voucher URI links (VertNet/iDigBio) in occurrence popups.
- GBIF layer colour: `#ff7043`.

### Docker / Render
- **Render deploy live** at https://mdd-map.onrender.com — `/health` OK.
- Dockerfile bakes **Primates GBIF demo** (`--from-mdd --order Primates --limit-per-species 100`) — ~513 species including Galagidae.
- Dockerfile copies `estimated_type_localities.csv` so estimated layer works on Render.
- Build time for Primates step: ~20–40 min on Render free tier.

### Estimated type-locality geocoding
- Full geocoding pass + retry recovered **702 additional proposals** (total 1,647 proposed).
- Script improvements: `--only-review-status`, `--only-geocode-method`, `--retry-cache-errors`; better Nominatim query building.
- QC workflow: `export_estimated_qc_sample.py` + docs in `mdd_project/data/review/README.md`.
- Generated `estimated_qc_sample.csv` (50 rows: 30 high, 20 medium confidence).
- **QC finding:** many Nominatim `high` hits are geographically wrong (e.g. Panama → New Mexico). Good rows include *Gorilla beringei* → Mount Sabyinyo, *Hylomyscus vulcanorum* (curated).

### UI / language
- About panel and IUCN labels reverted to **English** (Swedish experiment removed).
- IUCN Red List link on species card.
- "Show all MDD type localities" toggle visible when a species is selected (under Layers).

### Museum / review work
- `museum_remaining_action_items.csv`: 7 standalone zero-match retain policies left.
- **ASRU** still `not_confirmed_from_pdf` — needs Pavlenko & Denisenko (1976) paper.
- **LSNSAU** confirmed from PDF.

---

## Verified today (2026-05-20)

| Check | Result |
|-------|--------|
| Render `/health` | OK |
| Render `/api/occurrences/Gorilla_beringei` | 100 records (baked Primates import) |
| Render `/api/type-localities/coverage/summary` | OK — 6,871 species, 1,647 estimated on map |
| Local DuckDB observations | 1,563 rows, 21 species (includes Galagidae batch + Gorilla import) |
| Local estimated proposed | 1,647 |
| *Gorilla beringei* official type coords | None in MDD v2.4 (expected — use estimated layer) |
| *Gorilla beringei* estimated locality | Mount Sabyinyo (in QC sample, high confidence) |

**Screenshot note:** A sidebar showing "CR · Akut hotad", GBIF count 0, and coverage error was from an **older build or local dev without API running**. Current Render has English labels, Gorilla GBIF data, and working coverage stats. Hard refresh if cached.

---

## In progress / user action needed

1. **QC review** — fill `qc_decision` column in `mdd_project/data/review/estimated_qc_sample.csv` (many `high` Nominatim rows should be `reject`).
2. **Commit QC sample** — `estimated_qc_sample.csv` is modified locally, not yet committed.
3. **ASRU museum** — obtain source PDF for final confirmation.
4. **Render cold starts** — first request after sleep can take 30–60+ seconds; coverage panel may briefly fail until API is warm.

---

## Next session — suggested priorities

1. Finish QC sample review; apply decisions back to `estimated_type_localities.csv`.
2. Commit QC sample (and any review decisions) when ready.
3. Consider curating/fixing systematic Nominatim false positives (country-aware filtering?).
4. Optional: import more GBIF families locally for richer local demos.
5. Optional: custom domain on Render.

---

## Key commits (recent)

| Commit | Summary |
|--------|---------|
| `632bbc6` | QC export script, Primates GBIF bake, English UI |
| `6cc3f87` | Filter map layers to selected species; tighten GBIF queries |
| `98b24f1` | Bake Galagidae GBIF + estimated localities into Docker |
| `fc9df55` | Fix Render TS build error; expand data-source UI |
| `fa0450c` | Retry geocoding — +702 proposals |
| `618a56d` | Fix GBIF layer loading and species search |
| `56b2363` | First full estimated type-locality geocoding pass |

---

## Quick commands

| Task | Command |
|------|---------|
| Local Docker | `docker build -t mdd-map .` then `docker run -p 10000:10000 -e PORT=10000 mdd-map` |
| Local API | `$env:PYTHONPATH='.'; uvicorn mdd_project.web.api.main:app --reload --port 8000` |
| Local frontend | `cd mdd_project/web/frontend && npm run dev` |
| Rebuild DB | `python mdd_project/scripts/setup_database.py` |
| GBIF import | `python mdd_project/scripts/gbif_import.py --species "..." --limit 200` *(stop API first on Windows)* |
| Import estimated CSV | `python mdd_project/scripts/import_estimated_type_localities.py` |
| Export QC sample | `python mdd_project/scripts/export_estimated_qc_sample.py` |
| Geocode (retry) | `python mdd_project/scripts/geocode_type_localities.py --retry-cache-errors` |

---

## Key paths

| Item | Path |
|------|------|
| Repo root | `c:\Users\galag\GitHub\MDD` |
| DuckDB (local, gitignored) | `mdd_project/data/processed/mdd.duckdb` |
| Estimated localities CSV | `mdd_project/data/review/geocoding/estimated_type_localities.csv` |
| QC sample (new batches) | `mdd_project/data/review/qc/estimated_qc_sample.csv` |
| Nominatim cache | `mdd_project/data/review/geocoding/nominatim_geocode_cache.json` |
| Web frontend | `mdd_project/web/frontend/src/App.tsx` |
| FastAPI | `mdd_project/web/api/main.py` |
| Render deploy guide | `mdd_project/DEPLOY_RENDER.md` |
| Dockerfile | `Dockerfile` (repo root) |

---

*Handoff log for next session — not committed unless you choose to add it to git.*
