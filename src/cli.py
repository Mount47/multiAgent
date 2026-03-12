"""CLI entry point - run the multi-agent development workflow."""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

# Ensure project root is in path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load .env file
load_dotenv(project_root / ".env")


def setup_logging(level: str = "INFO") -> None:
    """Configure structured logging."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )


async def run_workflow(task_description: str) -> None:
    """Run the full multi-agent development workflow for a given task."""
    from src.orchestration.team_builder import build_team

    logger = logging.getLogger("workflow")

    print("\n" + "=" * 60)
    print("  Multi-Agent Software Development System")
    print("=" * 60)
    print(f"\n📋 Task: {task_description}\n")
    print("-" * 60)

    # Build the agent team
    logger.info("Building agent team...")
    team = await build_team()

    # Run the workflow with streaming output
    logger.info("Starting workflow...")
    print()

    stream = team.run_stream(task=task_description)

    async for event in stream:
        # Display each agent message
        if hasattr(event, "source") and hasattr(event, "content"):
            agent_name = event.source
            content = event.content

            # Color-code by agent role
            colors = {
                "product_manager": "\033[94m",  # Blue
                "architect": "\033[95m",        # Magenta
                "coder": "\033[92m",            # Green
                "tester": "\033[93m",           # Yellow
                "reviewer": "\033[96m",         # Cyan
            }
            reset = "\033[0m"
            color = colors.get(agent_name, "")

            print(f"\n{color}{'─' * 50}")
            print(f"  🤖 [{agent_name.upper()}]")
            print(f"{'─' * 50}{reset}")
            print(content)

    print("\n" + "=" * 60)
    print("  ✅ Workflow Complete!")
    print("=" * 60)


def main() -> None:
    """Main CLI entry point."""
    setup_logging()

    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
    else:
        print("\nMulti-Agent Software Development System")
        print("-" * 40)
        task = input("\nEnter your development task:\n> ").strip()

    if not task:
        print("Error: No task provided.")
        sys.exit(1)

    asyncio.run(run_workflow(task))


if __name__ == "__main__":
    main()
