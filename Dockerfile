# syntax=docker/dockerfile:1.7

# ============================================================
# Stage 1: Base — setup común (venv, usuario, variables)
# ============================================================
FROM python:3.14-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN useradd --create-home --shell /bin/bash app

# ============================================================
# Stage 2: Builder — instala el paquete + deps de producción
# ============================================================
FROM base AS builder

WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --upgrade pip && pip install .

# ============================================================
# Stage 3: Dev — editable install + dev deps (para docker compose)
# ============================================================
FROM base AS dev

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY tests ./tests

RUN pip install --upgrade pip && pip install -e ".[dev]"

RUN chown -R app:app /app /opt/venv
USER app

CMD ["bash"]

# ============================================================
# Stage 4: Runtime — imagen mínima de producción
# ============================================================
FROM python:3.14-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

COPY --from=builder /opt/venv /opt/venv

RUN useradd --create-home --shell /bin/bash app
USER app
WORKDIR /home/app

CMD ["python", "-c", "import slot_engine; print('slot_engine loaded correctly')"]