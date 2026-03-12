"""Agent factory - creates all agents from configuration."""

from __future__ import annotations

from autogen_agentchat.agents import AssistantAgent

from src.agents.architect import create_architect
from src.agents.coder import create_coder
from src.agents.product_manager import create_product_manager
from src.agents.reviewer import create_reviewer
from src.agents.tester import create_tester
from src.models.factory import ModelClientFactory

# Map role names to their creator functions
_AGENT_CREATORS = {
    "product_manager": create_product_manager,
    "architect": create_architect,
    "coder": create_coder,
    "tester": create_tester,
    "reviewer": create_reviewer,
}


class AgentFactory:
    """Creates all agents with their assigned model clients."""

    def __init__(self, model_factory: ModelClientFactory):
        self._model_factory = model_factory

    def create_agent(self, role: str) -> AssistantAgent:
        """Create a single agent by role name."""
        if role not in _AGENT_CREATORS:
            available = ", ".join(_AGENT_CREATORS.keys())
            raise ValueError(f"Unknown agent role: {role}. Available: {available}")

        model_client = self._model_factory.get_client_for_agent(role)
        creator = _AGENT_CREATORS[role]
        return creator(model_client)

    def create_all(self) -> dict[str, AssistantAgent]:
        """Create all agents and return them as a dict keyed by role name."""
        return {role: self.create_agent(role) for role in _AGENT_CREATORS}
