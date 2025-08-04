#!/usr/bin/env python
"""
Tempo Trace Troubleshooter - A comprehensive tool to diagnose and fix trace issues.

This script:
1. Checks if Tempo is running and accessible
2. Verifies Grafana datasource configuration
3. Tests sending trace spans to Tempo using different methods
4. Inspects metrics to verify trace ingestion
5. Provides recommendations for fixing common issues
"""
import os
import sys
import time
import logging
import subprocess
import requests
import socket
import json
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("tempo-troubleshooter")

# Configuration - endpoints, ports, etc.
TEMPO_HOST = os.environ.get("TEMPO_HOST", "localhost")
TEMPO_PORT = int(os.environ.get("TEMPO_PORT", "3200"))
TEMPO_OTLP_GRPC_PORT = int(os.environ.get("TEMPO_OTLP_GRPC_PORT", "14317"))
TEMPO_OTLP_HTTP_PORT = int(os.environ.get("TEMPO_OTLP_HTTP_PORT", "14318"))
GRAFANA_URL = os.environ.get("GRAFANA_URL", "http://localhost:3000")
GRAFANA_USER = os.environ.get("GRAFANA_USER", "admin")
GRAFANA_PASSWORD = os.environ.get("GRAFANA_PASSWORD", "admin")

# Key Tempo metrics to check
TEMPO_METRICS_TO_CHECK = [
    "tempo_distributor_traces_per_batch_count",  # Shows traces are being ingested
    "tempo_ingester_blocks_flushed_total",       # Shows traces are being written to disk
]

def print_header(title):
    """Format a section header"""
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)

