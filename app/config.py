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
