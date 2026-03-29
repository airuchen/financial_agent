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
            temperature=settings.llm_temperature,
            timeout=settings.llm_timeout,
        )
    elif settings.llm_provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.openai_api_key,
            temperature=settings.llm_temperature,
            timeout=settings.llm_timeout,
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")
