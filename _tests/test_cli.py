"""
Test script to send a trace to Tempo via the application's tempo client
"""
import sys
import os
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("tempo-cli-test")

# Add the parent directory to the path to import the app modules
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.insert(0, parent_dir)

from app.core.tempo.core import TempoClient

def main():
    """Send a test trace to Tempo"""
    # Use otel-collector endpoint for reliable trace delivery
    os.environ["TEMPO_EXPORTER_ENDPOINT"] = "localhost:4317"
    
    # Create a tempo client for testing
    tempo_client = TempoClient(
        service_name="tempo-cli-test",
        service_version="1.0.0",
        environment="test"
    )
    
    # Send multiple spans with different data to create a rich trace
    logger.info("Creating test trace with multiple spans...")
    
    # Create a parent span
    with tempo_client.create_span("test-parent-operation") as parent:
        parent.set_attribute("test_run", True)
        parent.set_attribute("service.name", "tempo-cli-test")
        parent.set_attribute("environment", "test")
        
        # Add child spans with timing
        for i in range(3):
            with tempo_client.create_span(f"test-child-{i}") as child:
                child.set_attribute("child_index", i)
                child.set_attribute("service.name", "tempo-cli-test")
                
                # Add some processing time to make the trace interesting
                time.sleep(0.1 * (i + 1))
                
                # Add an event
                child.add_event(f"processed-item-{i}", {
                    "timestamp": time.time(),
                    "item_value": i * 100
                })
    
    # Force flush to ensure trace is sent
    logger.info("Flushing trace data...")
    tempo_client.shutdown()
    
    logger.info(f"Test complete! Check Grafana Tempo for traces from service 'tempo-cli-test'")
    logger.info("If you don't see traces in Grafana, try these troubleshooting steps:")
    logger.info("1. Make sure the Tempo container is running: docker ps | grep tempo")
    logger.info("2. Check Tempo logs: docker logs tempo")
    logger.info("3. Check otel-collector logs: docker logs otel-collector")
    logger.info("4. Verify Grafana can reach Tempo: docker exec -it grafana curl -I http://tempo:3200")

if __name__ == "__main__":
    main()
