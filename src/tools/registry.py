"""Tool registry - maps agent roles to their available tools."""

from __future__ import annotations

from autogen_core.tools import FunctionTool

from src.tools.code_executor import execute_python_code
from src.tools.dependency_installer import install_dependency
from src.tools.file_manager import read_file, write_file
from src.tools.test_runner import run_tests

# Create FunctionTool instances
execute_code_tool = FunctionTool(
    execute_python_code,
    name="execute_code",
    description="Execute Python code and return the output. Use this to run and test code.",
)

run_tests_tool = FunctionTool(
    run_tests,
    name="run_tests",
    description="Write and execute pytest tests. Pass test_code and optionally source_code.",
)

write_file_tool = FunctionTool(
    write_file,
    name="write_file",
    description="Write content to a file in the workspace. Pass filename and content.",
)

read_file_tool = FunctionTool(
    read_file,
    name="read_file",
    description="Read content from a file in the workspace. Pass filename.",
)

install_dep_tool = FunctionTool(
    install_dependency,
    name="install_dependency",
    description="Install a Python package using pip. Pass the package name.",
)


# Map agent roles to their tools
ROLE_TOOLS: dict[str, list[FunctionTool]] = {
    "product_manager": [],  # No tools - only analyzes requirements
    "architect": [],  # No tools - only designs
    "coder": [execute_code_tool, write_file_tool, read_file_tool, install_dep_tool],
    "tester": [execute_code_tool, run_tests_tool, read_file_tool],
    "reviewer": [],  # No tools - only reviews
}


def get_tools_for_role(role: str) -> list[FunctionTool]:
    """Get the list of tools available to a specific agent role."""
    return ROLE_TOOLS.get(role, [])
