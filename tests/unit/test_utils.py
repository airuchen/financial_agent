import json

from app.models import Source
from app.utils import extract_sources_from_tavily, format_sse_event


def test_format_sse_event_token():
    """SSE event formats token with correct event type and JSON data."""
    result = format_sse_event("token", {"content": "Hello", "type": "token"})
    assert result == 'event: token\ndata: {"content": "Hello", "type": "token"}\n\n'


def test_format_sse_event_done():
    """SSE done event includes full response."""
    result = format_sse_event("done", {"full_response": "Complete answer"})
    assert "event: done" in result
    data_line = result.split("\n")[1]
    parsed = json.loads(data_line.replace("data: ", ""))
    assert parsed["full_response"] == "Complete answer"


def test_format_sse_event_sources():
    """SSE sources event formats source list."""
    sources = [{"title": "Reuters", "url": "https://reuters.com", "snippet": "EUR/USD"}]
    result = format_sse_event("sources", {"sources": sources})
    assert "event: sources" in result
    data_line = result.split("\n")[1]
    parsed = json.loads(data_line.replace("data: ", ""))
    assert len(parsed["sources"]) == 1
    assert parsed["sources"][0]["title"] == "Reuters"


def test_extract_sources_from_tavily():
    """Extracts title, url, snippet from Tavily search results."""
    tavily_results = [
        {
            "title": "Reuters",
            "url": "https://reuters.com/article",
            "content": "EUR/USD is 1.08",
            "score": 0.95,
        },
        {
            "title": "Bloomberg",
            "url": "https://bloomberg.com/news",
            "content": "Fed holds rates",
            "score": 0.90,
        },
    ]
    sources = extract_sources_from_tavily(tavily_results)
    assert len(sources) == 2
    assert sources[0] == Source(
        title="Reuters", url="https://reuters.com/article", snippet="EUR/USD is 1.08"
    )
    assert sources[1] == Source(
        title="Bloomberg", url="https://bloomberg.com/news", snippet="Fed holds rates"
    )


def test_extract_sources_from_tavily_empty():
    """Returns empty list when no results."""
    sources = extract_sources_from_tavily([])
    assert sources == []
