#!/usr/bin/env python
"""
Enhanced Tempo Trace Test Script - Tests multiple protocols and endpoints to send traces to Tempo.
"""
import os
import time
import logging
import sys
import uuid
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, 
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("tempo-test-multi")

# Import OpenTelemetry modules
try:
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.trace.status import Status, StatusCode
    
    # Import both gRPC and HTTP exporters
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter as GrpcExporter
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as HttpExporter
    
    logger.info("Successfully imported OpenTelemetry modules")
except ImportError as e:
    logger.error(f"Failed to import OpenTelemetry: {e}")
    logger.error("Please install required packages: pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp")
    sys.exit(1)

# Unique ID for this test run
TEST_RUN_ID = str(uuid.uuid4())[:8]

# Define endpoints to test
ENDPOINTS = [
    # From host to Docker-exposed ports - we're running outside Docker
    {"name": "host-grpc", "protocol": "grpc", "endpoint": "localhost:14317"},
    {"name": "host-http", "protocol": "http", "endpoint": "http://localhost:14318/v1/traces"},
    
    # Within Docker network - these won't work from outside Docker
    # {"name": "docker-grpc", "protocol": "grpc", "endpoint": "tempo:4317"},
    # {"name": "docker-http", "protocol": "http", "endpoint": "http://tempo:4318/v1/traces"},
]

def create_test_span(tracer, name, attributes=None):
    """Create a test span with the given name and attributes"""
    if attributes is None:
        attributes = {}
        
    # Add common test attributes
    attributes.update({
        "test.id": TEST_RUN_ID,
        "test.timestamp": datetime.utcnow().isoformat(),
        "test.name": name
    })
    
    with tracer.start_as_current_span(name) as span:
        # Add attributes to the span
        for key, value in attributes.items():
            span.set_attribute(key, value)
            
        # Simulate some work
        time.sleep(0.1)
        
        # Log an event
        span.add_event("test.event", {"message": f"Testing span {name}"})
    
    return True

def test_endpoint(endpoint_config):
    """Test sending spans to the given endpoint"""
    name = endpoint_config["name"]
    protocol = endpoint_config["protocol"]
    endpoint = endpoint_config["endpoint"]
    
    logger.info(f"Testing {name} endpoint: {endpoint}")
    
    # Create a resource with unique test identifiers
    resource = Resource.create({
        "service.name": f"tempo-test-{name}",
        "test.id": TEST_RUN_ID,
        "test.protocol": protocol,
        "test.endpoint": endpoint
    })
    
    # Set up the tracer provider
    provider = TracerProvider(resource=resource)
    
    try:
        # Create appropriate exporter based on protocol
        if protocol == "grpc":
            exporter = GrpcExporter(endpoint=endpoint, insecure=True)
            logger.info(f"Created gRPC exporter for {endpoint}")
        else:  # http
            exporter = HttpExporter(endpoint=endpoint)
            logger.info(f"Created HTTP exporter for {endpoint}")
        
        # Add the exporter to the provider
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)
        
        # Create tracer
        temp_trace = trace.get_tracer_provider()
        trace.set_tracer_provider(provider)
        tracer = trace.get_tracer(f"tempo-test-{name}")
        
        # Create a parent span
        parent_name = f"test-{name}-parent"
        create_test_span(tracer, parent_name, {
            "span.type": "parent",
            "test.protocol": protocol
        })
        
        # Create a few child spans
        for i in range(3):
            child_name = f"test-{name}-child-{i}"
            create_test_span(tracer, child_name, {
                "span.type": "child",
                "child.index": i,
                "test.protocol": protocol
            })
        
        # Force flush the exporter
        logger.info(f"Flushing spans for {name}")
        provider.force_flush()
        
        # Reset tracer provider to avoid affecting other tests
        trace.set_tracer_provider(temp_trace)
        
        logger.info(f"✅ Successfully sent test spans via {name}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to send spans via {name}: {str(e)}")
        return False

def main():
    """Run tests for all endpoints"""
    logger.info(f"Starting Tempo multi-endpoint test (Test ID: {TEST_RUN_ID})")
    
    success_count = 0
    
    for endpoint in ENDPOINTS:
        try:
            if test_endpoint(endpoint):
                success_count += 1
        except Exception as e:
            logger.error(f"Error testing {endpoint['name']}: {str(e)}")
    
    logger.info(f"Test complete. {success_count}/{len(ENDPOINTS)} endpoints successful.")
    logger.info(f"Test ID: {TEST_RUN_ID} - Check Grafana Tempo for traces with this ID.")
    
    if success_count == 0:
        logger.error("❌ All tests failed. Check your Tempo configuration and network connectivity.")
        sys.exit(1)

if __name__ == "__main__":
    main()
