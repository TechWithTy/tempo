from app.core.config import settings
from typing import Optional

# Tempo exporter and authentication settings (should be environment-specific)
TEMPO_EXPORTER_ENDPOINT: str = getattr(settings, "TEMPO_EXPORTER_ENDPOINT", "tempo:4317")
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

TEMPO_EXPORTER_ENDPOINT: str = getattr(
    settings, "TEMPO_EXPORTER_ENDPOINT", "tempo:4317"
)
TEMPO_CA_FILE: str | None = getattr(settings, "TEMPO_CA_FILE", None)
TEMPO_CERT_FILE: str | None = getattr(settings, "TEMPO_CERT_FILE", None)
TEMPO_KEY_FILE: str | None = getattr(settings, "TEMPO_KEY_FILE", None)
TEMPO_SKIP_VERIFY: bool = bool(getattr(settings, "TEMPO_SKIP_VERIFY", False))
TEMPO_USERNAME: str | None = getattr(settings, "TEMPO_USERNAME", None)  # ! Sensitive
TEMPO_PASSWORD: str | None = getattr(settings, "TEMPO_PASSWORD", None)  # ! Sensitive
TEMPO_BEARER_TOKEN: str | None = getattr(settings, "TEMPO_BEARER_TOKEN", None)  # ! Sensitive

