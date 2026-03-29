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


def _mock_llm_response(intent: str, reasoning: str) -> MagicMock:
    """Create a mock LLM that returns an intent decision JSON."""
    response = MagicMock()
    response.content = json.dumps({"intent": intent, "reasoning": reasoning})
    llm = AsyncMock()
    llm.ainvoke = AsyncMock(return_value=response)
    return llm


@pytest.mark.asyncio
async def test_router_routes_current_data_to_search():
    """Queries about current data should route to search."""
    llm = _mock_llm_response("casual", "ignored because deterministic veto")
    state = _make_state("What is the current EUR/USD exchange rate?")
    result = await router_node(state, llm)
    assert result["route"] == "search"
    llm.ainvoke.assert_not_awaited()


@pytest.mark.asyncio
async def test_router_routes_greeting_to_direct():
    """Greetings should route direct via classifier intent."""
    llm = _mock_llm_response("casual", "This is a greeting")
    state = _make_state("Hello")
    result = await router_node(state, llm)
    assert result["route"] == "direct"


@pytest.mark.asyncio
async def test_router_mixed_greeting_and_price_routes_search():
    """Mixed greeting + time-critical finance must route to search."""
    llm = _mock_llm_response("casual", "ignored")
    state = _make_state("hi, could you tell me the current stock price?")
    result = await router_node(state, llm)
    assert result["route"] == "search"
    llm.ainvoke.assert_not_awaited()


@pytest.mark.asyncio
async def test_router_routes_definition_to_direct():
    """General knowledge questions should route to direct."""
    llm = _mock_llm_response("direct_finance", "Asks for a definition")
    state = _make_state("What is diversification?")
    result = await router_node(state, llm)
    assert result["route"] == "direct"


@pytest.mark.asyncio
async def test_router_routes_regulatory_to_search():
    """Regulatory update queries should route to search."""
    llm = _mock_llm_response("search_finance", "Asks about recent regulatory change")
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


@pytest.mark.asyncio
async def test_router_handles_unknown_intent_with_search_fallback():
    """Unknown intents should fallback to search for safety."""
    response = MagicMock()
    response.content = json.dumps({"intent": "unknown", "reasoning": "n/a"})
    llm = AsyncMock()
    llm.ainvoke = AsyncMock(return_value=response)
    state = _make_state("Explain diversification")
    result = await router_node(state, llm)
    assert result["route"] == "search"
