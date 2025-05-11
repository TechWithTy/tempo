"""
Test suite for Tempo full functionality and best practices, following project and OpenTelemetry guidelines.
References:
- best_practices.md
- https://opentelemetry.io/docs/specs/otel/trace/api/
"""

import pytest
import requests
import time
import uuid

TEMPO_HOST = "127.0.0.1"
TEMPO_PORT = 3200
TEMPO_OTLP_GRPC_PORT = 14317
TEMPO_OTLP_HTTP_PORT = 14318

# * Helper: Query Tempo metrics endpoint to check health

def tempo_is_healthy():
    try:
        resp = requests.get(f"http://{TEMPO_HOST}:{TEMPO_PORT}/metrics", timeout=2)
        return resp.status_code == 200
    except Exception:
        return False

# * Helper: 
import pytest
from unittest.mock import patch, MagicMock

# * Pytest fixture for mocking Tempo API responses
tempo_trace_mock_response = {
    "data": {
        "spans": [
            {
                "traceID": "mockedtraceid",
                "attributes": {"test.attribute": "value", "env": "test"}
            }
        ]
    }
}

@pytest.fixture
def mock_tempo_api():
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = tempo_trace_mock_response
        mock_get.return_value = mock_response
        yield mock_get

# * Parameterized test for different edge cases
@pytest.mark.usefixtures("ensure_tempo_running")
@pytest.mark.parametrize("mock_json,status_code,expected", [
    # Normal trace found
    (tempo_trace_mock_response, 200, True),
    # No spans found
    ({"data": {"spans": []}}, 200, False),
    # Tempo returns error
    ({}, 404, False),
])
def test_query_mocked_tempo_trace(mock_tempo_api, mock_json, status_code, expected):
    mock_tempo_api.return_value.status_code = status_code
    mock_tempo_api.return_value.json.return_value = mock_json
    trace_id = "mockedtraceid"
    url = f"http://{TEMPO_HOST}:{TEMPO_PORT}/api/traces/{trace_id}"
    resp = requests.get(url)
    if status_code != 200:
        assert not expected
        return
    data = resp.json()
    spans = data.get('data', {}).get('spans', [])
    if expected:
        assert spans, "Expected at least one span in mocked response"
        attr_keys = [k for span in spans for k in span.get('attributes', {})]
        assert "test.attribute" in attr_keys, "Expected attribute missing in mocked trace"
    else:
        assert not spans, "Expected no spans in mocked response"


@pytest.mark.usefixtures("ensure_tempo_running")
def test_tempo_container_healthy():
    """
    Test that the Tempo container is running and healthy.
    """
    assert tempo_is_healthy(), "Tempo metrics endpoint not healthy"

