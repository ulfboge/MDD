# MDD FastAPI — Species & Taxonomy REST API

Lightweight REST API serving MDD v2.4 taxonomy, synonyms, and type localities from
a local DuckDB database.  No server needed — DuckDB runs in-process.

## Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Framework | FastAPI | Async, auto-docs (Swagger UI), Pydantic validation |
| Database  | DuckDB (via `duckdb` Python package) | Zero-server, in-process, reads Parquet/GeoParquet directly |
| Geometry  | Stub — GeoJSON via ST_AsGeoJSON (future) | |
| Cache     | In-process dict or Redis | Optional for high-traffic deployments |

## Quickstart

```bash
# 1. Install API dependencies
pip install fastapi "uvicorn[standard]"

# 2. Build the database (if not already done)
python mdd_project/scripts/setup_database.py

# 3. Start the API server (run from repo root)
uvicorn mdd_project.web.api.main:app --reload --port 8000
# OR from mdd_project/:
#   uvicorn web.api.main:app --reload --port 8000

# 4. Open docs
# → http://localhost:8000/docs   (Swagger UI)
# → http://localhost:8000/redoc  (ReDoc)
```

## Implemented endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /species` | List/filter species (`?order=Primates&family=Galagidae&limit=100`) |
| `GET /species/{name}` | Single species by scientific name (underscore or space) |
| `GET /synonyms/{name}` | All synonyms for an accepted species name |
| `GET /occurrences/{species}` | Stub — returns empty list + TODO message |
| `GET /health` | Liveness probe |

## Example requests

```bash
# All Galagidae
curl "http://localhost:8000/species?family=Galagidae"

# Single species (underscore or space format both work)
curl "http://localhost:8000/species/Otolemur_crassicaudatus"
curl "http://localhost:8000/species/Otolemur%20crassicaudatus"

# Synonyms
curl "http://localhost:8000/synonyms/Galago_senegalensis"

# All Primates (max 500)
curl "http://localhost:8000/species?order=Primates&limit=500"
```

## Planned endpoints (future)

```
GET /synonyms/resolve?name=X    → resolve any name to current MDD accepted name
GET /type-localities            → GeoJSON FeatureCollection of type localities
GET /search?q=<text>            → full-text search across sci_name, common name, synonyms
```

## DuckDB connection pattern

```python
import duckdb
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "processed" / "mdd.duckdb"

def get_conn():
    # Open read-only for concurrent API access
    return duckdb.connect(str(DB_PATH), read_only=True)
```
