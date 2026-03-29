import json
from unittest.mock import AsyncMock

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from pydantic import PrivateAttr

from app.agent.graph import build_graph


class MockStreamingChatModel(BaseChatModel):
    _responses: list[str] = PrivateAttr()
    _stream_chunks: list[str] = PrivateAttr()
    _response_index: int = PrivateAttr(default=0)

    def __init__(
        self,
        *,
        responses: list[str],
        stream_chunks: list[str],
    ):
        super().__init__()
        self._responses = responses
        self._stream_chunks = stream_chunks

    @property
    def _llm_type(self) -> str:
        return "mock-streaming"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        if self._response_index >= len(self._responses):
            raise AssertionError("No mocked response left for _generate()")
        text = self._responses[self._response_index]
        self._response_index += 1
        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content=text))]
        )

    async def _astream(self, messages, stop=None, **kwargs):
        for content in self._stream_chunks:
            yield ChatGenerationChunk(message=AIMessageChunk(content=content))


def _mock_search_tool(results: list[dict]) -> AsyncMock:
    """Create a mock Tavily search tool."""
    tool = AsyncMock()
    tool.ainvoke = AsyncMock(return_value={"results": results})
    return tool


@pytest.mark.asyncio
async def test_graph_search_path():
    """Search route produces a sourced final answer."""
    router_response = json.dumps(
        {"route": "search", "reasoning": "Asks for current data"}
    )
    llm = MockStreamingChatModel(
        responses=[router_response],
        stream_chunks=["The EUR/USD rate is 1.08 [1]."],
    )

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
    llm = MockStreamingChatModel(
        responses=[router_response],
        stream_chunks=[direct_answer],
    )

    search_tool = _mock_search_tool([])

    graph = build_graph(llm, search_tool)
    result = await graph.ainvoke(
        {"messages": [("human", "Hello")], "route": "", "sources": []}
    )

    final_message = result["messages"][-1].content
    assert "Hello" in final_message
    assert "Sources:" not in final_message
    assert result["sources"] == []
