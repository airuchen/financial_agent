# Internet-Search Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an LLM-powered financial research agent with explicit query routing, exposed via FastAPI REST API with SSE streaming.

**Architecture:** LangGraph graph with 4 nodes (router → search_agent|direct_response → format_response). LLM provider is pluggable (Ollama/OpenAI) via factory. FastAPI serves POST /query (SSE + JSON) and GET /health.

**Tech Stack:** Python 3.12, uv, LangGraph, LangChain, FastAPI, Tavily, Ollama/OpenAI, pytest, ruff, Docker, GitHub Actions

---

## File Map

| File | Responsibility |
|------|---------------|
| `pyproject.toml` | Dependencies, ruff config, semantic-release config |
| `.pre-commit-config.yaml` | Pre-commit hooks (ruff format, ruff check) |
| `.env.example` | Template for environment variables |
| `app/__init__.py` | Package marker |
| `app/config.py` | Pydantic Settings — all env vars, defaults, validation |
| `app/llm.py` | LLM factory — returns ChatOllama or ChatOpenAI |
| `app/models.py` | Pydantic schemas — QueryRequest, QueryResponse, RouteDecision |
| `app/utils.py` | SSE event formatting, source extraction helpers |
| `app/agent/state.py` | AgentState TypedDict |
| `app/agent/prompts.py` | System prompts for router and agent |
| `app/agent/nodes.py` | Graph node functions — router, search_agent, direct_response, format_response |
| `app/agent/graph.py` | LangGraph graph assembly — wires nodes + conditional edges |
| `app/api/routes.py` | FastAPI router — POST /query, GET /health |
| `app/main.py` | FastAPI app creation, lifespan, CORS, router inclusion |
| `tests/conftest.py` | Shared fixtures |
| `tests/unit/test_utils.py` | Tests for SSE formatting, source extraction |
| `tests/unit/test_router.py` | Tests for routing classification |
| `tests/unit/test_llm.py` | Tests for LLM factory |
| `tests/acceptance/test_agent.py` | Full graph flow with mocked LLM + search |
| `tests/e2e/test_api_container.py` | HTTP tests against running container |
| `Dockerfile` | Multi-stage build for the API service |
| `docker-compose.yml` | API + Ollama (optional profile) |
| `.github/workflows/ci.yml` | PR pipeline: lint → test → build → e2e |
| `.github/workflows/release.yml` | Merge pipeline: version → retag → docs |
| `docs/adr/template.md` | ADR template |
| `docs/adr/001-langgraph-explicit-router.md` | ADR for router approach |
| `docs/adr/002-ollama-openai-abstraction.md` | ADR for LLM abstraction |
| `docs/adr/003-tavily-search-tool.md` | ADR for Tavily choice |
| `docs/api.md` | REST API documentation |
| `docs/deployment.md` | Deployment architecture diagram + narrative |
| `docs/configuration.md` | Environment variable reference |
| `docs/Doxyfile` | Doxygen config for Python |
| `README.md` | Project overview, quickstart, how to run |

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `.pre-commit-config.yaml`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `app/__init__.py`
- Create: `app/agent/__init__.py`
- Create: `app/api/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/unit/__init__.py`
- Create: `tests/acceptance/__init__.py`
- Create: `tests/e2e/__init__.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "scalable-search-agent"
version = "0.1.0"
description = "LLM-powered Internet-Search Agent for financial research"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
    "langchain>=0.3.0",
    "langchain-community>=0.3.0",
    "langchain-openai>=0.3.0",
    "langgraph>=0.2.0",
    "langchain-ollama>=0.2.0",
    "tavily-python>=0.5.0",
    "pydantic-settings>=2.7.0",
    "sse-starlette>=2.2.0",
    "httpx>=0.28.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "ruff>=0.8.0",
    "pre-commit>=4.0.0",
    "python-semantic-release>=9.0.0",
]

[tool.ruff]
target-version = "py312"
line-length = 88

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "SIM", "RUF"]

[tool.ruff.format]
quote-style = "double"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.semantic_release]
version_variable = "pyproject.toml:version"
branch = "main"
commit_message = "chore(release): {version}"
build_command = ""

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

- [ ] **Step 2: Create .pre-commit-config.yaml**

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.6
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

- [ ] **Step 3: Create .env.example**

```bash
# LLM Provider: "ollama" or "openai"
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5:7b

# Ollama (only if LLM_PROVIDER=ollama)
OLLAMA_BASE_URL=http://localhost:11434

# OpenAI (only if LLM_PROVIDER=openai)
OPENAI_API_KEY=sk-your-key-here

# Tavily
TAVILY_API_KEY=tvly-your-key-here

# API
API_HOST=0.0.0.0
API_PORT=8000
LLM_TIMEOUT=30
```

- [ ] **Step 4: Create .gitignore**

```text
__pycache__/
*.py[cod]
.env
.venv/
*.egg-info/
dist/
build/
.ruff_cache/
.pytest_cache/
.superpowers/
docs/doxygen_output/
```

- [ ] **Step 5: Create package __init__.py files**

Create empty `__init__.py` in: `app/`, `app/agent/`, `app/api/`, `tests/`, `tests/unit/`, `tests/acceptance/`, `tests/e2e/`

- [ ] **Step 6: Install dependencies and set up pre-commit**

Run: `uv sync --all-extras`
Expected: Lock file created, dependencies installed

Run: `uv run pre-commit install`
Expected: "pre-commit installed at .git/hooks/pre-commit"

- [ ] **Step 7: Verify ruff works**

Run: `uv run ruff check .`
Expected: No errors (empty project)

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml uv.lock .pre-commit-config.yaml .env.example .gitignore app/ tests/
git commit -m "chore: scaffold project with uv, ruff, pre-commit"
```

---

### Task 2: Config and LLM Factory

**Files:**
- Create: `app/config.py`
- Create: `app/llm.py`
- Create: `tests/unit/test_llm.py`

- [ ] **Step 1: Write failing tests for config and LLM factory**

