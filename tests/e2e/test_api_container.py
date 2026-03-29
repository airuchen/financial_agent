"""E2E tests that run against a live Docker container.

These tests expect the API to be running at http://localhost:8000.
They are skipped if the service is not reachable.
"""

import httpx
import pytest

BASE_URL = "http://localhost:8000"


@pytest.fixture(scope="module")
def check_service():
    """Skip all tests if the API service is not running."""
    try:
        response = httpx.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            pytest.skip("API service not healthy")
    except httpx.ConnectError:
        pytest.skip("API service not running at localhost:8000")


@pytest.mark.usefixtures("check_service")
class TestE2EApi:
    def test_health(self):
        """Health endpoint returns ok status."""
        response = httpx.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_query_json(self):
        """POST /query with stream=false returns valid JSON response."""
        response = httpx.post(
            f"{BASE_URL}/query",
            json={"query": "What is diversification?", "stream": False},
            timeout=60,
        )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert data["route"] in ("search", "direct")

    def test_query_sse_stream(self):
        """POST /query with stream=true returns SSE events."""
        with httpx.stream(
            "POST",
            f"{BASE_URL}/query",
            json={"query": "Hello", "stream": True},
            timeout=60,
        ) as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]

            events = []
            for line in response.iter_lines():
                if line.startswith("event:"):
                    events.append(line.split("event: ")[1])

            assert "route" in events
            assert "done" in events

    def test_query_validation_error(self):
        """POST /query with empty query returns 422."""
        response = httpx.post(
            f"{BASE_URL}/query",
            json={"query": ""},
            timeout=10,
        )
        assert response.status_code == 422
