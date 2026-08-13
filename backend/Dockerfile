FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_ROOT_USER_ACTION=ignore

WORKDIR /app

# Dependencias del sistema mínimas para asyncpg/psycopg/cryptography
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalar el proyecto como paquete requiere el código presente (packages=["app"]),
# por eso copiamos todo antes de instalar. En desarrollo el código se monta por
# volumen y uvicorn corre con --reload, así que el build se hace una sola vez.
COPY . .
RUN pip install --upgrade pip && pip install ".[dev]"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