```python
# tests/unit/test_llm.py
from unittest.mock import patch

import pytest

from app.config import Settings
from app.llm import create_llm


def test_create_llm_ollama():
    """Factory returns ChatOllama when provider is ollama."""
    settings = Settings(
        llm_provider="ollama",
        llm_model="qwen2.5:7b",
        ollama_base_url="http://localhost:11434",
        tavily_api_key="tvly-test",
    )
    llm = create_llm(settings)
    from langchain_ollama import ChatOllama

    assert isinstance(llm, ChatOllama)


def test_create_llm_openai():
    """Factory returns ChatOpenAI when provider is openai."""
    settings = Settings(
        llm_provider="openai",
        llm_model="gpt-4o-mini",
        openai_api_key="sk-test",
        tavily_api_key="tvly-test",
    )
    llm = create_llm(settings)
    from langchain_openai import ChatOpenAI

    assert isinstance(llm, ChatOpenAI)


def test_create_llm_invalid_provider():
    """Factory raises ValueError for unknown provider."""
    settings = Settings(
        llm_provider="invalid",
        llm_model="some-model",
        tavily_api_key="tvly-test",
    )
    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        create_llm(settings)


def test_settings_defaults():
    """Settings loads defaults correctly."""
    with patch.dict(
        "os.environ",
        {"TAVILY_API_KEY": "tvly-test"},
        clear=False,
    ):
        settings = Settings()
        assert settings.llm_provider == "ollama"
        assert settings.llm_model == "qwen2.5:7b"
        assert settings.llm_timeout == 30
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_llm.py -v`
Expected: FAIL — ModuleNotFoundError for `app.config`

- [ ] **Step 3: Implement config.py**

```python
# app/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # LLM
    llm_provider: str = "ollama"
    llm_model: str = "qwen2.5:7b"
    llm_timeout: int = 30

    # Ollama
    ollama_base_url: str = "http://localhost:11434"

    # OpenAI
    openai_api_key: str = ""

    # Tavily
    tavily_api_key: str = ""

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
```

- [ ] **Step 4: Implement llm.py**

```python
# app/llm.py
from langchain_core.language_models import BaseChatModel

from app.config import Settings


def create_llm(settings: Settings) -> BaseChatModel:
    """Create an LLM client based on the configured provider.

    Args:
        settings: Application settings with provider and model config.

    Returns:
        A LangChain chat model instance.

    Raises:
        ValueError: If the provider is not supported.
    """
    if settings.llm_provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=settings.llm_model,
            base_url=settings.ollama_base_url,
            timeout=settings.llm_timeout,
        )
    elif settings.llm_provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.openai_api_key,
            timeout=settings.llm_timeout,
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_llm.py -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add app/config.py app/llm.py tests/unit/test_llm.py
git commit -m "feat: add config settings and pluggable LLM factory"
```

---

### Task 3: Pydantic Models and Utilities

**Files:**
- Create: `app/models.py`
- Create: `app/utils.py`
- Create: `tests/unit/test_utils.py`

- [ ] **Step 1: Write failing tests for utils**

```python
# tests/unit/test_utils.py
import json

from app.models import RouteDecision, Source
from app.utils import format_sse_event, extract_sources_from_tavily


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
        {"title": "Reuters", "url": "https://reuters.com/article", "content": "EUR/USD is 1.08", "score": 0.95},
        {"title": "Bloomberg", "url": "https://bloomberg.com/news", "content": "Fed holds rates", "score": 0.90},
    ]
    sources = extract_sources_from_tavily(tavily_results)
    assert len(sources) == 2
    assert sources[0] == Source(title="Reuters", url="https://reuters.com/article", snippet="EUR/USD is 1.08")
    assert sources[1] == Source(title="Bloomberg", url="https://bloomberg.com/news", snippet="Fed holds rates")


def test_extract_sources_from_tavily_empty():
    """Returns empty list when no results."""
    sources = extract_sources_from_tavily([])
    assert sources == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_utils.py -v`
Expected: FAIL — ModuleNotFoundError for `app.models`

- [ ] **Step 3: Implement models.py**

```python
# app/models.py
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Request body for POST /query."""

    query: str = Field(..., min_length=1, description="The user's research query")
    stream: bool = Field(default=True, description="Whether to stream the response via SSE")


class Source(BaseModel):
    """A source reference from web search results."""

    title: str
    url: str
    snippet: str


class QueryResponse(BaseModel):
    """JSON response body for POST /query when stream=false."""

    response: str
    route: str
    sources: list[Source] = Field(default_factory=list)


class RouteDecision(BaseModel):
    """Structured output from the router node."""

    route: str = Field(..., description="Either 'search' or 'direct'")
    reasoning: str = Field(..., description="Why this route was chosen")
```

- [ ] **Step 4: Implement utils.py**

```python
# app/utils.py
import json

from app.models import Source


def format_sse_event(event: str, data: dict) -> str:
    """Format a Server-Sent Event string.

    Args:
        event: The SSE event type (e.g., "token", "sources", "done").
        data: The event payload as a dictionary.

    Returns:
        A formatted SSE event string with trailing double newline.
    """
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def extract_sources_from_tavily(results: list[dict]) -> list[Source]:
    """Extract Source objects from Tavily search result dicts.

    Args:
        results: Raw Tavily result dicts with title, url, content keys.

    Returns:
        List of Source objects with title, url, snippet fields.
    """
    return [
        Source(
            title=r.get("title", ""),
            url=r.get("url", ""),
            snippet=r.get("content", ""),
        )
        for r in results
    ]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_utils.py -v`
Expected: 5 passed

- [ ] **Step 6: Commit**

```bash
git add app/models.py app/utils.py tests/unit/test_utils.py
git commit -m "feat: add Pydantic models and SSE/source utility helpers"
```

---

### Task 4: Agent Prompts and State

**Files:**
- Create: `app/agent/state.py`
- Create: `app/agent/prompts.py`

- [ ] **Step 1: Implement state.py**

```python
# app/agent/state.py
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
```

