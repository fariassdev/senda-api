FROM python:3.12.5-slim

# Install system dependencies required for Python packages
# - build-essential: For compiling C code (needed by many packages)
# - portaudio19-dev: Required to build pyaudio
# - libpq-dev: Required to build psycopg2 (provides pg_config)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    portaudio19-dev \
    libpq-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy files required for the installation step
# This includes the project definition and the source code itself
COPY pyproject.toml uv.lock* README.md /app/
COPY src ./src

# Install uv and then the project with its dependencies
# This layer is cached as long as pyproject.toml or the src directory don't change
RUN pip install uv && \
    uv pip install --system .

# Copy the rest of the application files
# This is useful for files not needed during install (e.g., tests, configs)
COPY . /app

EXPOSE 8000

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
