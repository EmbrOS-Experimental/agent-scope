"""Tests for the emitter and session."""

from __future__ import annotations

from agentscope.core.emitter import AgentEmitter, AgentScopeSession
from agentscope.core.models import EventType


def test_session_start(session: AgentScopeSession):
    assert session.run.status == "running"
    assert len(session.run.events) == 1
    assert session.run.events[0].event_type == EventType.RUN_START


def test_session_end(session: AgentScopeSession):
    run = session.end("completed")
    assert run.status == "completed"
    assert run.completed_at is not None
    assert run.summary.total_events >= 2  # start + end


def test_add_llm_call(session: AgentScopeSession):
    event = session.add_llm_call(
        model="gpt-4",
        prompt="Hello",
        response="Hi!",
        prompt_tokens=10,
        completion_tokens=5,
        cost_usd=0.003,
    )
    assert event.event_type == EventType.LLM_RESPONSE
    assert event.token_usage is not None
    assert event.token_usage.total_tokens == 15
    assert event.token_usage.cost_usd == 0.003


def test_add_tool_call(session: AgentScopeSession):
    event = session.add_tool_call(
        tool_name="bash",
        arguments={"cmd": "ls -la"},
        result="file1.py\nfile2.py",
        duration_ms=150.0,
    )
    assert event.event_type == EventType.TOOL_CALL
    assert event.tool_call is not None
    assert event.tool_call.tool_name == "bash"
    assert event.tool_call.result == "file1.py\nfile2.py"
    assert event.duration_ms == 150.0


def test_add_tool_call_with_error(session: AgentScopeSession):
    event = session.add_tool_call(
        tool_name="bash",
        arguments={"cmd": "rm -rf /"},
        error="Permission denied",
    )
    assert event.error == "Permission denied"
    assert event.tool_call.error == "Permission denied"


def test_add_file_diff(session: AgentScopeSession):
    event = session.add_file_diff(
        file_path="src/auth.py",
        change_type="modified",
        diff_text="@@ -10,5 +10,8 @@",
        lines_added=3,
        lines_removed=1,
    )
    assert event.event_type == EventType.FILE_DIFF
    assert event.file_diff.file_path == "src/auth.py"
    assert event.file_diff.lines_added == 3


def test_add_git_state(session: AgentScopeSession):
    event = session.add_git_state(
        branch="feature/auth",
        commit_hash="deadbeef",
        dirty=True,
        untracked_files=["temp.py"],
    )
    assert event.event_type == EventType.GIT_STATE
    assert event.git_state.branch == "feature/auth"
    assert event.git_state.dirty is True


def test_add_test_result(session: AgentScopeSession):
    event = session.add_test_result(
        test_name="test_login",
        passed=True,
        duration_ms=125.5,
        stdout="OK",
    )
    assert event.event_type == EventType.TEST_RESULT
    assert event.test_result.passed is True
    assert event.test_result.duration_ms == 125.5


def test_add_approval(session: AgentScopeSession):
    event = session.add_approval(
        action="deploy",
        description="Deploy to production",
        approved=True,
        approver="robert",
    )
    assert event.event_type == EventType.APPROVAL_REQUEST
    assert event.approval.approved is True
    assert event.approval.approver == "robert"


def test_add_shell_command(session: AgentScopeSession):
    event = session.add_shell_command(
        command="pytest tests/ -v",
        output="5 passed in 2.3s",
        exit_code=0,
        duration_ms=2300.0,
    )
    assert event.event_type == EventType.SHELL_COMMAND
    assert event.data["exit_code"] == 0


def test_add_error(session: AgentScopeSession):
    event = session.add_error("Something went wrong", context="during tool call")
    assert event.event_type == EventType.ERROR
    assert event.error == "Something went wrong"


def test_llm_call_context_manager(session: AgentScopeSession):
    import time
    
    with session.llm_call(model="gpt-4") as call:
        time.sleep(0.01)  # Simulate some work
        call.set_response("Hello!", prompt="Hi", prompt_tokens=5, completion_tokens=3)
    
    # Check that an LLM_RESPONSE event was added
    llm_events = [e for e in session.run.events if e.event_type == EventType.LLM_RESPONSE]
    assert len(llm_events) == 1
    assert llm_events[0].token_usage.total_tokens == 8
    assert llm_events[0].duration_ms is not None
    assert llm_events[0].duration_ms >= 10  # At least 10ms


def test_emitter_creates_session(emitter: AgentEmitter):
    session = emitter.start_session(
        title="My test run",
        agent_type="aider",
        model="claude-sonnet-4",
    )
    assert session.run.title == "My test run"
    assert session.run.agent_type == "aider"
    assert session.run.model == "claude-sonnet-4"
    assert session.run.status == "running"


def test_session_auto_save(session: AgentScopeSession, tmp_storage: AgentStore):
    session.add_llm_call("gpt-4", "test", "response", 5, 3, 0.001)
    run = session.end("completed")
    
    # Should be auto-saved
    loaded = tmp_storage.load_run(run.id)
    assert loaded is not None
    assert loaded.id == run.id


def test_summary_updates_on_each_event(session: AgentScopeSession):
    initial = session.run.summary.total_events
    
    session.add_llm_call("gpt-4", "a", "b", 1, 1, 0.001)
    assert session.run.summary.total_events == initial + 1
    assert session.run.summary.total_tokens == 2
    
    session.add_tool_call("bash", {"cmd": "ls"})
    assert session.run.summary.total_tool_calls == 1
    
    session.add_file_diff("test.py", "modified")
    assert session.run.summary.total_file_changes == 1
    
    session.add_error("oops")
    assert session.run.summary.errors_count == 1
