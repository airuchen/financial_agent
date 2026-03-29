import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.agent.resilience import ExternalServiceError
from app.cache_policy import (
    CacheKeyContext,
    classify_cache_policy,
    direct_answer_cache_key,
    search_answer_cache_key,
    search_results_cache_key,
)
from app.models import QueryRequest, QueryResponse, Source
from app.utils import format_sse_event

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/query")
async def query(request: Request, body: QueryRequest):
    """Handle a financial research query.

    Routes the query through the agent graph and returns
    either a streaming SSE response or a JSON response.

    Args:
        request: The FastAPI request (for accessing app state).
        body: The validated query request body.

    Returns:
        StreamingResponse for SSE or QueryResponse for JSON.
    """
    graph = request.app.state.graph
    cache = getattr(request.app.state, "cache", None)
    key_ctx = CacheKeyContext(
        model=getattr(request.app.state, "model", "unknown"),
        prompt_revision=getattr(request.app.state, "cache_prompt_revision", "v1"),
    )
    policy = classify_cache_policy(body.query)
    state: dict[str, Any] = {
        "messages": [("human", body.query)],
        "route": "",
        "sources": [],
    }
    cached_meta = {
        "cache_hit": False,
        "cache_tier": "none",
        "retrieved_at": None,
        "stale_results": False,
    }

    try:
        guard = getattr(request.app.state, "guard", None)
        if guard:
            await guard.enforce(request)

        if cache and policy != "critical_market":
            if policy == "direct_knowledge":
                cached_direct = await cache.get_json(
                    direct_answer_cache_key(body.query, key_ctx)
                )
                if cached_direct:
                    return _cached_response(body.stream, cached_direct)

            if policy == "search_noncritical":
                cached_search_answer = await cache.get_json(
                    search_answer_cache_key(body.query, key_ctx)
                )
                if cached_search_answer:
                    return _cached_response(body.stream, cached_search_answer)

                cached_results = await cache.get_json(
                    search_results_cache_key(body.query)
                )
                if cached_results and isinstance(cached_results.get("results"), list):
                    state["cached_search_results"] = cached_results["results"]
                    cached_meta = {
                        "cache_hit": True,
                        "cache_tier": "search_results",
                        "retrieved_at": cached_results.get("retrieved_at"),
                        "stale_results": True,
                    }

        if body.stream:
            return StreamingResponse(
                _stream_response(graph, state, cached_meta),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )

        result = await graph.ainvoke(state)
        final_message = result["messages"][-1].content
        sources = [
            Source(**s) if isinstance(s, dict) else s for s in result.get("sources", [])
        ]
        response_data = QueryResponse(
            response=final_message,
            route=result.get("route", ""),
            sources=sources,
            cache_hit=cached_meta["cache_hit"],
            cache_tier=cached_meta["cache_tier"],
            retrieved_at=cached_meta["retrieved_at"],
            stale_results=cached_meta["stale_results"],
        )
        await _maybe_write_cache(
            cache=cache,
            query=body.query,
            key_ctx=key_ctx,
            result=result,
            policy=policy,
            ttl_direct_sec=getattr(request.app.state, "cache_ttl_direct_sec", 86400),
            ttl_search_results_sec=getattr(
                request.app.state, "cache_ttl_search_results_sec", 900
            ),
            ttl_search_answer_sec=getattr(
                request.app.state, "cache_ttl_search_answer_sec", 300
            ),
        )
        return QueryResponse(**response_data.model_dump())
    except HTTPException:
        raise
    except ExternalServiceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": exc.message},
            headers=exc.headers,
        ) from None
    except TimeoutError:
        raise HTTPException(
            status_code=504,
            detail={"code": "request_timeout", "message": "Request timed out"},
        ) from None
    except Exception:
        logger.exception("Unexpected error processing query")
        raise HTTPException(status_code=500, detail="Internal server error") from None


