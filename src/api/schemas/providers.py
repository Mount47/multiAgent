"""Schemas for model provider APIs."""

from __future__ import annotations

from pydantic import BaseModel


class ProviderCapabilities(BaseModel):
    """High-level provider capabilities."""

    vision: bool
    function_calling: bool
    json_output: bool
    family: str


class ProviderItem(BaseModel):
    """Provider descriptor."""

    name: str
    model: str
    base_url: str
    capabilities: ProviderCapabilities

