"""Provider discovery route."""

from __future__ import annotations

import os

from fastapi import APIRouter

from src.api.schemas.providers import ProviderCapabilities, ProviderItem
from src.models.factory import ModelClientFactory

router = APIRouter(prefix="/api/providers", tags=["providers"])


@router.get("", response_model=list[ProviderItem])
async def list_providers() -> list[ProviderItem]:
    """List configured model providers and capabilities."""
    factory = ModelClientFactory()
    items: list[ProviderItem] = []
    for name, conf in factory.config.providers.items():
        items.append(
            ProviderItem(
                name=name,
                model=conf.model,
                base_url=conf.base_url,
                capabilities=ProviderCapabilities(
                    vision=conf.model_info.vision,
                    function_calling=conf.model_info.function_calling,
                    json_output=conf.model_info.json_output,
                    family=conf.model_info.family,
                ),
            )
        )
    return items


@router.get("/default")
async def get_default_provider() -> dict[str, str]:
    """Return current default provider name from environment."""
    return {"default_provider": os.getenv("DEFAULT_MODEL", "deepseek-chat")}

