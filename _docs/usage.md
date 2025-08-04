# Using Tempo Tracing with FastAPI

This guide explains how to use the integrated Tempo tracing system with FastAPI to visualize request journeys and improve performance.

## Overview

The Tempo tracing integration works alongside the existing telemetry system to provide enhanced distributed tracing capabilities. This integration allows you to:

1. Visualize the complete journey of a request through your API
2. Identify performance bottlenecks in your application
3. Track database operations and their performance
4. Correlate traces across multiple services
5. Monitor API endpoint performance in real-time

## Decorators for Tracing

### API Route Tracing

The `trace_api_route` decorator can be added to any FastAPI route handler to automatically create a trace span for the request:

```python
from app.core.tempo.api_tracing import trace_api_route

@router.get("/items")
@trace_api_route(
    operation_name="items.list",  # Optional custom name
    include_query_params=True,    # Include query parameters in trace
    include_path_params=True,     # Include path parameters in trace
    include_headers=False,        # Don't include headers by default
    include_request_body=False,   # Don't include request body by default
    include_response_body=False   # Don't include response body by default
)
async def read_items():
    # Your API logic here
    pass
```

### Database Operation Tracing

The `trace_db_operation` decorator can be added to any database function to track its performance:

```python
from app.core.tempo.api_tracing import trace_db_operation

@trace_db_operation(operation="get", table="users")
async def get_user(user_id: str):
    # Database logic here
    pass
```

## Viewing Traces in Grafana

1. Access your Grafana instance (typically at http://localhost:3000 or your deployment URL)
2. Navigate to the Explore section
3. Select Tempo as the data source
4. Use the search interface to find traces:
   - Search by trace ID if you have it
   - Search by service name
   - Filter by duration to find slow requests
   - Filter by HTTP status code to find errors

## Common Trace Attributes

The tracing system captures many useful attributes automatically:

- `http.method`: The HTTP method of the request (GET, POST, etc.)
- `http.url`: The full URL of the request
- `http.route`: The route pattern of the request
- `http.status_code`: The HTTP status code of the response
- `duration_ms`: The duration of the request in milliseconds
- `error.message`: Error message if an exception occurred
- `db.operation`: Type of database operation (select, insert, etc.)
- `db.table`: Database table being accessed

## Best Practices

1. **Add tracing to critical paths**: Focus on high-traffic or performance-sensitive routes first
2. **Don't include sensitive data**: Be careful with what you include in spans (no passwords, tokens, etc.)
3. **Use meaningful operation names**: Choose descriptive names that make it easy to identify operations
4. **Add custom attributes for context**: Add business-specific attributes to help with debugging
5. **Sample appropriately**: For high-volume endpoints, consider using sampling to reduce overhead

## Troubleshooting

If traces aren't appearing in Grafana Tempo:

1. Check that the Tempo exporter endpoint is correctly configured in environment variables
2. Verify that the Tempo service is running and accessible
3. Look for errors in the application logs related to the Tempo client
4. Check that the trace context is being properly propagated between services
5. Verify that the sampling rate isn't set too low

## Additional Resources

- [Grafana Tempo Documentation](https://grafana.com/docs/tempo/latest/)
- [OpenTelemetry Python Documentation](https://opentelemetry.io/docs/instrumentation/python/)
- [FastAPI Instrumentation Guide](https://opentelemetry.io/docs/instrumentation/python/automatic/fastapi/)
