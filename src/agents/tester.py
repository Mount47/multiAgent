"""Tester agent - test writing and execution."""

from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient

from src.agents.base import load_system_prompt
from src.tools.registry import get_tools_for_role


def create_tester(model_client: OpenAIChatCompletionClient) -> AssistantAgent:
    """Create the Tester agent with test execution tools."""
    return AssistantAgent(
        name="tester",
        description="Writes and executes unit tests for the generated code.",
        system_message=load_system_prompt("tester"),
        model_client=model_client,
        tools=get_tools_for_role("tester"),
        # See coder.py: loop tool calls and finish on a natural text verdict
        # rather than the forced-reflection pass that some providers break on.
        max_tool_iterations=5,
        reflect_on_tool_use=False,
    )
