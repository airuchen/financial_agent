from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages

from app.models import Source


class AgentState(TypedDict):
    """State passed between LangGraph nodes.

    Attributes:
        messages: Conversation message history, managed by LangGraph.
        route: Routing decision — "search" or "direct".
        sources: Source references extracted from search results.
    """

    messages: Annotated[list, add_messages]
    route: str
    sources: list[Source]
