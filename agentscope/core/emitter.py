"""Core emitter that captures agent run events."""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import contextmanager
from typing import Any, Generator, Optional

from agentscope.core.models import (
    AgentRun,
    ApprovalEvent,
    EventType,
    FileDiff,
    GitState,
    RunSummary,
    TestResult,
    TokenUsage,
    TraceEvent,
    ToolCall,
)
from agentscope.core.redaction import RedactionPipeline
from agentscope.core.store import AgentStore

logger = logging.getLogger(__name__)


class AgentScopeSession:
    """Active session for capturing a single agent run.

    Usage::

        session = AgentScopeSession(
            title="Fix auth bug",
            agent_type="aider",
            working_directory="/path/to/repo",
            model="claude-sonnet-4",
        )
        session.start()

        with session.llm_call(model="claude-sonnet-4") as call:
            call.set_response(response_text, prompt_tokens=100, completion_tokens=50)

        session.add_tool_call("bash", {"cmd": "pytest"}, result="3 passed")
        session.add_file_diff("src/auth.py", "modified", diff_text="@@ ...")

        run = session.end()
    """

    def __init__(
        self,
        title: str = "",
        agent_type: str = "custom",
        working_directory: str = ".",
        model: str = "unknown",
        command: str = "",
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
        store: Optional[AgentStore] = None,
        redaction: Optional[RedactionPipeline] = None,
        auto_save: bool = True,
    ):
        self.run = AgentRun(
            id=str(uuid.uuid4()),
            title=title,
            agent_type=agent_type,
            working_directory=str(working_directory),
            model=model,
            command=command,
            tags=tags or [],
            metadata=metadata or {},
        )
        self._store = store
        self._redaction = redaction or RedactionPipeline()
        self._auto_save = auto_save
        self._active = False
        self._start_time: float = 0

    def start(self) -> None:
        """Mark the run as started."""
        self._active = True
        self._start_time = time.monotonic()
        event = TraceEvent(
            run_id=self.run.id,
            event_type=EventType.RUN_START,
            data={
                "title": self.run.title,
                "agent_type": self.run.agent_type,
                "model": self.run.model,
                "working_directory": self.run.working_directory,
            },
        )
        self.run.add_event(event)
        logger.info(f"Started run {self.run.id}: {self.run.title}")

    def end(self, status: str = "completed") -> AgentRun:
        """Finalize the run and optionally persist it."""
        self._active = False
        duration = (time.monotonic() - self._start_time) * 1000
        
        # Only set total duration from wall clock if no events had durations
        if self.run.summary.total_duration_ms == 0:
            self.run.summary.total_duration_ms = duration
        
        event = TraceEvent(
            run_id=self.run.id,
            event_type=EventType.RUN_END,
            data={"status": status, "duration_ms": duration},
            duration_ms=duration,
        )
        self.run.add_event(event)
        self.run.finalize(status)

        if self._store and self._auto_save:
            self._store.save_run(self.run)

        logger.info(
            f"Ended run {self.run.id}: {status}, "
            f"{self.run.summary.total_events} events, "
            f"{duration:.0f}ms"
        )
        return self.run

    def add_event(
        self,
        event_type: EventType,
        data: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> TraceEvent:
        """Add a generic event to the run."""
        event = TraceEvent(
            run_id=self.run.id,
            event_type=event_type,
            data=data or {},
            **kwargs,
        )
        event = self._redaction.redact_event(event)
        self.run.add_event(event)
        return event

    def add_llm_call(
        self,
        model: str,
        prompt: str,
        response: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        cost_usd: float = 0.0,
        duration_ms: Optional[float] = None,
    ) -> TraceEvent:
        """Capture an LLM request/response pair."""
        total = prompt_tokens + completion_tokens
        token_usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total,
            cost_usd=cost_usd,
            model=model,
        )

        event = TraceEvent(
            run_id=self.run.id,
            event_type=EventType.LLM_RESPONSE,
            data={
                "model": model,
                "prompt": prompt,
                "response": response,
            },
            token_usage=token_usage,
            duration_ms=duration_ms,
        )
        event = self._redaction.redact_event(event)
        self.run.add_event(event)
        return event

    def add_tool_call(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        result: Optional[str] = None,
        error: Optional[str] = None,
        duration_ms: Optional[float] = None,
    ) -> TraceEvent:
        """Capture a tool call."""
        tool_call = ToolCall(
            tool_name=tool_name,
            arguments=arguments,
            result=result,
            error=error,
            duration_ms=duration_ms,
        )
        event = TraceEvent(
            run_id=self.run.id,
            event_type=EventType.TOOL_CALL,
            data={"tool_name": tool_name},
            tool_call=tool_call,
            duration_ms=duration_ms,
            error=error,
        )
        event = self._redaction.redact_event(event)
        self.run.add_event(event)
        return event

    def add_file_diff(
        self,
        file_path: str,
        change_type: str,
        diff_text: Optional[str] = None,
        lines_added: int = 0,
        lines_removed: int = 0,
    ) -> TraceEvent:
        """Capture a file change."""
        file_diff = FileDiff(
            file_path=file_path,
            change_type=change_type,
            diff_text=diff_text,
            lines_added=lines_added,
            lines_removed=lines_removed,
        )
        event = TraceEvent(
            run_id=self.run.id,
            event_type=EventType.FILE_DIFF,
            data={"file_path": file_path, "change_type": change_type},
            file_diff=file_diff,
        )
        event = self._redaction.redact_event(event)
        self.run.add_event(event)
        return event

    def add_git_state(
        self,
        branch: str = "unknown",
        commit_hash: str = "unknown",
        dirty: bool = False,
        untracked_files: Optional[list[str]] = None,
    ) -> TraceEvent:
        """Capture current git state."""
        git_state = GitState(
            branch=branch,
            commit_hash=commit_hash,
            dirty=dirty,
            untracked_files=untracked_files or [],
        )
        event = TraceEvent(
            run_id=self.run.id,
            event_type=EventType.GIT_STATE,
            data={"branch": branch, "commit_hash": commit_hash},
            git_state=git_state,
        )
        self.run.add_event(event)
        return event

    def add_test_result(
        self,
        test_name: str,
        passed: bool,
        duration_ms: float = 0.0,
        stdout: str = "",
        stderr: str = "",
        error_type: Optional[str] = None,
    ) -> TraceEvent:
        """Capture a test result."""
        test_result = TestResult(
            test_name=test_name,
            passed=passed,
            duration_ms=duration_ms,
            stdout=stdout,
            stderr=stderr,
            error_type=error_type,
        )
        event = TraceEvent(
            run_id=self.run.id,
            event_type=EventType.TEST_RESULT,
            data={"test_name": test_name, "passed": passed},
            test_result=test_result,
            duration_ms=duration_ms,
        )
        event = self._redaction.redact_event(event)
        self.run.add_event(event)
        return event

    def add_approval(
        self,
        action: str,
        description: str,
        approved: bool = False,
        approver: Optional[str] = None,
    ) -> TraceEvent:
        """Capture an approval checkpoint."""
        approval = ApprovalEvent(
            action=action,
            description=description,
            approved=approved,
            approver=approver,
        )
        event = TraceEvent(
            run_id=self.run.id,
            event_type=EventType.APPROVAL_REQUEST,
            data={"action": action, "approved": approved},
            approval=approval,
        )
        self.run.add_event(event)
        return event

    def add_shell_command(
        self,
        command: str,
        output: Optional[str] = None,
        exit_code: Optional[int] = None,
        duration_ms: Optional[float] = None,
    ) -> TraceEvent:
        """Capture a shell command execution."""
        event = TraceEvent(
            run_id=self.run.id,
            event_type=EventType.SHELL_COMMAND,
            data={
                "command": command,
                "output": output,
                "exit_code": exit_code,
            },
            duration_ms=duration_ms,
        )
        event = self._redaction.redact_event(event)
        self.run.add_event(event)
        return event

    def add_error(self, error: str, context: Optional[str] = None) -> TraceEvent:
        """Capture an error."""
        event = TraceEvent(
            run_id=self.run.id,
            event_type=EventType.ERROR,
            data={"context": context or "", "error": error},
            error=error,
        )
        event = self._redaction.redact_event(event)
        self.run.add_event(event)
        return event

    @contextmanager
    def llm_call(self, model: str = "") -> Generator["_LLMCallContext", None, None]:
        """Context manager for timing an LLM call."""
        ctx = _LLMCallContext(self, model or self.run.model)
        yield ctx
        ctx._finalize()


