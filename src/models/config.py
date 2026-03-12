"""Pydantic models for model provider configuration."""

from __future__ import annotations

from pydantic import BaseModel


class ModelInfo(BaseModel):
    """Capabilities of a model, required by AutoGen's OpenAIChatCompletionClient."""

    vision: bool = False
    function_calling: bool = True
    json_output: bool = True
    family: str = "unknown"


class ProviderConfig(BaseModel):
    """Configuration for a single LLM provider."""

    model: str
    base_url: str
    api_key_env: str = ""
    temperature: float = 0.3
    model_info: ModelInfo = ModelInfo()


class ModelsConfig(BaseModel):
    """Top-level configuration loaded from models.yaml."""

    providers: dict[str, ProviderConfig]
    agent_models: dict[str, str | None] = {}
