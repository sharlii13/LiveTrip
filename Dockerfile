# LiveTrip: one container serving the website and the API. Build from the repository root.

# 1. Build the website
FROM node:22-slim AS site
WORKDIR /site
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# 2. The backend, plus the built website
FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1 \
    LIVETRIP_ENV=production \
    LIVETRIP_FRONTEND_DIST=/srv/site \
    LIVETRIP_DATABASE_URL=sqlite:////data/livetrip.db \
    LIVETRIP_UPLOAD_DIR=/data/uploads
WORKDIR /srv/Backend/Backend
COPY Backend/Backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY Backend/Backend/app ./app
COPY --from=site /site/dist /srv/site
RUN mkdir -p /data
WORKDIR /srv/Backend/Backend/app

# One worker: rate limits and caches live in the process, and SQLite suits a single writer.
# --proxy-headers: behind the host's HTTPS proxy, so limits count real visitors, not the proxy.
CMD ["sh", "-c", "exec python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
