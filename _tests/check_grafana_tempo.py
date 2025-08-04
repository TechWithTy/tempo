#!/usr/bin/env python
"""
Script to check the status of Grafana and Tempo integration.
This script queries the Grafana API to verify the Tempo datasource status.
"""
import os
import sys
import logging
import requests
import json

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, 
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("grafana-check")

# Grafana settings (adjust as needed)
GRAFANA_URL = os.environ.get("GRAFANA_URL", "http://localhost:3000")
GRAFANA_USER = os.environ.get("GRAFANA_USER", "admin")
GRAFANA_PASSWORD = os.environ.get("GRAFANA_PASSWORD", "admin")

def check_grafana_health():
    """Check if Grafana is up and running"""
    try:
        response = requests.get(f"{GRAFANA_URL}/api/health", timeout=5)
        response.raise_for_status()
        logger.info(f"Grafana health check: {response.json()}")
        return True
    except Exception as e:
        logger.error(f"Grafana health check failed: {e}")
        return False

def check_tempo_datasource():
    """Check if Tempo datasource is configured in Grafana"""
    try:
        # Authenticate
        session = requests.Session()
        session.auth = (GRAFANA_USER, GRAFANA_PASSWORD)
        
        # Get datasources
        response = session.get(f"{GRAFANA_URL}/api/datasources", timeout=5)
        response.raise_for_status()
        
        datasources = response.json()
        logger.info(f"Found {len(datasources)} datasources:")
        
        tempo_datasource = None
        for ds in datasources:
            logger.info(f"- {ds['name']} (type: {ds['type']}, id: {ds['id']})")
            if ds['type'] == 'tempo':
                tempo_datasource = ds
        
        if tempo_datasource:
            logger.info(f"Found Tempo datasource: {tempo_datasource['name']}")
            
            # Check datasource health
            health_response = session.get(
                f"{GRAFANA_URL}/api/datasources/{tempo_datasource['id']}/health", 
                timeout=5
            )
            health_response.raise_for_status()
            
            health_data = health_response.json()
            logger.info(f"Tempo datasource health: {json.dumps(health_data, indent=2)}")
            
            return True
        else:
            logger.warning("No Tempo datasource found in Grafana")
            return False
            
    except Exception as e:
        logger.error(f"Error checking Tempo datasource: {e}")
        return False

def main():
    logger.info("Starting Grafana and Tempo datasource check")
    
    if not check_grafana_health():
        logger.error("Grafana is not available")
        return
    
    if not check_tempo_datasource():
        logger.warning("Tempo datasource is not properly configured")
        
        # Provide advice on how to add Tempo datasource
        logger.info("\nTo add Tempo datasource in Grafana:")
        logger.info("1. Go to Grafana UI (http://localhost:3000)")
        logger.info("2. Navigate to Connections > Data Sources")
        logger.info("3. Click 'Add data source'")
        logger.info("4. Search for and select 'Tempo'")
        logger.info("5. Set URL to 'http://tempo:3200' (if using Docker Compose)")
        logger.info("6. Click 'Save & Test'")
    
    logger.info("Check complete")

if __name__ == "__main__":
    main()
