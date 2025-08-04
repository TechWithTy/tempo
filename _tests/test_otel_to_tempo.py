#!/usr/bin/env python
"""
Test the connection between OpenTelemetry Collector and Tempo.

This script:
1. Sends traces directly to the OpenTelemetry collector
2. Verifies if Tempo received them by querying its API endpoints
3. Checks Tempo metrics to confirm ingestion
4. Provides clear success/failure indications

Usage:
    poetry run python -m app.core.tempo._tests.test_otel_to_tempo
"""

import os
import sys
import time
import uuid
import logging
import json
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("otel-to-tempo-test")

try:
    # Import required libraries
    import requests
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
except ImportError:
    logger.error("Required packages not found. Please run: poetry add opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp requests")
    sys.exit(1)


def check_tempo_metrics(host="localhost", port=3200):
    """
    Query Tempo metrics to see if it's ingesting traces.
    
    Returns:
        tuple: (success, metrics_data)
    """
    try:
        response = requests.get(f"http://{host}:{port}/metrics")
        if response.status_code != 200:
            return False, f"Tempo metrics endpoint returned status code {response.status_code}"
        
        # Look for ingestion-related metrics
        metrics_text = response.text
        ingestion_metrics = {}
        
        # Key metrics to look for
        important_metrics = [
            "tempo_distributor_spans_received_total",
            "tempo_ingester_traces_created_total",
            "tempo_ingester_blocks_flushed_total"
        ]
        
        for line in metrics_text.splitlines():
            if line.startswith('#'):
                continue  # Skip comments
                
            for metric in important_metrics:
                if line.startswith(metric):
                    try:
                        parts = line.split(' ')
                        if len(parts) >= 2:
                            name = parts[0]
                            value = float(parts[-1])
                            ingestion_metrics[name] = value
                    except Exception:
                        continue
        
        return True, ingestion_metrics
    except Exception as e:
        return False, f"Error querying Tempo metrics: {str(e)}"


def check_tempo_search(host="localhost", port=3200, service_name=None, min_start_time=None):
    """
    Check if traces for a given service exist in Tempo.
    
    Args:
        host: Tempo host
        port: Tempo port
        service_name: Service name to look for
        min_start_time: Minimum start time as ISO string
        
    Returns:
        tuple: (success, found_traces)
    """
    if not service_name:
        return False, "No service name provided for search"
    
    try:
        # Let's just use the tag search without the time filter for reliability
        search_url = f"http://{host}:{port}/api/search"
        params = {
            "tags": f"service.name=\"{service_name}\"",
            "limit": "20"
        }
        
        # Query without time filters first
        response = requests.get(search_url, params=params)
        
        if response.status_code != 200:
            # Try the older v1 API 
            search_url = f"http://{host}:{port}/api/v1/search"
            response = requests.get(search_url, params=params)
            
            if response.status_code != 200:
                return False, f"Tempo search API returned status {response.status_code}: {response.text}"
        
        # Parse response
        try:
            search_results = response.json()
            
            if not search_results or "traces" not in search_results:
                return True, {"traces_found": False, "message": "No traces found for service"}
            
            traces = search_results["traces"]
            if not traces:
                return True, {"traces_found": False, "message": "Empty traces array returned"}
            
            # Return success with trace count
            return True, {
                "traces_found": True,
                "trace_count": len(traces),
                "sample_traces": traces[:2]  # Return first two for inspection
            }
            
        except json.JSONDecodeError:
            return False, f"Failed to parse Tempo search response: {response.text[:100]}..."
        
    except Exception as e:
        return False, f"Error querying Tempo search API: {str(e)}"


def send_test_traces(service_name="otel-to-tempo-test"):
    """
    Send test traces with distinct pattern to Tempo via OTel collector.
    
    Returns:
        tuple: (success, details)
    """
    # Create a unique test ID and timestamp
    test_id = f"test-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    test_timestamp = datetime.now()
    trace_ids = []
    
    try:
        # First try host-mapped collector port
        endpoint = "localhost:4317"
        
        # Configure resource with service info - use VERY specific service name for easy search
        resource = Resource.create({
            "service.name": service_name,
            "test.id": test_id,
            "test.timestamp": test_timestamp.isoformat(),
        })
        
        # Set up trace provider with resource
        provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(provider)
        
        # Create OTLP exporter to send to collector
        otlp_exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        
        # Get tracer
        tracer = trace.get_tracer(service_name)
        
        # Send 3 trace groups with unique attributes
        for i in range(3):
            trace_group_id = str(uuid.uuid4())
            with tracer.start_as_current_span(f"otel-to-tempo-test-{i}") as parent:
                parent.set_attribute("test.group_id", trace_group_id)
                parent.set_attribute("test.index", i)
                parent.set_attribute("test.type", "otel-to-tempo")
                
                trace_id = format(parent.get_span_context().trace_id, '032x')
                trace_ids.append(trace_id)
                logger.info(f"Created trace with ID: {trace_id}")
                
                # Add a child span
                with tracer.start_as_current_span(f"child-span-{i}") as child:
                    child.set_attribute("child.index", i)
                    time.sleep(0.1)  # Ensure span has duration
        
        # Force flush to ensure spans are exported immediately
        provider.force_flush()
        provider.shutdown()
        
        return True, {
            "trace_ids": trace_ids,
            "test_id": test_id,
            "service_name": service_name,
            "timestamp": test_timestamp.isoformat(),
        }
        
    except Exception as e:
        return False, f"Error sending traces: {str(e)}"


