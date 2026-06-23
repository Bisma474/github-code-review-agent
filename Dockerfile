FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

COPY . .

ENV PYTHONPATH=/app
ENV APP_ENV=production

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://127.0.0.1:${PORT:-8000}/health', timeout=5)" || exit 1

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
