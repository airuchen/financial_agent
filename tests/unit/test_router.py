import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agent.nodes import router_node
from app.agent.state import AgentState


def _make_state(query: str) -> AgentState:
    """Create an AgentState with a single user message."""
    from langchain_core.messages import HumanMessage

    return AgentState(
        messages=[HumanMessage(content=query)],
        route="",
        sources=[],
    )


def _mock_llm_response(route: str, reasoning: str) -> MagicMock:
    """Create a mock LLM that returns a route decision JSON."""
    response = MagicMock()
    response.content = json.dumps({"route": route, "reasoning": reasoning})
    llm = AsyncMock()
    llm.ainvoke = AsyncMock(return_value=response)
    return llm


@pytest.mark.asyncio
async def test_router_routes_current_data_to_search():
    """Queries about current data should route to search."""
    llm = _mock_llm_response("search", "Asks for current exchange rate")
    state = _make_state("What is the current EUR/USD exchange rate?")
    result = await router_node(state, llm)
    assert result["route"] == "search"


@pytest.mark.asyncio
async def test_router_routes_greeting_to_direct():
    """Greetings should route to direct response."""
    llm = _mock_llm_response("direct", "This is a greeting")
    state = _make_state("Hello")
    result = await router_node(state, llm)
    assert result["route"] == "direct"
    llm.ainvoke.assert_not_awaited()


@pytest.mark.asyncio
async def test_router_short_circuits_small_talk_to_direct():
    """Small-talk must deterministically route direct without LLM call."""
    llm = _mock_llm_response("search", "ignored")
    state = _make_state("How are you?")
    result = await router_node(state, llm)
    assert result["route"] == "direct"
    llm.ainvoke.assert_not_awaited()


@pytest.mark.asyncio
async def test_router_routes_definition_to_direct():
    """General knowledge questions should route to direct."""
    llm = _mock_llm_response("direct", "Asks for a definition")
    state = _make_state("What is diversification?")
    result = await router_node(state, llm)
    assert result["route"] == "direct"


@pytest.mark.asyncio
async def test_router_routes_regulatory_to_search():
    """Regulatory update queries should route to search."""
    llm = _mock_llm_response("search", "Asks about recent regulatory change")
    state = _make_state("What was the latest Fed decision?")
    result = await router_node(state, llm)
    assert result["route"] == "search"


@pytest.mark.asyncio
async def test_router_handles_malformed_llm_response():
    """Falls back to search when LLM returns invalid JSON."""
    response = MagicMock()
    response.content = "I'm not sure what to do"
    llm = AsyncMock()
    llm.ainvoke = AsyncMock(return_value=response)
    state = _make_state("Current EUR/USD")
    result = await router_node(state, llm)
    assert result["route"] == "search"