class _LLMCallContext:
    """Helper for context-managed LLM calls."""

    def __init__(self, session: AgentScopeSession, model: str):
        self._session = session
        self._model = model
        self._start = time.monotonic()
        self._prompt = ""
        self._response = ""
        self._tokens_in = 0
        self._tokens_out = 0
        self._cost = 0.0

    def set_response(
        self,
        response: str,
        prompt: str = "",
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        cost_usd: float = 0.0,
    ) -> None:
        self._response = response
        self._prompt = prompt
        self._tokens_in = prompt_tokens
        self._tokens_out = completion_tokens
        self._cost = cost_usd

    def _finalize(self) -> None:
        duration = (time.monotonic() - self._start) * 1000
        self._session.add_llm_call(
            model=self._model,
            prompt=self._prompt,
            response=self._response,
            prompt_tokens=self._tokens_in,
            completion_tokens=self._tokens_out,
            cost_usd=self._cost,
            duration_ms=duration,
        )


class AgentEmitter:
    """High-level entry point for creating AgentScope sessions.

    Example::

        emitter = AgentEmitter()
        session = emitter.start_session("Fix login bug", agent_type="aider")
        session.add_tool_call("bash", {"cmd": "git status"})
        session.add_llm_call("claude-sonnet-4", "prompt...", "response...")
        run = session.end()
    """

    def __init__(
        self,
        storage_dir: Optional[str] = None,
        auto_save: bool = True,
    ):
        from pathlib import Path
        store = AgentStore(
            storage_dir=Path(storage_dir) if storage_dir else None
        ) if auto_save else None
        self._store = store
        self._redaction = RedactionPipeline()
        self._auto_save = auto_save

    def start_session(
        self,
        title: str = "",
        agent_type: str = "custom",
        working_directory: str = ".",
        model: str = "unknown",
        command: str = "",
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AgentScopeSession:
        """Create and start a new capture session."""
        session = AgentScopeSession(
            title=title,
            agent_type=agent_type,
            working_directory=working_directory,
            model=model,
            command=command,
            tags=tags,
            metadata=metadata,
            store=self._store,
            redaction=self._redaction,
            auto_save=self._auto_save,
        )
        session.start()
        return session
