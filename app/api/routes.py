import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

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

    try:
        if body.stream:
            return StreamingResponse(
                _stream_response(graph, body.query),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )
        else:
            result = await graph.ainvoke(
                {"messages": [("human", body.query)], "route": "", "sources": []}
            )
            final_message = result["messages"][-1].content
            sources = [
                Source(**s) if isinstance(s, dict) else s
                for s in result.get("sources", [])
            ]
            return QueryResponse(
                response=final_message,
                route=result.get("route", ""),
                sources=sources,
            )
    except TimeoutError:
        raise HTTPException(status_code=504, detail="Request timed out") from None
    except Exception:
        logger.exception("Unexpected error processing query")
        raise HTTPException(status_code=500, detail="Internal server error") from None


async def _stream_response(graph, query: str):
    """Generate SSE events from the agent graph.

    Args:
        graph: The compiled LangGraph.
        query: The user's query string.

    Yields:
        Formatted SSE event strings.
    """
    result = await graph.ainvoke(
        {"messages": [("human", query)], "route": "", "sources": []}
    )

    route = result.get("route", "")
    yield format_sse_event("route", {"route": route})

    final_message = result["messages"][-1].content
    # Emit tokens (word-level chunking for SSE)
    for word in final_message.split(" "):
        yield format_sse_event("token", {"content": word + " ", "type": "token"})

    if result.get("sources"):
        sources_data = [
            s.model_dump() if hasattr(s, "model_dump") else s
            for s in result["sources"]
        ]
        yield format_sse_event("sources", {"sources": sources_data})

    yield format_sse_event("done", {"full_response": final_message})


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