- [ ] **Step 2: Implement prompts.py**

```python
# app/agent/prompts.py

ROUTER_SYSTEM_PROMPT = """You are a query router for a financial research assistant.

Classify the user's query into one of two routes:

**"search"** — Use when the query asks about:
- Current or recent market data (prices, rates, indices)
- Recent news, events, or regulatory changes
- Specific company earnings, filings, or announcements
- Economic indicators with a temporal component (latest GDP, current inflation)
- Any information that changes over time and requires up-to-date data

**"direct"** — Use when the query asks about:
- Greetings or casual conversation ("Hello", "How are you?")
- General financial concepts or definitions ("What is diversification?", "Explain P/E ratio")
- Mathematical calculations or formulas
- Static knowledge that doesn't change frequently
- Requests for explanations of well-established theories

Respond with ONLY a JSON object in this exact format:
{{"route": "search" or "direct", "reasoning": "brief explanation of why"}}
"""

SEARCH_AGENT_SYSTEM_PROMPT = """You are a financial research assistant with access to web search.

Your role is to help investment professionals research market data, regulatory updates, and economic indicators.

When answering:
1. Use the search tool to find current, accurate information
2. Synthesize information from multiple sources when possible
3. Present findings in a clear, professional format
4. Always attribute information to its source
5. If search results are insufficient, state what you found and what remains uncertain

Focus on accuracy over completeness. It is better to say "I found X but could not confirm Y" than to speculate.
"""

DIRECT_RESPONSE_SYSTEM_PROMPT = """You are a financial research assistant.

Answer the user's question directly from your knowledge. Be concise, accurate, and professional.

If the question is a greeting, respond warmly but briefly.
If the question is about financial concepts, provide a clear explanation suitable for investment professionals.
"""
```

- [ ] **Step 3: Commit**

```bash
git add app/agent/state.py app/agent/prompts.py
git commit -m "feat: add agent state schema and system prompts"
```

---

### Task 5: Router Node

**Files:**
- Create: `app/agent/nodes.py`
- Create: `tests/unit/test_router.py`

- [ ] **Step 1: Write failing tests for the router node**

```python
# tests/unit/test_router.py
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agent.nodes import router_node
from app.agent.state import AgentState
from app.models import RouteDecision


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_router.py -v`
Expected: FAIL — ImportError for `app.agent.nodes`

- [ ] **Step 3: Implement router_node in nodes.py**

```python
# app/agent/nodes.py
import json
import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage

from app.agent.prompts import (
    DIRECT_RESPONSE_SYSTEM_PROMPT,
    ROUTER_SYSTEM_PROMPT,
    SEARCH_AGENT_SYSTEM_PROMPT,
)
from app.agent.state import AgentState

logger = logging.getLogger(__name__)


async def router_node(state: AgentState, llm: BaseChatModel) -> dict:
    """Classify user query as 'search' or 'direct'.

    Args:
        state: Current agent state with user message.
        llm: The LLM to use for classification.

    Returns:
        Dict with 'route' key set to 'search' or 'direct'.
    """
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_router.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add app/agent/nodes.py tests/unit/test_router.py
git commit -m "feat: implement router node with search/direct classification"
```

---

### Task 6: Direct Response and Search Agent Nodes

**Files:**
- Modify: `app/agent/nodes.py`

- [ ] **Step 1: Add direct_response node to nodes.py**

Append to `app/agent/nodes.py`:

```python
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
```

- [ ] **Step 2: Add search_agent node to nodes.py**

Append to `app/agent/nodes.py`:

```python
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
    from app.utils import extract_sources_from_tavily

    user_query = state["messages"][-1].content
    search_results = await search_tool.ainvoke({"query": user_query})

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

    synthesis_prompt = f"""{SEARCH_AGENT_SYSTEM_PROMPT}

Search results:
{context}

Synthesize the above search results to answer the user's question. Reference sources using [1], [2], etc."""

    messages = [SystemMessage(content=synthesis_prompt)] + state["messages"]
    response = await llm.ainvoke(messages)
    return {"messages": [response], "sources": sources}
```

- [ ] **Step 3: Add format_response node to nodes.py**

Append to `app/agent/nodes.py`:

```python
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

    from langchain_core.messages import AIMessage

    last_message = state["messages"][-1]
    references = "\n\n**Sources:**\n"
    for i, source in enumerate(state["sources"], 1):
        references += f"[{i}] [{source.title}]({source.url})\n"

    formatted_content = last_message.content + references
    return {"messages": [AIMessage(content=formatted_content)]}
```

- [ ] **Step 4: Run all unit tests**

Run: `uv run pytest tests/unit/ -v`
Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
git add app/agent/nodes.py
git commit -m "feat: add direct_response, search_agent, and format_response nodes"
```

---

### Task 7: LangGraph Graph Assembly

**Files:**
- Create: `app/agent/graph.py`
- Create: `tests/acceptance/test_agent.py`

- [ ] **Step 1: Write failing acceptance tests**

```python
# tests/acceptance/test_agent.py
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agent.graph import build_graph


def _mock_llm(responses: list[str]) -> AsyncMock:
    """Create a mock LLM that returns a sequence of responses."""
    llm = AsyncMock()
    side_effects = []
    for text in responses:
        msg = MagicMock()
        msg.content = text
        side_effects.append(msg)
    llm.ainvoke = AsyncMock(side_effect=side_effects)
    return llm


def _mock_search_tool(results: list[dict]) -> AsyncMock:
    """Create a mock Tavily search tool."""
    tool = AsyncMock()
    tool.ainvoke = AsyncMock(return_value={"results": results})
    return tool


