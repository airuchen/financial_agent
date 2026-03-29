# Internet-Search Agent — Design Spec

## Overview

An LLM-powered Internet-Search Agent for financial research, exposed via REST API. Built for Scalable Capital's Investment Research team to gather, process, and summarize financial information from the web.

## Tech Stack

| Component | Choice |
|-----------|--------|
| Agent framework | LangGraph (LangChain) |
| LLM (default) | Ollama — qwen2.5:7b |
| LLM (alternative) | OpenAI — gpt-4o-mini |
| Search tool | Tavily API |
| API framework | FastAPI |
| Package manager | uv |
| Linting/formatting | ruff + pre-commit |
| Testing | pytest, pytest-asyncio, httpx |
| Containerization | Docker, docker-compose |
| CI/CD | GitHub Actions |
| Deployment | AWS (ECS Fargate, ALB, ElastiCache, CloudWatch) |

## Agent Architecture

### Graph Structure (LangGraph — Approach B: Explicit Router)

```
START → router_node → [search_agent | direct_response] → format_response → END
```

**Nodes:**

1. **`router_node`** — Calls the LLM with a classification prompt. Uses structured output to return `{"route": "search" | "direct", "reasoning": "..."}`. Routing heuristics:
   - **Search:** current prices, recent events, specific financial data, regulatory updates, named entities with temporal context
   - **Direct:** greetings, definitions, general finance concepts, math, static knowledge

2. **`search_agent`** — ReAct agent with Tavily as its tool. May perform multiple searches to gather sufficient information, then synthesizes results with source attribution.

3. **`direct_response`** — Single LLM call with no tools. Answers from model knowledge.

4. **`format_response`** — Runs for both routes. Normalizes output into a consistent structure. For search route: adds numbered source citations (e.g., "[1]", "[2]") and appends a references list. For direct route: passes through the response as-is.

### State Schema

```python
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    route: str              # "search" or "direct"
    sources: list[dict]     # [{"title": str, "url": str, "snippet": str}]
```

### Streaming

LangGraph's `astream_events` pipes tokens through FastAPI's `StreamingResponse` via Server-Sent Events (SSE).

## LLM Provider Abstraction

Config-driven provider selection via environment variable. LangChain's `BaseChatModel` interface makes `ChatOllama` and `ChatOpenAI` interchangeable.

```python
# .env
LLM_PROVIDER=ollama          # or "openai"
LLM_MODEL=qwen2.5:7b         # or "gpt-4o-mini"
OPENAI_API_KEY=sk-...         # only needed if provider=openai
```

Factory function in `app/llm.py` returns the configured client. All downstream code receives the LLM via dependency injection — no provider-specific branching outside the factory.

**Deployment impact:** When using OpenAI, the Ollama GPU service is not needed. ECS runs only CPU-based API tasks. `docker-compose.yml` uses a `local-llm` profile for Ollama:

```yaml
services:
  ollama:
    profiles: ["local-llm"]
```

## REST API

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/query` | Submit a query, returns streamed SSE or JSON response |
| `GET` | `/health` | Health check (LLM connectivity, Tavily key present) |

### POST /query

**Request:**
```json
{
  "query": "What is the current EUR/USD exchange rate?",
  "stream": true
}
```

**SSE Response (stream: true):**
```
event: route
data: {"route": "search", "reasoning": "Query asks for current exchange rate"}

event: token
data: {"content": "The", "type": "token"}

event: token
data: {"content": " current", "type": "token"}

event: sources
data: {"sources": [{"title": "...", "url": "...", "snippet": "..."}]}

