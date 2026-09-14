# RVC2MQTT Docker Container
# Phase 2.5: Production Deployment
# Base: Python 3.11 slim for smaller image size

FROM python:3.11-slim@sha256:9534e5a8e315485d4061ed659af0fd78a284c015f9b73661b41d6bab25604534 AS base

# Apply Debian security updates at build time. The digest above pins the exact
# upstream base, but that base is rebuilt on Docker's cadence, not Debian's: a
# fixed CVE published after the last upstream rebuild would otherwise fail the
# CI scan gate and block every PR until upstream catches up. Upgrading here
# patches whatever the security suite has fixed at the moment we build.
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

FROM base AS dependencies
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
RUN --mount=from=ghcr.io/astral-sh/uv:0.12.11@sha256:79c6f4776b851471cc73b7d21d0cc834bb94383c292e83640d27eff512864df7,source=/uv,target=/bin/uv \
    uv sync --locked --only-group runtime --no-managed-python --no-cache

FROM base AS runtime
# Preserve the existing removal of vulnerable, unused system build tooling.
RUN --mount=from=ghcr.io/astral-sh/uv:0.12.11@sha256:79c6f4776b851471cc73b7d21d0cc834bb94383c292e83640d27eff512864df7,source=/uv,target=/bin/uv \
    uv pip uninstall --python /usr/local/bin/python setuptools
ENV PATH="/app/.venv/bin:$PATH"
COPY --from=dependencies /app/.venv /app/.venv

# Set metadata
LABEL maintainer="rvc2mqtt"
LABEL description="RV-C to MQTT bridge with Home Assistant Discovery"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Copy application files
COPY rvc2mqtt.py rvc_config.py .
COPY ha_discovery.py .
COPY rvc_commands.py .
COPY can_tx.py .
COPY command_handler.py .
COPY command_validator.py .
COPY audit_logger.py .
COPY mqttlog.py .
COPY rvc-spec.yml .

# Deployment must mount its own /app/rvc2mqtt.ini; site settings never enter the image.

# Copy mappings directory
COPY mappings/ ./mappings/

# Set timezone (can be overridden by environment variable)
ENV TZ=America/New_York

# Run as non-root user for security
# Use UID 99 and GID 100 (nobody:users) to match Unraid's standard appdata ownership
# Creating directories and setting permissions for when running without volume mounts
RUN mkdir -p /app/logs /app/audit && \
    chmod -R 777 /app/logs /app/audit
# Run as nobody:users (99:100) - Unraid standard
USER 99:100

# Entry point
CMD ["python", "-u", "rvc2mqtt.py"]
