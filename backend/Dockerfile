FROM python:3.12-slim

# uv zamiast pipa: instalacja z uv.lock jest odtwarzalna co do wersji
# i wyraźnie szybsza.
COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /usr/local/bin/uv

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/usr/local

# Zależności przed kodem — zmiana app.py nie unieważnia tej warstwy.
# --no-install-project, bo projekt nie jest pakietem do zainstalowania.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project --no-dev

COPY app.py ./

ENV ARTIFACTS_DIR=/artifacts
EXPOSE 8080

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
