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
| `CACHE_ENABLED` | `true` | no | Enable Redis-backed response/search caching |
| `REDIS_URL` | `redis://localhost:6379/0` | no | Redis connection URL |
| `CACHE_PROMPT_REVISION` | `v1` | no | Prompt revision tag included in cache keys |
| `CACHE_TTL_DIRECT_SEC` | `86400` | no | TTL for direct-response cache entries |
| `CACHE_TTL_SEARCH_RESULTS_SEC` | `900` | no | TTL for cached non-critical search results |
| `CACHE_TTL_SEARCH_ANSWER_SEC` | `300` | no | TTL for cached non-critical search answers |

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
