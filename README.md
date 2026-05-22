# MDD — Mammal Diversity Database web map

Interactive map of MDD v2.4 type localities, estimated review coordinates, and GBIF occurrences.

**Live:** https://mdd-map.onrender.com

## Quick start

```bash
pip install -r requirements.txt
python mdd_project/scripts/setup_database.py
uvicorn mdd_project.web.api.main:app --reload --port 8000
# separate terminal:
cd mdd_project/web/frontend && npm install && npm run dev
```

## Documentation

| Topic | Location |
|-------|----------|
| Setup, DuckDB, scripts | [`mdd_project/README.md`](mdd_project/README.md) |
| All project docs | [`docs/README.md`](docs/README.md) |
| Render deployment | [`docs/DEPLOY_RENDER.md`](docs/DEPLOY_RENDER.md) |
| Session log | [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) |
| Review / QC data | [`mdd_project/data/review/README.md`](mdd_project/data/review/README.md) |
| MDD v2.4 CSV inputs | [`mdd_project/data/raw/MDD/`](mdd_project/data/raw/MDD/) |

## Repo layout

```
MDD/
├── docs/                  ← deployment guides, session log, QGIS notes
├── deploy/                ← nginx template for Docker
├── mdd_project/
│   ├── data/raw/MDD/      ← MDD v2.4 CSV source files
│   ├── data/review/       ← geocoding + museum audit outputs
│   ├── scripts/           ← DuckDB build, GBIF import, geocoding
│   └── web/               ← FastAPI + Vite frontend
├── Dockerfile
├── render.yaml
└── requirements.txt
```
