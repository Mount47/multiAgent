"""Application settings loaded from .env file."""

from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM API Keys
    openai_api_key: str = ""
    deepseek_api_key: str = ""

    # Default model provider
    default_model: str = "deepseek-chat"

    # Ollama
    ollama_base_url: str = "http://localhost:11434/v1"

    # Application
    workspace_dir: str = "./workspace"
    log_level: str = "INFO"
    max_workflow_rounds: int = 30

    # Paths
    project_root: Path = Path(__file__).parent.parent

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
