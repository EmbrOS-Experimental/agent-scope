"""Integration tests — full capture workflow."""

from __future__ import annotations

from agentscope.core.emitter import AgentEmitter
from agentscope.core.models import EventType


def test_full_agent_run_workflow(tmp_path):
    """Simulate a complete agent run from start to finish."""
    emitter = AgentEmitter(storage_dir=str(tmp_path / "traces"))
    
    session = emitter.start_session(
        title="Fix authentication bug #42",
        agent_type="aider",
        model="claude-sonnet-4",
        working_directory="/home/user/myapp",
        tags=["bugfix", "auth"],
    )
    
    # Agent starts analyzing
    session.add_git_state(branch="main", commit_hash="abc1234", dirty=False)
    
    # LLM call 1: understand the bug
    session.add_llm_call(
        model="claude-sonnet-4",
        prompt="Analyze the authentication bug in src/auth.py",
        response="The bug is in the token validation logic...",
        prompt_tokens=500,
        completion_tokens=200,
        cost_usd=0.015,
        duration_ms=2500.0,
    )
    
    # Shell command: look at the file
    session.add_shell_command(
        command="cat src/auth.py",
        output="def validate_token(token): ...",
        exit_code=0,
        duration_ms=50.0,
    )
    
    # LLM call 2: plan the fix
    session.add_llm_call(
        model="claude-sonnet-4",
        prompt="Plan the fix",
        response="We need to add null check before token.decode()",
        prompt_tokens=800,
        completion_tokens=150,
        cost_usd=0.021,
        duration_ms=1800.0,
    )
    
    # Tool call: apply the fix
    session.add_tool_call(
        tool_name="str_replace_editor",
        arguments={"command": "str_replace", "path": "src/auth.py", "old_str": "token.decode()", "new_str": "token.decode() if token else None"},
        result="File updated successfully",
        duration_ms=300.0,
    )
    
    # File diff captured
    session.add_file_diff(
        file_path="src/auth.py",
        change_type="modified",
        diff_text="@@ -42,3 +42,3 @@\n-    token.decode()\n+    token.decode() if token else None",
        lines_added=1,
        lines_removed=1,
    )
    
    # Git state after edit
    session.add_git_state(branch="main", commit_hash="abc1234", dirty=True)
    
    # Run tests
    session.add_shell_command(
        command="pytest tests/test_auth.py -v",
        output="3 passed in 0.5s",
        exit_code=0,
        duration_ms=500.0,
    )
    
    session.add_test_result("test_validate_token_valid", True, duration_ms=120.0)
    session.add_test_result("test_validate_token_null", True, duration_ms=80.0)
    session.add_test_result("test_validate_token_expired", True, duration_ms=100.0)
    
    # Approval checkpoint
    session.add_approval(
        action="commit changes",
        description="Commit the auth fix",
        approved=True,
        approver="robert",
    )
    
    # Finalize
    run = session.end("completed")
    
    # Verify
    assert run.status == "completed"
    assert run.summary.total_events >= 12
    assert run.summary.total_tool_calls == 1
    assert run.summary.total_file_changes == 1
    assert run.summary.total_tests == 3
    assert run.summary.tests_passed == 3
    assert run.summary.total_tokens == 1650  # 500+200+800+150
    assert abs(run.summary.total_cost_usd - 0.036) < 0.001
    # Check that events have duration (from LLM calls etc.)
    event_durations = [e.duration_ms for e in run.events if e.duration_ms]
    assert len(event_durations) > 0
    assert len(run.tags) == 2
    assert "bugfix" in run.tags


def test_failed_run_workflow(tmp_path):
    """Simulate a run that fails."""
    emitter = AgentEmitter(storage_dir=str(tmp_path / "traces"))
    
    session = emitter.start_session(
        title="Add payment integration",
        agent_type="aider",
        model="gpt-4",
    )
    
    session.add_llm_call("gpt-4", "Add Stripe", "Here's the code...", 300, 100, 0.012)
    session.add_tool_call("bash", {"cmd": "npm install stripe"}, error="npm ERR! network timeout")
    session.add_error("Failed to install dependencies")
    
    run = session.end("failed")
    
    assert run.status == "failed"
    assert run.summary.errors_count >= 1


def test_multiple_sessions(tmp_path):
    """Test creating multiple sessions."""
    emitter = AgentEmitter(storage_dir=str(tmp_path / "traces"))
    
    runs = []
    for i in range(3):
        session = emitter.start_session(title=f"Run {i}", agent_type="test")
        session.add_llm_call("gpt-4", f"prompt-{i}", f"response-{i}", 10, 5, 0.001)
        run = session.end("completed")
        runs.append(run)
    
    # All should be saved
    store = emitter._store
    listed = store.list_runs(limit=10)
    assert len(listed) == 3
    
    # Each should be loadable
    for run in runs:
        loaded = store.load_run(run.id)
        assert loaded is not None
        assert loaded.title == run.title
