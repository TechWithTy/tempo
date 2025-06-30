"""
Tempo core implementation for tracing integration with Grafana Tempo.
This module extends the existing telemetry system with Tempo-specific exporters
and utilities for distributed tracing visualization.
"""
import logging
import os
from typing import Any, Dict, Optional

import grpc
from circuitbreaker import circuit
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.core.tempo.config import (
    TEMPO_BEARER_TOKEN,
    TEMPO_CA_FILE,
    TEMPO_CERT_FILE,
    TEMPO_EXPORTER_ENDPOINT,
    TEMPO_KEY_FILE,
    TEMPO_PASSWORD,
    TEMPO_SKIP_VERIFY,
    TEMPO_USERNAME,
)

logger = logging.getLogger(__name__)


class TempoClient:
    """Client for Grafana Tempo integration, extending the telemetry system."""

    def __init__(
        self,
        service_name: str,
        service_version: str = "1.0.0",
        environment: Optional[str] = None,
    ):
        """Initialize Tempo client with service information and authentication."""
        self.service_name = service_name
        self.service_version = service_version
        self.environment = environment or os.getenv("ENVIRONMENT", "development")
        self._setup_trace_provider()

    @circuit(
        failure_threshold=3,
        recovery_timeout=30,
        expected_exception=(grpc.RpcError, ConnectionError, RuntimeError),
        fallback_function=lambda e: logger.warning(f"Tempo circuit open: {str(e)}"),
    )
    def _setup_trace_provider(self) -> None:
        """
        Set up the trace provider with Tempo-specific configuration.
        Uses circuit breaker pattern for resilience.
        """
        # Create a resource with service info
        resource = Resource.create(
            {
                "service.name": self.service_name,
                "service.version": self.service_version,
                "environment": self.environment,
                "deployment.environment": self.environment,
            }
        )

        # Set up trace provider with resource
        provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(provider)

        # Create OTLP exporter configured for Tempo
        credentials = self._get_tempo_credentials()
        
        otlp_exporter = OTLPSpanExporter(
            endpoint=TEMPO_EXPORTER_ENDPOINT,
            credentials=credentials,
            insecure=TEMPO_SKIP_VERIFY,
        )

        # Use batch span processor for efficiency
        span_processor = BatchSpanProcessor(otlp_exporter)
        provider.add_span_processor(span_processor)

        logger.info(f"Tempo trace provider initialized for service: {self.service_name}")

    def _get_tempo_credentials(self) -> Optional[grpc.ChannelCredentials]:
        """
        Configure secure credentials for Tempo connection.
        Handles multiple authentication methods (TLS, username/password, token).
        """
        if TEMPO_CA_FILE and TEMPO_CERT_FILE and TEMPO_KEY_FILE:
            # TLS authentication with client certificates
            with open(TEMPO_CA_FILE, "rb") as ca_file:
                ca_data = ca_file.read()
            with open(TEMPO_CERT_FILE, "rb") as cert_file:
                cert_data = cert_file.read()
            with open(TEMPO_KEY_FILE, "rb") as key_file:
                key_data = key_file.read()

            credentials = grpc.ssl_channel_credentials(
                root_certificates=ca_data,
                private_key=key_data,
                certificate_chain=cert_data,
            )

            # Add user/password if provided
            if TEMPO_USERNAME and TEMPO_PASSWORD:
                credentials = grpc.composite_channel_credentials(
                    credentials,
                    grpc.access_token_call_credentials(
                        f"{TEMPO_USERNAME}:{TEMPO_PASSWORD}"
                    ),
                )
            # Add bearer token if provided
            elif TEMPO_BEARER_TOKEN:
                credentials = grpc.composite_channel_credentials(
                    credentials,
                    grpc.access_token_call_credentials(TEMPO_BEARER_TOKEN),
                )

            return credentials
        elif TEMPO_USERNAME and TEMPO_PASSWORD:
            # Basic auth without TLS
            return grpc.access_token_call_credentials(
                f"{TEMPO_USERNAME}:{TEMPO_PASSWORD}"
            )
        elif TEMPO_BEARER_TOKEN:
            # Bearer token auth without TLS
            return grpc.access_token_call_credentials(TEMPO_BEARER_TOKEN)

        # No credentials needed
        return None

    def create_span(
        self, name: str, context: Optional[Dict[str, Any]] = None
    ) -> trace.Span:
        """
        Create a new span with the specified name and context attributes.
        
        Args:
            name: Name of the span
            context: Optional dictionary of attributes to add to the span
            
        Returns:
            An OpenTelemetry span object
        """
        tracer = trace.get_tracer_provider().get_tracer(
            self.service_name, self.service_version
        )
        span = tracer.start_span(name)
        
        if context:
            for key, value in context.items():
                span.set_attribute(key, str(value))
        
        return span
        
    def send_test_span(self) -> None:
        """
        Send a test span to validate the Tempo connection.
        This can be used to verify that spans are being exported properly.
        """
        import time
        
        logger.info("Sending test span to Tempo")
        tracer = trace.get_tracer_provider().get_tracer(
            self.service_name, self.service_version
        )
        
        with tracer.start_as_current_span("tempo-connection-test") as span:
            span.set_attribute("tempo.test", True)
            span.set_attribute("tempo.endpoint", TEMPO_EXPORTER_ENDPOINT)
            span.add_event("tempo.test.sent", {
                "timestamp": str(time.time()),
                "environment": self.environment
            })
            
        # Force flush to ensure the span is sent immediately
        provider = trace.get_tracer_provider()
        if hasattr(provider, "force_flush"):
            provider.force_flush()
            
        logger.info(f"Test span sent to Tempo endpoint: {TEMPO_EXPORTER_ENDPOINT}. Check Grafana to verify it was received.")

    def shutdown(self) -> None:
        """
        Properly shutdown the trace provider to flush remaining spans.
        Should be called during application shutdown.
        """
        trace.get_tracer_provider().shutdown()
        logger.info("Tempo trace provider shut down")


# Singleton instance for app-wide use
tempo_client: Optional[TempoClient] = None


def init_tempo(
    service_name: str, service_version: str = "1.0.0", environment: Optional[str] = None
) -> TempoClient:
    """
    Initialize the Tempo client as a singleton.
    
    Args:
        service_name: Name of the service 
        service_version: Version of the service
        environment: Deployment environment
        
    Returns:
        TempoClient instance
    """
    global tempo_client
    if tempo_client is None:
        tempo_client = TempoClient(
            service_name=service_name,
            service_version=service_version,
            environment=environment,
        )
    return tempo_client


def get_tempo() -> TempoClient:
    """
    Get the initialized Tempo client.
    
    Raises:
        RuntimeError: If tempo client hasn't been initialized
        
    Returns:
        TempoClient instance
    """
    if tempo_client is None:
        raise RuntimeError("Tempo client not initialized. Call init_tempo() first.")
    return tempo_client


def shutdown_tempo() -> None:
    """Shutdown the Tempo client."""
    global tempo_client
    if tempo_client is not None:
        tempo_client.shutdown()
        tempo_client = None
