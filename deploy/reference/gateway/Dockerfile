FROM python:3.11-slim

WORKDIR /app

# system deps for psql client
RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client && rm -rf /var/lib/apt/lists/*

COPY . /app

# Make sure packaging tools are present
RUN python -m pip install --upgrade pip setuptools wheel

# Install the gateway package (non-editable) for container builds
RUN pip install --no-cache-dir .

EXPOSE 8000
