import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from langchain_core.messages import AIMessage, HumanMessage

from app.agent.resilience import (
    LLMBackendError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
    SearchBackendError,
    SearchProviderError,
    SearchRateLimitError,
    SearchTimeoutError,
)
from app.api.routes import _stream_response
from app.cache_policy import (
    CacheKeyContext,
    direct_answer_cache_key,
    search_results_cache_key,
)
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


class FakeStreamGraph:
    def __init__(
        self,
        *,
        pause_after_first_token: asyncio.Event | None = None,
        final_response: str = "The EUR/USD rate is 1.08 [1].",
    ):
        self.pause_after_first_token = pause_after_first_token
        self.final_response = final_response
        self.ainvoke = AsyncMock()

    async def astream_events(self, state, version="v2"):
        yield {
            "event": "on_chain_end",
            "name": "router",
            "data": {"output": {"route": "search"}},
        }
        yield {
            "event": "on_chat_model_stream",
            "name": "MockModel",
            "data": {"chunk": SimpleNamespace(content="The ")},
        }
        if self.pause_after_first_token is not None:
            await self.pause_after_first_token.wait()
        yield {
            "event": "on_chat_model_stream",
            "name": "MockModel",
            "data": {"chunk": SimpleNamespace(content="EUR/USD rate is 1.08 [1].")},
        }
        yield {
            "event": "on_chain_end",
            "name": "LangGraph",
            "data": {
                "output": {
                    "messages": [SimpleNamespace(content=self.final_response)],
                    "route": "search",
                    "sources": [
                        {
                            "title": "Reuters",
                            "url": "https://reuters.com",
                            "snippet": "EUR/USD at 1.08",
                        }
                    ],
                }
            },
        }


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
            json={"query": "Summarize last week Fed decision", "stream": False},
        )

    assert response.status_code == 200
    assert len(cache.set_calls) >= 1


@pytest.mark.asyncio
async def test_query_json_marks_reused_search_results_as_stale(app, mock_graph):
    """Cached search-result reuse should surface stale-result metadata."""
    query = "Summarize last week Fed decision"
    cache = FakeCache(
        {
            search_results_cache_key(query): {
                "results": [
                    {
                        "title": "Reuters",
                        "url": "https://reuters.com",
                        "content": "ECB updated guidance",
                    }
                ],
                "retrieved_at": "2026-03-29T00:00:00+00:00",
            }
        }
    )
    app.state.cache = cache
    app.state.model = "test-model"
    app.state.cache_prompt_revision = "v1"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/query",
            json={"query": query, "stream": False},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["cache_hit"] is True
    assert data["cache_tier"] == "search_results"
    assert data["stale_results"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("raised_error", "status_code", "detail_code"),
    [
        (SearchTimeoutError(), 504, "search_timeout"),
        (SearchRateLimitError(), 429, "search_rate_limited"),
        (SearchBackendError(), 503, "search_backend_unavailable"),
        (SearchProviderError(), 503, "search_provider_failure"),
        (LLMTimeoutError(), 504, "llm_timeout"),
        (LLMRateLimitError(), 429, "llm_rate_limited"),
        (LLMBackendError(), 503, "llm_backend_unavailable"),
        (LLMProviderError(), 503, "llm_provider_failure"),
    ],
)
async def test_query_maps_external_failures(
    app, mock_graph, raised_error, status_code, detail_code
):
    """POST /query should map typed provider failures to stable HTTP responses."""
    mock_graph.ainvoke = AsyncMock(side_effect=raised_error)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/query",
            json={"query": "Current EUR/USD rate", "stream": False},
        )

    assert response.status_code == status_code
    assert response.json()["detail"]["code"] == detail_code


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
async def test_query_sse_stream_returns_sse_events(app):
    """POST /query with stream=true returns SSE events."""
    app.state.graph = FakeStreamGraph()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/query",
            json={"query": "Current EUR/USD rate", "stream": True},
        )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert "event: route" in response.text
    assert "event: meta" in response.text
    assert "event: token" in response.text
    assert "event: sources" in response.text
    assert "event: done" in response.text


@pytest.mark.asyncio
async def test_stream_response_is_incremental_and_ordered():
    """The SSE generator emits route/meta before later chunks arrive."""
    pause_after_first_chunk = asyncio.Event()
    graph = FakeStreamGraph(pause_after_first_token=pause_after_first_chunk)
    state = {
        "messages": [("human", "Current EUR/USD rate")],
        "route": "",
        "sources": [],
    }
    cached_meta = {
        "cache_hit": False,
        "cache_tier": "none",
        "retrieved_at": None,
        "stale_results": False,
    }

    events = _stream_response(graph, state, cached_meta)
    first = await events.__anext__()
    second = await events.__anext__()
    third = await events.__anext__()

    assert "event: route" in first
    assert "event: meta" in second
    assert "event: token" in third
    assert "The " in third

    next_event = asyncio.create_task(events.__anext__())
    await asyncio.sleep(0)
    assert next_event.done() is False

    assert pause_after_first_chunk.is_set() is False
    pause_after_first_chunk.set()

    fourth = await next_event
    assert "event: token" in fourth

    remaining = [chunk async for chunk in events]
    assert "event: sources" in remaining[0]
    assert "event: done" in remaining[1]


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
