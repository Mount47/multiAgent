"""Team builder - assembles SelectorGroupChat from agents and state machine."""

from __future__ import annotations

import logging

from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import SelectorGroupChat

from src.agents.factory import AgentFactory
from src.models.factory import ModelClientFactory
from src.orchestration.selector import create_workflow_selector
from src.orchestration.state_machine import WorkflowStateMachine

logger = logging.getLogger(__name__)


async def build_team(
    model_factory: ModelClientFactory | None = None,
) -> SelectorGroupChat:
    """Build a SelectorGroupChat team with all agents and custom workflow selector.

    Args:
        model_factory: Optional pre-configured model factory.
            If None, creates one from default config.

    Returns:
        A configured SelectorGroupChat ready to run.
    """
    if model_factory is None:
        model_factory = ModelClientFactory()

    # Create all agents
    agent_factory = AgentFactory(model_factory)
    agents = agent_factory.create_all()

    logger.info("Created agents: %s", list(agents.keys()))

    # Build state machine from config
    state_machine = WorkflowStateMachine.from_yaml()

    # Create custom selector function
    selector_func = create_workflow_selector(state_machine)

    # Termination conditions
    termination = (
        TextMentionTermination("APPROVED")
        | MaxMessageTermination(state_machine.max_rounds)
    )

    # Build the team
    # SelectorGroupChat requires a model_client for fallback speaker selection
    # Our selector_func always returns a concrete agent name, so fallback
    # is never exercised, but the parameter is required by the API
    team = SelectorGroupChat(
        participants=list(agents.values()),
        model_client=model_factory.get_client(
            list(model_factory.config.providers.keys())[0]
        ),
        selector_func=selector_func,
        termination_condition=termination,
    )

    logger.info("Team built with %d agents", len(agents))
    return team
