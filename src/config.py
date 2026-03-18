from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    api_title: str = "LLM Security Scanner"
    api_version: str = "3.0"

    llm_provider: str = "openai"
    llm_model: str = "gpt-5-mini"
    llm_api_key: str = ""

    model_config = {"env_file": ".env"}


settings = Settings()
