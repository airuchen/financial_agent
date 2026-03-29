from unittest.mock import patch

import pytest
from pydantic import ValidationError

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


def test_settings_requires_tavily_api_key():
    """Settings validation fails when TAVILY_API_KEY is missing."""
    with (
        patch.dict("os.environ", {"TAVILY_API_KEY": ""}, clear=False),
        pytest.raises(ValidationError, match="TAVILY_API_KEY is required"),
    ):
        Settings()


def test_settings_requires_openai_key_for_openai_provider():
    """Settings validation fails without OPENAI_API_KEY in OpenAI mode."""
    with (
        patch.dict(
            "os.environ",
            {
                "LLM_PROVIDER": "openai",
                "OPENAI_API_KEY": "",
                "TAVILY_API_KEY": "tvly-test",
            },
            clear=False,
        ),
        pytest.raises(
            ValidationError,
            match="OPENAI_API_KEY is required when LLM_PROVIDER=openai",
        ),
    ):
        Settings()
