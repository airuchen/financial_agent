import json
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage

from app.agent.graph import build_graph


def _mock_llm(responses: list[str]) -> AsyncMock:
    """Create a mock LLM that returns a sequence of AIMessage responses."""
    llm = AsyncMock()
    side_effects = [AIMessage(content=text) for text in responses]
    llm.ainvoke = AsyncMock(side_effect=side_effects)
    return llm


def _mock_search_tool(results: list[dict]) -> AsyncMock:
    """Create a mock Tavily search tool."""
    tool = AsyncMock()
    tool.ainvoke = AsyncMock(return_value={"results": results})
    return tool


@pytest.mark.asyncio
async def test_graph_search_path():
    """Search route: router -> search_agent -> format_response produces sourced answer."""
    router_response = json.dumps(
        {"route": "search", "reasoning": "Asks for current data"}
    )
    agent_response = "The EUR/USD rate is 1.08 [1]."
    llm = _mock_llm([router_response, agent_response])

    search_results = [
        {
            "title": "Reuters",
            "url": "https://reuters.com",
            "content": "EUR/USD at 1.08",
            "score": 0.95,
        },
    ]
    search_tool = _mock_search_tool(search_results)

    graph = build_graph(llm, search_tool)
    result = await graph.ainvoke(
        {"messages": [("human", "Current EUR/USD rate")], "route": "", "sources": []}
    )

    final_message = result["messages"][-1].content
    assert "EUR/USD" in final_message
    assert "Sources:" in final_message
    assert "Reuters" in final_message
    assert len(result["sources"]) == 1


@pytest.mark.asyncio
async def test_graph_direct_path():
    """Direct route: router -> direct_response -> format_response with no sources."""
    router_response = json.dumps({"route": "direct", "reasoning": "Greeting"})
    direct_answer = "Hello! How can I help with your financial research?"
    llm = _mock_llm([router_response, direct_answer])

    search_tool = _mock_search_tool([])

    graph = build_graph(llm, search_tool)
    result = await graph.ainvoke(
        {"messages": [("human", "Hello")], "route": "", "sources": []}
    )

    final_message = result["messages"][-1].content
    assert "Hello" in final_message
    assert "Sources:" not in final_message
    assert result["sources"] == []
