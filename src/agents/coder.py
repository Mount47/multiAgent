"""Coder agent - code generation with tool access."""

from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient

from src.agents.base import load_system_prompt
from src.tools.registry import get_tools_for_role


def create_coder(model_client: OpenAIChatCompletionClient) -> AssistantAgent:
    """Create the Coder agent with code execution tools."""
    return AssistantAgent(
        name="coder",
        description="Writes Python code based on requirements and architecture design.",
        system_message=load_system_prompt("coder"),
        model_client=model_client,
        tools=get_tools_for_role("coder"),
        reflect_on_tool_use=True,  # Agent reviews tool output before responding
    )
