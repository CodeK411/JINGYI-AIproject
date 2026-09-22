FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY data ./data
RUN pip install --no-cache-dir ".[api]"

ENV CORPUS_DIR=/app/data/corpus
ENV AUDIT_DB=/app/artifacts/audit.db
RUN mkdir -p /app/artifacts

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "veripolicy.api:app", "--host", "0.0.0.0", "--port", "8000"]

