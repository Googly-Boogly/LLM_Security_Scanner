from pathlib import Path
from pydantic_settings import BaseSettings

_ENV_FILE = Path(__file__).parent.parent / ".env"


class Settings(BaseSettings):
    api_title: str = "LLM Security Scanner"
    api_version: str = "3.0"

    # Target LLM
    llm_provider: str = "openai"
    llm_model: str = "gpt-5-mini"
    llm_api_key: str = ""

    # Judge LLM (defaults to target model if not set)
    judge_model: str = ""

    # Scan behaviour
    system_prompt: str = "You are a helpful assistant."
    categories: str = "injection,jailbreak,leakage,harmful"
    concurrency: int = 5

    # Output
    output: str = ""   # empty = auto-generate scan_YYYYMMDD_HHMMSS.json

    model_config = {"env_file": str(_ENV_FILE)}


settings = Settings()
