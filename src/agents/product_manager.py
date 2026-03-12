"""Product Manager agent - requirement analysis."""

from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient

from src.agents.base import load_system_prompt


def create_product_manager(model_client: OpenAIChatCompletionClient) -> AssistantAgent:
    """Create the Product Manager agent."""
    return AssistantAgent(
        name="product_manager",
        description="Analyzes user requirements and produces structured requirement documents.",
        system_message=load_system_prompt("product_manager"),
        model_client=model_client,
    )
