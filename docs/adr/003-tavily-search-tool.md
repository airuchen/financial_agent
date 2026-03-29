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
