FROM python:3.11-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential git && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --no-cache-dir \
    pypdf2 pdfplumber pyyaml python-dotenv \
    requests rapidfuzz pydantic qdrant-client

COPY . .

ENV PYTHONUNBUFFERED=1
CMD ["python3", "scripts/turso_intake_worker.py", "watch"]
