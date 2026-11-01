# syntax=docker/dockerfile:1

# ---- Base image ----
# Slim keeps the image small; 3.13 is the current full-support line.
FROM python:3.13-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install dependencies first (better layer caching).
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install .

# Copy the application code.
COPY app ./app

# Create a non-root user to run the app.
RUN useradd --create-home --uid 1000 appuser
USER appuser

EXPOSE 8000

# One worker is fine for dev. Production scaling (gunicorn/uvicorn workers)
# comes in the deployment milestone.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
