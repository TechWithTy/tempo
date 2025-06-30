# Tempo Test Suite

This directory contains test scripts to diagnose and troubleshoot issues with the Tempo tracing pipeline.

## Overview of Tests

1. **test_app_to_otel.py** - Tests the connection between the FastAPI app and OpenTelemetry collector
2. **test_otel_to_tempo.py** - Tests the connection between OpenTelemetry collector and Tempo
3. **test_tempo_to_grafana.py** - Tests the connection between Tempo and Grafana
4. **run_all_tests.py** - A convenience script to run all tests in sequence

## Running the Tests

Make sure all required packages are installed:

```bash
poetry add opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp requests
```

Run individual tests:

```bash
# Test app to OpenTelemetry connection
poetry run python -m app.core.tempo._tests.test_app_to_otel

# Test OpenTelemetry to Tempo connection
poetry run python -m app.core.tempo._tests.test_otel_to_tempo

# Test Tempo to Grafana connection
poetry run python -m app.core.tempo._tests.test_tempo_to_grafana
```

Or run all tests sequentially:

```bash
poetry run python -m app.core.tempo._tests.run_all_tests
```

## Common Issues and Solutions

1. **"No service names found" in Grafana Tempo:**
   - Ensure trace data is actually reaching Tempo
   - Check if the service name is consistent across all spans
   - Try sending test spans with a very specific service name for easier identification

2. **Traces sent but not visible:**
   - Verify if the Tempo container is storing the data correctly
   - Check retention settings in Tempo configuration
   - Make sure Grafana is querying the correct Tempo instance

3. **Connection refused errors:**
   - Check network connectivity between services
   - Verify ports are correctly mapped in Docker Compose
   - Ensure services are running and healthy

4. **Docker networking issues:**
   - When running inside Docker, use service names like `tempo:4317`
   - When running on host machine, use `localhost:14317` (mapped port)
   - Check Docker network configurations and ensure the app is on same network as services

## Docker Commands for Troubleshooting

```bash
# Check container logs
docker logs tempo
docker logs otel-collector
docker logs grafana

# Restart the services
docker-compose -f docker-compose.monitoring.yml restart tempo otel-collector grafana

# Check the running containers
docker ps --format "{{.Names}}: {{.Status}}" | grep -E "tempo|otel|grafana"
```
