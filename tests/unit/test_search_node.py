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