def main():
    """Main test function."""
    print("\n" + "=" * 80)
    print(" OpenTelemetry Collector to Tempo Connection Test")
    print("=" * 80)
    
    # Step 1: Check Tempo metrics state before test
    logger.info("Checking initial Tempo metrics...")
    metrics_success, initial_metrics = check_tempo_metrics()
    
    if not metrics_success:
        logger.warning(f"Failed to get Tempo metrics: {initial_metrics}")
        logger.info("Continuing test anyway...")
    else:
        logger.info(f"Initial Tempo metrics: {initial_metrics}")
    
    # Step 2: Send test traces with unique service name
    service_name = f"otel-tempo-test-{int(time.time())}"
    logger.info(f"Sending test traces with service name: {service_name}")
    
    trace_success, trace_details = send_test_traces(service_name)
    if not trace_success:
        logger.error(f"Failed to send test traces: {trace_details}")
        sys.exit(1)
    
    # Give Tempo time to ingest the traces
    logger.info("Waiting for Tempo to ingest traces (10 seconds)...")
    time.sleep(10)
    
    # Step 3: Check if metrics changed
    logger.info("Checking Tempo metrics after sending traces...")
    metrics_success, after_metrics = check_tempo_metrics()
    
    if metrics_success:
        # Check if ingestion metrics increased
        metrics_changed = False
        if isinstance(initial_metrics, dict) and isinstance(after_metrics, dict):
            for key in after_metrics:
                if key in initial_metrics and after_metrics[key] > initial_metrics[key]:
                    logger.info(f"✅ Metric {key} increased: {initial_metrics[key]} -> {after_metrics[key]}")
                    metrics_changed = True
                elif key in initial_metrics:
                    logger.info(f"Metric {key} unchanged: {initial_metrics[key]} -> {after_metrics[key]}")
                else:
                    logger.info(f"New metric {key}: {after_metrics[key]}")
        
        if metrics_changed:
            logger.info("✅ METRICS TEST PASSED: Tempo ingestion metrics increased!")
        else:
            logger.warning("⚠️ METRICS TEST INCONCLUSIVE: No change in Tempo ingestion metrics")
    else:
        logger.warning(f"Failed to get Tempo metrics after test: {after_metrics}")
    
    # Step 4: Check Tempo search API
    logger.info("Checking if traces appear in Tempo search API...")
    timestamp = None
    if isinstance(trace_details, dict) and "timestamp" in trace_details:
        # Convert to timestamp 5 minutes before test for safety
        test_time = datetime.fromisoformat(trace_details["timestamp"])
        search_time = (test_time - timedelta(minutes=5)).isoformat()
        timestamp = search_time
    
    search_success, search_results = check_tempo_search(
        service_name=service_name,
        min_start_time=timestamp
    )
    
    if search_success:
        if isinstance(search_results, dict) and search_results.get("traces_found", False):
            logger.info(f"✅ SEARCH TEST PASSED: Found {search_results['trace_count']} traces in Tempo!")
            if "sample_traces" in search_results:
                logger.info(f"Sample trace IDs: {json.dumps(search_results['sample_traces'], indent=2)}")
        else:
            logger.warning("❌ SEARCH TEST FAILED: No traces found in Tempo")
            logger.info(f"Search result: {search_results}")
    else:
        logger.error(f"Failed to search Tempo: {search_results}")
    
    # Final summary
    print("\n" + "=" * 80)
    success_count = 0
    if metrics_changed:
        success_count += 1
    if search_success and isinstance(search_results, dict) and search_results.get("traces_found", False):
        success_count += 1
    
    if success_count == 2:
        logger.info("🎉 OVERALL TEST: PASSED! OTel to Tempo connection is working correctly!")
    elif success_count == 1:
        logger.info("⚠️ OVERALL TEST: PARTIAL PASS - Check logs for details")
    else:
        logger.info("❌ OVERALL TEST: FAILED - Traces are not being properly ingested by Tempo")
        
    logger.info("\nTroubleshooting steps if test failed:")
    logger.info("1. Check OTel collector logs: docker logs otel-collector")
    logger.info("2. Check Tempo logs: docker logs tempo")
    logger.info("3. Verify network connectivity between containers")
    logger.info("4. Make sure the otel-collector config has the correct Tempo endpoint")
    
    print("=" * 80)


if __name__ == "__main__":
    main()
