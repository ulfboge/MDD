# MDD Project — Session Status Log

**Last updated:** 2026-05-18  
**Repo:** `c:\Users\galag\GitHub\MDD`  
**Remote:** https://github.com/ulfboge/MDD.git (`main`, commit `c7d0051`)

---

## Completed

- **MDD v2.4 → DuckDB** — `mdd_project/data/processed/mdd.duckdb`; taxonomy schema, views, harmonization script
- **FastAPI** — species, synonyms, type-localities, occurrences, health endpoints
- **GBIF import pipeline** — `gbif_import.py`; observations table separate from DB setup
- **React / MapLibre web map** — layer help text; species-specific type locality (0–1); optional “show all” (~1941)
- **Type locality** — MDD geocoded coords only (~28%); text-only for many species (e.g. *Pan troglodytes*, *Galago moholi*, *Ursus arctos*)
- **Docker** — single container (nginx + uvicorn); tested locally on port **10000**; container name `mdd-map-run` may still be running
- **Render deploy prep** — `render.yaml`, `DEPLOY_RENDER.md`; pushed to GitHub; CSVs in repo
- **User state** — on Render Blueprint page, ready to Deploy (service **mdd-map**)

---

## In progress / user action needed

- **Render Blueprint** — click **Deploy Blueprint**, wait for build, note live URL
- **Free tier** — cold starts; no runtime `gbif_import` on Render unless baked into the image

---

## Tomorrow — next steps (prioritized)

1. Confirm Render deploy succeeded; test `/health` and map URL
2. Optional: bake demo GBIF occurrences into Docker image for live demo species
3. Optional: Git LFS if GitHub complains about Species_Syn CSV size
4. Custom domain on Render if desired
5. Future: QGIS templates, more GBIF imports, PostgreSQL path

---

## Quick commands

| Task | Command |
|------|---------|
| Local Docker | `docker run -p 10000:10000 -e PORT=10000 mdd-map` |
| Rebuild DB | `python mdd_project/scripts/setup_database.py` |
| GBIF import | `python mdd_project/scripts/gbif_import.py --species "..." --limit 200` *(stop API first on Windows)* |
| Local API | `uvicorn` (see project docs) |
| Local frontend | `npm run dev` in `web/frontend` |

---

## Key paths

| Item | Path |
|------|------|
| Repo root | `c:\Users\galag\GitHub\MDD` |
| Project README | `mdd_project/README.md` |
| Render deploy guide | `mdd_project/DEPLOY_RENDER.md` |
| DuckDB | `mdd_project/data/processed/mdd.duckdb` |

---

*Handoff log for next session — not committed unless you choose to add it to git.*
