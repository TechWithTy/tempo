# Tempo Tracing Integration Guide

This guide explains how to set up and troubleshoot Tempo tracing with Grafana in the FastAPI Connect application.

## Components

1. **Tempo**: Distributed tracing backend that stores and queries traces
2. **OpenTelemetry Collector**: Collects traces from applications and forwards them to Tempo
3. **Grafana**: Visualization platform that connects to Tempo for trace viewing

## Setup

### Running the Stack

The easiest way to run the complete monitoring stack with Tempo tracing:

### Accessing Grafana

1. Open Grafana at http://localhost:3000
2. Login with:
   - Username: `admin`
   - Password: `admin`
3. Navigate to Explore
4. Select the Tempo data source from the dropdown
5. Search for traces by service name (e.g., "tempo-test")

## Troubleshooting

If traces aren't showing up in Grafana:

1. **Network Connectivity**
   - Ensure all services are on the `app-network` Docker network
   - Verify container names match those used in configuration files

2. **OpenTelemetry Collector**
   - Check that the collector configuration exports traces to Tempo
   - Verify the collector is receiving traces by checking its logs:
     ```bash
     docker logs otel-collector
     ```

3. **Tempo Configuration**
   - Make sure Tempo is properly configured to receive traces via OTLP
   - Check if Tempo is running correctly:
     ```bash
     docker logs tempo
     ```

4. **Grafana Data Source**
   - Verify the Tempo data source is correctly configured in Grafana
   - Check that URL is set to `http://tempo:3200`

5. **Test Script**
   - Run the verification script to generate test traces:
     ```bash
     cd backend
     pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp
     python -m app.core.tempo.verify_tempo
     ```

## Configuration Files

Key configuration files:

- `backend/app/core/tempo/docker/tempo-config.example.yaml`: Tempo configuration
- `backend/app/core/telemetry/docker/otel-collector-config.yaml`: OpenTelemetry collector config
- `backend/app/core/grafana/provisioning/datasources/tempo.yaml`: Grafana Tempo data source config
- `docker-compose.monitoring.yml`: Docker Compose configuration for monitoring stack

## Adding Traces to Your Application

To add traces to your FastAPI application:

1. Install the required packages:

```bash
pip install opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation-fastapi opentelemetry-exporter-otlp
```

2. Add instrumentation to your FastAPI app:

```python
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Configure the tracer
resource = Resource(attributes={SERVICE_NAME: "your-service-name"})
tracer_provider = TracerProvider(resource=resource)
trace.set_tracer_provider(tracer_provider)

# Create OTLP exporter and add it to the tracer provider
otlp_exporter = OTLPSpanExporter(endpoint="otel-collector:4317", insecure=True)
tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

# Instrument FastAPI
app = FastAPI()
FastAPIInstrumentor.instrument_app(app)
```