event: done
data: {"full_response": "The current EUR/USD..."}
```

**JSON Response (stream: false):**
```json
{
  "response": "The current EUR/USD exchange rate is...",
  "route": "search",
  "sources": [{"title": "...", "url": "...", "snippet": "..."}]
}
```

### Error Codes

| Code | Meaning |
|------|---------|
| 422 | Invalid request body |
| 503 | LLM provider not available |
| 504 | LLM/search timeout (30s default) |
| 500 | Unexpected error |

## Project Structure

```
scalable_test/
├── .github/
│   └── workflows/
│       ├── ci.yml                    # PR: lint → test → build → e2e
│       └── release.yml               # Merge: version bump → retag → docs
├── .pre-commit-config.yaml
├── app/
│   ├── __init__.py
│   ├── main.py                       # FastAPI app, lifespan, CORS
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py                 # POST /query, GET /health
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── graph.py                  # LangGraph graph definition
│   │   ├── nodes.py                  # router_node, search_agent, direct_response, format_response
│   │   ├── state.py                  # AgentState TypedDict
│   │   └── prompts.py                # System prompts for router and agent
│   ├── config.py                     # Settings via pydantic-settings
│   ├── llm.py                        # LLM factory (Ollama / OpenAI)
│   ├── models.py                     # Pydantic request/response schemas
│   └── utils.py                      # Shared helpers (SSE formatting, retry, source extraction)
├── tests/
│   ├── unit/
│   │   ├── test_router.py            # Routing decision tests
│   │   └── test_utils.py             # Utility function tests
│   ├── acceptance/
│   │   └── test_agent.py             # Full graph flow with mocked search
│   └── e2e/
│       └── test_api_container.py     # Runs against built Docker image
├── docs/
│   ├── adr/
│   │   ├── 001-langgraph-explicit-router.md
│   │   ├── 002-ollama-openai-abstraction.md
│   │   ├── 003-tavily-search-tool.md
│   │   └── template.md
│   ├── api.md                        # REST API documentation
│   ├── deployment.md                 # Deployment architecture + diagram
│   ├── configuration.md              # Env vars, provider setup, docker profiles
│   └── Doxyfile                      # Doxygen configuration for Python
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml                    # uv, ruff config, semantic-release config
├── uv.lock
├── .env.example
└── README.md
```

## Testing Strategy

### Unit Tests (`tests/unit/`)

**`test_router.py`:**
- Mock the LLM, verify routing classifications
- Cases: "Current EUR/USD" → search, "Hello" → direct, "What is diversification?" → direct, "Latest Fed decision" → search
- Test structured output parsing and fallback on malformed LLM responses

**`test_utils.py`:**
- Test SSE event formatting
- Test source extraction and normalization
- Test response formatting helpers

### Acceptance Tests (`tests/acceptance/`)

**`test_agent.py`:**
- Full LangGraph execution with mocked Tavily responses
- Verify search path produces source attribution
- Verify direct path produces no sources
- Test streaming event sequence

### E2E Tests (`tests/e2e/`)

**`test_api_container.py`:**
- Runs against the built Docker image
- Send queries via HTTP, validate SSE stream format
- Test health endpoint
- Test error responses (missing query, provider down)

### Test Runner

`pytest` with `pytest-asyncio`. `httpx.AsyncClient` for API tests. Mocking via `unittest.mock`.

## CI/CD Pipeline (GitHub Actions)

### On PR / Push to Non-Main (`ci.yml`)

```
Static Tests          Unit + Acceptance       Build Test Image       E2E Tests
─────────────  →  ───────────────────  →  ──────────────────  →  ─────────────────
pre-commit run       pytest tests/unit/      docker build           run container
ruff format --check  pytest tests/acceptance  tag: test-<sha>       pytest tests/e2e/
ruff check                                                          against container
```

### On Merge to Main (`release.yml`)

```
Version Bump                     Retag + Push               Build Docs
──────────────────────  →  ─────────────────────  →  ──────────────────
python-semantic-release       retag test-<sha>          doxygen docs/Doxyfile
based on conventional          with version tag          deploy to GitHub Pages
commit messages                push to ECR
```

### Commit Convention

Conventional Commits drive automatic versioning:
- `feat:` → minor version bump
- `fix:` → patch version bump
- `feat!:` or `BREAKING CHANGE:` → major version bump

## Documentation

### Architecture Decision Records (`docs/adr/`)

Lightweight MADR format:
```markdown
# ADR-NNN: Title

## Status
Accepted | Superseded | Deprecated

## Context
What is the issue that we're seeing that is motivating this decision?

## Decision
What is the change that we're proposing and/or doing?

## Consequences
What becomes easier or more difficult because of this change?
```

### Doxygen Documentation Hub

- Python docstrings in **Google style** (compatible with Doxygen's Python parser)
- `Doxyfile` configured to scan `app/` recursively
- Generates HTML site with module hierarchy, call graphs, cross-references
- Built in CI on merge, deployed to GitHub Pages

### API Documentation

`docs/api.md` with endpoint descriptions, request/response schemas, example curl commands, and error code reference. FastAPI also auto-generates OpenAPI spec at `/docs`.

## Deployment Architecture (Production AWS)

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
│                          - GPU utilization       - (no Ollama key)      │
│                          - Alarms → SNS                                  │
│                                                                          │
│  ECR (container registry)                                                │
└─────────────────────────────────────────────────────────────────────────┘

External: Tavily API, OpenAI API (when LLM_PROVIDER=openai)
```

### Scalability
- API tasks auto-scale on CPU/request count (2-10 tasks)
- Ollama tasks scale on GPU utilization (when used)
- Redis caches repeated queries (e.g., "EUR/USD" asked 100x/day)
- ALB distributes SSE connections evenly
- When using OpenAI: no GPU infrastructure needed, scales purely on API task count

### Reliability
- Multi-AZ deployment for API and Ollama services
- Health checks on both services
- CloudWatch alarms → SNS for on-call alerts
- Circuit breaker on external API calls (Tavily, OpenAI)

### Security
- TLS everywhere (CloudFront → ALB → tasks)
- Secrets Manager for all API keys
- Private subnets for ECS tasks
- WAF on CloudFront for rate limiting and DDoS protection

### Observability
- CloudWatch Logs for all services
- X-Ray for distributed tracing (API → LLM → Tavily)
- Custom metrics: query latency, routing decisions, cache hit rate
- Dashboard for GPU utilization and model throughput

## Code Quality

### SOLID Principles
- **Single Responsibility:** Each module has one job — `nodes.py` (graph logic), `routes.py` (HTTP), `prompts.py` (prompt text), `llm.py` (provider factory)
- **Open/Closed:** New tools or LLM providers added without modifying existing nodes (tools list and LLM injected)
- **Liskov Substitution:** `ChatOllama` and `ChatOpenAI` are interchangeable via `BaseChatModel`
- **Interface Segregation:** Small typed interfaces — `RouteDecision`, `AgentState`, `QueryRequest`
- **Dependency Inversion:** LLM client and search tool injected via config/factory, not hardcoded. Tests swap in mocks.

### Conventions
- Google-style docstrings on all public functions/classes
- Conventional Commits for all commit messages
- Factor shared logic into `app/utils.py`
- Each commit minimal and focused on a single purpose
