FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

COPY . .

ENV PYTHONPATH=/app
ENV APP_ENV=production

CMD ["uvicorn", "app.main:create_app", "--host", "0.0.0.0", "--port", "8000"]
