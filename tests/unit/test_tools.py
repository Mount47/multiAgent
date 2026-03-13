"""Tests for file management and dependency installer tools."""

import os
import tempfile

import pytest

from src.tools.dependency_installer import install_dependency
from src.tools.file_manager import read_file, write_file


@pytest.fixture(autouse=True)
def temp_workspace(monkeypatch, tmp_path):
    """Redirect workspace to a temp directory for all tests."""
    monkeypatch.setattr("src.tools.file_manager.settings", type("S", (), {"workspace_dir": str(tmp_path)})())
    return tmp_path


class TestWriteFile:
    def test_write_creates_file(self, tmp_path) -> None:
        result = write_file("hello.py", "print('hi')")
        assert "File written" in result
        assert (tmp_path / "hello.py").exists()
        assert (tmp_path / "hello.py").read_text() == "print('hi')"

    def test_write_overwrites_existing(self, tmp_path) -> None:
        write_file("f.txt", "v1")
        write_file("f.txt", "v2")
        assert (tmp_path / "f.txt").read_text() == "v2"

    def test_rejects_path_traversal(self) -> None:
        result = write_file("../etc/passwd", "bad")
        assert "[ERROR]" in result

    def test_rejects_subdirectory_path(self) -> None:
        result = write_file("sub/file.py", "code")
        assert "[ERROR]" in result


class TestReadFile:
    def test_read_existing_file(self, tmp_path) -> None:
        write_file("test.txt", "hello world")
        content = read_file("test.txt")
        assert content == "hello world"

    def test_read_nonexistent_file(self) -> None:
        result = read_file("nonexistent.py")
        assert "[ERROR]" in result


class TestDependencyInstaller:
    def test_rejects_empty_package(self) -> None:
        result = install_dependency("")
        assert "[ERROR]" in result

    def test_rejects_long_package_name(self) -> None:
        result = install_dependency("a" * 101)
        assert "[ERROR]" in result

    def test_rejects_dangerous_characters(self) -> None:
        for char in [";", "&", "|", "`", "$", "(", ")"]:
            result = install_dependency(f"pkg{char}rm -rf /")
            assert "[ERROR]" in result, f"Should reject '{char}'"
