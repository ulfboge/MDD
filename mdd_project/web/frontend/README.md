# MDD Web Map — React + MapLibre GL JS

Interactive web map for the Mammal Diversity Database.

## Tech stack

| Layer | Tool |
|---|---|
| Build | Vite 6 + TypeScript |
| UI | React 18 |
| Map | MapLibre GL JS 5 |
| Basemap | CARTO Positron light (no API key) |
| API | FastAPI proxy at `/api/*` → `:8000` |

## Getting started

```bash
# 1. Install dependencies
cd mdd_project/web/frontend
npm install

# 2. Start FastAPI in a separate terminal first
cd ../..       # → mdd_project/
uvicorn web.api.main:app --reload --port 8000

# 3. Start Vite dev server (proxies /api → :8000)
npm run dev
# → http://localhost:5173
```

## Features

- **Type localities layer** — 4,000+ georeferenced MDD type specimens, coloured by IUCN status
- **Species search** — type any mammal name → autocomplete → fly to type locality
- **GBIF occurrences layer** — orange dots loaded when a species is selected
  (requires data in DB from `gbif_import.py`)
- **Popup info** — click any point for details

## Loading GBIF occurrences

The map shows GBIF occurrences from the local DuckDB database.
Run the import script once to populate data:

```bash
# Single species (from repo root)
python mdd_project/scripts/gbif_import.py --species "Ursus arctos" --limit 500

# Entire family
python mdd_project/scripts/gbif_import.py --from-mdd --family Galagidae --limit-per-species 100
```

## Build for production

```bash
npm run build
# output in dist/
```

## Vite proxy

`vite.config.ts` proxies all `/api/*` requests to `http://localhost:8000`
(strips the `/api` prefix).  No CORS issues during development.
