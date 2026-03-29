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
