FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

COPY . .

ENV PYTHONPATH=/app
ENV APP_ENV=production

# Use shell form so $PORT is expanded at runtime (required by Railway)
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
