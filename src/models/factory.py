"""Factory for creating LLM model clients from YAML configuration.

Supports OpenAI, DeepSeek, and Ollama (all via OpenAI-compatible API).
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from autogen_ext.models.openai import OpenAIChatCompletionClient

from config.settings import settings
from src.models.config import ModelsConfig, ProviderConfig

_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "models.yaml"


def load_models_config(config_path: Path = _CONFIG_PATH) -> ModelsConfig:
    """Load and parse models.yaml into a ModelsConfig object."""
    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return ModelsConfig(**raw)


def create_model_client(provider_config: ProviderConfig) -> OpenAIChatCompletionClient:
    """Create an OpenAIChatCompletionClient from a provider configuration.

    DeepSeek and Ollama both expose OpenAI-compatible APIs,
    so a single client type handles all providers via different base_url.
    """
    # Resolve API key from environment variable
    api_key = "placeholder"
    if provider_config.api_key_env:
        api_key = os.environ.get(provider_config.api_key_env, "")
        if not api_key:
            raise ValueError(
                f"Environment variable {provider_config.api_key_env} is not set. "
                f"Please set it in your .env file."
            )

    return OpenAIChatCompletionClient(
        model=provider_config.model,
        base_url=provider_config.base_url,
        api_key=api_key,
        temperature=provider_config.temperature,
        timeout=settings.llm_timeout_seconds,
        max_retries=settings.llm_max_retries,
        model_info={
            "vision": provider_config.model_info.vision,
            "function_calling": provider_config.model_info.function_calling,
            "json_output": provider_config.model_info.json_output,
            "family": provider_config.model_info.family,
        },
    )


class ModelClientFactory:
    """Factory that creates model clients by provider name.

    Usage:
        factory = ModelClientFactory()
        client = factory.get_client("deepseek-chat")
        agent_client = factory.get_client_for_agent("coder")
    """

    def __init__(self, config_path: Path = _CONFIG_PATH):
        self._config = load_models_config(config_path)
        self._clients: dict[str, OpenAIChatCompletionClient] = {}

    @property
    def config(self) -> ModelsConfig:
        return self._config

    def get_client(self, provider_name: str) -> OpenAIChatCompletionClient:
        """Get or create a model client for the given provider name."""
        if provider_name not in self._config.providers:
            available = ", ".join(self._config.providers.keys())
            raise ValueError(
                f"Unknown provider '{provider_name}'. Available: {available}"
            )

        if provider_name not in self._clients:
            provider_config = self._config.providers[provider_name]
            self._clients[provider_name] = create_model_client(provider_config)

        return self._clients[provider_name]

    def get_client_for_agent(self, agent_role: str) -> OpenAIChatCompletionClient:
        """Get the model client assigned to a specific agent role.

        Falls back to DEFAULT_MODEL from environment if agent has no override.
        """
        provider_name = self._config.agent_models.get(agent_role)

        if provider_name is None:
            # Fall back to DEFAULT_MODEL env var
            provider_name = os.environ.get("DEFAULT_MODEL", "deepseek-chat")

        return self.get_client(provider_name)
