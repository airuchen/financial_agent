# Financial Research Agent

LLM-powered Internet-Search Agent for financial research. Built with LangGraph, FastAPI, and Tavily.

## Features

- **Smart Query Routing** — Automatically decides whether to search the web or answer from knowledge
- **Mixed-Intent Safe Routing** — Time-critical finance signals (e.g., "current stock price") force search even with greeting prefixes
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
# Set API_KEY_HASHES with sha256 hashes for allowed API keys
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
  -H "Authorization: Bearer <api_key>" \
  -d '{"query": "What is the current EUR/USD rate?", "stream": false}'

# SSE streaming
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <api_key>" \
  -d '{"query": "Latest Fed decision", "stream": true}' \
  --no-buffer

# Health check
curl http://localhost:8000/health

# Interactive chat client (streaming)
uv run python tools/chat.py

# With custom URL and API key
uv run python tools/chat.py --url http://localhost:8000 --api-key your-key
```

## Testing

```bash
uv run pytest tests/unit/ -v           # Unit tests
uv run pytest tests/acceptance/ -v     # Acceptance tests
uv run pytest tests/e2e/ -v            # E2E tests (requires running container)
```

## Documentation

- [Architecture](docs/architecture.md)
- [API Reference](docs/api.md)
- [Configuration Guide](docs/configuration.md)
- [Production Readiness: Scalability, Security, Reliability](docs/production-readiness.md)
- [Deployment Architecture](docs/deployment.md)
- [Architecture Decision Records](docs/adr/)

