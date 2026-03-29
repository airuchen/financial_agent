from unittest.mock import patch

import pytest

from app.config import Settings
from app.llm import create_llm


def test_create_llm_ollama():
    """Factory returns ChatOllama when provider is ollama."""
    settings = Settings(
        llm_provider="ollama",
        llm_model="qwen2.5:7b",
        ollama_base_url="http://localhost:11434",
        tavily_api_key="tvly-test",
    )
    llm = create_llm(settings)
    from langchain_ollama import ChatOllama

    assert isinstance(llm, ChatOllama)


def test_create_llm_openai():
    """Factory returns ChatOpenAI when provider is openai."""
    settings = Settings(
        llm_provider="openai",
        llm_model="gpt-4o-mini",
        openai_api_key="sk-test",
        tavily_api_key="tvly-test",
    )
    llm = create_llm(settings)
    from langchain_openai import ChatOpenAI

    assert isinstance(llm, ChatOpenAI)


def test_create_llm_invalid_provider():
    """Factory raises ValueError for unknown provider."""
    settings = Settings(
        llm_provider="invalid",
        llm_model="some-model",
        tavily_api_key="tvly-test",
    )
    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        create_llm(settings)


def test_settings_defaults():
    """Settings loads defaults correctly."""
    with patch.dict(
        "os.environ",
        {"TAVILY_API_KEY": "tvly-test"},
        clear=False,
    ):
        settings = Settings()
        assert settings.llm_provider == "ollama"
        assert settings.llm_model == "qwen2.5:7b"
        assert settings.llm_timeout == 30
