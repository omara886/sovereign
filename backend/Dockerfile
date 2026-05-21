FROM python:3.12-slim-bookworm

WORKDIR /app

# System deps: DB, image processing, RAQM (HarfBuzz-backed Arabic shaping + FriBiDi RTL)
# Split into two layers: critical deps first, RAQM second (for better cache)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    libjpeg-dev zlib1g-dev libpng-dev libwebp-dev \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y --no-install-recommends \
    libraqm-dev libfribidi-dev libharfbuzz-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install all deps EXCEPT Pillow first (cached layer)
RUN pip install --no-cache-dir $(grep -iv 'pillow' requirements.txt | grep -v '^\s*#' | grep -v '^\s*$' | tr '\n' ' ')

# Rebuild Pillow from source with libraqm support
# If this fails, Railway will retry; previous layers cached
RUN pip install --no-cache-dir --no-binary=Pillow Pillow

COPY . .

EXPOSE 8000

CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
