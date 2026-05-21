# MDD — single-container image (nginx + uvicorn + DuckDB) for Render
# Build: docker build -t mdd-map .
# Run:   docker run -p 10000:10000 -e PORT=10000 mdd-map

# -----------------------------------------------------------------------------
# Stage 1: Vite frontend → dist/
# -----------------------------------------------------------------------------
FROM node:22-alpine AS frontend

WORKDIR /build
COPY mdd_project/web/frontend/package.json mdd_project/web/frontend/package-lock.json ./
RUN npm ci

COPY mdd_project/web/frontend/ ./
RUN npm run build

# -----------------------------------------------------------------------------
# Stage 2: Python — install deps and build mdd.duckdb from CSVs
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS python-builder

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mdd_project/scripts/ mdd_project/scripts/
RUN mkdir -p mdd_project/data/processed

# MDD v2.4 CSVs (repo root); setup_database.py also checks REPO_ROOT
COPY MDD_v2.4_6871species.csv Species_Syn_v2.4.csv TypeSpecimenMetadata_v2.4.csv META_v2.4.csv Diff_v2.3-v2.4.csv ./

# Review CSV → estimated type localities table (separate from official MDD coords)
COPY mdd_project/data/review/estimated_type_localities.csv mdd_project/data/review/estimated_type_localities.csv

RUN python mdd_project/scripts/setup_database.py --skip-exports

# Demo GBIF occurrences for galagos (Galagidae) — baked into image for Render
RUN python mdd_project/scripts/gbif_import.py \
    --from-mdd --family Galagidae --limit-per-species 300 --no-export

# -----------------------------------------------------------------------------
# Stage 3: Runtime — python slim + nginx, static dist, app, duckdb
# -----------------------------------------------------------------------------
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx gettext-base \
    && rm -rf /var/lib/apt/lists/* \
    && rm -f /etc/nginx/sites-enabled/default \
    && mkdir -p /var/cache/nginx /var/log/nginx \
    && chown -R www-data:www-data /var/cache/nginx /var/log/nginx

# Runtime Python deps only (no geopandas/pyarrow in production)
RUN pip install --no-cache-dir \
    "duckdb>=1.2.0" \
    "fastapi>=0.115.0" \
    "uvicorn[standard]>=0.34.0"

COPY mdd_project/ mdd_project/
COPY --from=python-builder /app/mdd_project/data/processed/mdd.duckdb mdd_project/data/processed/mdd.duckdb
COPY --from=frontend /build/dist /usr/share/nginx/html

COPY deploy/nginx.conf.template /etc/nginx/nginx.conf.template
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN sed -i 's/\r$//' /docker-entrypoint.sh && chmod +x /docker-entrypoint.sh

ENV PYTHONPATH=/app
ENV PORT=10000

EXPOSE 10000

ENTRYPOINT ["/docker-entrypoint.sh"]
