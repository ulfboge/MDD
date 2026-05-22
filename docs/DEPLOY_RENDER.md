# Deploy MDD to Render (single Docker container)

One container runs **nginx** (static Vite build + reverse proxy) and **uvicorn** (FastAPI over `mdd.duckdb`). DuckDB is built from MDD v2.4 CSVs during the Docker image build.

## Prerequisites

1. Push this repository to GitHub (or GitLab).
2. Ensure the MDD v2.4 CSV files are in **`mdd_project/data/raw/MDD/`** (required for the image build):
   - `MDD_v2.4_6871species.csv`
   - `Species_Syn_v2.4.csv`
   - `TypeSpecimenMetadata_v2.4.csv`
   - `META_v2.4.csv`
   - `Diff_v2.3-v2.4.csv`

   Download from [mammaldiversity.org](https://www.mammaldiversity.org/) or [Zenodo](https://doi.org/10.5281/zenodo.18135819).

## Option A — Blueprint (`render.yaml`)

1. [Render Dashboard](https://dashboard.render.com/) → **Blueprints** → **New Blueprint Instance**.
2. Connect the repository; Render reads `render.yaml` at the repo root.
3. Confirm the web service **mdd-map** and deploy.

## Option B — Manual Web Service

1. **New** → **Web Service** → connect the repository.
2. **Runtime**: Docker.
3. **Dockerfile path**: `./Dockerfile` (repo root).
4. **Health check path**: `/health`.
5. **Environment**: `PORT` is set by Render (Blueprint uses `10000`; Render injects `PORT` at runtime — the entrypoint reads it).

## Build time

- **Frontend** (`npm ci` + `vite build`): ~1–2 minutes.
- **DuckDB** (`setup_database.py --skip-exports` + estimated CSV): ~1–3 minutes depending on plan CPU.
- **GBIF demo import** (Galagidae, 100 records/species): ~2–5 minutes (network calls to api.gbif.org).
- **Total first deploy**: often **8–15 minutes** on free tier.

Image size is typically **~800 MB–1.2 GB** (Python slim + nginx + ~116 MB DuckDB + dependencies).

## Local smoke test

```bash
docker build -t mdd-map .
docker run --rm -p 10000:10000 -e PORT=10000 mdd-map
```

- App: http://localhost:10000  
- API (via proxy): http://localhost:10000/api/species?limit=5  
- Health: http://localhost:10000/health  

## Architecture

| Path | Handler |
|------|---------|
| `/`, `/assets/*` | nginx → Vite `dist/` |
| `/api/*` | nginx → uvicorn `:8000` ( `/api` stripped, same as Vite dev proxy ) |
| `/health` | nginx → FastAPI `/health` |

Frontend uses `fetch('/api/...')` so the UI and API share one origin (no CORS).

## GBIF occurrences on Render

The Docker build **pre-bakes** a small GBIF demo dataset:

```bash
python mdd_project/scripts/gbif_import.py --from-mdd --order Primates --limit-per-species 100 --no-export
```

That gives orange occurrence dots for **Primates** (513 species, including Galagidae) when selected in the map. The per-species cap keeps Docker build time manageable (~20–40 min for this step on Render); increase `--limit-per-species` in the Dockerfile if you want denser maps.

To change the demo set, edit the `gbif_import.py` step in the repo-root `Dockerfile` (e.g. another `--family` or `--order`). Do **not** import full-mammal GBIF into the image — build time and image size would explode.

The `observations` table is **not** created by `setup_database.py` alone; it appears only after this build step (or a manual local import).

Type localities (~1,941 official + ~1,647 estimated review points) work from the baked taxonomy DB.

## Render free tier limitations

- **Sleep**: Free web services spin down after ~15 minutes of inactivity; first request after sleep can take **30–60+ seconds** (cold start + DuckDB load).
- **Ephemeral disk**: Anything written at runtime (e.g. GBIF import) is **lost** on redeploy/restart unless you add a [persistent disk](https://render.com/docs/disks) (paid).
- **Build minutes / bandwidth**: Large CSVs in the repo increase clone and build time; keep CSVs in the repo only if license/redistribution allows.
- **RAM/CPU**: Heavy DuckDB queries under load may be slow on free instances.

## Custom domain

Set **Custom Domain** on the Render service. Vite `base` is `/` — no path prefix changes needed for `*.onrender.com` or your own domain.

## Files

| File | Role |
|------|------|
| `Dockerfile` | Multi-stage build (Node → Python DB → runtime) |
| `deploy/nginx.conf.template` | nginx listen `$PORT`, `/api/` proxy, SPA fallback |
| `docker-entrypoint.sh` | Start uvicorn, then nginx foreground |
| `render.yaml` | Blueprint definition |
| `.dockerignore` | Smaller build context |
