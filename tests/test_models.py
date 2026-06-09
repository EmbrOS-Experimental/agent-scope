"""Tests for core data models."""

from __future__ import annotations

from agentscope.core.models import (
    AgentRun,
    EventType,
    FileDiff,
    GitState,
    RunSummary,
    TestResult,
    TokenUsage,
    TraceEvent,
    ToolCall,
)


def test_trace_event_creation():
    event = TraceEvent(
        run_id="test-123",
        event_type=EventType.LLM_RESPONSE,
        data={"model": "gpt-4"},
    )
    assert event.run_id == "test-123"
    assert event.event_type == EventType.LLM_RESPONSE
    assert event.id is not None
    assert event.timestamp is not None


def test_agent_run_add_event_updates_summary():
    run = AgentRun(title="test", agent_type="test")
    
    run.add_event(TraceEvent(
        run_id=run.id,
        event_type=EventType.TOOL_CALL,
        tool_call=ToolCall(tool_name="bash", arguments={"cmd": "ls"}),
    ))
    assert run.summary.total_events == 1
    assert run.summary.total_tool_calls == 1

    run.add_event(TraceEvent(
        run_id=run.id,
        event_type=EventType.FILE_DIFF,
        file_diff=FileDiff(file_path="test.py", change_type="modified"),
    ))
    assert run.summary.total_file_changes == 1

    run.add_event(TraceEvent(
        run_id=run.id,
        event_type=EventType.TEST_RESULT,
        test_result=TestResult(test_name="test_a", passed=True),
    ))
    assert run.summary.total_tests == 1
    assert run.summary.tests_passed == 1
    assert run.summary.tests_failed == 0

    run.add_event(TraceEvent(
        run_id=run.id,
        event_type=EventType.TEST_RESULT,
        test_result=TestResult(test_name="test_b", passed=False),
    ))
    assert run.summary.total_tests == 2
    assert run.summary.tests_failed == 1


def test_agent_run_token_tracking():
    run = AgentRun(title="test")
    
    run.add_event(TraceEvent(
        run_id=run.id,
        event_type=EventType.LLM_RESPONSE,
        token_usage=TokenUsage(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            cost_usd=0.005,
            model="gpt-4",
        ),
    ))
    assert run.summary.total_tokens == 150
    assert run.summary.total_cost_usd == 0.005

    run.add_event(TraceEvent(
        run_id=run.id,
        event_type=EventType.LLM_RESPONSE,
        token_usage=TokenUsage(
            prompt_tokens=200,
            completion_tokens=100,
            total_tokens=300,
            cost_usd=0.01,
            model="gpt-4",
        ),
    ))
    assert run.summary.total_tokens == 450
    assert run.summary.total_cost_usd == 0.015


def test_agent_run_finalize():
    run = AgentRun(title="test")
    run.finalize("completed")
    assert run.status == "completed"
    assert run.completed_at is not None


def test_run_summary_defaults():
    s = RunSummary()
    assert s.total_events == 0
    assert s.total_tool_calls == 0
    assert s.total_cost_usd == 0.0


def test_tool_call_model():
    tc = ToolCall(tool_name="bash", arguments={"cmd": "ls"}, result="output")
    assert tc.tool_name == "bash"
    assert tc.result == "output"
    assert tc.error is None


def test_file_diff_model():
    fd = FileDiff(file_path="src/main.py", change_type="modified", lines_added=5, lines_removed=2)
    assert fd.file_path == "src/main.py"
    assert fd.lines_added == 5


def test_git_state_model():
    gs = GitState(branch="main", commit_hash="abc123", dirty=True, untracked_files=["temp.py"])
    assert gs.branch == "main"
    assert gs.dirty is True
    assert len(gs.untracked_files) == 1


def test_test_result_model():
    tr = TestResult(test_name="test_login", passed=True, duration_ms=150.0)
    assert tr.passed is True
    assert tr.duration_ms == 150.0
