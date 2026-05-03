# syntax=docker/dockerfile:1.7

# ----- Stage 1: builder -----------------------------------------------------
FROM python:3.12-slim AS builder

# Bring in the uv binary from the official image. Pinning by tag avoids
# silent toolchain drift on rebuilds.
COPY --from=ghcr.io/astral-sh/uv:0.5.0 /uv /usr/local/bin/uv

WORKDIR /app

# Install runtime deps first (without the project itself) so this layer
# caches across source-code changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Now bring in source + project metadata and install the project.
COPY govlink ./govlink
COPY alembic.ini ./
COPY alembic ./alembic
COPY README.md LICENSE ./
RUN uv sync --frozen --no-dev


# ----- Stage 2: runtime -----------------------------------------------------
FROM python:3.12-slim AS runtime

# curl is needed for the HEALTHCHECK and is small (~250 KB installed).
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 govlink

WORKDIR /app
COPY --from=builder --chown=govlink:govlink /app /app

# Make sure the virtualenv's Python is on PATH.
ENV PATH="/app/.venv/bin:$PATH" \
    GOVLINK_ENV=production \
    PYTHONUNBUFFERED=1

USER govlink
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

LABEL org.opencontainers.image.source="https://github.com/TODO/govlink" \
      org.opencontainers.image.title="govlink" \
      org.opencontainers.image.description="Open data API for Gambian government datasets." \
      org.opencontainers.image.licenses="MIT"

CMD ["uvicorn", "govlink.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
