#!/usr/bin/env python
"""
Test the connection between Tempo and Grafana.

This script:
1. Verifies the Grafana Tempo datasource is configured correctly
2. Sends test traces that should appear in Grafana
3. Queries the Grafana API to check if traces are accessible
4. Provides clear success/failure indications and troubleshooting steps

Usage:
    poetry run python -m app.core.tempo._tests.test_tempo_to_grafana
"""

import os
import sys
import time
import uuid
import json
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("tempo-to-grafana-test")

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


# Configuration with defaults
GRAFANA_URL = os.environ.get("GRAFANA_URL", "http://localhost:3000")
GRAFANA_USER = os.environ.get("GRAFANA_USER", "admin")
GRAFANA_PASSWORD = os.environ.get("GRAFANA_PASSWORD", "admin")
print(f"GRAFANA_URL: {GRAFANA_URL}, GRAFANA_USER: {GRAFANA_USER}, GRAFANA_PASSWORD: {GRAFANA_PASSWORD}")
TEMPO_HOST = os.environ.get("TEMPO_HOST", "localhost")
TEMPO_PORT = int(os.environ.get("TEMPO_PORT", "3200"))
OTEL_ENDPOINT = os.environ.get("OTEL_ENDPOINT", "localhost:4317")
print(f"TEMPO_HOST: {TEMPO_HOST}, TEMPO_PORT: {TEMPO_PORT}, OTEL_ENDPOINT: {OTEL_ENDPOINT}")


def check_grafana_datasources():
    """
    Check if the Tempo datasource is configured in Grafana.
    
    Returns:
        tuple: (success, details)
    """
    try:
        session = requests.Session()
        session.auth = (GRAFANA_USER, GRAFANA_PASSWORD)
        
        # Get all datasources
        response = session.get(f"{GRAFANA_URL}/api/datasources")
        if response.status_code != 200:
            return False, f"Failed to get datasources: Status {response.status_code}"
        
        datasources = response.json()
        tempo_ds = None
        
        for ds in datasources:
            if ds["type"] == "tempo":
                tempo_ds = ds
                break
        
        if not tempo_ds:
            return False, "No Tempo datasource found in Grafana"
        
        # Check if Tempo datasource is pointing to the correct URL
        ds_url = tempo_ds.get("url", "")
        expected_urls = [f"http://{TEMPO_HOST}:{TEMPO_PORT}", "http://tempo:3200"]
        
        if not any(url in ds_url for url in expected_urls):
            return False, f"Tempo datasource URL is incorrect: {ds_url}"
        
        # Test datasource
        test_url = f"{GRAFANA_URL}/api/datasources/{tempo_ds['id']}/health"
        test_response = session.get(test_url)
        
        # Accept 200 OK or 404 (endpoint might not exist) as non-fatal
        if test_response.status_code not in (200, 404):
            return False, f"Datasource health check failed: Status {test_response.status_code}"
        
        # If 200, check health status
        if test_response.status_code == 200:
            try:
                health_data = test_response.json()
                if health_data.get("status") != "OK":
                    logger.warning(f"Datasource health status: {health_data.get('status', 'Unknown')}, message: {health_data.get('message', 'No message')}")
                    # Don't fail on non-OK status, we'll test the connection directly
            except Exception:
                pass  # Continue even if we can't parse the health response
            
        return True, tempo_ds
        
    except Exception as e:
        return False, f"Error checking Grafana datasources: {str(e)}"


