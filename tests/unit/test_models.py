"""Tests for model configuration and factory."""

from pathlib import Path

import pytest

from src.models.config import ModelInfo, ModelsConfig, ProviderConfig


class TestModelInfo:
    def test_defaults(self) -> None:
        info = ModelInfo()
        assert info.vision is False
        assert info.function_calling is True
        assert info.json_output is True
        assert info.family == "unknown"

    def test_custom_values(self) -> None:
        info = ModelInfo(vision=True, family="gpt-4")
        assert info.vision is True
        assert info.family == "gpt-4"


class TestProviderConfig:
    def test_minimal(self) -> None:
        p = ProviderConfig(model="gpt-4", base_url="https://api.openai.com/v1")
        assert p.model == "gpt-4"
        assert p.temperature == 0.3
        assert p.api_key_env == ""

    def test_full(self) -> None:
        p = ProviderConfig(
            model="deepseek-chat",
            base_url="https://api.deepseek.com/v1",
            api_key_env="DEEPSEEK_API_KEY",
            temperature=0.7,
            model_info=ModelInfo(family="deepseek"),
        )
        assert p.api_key_env == "DEEPSEEK_API_KEY"
        assert p.temperature == 0.7
        assert p.model_info.family == "deepseek"


class TestModelsConfig:
    def test_loading_yaml(self) -> None:
        """Verify models.yaml can be loaded into ModelsConfig."""
        import yaml

        config_path = Path(__file__).parent.parent.parent / "config" / "models.yaml"
        with open(config_path, "r") as f:
            raw = yaml.safe_load(f)

        providers = {}
        for name, cfg in raw["providers"].items():
            providers[name] = ProviderConfig(**cfg)

        config = ModelsConfig(
            providers=providers,
            agent_models=raw.get("agent_models", {}),
        )
        assert len(config.providers) >= 1
        assert "agent_models" in raw or len(config.agent_models) == 0
