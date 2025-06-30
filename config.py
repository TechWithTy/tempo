from app.core.config import settings
from typing import Optional
import os

# Tempo exporter and authentication settings (should be environment-specific)
# Default to localhost ports when running on host, or container name when inside Docker
# ALWAYS send to otel-collector, not directly to tempo
"""
# Determine Tempo exporter endpoint per environment:
# - In Docker (DOCKER_ENV=true), default to otel-collector:4317
# - Locally, use host-mapped port localhost:14317
"""
docker_env = os.getenv("DOCKER_ENV", "").lower() in ("1", "true")
if docker_env:
    default_endpoint = getattr(settings, "TEMPO_EXPORTER_ENDPOINT", "otel-collector:4317")
else:
    default_endpoint = os.environ.get("TEMPO_EXPORTER_ENDPOINT", "localhost:14317")
TEMPO_EXPORTER_ENDPOINT: str = os.environ.get("TEMPO_EXPORTER_ENDPOINT", default_endpoint)
TEMPO_CA_FILE: str | None = getattr(settings, "TEMPO_CA_FILE", None)
TEMPO_CERT_FILE: str | None = getattr(settings, "TEMPO_CERT_FILE", None)
TEMPO_KEY_FILE: str | None = getattr(settings, "TEMPO_KEY_FILE", None)
TEMPO_SKIP_VERIFY: bool = bool(getattr(settings, "TEMPO_SKIP_VERIFY", False))
TEMPO_USERNAME: str | None = getattr(settings, "TEMPO_USERNAME", None)  # ! Sensitive
TEMPO_PASSWORD: str | None = getattr(settings, "TEMPO_PASSWORD", None)  # ! Sensitive
TEMPO_BEARER_TOKEN: str | None = getattr(settings, "TEMPO_BEARER_TOKEN", None)  # ! Sensitive

# Tempo service and storage config
TEMPO_PORT: int = int(getattr(settings, "TEMPO_PORT", 3200))
TEMPO_OTLP_PORT: int = int(getattr(settings, "TEMPO_OTLP_PORT", 14317))
TEMPO_STORAGE_PATH: str = getattr(settings, "TEMPO_STORAGE_PATH", "/var/tempo")
TEMPO_OTLP_HTTP_PORT: int = int(getattr(settings, "TEMPO_OTLP_HTTP_PORT", 14318))
TEMPO_RETENTION_PERIOD: str = getattr(settings, "TEMPO_RETENTION_PERIOD", "168h")
TEMPO_RECEIVER_JAEGER_PORT: int = int(getattr(settings, "TEMPO_RECEIVER_JAEGER_PORT", 14250))
TEMPO_ZIPKIN_PORT: int = int(getattr(settings, "TEMPO_ZIPKIN_PORT", 9411))

