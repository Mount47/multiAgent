"""Agent factory - creates all agents from configuration."""

from __future__ import annotations

import logging
import os

from autogen_agentchat.agents import AssistantAgent

from src.agents.architect import create_architect
from src.agents.base import load_system_prompt
from src.agents.coder import create_coder
from src.agents.product_manager import create_product_manager
from src.agents.reviewer import create_reviewer
from src.agents.tester import create_tester
from src.models.factory import ModelClientFactory

logger = logging.getLogger(__name__)

# Map role names to their creator functions
_AGENT_CREATORS = {
    "product_manager": create_product_manager,
    "architect": create_architect,
    "coder": create_coder,
    "tester": create_tester,
    "reviewer": create_reviewer,
}

# Roles that use tools — only relevant when model supports function_calling
_TOOL_ROLES = {"coder", "tester", "architect"}


class AgentFactory:
    """Creates all agents with their assigned model clients."""

    def __init__(self, model_factory: ModelClientFactory):
        self._model_factory = model_factory

    def _supports_tools(self, role: str) -> bool:
        """Check if the model assigned to this role supports function calling."""
        if role not in _TOOL_ROLES:
            return False
        try:
            config = self._model_factory.config
            provider_name = config.agent_models.get(role)
            if provider_name is None:
                provider_name = os.environ.get("DEFAULT_MODEL", "deepseek-chat")
            provider = config.providers.get(provider_name)
            if provider and not provider.model_info.function_calling:
                return False
        except Exception:
            pass
        return True

    def create_agent(self, role: str) -> AssistantAgent:
        """Create a single agent by role name.

        If the assigned model does not support function calling,
        the agent is created without tools (degraded mode).
        """
        if role not in _AGENT_CREATORS:
            available = ", ".join(_AGENT_CREATORS.keys())
            raise ValueError(f"Unknown agent role: {role}. Available: {available}")

        model_client = self._model_factory.get_client_for_agent(role)

        if role in _TOOL_ROLES and not self._supports_tools(role):
            logger.warning(
                "Model for role '%s' does not support function_calling - "
                "creating agent without tools (degraded mode)",
                role,
            )
            return AssistantAgent(
                name=role,
                model_client=model_client,
                system_message=load_system_prompt(role)
                + "\n\nNOTE: You do not have access to tools. "
                "Write code directly in your response using markdown code blocks.",
            )

        creator = _AGENT_CREATORS[role]
        return creator(model_client)

    def create_all(self) -> dict[str, AssistantAgent]:
        """Create all agents and return them as a dict keyed by role name."""
        return {role: self.create_agent(role) for role in _AGENT_CREATORS}
