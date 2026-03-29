import json
import logging
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, SystemMessage

from app.agent.prompts import (
    DIRECT_RESPONSE_SYSTEM_PROMPT,
    ROUTER_SYSTEM_PROMPT,
    SEARCH_AGENT_SYSTEM_PROMPT,
)
from app.agent.state import AgentState
from app.cache_policy import is_casual_query
from app.utils import extract_sources_from_tavily

logger = logging.getLogger(__name__)


async def router_node(state: AgentState, llm: BaseChatModel) -> dict:
    """Classify user query as 'search' or 'direct'.

    Args:
        state: Current agent state with user message.
        llm: The LLM to use for classification.

    Returns:
        Dict with 'route' key set to 'search' or 'direct'.
    """
    user_query = state["messages"][-1].content
    if is_casual_query(user_query):
        logger.info("Route decision: direct — deterministic casual-intent guard match")
        return {"route": "direct"}

    messages = [SystemMessage(content=ROUTER_SYSTEM_PROMPT)] + state["messages"]
    response = await llm.ainvoke(messages)

    try:
        decision = json.loads(response.content)
        route = decision.get("route", "search")
        if route not in ("search", "direct"):
            route = "search"
        logger.info("Route decision: %s — %s", route, decision.get("reasoning", ""))
    except (json.JSONDecodeError, AttributeError):
        logger.warning("Malformed router response, defaulting to search")
        route = "search"

    return {"route": route}


async def direct_response(state: AgentState, llm: BaseChatModel) -> dict:
    """Generate a direct response without web search.

    Args:
        state: Current agent state with user message.
        llm: The LLM to use for generation.

    Returns:
        Dict with assistant message added to messages.
    """
    messages = [SystemMessage(content=DIRECT_RESPONSE_SYSTEM_PROMPT)] + state[
        "messages"
    ]
    response = await llm.ainvoke(messages)
    return {"messages": [response], "sources": []}


async def search_agent(state: AgentState, llm: BaseChatModel, search_tool) -> dict:
    """Execute web search and synthesize results.

    Uses Tavily to search the web, then asks the LLM to synthesize
    the results into a coherent response with source attribution.

    Args:
        state: Current agent state with user message.
        llm: The LLM to use for synthesis.
        search_tool: A Tavily search tool instance.

    Returns:
        Dict with assistant message and source list.
    """
    user_query = state["messages"][-1].content
    search_results = state.get("cached_search_results")
    if search_results is None:
        search_results = await _invoke_search_tool(search_tool, user_query)

    # Handle both dict and list returns from Tavily
    if isinstance(search_results, dict):
        results_list = search_results.get("results", [])
    elif isinstance(search_results, list):
        results_list = search_results
    else:
        results_list = []

    sources = extract_sources_from_tavily(results_list)

    # Build context from search results
    context_parts = []
    for i, source in enumerate(sources, 1):
        context_parts.append(f"[{i}] {source.title} ({source.url})\n{source.snippet}")
    context = "\n\n".join(context_parts)

    instruction = (
        "Synthesize the above search results to answer the user's question. "
        "Reference sources using [1], [2], etc."
    )
    synthesis_prompt = f"""{SEARCH_AGENT_SYSTEM_PROMPT}

Search results:
{context}

{instruction}"""

    messages = [SystemMessage(content=synthesis_prompt)] + state["messages"]
    response = await llm.ainvoke(messages)
    return {"messages": [response], "sources": sources}


async def _invoke_search_tool(search_tool: Any, user_query: str) -> Any:
    """Call the configured search tool across supported async interfaces.

    Supports both:
    - LangChain-style tools exposing `ainvoke({"query": ...})`
    - Tavily Async client exposing `search(query=...)`
    """
    if hasattr(search_tool, "ainvoke"):
        return await search_tool.ainvoke({"query": user_query})
    if hasattr(search_tool, "search"):
        return await search_tool.search(query=user_query)
    raise TypeError(
        "Unsupported search tool interface. Expected async 'ainvoke' or 'search'."
    )


async def format_response(state: AgentState) -> dict:
    """Normalize response format and append source references.

    For search route: appends a numbered references list.
    For direct route: passes through as-is.

    Args:
        state: Current agent state with response message and sources.

    Returns:
        Dict with formatted message.
    """
    if not state.get("sources"):
        return {}

    last_message = state["messages"][-1]
    references = "\n\n**Sources:**\n"
    for i, source in enumerate(state["sources"], 1):
        references += f"[{i}] [{source.title}]({source.url})\n"

    formatted_content = last_message.content + references
    return {"messages": [AIMessage(content=formatted_content)]}
