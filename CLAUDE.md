# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Internet-Search Agent for financial research at Scalable Capital. LLM-powered agent with smart query routing (search vs. direct answer), exposed via REST API with SSE streaming.

## Tech Stack

- **Agent:** LangGraph (LangChain) with explicit router pattern
- **LLM:** Pluggable — Ollama (qwen2.5:7b) or OpenAI (gpt-4o-mini) via `LLM_PROVIDER` env var
- **Search:** Tavily API
- **API:** FastAPI with SSE streaming
- **Package manager:** uv
- **Linting:** ruff + pre-commit
- **Testing:** pytest + pytest-asyncio + httpx
- **CI:** GitHub Actions (conventional commits + python-semantic-release)

## Commands

```bash
# Setup
uv sync                              # Install dependencies
uv run pre-commit install            # Install pre-commit hooks
cp .env.example .env                 # Configure environment

# Run
uv run uvicorn app.main:app --reload              # Dev server
docker compose up                                  # Full stack (API only, OpenAI mode)
docker compose --profile local-llm up              # Full stack with Ollama

# Test
uv run pytest tests/unit/                          # Unit tests
uv run pytest tests/acceptance/                    # Acceptance tests (mocked search)
uv run pytest tests/e2e/                           # E2E tests (requires running container)
uv run pytest                                      # All tests

# Lint
uv run ruff check .                                # Lint
uv run ruff format --check .                       # Format check
uv run pre-commit run --all-files                  # All pre-commit hooks

# Docs
doxygen docs/Doxyfile                              # Build Doxygen HTML
```

## Architecture

```
START → router_node → [search_agent | direct_response] → format_response → END
```

- `router_node`: Classifies query as "search" or "direct" via structured LLM output
- `search_agent`: ReAct agent with Tavily tool, produces sourced answers
- `direct_response`: Single LLM call, no tools
- `format_response`: Normalizes output, adds citations for search route

LLM provider is abstracted via factory in `app/llm.py` — `ChatOllama` and `ChatOpenAI` are interchangeable through LangChain's `BaseChatModel`.

## Conventions

- **Commits:** Conventional Commits (`feat:`, `fix:`, `chore:`) — drives semantic versioning
- **Docstrings:** Google style (Doxygen-compatible)
- **Code quality:** SOLID principles, DI for LLM/search, shared helpers in `app/utils.py`
- **ADRs:** Architecture Decision Records in `docs/adr/` using MADR format
