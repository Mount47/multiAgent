"""Application settings loaded from .env file."""

from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM API Keys
    gemini_api_key: str = ""
    openai_api_key: str = ""
    deepseek_api_key: str = ""

    # Default model provider
    default_model: str = "gemini"
    llm_timeout_seconds: float = 60.0
    llm_max_retries: int = 2

    # Application
    workspace_dir: str = "./workspace"
    log_level: str = "INFO"
    max_workflow_rounds: int = 30

    # Paths
    project_root: Path = Path(__file__).parent.parent

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
