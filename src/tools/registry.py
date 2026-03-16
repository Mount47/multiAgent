"""Tool registry - maps agent roles to their available tools."""

from __future__ import annotations

from autogen_core.tools import FunctionTool

from src.tools.instrumented import (
    execute_code_tool as execute_code_fn,
    install_dependency_tool as install_dependency_fn,
    read_file_tool as read_file_fn,
    run_tests_tool as run_tests_fn,
    save_to_memory_tool as save_to_memory_fn,
    search_memory_tool as search_memory_fn,
    write_file_tool as write_file_fn,
)

# Create FunctionTool instances
execute_code_tool = FunctionTool(
    execute_code_fn,
    name="execute_code",
    description="Execute Python code and return the output. Use this to run and test code.",
)

run_tests_tool = FunctionTool(
    run_tests_fn,
    name="run_tests",
    description="Write and execute pytest tests. Pass test_code and optionally source_code.",
)

write_file_tool = FunctionTool(
    write_file_fn,
    name="write_file",
    description="Write content to a file in the workspace. Pass filename and content.",
)

read_file_tool = FunctionTool(
    read_file_fn,
    name="read_file",
    description="Read content from a file in the workspace. Pass filename.",
)

install_dep_tool = FunctionTool(
    install_dependency_fn,
    name="install_dependency",
    description="Install a Python package using pip. Pass the package name.",
)

search_memory_tool = FunctionTool(
    search_memory_fn,
    name="search_memory",
    description="Search past conversations and code snippets for relevant context.",
)

save_to_memory_tool = FunctionTool(
    save_to_memory_fn,
    name="save_to_memory",
    description="Save important context (conversation or code) to memory for future retrieval.",
)


# Map agent roles to their tools
ROLE_TOOLS: dict[str, list[FunctionTool]] = {
    "product_manager": [],
    "architect": [search_memory_tool],
    "coder": [execute_code_tool, write_file_tool, read_file_tool, install_dep_tool, search_memory_tool, save_to_memory_tool],
    "tester": [execute_code_tool, run_tests_tool, read_file_tool],
    "reviewer": [],
}


def get_tools_for_role(role: str) -> list[FunctionTool]:
    """Get the list of tools available to a specific agent role."""
    return ROLE_TOOLS.get(role, [])