async def _stream_response(graph, state: dict[str, Any], cached_meta: dict[str, Any]):
    """Generate SSE events from the agent graph.

    Args:
        graph: The compiled LangGraph.
        state: Prepared graph state.
        cached_meta: Cache metadata for the current request.

    Yields:
        Formatted SSE event strings.
    """
    route_emitted = False
    final_state: dict[str, Any] | None = None
    final_message = ""
    sources_data: list[dict[str, Any]] = []

    try:
        event_stream = graph.astream_events(
            state,
            version="v2",
            config={"configurable": {"stream_tokens": True}},
        )
    except TypeError:
        # Test fakes may not accept the optional config kwarg.
        event_stream = graph.astream_events(state, version="v2")

    async for event in event_stream:
        event_name = event.get("event")
        name = event.get("name")
        data = event.get("data") or {}

        if event_name == "on_chain_end" and name == "router":
            output = data.get("output") or {}
            route = output.get("route", "") if isinstance(output, dict) else ""
            yield format_sse_event("route", {"route": route})
            yield format_sse_event("meta", cached_meta)
            route_emitted = True
            continue

        if event_name == "on_chat_model_stream" and route_emitted:
            chunk = data.get("chunk")
            content = _chunk_content(chunk)
            if content:
                yield format_sse_event("token", {"content": content, "type": "token"})
            continue

        if event_name == "on_chain_end" and name == "LangGraph":
            output = data.get("output")
            if isinstance(output, dict):
                final_state = output

    if final_state is None:
        final_state = state

    if not route_emitted:
        route = final_state.get("route", "")
        yield format_sse_event("route", {"route": route})
        yield format_sse_event("meta", cached_meta)

    sources_data = _serialize_sources(final_state.get("sources", []))
    if sources_data:
        yield format_sse_event("sources", {"sources": sources_data})

    messages = final_state.get("messages", [])
    if messages:
        final_message = getattr(messages[-1], "content", "")

    yield format_sse_event(
        "done",
        {
            "full_response": final_message,
            "cache_hit": cached_meta.get("cache_hit", False),
            "cache_tier": cached_meta.get("cache_tier"),
            "retrieved_at": cached_meta.get("retrieved_at"),
            "stale_results": cached_meta.get("stale_results", False),
        },
    )


@router.get("/health")
async def health(request: Request):
    """Health check endpoint.

    Returns:
        JSON with status and provider info.
    """
    return {
        "status": "ok",
        "provider": getattr(request.app.state, "provider", "unknown"),
    }


def _cached_response(stream: bool, payload: dict[str, Any]):
    if stream:
        return StreamingResponse(
            _stream_cached_response(payload),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    return QueryResponse(
        response=payload["response"],
        route=payload["route"],
        sources=[Source(**s) for s in payload.get("sources", [])],
        cache_hit=True,
        cache_tier=payload.get("cache_tier", "answer"),
        retrieved_at=payload.get("retrieved_at"),
        stale_results=payload.get("stale_results", False),
    )


async def _stream_cached_response(payload: dict[str, Any]):
    meta = {
        "cache_hit": True,
        "cache_tier": payload.get("cache_tier", "answer"),
        "retrieved_at": payload.get("retrieved_at"),
        "stale_results": payload.get("stale_results", False),
    }
    yield format_sse_event("route", {"route": payload["route"]})
    yield format_sse_event("meta", meta)
    for word in payload["response"].split(" "):
        yield format_sse_event("token", {"content": word + " ", "type": "token"})
    if payload.get("sources"):
        yield format_sse_event("sources", {"sources": payload["sources"]})
    yield format_sse_event(
        "done",
        {
            "full_response": payload["response"],
            "cache_hit": True,
            "cache_tier": payload.get("cache_tier", "answer"),
            "retrieved_at": payload.get("retrieved_at"),
            "stale_results": payload.get("stale_results", False),
        },
    )


async def _maybe_write_cache(
    *,
    cache,
    query: str,
    key_ctx: CacheKeyContext,
    result: dict[str, Any],
    policy: str,
    ttl_direct_sec: int,
    ttl_search_results_sec: int,
    ttl_search_answer_sec: int,
):
    if not cache or policy == "critical_market":
        return

    route = result.get("route", "")
    response = result["messages"][-1].content
    sources = _serialize_sources(result.get("sources", []))
    now = datetime.now(UTC).isoformat()

    if route == "direct":
        await cache.set_json(
            direct_answer_cache_key(query, key_ctx),
            {
                "response": response,
                "route": "direct",
                "sources": [],
                "cache_tier": "direct",
                "retrieved_at": now,
            },
            ttl_direct_sec,
        )
        return

    if route == "search" and policy == "search_noncritical":
        await cache.set_json(
            search_results_cache_key(query),
            {"results": _sources_to_results(sources), "retrieved_at": now},
            ttl_search_results_sec,
        )
        await cache.set_json(
            search_answer_cache_key(query, key_ctx),
            {
                "response": response,
                "route": "search",
                "sources": sources,
                "cache_tier": "search_answer",
                "retrieved_at": now,
            },
            ttl_search_answer_sec,
        )


def _serialize_sources(sources: list[Any]) -> list[dict]:
    serialized = []
    for source in sources:
        if isinstance(source, dict):
            serialized.append(source)
        elif hasattr(source, "model_dump"):
            serialized.append(source.model_dump())
    return serialized


def _sources_to_results(sources: list[dict]) -> list[dict]:
    return [
        {
            "title": s.get("title", ""),
            "url": s.get("url", ""),
            "content": s.get("snippet", ""),
        }
        for s in sources
    ]


def _chunk_content(chunk: Any) -> str:
    content = getattr(chunk, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                parts.append(str(block.get("text", block.get("content", ""))))
        return "".join(parts)
    return ""