@pytest.mark.asyncio
async def test_graph_search_path():
    """Search route: router → search_agent → format_response produces sourced answer."""
    router_response = json.dumps({"route": "search", "reasoning": "Asks for current data"})
    agent_response = "The EUR/USD rate is 1.08 [1]."
    llm = _mock_llm([router_response, agent_response])

    search_results = [
        {"title": "Reuters", "url": "https://reuters.com", "content": "EUR/USD at 1.08", "score": 0.95},
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
    """Direct route: router → direct_response → format_response with no sources."""
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/acceptance/test_agent.py -v`
Expected: FAIL — ImportError for `app.agent.graph`

- [ ] **Step 3: Implement graph.py**

```python
# app/agent/graph.py
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

    # Add nodes with bound dependencies
    graph.add_node("router", lambda state: router_node(state, llm))
    graph.add_node("search_agent", lambda state: search_agent(state, llm, search_tool))
    graph.add_node("direct_response", lambda state: direct_response(state, llm))
    graph.add_node("format_response", format_response)

    # Wire edges
    graph.set_entry_point("router")
    graph.add_conditional_edges("router", _route_after_router)
    graph.add_edge("search_agent", "format_response")
    graph.add_edge("direct_response", "format_response")
    graph.add_edge("format_response", END)

    return graph.compile()
```

- [ ] **Step 4: Run acceptance tests**

Run: `uv run pytest tests/acceptance/test_agent.py -v`
Expected: 2 passed

- [ ] **Step 5: Run all tests**

Run: `uv run pytest tests/unit/ tests/acceptance/ -v`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add app/agent/graph.py tests/acceptance/test_agent.py
git commit -m "feat: assemble LangGraph with router, search, direct, and format nodes"
```

---

### Task 8: FastAPI Application and Routes

**Files:**
- Create: `app/api/routes.py`
- Create: `app/main.py`
- Create: `tests/conftest.py`
- Create: `tests/unit/test_api.py`

- [ ] **Step 1: Write failing API tests**

```python
# tests/unit/test_api.py
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture
def mock_graph():
    """Create a mock compiled graph."""
    graph = AsyncMock()
    msg = MagicMock()
    msg.content = "The EUR/USD rate is 1.08."
    graph.ainvoke = AsyncMock(
        return_value={
            "messages": [MagicMock(), msg],  # HumanMessage + AIMessage
            "route": "search",
            "sources": [
                {"title": "Reuters", "url": "https://reuters.com", "snippet": "EUR/USD at 1.08"},
            ],
        }
    )
    return graph


@pytest.fixture
def app(mock_graph):
    """Create a test FastAPI app with mocked graph."""
    application = create_app()
    application.state.graph = mock_graph
    return application


@pytest.mark.asyncio
async def test_query_json_response(app, mock_graph):
    """POST /query with stream=false returns JSON response."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/query",
            json={"query": "Current EUR/USD rate", "stream": False},
        )
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert data["route"] == "search"
    assert len(data["sources"]) == 1


@pytest.mark.asyncio
async def test_query_missing_query(app):
    """POST /query with empty query returns 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/query", json={"query": ""})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_health_endpoint(app):
    """GET /health returns status."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_api.py -v`
Expected: FAIL — ImportError for `app.main`

- [ ] **Step 3: Implement routes.py**

```python
# app/api/routes.py
import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.models import QueryRequest, QueryResponse, Source
from app.utils import format_sse_event

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/query")
async def query(request: Request, body: QueryRequest):
    """Handle a financial research query.

    Routes the query through the agent graph and returns
    either a streaming SSE response or a JSON response.

    Args:
        request: The FastAPI request (for accessing app state).
        body: The validated query request body.

    Returns:
        StreamingResponse for SSE or QueryResponse for JSON.
    """
    graph = request.app.state.graph

    try:
        if body.stream:
            return StreamingResponse(
                _stream_response(graph, body.query),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )
        else:
            result = await graph.ainvoke(
                {"messages": [("human", body.query)], "route": "", "sources": []}
            )
            final_message = result["messages"][-1].content
            sources = [
                Source(**s) if isinstance(s, dict) else s
                for s in result.get("sources", [])
            ]
            return QueryResponse(
                response=final_message,
                route=result.get("route", ""),
                sources=sources,
            )
    except TimeoutError:
        raise HTTPException(status_code=504, detail="Request timed out")
    except Exception:
        logger.exception("Unexpected error processing query")
        raise HTTPException(status_code=500, detail="Internal server error")


async def _stream_response(graph, query: str):
    """Generate SSE events from the agent graph.

    Args:
        graph: The compiled LangGraph.
        query: The user's query string.

    Yields:
        Formatted SSE event strings.
    """
    result = await graph.ainvoke(
        {"messages": [("human", query)], "route": "", "sources": []}
    )

    route = result.get("route", "")
    yield format_sse_event("route", {"route": route})

    final_message = result["messages"][-1].content
    # Emit tokens (word-level chunking for SSE)
    for word in final_message.split(" "):
        yield format_sse_event("token", {"content": word + " ", "type": "token"})

    if result.get("sources"):
        sources_data = [
            s.model_dump() if hasattr(s, "model_dump") else s
            for s in result["sources"]
        ]
        yield format_sse_event("sources", {"sources": sources_data})

    yield format_sse_event("done", {"full_response": final_message})


@router.get("/health")
async def health(request: Request):
    """Health check endpoint.

    Returns:
        JSON with status and provider info.
    """
    return {
        "status": "ok",
        "provider": getattr(request.app.state, "provider", "unknown"),
    }
```

- [ ] **Step 4: Implement main.py**

```python
# app/main.py
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import Settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the agent graph on startup.

    Creates the LLM client, search tool, and compiled graph,
    storing them on app.state for route handlers to access.
    """
    settings = Settings()

    from app.llm import create_llm

    llm = create_llm(settings)

    from tavily import AsyncTavilyClient

    tavily_client = AsyncTavilyClient(api_key=settings.tavily_api_key)

    from app.agent.graph import build_graph

    app.state.graph = build_graph(llm, tavily_client)
    app.state.provider = settings.llm_provider

    logger.info(
        "Agent ready — provider=%s, model=%s",
        settings.llm_provider,
        settings.llm_model,
    )
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI app with CORS and routes.
    """
    app = FastAPI(
        title="Financial Research Agent API",
        description="LLM-powered Internet-Search Agent for financial research",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)
    return app


app = create_app()
```

Note: The module-level `app` does **not** use `lifespan` — this is intentional so tests can inject mocks via `app.state.graph`. The production entrypoint wires lifespan separately (see Task 10 docker-compose).

- [ ] **Step 5: Run API tests**

Run: `uv run pytest tests/unit/test_api.py -v`
Expected: 3 passed

- [ ] **Step 6: Run full test suite**

Run: `uv run pytest tests/unit/ tests/acceptance/ -v`
Expected: All tests pass

- [ ] **Step 7: Commit**

```bash
git add app/api/routes.py app/main.py tests/unit/test_api.py tests/conftest.py
git commit -m "feat: add FastAPI routes (POST /query, GET /health) with SSE streaming"
```

---

### Task 9: Wire Lifespan for Production

**Files:**
- Modify: `app/main.py`

- [ ] **Step 1: Update main.py to use lifespan in production app**

The `create_app` function needs a parameter to optionally include lifespan:

Replace the bottom of `app/main.py`:

```python
def create_app(use_lifespan: bool = False) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        use_lifespan: If True, attach the lifespan handler that initializes
            the real LLM and search tool. False for testing.

    Returns:
        Configured FastAPI app with CORS and routes.
    """
    app = FastAPI(
        title="Financial Research Agent API",
        description="LLM-powered Internet-Search Agent for financial research",
        version="0.1.0",
        lifespan=lifespan if use_lifespan else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)
    return app


app = create_app(use_lifespan=True)
```

- [ ] **Step 2: Verify existing tests still pass**

Run: `uv run pytest tests/unit/test_api.py -v`
Expected: All pass (tests use `create_app()` which defaults to `use_lifespan=False`)

- [ ] **Step 3: Commit**

```bash
git add app/main.py
git commit -m "feat: wire lifespan for production startup with LLM and search tool init"
```

---

### Task 10: Docker and Docker Compose

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`

- [ ] **Step 1: Create Dockerfile**

```dockerfile
# Dockerfile
FROM python:3.12-slim AS base

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install dependencies (cached layer)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy application code
COPY app/ app/

# Expose port
EXPOSE 8000

# Run with uvicorn
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Create docker-compose.yml**

```yaml
# docker-compose.yml
services:
  api:
    build: .
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      ollama:
        condition: service_started
        required: false
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  ollama:
    image: ollama/ollama:latest
    profiles: ["local-llm"]
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  ollama_data:
```

- [ ] **Step 3: Test Docker build**

Run: `docker build -t scalable-search-agent:test .`
Expected: Build succeeds

- [ ] **Step 4: Commit**

```bash
git add Dockerfile docker-compose.yml
git commit -m "feat: add Dockerfile and docker-compose with optional Ollama profile"
```

---

### Task 11: GitHub Actions CI Pipeline

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create CI workflow**

```yaml
# .github/workflows/ci.yml
name: CI

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          version: "latest"
      - run: uv sync --all-extras
      - run: uv run ruff format --check .
      - run: uv run ruff check .

  test:
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          version: "latest"
      - run: uv sync --all-extras
      - name: Run unit tests
        run: uv run pytest tests/unit/ -v --tb=short
      - name: Run acceptance tests
        run: uv run pytest tests/acceptance/ -v --tb=short

  build:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v4
      - name: Build test image
        run: |
          docker build -t scalable-search-agent:test-${{ github.sha }} .

  e2e:
    runs-on: ubuntu-latest
    needs: build
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
        with:
          version: "latest"
      - run: uv sync --all-extras
      - name: Build and start container
        run: |
          docker build -t scalable-search-agent:test .
          docker run -d --name agent-test \
            -p 8000:8000 \
            -e LLM_PROVIDER=openai \
            -e LLM_MODEL=gpt-4o-mini \
            -e OPENAI_API_KEY=${{ secrets.OPENAI_API_KEY }} \
            -e TAVILY_API_KEY=${{ secrets.TAVILY_API_KEY }} \
            scalable-search-agent:test
          sleep 10
      - name: Run E2E tests
        run: uv run pytest tests/e2e/ -v --tb=short
      - name: Cleanup
        if: always()
        run: docker stop agent-test && docker rm agent-test
```

- [ ] **Step 2: Commit**

```bash
mkdir -p .github/workflows
git add .github/workflows/ci.yml
git commit -m "ci: add GitHub Actions pipeline with lint, test, build, and e2e stages"
```

---

### Task 12: GitHub Actions Release Pipeline

**Files:**
- Create: `.github/workflows/release.yml`

- [ ] **Step 1: Create release workflow**

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    branches: [main]

jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      packages: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          token: ${{ secrets.GITHUB_TOKEN }}

      - uses: astral-sh/setup-uv@v4
        with:
          version: "latest"

      - run: uv sync --all-extras

      - name: Semantic Release
        id: release
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          uv run semantic-release version
          echo "version=$(uv run semantic-release version --print)" >> $GITHUB_OUTPUT

      - name: Build and tag Docker image
        if: steps.release.outputs.version != ''
        run: |
          VERSION=${{ steps.release.outputs.version }}
          docker build -t scalable-search-agent:${VERSION} .
          docker tag scalable-search-agent:${VERSION} scalable-search-agent:latest

      - name: Push to GitHub Container Registry
        if: steps.release.outputs.version != ''
        run: |
          VERSION=${{ steps.release.outputs.version }}
          echo "${{ secrets.GITHUB_TOKEN }}" | docker login ghcr.io -u ${{ github.actor }} --password-stdin
          docker tag scalable-search-agent:${VERSION} ghcr.io/${{ github.repository }}:${VERSION}
          docker tag scalable-search-agent:${VERSION} ghcr.io/${{ github.repository }}:latest
          docker push ghcr.io/${{ github.repository }}:${VERSION}
          docker push ghcr.io/${{ github.repository }}:latest

  docs:
    runs-on: ubuntu-latest
    needs: release
    permissions:
      pages: write
      id-token: write
    steps:
      - uses: actions/checkout@v4
      - name: Install Doxygen
        run: sudo apt-get install -y doxygen graphviz
      - name: Build docs
        run: doxygen docs/Doxyfile
      - name: Upload to Pages
        uses: actions/upload-pages-artifact@v3
        with:
          path: docs/doxygen_output/html
      - name: Deploy to GitHub Pages
        uses: actions/deploy-pages@v4
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/release.yml
git commit -m "ci: add release pipeline with semantic versioning, Docker push, and docs deploy"
```

---

### Task 13: E2E Test File

**Files:**
- Create: `tests/e2e/test_api_container.py`

- [ ] **Step 1: Write E2E tests**

```python
# tests/e2e/test_api_container.py
"""E2E tests that run against a live Docker container.

These tests expect the API to be running at http://localhost:8000.
They are skipped if the service is not reachable.
"""
import json

import httpx
import pytest

BASE_URL = "http://localhost:8000"


@pytest.fixture(scope="module")
def check_service():
    """Skip all tests if the API service is not running."""
    try:
        response = httpx.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            pytest.skip("API service not healthy")
    except httpx.ConnectError:
        pytest.skip("API service not running at localhost:8000")


@pytest.mark.usefixtures("check_service")
class TestE2EApi:
    def test_health(self):
        """Health endpoint returns ok status."""
        response = httpx.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_query_json(self):
        """POST /query with stream=false returns valid JSON response."""
        response = httpx.post(
            f"{BASE_URL}/query",
            json={"query": "What is diversification?", "stream": False},
            timeout=60,
        )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert data["route"] in ("search", "direct")

    def test_query_sse_stream(self):
        """POST /query with stream=true returns SSE events."""
        with httpx.stream(
            "POST",
            f"{BASE_URL}/query",
            json={"query": "Hello", "stream": True},
            timeout=60,
        ) as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]

            events = []
            for line in response.iter_lines():
                if line.startswith("event:"):
                    events.append(line.split("event: ")[1])

            assert "route" in events
            assert "done" in events

    def test_query_validation_error(self):
        """POST /query with empty query returns 422."""
        response = httpx.post(
            f"{BASE_URL}/query",
            json={"query": ""},
            timeout=10,
        )
        assert response.status_code == 422
