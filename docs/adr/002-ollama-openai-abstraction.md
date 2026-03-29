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
