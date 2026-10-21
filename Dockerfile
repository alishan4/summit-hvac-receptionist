FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir fastapi uvicorn pydantic pydantic-settings sqlalchemy pyyaml httpx \
    google-api-python-client google-auth
COPY app ./app
COPY config ./config
COPY prompts ./prompts
COPY scripts ./scripts
RUN useradd -m appuser && mkdir /data && chown appuser /data
USER appuser
# SQLite lives on a mounted volume; set DATABASE_URL=postgresql+psycopg://... to swap (add the driver).
ENV DATABASE_URL=sqlite:////data/summit.db
EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:8000/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
