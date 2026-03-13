"""Tests for tool registry."""

from src.tools.registry import ROLE_TOOLS, get_tools_for_role


class TestRoleTools:
    def test_all_roles_defined(self) -> None:
        expected_roles = {"product_manager", "architect", "coder", "tester", "reviewer"}
        assert set(ROLE_TOOLS.keys()) == expected_roles

    def test_coder_has_execution_tools(self) -> None:
        coder_tools = get_tools_for_role("coder")
        tool_names = {t.name for t in coder_tools}
        assert "execute_code" in tool_names
        assert "write_file" in tool_names
        assert "read_file" in tool_names
        assert "install_dependency" in tool_names

    def test_coder_has_memory_tools(self) -> None:
        coder_tools = get_tools_for_role("coder")
        tool_names = {t.name for t in coder_tools}
        assert "search_memory" in tool_names
        assert "save_to_memory" in tool_names

    def test_tester_has_test_tools(self) -> None:
        tester_tools = get_tools_for_role("tester")
        tool_names = {t.name for t in tester_tools}
        assert "execute_code" in tool_names
        assert "run_tests" in tool_names
        assert "read_file" in tool_names

    def test_architect_has_memory_search(self) -> None:
        arch_tools = get_tools_for_role("architect")
        tool_names = {t.name for t in arch_tools}
        assert "search_memory" in tool_names

    def test_pm_has_no_tools(self) -> None:
        assert get_tools_for_role("product_manager") == []

    def test_reviewer_has_no_tools(self) -> None:
        assert get_tools_for_role("reviewer") == []

    def test_unknown_role_returns_empty(self) -> None:
        assert get_tools_for_role("unknown_role") == []
