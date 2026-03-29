from langchain_core.language_models import BaseChatModel
from langgraph.graph import END, StateGraph

from app.agent.nodes import (
    direct_response,
    format_response,
    router_node,
    search_agent,
)
from app.agent.state import AgentState


def _route_after_router(state: AgentState) -> str:
    """Conditional edge: route to search_agent or direct_response."""
    return "search_agent" if state["route"] == "search" else "direct_response"


def build_graph(llm: BaseChatModel, search_tool) -> StateGraph:
    """Build and compile the agent LangGraph.

    Args:
        llm: The LLM client for all nodes.
        search_tool: The Tavily search tool instance.

    Returns:
        A compiled LangGraph ready for invocation.
    """
    graph = StateGraph(AgentState)

    # Add nodes with bound dependencies (async wrappers to properly await)
    async def _router(state):
        return await router_node(state, llm)

    async def _search_agent(state):
        return await search_agent(state, llm, search_tool)

    async def _direct_response(state):
        return await direct_response(state, llm)

    graph.add_node("router", _router)
    graph.add_node("search_agent", _search_agent)
    graph.add_node("direct_response", _direct_response)
    graph.add_node("format_response", format_response)

    # Wire edges
    graph.set_entry_point("router")
    graph.add_conditional_edges("router", _route_after_router)
    graph.add_edge("search_agent", "format_response")
    graph.add_edge("direct_response", "format_response")
    graph.add_edge("format_response", END)

    return graph.compile()
