FROM node:24-alpine AS web

WORKDIR /web
COPY mobile/package.json mobile/package-lock.json ./
RUN npm ci --ignore-scripts
COPY mobile ./
ENV EXPO_PUBLIC_API_URL=https://api.altspacelabs.com
RUN npm run sync:locations && npm run export:web

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV WATTRA_DB=/data/wattra.db
ENV WATTRA_WEB_DIST=/srv/web
WORKDIR /srv

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY --from=web /web/dist ./web
RUN mkdir -p /data

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.getenv(\"PORT\", \"8000\")}/api/health', timeout=4).read()" || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
