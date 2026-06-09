"""Core data models for AgentScope trace events."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


class EventType(str, enum.Enum):
    """Types of trace events captured during an agent run."""
    LLM_REQUEST = "llm_request"
    LLM_RESPONSE = "llm_response"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    FILE_DIFF = "file_diff"
    GIT_STATE = "git_state"
    TEST_RESULT = "test_result"
    APPROVAL_REQUEST = "approval_request"
    APPROVAL_RESPONSE = "approval_response"
    SHELL_COMMAND = "shell_command"
    SHELL_OUTPUT = "shell_output"
    RUN_START = "run_start"
    RUN_END = "run_end"
    ERROR = "error"


class ToolCall(BaseModel):
    """A single tool invocation by the agent."""
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    result: Optional[str] = None
    duration_ms: Optional[float] = None
    error: Optional[str] = None


class FileDiff(BaseModel):
    """A file change captured during the run."""
    file_path: str
    change_type: str  # "added", "modified", "deleted", "renamed"
    diff_text: Optional[str] = None
    lines_added: int = 0
    lines_removed: int = 0


class GitState(BaseModel):
    """Git repository state at a point in time."""
    branch: str = "unknown"
    commit_hash: str = "unknown"
    dirty: bool = False
    untracked_files: list[str] = Field(default_factory=list)


class TestResult(BaseModel):
    """Result of a test execution."""
    test_name: str
    passed: bool
    duration_ms: float = 0.0
    stdout: str = ""
    stderr: str = ""
    error_type: Optional[str] = None


class ApprovalEvent(BaseModel):
    """A human-in-the-loop approval checkpoint."""
    action: str
    description: str
    approved: bool = False
    approver: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TokenUsage(BaseModel):
    """Token and cost tracking for an LLM call."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    model: str = "unknown"


class TraceEvent(BaseModel):
    """A single event in an agent run trace."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    run_id: str
    event_type: EventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sequence: int = 0
    data: dict[str, Any] = Field(default_factory=dict)
    # Typed sub-models stored in data, accessible via helpers
    tool_call: Optional[ToolCall] = None
    file_diff: Optional[FileDiff] = None
    git_state: Optional[GitState] = None
    test_result: Optional[TestResult] = None
    approval: Optional[ApprovalEvent] = None
    token_usage: Optional[TokenUsage] = None
    duration_ms: Optional[float] = None
    error: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunSummary(BaseModel):
    """Summary statistics for a completed agent run."""
    total_events: int = 0
    total_tool_calls: int = 0
    total_file_changes: int = 0
    total_tests: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    total_duration_ms: float = 0.0
    errors_count: int = 0
    approvals_count: int = 0


class AgentRun(BaseModel):
    """A complete agent run with all trace events."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    agent_type: str = "unknown"  # "aider", "continue", "openhands", "langgraph", "custom"
    status: str = "running"  # "running", "completed", "failed", "cancelled"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    working_directory: str = "."
    command: str = ""
    model: str = "unknown"
    events: list[TraceEvent] = Field(default_factory=list)
    summary: RunSummary = Field(default_factory=RunSummary)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def add_event(self, event: TraceEvent) -> None:
        """Add an event and update summary counters."""
        event.run_id = self.id
        event.sequence = len(self.events)
        self.events.append(event)
        self._update_summary(event)

    def _update_summary(self, event: TraceEvent) -> None:
        s = self.summary
        s.total_events += 1
        if event.event_type == EventType.TOOL_CALL:
            s.total_tool_calls += 1
        elif event.event_type == EventType.FILE_DIFF:
            s.total_file_changes += 1
        elif event.event_type == EventType.TEST_RESULT and event.test_result:
            s.total_tests += 1
            if event.test_result.passed:
                s.tests_passed += 1
            else:
                s.tests_failed += 1
        elif event.event_type == EventType.ERROR:
            s.errors_count += 1
        elif event.event_type == EventType.APPROVAL_REQUEST:
            s.approvals_count += 1
        if event.token_usage:
            s.total_tokens += event.token_usage.total_tokens
            s.total_cost_usd += event.token_usage.cost_usd
        if event.duration_ms:
            s.total_duration_ms += event.duration_ms

    def finalize(self, status: str = "completed") -> None:
        self.status = status
        self.completed_at = datetime.now(timezone.utc)