```

- [ ] **Step 2: Commit**

```bash
git add tests/e2e/test_api_container.py
git commit -m "test: add E2E tests for containerized API"
```

---

### Task 14: Documentation — ADRs

**Files:**
- Create: `docs/adr/template.md`
- Create: `docs/adr/001-langgraph-explicit-router.md`
- Create: `docs/adr/002-ollama-openai-abstraction.md`
- Create: `docs/adr/003-tavily-search-tool.md`

- [ ] **Step 1: Create ADR template**

```markdown
<!-- docs/adr/template.md -->
# ADR-NNN: Title

## Status
Proposed | Accepted | Deprecated | Superseded

## Context
What is the issue that we're seeing that is motivating this decision?

## Decision
What is the change that we're proposing and/or doing?

## Consequences
What becomes easier or more difficult because of this change?
```

- [ ] **Step 2: Create ADR-001**

```markdown
<!-- docs/adr/001-langgraph-explicit-router.md -->
# ADR-001: Use LangGraph with Explicit Router Pattern

## Status
Accepted

## Context
The agent must intelligently decide when to search the web vs. answer from its knowledge base. Three approaches were considered:
- **A) Pure ReAct**: LLM decides on each turn whether to use tools. Simplest code, but 7B models make unreliable tool-use decisions.
- **B) Explicit Router**: Separate classification step before the agent. Testable and predictable.
- **C) ReAct with Prompt Hints**: ReAct with system prompt heuristics to guide routing.

