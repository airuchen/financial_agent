from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.agent.nodes import search_agent


@pytest.mark.asyncio
async def test_search_agent_supports_search_method():
    """search_agent should work with Tavily Async client-style `search` method."""

    class SearchOnlyTool:
        async def search(self, query: str):
            assert query == "latest eurusd"
            return {
                "results": [
                    {
                        "title": "Reuters",
                        "url": "https://reuters.com",
                        "content": "EUR/USD at 1.08",
                    }
                ]
            }

    llm = AsyncMock()
    llm.ainvoke = AsyncMock(return_value=AIMessage(content="EUR/USD is 1.08 [1]."))
    state = {
        "messages": [HumanMessage(content="latest eurusd")],
        "route": "search",
        "sources": [],
    }

    result = await search_agent(state, llm, SearchOnlyTool())
    assert "messages" in result
    assert len(result["sources"]) == 1
    assert result["sources"][0].title == "Reuters"


@pytest.mark.asyncio
async def test_search_agent_returns_uncertainty_on_no_hits():
    """search_agent should emit a clear fallback when no search results are found."""

    class EmptySearchTool:
        async def search(self, query: str):
            assert query == "latest eurusd"
            return {"results": []}

    llm = AsyncMock()
    llm.ainvoke = AsyncMock(return_value=AIMessage(content="unused"))
    state = {
        "messages": [HumanMessage(content="latest eurusd")],
        "route": "search",
        "sources": [],
    }

    result = await search_agent(state, llm, EmptySearchTool())
    assert result["sources"] == []
    assert "couldn't find any current web results" in result["messages"][-1].content
    llm.ainvoke.assert_not_awaited()


@pytest.mark.asyncio
async def test_search_agent_retries_tavily_then_succeeds(monkeypatch):
    """search_agent should retry transient Tavily failures with backoff."""

    class FlakySearchTool:
        def __init__(self):
            self.calls = 0

        async def ainvoke(self, payload: dict):
            assert payload == {"query": "latest eurusd"}
            self.calls += 1
            if self.calls == 1:
                raise TimeoutError("search timed out")
            return {
                "results": [
                    {
                        "title": "Reuters",
                        "url": "https://reuters.com",
                        "content": "EUR/USD at 1.08",
                    }
                ]
            }

    sleep = AsyncMock()
    monkeypatch.setattr("app.agent.resilience.asyncio.sleep", sleep)

    llm = AsyncMock()
    llm.ainvoke = AsyncMock(return_value=AIMessage(content="EUR/USD is 1.08 [1]."))
    state = {
        "messages": [HumanMessage(content="latest eurusd")],
        "route": "search",
        "sources": [],
    }

    tool = FlakySearchTool()
    result = await search_agent(state, llm, tool)
    assert len(result["sources"]) == 1
    assert tool.calls == 2
    assert sleep.await_count == 1


@pytest.mark.asyncio
async def test_search_agent_retries_llm_then_succeeds(monkeypatch):
    """search_agent should retry transient LLM synthesis failures with backoff."""

    class StableSearchTool:
        async def search(self, query: str):
            assert query == "latest eurusd"
            return {
                "results": [
                    {
                        "title": "Reuters",
                        "url": "https://reuters.com",
                        "content": "EUR/USD at 1.08",
                    }
                ]
            }

    sleep = AsyncMock()
    monkeypatch.setattr("app.agent.resilience.asyncio.sleep", sleep)

    llm = AsyncMock()
    llm.ainvoke = AsyncMock(
        side_effect=[
            TimeoutError("llm timed out"),
            AIMessage(content="EUR/USD is 1.08 [1]."),
        ]
    )
    state = {
        "messages": [HumanMessage(content="latest eurusd")],
        "route": "search",
        "sources": [],
    }

    result = await search_agent(state, llm, StableSearchTool())
    assert len(result["sources"]) == 1
    assert llm.ainvoke.await_count == 2
    assert sleep.await_count == 1


@pytest.mark.asyncio
async def test_search_agent_raises_on_invalid_tool_interface():
    """search_agent should fail fast for unsupported tool contracts."""
    llm = AsyncMock()
    llm.ainvoke = AsyncMock(return_value=AIMessage(content="n/a"))
    state = {
        "messages": [HumanMessage(content="latest eurusd")],
        "route": "search",
        "sources": [],
    }

    with pytest.raises(TypeError, match="Unsupported search tool interface"):
        await search_agent(state, llm, object())
