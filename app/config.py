from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # LLM
    llm_provider: str = "ollama"
    llm_model: str = "qwen2.5:7b"
    llm_timeout: int = 30

    # Ollama
    ollama_base_url: str = "http://localhost:11434"

    # OpenAI
    openai_api_key: str = ""

    # Tavily
    tavily_api_key: str = ""

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_allowed_origins: str = "http://localhost:3000,http://localhost:5173"
    cors_allow_credentials: bool = False

    # Cache
    cache_enabled: bool = True
    redis_url: str = "redis://localhost:6379/0"
    cache_prompt_revision: str = "v1"
    cache_ttl_direct_sec: int = 86400
    cache_ttl_search_results_sec: int = 900
    cache_ttl_search_answer_sec: int = 300

    @model_validator(mode="after")
    def validate_required_keys(self):
        """Validate provider-dependent and required external API credentials."""
        if self.llm_provider == "openai" and not self.openai_api_key.strip():
            raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
        if not self.tavily_api_key.strip():
            raise ValueError("TAVILY_API_KEY is required")
        return self
