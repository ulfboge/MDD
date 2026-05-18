#!/bin/sh
set -e

PORT="${PORT:-10000}"
export PORT

envsubst '${PORT}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

python -m uvicorn mdd_project.web.api.main:app \
    --host 127.0.0.1 \
    --port 8000 \
    --log-level info &
UVICORN_PID=$!

# Wait for API before nginx accepts traffic (Render health check)
i=0
while [ "$i" -lt 60 ]; do
    if python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)" 2>/dev/null; then
        break
    fi
    i=$((i + 1))
    sleep 1
done

trap 'kill "$UVICORN_PID" 2>/dev/null || true' EXIT TERM INT

exec nginx -g 'daemon off;'
