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
  "cache_hit": false,
  "cache_tier": "none",
  "retrieved_at": null,
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
data: {"route": "search"}

event: meta
data: {"cache_hit": false, "cache_tier": "none", "retrieved_at": null}

event: token
data: {"content": "The ", "type": "token"}

event: token
data: {"content": "current ", "type": "token"}

event: sources
data: {"sources": [{"title": "...", "url": "...", "snippet": "..."}]}

event: done
data: {"full_response": "The current EUR/USD exchange rate is...", "cache_hit": false, "cache_tier": "none", "retrieved_at": null}
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
