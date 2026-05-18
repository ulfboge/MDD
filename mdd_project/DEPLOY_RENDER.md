# Deploy MDD to Render (single Docker container)

One container runs **nginx** (static Vite build + reverse proxy) and **uvicorn** (FastAPI over `mdd.duckdb`). DuckDB is built from MDD v2.4 CSVs during the Docker image build.

## Prerequisites

1. Push this repository to GitHub (or GitLab).
2. Ensure these CSV files are in the **repo root** (required for the image build):
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
- **DuckDB** (`setup_database.py --skip-exports`): ~1–3 minutes depending on plan CPU.
- **Total first deploy**: often **5–10 minutes** on free tier.

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

`setup_database.py` does **not** create the `observations` table. On the **free** tier:

- Do **not** run `gbif_import.py` at container startup (slow, network-heavy, ephemeral disk).
- Occurrence dots stay empty unless you **pre-bake** a small demo DB in the image (run import locally, commit or copy `mdd.duckdb` — not recommended for full GBIF data) or attach a **persistent disk** and import once on a paid instance.

Type localities (~1,941 points) work out of the box from the baked taxonomy DB.

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
