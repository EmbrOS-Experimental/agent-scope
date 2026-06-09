"""Local trace storage — filesystem-based with JSON, SQLite optional."""

from __future__ import annotations

import json
import os
import platform
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from agentscope.core.models import AgentRun, RunSummary, TraceEvent, EventType
from agentscope.core.redaction import RedactionPipeline

import logging

logger = logging.getLogger(__name__)


def get_default_storage_dir() -> Path:
    """Get the default storage directory for AgentScope traces.
    
    Cross-platform:
    - Windows: %LOCALAPPDATA%/AgentScope/traces
    - macOS: ~/Library/Application Support/AgentScope/traces
    - Linux: ~/.local/share/agentscope/traces
    """
    system = platform.system()
    if system == "Windows":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif system == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    
    storage = base / "AgentScope" / "traces"
    storage.mkdir(parents=True, exist_ok=True)
    return storage


class AgentStore:
    """Stores and retrieves agent run traces."""

    def __init__(
        self,
        storage_dir: Optional[Path] = None,
        redaction: Optional[RedactionPipeline] = None,
    ):
        self.storage_dir = storage_dir or get_default_storage_dir()
        self.redaction = redaction or RedactionPipeline()
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _run_dir(self, run_id: str) -> Path:
        return self.storage_dir / run_id

    def _run_meta_path(self, run_id: str) -> Path:
        return self._run_dir(run_id) / "run.json"

    def _events_path(self, run_id: str) -> Path:
        return self._run_dir(run_id) / "events.jsonl"

    def save_run(self, run: AgentRun) -> Path:
        """Save a complete run to disk."""
        run_dir = self._run_dir(run.id)
        run_dir.mkdir(parents=True, exist_ok=True)

        # Save metadata
        meta_path = self._run_meta_path(run.id)
        meta_path.write_text(run.model_dump_json(indent=2), encoding="utf-8")

        # Save events as JSONL
        events_path = self._events_path(run.id)
        with open(events_path, "w", encoding="utf-8") as f:
            for event in run.events:
                f.write(event.model_dump_json() + "\n")

        logger.info(f"Saved run {run.id} to {run_dir}")
        return run_dir

    def load_run(self, run_id: str) -> Optional[AgentRun]:
        """Load a run from disk."""
        run_dir = self._run_dir(run_id)
        meta_path = self._run_meta_path(run_id)
        events_path = self._events_path(run_id)

        if not meta_path.exists():
            logger.warning(f"Run {run_id} not found")
            return None

        run = AgentRun.model_validate_json(meta_path.read_text(encoding="utf-8"))

        # Load events
        if events_path.exists():
            events = []
            for line in events_path.read_text(encoding="utf-8").strip().split("\n"):
                if line.strip():
                    events.append(TraceEvent.model_validate_json(line))
            run.events = events

        return run

    def list_runs(
        self,
        agent_type: Optional[str] = None,
        status: Optional[str] = None,
        tags: Optional[list[str]] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AgentRun]:
        """List runs with optional filtering."""
        runs = []
        run_dirs = sorted(
            [d for d in self.storage_dir.iterdir() if d.is_dir()],
            key=lambda d: d.stat().st_mtime,
            reverse=True,
        )

        for run_dir in run_dirs:
            meta_path = run_dir / "run.json"
            if not meta_path.exists():
                continue

            try:
                run = AgentRun.model_validate_json(
                    meta_path.read_text(encoding="utf-8")
                )
            except Exception:
                continue

            # Apply filters
            if agent_type and run.agent_type != agent_type:
                continue
            if status and run.status != status:
                continue
            if tags and not all(t in run.tags for t in tags):
                continue

            runs.append(run)

        return runs[offset : offset + limit]

    def delete_run(self, run_id: str) -> bool:
        """Delete a run and all its data."""
        run_dir = self._run_dir(run_id)
        if run_dir.exists():
            shutil.rmtree(run_dir)
            logger.info(f"Deleted run {run_id}")
            return True
        return False

    def prune_old_runs(self, max_age_days: int = 30, keep_min: int = 5) -> int:
        """Remove runs older than max_age_days, keeping at least keep_min."""
        cutoff = datetime.now(timezone.utc).timestamp() - (max_age_days * 86400)
        runs = self.list_runs(limit=10000)
        
        deleted = 0
        kept = 0
        for run in sorted(runs, key=lambda r: r.created_at):
            if kept < keep_min:
                kept += 1
                continue
            if run.created_at.timestamp() < cutoff:
                if self.delete_run(run.id):
                    deleted += 1
        return deleted
