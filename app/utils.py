import json

from app.models import Source


def format_sse_event(event: str, data: dict) -> str:
    """Format a Server-Sent Event string.

    Args:
        event: The SSE event type (e.g., "token", "sources", "done").
        data: The event payload as a dictionary.

    Returns:
        A formatted SSE event string with trailing double newline.
    """
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def extract_sources_from_tavily(results: list[dict]) -> list[Source]:
    """Extract Source objects from Tavily search result dicts.

    Args:
        results: Raw Tavily result dicts with title, url, content keys.

    Returns:
        List of Source objects with title, url, snippet fields.
    """
    return [
        Source(
            title=r.get("title", ""),
            url=r.get("url", ""),
            snippet=r.get("content", ""),
        )
        for r in results
    ]
