"""Reviewer agent - code review with structured APPROVE/REVISE verdict.

This is a custom BaseChatAgent because it needs to produce structured output
with an explicit verdict that drives the state machine transition.
"""

from __future__ import annotations

import logging
from typing import Sequence

from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient

from src.agents.base import load_system_prompt

logger = logging.getLogger(__name__)


def create_reviewer(model_client: OpenAIChatCompletionClient) -> AssistantAgent:
    """Create the Reviewer agent.

    Uses AssistantAgent with a carefully designed system prompt that ensures
    the reviewer always ends with APPROVED or REVISE verdict.
    The state machine parses this verdict from the message content.
    """
    return AssistantAgent(
        name="reviewer",
        description=(
            "Reviews code quality and correctness. "
            "Always ends response with APPROVED or REVISE verdict."
        ),
        system_message=load_system_prompt("reviewer"),
        model_client=model_client,
    )
