"""Architect agent - system design."""

from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient

from src.agents.base import load_system_prompt


def create_architect(model_client: OpenAIChatCompletionClient) -> AssistantAgent:
    """Create the Architect agent."""
    return AssistantAgent(
        name="architect",
        description="Designs system architecture, defines interfaces and tech stack.",
        system_message=load_system_prompt("architect"),
        model_client=model_client,
    )