We are using qwen2.5:7b (local Ollama) as the default model, which has limited tool-calling reliability compared to larger models.

## Decision
Use approach B — explicit router with a separate classification node. The LangGraph graph structure is:
`router_node → [search_agent | direct_response] → format_response`

The router uses structured JSON output for its classification, making it independently testable.

## Consequences
- **Easier:** Unit testing routing logic, debugging routing decisions, tuning routing independently of generation.
- **Harder:** Adds one extra LLM call per query (router step). Slightly more code than pure ReAct.
- **Trade-off accepted:** The extra latency (~1-2s) is worth the reliability and testability gains.
```

- [ ] **Step 3: Create ADR-002**

```markdown
<!-- docs/adr/002-ollama-openai-abstraction.md -->
# ADR-002: Pluggable LLM Provider via Factory Pattern

## Status
Accepted

## Context
The assignment allows any LLM provider. We want to support both local inference (Ollama) for development/self-hosted deployment and cloud APIs (OpenAI) for production/CI.

LangChain provides `BaseChatModel` as a common interface for `ChatOllama` and `ChatOpenAI`.

## Decision
Use a factory function (`app/llm.py:create_llm`) that reads `LLM_PROVIDER` from environment and returns the appropriate LangChain chat model. All downstream code depends on `BaseChatModel`, not concrete implementations.

Docker Compose uses an optional `local-llm` profile for the Ollama service, which is excluded when using OpenAI.

## Consequences
- **Easier:** Switching providers is a single env var change. CI can use OpenAI (no GPU needed). Tests mock at the `BaseChatModel` level.
- **Harder:** Must validate that prompts work well with both providers. Structured output parsing may behave differently between models.
```

- [ ] **Step 4: Create ADR-003**

```markdown
<!-- docs/adr/003-tavily-search-tool.md -->
# ADR-003: Use Tavily for Web Search

## Status
Accepted

## Context
The agent needs a web search tool. Options considered:
- **Tavily**: Purpose-built for AI agents, returns clean structured JSON, free tier (1000 req/month).
- **SerpAPI**: Wraps Google results, comprehensive but more complex response format.
- **DuckDuckGo**: Completely free, no API key, but unstructured and less reliable.
- **Brave Search**: Good quality, free tier, but less agent-focused.

