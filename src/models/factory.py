"""Factory for creating LLM model clients from YAML configuration.

Supports OpenAI, DeepSeek, and Ollama (all via OpenAI-compatible API).
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

import logging

import yaml
from autogen_core.models import ChatCompletionClient
from autogen_ext.models.openai import OpenAIChatCompletionClient

from config.settings import settings
from src.models.config import ModelsConfig, ProviderConfig
from src.models.resilient_client import ResilientChatCompletionClient

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "models.yaml"

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}


def _bypass_proxy_for_local(base_url: str) -> None:
    """Ensure local base_urls bypass any HTTP(S)_PROXY (e.g. Clash/v2ray).

    A system proxy set for reaching Gemini/OpenAI will otherwise intercept
    calls to a local Ollama server and return ``502 Bad Gateway``. We only
    add local hosts to NO_PROXY so remote providers keep using the proxy.
    """
    host = (urlparse(base_url).hostname or "").lower()
    if host not in _LOCAL_HOSTS:
        return
    existing = os.environ.get("NO_PROXY", "") or os.environ.get("no_proxy", "")
    entries = {e.strip() for e in existing.split(",") if e.strip()}
    if not _LOCAL_HOSTS <= entries:
        merged = ",".join(sorted(entries | _LOCAL_HOSTS))
        os.environ["NO_PROXY"] = merged
        os.environ["no_proxy"] = merged


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
    # Local servers (Ollama) must bypass any system HTTP proxy.
    _bypass_proxy_for_local(provider_config.base_url)

    # Resolve API key from environment variable
    api_key = "placeholder"
    if provider_config.api_key_env:
        api_key = os.environ.get(provider_config.api_key_env, "")
        if not api_key:
            raise ValueError(
                f"Environment variable {provider_config.api_key_env} is not set. "
                f"Please set it in your .env file."
            )

    extra: dict = {}
    if provider_config.extra_body:
        extra["extra_body"] = provider_config.extra_body

    return OpenAIChatCompletionClient(
        model=provider_config.model,
        base_url=provider_config.base_url,
        api_key=api_key,
        temperature=provider_config.temperature,
        timeout=settings.llm_timeout_seconds,
        # ResilientChatCompletionClient owns the retry policy; keep the inner
        # SDK from retrying too so attempts aren't multiplied.
        max_retries=0,
        model_info={
            "vision": provider_config.model_info.vision,
            "function_calling": provider_config.model_info.function_calling,
            "json_output": provider_config.model_info.json_output,
            "family": provider_config.model_info.family,
        },
        **extra,
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
        self._raw_clients: dict[str, OpenAIChatCompletionClient] = {}
        self._clients: dict[str, ChatCompletionClient] = {}

    @property
    def config(self) -> ModelsConfig:
        return self._config

    def _get_raw_client(self, provider_name: str) -> OpenAIChatCompletionClient:
        """Build (and cache) the underlying OpenAI client for a provider."""
        if provider_name not in self._raw_clients:
            self._raw_clients[provider_name] = create_model_client(
                self._config.providers[provider_name]
            )
        return self._raw_clients[provider_name]

    def get_client(self, provider_name: str) -> ChatCompletionClient:
        """Get a resilient client (retry + fallback) for the given provider."""
        if provider_name not in self._config.providers:
            available = ", ".join(self._config.providers.keys())
            raise ValueError(
                f"Unknown provider '{provider_name}'. Available: {available}"
            )

        if provider_name not in self._clients:
            clients: list[tuple[str, ChatCompletionClient]] = [
                (provider_name, self._get_raw_client(provider_name))
            ]
            # Resolve fallback chain; skip any that can't be built (e.g. no key).
            for fb_name in self._config.providers[provider_name].fallback:
                if fb_name == provider_name or fb_name not in self._config.providers:
                    continue
                try:
                    clients.append((fb_name, self._get_raw_client(fb_name)))
                except Exception as exc:  # noqa: BLE001
                    logger.info(
                        "[LLM] fallback provider '%s' unavailable, skipping: %s",
                        fb_name, exc,
                    )
            self._clients[provider_name] = ResilientChatCompletionClient(
                clients,
                max_attempts=settings.llm_retry_max_attempts,
                base_delay=settings.llm_retry_base_delay,
                max_delay=settings.llm_retry_max_delay,
            )

        return self._clients[provider_name]

    def get_client_for_agent(self, agent_role: str) -> ChatCompletionClient:
        """Get the model client assigned to a specific agent role.

        Falls back to DEFAULT_MODEL from environment if agent has no override.
        """
        provider_name = self._config.agent_models.get(agent_role)

        if provider_name is None:
            # Fall back to DEFAULT_MODEL env var
            provider_name = os.environ.get("DEFAULT_MODEL", "deepseek-chat")

        return self.get_client(provider_name)
