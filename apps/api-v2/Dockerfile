# The replacement service, built the same way the Django image is.
# Pinned to the tag the Django image already builds on, so a build here needs
# no pull of its own.
FROM python:3.13.14-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

RUN pip install --no-cache-dir uv

WORKDIR /app

# Permissions are set at COPY time: the build context on the deployment host can
# carry mode 000 on files, and inheriting that makes the app unreadable to itself.

# Dependencies first: they change less often than the source.
COPY --chmod=644 pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen --no-install-project

COPY --chmod=755 src ./src
COPY --chmod=644 alembic.ini ./
COPY --chmod=755 migrations ./migrations
RUN uv sync --no-dev --frozen --no-editable

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app/src

RUN useradd --create-home --uid 10001 app && chown -R app:app /app \
    && chmod -R a+rX /app
USER app

EXPOSE 8010

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8010/health/ready/', timeout=3)"

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8010"]
