"""Tests for agent adapters."""

from __future__ import annotations

from agentscope.adapters.shims import AiderAdapter, ContinueAdapter
from agentscope.core.models import EventType


def test_aider_adapter_detects_model(session):
    adapter = AiderAdapter(session)
    adapter.parse_and_record("Model: claude-sonnet-4-20250514")
    assert session.run.model == "claude-sonnet-4-20250514"


def test_aider_adapter_detects_shell_command(session):
    adapter = AiderAdapter(session)
    adapter.parse_and_record("$ pytest tests/ -v")
    
    shell_events = [e for e in session.run.events if e.event_type == EventType.SHELL_COMMAND]
    assert len(shell_events) == 1


def test_aider_adapter_detects_file_edit(session):
    adapter = AiderAdapter(session)
    adapter.parse_and_record("Applied edit to src/auth.py")
    
    diff_events = [e for e in session.run.events if e.event_type == EventType.FILE_DIFF]
    assert len(diff_events) == 1
    assert diff_events[0].file_diff.file_path == "src/auth.py"


def test_aider_adapter_detects_error(session):
    adapter = AiderAdapter(session)
    adapter.parse_and_record("Error: File not found")
    
    error_events = [e for e in session.run.events if e.event_type == EventType.ERROR]
    assert len(error_events) == 1


def test_continue_adapter_tool_call(session):
    adapter = ContinueAdapter(session)
    adapter.on_tool_call("bash", {"cmd": "ls -la"})
    
    tool_events = [e for e in session.run.events if e.event_type == EventType.TOOL_CALL]
    assert len(tool_events) == 1
    assert tool_events[0].tool_call.tool_name == "bash"


def test_continue_adapter_tool_result(session):
    adapter = ContinueAdapter(session)
    adapter.on_tool_call("bash", {"cmd": "ls"})
    adapter.on_tool_result("bash", "file1.py\nfile2.py")
    
    tool_events = [e for e in session.run.events if e.event_type == EventType.TOOL_CALL]
    assert tool_events[0].tool_call.result == "file1.py\nfile2.py"


def test_continue_adapter_llm_response(session):
    adapter = ContinueAdapter(session)
    adapter.on_llm_response(
        model="gpt-4",
        prompt="Hello",
        response="Hi there!",
        prompt_tokens=5,
        completion_tokens=3,
    )
    
    llm_events = [e for e in session.run.events if e.event_type == EventType.LLM_RESPONSE]
    assert len(llm_events) == 1
    assert llm_events[0].token_usage.total_tokens == 8
