from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from langchain_core.messages import AIMessage, HumanMessage

from app.cache_policy import CacheKeyContext, direct_answer_cache_key
from app.main import create_app
from app.models import Source


class FakeCache:
    def __init__(self, initial: dict | None = None):
        self.store = initial or {}
        self.set_calls = []

    async def get_json(self, key: str):
        return self.store.get(key)

    async def set_json(self, key: str, value: dict, ttl_seconds: int):
        self.set_calls.append((key, value, ttl_seconds))
        self.store[key] = value


class AllowGuard:
    async def enforce(self, request):
        return None


class RejectGuard:
    def __init__(self, status_code: int, detail: dict, headers: dict | None = None):
        self.status_code = status_code
        self.detail = detail
        self.headers = headers

    async def enforce(self, request):
        raise HTTPException(
            status_code=self.status_code,
            detail=self.detail,
            headers=self.headers,
        )


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
    application.state.guard = AllowGuard()
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
async def test_query_json_uses_cached_direct_answer(app, mock_graph):
    """POST /query returns cached direct response when available."""
    cache_key = direct_answer_cache_key(
        "What is diversification?",
        CacheKeyContext(model="test-model", prompt_revision="v1"),
    )
    app.state.cache = FakeCache(
        {
            cache_key: {
                "response": "Diversification spreads risk.",
                "route": "direct",
                "sources": [],
                "cache_tier": "direct",
                "retrieved_at": "2026-03-29T00:00:00+00:00",
            }
        }
    )
    app.state.model = "test-model"
    app.state.cache_prompt_revision = "v1"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/query",
            json={"query": "What is diversification?", "stream": False},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["cache_hit"] is True
    assert data["cache_tier"] == "direct"
    assert data["route"] == "direct"
    mock_graph.ainvoke.assert_not_awaited()


@pytest.mark.asyncio
async def test_query_json_writes_cache_for_noncritical_search(app, mock_graph):
    """POST /query writes search caches for non-critical search queries."""
    cache = FakeCache()
    app.state.cache = cache
    app.state.model = "test-model"
    app.state.cache_prompt_revision = "v1"
    app.state.cache_ttl_direct_sec = 86400
    app.state.cache_ttl_search_results_sec = 900
    app.state.cache_ttl_search_answer_sec = 300

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/query",
            json={"query": "Summarize last week ECB communication", "stream": False},
        )

    assert response.status_code == 200
    assert len(cache.set_calls) >= 1


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
    assert "event: meta" in body
    assert "event: token" in body
    assert "event: done" in body


@pytest.mark.asyncio
async def test_query_missing_api_key_returns_401(app):
    """POST /query should return 401 when guard rejects auth."""
    app.state.guard = RejectGuard(
        401,
        {"code": "unauthorized", "message": "Missing or invalid API key."},
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/query",
            json={"query": "What is diversification?", "stream": False},
        )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "unauthorized"


@pytest.mark.asyncio
async def test_query_rate_limit_returns_429_with_headers(app):
    """POST /query should return 429 with retry/rate-limit headers."""
    app.state.guard = RejectGuard(
        429,
        {"code": "rate_limit_exceeded", "message": "Too many requests."},
        headers={
            "Retry-After": "30",
            "X-RateLimit-Limit-Minute": "60",
            "X-RateLimit-Remaining-Minute": "0",
        },
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/query",
            json={"query": "What is diversification?", "stream": False},
        )
    assert response.status_code == 429
    assert response.headers["retry-after"] == "30"
    assert response.headers["x-ratelimit-limit-minute"] == "60"


@pytest.mark.asyncio
async def test_query_rate_limiter_unavailable_returns_503(app):
    """POST /query should fail closed with 503 when limiter is unavailable."""
    app.state.guard = RejectGuard(
        503,
        {
            "code": "rate_limiter_unavailable",
            "message": "Rate-limiting backend unavailable; retry later.",
        },
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/query",
            json={"query": "What is diversification?", "stream": False},
        )
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "rate_limiter_unavailable"
