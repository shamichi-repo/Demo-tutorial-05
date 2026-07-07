"""Tests for agent file structure and module validity."""

import pytest


@pytest.mark.structure
class TestRequiredFiles:
    """Test that all required files exist."""

    def test_agent_directory_exists(self, agent_path):
        assert agent_path.exists(), f"Agent directory not found: {agent_path}"
        assert agent_path.is_dir(), f"Agent path is not a directory: {agent_path}"

    def test_app_directory_exists(self, agent_app_path):
        assert agent_app_path.exists(), f"App directory not found: {agent_app_path}"
        assert agent_app_path.is_dir(), f"App path is not a directory: {agent_app_path}"

    def test_requirements_txt_exists(self, agent_path):
        req_file = agent_path / "requirements.txt"
        assert req_file.exists(), "requirements.txt is missing"
        assert req_file.stat().st_size > 0, "requirements.txt is empty"

    def test_agent_py_exists(self, agent_app_path):
        agent_file = agent_app_path / "agent.py"
        assert agent_file.exists(), "agent.py is missing"

    def test_main_py_exists(self, agent_app_path):
        main_file = agent_app_path / "main.py"
        assert main_file.exists(), "main.py is missing"

    def test_mcp_tools_py_exists(self, agent_app_path):
        mcp_file = agent_app_path / "mcp_tools.py"
        assert mcp_file.exists(), "mcp_tools.py is missing"

    def test_agent_executor_py_exists(self, agent_app_path):
        exe_file = agent_app_path / "agent_executor.py"
        assert exe_file.exists(), "agent_executor.py is missing"