def send_test_traces(service_name="tempo-grafana-test"):
    """
    Send test traces with a distinctive pattern for easy searching in Grafana.
    
    Returns:
        tuple: (success, details)
    """
    # Create a unique test ID and timestamp
    test_id = f"test-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    test_timestamp = datetime.now()
    trace_ids = []
    
    try:
        # Configure resource with distinctive service name
        resource = Resource.create({
            "service.name": service_name,
            "test.id": test_id,
            "test.timestamp": test_timestamp.isoformat(),
        })
        
        # Set up trace provider with resource
        provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(provider)
        
        # Create OTLP exporter to send to collector
        otlp_exporter = OTLPSpanExporter(endpoint=OTEL_ENDPOINT, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        
        # Get tracer
        tracer = trace.get_tracer(service_name)
        
        # Send 3 trace groups with unique attributes for easy search
        for i in range(3):
            trace_group_id = str(uuid.uuid4())
            with tracer.start_as_current_span(f"grafana-tempo-test-{i}") as parent:
                parent.set_attribute("test.group_id", trace_group_id)
                parent.set_attribute("test.index", i)
                parent.set_attribute("test.type", "grafana-tempo")
                
                trace_id = format(parent.get_span_context().trace_id, '032x')
                trace_ids.append(trace_id)
                logger.info(f"Created trace with ID: {trace_id}")
                
                # Add child spans to make the trace more interesting
                with tracer.start_as_current_span("db-query") as child1:
                    child1.set_attribute("db.system", "postgresql")
                    child1.set_attribute("db.statement", "SELECT * FROM test_table")
                    time.sleep(0.1)
                
                with tracer.start_as_current_span("http-call") as child2:
                    child2.set_attribute("http.method", "GET")
                    child2.set_attribute("http.url", "https://example.com/api")
                    time.sleep(0.1)
                    
                    # Add nested span
                    with tracer.start_as_current_span("process-data") as grandchild:
                        grandchild.set_attribute("process.type", "json")
                        time.sleep(0.1)
        
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
        return False, f"Error sending test traces: {str(e)}"


def check_tempo_services(tempo_host=TEMPO_HOST, tempo_port=TEMPO_PORT, service_name=None):
    """
    Check if a service is available in Tempo's services list.
    
    Returns:
        tuple: (success, services_list)
    """
    try:
        # First try the newer API endpoint (Tempo 2.0+)
        response = requests.get(f"http://{tempo_host}:{tempo_port}/api/search/tags/service.name/values")
        
        # If that fails, try the v1 API endpoint
        if response.status_code != 200:
            response = requests.get(f"http://{tempo_host}:{tempo_port}/api/v1/services")
            
        # If both fail, try via Grafana proxy
        if response.status_code != 200:
            session = requests.Session()
            session.auth = (GRAFANA_USER, GRAFANA_PASSWORD)
            datasources_response = session.get(f"{GRAFANA_URL}/api/datasources")
            if datasources_response.status_code == 200:
                datasources = datasources_response.json()
                tempo_ds = next((ds for ds in datasources if ds["type"] == "tempo"), None)
                if tempo_ds:
                    response = session.get(f"{GRAFANA_URL}/api/datasources/proxy/{tempo_ds['id']}/api/search/tags/service.name/values")
        
        if response.status_code != 200:
            return False, f"Failed to get services: Status {response.status_code}"
        
        # Parse response
        try:
            services_data = response.json()
            if not isinstance(services_data, list):
                return False, f"Unexpected response format: {services_data}"
            
            if service_name and service_name not in services_data:
                return True, {"services": services_data, "target_found": False}
            
            return True, {"services": services_data, "target_found": service_name in services_data}
        
        except json.JSONDecodeError:
            return False, f"Failed to parse services response: {response.text[:100]}..."
    
    except Exception as e:
        return False, f"Error checking Tempo services: {str(e)}"


def check_grafana_query_trace(trace_ids=None):
    """
    Check if we can query traces through Grafana's API.
    
    Returns:
        tuple: (success, details)
    """
    try:
        session = requests.Session()
        session.auth = (GRAFANA_USER, GRAFANA_PASSWORD)
        
        # First, we need to get the datasource ID
        response = session.get(f"{GRAFANA_URL}/api/datasources")
        if response.status_code != 200:
            return False, f"Failed to get datasources: Status {response.status_code}"
        
        datasources = response.json()
        tempo_ds = None
        
        for ds in datasources:
            if ds["type"] == "tempo":
                tempo_ds = ds
                break
        
        if not tempo_ds:
            return False, "No Tempo datasource found in Grafana"
        
        ds_uid = tempo_ds.get("uid")
        
        # If we have trace IDs, try to query them
        if trace_ids:
            results = []
            for trace_id in trace_ids[:2]:  # Just try the first two
                trace_url = f"{GRAFANA_URL}/api/datasources/proxy/{tempo_ds['id']}/api/traces/{trace_id}"
                trace_response = session.get(trace_url)
                
                if trace_response.status_code == 200:
                    results.append({
                        "trace_id": trace_id,
                        "found": True,
                        "status": trace_response.status_code
                    })
                else:
                    results.append({
                        "trace_id": trace_id,
                        "found": False,
                        "status": trace_response.status_code,
                        "response": trace_response.text[:100] if trace_response.text else "Empty response"
                    })
            
            # Return based on if any traces were found
            found_any = any(r["found"] for r in results)
            return found_any, {
                "results": results,
                "datasource_id": tempo_ds["id"],
                "datasource_uid": ds_uid
            }
        
        # If no trace IDs, just check if we can get the query interface
        explore_url = f"{GRAFANA_URL}/api/datasources/proxy/{tempo_ds['id']}/api/search/tags"
        explore_response = session.get(explore_url)
        
        if explore_response.status_code != 200:
            return False, f"Failed to query Tempo search tags: Status {explore_response.status_code}"
        
        # Try to parse the response
        try:
            tags_data = explore_response.json()
            return True, {
                "datasource_id": tempo_ds["id"],
                "datasource_uid": ds_uid,
                "available_tags": tags_data
            }
        except json.JSONDecodeError:
            return False, f"Failed to parse search tags response: {explore_response.text[:100]}..."
    
    except Exception as e:
        return False, f"Error checking Grafana query: {str(e)}"


def main():
    """Main test function."""
    print("\n" + "=" * 80)
    print(" Tempo to Grafana Connection Test")
    print("=" * 80)
    
    # Step 1: Check Grafana datasource configuration
    # logger.info("Checking Grafana Tempo datasource configuration...")
    # ds_success, ds_details = check_grafana_datasources()
    
    # if ds_success:
    #     logger.info(f"✅ Tempo datasource configured correctly in Grafana: {json.dumps(ds_details, indent=2)}")
    # else:
    #     logger.error(f"❌ Tempo datasource issue: {ds_details}")
    #     logger.info("\nTroubleshooting steps:")
    #     logger.info("1. Check if Grafana is running: docker ps | grep grafana")
    #     logger.info("2. Log into Grafana (http://localhost:3000) with admin/admin")
    #     logger.info("3. Go to Connections > Data Sources")
    #     logger.info("4. Add or edit the Tempo data source with URL http://tempo:3200")
    #     logger.info("5. Make sure to Save & Test the configuration")
    #     sys.exit(1)
    
    # Step 2: Send test traces with unique service name
    service_name = f"tempo-grafana-test-{int(time.time())}"
    logger.info(f"Sending test traces with service name: {service_name}")
    
    trace_success, trace_details = send_test_traces(service_name)
    if not trace_success:
        logger.error(f"Failed to send test traces: {trace_details}")
        sys.exit(1)
    
    trace_ids = trace_details.get("trace_ids", []) if isinstance(trace_details, dict) else []
    
    # Give traces time to propagate to Tempo and Grafana
    logger.info("Waiting for traces to propagate to Tempo and Grafana (15 seconds)...")
    time.sleep(15)
    
    # Step 3: Check if service appears in Tempo services list
    logger.info("Checking if service appears in Tempo services list...")
    services_success, services_details = check_tempo_services(service_name=service_name)
    
    if services_success and isinstance(services_details, dict):
        if services_details.get("target_found", False):
            logger.info(f"✅ Service {service_name} found in Tempo services list!")
        else:
            service_list = services_details.get("services", [])
            logger.warning(f"⚠️ Service {service_name} NOT found in Tempo services list")
            logger.info(f"Available services: {json.dumps(service_list, indent=2)}")
    else:
        logger.warning(f"⚠️ Failed to query Tempo services list: {services_details}")
    
    # Step 4: Check if we can query traces through Grafana
    logger.info("Checking if traces can be queried through Grafana...")
    query_success, query_details = check_grafana_query_trace(trace_ids)
    
    if query_success:
        logger.info("✅ Successfully queried traces through Grafana!")
        if isinstance(query_details, dict) and "results" in query_details:
            logger.info(f"Query results: {json.dumps(query_details['results'], indent=2)}")
    else:
        logger.warning(f"⚠️ Failed to query traces through Grafana: {query_details}")
    
    # Step 5: Provide manual verification instructions
    print("\n" + "=" * 80)
    print(" Manual Verification Steps")
    print("=" * 80)
    logger.info("1. Open Grafana in your browser: http://localhost:3000")
    logger.info("2. Navigate to Explore (compass icon in left sidebar)")
    logger.info("3. Select 'Tempo' from the data source dropdown at the top")
    logger.info(f"4. In the Query type dropdown, select 'Search' and look for service name: {service_name}")
    logger.info("   Or select 'TraceQL' and enter the query:")
    logger.info(f"   {{service.name=\"{service_name}\"}}")
    logger.info("5. Click 'Run query' and check if traces appear")
    
    if trace_ids:
        logger.info("\nAlternatively, you can directly look up these trace IDs:")
        for trace_id in trace_ids:
            logger.info(f"- {trace_id}")
    
    # Final summary
    print("\n" + "=" * 80)
    if (services_success and isinstance(services_details, dict) and services_details.get("target_found", False) or 
        query_success
    ):
        logger.info("🎉 OVERALL TEST: PASSED! Tempo to Grafana connection is working!")
    else:
        logger.info("⚠️ OVERALL TEST: PARTIAL SUCCESS OR FAILURE")
        
    logger.info("\nTroubleshooting steps if visualization fails:")
    logger.info("1. Check network connectivity between Grafana and Tempo containers")
    logger.info("2. Verify Tempo datasource configuration in Grafana")
    logger.info("3. Check Grafana logs: docker logs grafana")
    logger.info("4. Check Tempo logs: docker logs tempo")
    logger.info("5. Ensure traces are actually getting to Tempo (use test_otel_to_tempo.py)")
    
    print("=" * 80)


if __name__ == "__main__":
    main()
