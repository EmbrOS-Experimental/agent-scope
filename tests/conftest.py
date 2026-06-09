"""Shared test fixtures."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from agentscope.core.emitter import AgentEmitter, AgentScopeSession
from agentscope.core.models import (
    AgentRun,
    EventType,
    FileDiff,
    GitState,
    TestResult,
    TokenUsage,
    TraceEvent,
)
from agentscope.core.redaction import RedactionPipeline
from agentscope.core.store import AgentStore


@pytest.fixture
def tmp_storage(tmp_path: Path) -> AgentStore:
    """Create a temporary AgentStore."""
    return AgentStore(storage_dir=tmp_path / "traces")


@pytest.fixture
def emitter(tmp_storage: AgentStore) -> AgentEmitter:
    """Create an AgentEmitter with temp storage."""
    return AgentEmitter(storage_dir=str(tmp_storage.storage_dir))


@pytest.fixture
def session(emitter: AgentEmitter) -> AgentScopeSession:
    """Create a started session for testing."""
    s = emitter.start_session(
        title="Test run",
        agent_type="test",
        model="test-model",
        working_directory="/tmp",
    )
    return s


@pytest.fixture
def completed_run(session: AgentScopeSession) -> AgentRun:
    """Create a completed run with sample events."""
    session.add_llm_call("gpt-4", "Hello", "Hi there!", 10, 5, 0.003)
    session.add_tool_call("bash", {"cmd": "ls"}, result="file1.py\nfile2.py")
    session.add_file_diff("src/main.py", "modified", lines_added=5, lines_removed=2)
    session.add_git_state(branch="main", commit_hash="abc123", dirty=True)
    session.add_test_result("test_login", True, duration_ms=150.0)
    session.add_test_result("test_logout", False, duration_ms=200.0, error_type="AssertionError")
    session.add_shell_command("pytest tests/", output="5 passed", exit_code=0)
    session.add_approval("deploy to prod", "Deploy the latest changes", approved=True)
    return session.end("completed")


@pytest.fixture
def redaction() -> RedactionPipeline:
    """Create a RedactionPipeline."""
    return RedactionPipeline()
