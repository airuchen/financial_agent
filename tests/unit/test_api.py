from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.messages import AIMessage, HumanMessage

from app.main import create_app
from app.models import Source


@pytest.fixture
def mock_graph():
    """Create a mock compiled graph."""
    graph = AsyncMock()
    graph.ainvoke = AsyncMock(
        return_value={
            "messages": [
                HumanMessage(content="test query"),
                AIMessage(content="The EUR/USD rate is 1.08."),
            ],
            "route": "search",
            "sources": [
                Source(
                    title="Reuters",
                    url="https://reuters.com",
                    snippet="EUR/USD at 1.08",
                ),
            ],
        }
    )
    return graph


@pytest.fixture
def app(mock_graph):
    """Create a test FastAPI app with mocked graph."""
    application = create_app()
    application.state.graph = mock_graph
    application.state.provider = "test"
    return application


@pytest.mark.asyncio
async def test_query_json_response(app, mock_graph):
    """POST /query with stream=false returns JSON response."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/query",
            json={"query": "Current EUR/USD rate", "stream": False},
        )
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert data["route"] == "search"
    assert len(data["sources"]) == 1


@pytest.mark.asyncio
async def test_query_missing_query(app):
    """POST /query with empty query returns 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/query", json={"query": ""})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_query_too_long(app):
    """POST /query over max query length returns 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/query", json={"query": "x" * 2001})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_health_endpoint(app):
    """GET /health returns status."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["provider"] == "test"


@pytest.mark.asyncio
async def test_query_sse_stream(app):
    """POST /query with stream=true returns SSE events."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/query",
            json={"query": "Current EUR/USD rate", "stream": True},
        )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    body = response.text
    assert "event: route" in body
    assert "event: token" in body
    assert "event: done" in body
