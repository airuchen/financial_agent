# Application Architecture

## Runtime Flow

```mermaid
flowchart TD
    C[Client] -->|POST /query| API[FastAPI /query]
    C -->|GET /health| H[FastAPI /health]

    API --> G{Auth Guard Enabled?}
    G -->|Yes| ARL[Auth + Rate Limiter]
    G -->|No| CP[Cache Policy Classifier]
    ARL --> CP

    CP --> CH{Redis Cache Enabled?}
    CH -->|Hit| CR[Return Cached Response]
    CH -->|Miss| AG[LangGraph Agent]
    CH -->|No Cache| AG

    AG --> R[Router Node]
    R -->|search| S[Search Agent Node]
    R -->|direct| D[Direct Response Node]

    S --> T[Tavily Search API]
    S --> L[LLM Provider]
    D --> L
    L --> F[Format Response Node]
    S --> F
    D --> F

    F --> W{Cache Write Eligible?}
    W -->|Yes| RC[(Redis Cache)]
    W -->|No| RESP[Response]
    RC --> RESP

    RESP -->|JSON| C
    RESP -->|SSE stream| C
```

## LangGraph Node Flow

```mermaid
flowchart LR
    START([START]) --> router[router_node]
    router -->|route=search| search[search_agent]
    router -->|route=direct| direct[direct_response]
    search --> format[format_response]
    direct --> format
    format --> END([END])
```

## Notes

- `router_node` uses deterministic rules for time-critical finance queries, then LLM intent classification for everything else.
- `search_agent` retrieves results (or uses cached results), sanitizes untrusted content, and synthesizes with source references.
- `format_response` appends numbered sources for search-routed responses.
