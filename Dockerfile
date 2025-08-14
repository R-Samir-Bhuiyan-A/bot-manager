# Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TEMPLATES_DIR=/app/templates \
    BOTS_ROOT=/data/bots

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App
COPY app ./app
COPY templates ./templates

# runtime dirs
RUN mkdir -p /data/bots

EXPOSE 8080
CMD ["uvicorn", "app.manager:app", "--host", "0.0.0.0", "--port", "8080"]
