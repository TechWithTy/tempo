#!/usr/bin/env python
"""
Test script to validate the Tempo OTLP connection.
This script generates trace spans and sends them directly to Tempo via OTLP.
"""
import os
import time
import random
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, 
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("tempo-test")

# Import OpenTelemetry modules
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace.status import Status, StatusCode

# Set the OTLP endpoint from environment or use the default
# Note: For gRPC, we need to use the format "host:port" without http://
# - Use otel-collector for sending traces when in the Docker network 
# - When running from host, we need to use the exposed port of either tempo or otel-collector
TEMPO_ENDPOINT = os.environ.get("TEMPO_ENDPOINT", "otel-collector:4317")  # Send to otel-collector in Docker
TEMPO_ENDPOINT_HOST = os.environ.get("TEMPO_ENDPOINT_HOST", "localhost:4317")  # For running outside Docker via otel-collector
logger.info(f"Using OTLP endpoint: {TEMPO_ENDPOINT} (or {TEMPO_ENDPOINT_HOST} if running from host)")

# Configure the tracer provider
resource = Resource.create({
    "service.name": "tempo-test",
    "service.version": "1.0.0",
    "environment": "test"
})

# Set up the provider
provider = TracerProvider(resource=resource)
trace.set_tracer_provider(provider)

# Create the OTLP exporter
# Default to using host endpoint unless explicitly set to run in Docker
endpoint_to_use = TEMPO_ENDPOINT_HOST if os.environ.get("RUN_FROM_HOST", "true").lower() == "true" else TEMPO_ENDPOINT
logger.info(f"Creating OTLP exporter with endpoint: {endpoint_to_use}")
otlp_exporter = OTLPSpanExporter(endpoint=endpoint_to_use, insecure=True)

# Add the exporter to the provider
provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

# Get a tracer
tracer = trace.get_tracer("tempo-test")

# Generate a test trace with nested spans
def create_test_trace():
    with tracer.start_as_current_span("main-request") as parent:
        # Add some attributes to the span
        parent.set_attribute("http.method", "GET")
        parent.set_attribute("http.url", "/api/test")
        parent.set_attribute("http.status_code", 200)
        
        # Create child span for database operation
        with tracer.start_as_current_span("database-query") as child1:
            child1.set_attribute("db.system", "postgresql")
            child1.set_attribute("db.statement", "SELECT * FROM users")
            child1.set_attribute("db.operation", "SELECT")
            
            # Simulate some work
            time.sleep(0.05)
            
            # Add an event
            child1.add_event("db.result_fetched", {"row_count": 10})
        
        # Create another child span for cache operation
        with tracer.start_as_current_span("cache-lookup") as child2:
            child2.set_attribute("cache.system", "redis")
            child2.set_attribute("cache.key", "user:profile:123")
            
            # Simulate cache miss
            time.sleep(0.02)
            child2.set_attribute("cache.hit", False)
            
            # Set error status occasionally to generate interesting traces
            if random.random() < 0.3:
                child2.set_status(Status(StatusCode.ERROR))
                child2.record_exception(Exception("Cache connection error"))
        
        # Final processing span
        with tracer.start_as_current_span("response-processing"):
            time.sleep(0.03)

# Run the test multiple times
def main():
    logger.info("Starting Tempo test - generating traces...")
    
    for i in range(5):
        logger.info(f"Generating trace {i+1}/5")
        create_test_trace()
        time.sleep(0.5)
    
    # Force flush the exporter to ensure all spans are sent
    logger.info("Flushing remaining spans...")
    provider.force_flush()
    logger.info("Test completed. Check Grafana Tempo for the generated traces.")

if __name__ == "__main__":
    main()