def check_port_open(host, port):
    """Check if a TCP port is open"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        logger.error(f"Socket check error: {str(e)}")
        return False

def check_tempo_health():
    """Check if Tempo metrics endpoint is accessible"""
    try:
        response = requests.get(f"http://{TEMPO_HOST}:{TEMPO_PORT}/metrics", timeout=2)
        if response.status_code == 200:
            return True, response.text
        else:
            return False, f"Status code: {response.status_code}"
    except Exception as e:
        return False, str(e)

def check_grafana_tempo_datasource():
    """Check if Tempo datasource is configured in Grafana"""
    try:
        session = requests.Session()
        session.auth = (GRAFANA_USER, GRAFANA_PASSWORD)
        
        # Get all datasources
        response = session.get(f"{GRAFANA_URL}/api/datasources", timeout=5)
        response.raise_for_status()
        
        datasources = response.json()
        logger.info(f"Found {len(datasources)} datasources")
        
        tempo_datasource = None
        for ds in datasources:
            if ds['type'] == 'tempo':
                tempo_datasource = ds
        
        if not tempo_datasource:
            return False, "No Tempo datasource found"
        
        # Check the datasource URL
        ds_url = tempo_datasource.get('url', '')
        if 'tempo:3200' not in ds_url and 'localhost:3200' not in ds_url:
            return False, f"Tempo datasource URL may be incorrect: {ds_url}"
        
        return True, tempo_datasource
    except Exception as e:
        return False, str(e)

def parse_tempo_metrics(metrics_text):
    """Extract and parse key Tempo metrics"""
    metrics = {}
    for line in metrics_text.splitlines():
        if line.startswith('#'):
            continue  # Skip comments
        
        for metric in TEMPO_METRICS_TO_CHECK:
            if line.startswith(metric):
                try:
                    name, value = line.rsplit(' ', 1)
                    metrics[name] = float(value)
                except ValueError:
                    continue
    
    return metrics

def send_test_trace():
    """Send a test trace to Tempo via OTLP/gRPC"""
    try:
        # Try to import the OpenTelemetry modules
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        
        # Create a unique test ID for this run
        test_id = f"test-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Configure a resource with unique identifiers
        resource = Resource.create({
            "service.name": "tempo-troubleshooter",
            "test.id": test_id
        })
        
        # Set up the tracer provider
        provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(provider)
        
        # Try both endpoints - container name (for Docker communication) and localhost (for host communication)
        endpoints = [
            f"tempo:4317",      # For services running in Docker
            f"localhost:14317"  # For services running on the host
        ]
        
        success = False
        error_messages = []
        
        for endpoint in endpoints:
            try:
                logger.info(f"Trying endpoint: {endpoint}")
                # Create exporter
                otlp_exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
                
                # Add the exporter to the provider
                span_processor = BatchSpanProcessor(otlp_exporter)
                provider.add_span_processor(span_processor)
                
                # Get a tracer
                tracer = trace.get_tracer("tempo-troubleshooter")
                
                # Create a test span
                with tracer.start_as_current_span(f"test-span-{endpoint}") as span:
                    span.set_attribute("test.endpoint", endpoint)
                    span.set_attribute("test.timestamp", datetime.now().isoformat())
                    time.sleep(0.1)  # Small delay for the span
                
                # Force flush the exporter
                provider.force_flush()
                
                # Remove the processor to avoid duplicate spans
                # provider.remove_span_processor(span_processor)
                
                logger.info(f"Sent test trace via {endpoint}")
                success = True
                
            except Exception as e:
                error_msg = f"Failed to send test trace via {endpoint}: {str(e)}"
                logger.warning(error_msg)
                error_messages.append(error_msg)
        
        if success:
            return True, test_id
        else:
            return False, "\n".join(error_messages)
            
    except ImportError as e:
        return False, f"Missing OpenTelemetry packages: {str(e)}"
    except Exception as e:
        return False, str(e)

def main():
    print_header("Tempo Trace Troubleshooter")
    logger.info("Starting Tempo trace diagnostics...")
    
    # Step 1: Check if Tempo is running
    print_header("1. Checking Tempo Service")
    
    # 1.1 Check Tempo UI/API port
    tempo_ui_port_open = check_port_open(TEMPO_HOST, TEMPO_PORT)
    logger.info(f"Tempo UI/API port ({TEMPO_PORT}): {'OPEN' if tempo_ui_port_open else 'CLOSED'}")
    
    # 1.2 Check Tempo OTLP gRPC port
    tempo_grpc_port_open = check_port_open(TEMPO_HOST, TEMPO_OTLP_GRPC_PORT)
    logger.info(f"Tempo OTLP gRPC port ({TEMPO_OTLP_GRPC_PORT}): {'OPEN' if tempo_grpc_port_open else 'CLOSED'}")
    
    # 1.3 Check Tempo OTLP HTTP port
    tempo_http_port_open = check_port_open(TEMPO_HOST, TEMPO_OTLP_HTTP_PORT)
    logger.info(f"Tempo OTLP HTTP port ({TEMPO_OTLP_HTTP_PORT}): {'OPEN' if tempo_http_port_open else 'CLOSED'}")
    
    # 1.4 Check Tempo health endpoint
    tempo_healthy, tempo_metrics_text = check_tempo_health()
    logger.info(f"Tempo health check: {'PASS' if tempo_healthy else 'FAIL'}")
    
    if not tempo_healthy:
        logger.error("Tempo service is not accessible. Please check if it's running.")
        logger.info("Try: docker ps | grep tempo")
        return
    
    # Step 2: Check Grafana datasource
    print_header("2. Checking Grafana Tempo Datasource")
    ds_configured, ds_info = check_grafana_tempo_datasource()
    
    logger.info(f"Tempo datasource configured: {'YES' if ds_configured else 'NO'}")
    if not ds_configured:
        logger.warning(f"Datasource issue: {ds_info}")
        logger.info("Adding a Tempo datasource in Grafana:")
        logger.info("1. Go to Grafana UI (http://localhost:3000)")
        logger.info("2. Navigate to Connections > Data Sources")
        logger.info("3. Click 'Add data source'")
        logger.info("4. Search for and select 'Tempo'")
        logger.info("5. Set URL to 'http://tempo:3200' (if using Docker Compose) or 'http://localhost:3200' (if not)")
        logger.info("6. Click 'Save & Test'")
    else:
        logger.info(f"Tempo datasource details: {ds_info}")
    
    # Step 3: Send test trace
    print_header("3. Sending Test Trace")
    trace_sent, trace_info = send_test_trace()
    
    logger.info(f"Test trace sent: {'SUCCESS' if trace_sent else 'FAILED'}")
    if not trace_sent:
        logger.error(f"Failed to send trace: {trace_info}")
    else:
        logger.info(f"Test trace ID: {trace_info}")
    
    # Step 4: Check Tempo metrics
    print_header("4. Checking Tempo Metrics")
    
    if tempo_healthy:
        metrics = parse_tempo_metrics(tempo_metrics_text)
        
        if metrics:
            logger.info("Found Tempo metrics:")
            for name, value in metrics.items():
                logger.info(f"- {name}: {value}")
                
            if all(value == 0 for value in metrics.values()):
                logger.warning("All metrics are zero - Tempo is not receiving traces!")
        else:
            logger.warning("No relevant metrics found. Tempo may not be ingesting traces.")
    
    # Final summary and recommendations
    print_header("Troubleshooting Summary")
    
    issues_found = []
    
    if not tempo_ui_port_open:
        issues_found.append("Tempo UI/API port is not accessible")
        
    if not tempo_grpc_port_open:
        issues_found.append("Tempo OTLP gRPC port is not accessible")
    
    if not tempo_http_port_open:
        issues_found.append("Tempo OTLP HTTP port is not accessible")
    
    if not tempo_healthy:
        issues_found.append("Tempo metrics endpoint is not healthy")
    
    if not ds_configured:
        issues_found.append("Grafana Tempo datasource is not configured correctly")
    
    if not trace_sent:
        issues_found.append("Failed to send test trace")
    
    if tempo_healthy and tempo_metrics_text and all(value == 0 for value in parse_tempo_metrics(tempo_metrics_text).values()):
        issues_found.append("Tempo is not ingesting any traces (all metrics are zero)")
    
    if issues_found:
        logger.warning("Issues found:")
        for i, issue in enumerate(issues_found, 1):
            logger.warning(f"{i}. {issue}")
        
        logger.info("\nRecommendations:")
        
        if not tempo_ui_port_open or not tempo_grpc_port_open or not tempo_http_port_open:
            logger.info("- Check if Tempo container is running: docker ps | grep tempo")
            logger.info("- Verify port mappings in docker-compose.yml or Tempo configuration")
        
        if not ds_configured:
            logger.info("- Configure Tempo datasource in Grafana as described above")
        
        if not trace_sent:
            logger.info("- Check OpenTelemetry configuration in your application")
            logger.info("- Verify the OTLP endpoint URL: tempo:4317 (Docker internal) or localhost:14317 (from host)")
            logger.info("- Install required packages: pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp")
        
        logger.info("- Check the Tempo logs for errors: docker logs tempo")
    else:
        logger.info("No issues found! The Tempo tracing pipeline appears to be working correctly.")
    
    logger.info("\nDiagnostics complete.")

if __name__ == "__main__":
    main()
