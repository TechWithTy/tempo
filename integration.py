"""
Integration module to connect the Tempo tracing system with the existing telemetry setup.
This allows for unified tracing between the two systems.
"""
import logging
from typing import Any, Dict, Optional

from fastapi import FastAPI

from app.core.telemetry.client import TelemetryClient
from app.core.telemetry.telemetry import get_telemetry
from app.core.tempo.core import init_tempo, get_tempo, TempoClient

logger = logging.getLogger(__name__)


def integrate_tempo_with_telemetry(
    app: FastAPI, 
    service_name: str,
    service_version: str = "1.0.0", 
    environment: Optional[str] = None
) -> TempoClient:
    """
    Integrate Tempo with the existing telemetry system.
    
    This function initializes Tempo and connects it with the existing
    telemetry system to ensure traces are properly correlated.
    
    Args:
        app: FastAPI application instance
        service_name: Name of the service
        service_version: Version of the service
        environment: Deployment environment
        
    Returns:
        Initialized TempoClient instance
    """
    # First, ensure telemetry is initialized
    try:
        telemetry_client = get_telemetry()
        logger.info("Using existing telemetry client")
    except RuntimeError:
        logger.warning("Telemetry not initialized, some features may be limited")
        telemetry_client = None
    
    # Initialize Tempo with the same service info
    tempo_client = init_tempo(
        service_name=service_name,
        service_version=service_version,
        environment=environment
    )
    
    # Register shutdown handler
    @app.on_event("shutdown")
    async def shutdown_tracing():
        """Ensure both telemetry and Tempo are properly shut down."""
        logger.info("Shutting down tracing systems")
        try:
            if telemetry_client:
                telemetry_client.shutdown()
        except Exception as e:
            logger.error(f"Error shutting down telemetry: {e}")
        
        try:
            tempo_client.shutdown()
        except Exception as e:
            logger.error(f"Error shutting down Tempo: {e}")
    
    # Add Tempo client to app state for easy access
    app.state.tempo_client = tempo_client
    
    return tempo_client


def create_correlated_span(name: str, context: Optional[Dict[str, Any]] = None) -> None:
    """
    Create a span that's correlated between telemetry and Tempo.
    
    This ensures the span appears in both systems with the same trace ID.
    
    Args:
        name: Name of the span
        context: Optional attributes to add to the span
    """
    # Get both clients
    try:
        telemetry_client = get_telemetry()
    except RuntimeError:
        telemetry_client = None
    
    tempo_client = get_tempo()
    
    # Create spans in both systems with same context
    if telemetry_client:
        telemetry_span = telemetry_client.start_span(name, context)
    
    tempo_span = tempo_client.create_span(name, context)
    
    # Return the Tempo span since it's specifically for Grafana Tempo visualization
    return tempo_span
