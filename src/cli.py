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
    from src.health import run_sync_checks
    from src.orchestration.team_builder import build_team

    logger = logging.getLogger("workflow")

    print("\n" + "=" * 60)
    print("  Multi-Agent Software Development System")
    print("=" * 60)

    # Pre-flight health checks
    print("\n[Pre-flight checks]")
    report = run_sync_checks()
    print(report.summary())
    if not report.critical_ok:
        print("\n[ABORT] Critical checks failed. Fix the issues above and retry.")
        return
    print()

    print(f"Task: {task_description}\n")
    print("-" * 60)

    # Build the agent team
    logger.info("Building agent team...")
    team = await build_team()

    # Run the workflow with streaming output
    logger.info("Starting workflow...")
    print()

    stream = team.run_stream(task=task_description)

    try:
        async for event in stream:
            # Display each agent message
            if hasattr(event, "source") and hasattr(event, "content"):
                agent_name = event.source
                content = event.content

                # Color-code by agent role
                colors = {
                    "product_manager": "\033[94m",  # Blue
                    "architect": "\033[95m",  # Magenta
                    "coder": "\033[92m",  # Green
                    "tester": "\033[93m",  # Yellow
                    "reviewer": "\033[96m",  # Cyan
                }
                reset = "\033[0m"
                color = colors.get(agent_name, "")

                print(f"\n{color}{'-' * 50}")
                print(f"  [AGENT: {agent_name.upper()}]")
                print(f"{'-' * 50}{reset}")
                print(content)
    except RuntimeError as exc:
        err_msg = str(exc)
        if "APIConnectionError" in err_msg or "APITimeoutError" in err_msg:
            print("\n[ERROR] LLM connection failed.")
            print("Possible causes: network is unreachable, proxy is not configured, or endpoint is blocked.")
            print("If needed, set HTTP_PROXY/HTTPS_PROXY in this shell and retry.")
            return
        raise

    print("\n" + "=" * 60)
    print("  Workflow Complete")
    print("=" * 60)


def main() -> None:
    """Main CLI entry point."""
    # Windows consoles default to GBK; agent output may contain characters
    # outside it (e.g. accented letters in generated test cases). Without
    # this, print() raises UnicodeEncodeError and tears down the whole event
    # loop (surfacing as CancelledError / "task_done() called too many times").
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

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
