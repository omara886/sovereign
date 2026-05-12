FROM python:3.12-slim

WORKDIR /app

# System deps: DB, image processing, RAQM (HarfBuzz-backed Arabic shaping + FriBiDi RTL)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    libjpeg-dev zlib1g-dev libpng-dev libwebp-dev \
    libraqm-dev libfribidi-dev libharfbuzz-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install all deps EXCEPT Pillow first
RUN pip install --no-cache-dir $(grep -v '^[Pp]illow' requirements.txt | tr '\n' ' ')

# Rebuild Pillow from source with libraqm support
# --no-binary=:Pillow: forces source build so it picks up libraqm
RUN pip install --no-cache-dir --no-binary=Pillow Pillow

COPY . .

EXPOSE 8000

CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
