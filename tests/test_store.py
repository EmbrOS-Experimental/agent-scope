"""Tests for the trace store."""

from __future__ import annotations

from agentscope.core.models import AgentRun, EventType, TraceEvent
from agentscope.core.store import AgentStore


def test_save_and_load_run(tmp_storage: AgentStore, completed_run: AgentRun):
    tmp_storage.save_run(completed_run)
    loaded = tmp_storage.load_run(completed_run.id)
    
    assert loaded is not None
    assert loaded.id == completed_run.id
    assert loaded.title == completed_run.title
    assert loaded.status == completed_run.status
    assert len(loaded.events) == len(completed_run.events)
    assert loaded.summary.total_events == completed_run.summary.total_events


def test_load_nonexistent_run(tmp_storage: AgentStore):
    result = tmp_storage.load_run("nonexistent-id-12345")
    assert result is None


def test_list_runs(tmp_storage: AgentStore, completed_run: AgentRun):
    tmp_storage.save_run(completed_run)
    runs = tmp_storage.list_runs()
    
    assert len(runs) >= 1
    assert any(r.id == completed_run.id for r in runs)


def test_list_runs_filter_by_status(tmp_storage: AgentStore, completed_run: AgentRun):
    tmp_storage.save_run(completed_run)
    
    completed = tmp_storage.list_runs(status="completed")
    assert all(r.status == "completed" for r in completed)
    
    failed = tmp_storage.list_runs(status="failed")
    assert len(failed) == 0


def test_list_runs_filter_by_agent_type(tmp_storage: AgentStore, completed_run: AgentStore):
    tmp_storage.save_run(completed_run)
    
    test_runs = tmp_storage.list_runs(agent_type="test")
    assert all(r.agent_type == "test" for r in test_runs)
    
    other = tmp_storage.list_runs(agent_type="aider")
    assert len(other) == 0


def test_list_runs_pagination(tmp_storage: AgentStore):
    # Create multiple runs
    for i in range(5):
        run = AgentRun(title=f"run-{i}", agent_type="test")
        run.add_event(TraceEvent(run_id=run.id, event_type=EventType.RUN_START))
        run.finalize("completed")
        tmp_storage.save_run(run)
    
    runs = tmp_storage.list_runs(limit=3)
    assert len(runs) == 3
    
    runs_offset = tmp_storage.list_runs(limit=3, offset=3)
    assert len(runs_offset) == 2


def test_delete_run(tmp_storage: AgentStore, completed_run: AgentRun):
    tmp_storage.save_run(completed_run)
    assert tmp_storage.load_run(completed_run.id) is not None
    
    result = tmp_storage.delete_run(completed_run.id)
    assert result is True
    assert tmp_storage.load_run(completed_run.id) is None


def test_delete_nonexistent_run(tmp_storage: AgentStore):
    result = tmp_storage.delete_run("nonexistent")
    assert result is False


def test_prune_old_runs(tmp_storage: AgentStore):
    import time
    from datetime import datetime, timezone, timedelta
    
    # Create a run
    run = AgentRun(title="old-run", agent_type="test")
    run.finalize("completed")
    tmp_storage.save_run(run)
    
    # Manually set created_at to 60 days ago
    run.created_at = datetime.now(timezone.utc) - timedelta(days=60)
    tmp_storage.save_run(run)
    
    # Prune runs older than 30 days, keep at least 1
    deleted = tmp_storage.prune_old_runs(max_age_days=30, keep_min=1)
    # Should not delete because keep_min=1
    assert deleted == 0


def test_default_storage_dir():
    from agentscope.core.store import get_default_storage_dir
    import platform
    
    path = get_default_storage_dir()
    assert path.exists()
    
    system = platform.system()
    if system == "Windows":
        assert "AgentScope" in str(path)
    elif system == "Darwin":
        assert "Application Support" in str(path)
    else:
        assert ".local" in str(path) or "share" in str(path)
