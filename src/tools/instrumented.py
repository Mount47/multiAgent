"""Async tool wrappers with observability decorators."""

from __future__ import annotations

import asyncio

from src.observability.tool_observer import observe_tool_call
from src.tools.code_executor import execute_python_code
from src.tools.dependency_installer import install_dependency
from src.tools.file_manager import read_file, write_file
from src.tools.memory_tools import save_to_memory, search_memory
from src.tools.test_runner import run_tests


@observe_tool_call("execute_code")
async def execute_code_tool(code: str) -> str:
    return await asyncio.to_thread(execute_python_code, code)


@observe_tool_call("run_tests")
async def run_tests_tool(test_code: str, source_code: str = "") -> str:
    return await asyncio.to_thread(run_tests, test_code, source_code)


@observe_tool_call("write_file")
async def write_file_tool(filename: str, content: str) -> str:
    return await asyncio.to_thread(write_file, filename, content)


@observe_tool_call("read_file")
async def read_file_tool(filename: str) -> str:
    return await asyncio.to_thread(read_file, filename)


@observe_tool_call("install_dependency")
async def install_dependency_tool(package: str) -> str:
    return await asyncio.to_thread(install_dependency, package)


@observe_tool_call("search_memory")
async def search_memory_tool(query: str, n_results: int = 3) -> str:
    return await asyncio.to_thread(search_memory, query, n_results)


@observe_tool_call("save_to_memory")
async def save_to_memory_tool(
    content: str, category: str = "conversation", metadata_str: str = ""
) -> str:
    return await asyncio.to_thread(save_to_memory, content, category, metadata_str)
