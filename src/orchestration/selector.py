"""Selector function for SelectorGroupChat.

Bridges AutoGen's SelectorGroupChat with our custom WorkflowStateMachine.
"""

from __future__ import annotations

import logging
from typing import Sequence

from autogen_agentchat.messages import BaseChatMessage, TextMessage

from src.orchestration.state_machine import WorkflowStateMachine

logger = logging.getLogger(__name__)


def create_workflow_selector(state_machine: WorkflowStateMachine):
    """Create a selector_func for SelectorGroupChat driven by the state machine.

    The returned function has the signature required by SelectorGroupChat:
        (messages: Sequence[...]) -> str | None

    Returns:
        A selector function that determines the next speaking agent.
    """

    def selector_func(messages: Sequence[BaseChatMessage]) -> str | None:
        # First message: always start with product_manager
        if not messages:
            return "product_manager"

        # Extract content from the last message
        last_message = messages[-1]
        if isinstance(last_message, TextMessage):
            content = last_message.content
        elif hasattr(last_message, "content"):
            content = str(last_message.content)
        else:
            content = ""

        # Advance state machine based on last message
        next_agent = state_machine.advance(content)

        if next_agent is None:
            logger.info("Workflow complete - no next agent")
            return None

        logger.info("Selector chose next agent: %s", next_agent)
        return next_agent

    return selector_func