## Decision
Use Tavily Search API. Its structured response format (title, url, content, score) maps directly to our `Source` model. The `tavily-python` SDK and LangChain integration (`TavilySearchResults`) provide both direct API access and tool-compatible interfaces.

## Consequences
- **Easier:** Clean JSON responses require minimal parsing. LangChain tool integration is first-class. Free tier sufficient for development and demo.
- **Harder:** Production usage requires a paid plan. Vendor dependency on Tavily's API availability.
```

- [ ] **Step 5: Commit**

```bash
mkdir -p docs/adr
git add docs/adr/
git commit -m "docs: add ADR template and initial architecture decision records"
```

---

### Task 15: Documentation — API, Deployment, Configuration

**Files:**
- Create: `docs/api.md`
- Create: `docs/deployment.md`
- Create: `docs/configuration.md`

- [ ] **Step 1: Create API documentation**

```markdown
<!-- docs/api.md -->
# REST API Documentation

Base URL: `http://localhost:8000`

## POST /query

Submit a financial research query to the agent.

### Request

```json
{
  "query": "What is the current EUR/USD exchange rate?",
  "stream": true
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| query | string | yes | — | The research query (min 1 character) |
| stream | boolean | no | true | Whether to stream response via SSE |

### Response (stream: false)

```json
{
  "response": "The current EUR/USD exchange rate is approximately 1.0847...",
  "route": "search",
  "sources": [
    {
      "title": "Reuters - Foreign Exchange",
      "url": "https://reuters.com/markets/currencies",
      "snippet": "EUR/USD trading at 1.0847 as of..."
    }
  ]
}
```

### Response (stream: true)

Server-Sent Events stream:

```
event: route
data: {"route": "search", "reasoning": "Query asks for current exchange rate"}

event: token
data: {"content": "The ", "type": "token"}

event: token
data: {"content": "current ", "type": "token"}

event: sources
data: {"sources": [{"title": "...", "url": "...", "snippet": "..."}]}

event: done
data: {"full_response": "The current EUR/USD exchange rate is..."}
```

### Error Responses

| Code | Description | Example |
|------|-------------|---------|
| 422 | Invalid request body | `{"detail": [{"msg": "String should have at least 1 character"}]}` |
| 503 | LLM provider unavailable | `{"detail": "LLM provider not available"}` |
| 504 | Request timeout | `{"detail": "Request timed out"}` |
| 500 | Internal error | `{"detail": "Internal server error"}` |

### Example: curl

```bash
# JSON response
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the latest Fed interest rate decision?", "stream": false}'

# SSE stream
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Current EUR/USD rate", "stream": true}' \
  --no-buffer
```

## GET /health

Health check endpoint.

### Response

```json
{
  "status": "ok",
  "provider": "ollama"
}
```
```

- [ ] **Step 2: Create deployment documentation**

```markdown
<!-- docs/deployment.md -->
# Deployment Architecture

## Production AWS Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              AWS Cloud                                   │
│                                                                          │
│  Route53 → CloudFront (CDN/TLS) → ALB (HTTPS termination)              │
│                                      │                                   │
│                    ┌─────────────────────────────────────┐              │
│                    │        ECS Cluster (Fargate)         │              │
│                    │                                      │              │
│                    │  ┌──────────────────────────────┐   │              │
│                    │  │ API Service (auto-scale 2-10) │   │              │
│                    │  │ FastAPI tasks (CPU)            │   │              │
│                    │  └──────────┬───────────────────┘   │              │
│                    │             │                        │              │
│                    │  ┌──────────▼───────────────────┐   │              │
│                    │  │ Ollama Service (optional)     │   │              │
│                    │  │ GPU instances (g5.xlarge)     │   │              │
│                    │  │ Only when LLM_PROVIDER=ollama │   │              │
│                    │  └──────────────────────────────┘   │              │
│                    └─────────────────────────────────────┘              │
│                                                                          │
│  ElastiCache (Redis)     CloudWatch + X-Ray     Secrets Manager         │
│  - Response caching      - Logs, metrics        - TAVILY_API_KEY        │
│  - Rate limiting         - Latency P50/95/99    - OPENAI_API_KEY        │
│                          - GPU utilization                               │
│                          - Alarms → SNS                                  │
│                                                                          │
│  ECR (container registry)                                                │
└─────────────────────────────────────────────────────────────────────────┘

External: Tavily API, OpenAI API (when LLM_PROVIDER=openai)
```

## Scalability
- API tasks auto-scale on CPU/request count (2-10 tasks)
- Ollama tasks scale on GPU utilization (when used)
- Redis caches repeated queries to reduce LLM/search load
- ALB distributes SSE connections with sticky sessions

## Reliability
- Multi-AZ deployment for all services
- Health checks with automatic task replacement
- CloudWatch alarms → SNS for alerting
- Circuit breaker on external APIs (Tavily, OpenAI)

## Security
- TLS termination at CloudFront and ALB
- API keys stored in AWS Secrets Manager
- ECS tasks run in private subnets (no public IPs)
- WAF on CloudFront for rate limiting and DDoS protection

## Observability
- CloudWatch Logs for structured application logs
- X-Ray for distributed tracing across API → LLM → Search
- Custom CloudWatch metrics: query latency, route distribution, cache hit rate
- Dashboards for GPU utilization and model inference throughput
```

- [ ] **Step 3: Create configuration documentation**

```markdown
<!-- docs/configuration.md -->
# Configuration

All configuration is via environment variables. Copy `.env.example` to `.env` for local development.

## Environment Variables

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `LLM_PROVIDER` | `ollama` | no | LLM backend: `ollama` or `openai` |
| `LLM_MODEL` | `qwen2.5:7b` | no | Model name for the chosen provider |
| `LLM_TIMEOUT` | `30` | no | LLM request timeout in seconds |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | no | Ollama API endpoint |
| `OPENAI_API_KEY` | — | if openai | OpenAI API key |
| `TAVILY_API_KEY` | — | yes | Tavily Search API key |
| `API_HOST` | `0.0.0.0` | no | API bind address |
| `API_PORT` | `8000` | no | API bind port |

