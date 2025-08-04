#!/usr/bin/env python
"""
CLI tool to test the Tempo integration by sending test spans directly.
Run this after starting the Tempo container to verify connectivity.
"""
import argparse
import logging
import sys
import time
import os

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("tempo-cli")

def setup_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Tempo CLI tool for testing and diagnostics")
    parser.add_argument("--test", action="store_true", help="Send test spans to Tempo")
    parser.add_argument("--endpoint", default=None, help="Override the Tempo OTLP endpoint")
    parser.add_argument("--grafana-check", action="store_true", help="Check Grafana Tempo datasource configuration")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    
    return parser.parse_args()

def test_tempo_spans(endpoint=None):
    """Send test spans to Tempo"""
    from app.core.tempo.core import init_tempo, get_tempo
    
    # Override endpoint if provided
    if endpoint:
        os.environ["TEMPO_EXPORTER_ENDPOINT"] = endpoint
        logger.info(f"Using override endpoint: {endpoint}")
    
    # Initialize tempo client
    tempo_client = init_tempo(
        service_name="tempo-cli-test",
        service_version="1.0.0",
        environment="test"
    )
    
    # Send a series of test spans
    logger.info("Sending test spans to Tempo...")
    for i in range(3):
        logger.info(f"Sending test span {i+1}/3")
        tempo_client.send_test_span()
        time.sleep(1)
    
    logger.info("Test spans sent. Check Grafana Tempo for results.")
    
    # Shutdown to ensure all spans are flushed
    tempo_client.shutdown()

def check_grafana_tempo():
    """Run the Grafana-Tempo connection check script"""
    import importlib.util
    import subprocess
    
    script_path = os.path.join(os.path.dirname(__file__), "check_grafana_tempo.py")
    
    if os.path.exists(script_path):
        logger.info("Running Grafana-Tempo connection check...")
        subprocess.run([sys.executable, script_path], check=False)
    else:
        logger.error(f"Check script not found at: {script_path}")

def main():
    """Main entry point"""
    args = setup_args()
    
    # Set log level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    
    logger.info("Tempo CLI Tool")
    logger.info("=============")
    
    if args.test:
        test_tempo_spans(args.endpoint)
    
    if args.grafana_check:
        check_grafana_tempo()
    
    if not (args.test or args.grafana_check):
        logger.info("No action specified. Use --test or --grafana-check")
        logger.info("Run with --help for more information")

if __name__ == "__main__":
    main()
