from pydantic import BaseModel

class TempoConfig(BaseModel):
    """Tempo backend configuration for telemetry storage."""
    url: str
    tenant_id: str | None
    tls_enabled: bool = False


class AlloyConfig(BaseModel):
    config_path: str
    relabel_rules: list[str]


class OtelCollectorConfig(BaseModel):
    endpoint: str
    receivers: list[str]
