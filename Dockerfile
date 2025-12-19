FROM python:3.12.5-slim

# Install system dependencies required for Python packages
# - build-essential: For compiling C code (needed by many packages)
# - portaudio19-dev: Required to build pyaudio
# - libpq-dev: Required to build psycopg2 (provides pg_config)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    portaudio19-dev \
    libpq-dev \
    postgresql-client && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy files required for the installation step
COPY pyproject.toml uv.lock* README.md /app/

# Install uv and then the project with its dependencies
RUN pip install uv && \
    uv pip install --system .

# Copy application files (only what's needed for runtime)
COPY senda ./senda
COPY version.py ./

# Copy migration scripts
COPY scripts/run-migrations.sh ./scripts/
RUN chmod +x ./scripts/run-migrations.sh

# Cloud Run expects port 8000
EXPOSE 8000

# Production-ready Uvicorn configuration
# - workers: Set to 1 for Cloud Run (scaling handled at container level)
# - timeout-keep-alive: Matches Cloud Run's timeout
# - access-log: Enabled for Cloud Run logging
CMD ["uvicorn", "senda.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--timeout-keep-alive", "300", "--access-log"]