## Running with Ollama (Local LLM)

```bash
# Start Ollama and pull the model
ollama pull qwen2.5:7b

# Start with Docker Compose
docker compose --profile local-llm up
```

## Running with OpenAI

```bash
# Set provider and key in .env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-your-key-here

# Start (no Ollama service needed)
docker compose up
```

## Running Locally (Development)

```bash
uv sync --all-extras
cp .env.example .env
# Edit .env with your keys
uv run uvicorn app.main:app --reload
```
```

- [ ] **Step 4: Commit**

```bash
git add docs/api.md docs/deployment.md docs/configuration.md
git commit -m "docs: add API reference, deployment architecture, and configuration guide"
```

---

### Task 16: Doxygen Configuration

**Files:**
- Create: `docs/Doxyfile`

- [ ] **Step 1: Create Doxyfile**

```
# docs/Doxyfile
PROJECT_NAME           = "Financial Research Agent"
PROJECT_BRIEF          = "LLM-powered Internet-Search Agent for financial research"
OUTPUT_DIRECTORY       = docs/doxygen_output

INPUT                  = app/
RECURSIVE              = YES
FILE_PATTERNS          = *.py
EXCLUDE_PATTERNS       = */__pycache__/*

EXTRACT_ALL            = YES
EXTRACT_PRIVATE        = NO
EXTRACT_STATIC         = YES

OPTIMIZE_OUTPUT_JAVA   = NO
PYTHON_DOCSTRING       = YES

GENERATE_HTML          = YES
GENERATE_LATEX         = NO

HTML_OUTPUT            = html
HTML_COLORSTYLE        = LIGHT

HAVE_DOT               = YES
CALL_GRAPH             = YES
CALLER_GRAPH           = YES
DOT_IMAGE_FORMAT       = svg

SOURCE_BROWSER         = YES
INLINE_SOURCES         = NO
```

- [ ] **Step 2: Commit**

```bash
git add docs/Doxyfile
git commit -m "docs: add Doxygen configuration for Python source documentation"
```

---

### Task 17: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create README**

```markdown
# Financial Research Agent

LLM-powered Internet-Search Agent for financial research. Built with LangGraph, FastAPI, and Tavily.

## Features

- **Smart Query Routing** — Automatically decides whether to search the web or answer from knowledge
- **Streaming Responses** — Real-time SSE streaming of agent responses
- **Source Attribution** — All search-based answers include numbered source references
- **Pluggable LLM** — Supports Ollama (local) and OpenAI (cloud) via environment config

## Quick Start

### Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [Docker](https://docs.docker.com/get-docker/) (for containerized deployment)
- [Ollama](https://ollama.com/) (if using local LLM)
- [Tavily API key](https://tavily.com/) (free tier available)

### Setup

```bash
# Clone and install
git clone <repo-url>
cd scalable_test
uv sync --all-extras

# Configure
cp .env.example .env
# Edit .env with your Tavily API key and LLM preference
```

### Run with Ollama (Local LLM)

```bash
ollama pull qwen2.5:7b
uv run uvicorn app.main:app --reload
```

### Run with OpenAI

```bash
# Set in .env: LLM_PROVIDER=openai, OPENAI_API_KEY=sk-...
uv run uvicorn app.main:app --reload
```

### Run with Docker

```bash
# OpenAI mode
docker compose up

# Ollama mode
docker compose --profile local-llm up
```

## Usage

```bash
# JSON response
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the current EUR/USD rate?", "stream": false}'

# SSE streaming
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Latest Fed decision", "stream": true}' \
  --no-buffer

# Health check
curl http://localhost:8000/health
```

## Testing

```bash
uv run pytest tests/unit/ -v           # Unit tests
uv run pytest tests/acceptance/ -v     # Acceptance tests
uv run pytest tests/e2e/ -v            # E2E tests (requires running container)
```

## Documentation

- [API Reference](../../api.md)
- [Configuration Guide](../../configuration.md)
- [Deployment Architecture](../../deployment.md)
- [Architecture Decision Records](../../adr/index.md)

## Architecture

```
POST /query → FastAPI → LangGraph:
  router_node → [search_agent | direct_response] → format_response → SSE/JSON response
```

See [ADR-001](../../adr/001-langgraph-explicit-router.md) for the routing
design rationale.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with quickstart, usage, and architecture overview"
```

---

## Self-Review Checklist

**Spec coverage:**
- [x] LangGraph with explicit router (Task 5-7)
- [x] Ollama + OpenAI abstraction (Task 2)
- [x] Tavily search integration (Task 6)
- [x] POST /query with SSE + JSON (Task 8)
- [x] GET /health (Task 8)
- [x] Pydantic models and schemas (Task 3)
- [x] uv + ruff + pre-commit (Task 1)
- [x] Unit tests for router (Task 5)
- [x] Unit tests for utils (Task 3)
- [x] Acceptance tests for graph (Task 7)
- [x] E2E tests for container (Task 13)
- [x] Dockerfile + docker-compose (Task 10)
- [x] CI pipeline (Task 11)
- [x] Release pipeline (Task 12)
- [x] ADRs (Task 14)
- [x] API docs (Task 15)
- [x] Deployment docs (Task 15)
- [x] Configuration docs (Task 15)
- [x] Doxygen (Task 16)
- [x] README (Task 17)
- [x] SOLID / DI / utils.py (Tasks 2, 3, 6)
- [x] Conventional commits (all tasks)

**Placeholder scan:** No TBDs, TODOs, or vague steps found.

**Type consistency:**
- `AgentState` used consistently in nodes and graph
- `Source` model used in utils, nodes, and routes
- `RouteDecision` defined in models, JSON parsing in router node
- `QueryRequest` / `QueryResponse` used in routes
- `Settings` used in config, llm factory, and main
- `create_llm` signature matches usage in main.py lifespan
- `build_graph` signature matches usage in main.py and tests
